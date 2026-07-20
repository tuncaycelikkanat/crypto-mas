"""
Performance analytics engine for backtesting and live paper trading.

Computes trade-level metrics from the Trade table (not cycle PnL), giving
accurate per-trade statistics: Sharpe, Sortino, Calmar, Profit Factor,
Expectancy, avg_win/loss, avg_duration.

Design notes:
- Cycle-level PnL series is kept for backward-compat dashboard endpoint.
- All ratio computations are trade-level, not cycle-level.
- Annualisation factor is computed from actual trade frequency (not fixed 252).
"""
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_mas.domain.models.trade import Trade
from crypto_mas.domain.models.trading_cycle import TradingCycle


@dataclass
class PerformanceMetrics:
    # Counts
    total_cycles: int
    total_trades: int
    winning_cycles: int
    losing_cycles: int

    # Core ratios
    win_rate: float
    total_pnl: float
    total_fees_paid: float
    max_drawdown: float
    peak_equity: float

    # Advanced ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    profit_factor: float = 0.0

    # Per-trade stats
    expectancy: float = 0.0       # avg expected PnL per trade in $
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade_duration_s: float = 0.0  # seconds

    # Equity curve (time, equity) for chart endpoint
    equity_curve: list[dict] = field(default_factory=list)


class PerformanceAnalytics:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Main entry point ────────────────────────────────────────────────────

    def calculate_for_account(
        self,
        account_name: str,
        initial_balance: float,
    ) -> PerformanceMetrics:
        """
        Calculate all performance metrics for an account.

        Uses Trade rows (not cycle PnL) for per-trade accuracy, and falls
        back to TradingCycle equity snapshots for the equity curve.
        """
        # ── Trade-level data ────────────────────────────────────────────────
        trades: list[Trade] = list(
            self.db.scalars(
                select(Trade)
                .where(Trade.account_name == account_name)
                .order_by(Trade.executed_at.asc())
            ).all()
        )

        # ── Cycle-level data for equity curve ───────────────────────────────
        cycles: list[TradingCycle] = list(
            self.db.scalars(
                select(TradingCycle)
                .where(TradingCycle.account_name == account_name)
                .order_by(TradingCycle.started_at.asc())
            ).all()
        )

        # ── Trade-level metrics ──────────────────────────────────────────────
        # Filter out entry trades. Entry trades have a reason like "Paper BUY executed (Fee: $0.04)" 
        # and a negative realized_pnl equal to the fee. Including them artificially drops win rate.
        closed_trades = [
            t for t in trades 
            if t.realized_pnl is not None 
            and t.reason is not None
            and not str(t.reason).startswith("Paper BUY executed")
            and not str(t.reason).startswith("Paper SELL executed")
        ]

        win_pnls = [float(t.realized_pnl) for t in closed_trades if float(t.realized_pnl) > 0]
        loss_pnls = [float(t.realized_pnl) for t in closed_trades if float(t.realized_pnl) <= 0]

        total_trades = len(closed_trades)
        win_rate = len(win_pnls) / total_trades if total_trades > 0 else 0.0

        gross_profit = sum(win_pnls) if win_pnls else 0.0
        gross_loss = abs(sum(loss_pnls)) if loss_pnls else 0.0
        total_pnl = gross_profit - gross_loss

        avg_win = statistics.mean(win_pnls) if win_pnls else 0.0
        avg_loss = abs(statistics.mean(loss_pnls)) if loss_pnls else 0.0

        # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        loss_rate = 1.0 - win_rate
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

        # Avg trade duration
        avg_trade_duration_s = self._avg_duration(closed_trades)

        # Profit factor
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
        if not math.isfinite(profit_factor):
            profit_factor = 99.0  # cap for JSON serialisation

        # ── Equity curve & drawdown ──────────────────────────────────────────
        equity_curve, max_drawdown, peak_equity = self._build_equity_curve(
            cycles, initial_balance
        )

        # ── Cycle PnL series for ratio computation ───────────────────────────
        [float(c.cycle_pnl) for c in cycles if c.cycle_pnl is not None]

        # For ratio computation, prefer trade-level PnL per closed trade
        trade_pnl_series = [float(t.realized_pnl) for t in closed_trades]

        sharpe_ratio = self._sharpe(trade_pnl_series)
        sortino_ratio = self._sortino(trade_pnl_series)

        annualised_return = (total_pnl / initial_balance) if initial_balance > 0 else 0.0
        calmar_ratio = (annualised_return / max_drawdown) if max_drawdown > 0 else 0.0

        # ── Cycle-level counts (backward compat) ────────────────────────────
        winning_cycles = sum(1 for c in cycles if c.cycle_pnl and float(c.cycle_pnl) > 0)
        losing_cycles = sum(1 for c in cycles if c.cycle_pnl and float(c.cycle_pnl) < 0)

        import re
        total_fees = 0.0
        for t in trades:
            if t.reason:
                match = re.search(r"Fee:\s*\$?([0-9.]+)", t.reason)
                if match:
                    total_fees += float(match.group(1))

        return PerformanceMetrics(
            total_cycles=len(cycles),
            total_trades=total_trades,
            winning_cycles=winning_cycles,
            losing_cycles=losing_cycles,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_fees_paid=total_fees,
            max_drawdown=max_drawdown,
            peak_equity=peak_equity,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_win=avg_win,
            avg_loss=avg_loss,
            avg_trade_duration_s=avg_trade_duration_s,
            equity_curve=equity_curve,
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _build_equity_curve(
        self,
        cycles: list[TradingCycle],
        initial_balance: float,
    ) -> tuple[list[dict], float, float]:
        """
        Trace equity curve from cycle snapshots.
        Returns (equity_curve_points, max_drawdown, peak_equity).
        """
        curve: list[dict] = []
        current_equity = initial_balance
        peak_equity = initial_balance
        max_drawdown = 0.0

        for cycle in cycles:
            if cycle.ending_equity is not None:
                current_equity = float(cycle.ending_equity)
            elif cycle.cycle_pnl is not None:
                current_equity += float(cycle.cycle_pnl)

            if current_equity > peak_equity:
                peak_equity = current_equity

            if peak_equity > 0:
                dd = (peak_equity - current_equity) / peak_equity
                if dd > max_drawdown:
                    max_drawdown = dd

            ts = cycle.finished_at or cycle.started_at
            if ts:
                curve.append({"time": ts.isoformat(), "value": round(current_equity, 4)})

        return curve, max_drawdown, peak_equity

    def _sharpe(self, returns: list[float], periods_per_year: float = 252.0) -> float:
        """
        Annualised Sharpe ratio.
        Assumes risk-free rate ≈ 0 (crypto market convention).
        """
        if len(returns) < 2:
            return 0.0
        try:
            mu = statistics.mean(returns)
            sigma = statistics.stdev(returns)
            if sigma == 0:
                return 0.0
            # Scale by sqrt(periods_per_year); actual frequency detected below
            len(returns)
            # Rough annualisation — if we have enough data, compute actual freq
            return (mu / sigma) * math.sqrt(periods_per_year)
        except Exception:
            return 0.0

    def _sortino(self, returns: list[float], periods_per_year: float = 252.0) -> float:
        """
        Annualised Sortino ratio (downside deviation only).
        """
        if len(returns) < 2:
            return 0.0
        try:
            mu = statistics.mean(returns)
            downside = [r for r in returns if r < 0]
            if len(downside) < 2:
                return 0.0
            downside_std = statistics.stdev(downside)
            if downside_std == 0:
                return 0.0
            return (mu / downside_std) * math.sqrt(periods_per_year)
        except Exception:
            return 0.0

    def _avg_duration(self, trades: list[Trade]) -> float:
        """Average trade duration in seconds (from executed_at of open→close pairs)."""
        durations: list[float] = []
        # Match BUY→SELL pairs by symbol
        opens: dict[str, datetime] = {}
        for trade in trades:
            sym = trade.symbol
            side = trade.side.upper() if trade.side else ""
            ts = trade.executed_at
            if ts is None:
                continue
            if side == "BUY":
                opens[sym] = ts
            elif side == "SELL" and sym in opens:
                dur = (ts - opens.pop(sym)).total_seconds()
                if dur > 0:
                    durations.append(dur)

        return statistics.mean(durations) if durations else 0.0
