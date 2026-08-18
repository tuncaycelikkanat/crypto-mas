from datetime import UTC, datetime

from crypto_mas.engine.portfolio.portfolio import PortfolioEngine
from crypto_mas.engine.regime import MarketRegime, RegimeSnapshot
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def test_portfolio_engine_immutability():
    """Ensure that build_target_portfolio does NOT mutate the original decision objects."""
    now = datetime.now(UTC)
    regime_snap = RegimeSnapshot(
        exchange=Exchange.BINANCE,
        symbol="DOGEUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        regime=MarketRegime.BEAR_TREND,
        confidence=0.90,
        risk_multiplier=1.0,
        reason="Bear market confirmed",
        timestamp=now,
    )

    signal = TradingSignal(
        exchange=Exchange.BINANCE,
        symbol="DOGEUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        signal_type=SignalType.TREND_FOLLOWING,
        direction=SignalDirection.LONG,
        strength=0.8,
        reason="Strong trend",
        timestamp=now,
    )

    score = AssetScore(
        exchange=Exchange.BINANCE,
        symbol="DOGEUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        direction=SignalDirection.LONG,
        final_score=0.75,
        trend_score=0.8,
        momentum_score=0.7,
        volatility_penalty=0.0,
        reason="High score",
        timestamp=now,
    )

    original_decision = TradingDecision(
        exchange=Exchange.BINANCE,
        symbol="DOGEUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        action=DecisionAction.CONSIDER_LONG,
        confidence=0.75,
        reason="Bullish divergence",
        signal=signal,
        score=score,
        regime=regime_snap,
    )

    decisions = [original_decision]
    engine = PortfolioEngine(coin_groups={"TOP10": {"BTCUSDT", "ETHUSDT"}})

    target = engine.build_target_portfolio(
        exchange=Exchange.BINANCE,
        timeframe=Timeframe.FOUR_HOURS,
        decisions=decisions,
    )

    # The original decision must NOT have been modified
    assert original_decision.confidence == 0.75
    assert original_decision.reason == "Bullish divergence"

    # The target should have rejected DOGEUSDT in bear trend because it's not in TOP10
    assert len(target.target_positions) == 0


def test_portfolio_engine_configurable_coin_groups():
    """Ensure custom coin groups and btc correlated symbols can be injected."""
    custom_coin_groups = {
        "TOP10": {"BTCUSDT", "CUSTOM_COIN"},
        "MEMES": {"CUSTOM_MEME"},
    }
    custom_btc_correlated = {"BTCUSDT", "CUSTOM_COIN"}

    engine = PortfolioEngine(
        coin_groups=custom_coin_groups,
        btc_correlated_symbols=custom_btc_correlated,
    )

    assert "CUSTOM_COIN" in engine.coin_groups["TOP10"]
    assert "CUSTOM_COIN" in engine.btc_correlated_symbols
