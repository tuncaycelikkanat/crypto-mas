import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from crypto_mas.infrastructure.api_client.circuit_breaker import resilient
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import (
    Exchange,
    MarketSymbol,
    OHLCVCandle,
    Timeframe,
)


class BinanceMarketDataProvider(MarketDataProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.binance_base_url.rstrip("/")

    @property
    def exchange(self) -> Exchange:
        return Exchange.BINANCE

    @resilient("binance_api", max_attempts=3)
    async def fetch_symbols(self) -> list[MarketSymbol]:
        url = f"{self.base_url}/api/v3/exchangeInfo"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        symbols: list[MarketSymbol] = []

        for item in payload.get("symbols", []):
            symbol = item.get("symbol", "")
            base_asset = item.get("baseAsset", "")
            quote_asset = item.get("quoteAsset", "")
            status = item.get("status", "UNKNOWN")

            # İlk aşamada yalnızca USDT spot çiftlerini alıyoruz.
            if quote_asset != "USDT":
                continue

            is_spot_allowed = bool(item.get("isSpotTradingAllowed", False))
            permissions = item.get("permissions", [])
            has_spot_permission = "SPOT" in permissions

            if not is_spot_allowed and not has_spot_permission:
                continue

            symbols.append(
                MarketSymbol(
                    exchange=Exchange.BINANCE,
                    symbol=symbol,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    status=status,
                    is_active=status == "TRADING",
                    is_stablecoin=self._is_stablecoin(base_asset),
                    is_leveraged_token=self._is_leveraged_token(symbol),
                    listing_date=None,
                    delisting_date=None,
                )
            )

        return symbols

    @resilient("binance_api", max_attempts=3)
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True,
    )
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[OHLCVCandle]:
        url = f"{self.base_url}/api/v3/klines"

        params: dict[str, str | int] = {
            "symbol": symbol,
            "interval": timeframe.value,
            "startTime": self._to_millis(start_time),
            "limit": limit,
        }

        if end_time is not None:
            params["endTime"] = self._to_millis(end_time)

        # Rate limit protection
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        candles: list[OHLCVCandle] = []

        for row in payload:
            candles.append(
                OHLCVCandle(
                    exchange=Exchange.BINANCE,
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=self._from_millis(int(row[0])),
                    open=Decimal(str(row[1])),
                    high=Decimal(str(row[2])),
                    low=Decimal(str(row[3])),
                    close=Decimal(str(row[4])),
                    volume=Decimal(str(row[5])),
                    close_time=self._from_millis(int(row[6])),
                    quote_volume=Decimal(str(row[7])),
                    trade_count=int(row[8]),
                    source="BINANCE_REST",
                )
            )

        return candles

    @staticmethod
    def _to_millis(value: datetime) -> int:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)

        value = value.astimezone(UTC)

        return int(value.timestamp() * 1000)

    @staticmethod
    def _from_millis(value: int) -> datetime:
        return datetime.fromtimestamp(value / 1000, tz=UTC)

    @staticmethod
    def _is_stablecoin(base_asset: str) -> bool:
        stablecoins = {
            "USDT",
            "USDC",
            "FDUSD",
            "TUSD",
            "DAI",
            "BUSD",
            "USDP",
            "EUR",
            "TRY",
        }

        return base_asset.upper() in stablecoins

    @staticmethod
    def _is_leveraged_token(symbol: str) -> bool:
        leveraged_suffixes = (
            "UPUSDT",
            "DOWNUSDT",
            "BULLUSDT",
            "BEARUSDT",
        )

        return symbol.upper().endswith(leveraged_suffixes)
