from dataclasses import dataclass
from datetime import datetime
import numpy as np


@dataclass(frozen=True)
class LiquidityMetricsSnapshot:
    symbol: str
    cvd: float                    # Cumulative Volume Delta (Net taker aggressive flow)
    cvd_slope_14: float           # 14-period slope of CVD (leading momentum)
    volume_imbalance_ratio: float # (BuyVol - SellVol) / TotalVol (-1.0 to 1.0)
    is_squeeze_risk: bool         # High open interest / divergence squeeze alert
    squeeze_type: str             # 'SHORT_SQUEEZE' | 'LONG_LIQUIDATION' | 'NONE'
    funding_proxy_bias: float     # Estimated funding pressure (-1.0 to 1.0)
    timestamp: datetime


class LiquidityMetricsCalculator:
    """
    Computes Order Flow, Cumulative Volume Delta (CVD), and Liquidity Squeeze
    metrics to provide leading edge signals before lagging price indicators react.
    """

    @staticmethod
    def calculate(
        symbol: str,
        closes: list[float],
        opens: list[float],
        volumes: list[float],
        timestamp: datetime,
    ) -> LiquidityMetricsSnapshot:
        n = len(closes)
        if n < 14:
            return LiquidityMetricsSnapshot(
                symbol=symbol,
                cvd=0.0,
                cvd_slope_14=0.0,
                volume_imbalance_ratio=0.0,
                is_squeeze_risk=False,
                squeeze_type="NONE",
                funding_proxy_bias=0.0,
                timestamp=timestamp,
            )

        c_arr = np.asarray(closes, dtype=np.float64)
        o_arr = np.asarray(opens, dtype=np.float64)
        v_arr = np.asarray(volumes, dtype=np.float64)

        # Approximate delta volume: (+volume when close >= open, -volume otherwise)
        # Weighted by candle body vs full range
        dir_sign = np.where(c_arr >= o_arr, 1.0, -1.0)
        delta_v = v_arr * dir_sign
        cvd_series = np.cumsum(delta_v)
        current_cvd = float(cvd_series[-1])

        # 14-period CVD linear slope (trend of aggressive buying/selling)
        x = np.arange(14)
        y = cvd_series[-14:]
        if np.std(y) > 1e-9:
            slope = float(np.polyfit(x, y, 1)[0])
        else:
            slope = 0.0

        # Recent 14-bar volume imbalance ratio
        recent_delta = np.sum(delta_v[-14:])
        recent_total = np.sum(v_arr[-14:])
        imbalance = float(recent_delta / recent_total) if recent_total > 0 else 0.0

        # Divergence / Squeeze Detection:
        # Price making lower lows but CVD making higher highs => Short Squeeze Absorption
        price_14_change = (c_arr[-1] - c_arr[-14]) / c_arr[-14] if c_arr[-14] > 0 else 0.0
        
        is_squeeze = False
        squeeze_type = "NONE"

        if price_14_change < -0.02 and slope > 0:
            is_squeeze = True
            squeeze_type = "SHORT_SQUEEZE"
        elif price_14_change > 0.02 and slope < 0:
            is_squeeze = True
            squeeze_type = "LONG_LIQUIDATION"

        # Funding proxy bias: persistent aggressive buying indicates positive funding rate pressure
        funding_bias = max(-1.0, min(imbalance * 1.5, 1.0))

        return LiquidityMetricsSnapshot(
            symbol=symbol,
            cvd=round(current_cvd, 2),
            cvd_slope_14=round(slope, 2),
            volume_imbalance_ratio=round(imbalance, 4),
            is_squeeze_risk=is_squeeze,
            squeeze_type=squeeze_type,
            funding_proxy_bias=round(funding_bias, 4),
            timestamp=timestamp,
        )
