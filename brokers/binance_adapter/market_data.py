from datetime import datetime
from decimal import Decimal

import httpx

from services.market_data_service.interfaces import MarketDataProvider
from services.market_data_service.schemas import Exchange, MarketSymbol, OHLCVCandle, Timeframe


class BinanceMarketDataProvider(MarketDataProvider):
    BASE_URL = "https://api.binance.com"

    async def fetch_symbols(self) -> list[MarketSymbol]:
        url = f"{self.BASE_URL}/api/v3/exchangeInfo"

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()

        symbols: list[MarketSymbol] = []

        for item in payload.get("symbols", []):
            quote_asset = item.get("quoteAsset", "")
            symbol = item.get("symbol", "")

            # İlk aşamada sadece USDT spot çiftlerini alıyoruz.
            if quote_asset != "USDT":
                continue

            permissions = item.get("permissions", [])
            is_spot = "SPOT" in permissions or item.get("isSpotTradingAllowed", False)

            if not is_spot:
                continue

            symbols.append(
                MarketSymbol(
                    exchange=Exchange.BINANCE,
                    symbol=symbol,
                    base_asset=item.get("baseAsset", ""),
                    quote_asset=quote_asset,
                    status=item.get("status", "UNKNOWN"),
                    is_active=item.get("status") == "TRADING",
                    is_stablecoin=self._is_stablecoin(item.get("baseAsset", "")),
                    is_leveraged_token=self._is_leveraged_token(symbol),
                )
            )

        return symbols

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[OHLCVCandle]:
        url = f"{self.BASE_URL}/api/v3/klines"

        params: dict[str, str | int] = {
            "symbol": symbol,
            "interval": timeframe.value,
            "startTime": self._to_millis(start_time),
            "limit": limit,
        }

        if end_time is not None:
            params["endTime"] = self._to_millis(end_time)

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
                    open_time=self._from_millis(row[0]),
                    open=Decimal(row[1]),
                    high=Decimal(row[2]),
                    low=Decimal(row[3]),
                    close=Decimal(row[4]),
                    volume=Decimal(row[5]),
                    close_time=self._from_millis(row[6]),
                    quote_volume=Decimal(row[7]),
                    trade_count=int(row[8]),
                    source="BINANCE_REST",
                )
            )

        return candles

    @staticmethod
    def _to_millis(value: datetime) -> int:
        return int(value.timestamp() * 1000)

    @staticmethod
    def _from_millis(value: int) -> datetime:
        return datetime.fromtimestamp(value / 1000)

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
        }
        return base_asset.upper() in stablecoins

    @staticmethod
    def _is_leveraged_token(symbol: str) -> bool:
        leveraged_suffixes = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")
        return symbol.upper().endswith(leveraged_suffixes)
