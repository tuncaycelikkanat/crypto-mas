from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from crypto_mas.agents.portfolio_manager_agent.schemas import PortfolioTarget
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange
from crypto_mas.services.paper_trading.schemas import (
    PaperExecutionItem,
    PaperExecutionReport,
    PaperExecutionStatus,
    PaperOrderSide,
)


class PaperBrokerService:
    def __init__(
        self,
        db: Session,
        time_provider: TimeProvider | None = None,
    ) -> None:
        self.account_repository = PaperAccountRepository(db)
        self.position_repository = PositionRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)
        self.time_provider = time_provider or SystemTimeProvider()

    def execute_target_portfolio(
        self,
        account_name: str,
        target: PortfolioTarget,
    ) -> PaperExecutionReport:
        account = self.account_repository.get_by_name(account_name)

        if account is None:
            raise ValueError(f"Paper account not found: {account_name}")

        starting_cash = account.cash_balance
        starting_equity = account.equity
        available_cash = account.cash_balance

        executed: list[PaperExecutionItem] = []
        skipped: list[PaperExecutionItem] = []

        for target_position in target.target_positions:
            existing_position = self.position_repository.get_open_position(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=target_position.symbol,
            )

            if existing_position is not None:
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=PaperOrderSide.BUY,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=0.0,
                        price=float(existing_position.current_price),
                        quantity=float(existing_position.quantity),
                        reason="Open position already exists.",
                    )
                )
                continue

            latest_snapshot = self.feature_snapshot_repository.get_latest(
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                timeframe=target.timeframe.value,
            )

            price = self._extract_close_price(latest_snapshot)

            if price is None or price <= Decimal("0"):
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=PaperOrderSide.BUY,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=0.0,
                        price=None,
                        quantity=None,
                        reason="Latest close price not available.",
                    )
                )
                continue

            target_notional = Decimal(str(target_position.target_weight)) * starting_equity

            if target_notional <= Decimal("0"):
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=PaperOrderSide.BUY,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=float(target_notional),
                        price=float(price),
                        quantity=None,
                        reason="Target notional is zero.",
                    )
                )
                continue

            if target_notional > available_cash:
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=PaperOrderSide.BUY,
                        status=PaperExecutionStatus.REJECTED,
                        target_weight=target_position.target_weight,
                        notional=float(target_notional),
                        price=float(price),
                        quantity=None,
                        reason="Insufficient paper cash balance.",
                    )
                )
                continue

            quantity = (target_notional / price).quantize(Decimal("0.00000001"))

            self.position_repository.create_open_position(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                quantity=quantity,
                entry_price=price,
                notional_value=target_notional,
                opened_at=self.time_provider.now(),
            )

            available_cash = (available_cash - target_notional).quantize(Decimal("0.00000001"))

            executed.append(
                PaperExecutionItem(
                    symbol=target_position.symbol,
                    side=PaperOrderSide.BUY,
                    status=PaperExecutionStatus.EXECUTED,
                    target_weight=target_position.target_weight,
                    notional=float(target_notional),
                    price=float(price),
                    quantity=float(quantity),
                    reason="Paper BUY executed at latest close price.",
                )
            )

        ending_equity = (
            available_cash + self._calculate_open_positions_value(account.name)
        ).quantize(Decimal("0.00000001"))

        updated_account = self.account_repository.update_balances(
            account=account,
            cash_balance=available_cash,
            equity=ending_equity,
        )

        return PaperExecutionReport(
            account_name=account.name,
            exchange=Exchange(target.exchange.value),
            starting_cash=float(starting_cash),
            ending_cash=float(updated_account.cash_balance),
            starting_equity=float(starting_equity),
            ending_equity=float(updated_account.equity),
            executed=executed,
            skipped=skipped,
            created_at=self.time_provider.now(),
        )

    def _calculate_open_positions_value(self, account_name: str) -> Decimal:
        positions = self.position_repository.list_open_positions(account_name=account_name)

        return sum(
            (position.quantity * position.current_price for position in positions),
            Decimal("0"),
        )

    @staticmethod
    def _extract_close_price(snapshot: FeatureSnapshot | None) -> Decimal | None:
        if snapshot is None:
            return None

        features: dict[str, Any] = snapshot.features_json
        value = features.get("close")

        if value is None:
            return None

        try:
            return Decimal(str(value))
        except Exception:
            return None
