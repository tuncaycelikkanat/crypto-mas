from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_mas.domain.models.position import Position


class PositionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_open_positions(self, account_name: str) -> list[Position]:
        stmt = (
            select(Position)
            .where(Position.account_name == account_name)
            .where(Position.status == "OPEN")
            .order_by(Position.opened_at.asc())
        )

        return list(self.db.scalars(stmt).all())

    def get_open_position(
        self,
        account_name: str,
        exchange: str,
        symbol: str,
    ) -> Position | None:
        stmt = (
            select(Position)
            .where(Position.account_name == account_name)
            .where(Position.exchange == exchange)
            .where(Position.symbol == symbol)
            .where(Position.status == "OPEN")
        )

        return self.db.scalars(stmt).first()

    def create_open_position(
        self,
        account_name: str,
        exchange: str,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        notional_value: Decimal,
        opened_at: datetime,
    ) -> Position:
        position = Position(
            account_name=account_name,
            exchange=exchange,
            symbol=symbol,
            side="LONG",
            status="OPEN",
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            notional_value=notional_value,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            opened_at=opened_at,
            closed_at=None,
        )

        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)

        return position

    def update_mark_price(
            self,
            position: Position,
            current_price: Decimal,
    ) -> Position:
        current_price = self._money(current_price)

        raw_unrealized_pnl = (current_price - position.entry_price) * position.quantity
        unrealized_pnl = self._zero_if_tiny(raw_unrealized_pnl)

        position.current_price = current_price
        position.unrealized_pnl = unrealized_pnl

        if unrealized_pnl == Decimal("0.00000000"):
            position.notional_value = self._money(position.notional_value)
        else:
            position.notional_value = self._money(position.quantity * current_price)

        self.db.commit()
        self.db.refresh(position)

        return position

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.00000001"))

    @staticmethod
    def _zero_if_tiny(value: Decimal) -> Decimal:
        if abs(value) < Decimal("0.00000001"):
            return Decimal("0.00000000")

        return value.quantize(Decimal("0.00000001"))