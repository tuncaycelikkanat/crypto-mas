from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class DomainPosition:
    """
    Pure business domain entity representing an active or theoretical position.
    Independent of persistence / ORM framework.
    """
    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: Decimal
    quantity: Decimal
    current_price: Decimal
    target_weight: float
    opened_at: datetime
    stop_loss_price: Decimal | None = None
    take_profit_price: Decimal | None = None

    @property
    def notional_value(self) -> Decimal:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> Decimal:
        if self.side == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        else:
            return (self.entry_price - self.current_price) * self.quantity

    @property
    def return_pct(self) -> float:
        if self.entry_price == 0:
            return 0.0
        if self.side == "LONG":
            return float((self.current_price - self.entry_price) / self.entry_price) * 100.0
        else:
            return float((self.entry_price - self.current_price) / self.entry_price) * 100.0


@dataclass
class PortfolioState:
    """
    Domain aggregate root representing the current state of a portfolio.
    """
    account_name: str
    total_equity: Decimal
    cash_balance: Decimal
    positions: dict[str, DomainPosition] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def gross_exposure(self) -> float:
        if self.total_equity <= 0:
            return 0.0
        total_pos_val = sum(pos.notional_value for pos in self.positions.values())
        return float(total_pos_val / self.total_equity)

    @property
    def cash_weight(self) -> float:
        if self.total_equity <= 0:
            return 0.0
        return float(self.cash_balance / self.total_equity)

    @property
    def open_position_count(self) -> int:
        return len(self.positions)

    def can_open_position(self, max_positions: int, max_gross_exposure: float, proposed_weight: float) -> bool:
        if self.open_position_count >= max_positions:
            return False
        if self.gross_exposure + proposed_weight > max_gross_exposure + 1e-6:
            return False
        return True
