from datetime import UTC, datetime
from decimal import Decimal

import pytest

from crypto_mas.domain.models.candle import Candle
from crypto_mas.engine.backtest.engine import BacktestEngine


@pytest.fixture
def backtest_engine():
    return BacktestEngine(initial_balance=1000.0, fee_rate=0.001, slippage_pct=0.0)

def test_backtest_engine_calculates_pnl_correctly(backtest_engine, monkeypatch):
    # Simulate a single winning trade
    # Buy at 10000, sell at 11000
    
    candles = [
        Candle(exchange="BINANCE", symbol="BTCUSDT", timeframe="15m", open_time=datetime(2023, 1, 1, 0, 0, tzinfo=UTC), close_time=datetime(2023, 1, 1, 0, 15, tzinfo=UTC),
               open=Decimal("10000"), high=Decimal("10100"), low=Decimal("9900"), close=Decimal("10000"), volume=Decimal("100")),
        Candle(exchange="BINANCE", symbol="BTCUSDT", timeframe="15m", open_time=datetime(2023, 1, 1, 0, 15, tzinfo=UTC), close_time=datetime(2023, 1, 1, 0, 30, tzinfo=UTC),
               open=Decimal("10000"), high=Decimal("11100"), low=Decimal("10000"), close=Decimal("10000"), volume=Decimal("100")),
        Candle(exchange="BINANCE", symbol="BTCUSDT", timeframe="15m", open_time=datetime(2023, 1, 1, 0, 30, tzinfo=UTC), close_time=datetime(2023, 1, 1, 0, 45, tzinfo=UTC),
               open=Decimal("10000"), high=Decimal("11100"), low=Decimal("10000"), close=Decimal("10000"), volume=Decimal("100")),
        Candle(exchange="BINANCE", symbol="BTCUSDT", timeframe="15m", open_time=datetime(2023, 1, 1, 0, 45, tzinfo=UTC), close_time=datetime(2023, 1, 1, 1, 0, tzinfo=UTC),
               open=Decimal("10000"), high=Decimal("11100"), low=Decimal("10000"), close=Decimal("10000"), volume=Decimal("100")),
        Candle(exchange="BINANCE", symbol="BTCUSDT", timeframe="15m", open_time=datetime(2023, 1, 1, 1, 0, tzinfo=UTC), close_time=datetime(2023, 1, 1, 1, 15, tzinfo=UTC),
               open=Decimal("10000"), high=Decimal("11100"), low=Decimal("10000"), close=Decimal("10000"), volume=Decimal("100")),
        Candle(exchange="BINANCE", symbol="BTCUSDT", timeframe="15m", open_time=datetime(2023, 1, 1, 1, 15, tzinfo=UTC), close_time=datetime(2023, 1, 1, 1, 30, tzinfo=UTC),
               open=Decimal("10000"), high=Decimal("11100"), low=Decimal("10000"), close=Decimal("11000"), volume=Decimal("100")),
    ]
    
    # Mocking strategy that buys on candle 0 and sells on candle 1
    class MockStrategy:
        def __init__(self):
            self.name = "MockStrategy"
            self.step = 0
            
        def decide(self, exchange, symbol, timeframe, snapshots):
            from datetime import UTC, datetime

            from crypto_mas.engine.regime import MarketRegime, RegimeSnapshot
            from crypto_mas.engine.scoring import AssetScore
            from crypto_mas.engine.signal import SignalDirection, TradingSignal
            from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
            
            action = DecisionAction.HOLD
            if self.step == 0:
                action = DecisionAction.CONSIDER_LONG
            elif self.step == 1:
                action = DecisionAction.CONSIDER_SHORT
                
            self.step += 1
            
            candle = snapshots[-1]
            
            return TradingDecision(
                exchange=exchange, symbol=symbol, timeframe=candle.timeframe,
                action=action, confidence=1.0,
                signal=TradingSignal(
                    exchange=exchange, symbol=symbol, timeframe=candle.timeframe,
                    signal_type="TREND_FOLLOWING", direction=SignalDirection.LONG if action == DecisionAction.CONSIDER_LONG else SignalDirection.NEUTRAL,
                    strength=1.0, indicators={}, reason="mock", timestamp=datetime.now(UTC)
                ),
                score=AssetScore(
                    exchange=exchange, symbol=symbol, timeframe=candle.timeframe,
                    direction=SignalDirection.LONG, trend_score=1.0, momentum_score=1.0,
                    volatility_penalty=0.0, final_score=1.0, components={}, reason="mock", timestamp=datetime.now(UTC)
                ),
                regime=RegimeSnapshot(
                    exchange=exchange, symbol=symbol, timeframe=candle.timeframe,
                    regime=MarketRegime.BULL_TREND, confidence=1.0, risk_multiplier=1.0,
                    reason="mock", timestamp=datetime.now(UTC)
                ),
                reason="mock test",
                created_at=datetime.now(UTC)
            )
            
    # Patch FeatureCalculator to bypass 50-candle requirement
    def mock_calculate(candles):
        return [{"timestamp": c.open_time, "features_json": {"close": float(c.close)}} for c in candles]
    monkeypatch.setattr(backtest_engine.feature_calculator, "calculate", mock_calculate)
    
    result = backtest_engine.run("BTCUSDT", candles, MockStrategy())
    
    # Balance: 1000. Buy at 10000. Trade amount = 100.
    # quantity = 0.01
    # fee = 0.1. Balance = 899.9
    # Exit at 11000. Notional = 110.
    # fee = 0.11. Return = 109.89.
    # Final Balance = 899.9 + 109.89 = 1009.79
    # PnL = 9.79
    
    assert result["total_trades"] == 1
    assert result["win_rate"] == 100.0
    assert result["total_pnl"] == pytest.approx(9.79)
    assert result["final_balance"] == pytest.approx(1009.79)

def test_backtest_engine_no_trades(backtest_engine, monkeypatch):
    candles = [
        Candle(exchange="BINANCE", symbol="BTCUSDT", timeframe="15m", open_time=datetime(2023, 1, 1, 0, 0, tzinfo=UTC), close_time=datetime(2023, 1, 1, 0, 15, tzinfo=UTC),
               open=Decimal("10000"), high=Decimal("10100"), low=Decimal("9900"), close=Decimal("10000"), volume=Decimal("100")),
    ]
    class HoldStrategy:
        def __init__(self):
            self.name = "HoldStrategy"
        def decide(self, exchange, symbol, timeframe, snapshots):
            return None
            
    def mock_calculate(candles):
        return [{"timestamp": c.open_time, "features_json": {"close": float(c.close)}} for c in candles]
    monkeypatch.setattr(backtest_engine.feature_calculator, "calculate", mock_calculate)

    result = backtest_engine.run("BTCUSDT", candles, HoldStrategy())
    assert result["total_trades"] == 0
    assert result["total_pnl"] == 0.0
    assert result["final_balance"] == 1000.0
