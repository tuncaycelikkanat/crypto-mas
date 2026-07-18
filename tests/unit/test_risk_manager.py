import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from crypto_mas.engine.risk.manager import RiskManager
from crypto_mas.engine.risk.models.btc_crash_model import BTCCrashModel
from crypto_mas.engine.risk.models.htf_portfolio_model import HTFPortfolioModel
from crypto_mas.engine.risk.models.regime_model import RegimeModel
from crypto_mas.engine.strategy.schemas import TradingDecision, DecisionAction
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.engine.signal import TradingSignal, SignalType, SignalDirection
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.regime import RegimeSnapshot, MarketRegime


@pytest.fixture
def risk_manager():
    return RiskManager(models=[
        BTCCrashModel(),
        HTFPortfolioModel(),
        RegimeModel()
    ])


def create_decision(action: DecisionAction, reason: str, confidence: float):
    decision = MagicMock()
    decision.action = action
    decision.reason = reason
    decision.confidence = confidence
    return decision

def test_btc_crash_rejects_long(risk_manager):
    decision = create_decision(action=DecisionAction.CONSIDER_LONG, reason="RSI Oversold", confidence=0.8)
    context = {"use_btc_shield": True, "btc_is_crashing": True}
    
    result = risk_manager.evaluate_decision(decision, context)
    
    assert result.action == DecisionAction.HOLD
    assert "REJECTED by BTC Crash Filter" in result.reason


def test_btc_crash_allows_short(risk_manager):
    decision = create_decision(action=DecisionAction.CONSIDER_SHORT, reason="RSI Overbought", confidence=0.8)
    context = {"use_btc_shield": True, "btc_is_crashing": True}
    
    result = risk_manager.evaluate_decision(decision, context)
    
    assert result.action == DecisionAction.CONSIDER_SHORT
    assert "REJECTED" not in result.reason


def test_htf_shield_rejects_long_in_bear_market(risk_manager):
    decision = create_decision(action=DecisionAction.CONSIDER_LONG, reason="MACD Cross", confidence=0.7)
    
    snapshot = FeatureSnapshot(
        id=1, exchange="binance", symbol="ETHUSDT", timeframe="4h",
        timestamp=datetime.now(timezone.utc),
        features_json={
            "close": 1000.0,
            "ema_20": 1100.0,
            "ema_50": 1200.0,
            "roc_14": -5.0
        }
    )
    context = {"use_htf_shield": True, "htf_snapshots": [snapshot]}
    
    result = risk_manager.evaluate_decision(decision, context)
    
    assert result.action == DecisionAction.HOLD
    assert "REJECTED by HTF Shield (Strong Bear)" in result.reason


def test_htf_shield_rejects_short_in_bull_market(risk_manager):
    decision = create_decision(action=DecisionAction.CONSIDER_SHORT, reason="RSI Divergence", confidence=0.7)
    
    snapshot = FeatureSnapshot(
        id=2, exchange="binance", symbol="ETHUSDT", timeframe="4h",
        timestamp=datetime.now(timezone.utc),
        features_json={
            "close": 1500.0,
            "ema_20": 1400.0,
            "ema_50": 1300.0,
            "roc_14": 5.0
        }
    )
    context = {"use_htf_shield": True, "htf_snapshots": [snapshot]}
    
    result = risk_manager.evaluate_decision(decision, context)
    
    assert result.action == DecisionAction.HOLD
    assert "REJECTED by HTF Shield (Strong Bull)" in result.reason


def test_regime_model_adjusts_confidence(risk_manager):
    decision = create_decision(action=DecisionAction.CONSIDER_LONG, reason="Setup", confidence=0.8)
    # Give the decision a HIGH_VOLATILITY regime
    decision.regime.regime = MarketRegime.HIGH_VOLATILITY

    context = {"use_regime_shield": True}

    result = risk_manager.evaluate_decision(decision, context)

    # In HIGH_VOLATILITY, it should REJECT
    assert result.action == DecisionAction.HOLD
    assert "REJECTED by Regime Shield (HIGH_VOLATILITY)" in result.reason


def test_all_shields_pass(risk_manager):
    decision = create_decision(action=DecisionAction.CONSIDER_LONG, reason="Perfect Setup", confidence=0.9)
    
    snapshot_4h = FeatureSnapshot(
        id=4, exchange="binance", symbol="ETHUSDT", timeframe="4h",
        timestamp=datetime.now(timezone.utc),
        features_json={
            "close": 1500.0,
            "ema_20": 1400.0,
            "ema_50": 1300.0,
            "roc_14": 5.0
        }
    )
    
    snapshot_15m = FeatureSnapshot(
        id=5, exchange="binance", symbol="ETHUSDT", timeframe="15m",
        timestamp=datetime.now(timezone.utc),
        features_json={
            "adx_14": 30.0  # Trending market
        }
    )
    
    context = {
        "use_btc_shield": True, "btc_is_crashing": False,
        "use_htf_shield": True, "htf_snapshots": [snapshot_4h],
        "use_regime_shield": True, "latest_features": snapshot_15m.features_json
    }
    
    result = risk_manager.evaluate_decision(decision, context)
    
    assert result.action == DecisionAction.CONSIDER_LONG
    assert result.confidence == 0.9  # Trending doesn't reduce confidence
    assert "REJECTED" not in result.reason
