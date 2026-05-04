from abc import ABC, abstractmethod
from datetime import datetime

from services.market_data_service.schemas import Exchange, MarketSymbol, OHLCVCandle, Timeframe


class MarketDataProvider(ABC):
    @property
    @abstractmethod
    def exchange(self) -> Exchange:
        """Exchange represented by this provider."""
        raise NotImplementedError

    @abstractmethod
    async def fetch_symbols(self) -> list[MarketSymbol]:
        """Fetch tradable market symbols from the exchange."""
        raise NotImplementedError

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[OHLCVCandle]:
        """Fetch OHLCV candles for a symbol and timeframe."""
        raise NotImplementedError
