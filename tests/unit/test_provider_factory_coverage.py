from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange
from crypto_mas.brokers.binance_adapter.market_data import BinanceMarketDataProvider
from crypto_mas.brokers.mexc_adapter.market_data import MexcMarketDataProvider
from crypto_mas.brokers.mock_adapter.market_data import MockMarketDataProvider
import pytest

def test_get_market_data_provider():
    assert isinstance(get_market_data_provider(Exchange.BINANCE), BinanceMarketDataProvider)
    assert isinstance(get_market_data_provider(Exchange.MEXC), MexcMarketDataProvider)
    assert isinstance(get_market_data_provider(Exchange.MOCK), MockMarketDataProvider)
    
    with pytest.raises(ValueError):
        get_market_data_provider("invalid")
