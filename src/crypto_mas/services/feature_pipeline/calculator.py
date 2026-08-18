import logging
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

        # ── Calculate Non-Parametric / Statistical Features ───────────────────
        # Distance to EMA20
        if "EMA_20" in df.columns:
            df["ema_20_dist"] = (df["close"] - df["EMA_20"]) / df["EMA_20"]
            roll_mean = df["ema_20_dist"].rolling(50, min_periods=20).mean()
            roll_std = df["ema_20_dist"].rolling(50, min_periods=20).std()
            df["ema_dist_zscore_50"] = (df["ema_20_dist"] - roll_mean) / (roll_std + 1e-9)
        else:
            df["ema_dist_zscore_50"] = 0.0

        if "RSI_14" in df.columns:
            rsi_mean = df["RSI_14"].rolling(50, min_periods=20).mean()
            rsi_std = df["RSI_14"].rolling(50, min_periods=20).std()
            df["rsi_zscore_50"] = (df["RSI_14"] - rsi_mean) / (rsi_std + 1e-9)
        else:
            df["rsi_zscore_50"] = 0.0

        # RVOL Percentile Rank (0.0 to 1.0)
        df["rvol_percentile_50"] = df["rvol"].rolling(50, min_periods=20).apply(
            lambda s: (s <= s.iloc[-1]).sum() / len(s) if len(s) > 0 else 0.5, raw=False
        )

        # Approximate CVD (Cumulative Volume Delta) via Price Action directional volume
        # Directional volume: +volume if close > open, -volume if close < open
        price_dir = np.where(df["close"] >= df["open"], 1.0, -1.0)
        df["cvd"] = (df["volume"] * price_dir).cumsum()

        # Replace infinite values and NaNs with None for JSON serialization
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].round(8)
        df = df.replace([np.inf, -np.inf, np.nan], None)

        feature_map = {
            "open": "open", "high": "high", "low": "low", "close": "close", 
            "volume": "volume", "VOL_SMA_20": "volume_sma_20", "rvol": "rvol",
            "OBV": "obv", "OBV_in_1": "obv", "CMF_20": "cmf_20", "EMA_20": "ema_20",
            "EMA_50": "ema_50", "SMA_20": "sma_20", "ADX_14": "adx_14", 
            "DMP_14": "plus_di", "DMN_14": "minus_di", "RSI_14": "rsi_14",
            "STOCHRSIk_14_14_3_3": "stoch_rsi_k", "STOCHk_14_3_3": "stoch_rsi_k",
            "STOCHRSId_14_14_3_3": "stoch_rsi_d", "STOCHd_14_3_3": "stoch_rsi_d",
            "ROC_14": "roc_14", "ROCP_14": "roc_14", "MACD_12_26_9": "macd",
            "MACDs_12_26_9": "macd_signal", "MACDh_12_26_9": "macd_hist",
            "ATRr_14": "atr_14", "BBU_20_2.0": "bb_upper", "BBU_20_2.0_2.0": "bb_upper",
            "BBM_20_2.0": "bb_middle", "BBM_20_2.0_2.0": "bb_middle",
            "BBL_20_2.0": "bb_lower", "BBL_20_2.0_2.0": "bb_lower",
            "rsi_zscore_50": "rsi_zscore_50", "ema_dist_zscore_50": "ema_dist_zscore_50",
            "rvol_percentile_50": "rvol_percentile_50", "cvd": "cvd",
        }

        expected_keys = [
            "open", "high", "low", "close", "volume", "volume_sma_20", "rvol", "obv", 
            "cmf_20", "ema_20", "ema_50", "sma_20", "adx_14", "plus_di", "minus_di", 
            "rsi_14", "stoch_rsi_k", "stoch_rsi_d", "roc_14", "macd", "macd_signal", 
            "macd_hist", "atr_14", "bb_upper", "bb_middle", "bb_lower",
            "rsi_zscore_50", "ema_dist_zscore_50", "rvol_percentile_50", "cvd"
        ]

        snapshots: list[dict[str, Any]] = []
        records = df.to_dict(orient="records")

        for row in records:
            features = {}
            for col, feat_name in feature_map.items():
                if col in row and row[col] is not None:
                    if feat_name not in features:
                        features[feat_name] = row[col]
            
            # Fill missing keys with None
            for key in expected_keys:
                if key not in features:
                    features[key] = None

            snapshots.append({
                "exchange": row.get("exchange"),
                "symbol": row.get("symbol"),
                "timeframe": row.get("timeframe"),
                "timestamp": row.get("timestamp"),
                "available_at": row.get("available_at"),
                "features_json": features,
            })

        return snapshots
