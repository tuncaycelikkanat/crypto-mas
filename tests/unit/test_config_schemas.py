from crypto_mas.services.config_service.schemas import TradingConfig


def test_trading_config_defaults():
    config = TradingConfig()
    
    assert config.max_positions == 3
    assert config.max_gross_exposure == 0.90
    assert config.max_position_weight == 0.35
    assert config.min_cash_weight == 0.10
    assert config.min_confidence == 0.35
    assert config.quote_asset == "USDT"
    assert config.symbol_limit == 10
    assert config.snapshot_limit == 200
    assert config.symbols == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def test_trading_config_overrides():
    config = TradingConfig(
        max_positions=5,
        max_gross_exposure=0.8,
        max_position_weight=0.2,
        min_cash_weight=0.2,
        min_confidence=0.5,
        quote_asset="BUSD",
        symbol_limit=20,
        snapshot_limit=100,
        symbols=["BTCUSDT"]
    )
    
    assert config.max_positions == 5
    assert config.max_gross_exposure == 0.8
    assert config.max_position_weight == 0.2
    assert config.min_cash_weight == 0.2
    assert config.min_confidence == 0.5
    assert config.quote_asset == "BUSD"
    assert config.symbol_limit == 20
    assert config.snapshot_limit == 100
    assert config.symbols == ["BTCUSDT"]
