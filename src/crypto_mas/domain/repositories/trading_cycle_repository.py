from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from crypto_mas.domain.models.trading_cycle import TradingCycle


class TradingCycleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, cycle: TradingCycle) -> TradingCycle:
        self.session.add(cycle)
        self.session.flush()
        return cycle

    def get_by_id(self, cycle_id: int) -> TradingCycle | None:
        return self.session.get(TradingCycle, cycle_id)

    def get_active_cycle(self, account_name: str) -> TradingCycle | None:
        stmt = (
            select(TradingCycle)
            .where(TradingCycle.account_name == account_name)
            .where(TradingCycle.status == "RUNNING")
            .order_by(TradingCycle.started_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_recent(self, account_name: str, limit: int = 10) -> Sequence[TradingCycle]:
        stmt = (
            select(TradingCycle)
            .where(TradingCycle.account_name == account_name)
            .order_by(TradingCycle.started_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()

    def update_status(self, cycle_id: int, status: str) -> None:
        stmt = (
            update(TradingCycle)
            .where(TradingCycle.id == cycle_id)
            .values(status=status)
        )
        self.session.execute(stmt)
        self.session.flush()
