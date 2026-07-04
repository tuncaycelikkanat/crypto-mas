from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from crypto_mas.domain.models.backfill_state import BackfillState


class BackfillStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_state(self, exchange: str, symbol: str, timeframe: str) -> BackfillState | None:
        stmt = (
            select(BackfillState)
            .where(BackfillState.exchange == exchange)
            .where(BackfillState.symbol == symbol)
            .where(BackfillState.timeframe == timeframe)
        )
        return self.session.scalars(stmt).first()

    def upsert_state(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        last_fetched_at: datetime,
    ) -> BackfillState:
        state = self.get_state(exchange, symbol, timeframe)
        if state:
            state.last_fetched_at = last_fetched_at
            self.session.commit()
            self.session.refresh(state)
            return state

        state = BackfillState(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            last_fetched_at=last_fetched_at,
        )
        self.session.add(state)
        self.session.commit()
        self.session.refresh(state)
        return state
