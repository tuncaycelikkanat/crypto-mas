import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.trading_cycle_repository import TradingCycleRepository
from crypto_mas.engine.portfolio.portfolio import PortfolioEngine
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.engine.strategy.factory import StrategyFactory
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.engine.regime.htf_manager import HTFRegimeManager
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService

logger = logging.getLogger(__name__)


class TradingCycleService:
    def __init__(
        self,
        db: Session,
        market_provider: MarketDataProvider,
        time_provider: TimeProvider | None = None,
        strategy_mode: str = "swing",
    ) -> None:
        self.db = db
        self.time_provider = time_provider or SystemTimeProvider()
        self.strategy_mode = strategy_mode

        self.cycle_repository = TradingCycleRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)

        self.fetcher_service = HistoricalFetcherService(provider=market_provider, db=db)
        self.feature_service = FeaturePipelineService(db)

        self.portfolio_engine = PortfolioEngine(time_provider=self.time_provider)
        self.risk_engine = RiskEngine()
        self.paper_broker = PaperBrokerService(
            db=db,
            time_provider=self.time_provider,
            strategy_mode=strategy_mode,
        )
        self.htf_manager = HTFRegimeManager()

    async def run_cycle(
        self,
        account_name: str,
        symbols: list[str],
        timeframe: Timeframe,
        strategy_name: str = "multi_agent",
        trigger: str = "MANUAL",
    ) -> TradingCycle:
        now = self.time_provider.now()
        strategy = StrategyFactory.create(strategy_name, time_provider=self.time_provider)
        
        # 1. Initialize Cycle
        cycle = TradingCycle(
            account_name=account_name,
            exchange=self.fetcher_service.provider.exchange.value,
            timeframe=timeframe.value,
            status="RUNNING",
            trigger=trigger,
            started_at=now,
        )
        self.cycle_repository.add(cycle)
        self.db.commit()
        
        def _log(stage: str, message: str, level: str = "INFO"):
            from crypto_mas.domain.models.execution_log import ExecutionLog
            log = ExecutionLog(
                account_name=account_name,
                cycle_id=cycle.id,
                level=level,
                stage=stage,
                message=message,
                created_at=self.time_provider.now()
            )
            self.db.add(log)
            self.db.commit()

        _log("INIT", f"Cycle started for {len(symbols)} symbols: {symbols}")

        try:
            # 2. Market Data Sync
            logger.info(f"[Cycle {cycle.id}] Starting market data sync for {len(symbols)} symbols.")
            _log("MARKET_DATA", f"Fetching history from {self.fetcher_service.provider.exchange.value} for {timeframe}")
            
            # Ensure BTCUSDT is in the fetch list for market-wide correlation checks
            fetch_symbols = set(symbols)
            fetch_symbols.add("BTCUSDT")
            fetch_symbols_list = list(fetch_symbols)
            
            # Fetch up to 60 periods back as a fallback if no state exists
            fallback_start = now - self._get_timedelta(timeframe) * 60
            
            await self.fetcher_service.backfill_universe(
                symbols=fetch_symbols_list,
                timeframe=timeframe,
                start_time=fallback_start,
                end_time=now,
            )
            
            # Fetch HTF data if we are trading on a lower timeframe
            htf = Timeframe.FOUR_HOURS
            is_ltf = timeframe in (Timeframe.ONE_MINUTE, Timeframe.FIFTEEN_MINUTES, Timeframe.ONE_HOUR)
            
            if is_ltf:
                _log("MARKET_DATA", f"Fetching HTF ({htf.value}) history for Regime Filter")
                htf_start = now - self._get_timedelta(htf) * 60
                await self.fetcher_service.backfill_universe(
                    symbols=fetch_symbols_list,
                    timeframe=htf,
                    start_time=htf_start,
                    end_time=now,
                )
                
            # Pre-calculate BTC features for market-wide check
            self.feature_service.calculate_and_store(
                exchange=self.fetcher_service.provider.exchange,
                symbol="BTCUSDT",
                timeframe=timeframe,
            )
            btc_snapshots = self.feature_snapshot_repository.list_by_symbol(
                exchange=self.fetcher_service.provider.exchange.value,
                symbol="BTCUSDT",
                timeframe=timeframe.value,
                limit=5,
            )
            
            btc_is_crashing = False
            if btc_snapshots:
                latest_btc = btc_snapshots[-1].features_json
                btc_roc = latest_btc.get("roc_14")
                if btc_roc is not None and btc_roc < -2.0: # BTC dropped > 2% in the last 14 periods
                    btc_is_crashing = True
                    _log("RISK", f"MARKET CRASH DETECTED! BTC ROC: {btc_roc:.2f}%. Longs will be restricted.", "WARN")
            
            # 3 & 4. Feature Engineering and Decisions
            decisions = []
            for symbol in symbols:
                logger.info(f"[Cycle {cycle.id}] Processing features and decisions for {symbol}")
                _log("STRATEGY", f"Evaluating {strategy_name} for {symbol}")
                
                # Calculate features
                self.feature_service.calculate_and_store(
                    exchange=self.fetcher_service.provider.exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                )
                
                # Get latest snapshots
                snapshots = self.feature_snapshot_repository.list_by_symbol(
                    exchange=self.fetcher_service.provider.exchange.value,
                    symbol=symbol,
                    timeframe=timeframe.value,
                    limit=100,
                )
                
                if not snapshots:
                    logger.warning(f"[Cycle {cycle.id}] No feature snapshots for {symbol}. Skipping.")
                    _log("STRATEGY", f"No data available for {symbol}, skipped", "WARN")
                    continue
                
                # Check HTF Filter
                htf_long_allowed = True
                htf_short_allowed = True
                if is_ltf:
                    self.feature_service.calculate_and_store(
                        exchange=self.fetcher_service.provider.exchange,
                        symbol=symbol,
                        timeframe=htf,
                    )
                    htf_snapshots = self.feature_snapshot_repository.list_by_symbol(
                        exchange=self.fetcher_service.provider.exchange.value,
                        symbol=symbol,
                        timeframe=htf.value,
                        limit=5,
                    )
                    htf_long_allowed = self.htf_manager.is_long_allowed(htf_snapshots)
                    htf_short_allowed = self.htf_manager.is_short_allowed(htf_snapshots)
                
                # Decision
                decision = strategy.decide(
                    exchange=self.fetcher_service.provider.exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    snapshots=snapshots,
                )
                
                if decision:
                    # Apply HTF filter overrides
                    from crypto_mas.engine.strategy.schemas import DecisionAction
                    
                    if decision.action == DecisionAction.CONSIDER_LONG:
                        if btc_is_crashing and symbol != "BTCUSDT":
                            _log("STRATEGY", f"Decision CONSIDER_LONG for {symbol} REJECTED due to general BTC market crash.", "WARN")
                            decision.action = DecisionAction.HOLD
                            decision.reason += " | REJECTED by BTC Crash Filter"
                        elif not htf_long_allowed:
                            _log("STRATEGY", f"Decision CONSIDER_LONG for {symbol} REJECTED by HTF 4H Bear Trend filter.", "WARN")
                            decision.action = DecisionAction.HOLD
                            decision.reason += " | REJECTED by HTF Bear Trend"
                            
                    elif decision.action == DecisionAction.CONSIDER_SHORT and not htf_short_allowed:
                        _log("STRATEGY", f"Decision CONSIDER_SHORT for {symbol} REJECTED by HTF 4H Bull Trend filter.", "WARN")
                        decision.action = DecisionAction.HOLD
                        decision.reason += " | REJECTED by HTF Bull Trend"
                        
                    if decision.action != DecisionAction.HOLD:
                        decisions.append(decision)
                        _log("STRATEGY", f"Decision made for {symbol}: {decision.action.value} (Confidence: {decision.confidence})")
                    
            cycle.symbols_processed = len(symbols)
            cycle.decisions_made = len(decisions)
            
            # 5. Portfolio Construction
            logger.info(f"[Cycle {cycle.id}] Constructing portfolio target from {len(decisions)} decisions.")
            _log("PORTFOLIO", f"Constructing target portfolio from {len(decisions)} active signals")
            target_portfolio = self.portfolio_engine.build_target_portfolio(
                exchange=self.fetcher_service.provider.exchange,
                timeframe=timeframe,
                decisions=decisions,
            )
            
            # 6. Risk Management
            logger.info(f"[Cycle {cycle.id}] Evaluating risk limits.")
            risk_assessment = self.risk_engine.assess(target=target_portfolio)
            approved_portfolio = risk_assessment.approved_target
            
            if approved_portfolio is None:
                _log("RISK", f"Risk engine rejected portfolio: {risk_assessment.reason}. Holding current positions.", "WARN")
                # Build an empty target to hold all current positions (no new buys, no forced sells)
                from crypto_mas.engine.portfolio import PortfolioTarget
                approved_portfolio = PortfolioTarget(
                    exchange=target_portfolio.exchange,
                    timeframe=target_portfolio.timeframe,
                    target_positions=[],
                    cash_weight=1.0,
                    gross_exposure=0.0,
                    reason="Risk-rejected: holding cash.",
                    created_at=self.time_provider.now(),
                )
            
            _log("RISK", "Risk checks passed, proceeding to execution")
            
            # 7. Execution
            logger.info(f"[Cycle {cycle.id}] Executing portfolio.")
            _log("EXECUTION", "Executing orders against virtual broker")
            
            # Mark to Market
            self.paper_broker.update_mark_prices(
                account_name=account_name,
                exchange=self.fetcher_service.provider.exchange,
                timeframe=timeframe.value,
                cycle_id=cycle.id,
            )
            
            # Close positions not in target
            close_report = self.paper_broker.close_positions_not_in_target(
                account_name=account_name,
                target=approved_portfolio,
                cycle_id=cycle.id,
            )
            
            # Execute target
            execute_report = self.paper_broker.execute_target_portfolio(
                account_name=account_name,
                target=approved_portfolio,
                cycle_id=cycle.id,
            )
            
            cycle.trades_executed = len(close_report.executed) + len(execute_report.executed)
            cycle.starting_equity = close_report.starting_equity
            cycle.ending_equity = execute_report.ending_equity
            cycle.cycle_pnl = cycle.ending_equity - cycle.starting_equity
            
            # 8. Finalize
            self.cycle_repository.update_status(cycle.id, "COMPLETED")
            cycle.finished_at = self.time_provider.now()
            self.db.commit()
            
            logger.info(f"[Cycle {cycle.id}] Completed successfully. PnL: {cycle.cycle_pnl}")
            _log("COMPLETED", f"Cycle finished. {cycle.trades_executed} trades executed. PnL change: ${cycle.cycle_pnl:.2f}", "SUCCESS")
            
            return cycle
            
        except Exception as e:
            logger.exception(f"[Cycle {cycle.id}] Failed with error: {e}")
            _log("FAILED", f"Critical error in cycle: {str(e)}", "ERROR")
            self.cycle_repository.update_status(cycle.id, "FAILED")
            self.db.commit()
            raise e
            
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
        return timedelta(hours=1)
