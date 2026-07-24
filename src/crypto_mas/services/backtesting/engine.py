import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_mas.domain.models.backtest_result import BacktestResult
from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.domain.repositories.backtest_result_repository import BacktestResultRepository
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.infrastructure.time.time_provider import SimulatedTimeProvider
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from crypto_mas.services.trading_cycle_service.utils import get_timedelta

logger = logging.getLogger(__name__)

class BacktestEngineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = BacktestResultRepository(db)

    async def run_backtest(
        self,
        job_id: str,
        exchange: Exchange,
        symbols: list[str],
        timeframe: Timeframe,
        strategy_name: str,
        start_time: datetime,
        end_time: datetime,
        initial_balance: float = 10000.0,
        risk_level: int = 100,
        use_btc_shield: bool = True,
        use_htf_shield: bool = True,
        use_regime_shield: bool = True,
        config_json: dict | None = None,
        # Walk-forward can inject pre-warmed caches to skip redundant data fetch
        _shared_candle_cache=None,
        _shared_feature_cache=None,
    ) -> BacktestResult:
        # Create backtest result record
        
        merged_config = {
            "risk_level": risk_level,
            "use_btc_shield": use_btc_shield,
            "use_htf_shield": use_htf_shield,
            "use_regime_shield": use_regime_shield,
        }
        if config_json:
            merged_config.update(config_json)
            
        result = BacktestResult(
            job_id=job_id,
            status="RUNNING",
            exchange=exchange.value,
            timeframe=timeframe.value,
            strategy_name=strategy_name,
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            initial_balance=initial_balance,
            config_json=merged_config
        )
        self.repository.add(result)
        self.db.commit()
        
        try:
            logger.info(f"[{job_id}] Backtest started from {start_time} to {end_time}")
            
            # Intercept magic symbol lists like AUTO_GAINERS for backtests
            if len(symbols) == 1 and symbols[0].startswith("AUTO_"):
                logger.warning(f"[{job_id}] Magic symbol '{symbols[0]}' is not supported for historical backtests without full exchange scans. Defaulting to Top 5 crypto assets.")
                symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
            # Step 1: Market data provider & fetcher
            provider = get_market_data_provider(exchange)
            fetcher = HistoricalFetcherService(provider=provider, db=self.db)
            
            # Insert INIT log so the UI has immediate feedback
            from crypto_mas.domain.models.execution_log import ExecutionLog
            init_log = ExecutionLog(
                account_name=f"backtest-{job_id}",
                cycle_id=0,
                level="INFO",
                stage="INIT",
                message=f"Starting historical data fetch for {len(symbols)} symbols. This may take 1-2 minutes...",
                created_at=datetime.now(UTC)
            )
            self.db.add(init_log)
            self.db.commit()
            
            # Also backfill an extra 60 periods before start_time so features can warm up!
            delta = get_timedelta(timeframe)
            warmup_start = start_time - delta * 60
            
            # Add BTC to fetch list for shield
            fetch_symbols = list(set(symbols + ["BTCUSDT"])) if use_btc_shield else list(symbols)
            
            logger.info(f"[{job_id}] Backfilling historical data for {timeframe.value}...")
            await fetcher.backfill_universe(
                symbols=fetch_symbols,
                timeframe=timeframe,
                start_time=warmup_start,
                end_time=end_time,
            )
            
            htf_map = {
                Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
                Timeframe.FIFTEEN_MINUTES: Timeframe.FOUR_HOURS,
                Timeframe.ONE_HOUR: Timeframe.ONE_DAY,
                Timeframe.FOUR_HOURS: Timeframe.ONE_WEEK,
                Timeframe.ONE_DAY: Timeframe.ONE_MONTH,
            }
            htf = htf_map.get(timeframe)
            if htf and use_htf_shield:
                logger.info(f"[{job_id}] Backfilling HTF ({htf.value}) historical data...")
                htf_warmup_start = start_time - get_timedelta(htf) * 60
                await fetcher.backfill_universe(
                    symbols=fetch_symbols,
                    timeframe=htf,
                    start_time=htf_warmup_start,
                    end_time=end_time,
                )
                
            # Insert log to indicate fetch completion
            fetch_log = ExecutionLog(
                account_name=f"backtest-{job_id}",
                cycle_id=0,
                level="INFO",
                stage="PROGRESS",
                message="Data fetch completed! Building in-memory feature vectors...",
                created_at=datetime.now(UTC)
            )
            self.db.add(fetch_log)
            self.db.commit()
            
            # Step 2: Create isolated paper account
            account_name = f"backtest-{job_id}"
            account_repo = PaperAccountRepository(self.db)
            account_repo.create_if_not_exists(
                name=account_name,
                exchange=exchange.value,
                base_currency="USDT",
                initial_balance=__import__("decimal").Decimal(str(initial_balance)),
            )
            self.db.commit()
            
            # Step 3: Setup simulated time and TradingCycleService
            time_provider = SimulatedTimeProvider(start_time=start_time)
            
            from crypto_mas.domain.repositories.candle_repository import CandleRepository
            from crypto_mas.domain.repositories.feature_snapshot_repository import (
                FeatureSnapshotRepository,
            )
            from crypto_mas.services.backtesting.memory_cache import (
                InMemoryCandleRepository,
                InMemoryFeatureSnapshotRepository,
            )

            if _shared_candle_cache is not None and _shared_feature_cache is not None:
                # Walk-forward mode: reuse pre-warmed caches — skip expensive data fetch
                logger.info(f"[{job_id}] Using shared memory cache from walk-forward parent.")
                mem_candles = _shared_candle_cache
                mem_features = _shared_feature_cache
            else:
                candle_db = CandleRepository(self.db)
                feature_db = FeatureSnapshotRepository(self.db)
                mem_candles = InMemoryCandleRepository(candle_db)
                mem_features = InMemoryFeatureSnapshotRepository(feature_db)
                
                # PRE-CALCULATE ALL FEATURES ONCE! (This avoids 1.0s delay per tick)
                from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
                temp_feature_svc = FeaturePipelineService(self.db, candle_repo=candle_db, feature_repo=feature_db)
                for sym in fetch_symbols:
                    all_candles = candle_db.list_by_symbol(exchange.value, sym, timeframe.value, end_time=end_time, limit=None)
                    if all_candles:
                        all_snaps = temp_feature_svc.calculator.calculate(all_candles)
                        if all_snaps:
                            mem_features.bulk_upsert(all_snaps)
                
                logger.warning(f"PROFILE [{job_id}] mem_features populated with {sum(len(v) for v in mem_features._snaps.values())} snaps!")

            
            strategy_mode = "swing"
            if strategy_name == "hft_momentum":
                strategy_mode = "scalping"
            elif strategy_name == "ema_golden_cross":
                strategy_mode = "hodl"

            cycle_service = TradingCycleService(
                db=self.db,
                market_provider=provider,
                time_provider=time_provider,
                strategy_mode=strategy_mode,
                candle_repo=mem_candles,
                feature_repo=mem_features
            )
            
            # --- BACKTEST OVERRIDES ---
            # 1. Force synchronous execution queue so trades don't lag behind the simulated time loop
            from crypto_mas.services.backtesting.memory_cache import InMemoryPositionRepository
            from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
            
            # Create a completely isolated execution queue for this specific backtest run
            # This prevents collisions with the live Trading Scheduler singleton
            queue = OrderExecutorQueue()
            queue.sync_mode = True
            
            # Reuse a SINGLE broker instance — don't call factory() on every cycle
            _backtest_broker = cycle_service.paper_broker
            _backtest_broker.is_backtest = True  # disables per-operation commit/flush/logging
            queue.set_broker_factory(lambda: _backtest_broker)
            
            # Inject the isolated queue into the orchestrator
            cycle_service.executor_queue = queue
            
            # Replace broker's DB-backed position repository with a pure in-memory version
            # This eliminates ALL SQLite reads/writes for positions during the simulation loop
            mem_positions = InMemoryPositionRepository()
            _backtest_broker.position_repository = mem_positions  # type: ignore
            
            # Cache account object in broker to avoid account_repo.get_by_name() every cycle
            _backtest_broker._bt_account = _backtest_broker.account_repository.get_by_name(account_name)  # type: ignore
            
            # Give the orchestrator access to the same in-memory position repo
            # so its open_position / SL-cooldown checks are also O(1) dict lookups
            cycle_service._bt_position_repo = mem_positions  # type: ignore
            
            # 2. Patch the broker service to use in-memory snapshots so it doesn't query SQLite 432,000 times!
            cycle_service.paper_broker.feature_snapshot_repository = mem_features
            
            # Pre-calculate all features instantly using Pandas/pandas-ta
            # and inject them into memory, bypassing the cycle's loop calculations.
            from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
            feature_svc = FeaturePipelineService(self.db, candle_repo=mem_candles)
            
            for sym in fetch_symbols:
                # 1. Base timeframe
                candles = mem_candles.list_by_symbol(exchange.value, sym, timeframe.value)
                if candles:
                    snapshots = feature_svc.calculator.calculate(candles)
                    if snapshots:
                        mem_features.bulk_upsert(snapshots)
                
                # 2. HTF (Higher Timeframe)
                htf_map = {
                    Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
                    Timeframe.FIFTEEN_MINUTES: Timeframe.FOUR_HOURS,
                    Timeframe.ONE_HOUR: Timeframe.ONE_DAY,
                    Timeframe.FOUR_HOURS: Timeframe.ONE_WEEK,
                    Timeframe.ONE_DAY: Timeframe.ONE_MONTH,
                }
                htf = htf_map.get(timeframe)
                if htf:
                    htf_candles = mem_candles.list_by_symbol(exchange.value, sym, htf.value)
                    if htf_candles:
                        htf_snapshots = feature_svc.calculator.calculate(htf_candles)
                        if htf_snapshots:
                            mem_features.bulk_upsert(htf_snapshots)

            # Patch feature_service in cycle_service so it doesn't recalculate on every tick!
            # It just returns fake metadata since the data is already in memory.
            def _mock_calc_and_store(*args, **kwargs):
                return {"exchange": exchange.value, "symbol": kwargs.get("symbol"), "timeframe": kwargs.get("timeframe"), "processed_rows": 0}
            cycle_service.feature_service.calculate_and_store = _mock_calc_and_store  # type: ignore
            
            # Patch fetcher_service so it doesn't try to download missing candles during the simulation loop!
            async def _mock_backfill_universe(*args, **kwargs):
                return
            cycle_service.fetcher_service.backfill_universe = _mock_backfill_universe  # type: ignore
            
            # Step 4: Time loop
            total_trades = 0
            cycle_count = 0
            
            while time_provider.now() <= end_time:
                cycle_count += 1

                # Batch DB commit every 100 cycles to release SQLite write locks
                if cycle_count % 100 == 0:
                    self.db.commit()

                # Heartbeat log every 1440 cycles (~1 day of 1-min candles)
                if cycle_count % 1440 == 0:
                    hb_log = ExecutionLog(
                        account_name=account_name,
                        cycle_id=0,
                        level="INFO",
                        stage="PROGRESS",
                        message=f"Simulated {cycle_count} cycles. Current time: {time_provider.now().strftime('%Y-%m-%d %H:%M')}",
                        created_at=datetime.now(UTC)
                    )
                    self.db.add(hb_log)
                    self.db.commit()

                # Check for user cancellation every 50 cycles (faster abort remains acceptable)
                if cycle_count % 50 == 0:
                    self.db.refresh(result)
                    if result.status == "CANCELLED":
                        logger.info(f"[{job_id}] Backtest cancelled by user.")
                        result.completed_at = datetime.now(UTC)  # type: ignore
                        self.db.commit()
                        break

                import time
                t0 = time.time()
                
                cycle = await cycle_service.run_cycle(
                    account_name=account_name,
                    symbols=symbols,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    trigger=f"BACKTEST-{job_id}",
                    risk_level=risk_level,
                    use_btc_shield=use_btc_shield,
                    use_htf_shield=use_htf_shield,
                    use_regime_shield=use_regime_shield,
                    cycle_index=cycle_count,
                    config_json=config_json,
                )
                
                t1 = time.time()

                total_trades += (cycle.trades_executed or 0)
                time_provider.tick(delta)
                
                t2 = time.time()
                logger.warning(f"PROFILE [{job_id}] Cycle {cycle_count}: run_cycle={t1-t0:.4f}s, tick={t2-t1:.4f}s")



                # Yield to event loop every 20 ticks to ensure Uvicorn stays responsive
                if cycle_count % 20 == 0:
                    import asyncio
                    await asyncio.sleep(0)
                
            # We no longer need to restore sync_mode because we used an isolated queue
            logger.info(f"Backtest {job_id} complete. Simulated {cycle_count} cycles.")
            account_repo.get_by_name(account_name)
            
            # 6. Calculate Performance Analytics
            logger.info(f"[{job_id}] Calculating performance analytics.")
            from crypto_mas.services.reporting_service.analytics import PerformanceAnalytics
            analytics = PerformanceAnalytics(self.db)
            metrics = analytics.calculate_for_account(account_name, initial_balance)
            
            result.total_trades = metrics.total_trades  # type: ignore

            # Accurate final equity from last cycle or computed
            stmt = select(TradingCycle).where(TradingCycle.account_name == account_name).order_by(TradingCycle.started_at.desc()).limit(1)
            last_cycle = self.db.scalars(stmt).first()
            if last_cycle and last_cycle.ending_equity:
                result.final_equity = last_cycle.ending_equity  # type: ignore
            else:
                result.final_equity = initial_balance + metrics.total_pnl  # type: ignore

            result.total_fees_paid = metrics.total_fees_paid  # type: ignore
            result.win_rate = metrics.win_rate  # type: ignore
            result.max_drawdown = metrics.max_drawdown  # type: ignore
            result.sharpe_ratio = metrics.sharpe_ratio  # type: ignore
            result.sortino_ratio = metrics.sortino_ratio  # type: ignore
            result.calmar_ratio = metrics.calmar_ratio  # type: ignore
            result.profit_factor = metrics.profit_factor  # type: ignore
            result.expectancy = metrics.expectancy  # type: ignore
            result.avg_win = metrics.avg_win  # type: ignore
            result.avg_loss = metrics.avg_loss  # type: ignore
            result.avg_trade_duration_s = metrics.avg_trade_duration_s  # type: ignore
            
            result.status = "COMPLETED"  # type: ignore
            result.completed_at = datetime.now(UTC)  # type: ignore
            self.db.commit()
            
            logger.info(f"[{job_id}] Backtest completed successfully. Final Equity: {result.final_equity}, Win Rate: {result.win_rate}, Max DD: {result.max_drawdown}")
            
            # 7. Archive Data
            try:
                self._archive_backtest_data(job_id, account_name, result)
            except Exception as e:
                logger.error(f"[{job_id}] Failed to archive backtest data: {e}")
                
            return result
            
        except Exception as e:
            logger.exception(f"[{job_id}] Backtest failed: {e}")
            self.repository.update_status(job_id, "FAILED")
            result.error_message = str(e)  # type: ignore
            result.completed_at = datetime.now(UTC)  # type: ignore
            self.db.commit()
            raise e

    def _archive_backtest_data(self, job_id: str, account_name: str, result: BacktestResult):
        import json
        from pathlib import Path
        
        archive_dir = Path(f"data/backtests/{job_id}")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Config
        with open(archive_dir / "config.json", "w") as f:
            json.dump(result.config_json or {}, f, indent=2)
            
        # 2. Stats
        stats = {
            "initial_balance": result.initial_balance,
            "final_equity": result.final_equity,
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "max_drawdown": result.max_drawdown,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "strategy": result.strategy_name,
            "symbols": result.symbols,
        }
        with open(archive_dir / "stats.json", "w") as f:
            json.dump(stats, f, indent=2)
            
        # 3. Trades
        from crypto_mas.domain.models.trade import Trade
        trades = self.db.execute(select(Trade).where(Trade.account_name == account_name)).scalars().all()
        trades_data = []
        for t in trades:
            trades_data.append({
                "symbol": t.symbol,
                "side": t.side,
                "quantity": float(t.quantity),
                "price": float(t.price),
                "realized_pnl": float(t.realized_pnl),
                "reason": t.reason,
                "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            })
        with open(archive_dir / "trades.json", "w") as f:
            json.dump(trades_data, f, indent=2)
            
        # 4. Market Data (Candles)
        from crypto_mas.domain.models.candle import Candle
        market_data = {}
        for sym in result.symbols:  # type: ignore
            candles = self.db.execute(
                select(Candle)
                .where(Candle.exchange == result.exchange)
                .where(Candle.symbol == sym)
                .where(Candle.timeframe == result.timeframe)
                .where(Candle.open_time >= result.start_time)
                .where(Candle.open_time <= result.end_time)
                .order_by(Candle.open_time.asc())
            ).scalars().all()
            
            market_data[sym] = [{
                "time": c.open_time.isoformat(),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume)
            } for c in candles]
            
        with open(archive_dir / "market_data.json", "w") as f:
            json.dump(market_data, f, indent=2)
            
        logger.info(f"[{job_id}] Successfully archived data to {archive_dir}")
