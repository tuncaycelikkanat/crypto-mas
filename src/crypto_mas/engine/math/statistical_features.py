import numpy as np
from numba import njit


@njit(cache=True)
def jit_rolling_zscore(values: np.ndarray, window: int = 50) -> np.ndarray:
    """
    Computes rolling z-score for a 1D float array using JIT.
    z = (x - mean) / std
    """
    n = len(values)
    z_scores = np.zeros(n, dtype=np.float64)
    
    if n < window:
        return z_scores

    for i in range(window - 1, n):
        win_slice = values[i - window + 1 : i + 1]
        mean = np.mean(win_slice)
        std = np.std(win_slice)
        
        if std > 1e-9:
            z_scores[i] = (values[i] - mean) / std
        else:
            z_scores[i] = 0.0
            
    return z_scores


@njit(cache=True)
def jit_rolling_percentile(values: np.ndarray, window: int = 50) -> np.ndarray:
    """
    Computes rolling empirical percentile (0.0 to 1.0) for each point
    relative to its lookback window.
    """
    n = len(values)
    percentiles = np.zeros(n, dtype=np.float64)
    
    if n < window:
        return percentiles

    for i in range(window - 1, n):
        target = values[i]
        win_slice = values[i - window + 1 : i + 1]
        count_less = 0
        for val in win_slice:
            if val <= target:
                count_less += 1
        percentiles[i] = count_less / float(window)
        
    return percentiles


class StatisticalFeatureEngine:
    """
    Computes self-calibrating statistical metrics (Z-scores and Quantile ranks)
    across indicator series to eliminate static numeric thresholds.
    """

    @staticmethod
    def calculate_zscore(series: list[float] | np.ndarray, window: int = 50) -> np.ndarray:
        arr = np.asarray(series, dtype=np.float64)
        return jit_rolling_zscore(arr, window=window)

    @staticmethod
    def calculate_percentile_rank(series: list[float] | np.ndarray, window: int = 50) -> np.ndarray:
        arr = np.asarray(series, dtype=np.float64)
        return jit_rolling_percentile(arr, window=window)

    @staticmethod
    def is_statistically_extreme(
        current_value: float,
        history: list[float],
        z_threshold: float = 2.0,
        quantile_threshold: float = 0.05,
    ) -> tuple[bool, str, float]:
        """
        Determines if current_value represents an upper or lower statistical extreme.
        Returns: (is_extreme, extreme_type: 'OVERSOLD' | 'OVERBOUGHT' | 'NORMAL', z_score)
        """
        if len(history) < 20:
            return False, "NORMAL", 0.0

        hist_arr = np.asarray(history, dtype=np.float64)
        mean = float(np.mean(hist_arr))
        std = float(np.std(hist_arr))

        if std < 1e-9:
            return False, "NORMAL", 0.0

        z = (current_value - mean) / std
        
        # Empirical quantile
        q = float(np.sum(hist_arr <= current_value)) / len(hist_arr)

        if z <= -z_threshold or q <= quantile_threshold:
            return True, "OVERSOLD", z
        elif z >= z_threshold or q >= (1.0 - quantile_threshold):
            return True, "OVERBOUGHT", z

        return False, "NORMAL", z
