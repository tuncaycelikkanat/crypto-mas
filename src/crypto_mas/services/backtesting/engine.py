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
    ) -> BacktestResult:
        # Create backtest result record
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
        )
        self.repository.add(result)
        self.db.commit()
        
        try:
            logger.info(f"[{job_id}] Backtest started from {start_time} to {end_time}")
            
            # Step 1: Pre-fetch market data
            # To simulate properly without fetching from API every tick, we backfill first.
            provider = get_market_data_provider(exchange)
            fetcher = HistoricalFetcherService(provider=provider, db=self.db)
            
            # Also backfill an extra 60 periods before start_time so features can warm up!
            delta = TradingCycleService._get_timedelta(timeframe)
            warmup_start = start_time - delta * 60
            
            logger.info(f"[{job_id}] Backfilling historical data...")
            await fetcher.backfill_universe(
                symbols=symbols,
                timeframe=timeframe,
                start_time=warmup_start,
                end_time=end_time,
            )
            logger.info(f"[{job_id}] Backfill completed.")
            
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
            
            # Set up InMemory caching for ultra-fast backtesting
            from crypto_mas.domain.repositories.candle_repository import CandleRepository
            from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
            from crypto_mas.services.backtesting.memory_cache import InMemoryCandleRepository, InMemoryFeatureSnapshotRepository
            
            candle_db = CandleRepository(self.db)
            feature_db = FeatureSnapshotRepository(self.db)
            
            mem_candles = InMemoryCandleRepository(candle_db)
            mem_features = InMemoryFeatureSnapshotRepository(feature_db)
            
            cycle_service = TradingCycleService(
                db=self.db,
                market_provider=provider,
                time_provider=time_provider,
                strategy_mode=strategy_name,
                candle_repo=mem_candles,
                feature_repo=mem_features
            )
            
            # Step 4: Time loop
            total_trades = 0
            cycle_count = 0
            
            while time_provider.now() <= end_time:
                cycle_count += 1
                if cycle_count % 10 == 0:
                    self.db.refresh(result)
                    if result.status == "CANCELLED":
                        logger.info(f"[{job_id}] Backtest cancelled by user.")
                        result.completed_at = datetime.now(UTC)
                        self.db.commit()
                        return result

                logger.debug(f"[{job_id}] Simulating time: {time_provider.now()}")
                
                cycle = await cycle_service.run_cycle(
                    account_name=account_name,
                    symbols=symbols,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    trigger=f"BACKTEST-{job_id}",
                )
                
                total_trades += cycle.trades_executed
                time_provider.tick(delta)
                
            # Step 5: Final metrics
            account = account_repo.get_by_name(account_name)
            
            # 6. Calculate Performance Analytics
            logger.info(f"[{job_id}] Calculating performance analytics.")
            from crypto_mas.services.reporting_service.analytics import PerformanceAnalytics
            analytics = PerformanceAnalytics(self.db)
            metrics = analytics.calculate_for_account(account_name, initial_balance)
            
            result.total_trades = metrics.total_trades
            
            # A more accurate final equity comes from the last cycle or current equity:
            stmt = select(TradingCycle).where(TradingCycle.account_name == account_name).order_by(TradingCycle.started_at.desc()).limit(1)
            last_cycle = self.db.scalars(stmt).first()
            if last_cycle and last_cycle.ending_equity:
                result.final_equity = last_cycle.ending_equity
            else:
                result.final_equity = initial_balance + metrics.total_pnl
                
            result.win_rate = metrics.win_rate
            result.max_drawdown = metrics.max_drawdown
            
            result.status = "COMPLETED"
            result.completed_at = datetime.now(UTC)
            self.db.commit()
            
            logger.info(f"[{job_id}] Backtest completed successfully. Final Equity: {result.final_equity}, Win Rate: {result.win_rate}, Max DD: {result.max_drawdown}")
            return result
            
        except Exception as e:
            logger.exception(f"[{job_id}] Backtest failed: {e}")
            self.repository.update_status(job_id, "FAILED")
            result.error_message = str(e)
            result.completed_at = datetime.now(UTC)
            self.db.commit()
            raise e
