from datetime import UTC, datetime, timedelta
from decimal import Decimal

from services.market_data_service.interfaces import MarketDataProvider
from services.market_data_service.schemas import Exchange, MarketSymbol, OHLCVCandle, Timeframe


class MockMarketDataProvider(MarketDataProvider):
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
        end = end_time or datetime.now(UTC)
        candles: list[OHLCVCandle] = []

        current = start_time
        price = Decimal("100.00")

        step = self._timeframe_to_delta(timeframe)

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
