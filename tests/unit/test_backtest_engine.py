from datetime import datetime, timezone
from crypto_mas.engine.backtest.engine import BacktestEngine, Position
from crypto_mas.engine.strategy.schemas import DecisionAction

class MockDecision:
    def __init__(self, symbol: str, action: DecisionAction, reason: str):
        self.symbol = symbol
        self.action = action
        self.reason = reason

def test_backtest_engine_initialization():
    engine = BacktestEngine(initial_balance=5000.0, fee_rate=0.001, slippage_pct=0.0005)
    assert engine.initial_balance == 5000.0
    assert engine.balance == 5000.0
    assert len(engine.positions) == 0
    assert len(engine.trades) == 0

def test_process_decision_long_and_short():
    engine = BacktestEngine(initial_balance=10000.0)
    now = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
    
    # 1. Open LONG position
    long_decision = MockDecision(
        symbol="BTCUSDT",
        action=DecisionAction.CONSIDER_LONG,
        reason="Test Long Entry"
    )
    features = {"close": 50000.0, "atr_14": 1000.0}
    engine._process_decision(long_decision, current_price=50000.0, current_time=now, features_json=features)
    
    assert "BTCUSDT" in engine.positions
    pos = engine.positions["BTCUSDT"]
    assert pos.side == "LONG"
    assert len(engine.trades) == 1
    assert engine.trades[0]["type"] == "OPEN_LONG"

    # 2. Reversal decision -> Close Long and Open Short
    short_decision = MockDecision(
        symbol="BTCUSDT",
        action=DecisionAction.CONSIDER_SHORT,
        reason="Test Short Reversal"
    )
    engine._process_decision(short_decision, current_price=51000.0, current_time=now, features_json=features)
    
    # After reversal: long is closed, short is opened
    assert "BTCUSDT" in engine.positions
    assert engine.positions["BTCUSDT"].side == "SHORT"
    assert len(engine.trades) == 3  # OPEN_LONG, CLOSE_LONG, OPEN_SHORT
    assert engine.trades[1]["type"] == "CLOSE_LONG"
    assert engine.trades[2]["type"] == "OPEN_SHORT"

def test_generate_report_metrics():
    engine = BacktestEngine(initial_balance=10000.0)
    now = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
    
    # Manually insert completed trades
    engine.trades = [
        {"type": "CLOSE_LONG", "symbol": "BTCUSDT", "realized_pnl": 200.0, "time": now, "reason": "Take Profit"},
        {"type": "CLOSE_SHORT", "symbol": "BTCUSDT", "realized_pnl": -50.0, "time": now, "reason": "Stop Loss"},
        {"type": "CLOSE_LONG", "symbol": "BTCUSDT", "realized_pnl": 150.0, "time": now, "reason": "Take Profit"}
    ]
    
    report = engine._generate_report("BTCUSDT", "TestStrategy")
    assert report["symbol"] == "BTCUSDT"
    assert report["total_trades"] == 3
    assert report["total_pnl"] == 300.0
    assert abs(report["win_rate"] - 66.67) < 0.1
    assert report["profit_factor"] == 7.0  # 350 profit / 50 loss
