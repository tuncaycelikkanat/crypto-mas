from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_mas.domain.models.execution_log import ExecutionLog


class ExecutionLogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, log: ExecutionLog) -> ExecutionLog:
        self.session.add(log)
        self.session.flush()
        return log

    def list_by_cycle(self, cycle_id: int) -> Sequence[ExecutionLog]:
        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.cycle_id == cycle_id)
            .order_by(ExecutionLog.created_at.asc())
        )
        return self.session.scalars(stmt).all()

    def list_recent(self, account_name: str, limit: int = 100) -> Sequence[ExecutionLog]:
        stmt = (
            select(ExecutionLog)
            .where(ExecutionLog.account_name == account_name)
            .order_by(ExecutionLog.created_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt).all()
