import logging
import time

from sqlalchemy.orm import Session

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.trading_cycle_repository import TradingCycleRepository
from crypto_mas.engine.portfolio.portfolio import PortfolioEngine
from crypto_mas.engine.risk.manager import RiskManager
from crypto_mas.engine.risk.models.btc_crash_model import BTCCrashModel
from crypto_mas.engine.risk.models.htf_portfolio_model import HTFPortfolioModel
from crypto_mas.engine.risk.models.regime_model import RegimeModel
from crypto_mas.engine.risk.profiles import get_risk_profile
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.engine.strategy.factory import StrategyFactory
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.services.gainers_service import fetch_gainers, fetch_hidden_gems
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
from crypto_mas.services.trading_cycle_service.market_data_orchestrator import (
    MarketDataOrchestrator,
)
from crypto_mas.services.trading_cycle_service.strategy_orchestrator import StrategyOrchestrator
from crypto_mas.infrastructure.db.async_compat import run_sync

logger = logging.getLogger(__name__)

DEFAULT_FALLBACK_SYMBOLS = ["BTCUSDT", "ETHUSDT"]


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
        executor_queue: OrderExecutorQueue | None = None,
    ) -> None:
        self.db = db
        self.time_provider = time_provider or SystemTimeProvider()
        self.strategy_mode = strategy_mode
        self.ws_client = ws_client
        self.executor_queue = executor_queue or OrderExecutorQueue.get_instance()

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
        
        # New orchestrators
        self.market_data_orchestrator = MarketDataOrchestrator(
            fetcher_service=self.fetcher_service,
            feature_service=self.feature_service,
            feature_snapshot_repository=self.feature_snapshot_repository,
        )
        
        self.strategy_orchestrator = StrategyOrchestrator(
            db=self.db,
            fetcher_service=self.fetcher_service,
            feature_service=self.feature_service,
            feature_snapshot_repository=self.feature_snapshot_repository,
            risk_manager=self.risk_manager,
            bt_position_repo=getattr(self, "_bt_position_repo", None),
        )

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
                    symbols = DEFAULT_FALLBACK_SYMBOLS
            except Exception as e:
                logger.error("Failed to fetch auto gainers: %s", e)
                if len(symbols) == 1:
                    symbols = DEFAULT_FALLBACK_SYMBOLS
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
                    symbols = DEFAULT_FALLBACK_SYMBOLS
            except Exception as e:
                logger.error("Failed to fetch hidden gems: %s", e)
                if len(symbols) == 1:
                    symbols = DEFAULT_FALLBACK_SYMBOLS
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
            await run_sync(self.db.commit)
            display_id = cycle.id
        else:
            display_id = cycle_index if cycle_index is not None else 0
            cycle.id = display_id


        def _log(stage: str, message: str, level: str = "INFO", payload: dict | None = None):
            if trigger.startswith("BACKTEST-"):
                if level in ("WARN", "WARNING"):
                    logger.warning("[%s] %s", stage, message)
                if level not in ("ERROR", "SUCCESS"):
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
                htf_map = {
                    Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
                    Timeframe.FIFTEEN_MINUTES: Timeframe.ONE_HOUR,
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
                btc_is_crashing, htf = await self.market_data_orchestrator.fetch_data_for_symbols(
                    symbols=symbols,
                    timeframe=timeframe,
                    now=now,
                    cycle=cycle,
                    _log=_log,
                    use_btc_shield=use_btc_shield,
                    display_id=display_id
                )
            
            time.time()
            decisions, open_positions = await self.strategy_orchestrator.run_strategies_and_score(
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
                cycle=cycle,
                account_name=account_name,
                _log=_log,
                open_positions=open_positions,
                strategy_id=strategy_id,
                risk_level=risk_level
            )
            time.time()
            
            if not trigger.startswith("BACKTEST-"):
                cycle.status = "COMPLETED"
                await run_sync(self.db.commit)
            cycle.trades_executed = len(decisions)

            
            return cycle
            
        except Exception as e:
            logger.exception("[Cycle %s] Failed with error: %s", display_id, e)
            _log("FAILED", f"Critical error in cycle {display_id}: {str(e)}", "ERROR")
            self.cycle_repository.update_status(cycle.id, "FAILED")
            if not trigger.startswith("BACKTEST-"):
                await run_sync(self.db.commit)
            raise e

    def _apply_risk_and_execute(self, decisions, timeframe, cycle, account_name, _log, open_positions: list[str], strategy_id: str | None = None, risk_level: int = 100):
        logger.debug("[Cycle %s] Constructing portfolio target from %s decisions.", cycle.id, len(decisions))
        _log("PORTFOLIO", f"Constructing target portfolio from {len(decisions)} active signals", payload={
            "total_signals": len(decisions),
            "candidate_symbols": [d.symbol for d in decisions],
            "actions": {d.symbol: d.action.value for d in decisions},
        })
        target_portfolio = self.portfolio_engine.build_target_portfolio(
            exchange=self.fetcher_service.provider.exchange,
            timeframe=timeframe,
            decisions=decisions,
            open_positions=open_positions,
            risk_level=risk_level
        )
        target_portfolio.strategy_id = strategy_id
        
        logger.debug("[Cycle %s] Evaluating risk limits.", cycle.id)
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
        
        logger.debug("[Cycle %s] Enqueuing portfolio target for execution.", cycle.id)
        _log("EXECUTION", "Enqueuing approved portfolio to asynchronous OrderExecutorQueue")
        
        self.executor_queue.enqueue(
            account_name=account_name,
            target=approved_portfolio,
            cycle_id=cycle.id
        )
        
        return decisions
