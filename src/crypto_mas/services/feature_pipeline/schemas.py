from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class FeatureSetSchema(BaseModel):
    """
    Type-safe schema for features_json stored in FeatureSnapshot models and used in strategy evaluation.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Basic OHLCV
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None

    # Volume & Moving Averages
    volume_sma_20: float | None = None
    rvol: float | None = None
    obv: float | None = None
    cmf_20: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    sma_20: float | None = None

    # Momentum & Trend
    adx_14: float | None = None
    plus_di: float | None = None
    minus_di: float | None = None
    rsi_14: float | None = None
    stoch_rsi_k: float | None = None
    stoch_rsi_d: float | None = None
    roc_14: float | None = None

    # MACD, ATR, Bollinger Bands
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    atr_14: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
