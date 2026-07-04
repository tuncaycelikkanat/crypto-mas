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
    ) -> None:
        self.db = db
        self.time_provider = time_provider or SystemTimeProvider()
        
        self.cycle_repository = TradingCycleRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)
        
        self.fetcher_service = HistoricalFetcherService(provider=market_provider, db=db)
        self.feature_service = FeaturePipelineService(db)
        
        self.portfolio_engine = PortfolioEngine(time_provider=self.time_provider)
        self.risk_engine = RiskEngine()
        self.paper_broker = PaperBrokerService(db=db, time_provider=self.time_provider)

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
        
        try:
            # 2. Market Data Sync
            logger.info(f"[Cycle {cycle.id}] Starting market data sync for {len(symbols)} symbols.")
            
            # Fetch up to 60 periods back as a fallback if no state exists
            fallback_start = now - self._get_timedelta(timeframe) * 60
            
            await self.fetcher_service.backfill_universe(
                symbols=symbols,
                timeframe=timeframe,
                start_time=fallback_start,
                end_time=now,
            )
            
            # 3 & 4. Feature Engineering and Decisions
            decisions = []
            for symbol in symbols:
                logger.info(f"[Cycle {cycle.id}] Processing features and decisions for {symbol}")
                
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
                    continue
                
                # Decision
                decision = strategy.decide(
                    exchange=self.fetcher_service.provider.exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    snapshots=snapshots,
                )
                
                if decision:
                    decisions.append(decision)
                    
            cycle.symbols_processed = len(symbols)
            cycle.decisions_made = len(decisions)
            
            # 5. Portfolio Construction
            logger.info(f"[Cycle {cycle.id}] Constructing portfolio target from {len(decisions)} decisions.")
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
                raise ValueError("Risk engine rejected the portfolio entirely.")
            
            # 7. Execution
            logger.info(f"[Cycle {cycle.id}] Executing portfolio.")
            
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
            
            return cycle
            
        except Exception as e:
            logger.exception(f"[Cycle {cycle.id}] Failed with error: {e}")
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
