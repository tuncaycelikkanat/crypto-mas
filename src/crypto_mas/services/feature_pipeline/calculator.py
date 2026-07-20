import logging
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import pandas_ta as ta  # noqa: F401

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
        for row in df.to_dict(orient="records"):
            def _safe_float(val: Any) -> float | None:
                if pd.isna(val) or val is None:
                    return None
                return float(Decimal(str(round(val, 8))))

            features = {
                # Price
                "open": _safe_float(row.get("open")),
                "high": _safe_float(row.get("high")),
                "low": _safe_float(row.get("low")),
                "close": _safe_float(row.get("close")),
                
                # Volume
                "volume": _safe_float(row.get("volume")),
                "volume_sma_20": _safe_float(row.get("VOL_SMA_20")),
                "rvol": _safe_float(row.get("rvol")),
                "obv": _safe_float(row.get("OBV", row.get("OBV_in_1"))),
                "cmf_20": _safe_float(row.get("CMF_20")),
                
                # Trend
                "ema_20": _safe_float(row.get("EMA_20")),
                "ema_50": _safe_float(row.get("EMA_50")),
                "sma_20": _safe_float(row.get("SMA_20")),
                "adx_14": _safe_float(row.get("ADX_14")),
                "plus_di": _safe_float(row.get("DMP_14")),
                "minus_di": _safe_float(row.get("DMN_14")),
                
                # Momentum
                "rsi_14": _safe_float(row.get("RSI_14")),
                "stoch_rsi_k": _safe_float(row.get("STOCHRSIk_14_14_3_3", row.get("STOCHk_14_3_3"))),
                "stoch_rsi_d": _safe_float(row.get("STOCHRSId_14_14_3_3", row.get("STOCHd_14_3_3"))),
                "roc_14": _safe_float(row.get("ROC_14", row.get("ROCP_14"))),
                "macd": _safe_float(row.get("MACD_12_26_9")),
                "macd_signal": _safe_float(row.get("MACDs_12_26_9")),
                "macd_hist": _safe_float(row.get("MACDh_12_26_9")),
                
                # Volatility
                "atr_14": _safe_float(row.get("ATRr_14")),
                "bb_upper": _safe_float(row.get("BBU_20_2.0", row.get("BBU_20_2.0_2.0"))),
                "bb_middle": _safe_float(row.get("BBM_20_2.0", row.get("BBM_20_2.0_2.0"))),
                "bb_lower": _safe_float(row.get("BBL_20_2.0", row.get("BBL_20_2.0_2.0"))),
            }

            snapshots.append(
                {
                    "exchange": row.get("exchange"),
                    "symbol": row.get("symbol"),
                    "timeframe": row.get("timeframe"),
                    "timestamp": row.get("timestamp"),
                    "available_at": row.get("available_at"),
                    "features_json": features,
                }
            )

        return snapshots
