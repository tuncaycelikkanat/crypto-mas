import math

from numba import njit


@njit(cache=True)
def jit_trend_score(
    close: float,
    ema_20: float,
    ema_50: float,
    direction_val: int,
) -> float:
    """
    Computes trend score using JIT compilation for maximum performance.
    direction_val: 1 for LONG, -1 for SHORT
    """
    if close <= 0:
        return 0.0

    if direction_val == 1:
        ema_spread = max((ema_20 - ema_50) / close, 0.0)
        price_distance = max((close - ema_20) / close, 0.0)
    elif direction_val == -1:
        ema_spread = max((ema_50 - ema_20) / close, 0.0)
        price_distance = max((ema_20 - close) / close, 0.0)
    else:
        return 0.0

    return max(0.0, min((ema_spread * 20.0) + (price_distance * 10.0), 1.0))


@njit(cache=True)
def jit_momentum_score(
    rsi_14: float,
    roc_14: float,
    macd: float,
    macd_signal: float,
    atr_14: float,
    close: float,
    direction_val: int,
) -> float:
    """
    Computes momentum score using JIT compilation.
    direction_val: 1 for LONG, -1 for SHORT
    """
    if close <= 0:
        return 0.0

    macd_hist = macd - macd_signal
    norm_denom = max(atr_14 * 0.1, 1e-9)

    if direction_val == 1:
        rsi_score = max((rsi_14 - 50.0) / 50.0, 0.0)
        roc_score = max(roc_14 / 10.0, 0.0)
        macd_score = max(math.tanh(macd_hist / norm_denom), 0.0)
    elif direction_val == -1:
        rsi_score = max((50.0 - rsi_14) / 50.0, 0.0)
        roc_score = max((-roc_14) / 10.0, 0.0)
        macd_score = max(math.tanh(-macd_hist / norm_denom), 0.0)
    else:
        return 0.0

    return max(0.0, min((rsi_score * 0.3) + (roc_score * 0.3) + (macd_score * 0.4), 1.0))


@njit(cache=True)
def jit_volatility_penalty(close: float, atr_14: float) -> float:
    """
    Computes volatility penalty using JIT.
    """
    if close <= 0:
        return 0.0

    atr_ratio = atr_14 / close
    return max(0.0, min(atr_ratio * 2.0, 0.35))


@njit(cache=True)
def jit_calculate_confidence(
    score: float,
    regime_confidence: float,
    risk_multiplier: float,
) -> float:
    """
    Calculate confidence weighting.
    """
    raw = score * 0.65 + regime_confidence * 0.35
    adjusted = raw * risk_multiplier
    return max(0.0, min(adjusted, 1.0))
