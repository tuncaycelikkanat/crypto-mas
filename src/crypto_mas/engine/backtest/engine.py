
import logging
from datetime import datetime
from typing import Any

from crypto_mas.domain.models.candle import Candle
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.services.feature_pipeline.calculator import FeatureCalculator
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

logger = logging.getLogger("backtest_engine")

class Position:
    def __init__(self, symbol: str, entry_price: float, quantity: float, entry_time: datetime, open_fee: float = 0.0, side: str = "LONG"):
        self.symbol = symbol
        self.entry_price = entry_price
        self.quantity = quantity
        self.entry_time = entry_time
        self.open_fee = open_fee
        self.side = side

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
        
        self.positions: dict[str, Position] = {}
        self.trades: list[Any] = []
        
        self.feature_calculator = FeatureCalculator()

    def run(
        self, 
        symbol: str, 
        candles: list[Candle], 
        strategy: BaseStrategy, 
        timeframe: Timeframe = Timeframe.FIFTEEN_MINUTES,
        exchange: Exchange = Exchange.BINANCE
    ) -> dict[str, Any]:
        """
        Runs the backtest over the provided historical candles using the specified strategy.
        """
        if not candles:
            return self._generate_report(symbol, strategy.__class__.__name__)  # type: ignore
            
        logger.info(f"Starting backtest for {symbol} with {len(candles)} candles. Strategy: {strategy.__class__.__name__}")
        
        # 1. Calculate Features for the entire dataset (fast)
        # FeatureCalculator takes a list of Candle objects and returns a list of dictionaries (snapshots)
        feature_snapshots = self.feature_calculator.calculate(candles)
        
        # 2. Iterate through time (simulate step-by-step execution)
        # We need at least a small window to pass to the strategy.
        # Most strategies only look at the last 2-5 snapshots. We will maintain a rolling window of 5 snapshots.
        
        snapshot_window = []
        
        for _idx, snap_dict in enumerate(feature_snapshots):
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
            decision = strategy.decide(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                snapshots=snapshot_window
            )
            
            if decision:
                self._process_decision(decision, current_price, current_time, features_json=features_json)
                
        # Close any open positions at the end of the backtest
        if symbol in self.positions and feature_snapshots:
            last_snap = feature_snapshots[-1]
            last_price = last_snap['features_json'].get('close', 0.0)
            self._close_position(symbol, last_price, last_snap['timestamp'], reason="End of Backtest")
            
        return self._generate_report(symbol, strategy.__class__.__name__)
        
    def _process_decision(self, decision, current_price: float, current_time: datetime, features_json: dict[str, Any] | None = None):
        symbol = decision.symbol
        
        # Dynamic ATR-based Take Profit and Stop Loss
        atr_val = features_json.get("atr_14") if features_json else None
        if atr_val and float(atr_val) > 0 and current_price > 0:
            atr_pct = float(atr_val) / current_price
            SL_PCT = max(0.005, min(0.05, atr_pct * 1.5))
            TP_PCT = max(0.01, min(0.10, SL_PCT * 2.0))
        else:
            TP_PCT = 0.02
            SL_PCT = 0.01
        
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.side == "LONG":
                pnl_pct = (current_price - pos.entry_price) / pos.entry_price
                if pnl_pct >= TP_PCT:
                    self._close_position(symbol, current_price, current_time, reason="Take Profit")
                elif pnl_pct <= -SL_PCT:
                    self._close_position(symbol, current_price, current_time, reason="Stop Loss")
                elif decision.action == DecisionAction.CONSIDER_SHORT:
                    self._close_position(symbol, current_price, current_time, reason="Strategy Reversal")
            else:  # SHORT
                pnl_pct = (pos.entry_price - current_price) / pos.entry_price
                if pnl_pct >= TP_PCT:
                    self._close_position(symbol, current_price, current_time, reason="Take Profit")
                elif pnl_pct <= -SL_PCT:
                    self._close_position(symbol, current_price, current_time, reason="Stop Loss")
                elif decision.action == DecisionAction.CONSIDER_LONG:
                    self._close_position(symbol, current_price, current_time, reason="Strategy Reversal")
                
        if symbol not in self.positions:
            if decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT):
                side = "LONG" if decision.action == DecisionAction.CONSIDER_LONG else "SHORT"
                trade_amount = self.balance * 0.10
                
                if side == "LONG":
                    execution_price = current_price * (1 + self.slippage_pct)
                else:
                    execution_price = current_price * (1 - self.slippage_pct)
                    
                quantity = trade_amount / execution_price
                fee = trade_amount * self.fee_rate
                
                self.balance -= (trade_amount + fee)
                self.positions[symbol] = Position(symbol, execution_price, quantity, current_time, open_fee=fee, side=side)
                
                self.trades.append({
                    "time": current_time,
                    "symbol": symbol,
                    "type": f"OPEN_{side}",
                    "side": side,
                    "price": execution_price,
                    "quantity": quantity,
                    "fee": fee,
                    "reason": decision.reason
                })

    def _close_position(self, symbol: str, current_price: float, current_time: datetime, reason: str):
        pos = self.positions.pop(symbol)
        
        if pos.side == "LONG":
            execution_price = current_price * (1 - self.slippage_pct)
            notional = pos.quantity * execution_price
            fee = notional * self.fee_rate
            self.balance += (notional - fee)
            pnl = notional - fee - (pos.quantity * pos.entry_price) - pos.open_fee
        else:  # SHORT
            execution_price = current_price * (1 + self.slippage_pct)
            entry_notional = pos.quantity * pos.entry_price
            exit_notional = pos.quantity * execution_price
            fee = exit_notional * self.fee_rate
            pnl = entry_notional - exit_notional - fee - pos.open_fee
            self.balance += (entry_notional + pnl)
        
        self.trades.append({
            "time": current_time,
            "symbol": symbol,
            "type": f"CLOSE_{pos.side}",
            "side": pos.side,
            "price": execution_price,
            "quantity": pos.quantity,
            "fee": fee,
            "realized_pnl": pnl,
            "reason": reason
        })
        
    def _generate_report(self, symbol: str, strategy_name: str) -> dict[str, Any]:
        closed_trades = [t for t in self.trades if (t['type'].startswith('CLOSE_') or t['type'] == 'SELL') and t['symbol'] == symbol]
        
        winning_trades = [t for t in closed_trades if t.get('realized_pnl', 0.0) > 0]
        losing_trades = [t for t in closed_trades if t.get('realized_pnl', 0.0) <= 0]
        
        total_profit = sum(t['realized_pnl'] for t in winning_trades)
        total_loss = abs(sum(t['realized_pnl'] for t in losing_trades))
        total_pnl = total_profit - total_loss
        
        profit_factor = (total_profit / total_loss) if total_loss > 0 else (float('inf') if total_profit > 0 else 0.0)
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
            "final_balance": self.initial_balance + total_pnl,
            "total_pnl": total_pnl,
            "pnl_pct": (total_pnl / self.initial_balance) * 100,
            "total_trades": len(closed_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_dd * 100
        }
