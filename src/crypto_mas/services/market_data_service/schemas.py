from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class Exchange(StrEnum):
    BINANCE = "BINANCE"
    MEXC = "MEXC"
    BYBIT = "BYBIT"
    OKX = "OKX"
    COINBASE = "COINBASE"
    KRAKEN = "KRAKEN"
    MOCK = "MOCK"


class Timeframe(StrEnum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"


class MarketSymbol(BaseModel):
    exchange: Exchange
    symbol: str = Field(min_length=1, max_length=64)
    base_asset: str = Field(min_length=1, max_length=32)
    quote_asset: str = Field(min_length=1, max_length=32)
    status: str = Field(default="TRADING", max_length=32)

    is_active: bool = True
    is_stablecoin: bool = False
    is_leveraged_token: bool = False

    listing_date: datetime | None = None
    delisting_date: datetime | None = None


class OHLCVCandle(BaseModel):
    exchange: Exchange
    symbol: str = Field(min_length=1, max_length=64)
    timeframe: Timeframe

    open_time: datetime
    close_time: datetime

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: Decimal
    quote_volume: Decimal | None = None
    trade_count: int | None = None

    source: str = "REST"


class HistoricalFetchResult(BaseModel):
    exchange: Exchange
    symbol: str
    timeframe: Timeframe
    fetched: int
    processed_rows: int
    start_time: datetime
    end_time: datetime
