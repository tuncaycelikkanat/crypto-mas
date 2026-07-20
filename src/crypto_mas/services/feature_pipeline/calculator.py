import logging
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

from crypto_mas.domain.models.candle import Candle

logger = logging.getLogger(__name__)


class FeatureCalculator:
    def calculate(self, candles: list[Candle]) -> list[dict[str, Any]]:
        if len(candles) < 60:
            return []

        # Convert candles to DataFrame
        df = pd.DataFrame([
            {
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": float(c.volume),
                "timestamp": c.open_time,
                "available_at": c.close_time,
                "exchange": c.exchange,
                "symbol": c.symbol,
                "timeframe": c.timeframe,
            }
            for c in candles
        ])

        # We need a clean sequential index for pandas-ta
        df.reset_index(drop=True, inplace=True)

        # ── Calculate Technical Indicators (Vectorized) ─────────────────────────
        # Price-based
        df.ta.sma(length=20, append=True)
        df.ta.ema(length=20, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2.0, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.roc(length=14, append=True)
        df.ta.adx(length=14, append=True)
        df.ta.stochrsi(length=14, rsi_length=14, k=3, d=3, append=True)

        # Volume-based
        df.ta.sma(close=df["volume"], length=20, append=True, prefix="VOL")
        df.ta.obv(append=True)
        df.ta.cmf(length=20, append=True)

        # Calculate RVOL: volume / VOL_SMA_20
        df["rvol"] = df["volume"] / df["VOL_SMA_20"]

        # Replace infinite values with NaN so they are safely parsed to None
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        snapshots: list[dict[str, Any]] = []

        # Convert back to standard list of dicts
        for row in df.itertuples(index=False):
            def _safe_float(val: Any) -> float | None:
                if pd.isna(val):
                    return None
                return float(Decimal(str(round(val, 8))))

            features = {
                # Price
                "open": _safe_float(row.open),
                "high": _safe_float(row.high),
                "low": _safe_float(row.low),
                "close": _safe_float(row.close),
                
                # Volume
                "volume": _safe_float(row.volume),
                "volume_sma_20": _safe_float(getattr(row, "VOL_SMA_20", None)),
                "rvol": _safe_float(getattr(row, "rvol", None)),
                "obv": _safe_float(getattr(row, "OBV", getattr(row, "OBV_in_1", None))),
                "cmf_20": _safe_float(getattr(row, "CMF_20", None)),
                
                # Trend
                "ema_20": _safe_float(getattr(row, "EMA_20", None)),
                "ema_50": _safe_float(getattr(row, "EMA_50", None)),
                "sma_20": _safe_float(getattr(row, "SMA_20", None)),
                "adx_14": _safe_float(getattr(row, "ADX_14", None)),
                "plus_di": _safe_float(getattr(row, "DMP_14", None)),
                "minus_di": _safe_float(getattr(row, "DMN_14", None)),
                
                # Momentum
                "rsi_14": _safe_float(getattr(row, "RSI_14", None)),
                "stoch_rsi_k": _safe_float(getattr(row, "STOCHRSIk_14_14_3_3", getattr(row, "STOCHk_14_3_3", None))),
                "stoch_rsi_d": _safe_float(getattr(row, "STOCHRSId_14_14_3_3", getattr(row, "STOCHd_14_3_3", None))),
                "roc_14": _safe_float(getattr(row, "ROC_14", None)),
                "macd": _safe_float(getattr(row, "MACD_12_26_9", None)),
                "macd_signal": _safe_float(getattr(row, "MACDs_12_26_9", None)),
                "macd_hist": _safe_float(getattr(row, "MACDh_12_26_9", None)),
                
                # Volatility
                "atr_14": _safe_float(getattr(row, "ATRr_14", None)),
                "bb_upper": _safe_float(getattr(row, "BBU_20_2.0_2.0", None)),
                "bb_middle": _safe_float(getattr(row, "BBM_20_2.0_2.0", None)),
                "bb_lower": _safe_float(getattr(row, "BBL_20_2.0_2.0", None)),
            }

            snapshots.append(
                {
                    "exchange": row.exchange,
                    "symbol": row.symbol,
                    "timeframe": row.timeframe,
                    "timestamp": row.timestamp,
                    "available_at": row.available_at,
                    "features_json": features,
                }
            )

        return snapshots
