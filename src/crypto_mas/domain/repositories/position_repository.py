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

    def has_recent_stop_loss(
        self,
        account_name: str,
        exchange: str,
        symbol: str,
        time_now: datetime,
        cooldown_minutes: int = 30,
    ) -> bool:
        from datetime import timedelta
        cutoff_time = time_now - timedelta(minutes=cooldown_minutes)
        stmt = (
            select(Position)
            .where(Position.account_name == account_name)
            .where(Position.exchange == exchange)
            .where(Position.symbol == symbol)
            .where(Position.status == "CLOSED")
            .where(Position.close_reason == "STOP_LOSS")
            .where(Position.closed_at >= cutoff_time)
        )
        return self.db.scalars(stmt).first() is not None

    def get_open_position_symbols(self, account_name: str, exchange: str) -> set[str]:
        """Single query: returns the set of symbols with an open position. O(1) lookup after call."""
        stmt = (
            select(Position.symbol)
            .where(Position.account_name == account_name)
            .where(Position.exchange == exchange)
            .where(Position.status == "OPEN")
        )
        return set(self.db.scalars(stmt).all())

    def get_recent_stop_loss_symbols(
        self,
        account_name: str,
        exchange: str,
        time_now: datetime,
        cooldown_minutes: int = 30,
    ) -> set[str]:
        """Single query: returns the set of symbols under stop-loss cooldown."""
        from datetime import timedelta
        cutoff_time = time_now - timedelta(minutes=cooldown_minutes)
        stmt = (
            select(Position.symbol)
            .where(Position.account_name == account_name)
            .where(Position.exchange == exchange)
            .where(Position.status == "CLOSED")
            .where(Position.close_reason == "STOP_LOSS")
            .where(Position.closed_at >= cutoff_time)
        )
        return set(self.db.scalars(stmt).all())

    def get_recent_closed_symbols(
        self,
        account_name: str,
        exchange: str,
        time_now: datetime,
        cooldown_minutes: int = 60,
    ) -> set[str]:
        """Single query: returns the set of ALL symbols closed recently to enforce a global cooldown."""
        from datetime import timedelta
        cutoff_time = time_now - timedelta(minutes=cooldown_minutes)
        stmt = (
            select(Position.symbol)
            .where(Position.account_name == account_name)
            .where(Position.exchange == exchange)
            .where(Position.status == "CLOSED")
            .where(Position.closed_at >= cutoff_time)
        )
        return set(self.db.scalars(stmt).all())

    def get_whipsaw_cooldown_symbols(
        self,
        account_name: str,
        exchange: str,
        time_now: datetime,
        min_stop_count: int = 2,
        cooldown_minutes: int = 2880,
    ) -> set[str]:
        """Single query: returns symbols that hit >= min_stop_count stop-losses within cooldown_minutes."""
        from datetime import timedelta
        from sqlalchemy import func
        cutoff_time = time_now - timedelta(minutes=cooldown_minutes)
        stmt = (
            select(Position.symbol)
            .where(Position.account_name == account_name)
            .where(Position.exchange == exchange)
            .where(Position.status == "CLOSED")
            .where(Position.close_reason == "STOP_LOSS")
            .where(Position.closed_at >= cutoff_time)
            .group_by(Position.symbol)
            .having(func.count(Position.id) >= min_stop_count)
        )
        return set(self.db.scalars(stmt).all())

    def create_open_position(
        self,
        account_name: str,
        exchange: str,
        symbol: str,
        quantity: Decimal,
        entry_price: Decimal,
        notional_value: Decimal,
        opened_at: datetime,
        stop_loss_price: Decimal | None = None,
        take_profit_price: Decimal | None = None,
        strategy_mode: str | None = None,
        side: str = "LONG",
        skip_commit: bool = False,
    ) -> Position:
        position = Position(
            account_name=account_name,
            exchange=exchange,
            symbol=symbol,
            side=side,
            status="OPEN",
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            notional_value=notional_value,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            strategy_mode=strategy_mode,
            opened_at=opened_at,
            closed_at=None,
            close_reason=None,
        )

        self.db.add(position)
        if not skip_commit:
            self.db.commit()
            self.db.refresh(position)

        return position

    def update_mark_price(
        self,
        position: Position,
        current_price: Decimal,
        skip_commit: bool = False,
    ) -> Position:
        current_price = self._money(current_price)

        if position.side == "LONG":
            raw_unrealized_pnl = (current_price - position.entry_price) * position.quantity
        else:
            raw_unrealized_pnl = (position.entry_price - current_price) * position.quantity
        unrealized_pnl = self._zero_if_tiny(raw_unrealized_pnl)

        position.current_price = current_price
        position.unrealized_pnl = unrealized_pnl

        if unrealized_pnl == Decimal("0.00000000"):
            position.notional_value = self._money(position.notional_value)
        else:
            position.notional_value = self._money(position.quantity * current_price)

        if not skip_commit:
            self.db.commit()
            self.db.refresh(position)

        return position

    def update_stop_loss(
        self,
        position: Position,
        stop_loss_price: Decimal,
        skip_commit: bool = False,
    ) -> Position:
        position.stop_loss_price = self._money(stop_loss_price)
        if not skip_commit:
            self.db.commit()
            self.db.refresh(position)
        return position

    def close_position(
            self,
            position: Position,
            exit_price: Decimal,
            closed_at: datetime,
            close_reason: str = "SIGNAL",
            skip_commit: bool = False,
    ) -> Position:
        exit_price = self._money(exit_price)

        if position.side == "LONG":
            raw_realized_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            raw_realized_pnl = (position.entry_price - exit_price) * position.quantity
        realized_pnl = self._zero_if_tiny(raw_realized_pnl)

        position.current_price = exit_price
        position.realized_pnl = realized_pnl
        position.unrealized_pnl = Decimal("0.00000000")

        if realized_pnl == Decimal("0.00000000"):
            position.notional_value = self._money(position.notional_value)
        else:
            position.notional_value = self._money(position.quantity * exit_price)

        position.status = "CLOSED"
        position.closed_at = closed_at
        position.close_reason = close_reason

        if not skip_commit:
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
