from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_mas.domain.models.trade import Trade


class TradeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, trade: Trade) -> Trade:
        self.session.add(trade)
        self.session.flush()
        return trade

    def list_by_account(self, account_name: str, limit: int = 100) -> Sequence[Trade]:
        stmt = (
            select(Trade)
            .where(Trade.account_name == account_name)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()

    def list_by_cycle(self, cycle_id: int) -> Sequence[Trade]:
        stmt = (
            select(Trade)
            .where(Trade.cycle_id == cycle_id)
            .order_by(Trade.executed_at.asc())
        )
        return self.session.scalars(stmt).all()
