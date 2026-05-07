from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from crypto_mas.domain.models.candle import Candle
from crypto_mas.services.market_data_service.schemas import OHLCVCandle


class CandleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_upsert(self, candles: Sequence[OHLCVCandle]) -> int:
        if not candles:
            return 0

        rows = [
            {
                "exchange": candle.exchange.value,
                "symbol": candle.symbol,
                "timeframe": candle.timeframe.value,
                "open_time": candle.open_time,
                "close_time": candle.close_time,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
                "quote_volume": candle.quote_volume,
                "trade_count": candle.trade_count,
                "source": candle.source,
            }
            for candle in candles
        ]

        stmt = insert(Candle).values(rows)

        stmt = stmt.on_conflict_do_update(
            constraint="uq_candles_exchange_symbol_tf_open",
            set_={
                "close_time": stmt.excluded.close_time,
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "quote_volume": stmt.excluded.quote_volume,
                "trade_count": stmt.excluded.trade_count,
                "source": stmt.excluded.source,
            },
        )

        self.db.execute(stmt)
        self.db.commit()

        return len(rows)

    def list_by_symbol(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[Candle]:
        stmt = (
            select(Candle)
            .where(Candle.exchange == exchange)
            .where(Candle.symbol == symbol)
            .where(Candle.timeframe == timeframe)
            .order_by(Candle.open_time.asc())
        )

        if start_time is not None:
            stmt = stmt.where(Candle.open_time >= start_time)

        if end_time is not None:
            stmt = stmt.where(Candle.open_time <= end_time)

        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.db.scalars(stmt).all())
