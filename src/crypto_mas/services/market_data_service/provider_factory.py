from crypto_mas.brokers.binance_adapter.market_data import BinanceMarketDataProvider
from crypto_mas.brokers.mexc_adapter.market_data import MexcMarketDataProvider
from crypto_mas.brokers.mock_adapter.market_data import MockMarketDataProvider
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import Exchange


def get_market_data_provider(exchange: Exchange) -> MarketDataProvider:
    match exchange:
        case Exchange.BINANCE:
            return BinanceMarketDataProvider()
        case Exchange.MEXC:
            return MexcMarketDataProvider()
        case Exchange.MOCK:
            return MockMarketDataProvider()
        case _:
            raise ValueError(f"Unsupported exchange: {exchange}")
