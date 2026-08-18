import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from crypto_mas.brokers.base_market_data import (
    DEFAULT_MARKET_HEADERS,
    from_millis,
    is_leveraged_token,
    is_stablecoin,
    to_millis,
)
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import (
    Exchange,
    MarketSymbol,
    OHLCVCandle,
    Timeframe,
)


class MexcMarketDataProvider(MarketDataProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.mexc_base_url.rstrip("/")

    @property
    def exchange(self) -> Exchange:
        return Exchange.MEXC

    async def fetch_symbols(self) -> list[MarketSymbol]:
        url = f"{self.base_url}/api/v3/exchangeInfo"

        async with httpx.AsyncClient(headers=DEFAULT_MARKET_HEADERS, timeout=20.0) as client:
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
                    exchange=Exchange.MEXC,
                    symbol=symbol,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    status="TRADING" if status == "1" or status == "TRADING" else status,
                    is_active=status == "1" or status == "TRADING",
                    is_stablecoin=is_stablecoin(base_asset),
                    is_leveraged_token=is_leveraged_token(symbol),
                    listing_date=None,
                    delisting_date=None,
                )
            )

        return symbols

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

        # MEXC expects uppercase W and M for week and month, and 60m for 1h
        interval = timeframe.value
        if interval == "1w":
            interval = "1W"
        elif interval == "1h":
            interval = "60m"

        params: dict[str, str | int] = {
            "symbol": symbol,
            "interval": interval,
            "startTime": to_millis(start_time),
            "limit": limit,
        }

        if end_time is not None:
            params["endTime"] = to_millis(end_time)

        # Rate limit protection (MEXC can be strict)
        await asyncio.sleep(0.1)

        async with httpx.AsyncClient(headers=DEFAULT_MARKET_HEADERS, timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        candles: list[OHLCVCandle] = []

        for row in payload:
            candles.append(
                OHLCVCandle(
                    exchange=Exchange.MEXC,
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=from_millis(int(row[0])),
                    open=Decimal(str(row[1])),
                    high=Decimal(str(row[2])),
                    low=Decimal(str(row[3])),
                    close=Decimal(str(row[4])),
                    volume=Decimal(str(row[5])),
                    close_time=from_millis(int(row[6])),
                    quote_volume=Decimal(str(row[7])),
                    trade_count=int(row[8]) if len(row) > 8 else 0, # MEXC might not return trade_count in some cases
                    source="MEXC_REST",
                )
            )

        return candles
