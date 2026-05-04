from collections.abc import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from domain.models.candle import Candle
from services.market_data_service.schemas import OHLCVCandle


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
