from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

TradingMode = Literal["BACKTEST", "PAPER", "LIVE"]


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "crypto-mas"
    app_version: str = "0.1.0"

    trading_mode: TradingMode = "PAPER"
    log_level: str = "INFO"

    database_url: str = ""
    redis_url: str = ""

    api_security_key: str = ""
    cors_origins: list[str] = ["*"]

    binance_api_key: str = ""
    binance_api_secret: str = ""

    binance_base_url: str = "https://data-api.binance.vision"
    binance_testnet_base_url: str = "https://testnet.binance.vision/api"
    
    mexc_base_url: str = "https://api.mexc.com"

    # Telegram Bot & Alerting Settings
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_enabled: bool = False

    # Scheduler Settings
    scheduled_symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    scheduled_timeframe: str = "1h"
    schedule_cron: str = "0 * * * *"  # Every hour at minute 0

    # Domain Constants & Strategy Groups (Externalized for flexibility)
    btc_correlated_symbols: set[str] = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT"}
    coin_groups: dict[str, set[str]] = {
        "TOP10": {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT"},
        "MEMES": {"DOGEUSDT", "SHIBUSDT", "FLOKIUSDT", "PEPEUSDT", "BONKUSDT", "WIFUSDT"},
        "L1": {"SOLUSDT", "ADAUSDT", "AVAXUSDT", "NEARUSDT", "FTMUSDT", "APTUSDT", "SUIUSDT", "INJUSDT"},
        "AI_HYPE": {"INJUSDT", "RNDRUSDT", "FETUSDT", "OCEANUSDT", "AGIXUSDT", "TAOUSDT"}
    }
    mode_config: dict[str, tuple[str, str, int]] = {
        "scalping": ("15m", "hft_momentum", 60),
        "swing":    ("4h",  "macd_cross",   120),
        "hodl":     ("1d",  "ema_golden_cross", 3600),
    }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
