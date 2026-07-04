from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from crypto_mas.domain.models.backtest_result import BacktestResult

class BacktestResultRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, result: BacktestResult) -> BacktestResult:
        self.session.add(result)
        self.session.flush()
        return result

    def get_by_job_id(self, job_id: str) -> BacktestResult | None:
        stmt = select(BacktestResult).where(BacktestResult.job_id == job_id)
        return self.session.scalars(stmt).first()

    def update_status(self, job_id: str, status: str) -> None:
        stmt = update(BacktestResult).where(BacktestResult.job_id == job_id).values(status=status)
        self.session.execute(stmt)
        self.session.flush()
        
    def list_all(self, limit: int = 100) -> Sequence[BacktestResult]:
        stmt = select(BacktestResult).order_by(BacktestResult.created_at.desc()).limit(limit)
        return self.session.scalars(stmt).all()
