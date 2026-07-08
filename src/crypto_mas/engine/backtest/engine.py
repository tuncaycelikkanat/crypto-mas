
from datetime import datetime, UTC
from typing import List, Dict, Any, Type
import logging

from crypto_mas.domain.models.candle import Candle
from crypto_mas.services.feature_pipeline.calculator import FeatureCalculator
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

logger = logging.getLogger("backtest_engine")

class Position:
    def __init__(self, symbol: str, entry_price: float, quantity: float, entry_time: datetime):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_time = entry_time

class BacktestEngine:
    def __init__(
        self, 
        initial_balance: float = 10000.0, 
        fee_rate: float = 0.001, # 0.1% fee
        slippage_pct: float = 0.0005 # 0.05% slippage
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.fee_rate = fee_rate
        self.slippage_pct = slippage_pct
        
        self.positions: Dict[str, Position] = {}
        self.trades = [] # List of executed trades
        
        self.feature_calculator = FeatureCalculator()

    def run(
        self, 
        symbol: str, 
        candles: List[Candle], 
        strategy: BaseStrategy, 
        timeframe: Timeframe = Timeframe.FIFTEEN_MINUTES,
        exchange: Exchange = Exchange.BINANCE
    ) -> Dict[str, Any]:
        """
        Runs the backtest over the provided historical candles using the specified strategy.
        """
        if not candles:
            return self._generate_report(symbol, strategy.name)
            
        logger.info(f"Starting backtest for {symbol} with {len(candles)} candles. Strategy: {strategy.__class__.__name__}")
        
        # 1. Calculate Features for the entire dataset (fast)
        # FeatureCalculator takes a list of Candle objects and returns a list of dictionaries (snapshots)
        feature_snapshots = self.feature_calculator.calculate(candles)
        
        # 2. Iterate through time (simulate step-by-step execution)
        # We need at least a small window to pass to the strategy.
        # Most strategies only look at the last 2-5 snapshots. We will maintain a rolling window of 5 snapshots.
        
        snapshot_window = []
        
        for idx, snap_dict in enumerate(feature_snapshots):
            current_time = snap_dict['timestamp']
            features_json = snap_dict['features_json']
            current_price = features_json.get('close', 0.0)
            
            snapshot = FeatureSnapshot(
                exchange=exchange.value,
                symbol=symbol,
                timeframe=timeframe.value,
                features_json=features_json,
                timestamp=current_time
            )
            
            snapshot_window.append(snapshot)
            if len(snapshot_window) > 5:
                snapshot_window.pop(0)
                
            if len(snapshot_window) < 5:
                continue # Wait for window to fill
                
            # Evaluate strategy
            decision = strategy.evaluate(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                snapshots=snapshot_window
            )
            
            if decision:
                self._process_decision(decision, current_price, current_time)
                
        # Close any open positions at the end of the backtest
        if symbol in self.positions and feature_snapshots:
            last_snap = feature_snapshots[-1]
            last_price = last_snap['features_json'].get('close', 0.0)
            self._close_position(symbol, last_price, last_snap['timestamp'], reason="End of Backtest")
            
        return self._generate_report(symbol, strategy.__class__.__name__)
        
    def _process_decision(self, decision, current_price: float, current_time: datetime):
        symbol = decision.symbol
        
        # Simple Logic: 
        # If CONSIDER_LONG and no position -> BUY
        # If CONSIDER_SHORT or NEUTRAL or HOLD -> Check if we should SELL
        # For this basic backtest, we will simulate a fixed Take Profit / Stop Loss, or let the strategy dictate SELL.
        # Currently, our strategies don't explicitly emit SELL (CONSIDER_SHORT is used for shorting, not closing longs).
        # So we'll implement a simple Trailing Stop or fixed TP/SL for the backtest.
        
        # Let's add a basic Take Profit (2%) and Stop Loss (1%)
        TP_PCT = 0.02
        SL_PCT = 0.01
        
        if symbol in self.positions:
            # Check TP/SL
            pos = self.positions[symbol]
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price
            
            if pnl_pct >= TP_PCT:
                self._close_position(symbol, current_price, current_time, reason="Take Profit")
            elif pnl_pct <= -SL_PCT:
                self._close_position(symbol, current_price, current_time, reason="Stop Loss")
            # Or if strategy says SHORT, close long
            elif decision.action == DecisionAction.CONSIDER_SHORT:
                self._close_position(symbol, current_price, current_time, reason="Strategy Reversal")
                
        elif decision.action == DecisionAction.CONSIDER_LONG:
            # Open Position
            # Risk 10% of balance per trade
            trade_amount = self.balance * 0.10
            
            # Apply slippage (buy higher)
            execution_price = current_price * (1 + self.slippage_pct)
            
            quantity = trade_amount / execution_price
            fee = trade_amount * self.fee_rate
            
            self.balance -= (trade_amount + fee)
            self.positions[symbol] = Position(symbol, execution_price, quantity, current_time)
            
            self.trades.append({
                "time": current_time,
                "symbol": symbol,
                "type": "BUY",
                "price": execution_price,
                "quantity": quantity,
                "fee": fee,
                "reason": decision.reason
            })

    def _close_position(self, symbol: str, current_price: float, current_time: datetime, reason: str):
        pos = self.positions.pop(symbol)
        
        # Apply slippage (sell lower)
        execution_price = current_price * (1 - self.slippage_pct)
        
        notional = pos.quantity * execution_price
        fee = notional * self.fee_rate
        
        self.balance += (notional - fee)
        
        pnl = notional - fee - (pos.quantity * pos.entry_price)
        
        self.trades.append({
            "time": current_time,
            "symbol": symbol,
            "type": "SELL",
            "price": execution_price,
            "quantity": pos.quantity,
            "fee": fee,
            "realized_pnl": pnl,
            "reason": reason
        })
        
    def _generate_report(self, symbol: str, strategy_name: str) -> Dict[str, Any]:
        closed_trades = [t for t in self.trades if t['type'] == 'SELL']
        
        winning_trades = [t for t in closed_trades if t['realized_pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['realized_pnl'] <= 0]
        
        total_profit = sum(t['realized_pnl'] for t in winning_trades)
        total_loss = abs(sum(t['realized_pnl'] for t in losing_trades))
        
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
        win_rate = (len(winning_trades) / len(closed_trades)) * 100 if closed_trades else 0.0
        
        # Calculate Max Drawdown
        peak = self.initial_balance
        max_dd = 0.0
        current_equity = self.initial_balance
        
        # We approximate equity curve via trades for simplicity
        for t in closed_trades:
            current_equity += t['realized_pnl']
            if current_equity > peak:
                peak = current_equity
            dd = (peak - current_equity) / peak
            if dd > max_dd:
                max_dd = dd
                
        return {
            "symbol": symbol,
            "strategy": strategy_name,
            "initial_balance": self.initial_balance,
            "final_balance": self.balance,
            "total_pnl": self.balance - self.initial_balance,
            "pnl_pct": ((self.balance - self.initial_balance) / self.initial_balance) * 100,
            "total_trades": len(closed_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_dd * 100
        }
