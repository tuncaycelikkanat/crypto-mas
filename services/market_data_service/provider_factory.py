from brokers.binance_adapter.market_data import BinanceMarketDataProvider
from brokers.mock_adapter.market_data import MockMarketDataProvider
from services.market_data_service.interfaces import MarketDataProvider
from services.market_data_service.schemas import Exchange


def get_market_data_provider(exchange: Exchange) -> MarketDataProvider:
    match exchange:
        case Exchange.BINANCE:
            return BinanceMarketDataProvider()
        case Exchange.MOCK:
            return MockMarketDataProvider()
        case _:
            raise ValueError(f"Unsupported exchange: {exchange}")
