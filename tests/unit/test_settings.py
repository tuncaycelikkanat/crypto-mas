from crypto_mas.infrastructure.config.settings import get_settings


def test_settings_loads() -> None:
    settings = get_settings()

    assert settings.app_name == "crypto-mas"
    assert settings.app_version == "0.1.0"
    assert settings.trading_mode in {"BACKTEST", "PAPER", "LIVE"}
    assert settings.database_url
    assert settings.redis_url
