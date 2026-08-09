import asyncio
import logging
from datetime import UTC, datetime, timedelta

from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("backtest_fetcher")

class HistoryFetcher:
    def __init__(self, exchange: Exchange):
        self.exchange = exchange
        self.provider = get_market_data_provider(exchange)
        self.db = SessionLocal()
        self.repo = CandleRepository(self.db)

    async def fetch_and_store(self, symbol: str, timeframe: Timeframe, start_date: datetime, end_date: datetime):
        """
        Fetches historical data chunk by chunk and saves to DB.
        """
        logger.info("Starting fetch for %s on %s from %s to %s", symbol, timeframe.value, start_date.date(), end_date.date())
        
        current_start = start_date
        total_fetched = 0
        
        while current_start < end_date:
            try:
                # We request up to 1000 candles
                candles = await self.provider.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_time=current_start,
                    limit=1000
                )
                
                if not candles:
                    logger.warning("No candles returned for %s after %s. Stopping.", symbol, current_start)
                    break
                
                # Filter out candles beyond end_date just in case
                valid_candles = [c for c in candles if c.open_time <= end_date]
                if not valid_candles:
                    break
                
                # We don't need to convert to DB model because bulk_upsert takes OHLCVCandle schemas!
                self.repo.bulk_upsert(valid_candles)
                total_fetched += len(valid_candles)
                
                logger.info("Fetched and saved %s candles. Total: %s. Reached: %s", len(valid_candles), total_fetched, valid_candles[-1].open_time)
                
                # Advance current_start for the next loop
                current_start = valid_candles[-1].open_time + timedelta(seconds=1)
                
                await asyncio.sleep(0.5) # Rate limit protection
                
            except Exception as e:
                logger.error("Error fetching data: %s", e)
                await asyncio.sleep(5)
                
        logger.info("Finished fetching %s. Total saved: %s", symbol, total_fetched)
        
    def close(self):
        self.db.close()

async def run_fetcher(symbol: str, timeframe_str: str, days_back: int):
    tf_map = {
        "15m": Timeframe.FIFTEEN_MINUTES,
        "4h":  Timeframe.FOUR_HOURS,
        "1d":  Timeframe.ONE_DAY,
    }
    tf = tf_map.get(timeframe_str, Timeframe.FIFTEEN_MINUTES)
    
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days_back)
    
    fetcher = HistoryFetcher(Exchange.BINANCE)
    try:
        await fetcher.fetch_and_store(symbol, tf, start_date, end_date)
    finally:
        fetcher.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch historical data for backtesting")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Symbol to fetch (e.g. BTCUSDT)")
    parser.add_argument("--timeframe", type=str, default="15m", help="Timeframe (15m, 4h, 1d)")
    parser.add_argument("--days", type=int, default=30, help="Days back to fetch")
    
    args = parser.parse_args()
    
    asyncio.run(run_fetcher(args.symbol, args.timeframe, args.days))
