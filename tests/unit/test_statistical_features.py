import numpy as np
import pytest

from crypto_mas.engine.math.statistical_features import StatisticalFeatureEngine


def test_rolling_zscore_calculation():
    # 60 sample points with known mean & std
    np.random.seed(42)
    values = np.random.normal(loc=50.0, scale=5.0, size=70)
    
    z_scores = StatisticalFeatureEngine.calculate_zscore(values, window=50)
    assert len(z_scores) == 70
    assert z_scores[0] == 0.0  # Not enough warm up
    # After window 50, z_scores should be reasonably bounded around [-3.5, 3.5]
    assert np.all(np.abs(z_scores[50:]) < 4.5)


def test_rolling_percentile_rank():
    values = np.arange(60, dtype=np.float64)  # strictly increasing
    percentiles = StatisticalFeatureEngine.calculate_percentile_rank(values, window=20)
    
    # For strictly increasing sequence, the latest value is the highest in the window => percentile 1.0
    assert pytest.approx(percentiles[-1], 0.01) == 1.0


def test_is_statistically_extreme():
    history = [50.0 + np.sin(i) * 5.0 for i in range(50)]
    
    # Value deeply below the distribution
    is_ext, ext_type, z = StatisticalFeatureEngine.is_statistically_extreme(
        current_value=30.0,
        history=history,
        z_threshold=2.0,
        quantile_threshold=0.05,
    )
    assert is_ext is True
    assert ext_type == "OVERSOLD"
    assert z < -2.0

    # Normal value
    is_norm, norm_type, _ = StatisticalFeatureEngine.is_statistically_extreme(
        current_value=50.0,
        history=history,
    )
    assert is_norm is False
    assert norm_type == "NORMAL"
