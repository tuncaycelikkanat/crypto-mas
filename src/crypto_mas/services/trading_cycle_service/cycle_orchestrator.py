import logging
import time
from datetime import UTC, timedelta

from sqlalchemy.orm import Session

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.domain.repositories.trading_cycle_repository import TradingCycleRepository
from crypto_mas.engine.portfolio.portfolio import PortfolioEngine
from crypto_mas.engine.risk.manager import RiskManager
from crypto_mas.engine.risk.models.btc_crash_model import BTCCrashModel
from crypto_mas.engine.risk.models.htf_portfolio_model import HTFPortfolioModel
from crypto_mas.engine.risk.models.regime_model import RegimeModel
from crypto_mas.engine.risk.profiles import get_risk_profile
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.engine.strategy.factory import StrategyFactory
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.services.gainers_service import fetch_gainers, fetch_hidden_gems
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService

logger = logging.getLogger(__name__)


class TradingCycleService:
    def __init__(
        self,
        db: Session,
        market_provider: MarketDataProvider,
        time_provider: TimeProvider | None = None,
        strategy_mode: str = "swing",
        candle_repo = None,
        feature_repo = None,
        ws_client = None,
    ) -> None:
        self.db = db
        self.time_provider = time_provider or SystemTimeProvider()
        self.strategy_mode = strategy_mode
        self.ws_client = ws_client

        self.cycle_repository = TradingCycleRepository(db)
        self.feature_snapshot_repository = feature_repo or FeatureSnapshotRepository(db)

        self.fetcher_service = HistoricalFetcherService(provider=market_provider, db=db)
        self.feature_service = FeaturePipelineService(
            db, 
            candle_repo=candle_repo, 
            feature_repo=self.feature_snapshot_repository
        )

        self.portfolio_engine = PortfolioEngine(time_provider=self.time_provider)
        self.risk_engine = RiskEngine(limits=get_risk_profile(strategy_mode))
        self.paper_broker = PaperBrokerService(
            db=db,
            time_provider=self.time_provider,
            strategy_mode=strategy_mode,
        )
        self.risk_manager = RiskManager(models=[
            BTCCrashModel(),
            HTFPortfolioModel(),
            RegimeModel(),
        ])

    async def run_cycle(
        self,
        account_name: str,
        symbols: list[str],
        timeframe: Timeframe,
        strategy_name: str = "multi_agent",
        trigger: str = "MANUAL",
        risk_level: int = 50,
        use_btc_shield: bool = True,
        use_htf_shield: bool = True,
        use_regime_shield: bool = True,
        cycle_index: int | None = None,
        config_json: dict | None = None,
    ) -> TradingCycle:
        now = self.time_provider.now()
        strategy = StrategyFactory.create(strategy_name, time_provider=self.time_provider)
        
        if "AUTO_GAINERS" in symbols:
            try:
                min_vol = max(2_000_000, 20_000_000 - (risk_level * 180_000))
                gainer_data = await fetch_gainers(exchange=self.fetcher_service.provider.exchange.value, limit=50, only_pump=True, min_volume_usdt=min_vol)
                auto_symbols = [item["symbol"] for item in gainer_data.get("pumpwatch", [])]
                if not auto_symbols:
                    auto_symbols = [item["symbol"] for item in gainer_data.get("gainers", [])]
                if auto_symbols:
                    symbols = auto_symbols
                    if self.ws_client:
                        for sym in symbols:
                            self.ws_client.add_subscription(sym, "trade")
                else:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
            except Exception as e:
                logger.error(f"Failed to fetch auto gainers: {e}")
                if len(symbols) == 1:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
                else:
                    symbols = [s for s in symbols if s != "AUTO_GAINERS"]
                    
        elif "HIDDEN_GEMS" in symbols:
            try:
                min_vol = max(1_000_000, 5_000_000 - (risk_level * 40_000))
                max_vol = 50_000_000
                gem_data = await fetch_hidden_gems(exchange=self.fetcher_service.provider.exchange.value, limit=50, min_volume_usdt=min_vol, max_volume_usdt=max_vol)
                auto_symbols = [item["symbol"] for item in gem_data.get("hidden_gems", [])]
                if auto_symbols:
                    symbols = auto_symbols
                    if self.ws_client:
                        for sym in symbols:
                            self.ws_client.add_subscription(sym, "trade")
                else:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
            except Exception as e:
                logger.error(f"Failed to fetch hidden gems: {e}")
                if len(symbols) == 1:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
                else:
                    symbols = [s for s in symbols if s != "HIDDEN_GEMS"]
        
        cycle = TradingCycle(
            account_name=account_name,
            exchange=self.fetcher_service.provider.exchange.value,
            timeframe=timeframe.value,
            status="RUNNING",
            trigger=trigger,
            started_at=now,
        )
        
        is_backtest = trigger.startswith("BACKTEST-")
        if not is_backtest:
            self.cycle_repository.add(cycle)
            self.db.commit()
            display_id = cycle.id
        else:
            # Skip DB writes for backtest to massively speed up the loop
            display_id = cycle_index if cycle_index is not None else 0
            cycle.id = display_id


        def _log(stage: str, message: str, level: str = "INFO", payload: dict | None = None):
            if trigger.startswith("BACKTEST-") and level not in ("ERROR", "SUCCESS"):
                return
            from crypto_mas.domain.models.execution_log import ExecutionLog
            log = ExecutionLog(
                account_name=account_name,
                cycle_id=cycle.id,
                level=level,
                stage=stage,
                message=message,
                payload_json=payload,
                created_at=self.time_provider.now()
            )
            self.db.add(log)

        _log("INIT", f"Cycle {display_id} started for {len(symbols)} symbols: {symbols}", payload={
            "cycle_id": cycle.id,
            "display_id": display_id,
            "account": account_name,
            "symbols": symbols,
            "strategy": strategy_name,
            "trigger": trigger,
            "time": now.isoformat(),
        })

        try:
            is_backtest = trigger.startswith("BACKTEST-")
            if is_backtest:
                # In backtest mode, skip fetching data because engine.py pre-calculated it in memory!
                htf_map = {
                    Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
                    Timeframe.FIFTEEN_MINUTES: Timeframe.FOUR_HOURS,
                    Timeframe.ONE_HOUR: Timeframe.ONE_DAY,
                    Timeframe.FOUR_HOURS: Timeframe.ONE_WEEK,
                    Timeframe.ONE_DAY: Timeframe.ONE_MONTH,
                }
                htf = htf_map.get(timeframe)
                
                btc_is_crashing = False
                if use_btc_shield:
                    btc_feat = self.feature_snapshot_repository.get_latest(
                        exchange=self.fetcher_service.provider.exchange.value,
                        symbol="BTCUSDT",
                        timeframe=timeframe.value,
                        end_time=now
                    )
                    roc_val = btc_feat.features_json.get("roc_14") if btc_feat else None
                    if roc_val is not None and roc_val < -5.0:
                        btc_is_crashing = True
                        _log("RISK", "MARKET CRASH DETECTED! BTC ROC: < -5.0%. Longs will be restricted.", "WARN")
            else:
                btc_is_crashing, htf = await self._fetch_data_for_symbols(symbols, timeframe, now, cycle, _log, use_btc_shield, display_id=display_id)
            
            time.time()
            decisions, open_positions = self._run_strategies_and_score(
                symbols=symbols,
                timeframe=timeframe,
                now=now,
                strategy=strategy,
                strategy_name=strategy_name,
                risk_level=risk_level,
                cycle=cycle,
                account_name=account_name,
                htf=htf,
                btc_is_crashing=btc_is_crashing,
                use_btc_shield=use_btc_shield,
                use_htf_shield=use_htf_shield,
                use_regime_shield=use_regime_shield,
                config_json=config_json,
                _log=_log,
                display_id=cycle.id if not is_backtest else cycle_index
            )
            
            cycle.symbols_processed = len(symbols)
            cycle.decisions_made = len(decisions)
            
            strategy_id = f"{strategy_name}_{risk_level}"

            self._apply_risk_and_execute(
                decisions=decisions,
                timeframe=timeframe,
                now=now,
                cycle=cycle,
                account_name=account_name,
                symbols=symbols,
                _log=_log,
                open_positions=open_positions,
                strategy_id=strategy_id
            )
            time.time()
            
            if not trigger.startswith("BACKTEST-"):
                cycle.status = "COMPLETED"
                self.db.commit()
            cycle.trades_executed = len(decisions)

            
            return cycle
            
        except Exception as e:
            logger.exception(f"[Cycle {display_id}] Failed with error: {e}")
            _log("FAILED", f"Critical error in cycle {display_id}: {str(e)}", "ERROR")
            self.cycle_repository.update_status(cycle.id, "FAILED")
            if not trigger.startswith("BACKTEST-"):
                self.db.commit()
            raise e

    async def _fetch_data_for_symbols(self, symbols, timeframe, now, cycle, _log, use_btc_shield=True, display_id: int | None = None):
        display_id = display_id if display_id is not None else cycle.id
        logger.debug(f"[Cycle {display_id}] Starting market data sync for {len(symbols)} symbols.")
        _log("MARKET_DATA", f"Fetching history from {self.fetcher_service.provider.exchange.value} for {timeframe}")
        
        fetch_symbols = set(symbols)
        if use_btc_shield:
            fetch_symbols.add("BTCUSDT")
        fetch_symbols_list = list(fetch_symbols)
        
        fallback_start = now - self._get_timedelta(timeframe) * 1000
        
        await self.fetcher_service.backfill_universe(
            symbols=fetch_symbols_list,
            timeframe=timeframe,
            start_time=fallback_start,
            end_time=now,
        )
        
        htf_map = {
            Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
            Timeframe.FIFTEEN_MINUTES: Timeframe.FOUR_HOURS,
            Timeframe.ONE_HOUR: Timeframe.ONE_DAY,
            Timeframe.FOUR_HOURS: Timeframe.ONE_WEEK,
            Timeframe.ONE_DAY: Timeframe.ONE_MONTH,
        }
        htf = htf_map.get(timeframe)
        
        if htf:
            _log("MARKET_DATA", f"Fetching HTF ({htf.value}) history for Regime Filter")
            htf_start = now - self._get_timedelta(htf) * 60
            await self.fetcher_service.backfill_universe(
                symbols=fetch_symbols_list,
                timeframe=htf,
                start_time=htf_start,
                end_time=now,
            )
            
        btc_is_crashing = False
        if use_btc_shield:
            self.feature_service.calculate_and_store(
                exchange=self.fetcher_service.provider.exchange,
                symbol="BTCUSDT",
                timeframe=timeframe,
                end_time=now,
                limit=1000,
            )
            btc_snapshots = self.feature_snapshot_repository.list_by_symbol(
                exchange=self.fetcher_service.provider.exchange.value,
                symbol="BTCUSDT",
                timeframe=timeframe.value,
                limit=5,
            )
            
            if btc_snapshots:
                latest_btc = btc_snapshots[-1].features_json
                btc_roc = latest_btc.get("roc_14")
                if btc_roc is not None and btc_roc < -5.0:
                    btc_is_crashing = True
                    _log("RISK", f"MARKET CRASH DETECTED! BTC ROC: {btc_roc:.2f}%. Longs will be restricted.", "WARN")
                    
        return btc_is_crashing, htf

    def _run_strategies_and_score(self, symbols, timeframe, now, strategy, strategy_name, risk_level, cycle, account_name, htf, btc_is_crashing, _log, use_btc_shield=True, use_htf_shield=True, use_regime_shield=True, config_json=None, display_id: int | None = None):
        display_id = display_id if display_id is not None else cycle.id
        decisions = []
        is_backtest = cycle.trigger.startswith("BACKTEST-")
        
        # --- Pre-fetch open positions + stop-loss cooldowns in 2 bulk queries ---
        exchange_str = self.fetcher_service.provider.exchange.value
        
        # In backtest mode, use the shared in-memory position repo — zero DB queries
        # In live mode, do 2 bulk SQL queries instead of N per-symbol queries
        pos_repo = getattr(self, "_bt_position_repo", None) if is_backtest else None
        if pos_repo is None:
            pos_repo = PositionRepository(self.db)
        
        open_position_symbols: set[str] = pos_repo.get_open_position_symbols(account_name, exchange_str)
        cooldown_symbols: set[str] = pos_repo.get_recent_stop_loss_symbols(
            account_name=account_name,
            exchange=exchange_str,
            time_now=now,
            cooldown_minutes=30,
        )
        
        for symbol in symbols:
            # logger.debug(f"[Cycle {display_id}] Processing features and decisions for {symbol}")
            _log("STRATEGY", f"Evaluating {strategy_name} for {symbol}")
            
            if not is_backtest:
                self.feature_service.calculate_and_store(
                    exchange=self.fetcher_service.provider.exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    end_time=now,
                    limit=1000,
                )
            
            snapshots = self.feature_snapshot_repository.list_by_symbol(
                exchange=self.fetcher_service.provider.exchange.value,
                symbol=symbol,
                timeframe=timeframe.value,
                end_time=now,
                limit=5,  # strategies only use the last 1-3 snapshots
            )
            
            if not snapshots:
                logger.warning(f"[Cycle {display_id}] No feature snapshots for {symbol}. Skipping.")
                _log("STRATEGY", f"No data available for {symbol}, skipped", "WARN")
                continue
            
            latest_snapshot = snapshots[-1]
            timeframe_delta = self._get_timedelta(timeframe)
            max_allowed_delay = timeframe_delta + timedelta(minutes=15)
            
            snap_time = latest_snapshot.timestamp
            if snap_time.tzinfo is None:
                snap_time = snap_time.replace(tzinfo=UTC)
            if now - snap_time > max_allowed_delay:
                err_msg = f"STALE DATA DETECTED for {symbol}: Latest snapshot timestamp {latest_snapshot.timestamp} is older than allowed {max_allowed_delay} from now {now}. Kill-Switch triggered."
                if is_backtest:
                    logger.warning(f"[Cycle {display_id}] {err_msg} (Skipped due to backtest data gap)")
                    _log("STRATEGY", f"Stale data for {symbol}, skipped", "WARN")
                    continue
                else:
                    logger.error(f"[Cycle {display_id}] {err_msg}")
                    raise ValueError(err_msg)

            htf_snapshots = []  # type: ignore
            if htf and use_htf_shield:
                if not is_backtest:
                    self.feature_service.calculate_and_store(
                        exchange=self.fetcher_service.provider.exchange,
                        symbol=symbol,
                        timeframe=htf,
                    )
                htf_snapshots = self.feature_snapshot_repository.list_by_symbol(
                    exchange=self.fetcher_service.provider.exchange.value,
                    symbol=symbol,
                    timeframe=htf.value,
                    end_time=now,
                    limit=5,
                )
            
            kwargs = {}
            if strategy_name == "regime_adaptive":
                kwargs["config"] = config_json or {}
            elif strategy_name == "multi_agent":
                kwargs["use_regime_shield"] = use_regime_shield
                
            decision = strategy.decide(
                exchange=self.fetcher_service.provider.exchange,
                symbol=symbol,
                timeframe=timeframe,
                snapshots=snapshots,
                risk_level=risk_level,
                is_open=(symbol in open_position_symbols),
                **kwargs
            )
            
            if decision:
                # 1. Base logic: Don't buy if we already hold an open position
                if decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT):
                    # O(1) set lookup — no DB query
                    if symbol in open_position_symbols:
                        _log("STRATEGY", f"Decision {decision.action.value} for {symbol} REJECTED: Already have an open position.", "WARN")
                        decision.action = DecisionAction.HOLD
                        decision.reason += " | REJECTED: Open Position Exists"
                        
                    elif symbol in cooldown_symbols:
                        _log("STRATEGY", f"Decision {decision.action.value} for {symbol} REJECTED: Cooldown active (Recent Stop-Loss).", "WARN")
                        decision.action = DecisionAction.HOLD
                        decision.reason += " | REJECTED: Cooldown (30m)"

                # 2. Modular Risk Architecture (QuantConnect style shields)
                if decision.action not in (DecisionAction.HOLD, DecisionAction.CLOSE_LONG, DecisionAction.CLOSE_SHORT):
                    context = {
                        "btc_is_crashing": btc_is_crashing,
                        "use_btc_shield": use_btc_shield,
                        "htf_snapshots": htf_snapshots if 'htf_snapshots' in locals() else [],
                        "use_htf_shield": use_htf_shield,
                        "use_regime_shield": use_regime_shield,
                    }
                    decision = self.risk_manager.evaluate_decision(decision, context)
                    
                    if decision.action == DecisionAction.HOLD:
                        _log("STRATEGY", f"Decision for {symbol} REJECTED by RiskManager: {decision.reason}", "WARN")
                    
                latest_snap = snapshots[-1].features_json if snapshots else {}
                
                # Append if NOT AVOID and NOT REJECTED HOLD (but keep valid HOLDs that come from tactics)
                if decision.action != DecisionAction.AVOID:
                    # Only append HOLD if it is for an OPEN position (otherwise it's noise)
                    if decision.action == DecisionAction.HOLD and symbol not in open_position_symbols:
                        pass
                    else:
                        decisions.append(decision)
                        _log(
                        "STRATEGY",
                        f"Decision made for {symbol}: {decision.action.value} (Confidence: {decision.confidence:.4f})",
                        payload={
                            "symbol": symbol,
                            "action": decision.action.value,
                            "confidence": round(decision.confidence, 4),
                            "score": {
                                "final_score": round(decision.score.final_score, 4),
                                "trend_score": round(decision.score.trend_score, 4),
                                "momentum_score": round(decision.score.momentum_score, 4),
                                "volatility_penalty": round(decision.score.volatility_penalty, 4),
                            },
                            "features": {
                                k: round(v, 4) if isinstance(v, float) else v
                                for k, v in latest_snap.items()
                                if k in (
                                    "rsi_14", "ema_20", "ema_50", "macd", "macd_signal",
                                    "bb_upper", "bb_lower", "bb_mid", "atr_14",
                                    "volume_sma_20", "roc_14", "adx_14",
                                    "close", "high", "low", "open",
                                )
                            },
                            "reason": decision.reason,
                            "regime": {
                                "trend": decision.regime.trend_label if hasattr(decision.regime, 'trend_label') else None,
                                "volatility": decision.regime.volatility_label if hasattr(decision.regime, 'volatility_label') else None,
                            } if decision.regime else None,
                        }
                    )
                else:
                    _log(
                        "STRATEGY",
                        f"Skipped {symbol}: {decision.reason or 'Conditions not met'}",
                        payload={
                            "symbol": symbol,
                            "action": "HOLD",
                            "features": {
                                k: round(v, 4) if isinstance(v, float) else v
                                for k, v in latest_snap.items()
                                if k in ("rsi_14", "macd", "macd_signal", "close", "roc_14", "volume_sma_20")
                            }
                        }
                    )
            else:
                latest_snap = snapshots[-1].features_json if snapshots else {}
                _log(
                    "STRATEGY",
                    f"Skipped {symbol}: No signal generated by strategy",
                    payload={
                        "symbol": symbol,
                        "action": "NONE",
                        "features": {
                            k: round(v, 4) if isinstance(v, float) else v
                            for k, v in latest_snap.items()
                            if k in ("rsi_14", "macd", "macd_signal", "close", "roc_14")
                        }
                    }
                )
        return decisions, list(open_position_symbols)

    def _apply_risk_and_execute(self, decisions, timeframe, now, cycle, account_name, symbols, _log, open_positions: list[str], strategy_id: str | None = None):
        logger.debug(f"[Cycle {cycle.id}] Constructing portfolio target from {len(decisions)} decisions.")
        _log("PORTFOLIO", f"Constructing target portfolio from {len(decisions)} active signals", payload={
            "total_signals": len(decisions),
            "candidate_symbols": [d.symbol for d in decisions],
            "actions": {d.symbol: d.action.value for d in decisions},
        })
        target_portfolio = self.portfolio_engine.build_target_portfolio(
            exchange=self.fetcher_service.provider.exchange,
            timeframe=timeframe,
            decisions=decisions,
            open_positions=open_positions
        )
        target_portfolio.strategy_id = strategy_id
        
        logger.debug(f"[Cycle {cycle.id}] Evaluating risk limits.")
        risk_assessment = self.risk_engine.assess(target=target_portfolio)
        approved_portfolio = risk_assessment.approved_target
        
        if approved_portfolio is None:
            _log("RISK", f"Risk engine rejected portfolio: {risk_assessment.reason}. Holding current positions.", "WARN")
            from crypto_mas.engine.portfolio import PortfolioTarget
            approved_portfolio = PortfolioTarget(
                exchange=target_portfolio.exchange,
                timeframe=target_portfolio.timeframe,
                strategy_id=strategy_id,
                target_positions=[],
                cash_weight=1.0,
                gross_exposure=0.0,
                reason="Risk-rejected: holding cash.",
                created_at=self.time_provider.now(),
            )

        if approved_portfolio and approved_portfolio.target_positions:
            _log("RISK", "Risk checks passed, proceeding to execution", payload={
                "status": risk_assessment.status.value if hasattr(risk_assessment.status, 'value') else str(risk_assessment.status),
                "reason": risk_assessment.reason,
                "approved_positions": [
                    {"symbol": p.symbol, "weight": round(p.target_weight, 4), "confidence": round(p.confidence, 4)}
                    for p in approved_portfolio.target_positions
                ],
                "gross_exposure": round(approved_portfolio.gross_exposure, 4),
                "cash_weight": round(approved_portfolio.cash_weight, 4),
            })
        else:
            _log("RISK", "Risk checks passed — no new positions to open", payload={
                "status": "APPROVED",
                "approved_positions": [],
                "reason": "No eligible long candidates survived filters.",
            })
        
        logger.debug(f"[Cycle {cycle.id}] Enqueuing portfolio target for execution.")
        _log("EXECUTION", "Enqueuing approved portfolio to asynchronous OrderExecutorQueue")
        
        from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
        
        queue = OrderExecutorQueue.get_instance()
        queue.enqueue(
            account_name=account_name,
            target=approved_portfolio,
            cycle_id=cycle.id
        )
        
        # The synchronous execution logic and cycle completion is now handled by OrderExecutorQueue!
        
        # We can just return the decisions
        return decisions

    @staticmethod
    def _get_timedelta(timeframe: Timeframe) -> timedelta:
        if timeframe == Timeframe.ONE_MINUTE:
            return timedelta(minutes=1)
        if timeframe == Timeframe.FIFTEEN_MINUTES:
            return timedelta(minutes=15)
        if timeframe == Timeframe.ONE_HOUR:
            return timedelta(hours=1)
        if timeframe == Timeframe.FOUR_HOURS:
            return timedelta(hours=4)
        if timeframe == Timeframe.ONE_DAY:
            return timedelta(days=1)
        if timeframe == Timeframe.ONE_WEEK:
            return timedelta(days=7)
        if timeframe == Timeframe.ONE_MONTH:
            return timedelta(days=30)
        return timedelta(hours=1)
