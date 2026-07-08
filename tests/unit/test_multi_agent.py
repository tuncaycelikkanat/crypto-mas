from datetime import datetime, UTC
from unittest.mock import MagicMock

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime, RegimeSnapshot
from crypto_mas.engine.scoring.scoring import AssetScore
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.engine.strategy.multi_agent import MultiAgentStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.infrastructure.time.time_provider import TimeProvider

def test_multi_agent_long_consideration():
    # Setup mocks
    signal_mock = MagicMock()
    signal_mock.generate.return_value = TradingSignal(
        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES,
        signal_type=SignalType.TREND_FOLLOWING, direction=SignalDirection.LONG, strength=0.8,
        indicators={}, reason="Test Signal", timestamp=datetime.now(UTC)
    )
    
    scoring_mock = MagicMock()
    scoring_mock.score.return_value = AssetScore(
        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES,
        direction=SignalDirection.LONG, trend_score=0.8, momentum_score=0.2, volatility_penalty=0.0,
        final_score=0.8, components={}, reason="Test Score", timestamp=datetime.now(UTC)
    )
    
    regime_mock = MagicMock()
    regime_mock.detect.return_value = RegimeSnapshot(
        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES,
        regime=MarketRegime.BULL_TREND, confidence=0.9, risk_multiplier=1.0,
        reason="Test Regime", timestamp=datetime.now(UTC)
    )
    
    time_provider_mock = MagicMock(spec=TimeProvider)
    time_provider_mock.now.return_value = datetime.now(UTC)
    
    strategy = MultiAgentStrategy(
        signal_agent=signal_mock,
        scoring_agent=scoring_mock,
        regime_agent=regime_mock,
        time_provider=time_provider_mock
    )
    
    snapshots = [MagicMock(spec=FeatureSnapshot)]
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    
    assert decision is not None
    assert decision.action == DecisionAction.CONSIDER_LONG
    assert decision.confidence > 0.0

def test_multi_agent_high_volatility_avoid():
    # Setup mocks
    signal_mock = MagicMock()
    signal_mock.generate.return_value = TradingSignal(
        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES,
        signal_type=SignalType.TREND_FOLLOWING, direction=SignalDirection.LONG, strength=0.8,
        indicators={}, reason="Test Signal", timestamp=datetime.now(UTC)
    )
    
    scoring_mock = MagicMock()
    scoring_mock.score.return_value = AssetScore(
        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES,
        direction=SignalDirection.LONG, trend_score=0.8, momentum_score=0.2, volatility_penalty=0.0,
        final_score=0.8, components={}, reason="Test Score", timestamp=datetime.now(UTC)
    )
    
    regime_mock = MagicMock()
    regime_mock.detect.return_value = RegimeSnapshot(
        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES,
        regime=MarketRegime.HIGH_VOLATILITY, confidence=0.9, risk_multiplier=0.2,
        reason="Test Regime", timestamp=datetime.now(UTC)
    )
    
    strategy = MultiAgentStrategy(
        signal_agent=signal_mock,
        scoring_agent=scoring_mock,
        regime_agent=regime_mock
    )
    
    snapshots = [MagicMock(spec=FeatureSnapshot)]
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    
    assert decision is not None
    assert decision.action == DecisionAction.AVOID

def test_multi_agent_missing_signal():
    signal_mock = MagicMock()
    signal_mock.generate.return_value = None
    
    strategy = MultiAgentStrategy(signal_agent=signal_mock)
    
    snapshots = [MagicMock(spec=FeatureSnapshot)]
    decision = strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.FIFTEEN_MINUTES, snapshots)
    
    assert decision is None

def test_decide_score_none():
    signal_agent = MagicMock()
    scoring_agent = MagicMock()
    
    signal_agent.generate.return_value = MagicMock()
    scoring_agent.score.return_value = None
    
    strategy = MultiAgentStrategy(signal_agent=signal_agent, scoring_agent=scoring_agent)
    
    assert strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.FOUR_HOURS, []) is None

def test_decide_regime_none():
    signal_agent = MagicMock()
    scoring_agent = MagicMock()
    regime_agent = MagicMock()
    
    signal_agent.generate.return_value = MagicMock()
    scoring_agent.score.return_value = MagicMock()
    regime_agent.detect.return_value = None
    
    strategy = MultiAgentStrategy(signal_agent=signal_agent, scoring_agent=scoring_agent, regime_agent=regime_agent)
    
    assert strategy.decide(Exchange.BINANCE, "BTCUSDT", Timeframe.FOUR_HOURS, []) is None

def test_decide_action_long_bear_trend():
    action = MultiAgentStrategy._decide_action(SignalDirection.LONG, 0.5, MarketRegime.BEAR_TREND)
    assert action == DecisionAction.AVOID

def test_decide_action_long_hold():
    action = MultiAgentStrategy._decide_action(SignalDirection.LONG, 0.2, MarketRegime.BULL_TREND)
    assert action == DecisionAction.HOLD

def test_decide_action_short_bull_trend():
    action = MultiAgentStrategy._decide_action(SignalDirection.SHORT, 0.5, MarketRegime.BULL_TREND)
    assert action == DecisionAction.AVOID

def test_decide_action_short_consider():
    action = MultiAgentStrategy._decide_action(SignalDirection.SHORT, 0.5, MarketRegime.BEAR_TREND)
    assert action == DecisionAction.CONSIDER_SHORT

def test_decide_action_short_hold():
    action = MultiAgentStrategy._decide_action(SignalDirection.SHORT, 0.2, MarketRegime.BEAR_TREND)
    assert action == DecisionAction.HOLD

def test_decide_action_neutral_hold():
    action = MultiAgentStrategy._decide_action(SignalDirection.NEUTRAL, 0.5, MarketRegime.SIDEWAYS)
    assert action == DecisionAction.HOLD
