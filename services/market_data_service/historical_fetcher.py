from datetime import datetime

from sqlalchemy.orm import Session

from domain.repositories.candle_repository import CandleRepository
from services.market_data_service.integrity import CandleIntegrityChecker
from services.market_data_service.interfaces import MarketDataProvider
from services.market_data_service.schemas import HistoricalFetchResult, Timeframe


class HistoricalFetcherService:
    def __init__(
        self,
        provider: MarketDataProvider,
        db: Session,
    ) -> None:
        self.provider = provider
        self.candle_repository = CandleRepository(db)
        self.integrity_checker = CandleIntegrityChecker()

    async def fetch_and_store(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> HistoricalFetchResult:
        candles = await self.provider.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        integrity_report = self.integrity_checker.validate(
            candles=candles,
            timeframe=timeframe,
        )

        if not integrity_report.is_valid:
            raise ValueError(
                f"Candle integrity check failed: {integrity_report.model_dump(mode='json')}"
            )

        processed_rows = self.candle_repository.bulk_upsert(candles)

        return HistoricalFetchResult(
            exchange=self.provider.exchange,
            symbol=symbol,
            timeframe=timeframe,
            fetched=len(candles),
            processed_rows=processed_rows,
            start_time=start_time,
            end_time=end_time,
        )
