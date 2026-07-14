from datetime import UTC, datetime, timedelta
from decimal import Decimal

from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import (
    Exchange,
    MarketSymbol,
    OHLCVCandle,
    Timeframe,
)


class MockMarketDataProvider(MarketDataProvider):
    @property
    def exchange(self) -> Exchange:
        return Exchange.MOCK

    async def fetch_symbols(self) -> list[MarketSymbol]:
        return [
            MarketSymbol(
                exchange=Exchange.MOCK,
                symbol="BTCUSDT",
                base_asset="BTC",
                quote_asset="USDT",
                status="TRADING",
                is_active=True,
            ),
            MarketSymbol(
                exchange=Exchange.MOCK,
                symbol="ETHUSDT",
                base_asset="ETH",
                quote_asset="USDT",
                status="TRADING",
                is_active=True,
            ),
            MarketSymbol(
                exchange=Exchange.MOCK,
                symbol="SOLUSDT",
                base_asset="SOL",
                quote_asset="USDT",
                status="TRADING",
                is_active=True,
            ),
        ]

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[OHLCVCandle]:
        end = self._align_to_timeframe(end_time or datetime.now(UTC), timeframe)
        candles: list[OHLCVCandle] = []

        step = self._timeframe_to_delta(timeframe)
        current = self._align_to_timeframe(start_time, timeframe)

        price = Decimal("100.00")

        while current < end and len(candles) < limit:
            close_time = current + step

            open_price = price
            close_price = price * Decimal("1.001")
            high_price = close_price * Decimal("1.002")
            low_price = open_price * Decimal("0.998")

            candles.append(
                OHLCVCandle(
                    exchange=Exchange.MOCK,
                    symbol=symbol,
                    timeframe=timeframe,
                    open_time=current,
                    close_time=close_time,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=Decimal("1000"),
                    quote_volume=Decimal("100000"),
                    trade_count=100,
                    source="MOCK",
                )
            )

            price = close_price
            current = close_time

        return candles

    @staticmethod
    def _timeframe_to_delta(timeframe: Timeframe) -> timedelta:
        match timeframe:
            case Timeframe.ONE_MINUTE:
                return timedelta(minutes=1)
            case Timeframe.FIVE_MINUTES:
                return timedelta(minutes=5)
            case Timeframe.FIFTEEN_MINUTES:
                return timedelta(minutes=15)
            case Timeframe.ONE_HOUR:
                return timedelta(hours=1)
            case Timeframe.FOUR_HOURS:
                return timedelta(hours=4)
            case Timeframe.ONE_DAY:
                return timedelta(days=1)
            case Timeframe.ONE_WEEK:
                return timedelta(days=7)
            case Timeframe.ONE_MONTH:
                return timedelta(days=30)

    @staticmethod
    def _align_to_timeframe(value: datetime, timeframe: Timeframe) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)

        value = value.astimezone(UTC)
        value = value.replace(second=0, microsecond=0)

        match timeframe:
            case Timeframe.ONE_MINUTE:
                return value

            case Timeframe.FIVE_MINUTES:
                minute = (value.minute // 5) * 5
                return value.replace(minute=minute)

            case Timeframe.FIFTEEN_MINUTES:
                minute = (value.minute // 15) * 15
                return value.replace(minute=minute)

            case Timeframe.ONE_HOUR:
                return value.replace(minute=0)

            case Timeframe.FOUR_HOURS:
                hour = (value.hour // 4) * 4
                return value.replace(hour=hour, minute=0)

            case Timeframe.ONE_DAY:
                return value.replace(hour=0, minute=0)
            case Timeframe.ONE_WEEK:
                days_since_monday = value.weekday()
                return (value - timedelta(days=days_since_monday)).replace(hour=0, minute=0)
            case Timeframe.ONE_MONTH:
                return value.replace(day=1, hour=0, minute=0)
