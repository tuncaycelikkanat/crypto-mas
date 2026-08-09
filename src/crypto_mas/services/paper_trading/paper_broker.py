import logging
from sqlalchemy.orm import Session

from crypto_mas.engine.portfolio import PortfolioTarget
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange
from crypto_mas.services.paper_trading.schemas import PaperExecutionReport
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository

from crypto_mas.services.paper_trading.risk_calculator import RiskCalculator
from crypto_mas.services.paper_trading.execution_reporter import ExecutionReporter
from crypto_mas.services.paper_trading.mark_to_market import MarkToMarket
from crypto_mas.services.paper_trading.position_manager import PositionManager

logger = logging.getLogger(__name__)

class PaperBrokerService:
    def __init__(
        self,
        db: Session,
        time_provider: TimeProvider | None = None,
        strategy_mode: str = "swing",
        is_backtest: bool = False,
    ) -> None:
        self.db = db
        self.time_provider = time_provider or SystemTimeProvider()
        self.strategy_mode = strategy_mode
        self.is_backtest = is_backtest
        self.account_repository = PaperAccountRepository(db)
        
        self.risk_calculator = RiskCalculator(strategy_mode=strategy_mode)
        self.reporter = ExecutionReporter(db, self.time_provider, is_backtest=is_backtest)
        self.mark_to_market = MarkToMarket(db, self.risk_calculator, self.reporter, self.time_provider, is_backtest=is_backtest)
        self.position_manager = PositionManager(db, self.risk_calculator, self.reporter, self.mark_to_market, self.time_provider, is_backtest=is_backtest)

    def execute_target_portfolio(
        self,
        account_name: str,
        target: PortfolioTarget,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        account = getattr(self, "_bt_account", None) if self.is_backtest else self.account_repository.get_by_name(account_name)
        if account is None:
            raise ValueError(f"Paper account not found: {account_name}")
        return self.position_manager.execute_target_portfolio(account, target, cycle_id)

    def close_positions_not_in_target(
        self,
        account_name: str,
        target: PortfolioTarget,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        account = getattr(self, "_bt_account", None) if self.is_backtest else self.account_repository.get_by_name(account_name)
        if account is None:
            raise ValueError(f"Paper account not found: {account_name}")
        return self.position_manager.close_positions_not_in_target(account, target, cycle_id)

    def update_mark_prices(
        self,
        account_name: str,
        exchange: Exchange,
        timeframe: str,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        account = getattr(self, "_bt_account", None) if self.is_backtest else self.account_repository.get_by_name(account_name)
        if account is None:
            raise ValueError(f"Paper account not found: {account_name}")
        return self.mark_to_market.update_mark_prices(account, exchange, timeframe, cycle_id)
