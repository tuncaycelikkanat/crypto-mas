from datetime import UTC, datetime
import pytest

from crypto_mas.engine.portfolio.bet_sizing import BetSizer
from crypto_mas.services.feature_pipeline.liquidity_metrics import LiquidityMetricsCalculator


def test_liquidity_metrics_cvd_and_squeeze():
    now = datetime.now(UTC)
    
    # 20 bars: price dropping but volume on positive closes increasing (bullish absorption / short squeeze)
    closes = [100.0 - i * 0.5 for i in range(20)]
    opens = [c - 0.2 for c in closes] # close > open (buying bars)
    volumes = [1000.0 + i * 100 for i in range(20)]

    snapshot = LiquidityMetricsCalculator.calculate(
        symbol="BTCUSDT",
        closes=closes,
        opens=opens,
        volumes=volumes,
        timestamp=now,
    )

    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.cvd > 0
    assert snapshot.is_squeeze_risk is True
    assert snapshot.squeeze_type == "SHORT_SQUEEZE"


def test_bet_sizer_fractional_kelly_and_volatility():
    sizer = BetSizer(
        target_annual_volatility=0.20,
        kelly_multiplier=0.25,
        max_single_weight=0.35,
        min_single_weight=0.02,
    )

    # 1. Fractional Kelly calculation: 60% win rate, 2:1 R/R
    # Full Kelly = 0.60 - (0.40 / 2.0) = 0.40
    # Quarter Kelly = 0.40 * 0.25 = 0.10
    kelly_w = sizer.calculate_fractional_kelly(win_rate=0.60, reward_risk_ratio=2.0)
    assert pytest.approx(kelly_w, 0.01) == 0.10

    # Negative edge should return 0.0
    neg_kelly = sizer.calculate_fractional_kelly(win_rate=0.30, reward_risk_ratio=1.0)
    assert neg_kelly == 0.0

    # 2. Volatility targeting
    # ATR = 1000 on 50000 BTC => 2% bar vol => annualized ~76%
    # Target 20% / 76% => weight ~0.26
    vol_w = sizer.calculate_volatility_target_weight(asset_atr=1000.0, asset_price=50000.0)
    assert 0.10 < vol_w < 0.35

    # 3. Combined size recommendation
    rec = sizer.recommend_size(
        symbol="BTCUSDT",
        confidence_score=0.85,
        asset_atr=1000.0,
        asset_price=50000.0,
        estimated_win_rate=0.60,
        reward_risk_ratio=2.0,
    )

    assert rec.symbol == "BTCUSDT"
    assert 0.02 <= rec.target_weight <= 0.35
    assert "BetSize: Kelly" in rec.reason
