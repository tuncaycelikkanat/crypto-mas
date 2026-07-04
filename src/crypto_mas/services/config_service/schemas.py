from pydantic import BaseModel, Field


class TradingConfig(BaseModel):
    max_positions: int = Field(default=3, ge=1)
    max_gross_exposure: float = Field(default=0.90, ge=0.0, le=1.0)
    max_position_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    min_cash_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    min_confidence: float = Field(default=0.35, ge=0.0, le=1.0)
    
    quote_asset: str = Field(default="USDT")
    symbol_limit: int = Field(default=10, ge=1)
    snapshot_limit: int = Field(default=200, ge=1)
    
    symbols: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
