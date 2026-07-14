"""
Walk-Forward Analysis Engine.

Divides a date range into N equal folds and runs an independent backtest
on each fold. Returns aggregate metrics to assess strategy robustness.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

logger = logging.getLogger(__name__)


@dataclass
class FoldResult:
    fold: int
    start_time: datetime
    end_time: datetime
    final_equity: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    total_trades: int


@dataclass
class WalkForwardResult:
    n_folds: int
    folds: list[FoldResult] = field(default_factory=list)
    avg_sharpe: float = 0.0
    avg_win_rate: float = 0.0
    avg_max_drawdown: float = 0.0
    total_trades: int = 0

    def compute_aggregates(self) -> None:
        """Compute aggregate statistics across all folds."""
        if not self.folds:
            return
        n = len(self.folds)
        self.avg_sharpe = sum(f.sharpe_ratio for f in self.folds) / n
        self.avg_win_rate = sum(f.win_rate for f in self.folds) / n
        self.avg_max_drawdown = sum(f.max_drawdown for f in self.folds) / n
        self.total_trades = sum(f.total_trades for f in self.folds)


class WalkForwardEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def run(
        self,
        job_id: str,
        exchange: Exchange,
        symbols: list[str],
        timeframe: Timeframe,
        strategy_name: str,
        start_time: datetime,
        end_time: datetime,
        n_folds: int = 4,
        initial_balance: float = 10_000.0,
    ) -> WalkForwardResult:
        """Run walk-forward analysis by dividing the date range into n_folds.

        Args:
            job_id: Unique identifier for this walk-forward run.
            n_folds: Number of equal time slices to test independently.
            Other args mirror BacktestEngineService.run_backtest().

        Returns:
            WalkForwardResult with per-fold and aggregate statistics.
        """
        total_duration = end_time - start_time
        fold_duration = total_duration / n_folds

        result = WalkForwardResult(n_folds=n_folds)

        for i in range(n_folds):
            fold_start = start_time + fold_duration * i
            fold_end = fold_start + fold_duration
            fold_job_id = f"{job_id}_fold_{i + 1}"

            logger.info(
                "[WalkForward] Fold %d/%d: %s → %s",
                i + 1, n_folds, fold_start.date(), fold_end.date(),
            )

            try:
                backtest_service = BacktestEngineService(self.db)
                bt_result = await backtest_service.run_backtest(
                    job_id=fold_job_id,
                    exchange=exchange,
                    symbols=symbols,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    start_time=fold_start,
                    end_time=fold_end,
                    initial_balance=initial_balance,
                )

                fold_result = FoldResult(
                    fold=i + 1,
                    start_time=fold_start,
                    end_time=fold_end,
                    final_equity=float(bt_result.final_equity or initial_balance),
                    win_rate=float(bt_result.win_rate or 0.0),
                    max_drawdown=float(bt_result.max_drawdown or 0.0),
                    sharpe_ratio=float(bt_result.sharpe_ratio or 0.0),
                    total_trades=bt_result.total_trades or 0,
                )
                result.folds.append(fold_result)

            except Exception as exc:
                logger.error("[WalkForward] Fold %d failed: %s", i + 1, exc)
                result.folds.append(
                    FoldResult(
                        fold=i + 1,
                        start_time=fold_start,
                        end_time=fold_end,
                        final_equity=initial_balance,
                        win_rate=0.0,
                        max_drawdown=0.0,
                        sharpe_ratio=0.0,
                        total_trades=0,
                    )
                )

        result.compute_aggregates()
        logger.info(
            "[WalkForward] Completed. avg_sharpe=%.3f avg_win_rate=%.1f%% avg_dd=%.1f%%",
            result.avg_sharpe, result.avg_win_rate * 100, result.avg_max_drawdown * 100,
        )
        return result
