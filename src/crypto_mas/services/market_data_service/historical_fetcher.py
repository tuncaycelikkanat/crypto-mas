import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.backfill_state_repository import BackfillStateRepository
from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.services.market_data_service.integrity import CandleIntegrityChecker
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import HistoricalFetchResult, Timeframe

logger = logging.getLogger(__name__)


class HistoricalFetcherService:
    def __init__(
        self,
        provider: MarketDataProvider,
        db: Session,
    ) -> None:
        self.provider = provider
        self.candle_repository = CandleRepository(db)
        self.state_repository = BackfillStateRepository(db)
        self.integrity_checker = CandleIntegrityChecker()

    async def fetch_and_store_range(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> HistoricalFetchResult:
        
        # Kaldığı yerden devam etme (Resume) mantığı
        latest_candles = self.candle_repository.list_by_symbol(
            exchange=self.provider.exchange.value,
            symbol=symbol,
            timeframe=timeframe.value,
            start_time=start_time,
            end_time=end_time,
            limit=1
        )
        
        if latest_candles:
            last_fetched = latest_candles[0].open_time
            if last_fetched.tzinfo is None:
                from datetime import UTC
                last_fetched = last_fetched.replace(tzinfo=UTC)
            
            logger.info(f"[{symbol}] Resuming backfill in range from {last_fetched}")
            current_start = last_fetched + timedelta(milliseconds=1)
        else:
            current_start = start_time

        total_fetched = 0
        total_processed = 0

        while current_start < end_time:
            logger.debug(f"[{symbol}] Fetching {limit} candles from {current_start}")
            
            try:
                candles = await self.provider.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=current_start,
                    end_time=end_time,
                    limit=limit,
                )
            except Exception as e:
                logger.error(f"[{symbol}] Failed to fetch candles: {e}")
                break

            if not candles:
                break

            integrity_report = self.integrity_checker.validate(
                candles=candles,
                timeframe=timeframe,
            )

            if not integrity_report.is_valid:
                logger.warning(f"[{symbol}] Integrity check failed: {integrity_report.model_dump(mode='json')}")
                break

            processed_rows = self.candle_repository.bulk_upsert(candles)
            
            total_fetched += len(candles)
            total_processed += processed_rows

            last_candle_time = candles[-1].open_time
            
            self.state_repository.upsert_state(
                exchange=self.provider.exchange.value,
                symbol=symbol,
                timeframe=timeframe.value,
                last_fetched_at=last_candle_time,
            )

            if len(candles) < limit:
                # Tüm veri çekildi
                break

            current_start = last_candle_time + timedelta(milliseconds=1)

        return HistoricalFetchResult(
            exchange=self.provider.exchange,
            symbol=symbol,
            timeframe=timeframe,
            fetched=total_fetched,
            processed_rows=total_processed,
            start_time=start_time,
            end_time=end_time,
        )

    async def backfill_universe(
        self,
        symbols: list[str],
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
        max_concurrent: int = 5,
        limit: int = 1000,
    ) -> list[HistoricalFetchResult]:
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def _fetch_with_semaphore(symbol: str) -> HistoricalFetchResult:
            async with semaphore:
                return await self.fetch_and_store_range(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                )

        tasks = [_fetch_with_semaphore(symbol) for symbol in symbols]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for res in completed:
            if isinstance(res, HistoricalFetchResult):
                results.append(res)
            elif isinstance(res, Exception):
                logger.error(f"Error during backfill: {res}")

        return results
