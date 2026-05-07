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

    binance_api_key: str = ""
    binance_api_secret: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
