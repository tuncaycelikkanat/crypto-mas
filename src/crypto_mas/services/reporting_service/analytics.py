from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import select

from crypto_mas.domain.models.trading_cycle import TradingCycle

@dataclass
class PerformanceMetrics:
    total_cycles: int
    total_trades: int
    winning_cycles: int
    losing_cycles: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    peak_equity: float

class PerformanceAnalytics:
    def __init__(self, db: Session) -> None:
        self.db = db

    def calculate_for_account(self, account_name: str, initial_balance: float) -> PerformanceMetrics:
        """
        Calculates performance metrics by tracing the equity curve of an account 
        across its trading cycles.
        """
        stmt = (
            select(TradingCycle)
            .where(TradingCycle.account_name == account_name)
            .order_by(TradingCycle.started_at.asc())
        )
        
        cycles = self.db.scalars(stmt).all()
        
        total_cycles = len(cycles)
        total_trades = sum(c.trades_executed for c in cycles if c.trades_executed)
        
        winning_cycles = 0
        losing_cycles = 0
        total_pnl = 0.0
        
        current_equity = initial_balance
        peak_equity = initial_balance
        max_drawdown = 0.0
        
        for cycle in cycles:
            pnl = float(cycle.cycle_pnl) if cycle.cycle_pnl else 0.0
            
            if pnl > 0:
                winning_cycles += 1
            elif pnl < 0:
                losing_cycles += 1
                
            total_pnl += pnl
            
            # Ending equity is recorded in cycle, or we can trace it
            if cycle.ending_equity:
                current_equity = float(cycle.ending_equity)
            else:
                current_equity += pnl
                
            if current_equity > peak_equity:
                peak_equity = current_equity
                
            if peak_equity > 0:
                drawdown = (peak_equity - current_equity) / peak_equity
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    
        win_rate = 0.0
        total_decisive_cycles = winning_cycles + losing_cycles
        if total_decisive_cycles > 0:
            win_rate = winning_cycles / total_decisive_cycles
            
        return PerformanceMetrics(
            total_cycles=total_cycles,
            total_trades=total_trades,
            winning_cycles=winning_cycles,
            losing_cycles=losing_cycles,
            win_rate=win_rate,
            total_pnl=total_pnl,
            max_drawdown=max_drawdown,
            peak_equity=peak_equity,
        )
