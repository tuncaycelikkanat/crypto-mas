"""
Walk-Forward Analysis Engine.

Divides a date range into N equal folds and runs an independent backtest
on each fold. Returns aggregate metrics to assess strategy robustness.

Performance improvement over the original:
- Historical data and features are fetched ONCE across all folds instead of
  being re-fetched N times. Each fold then slices the shared memory cache.
- The BacktestEngineService receives a pre-warmed InMemory cache so it skips
  the expensive DB backfill step.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

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
    sortino_ratio: float
    calmar_ratio: float
    profit_factor: float
    total_trades: int


@dataclass
class WalkForwardResult:
    n_folds: int
    folds: list[FoldResult] = field(default_factory=list)
    avg_sharpe: float = 0.0
    avg_sortino: float = 0.0
    avg_win_rate: float = 0.0
    avg_max_drawdown: float = 0.0
    avg_profit_factor: float = 0.0
    total_trades: int = 0

    def compute_aggregates(self) -> None:
        """Compute aggregate statistics across all folds."""
        if not self.folds:
            return
        n = len(self.folds)
        self.avg_sharpe = sum(f.sharpe_ratio for f in self.folds) / n
        self.avg_sortino = sum(f.sortino_ratio for f in self.folds) / n
        self.avg_win_rate = sum(f.win_rate for f in self.folds) / n
        self.avg_max_drawdown = sum(f.max_drawdown for f in self.folds) / n
        self.avg_profit_factor = sum(f.profit_factor for f in self.folds) / n
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
        risk_level: int = 100,
        use_btc_shield: bool = True,
        use_htf_shield: bool = True,
        use_regime_shield: bool = True,
    ) -> WalkForwardResult:
        """
        Run walk-forward analysis.

        Data is fetched and pre-calculated ONCE for the full range, then each
        fold receives a time-sliced view of the shared memory cache — no
        redundant network requests or feature recalculations.
        """
        from crypto_mas.domain.repositories.candle_repository import CandleRepository
        from crypto_mas.domain.repositories.feature_snapshot_repository import (
            FeatureSnapshotRepository,
        )
        from crypto_mas.services.backtesting.engine import BacktestEngineService
        from crypto_mas.services.backtesting.memory_cache import (
            InMemoryCandleRepository,
            InMemoryFeatureSnapshotRepository,
        )
        from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
        from crypto_mas.services.market_data_service.historical_fetcher import (
            HistoricalFetcherService,
        )
        from crypto_mas.services.market_data_service.provider_factory import (
            get_market_data_provider,
        )
        from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService

        result = WalkForwardResult(n_folds=n_folds)

        # ── Step 1: Fetch all data ONCE ──────────────────────────────────────
        provider = get_market_data_provider(exchange)
        fetcher = HistoricalFetcherService(provider=provider, db=self.db)

        delta = TradingCycleService._get_timedelta(timeframe)
        warmup_start = start_time - delta * 60

        fetch_symbols = list(set(symbols + ["BTCUSDT"])) if use_btc_shield else list(symbols)

        logger.info("[WalkForward] Fetching full date range: %s → %s", warmup_start.date(), end_time.date())
        await fetcher.backfill_universe(
            symbols=fetch_symbols,
            timeframe=timeframe,
            start_time=warmup_start,
            end_time=end_time,
        )

        htf_map = {
            Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
            Timeframe.FIFTEEN_MINUTES: Timeframe.FOUR_HOURS,
            Timeframe.ONE_HOUR: Timeframe.ONE_DAY,
            Timeframe.FOUR_HOURS: Timeframe.ONE_WEEK,
            Timeframe.ONE_DAY: Timeframe.ONE_MONTH,
        }
        htf = htf_map.get(timeframe)
        if htf and use_htf_shield:
            htf_warmup = start_time - TradingCycleService._get_timedelta(htf) * 60
            await fetcher.backfill_universe(
                symbols=fetch_symbols,
                timeframe=htf,
                start_time=htf_warmup,
                end_time=end_time,
            )

        # ── Step 2: Pre-calculate features ONCE ─────────────────────────────
        candle_db = CandleRepository(self.db)
        feature_db = FeatureSnapshotRepository(self.db)
        shared_candles = InMemoryCandleRepository(candle_db)
        shared_features = InMemoryFeatureSnapshotRepository(feature_db)

        # Load candles for all symbols into the shared cache
        for sym in fetch_symbols:
            shared_candles._ensure(
                f"{exchange.value}_{sym}_{timeframe.value}",
                exchange.value, sym, timeframe.value,
            )
            if htf:
                shared_candles._ensure(
                    f"{exchange.value}_{sym}_{htf.value}",
                    exchange.value, sym, htf.value,
                )

        feature_svc = FeaturePipelineService(self.db, candle_repo=shared_candles)
        for sym in fetch_symbols:
            candles = shared_candles.list_by_symbol(exchange.value, sym, timeframe.value)
            if candles:
                snaps = feature_svc.calculator.calculate(candles)
                if snaps:
                    shared_features.bulk_upsert(snaps)
            if htf:
                htf_candles = shared_candles.list_by_symbol(exchange.value, sym, htf.value)
                if htf_candles:
                    htf_snaps = feature_svc.calculator.calculate(htf_candles)
                    if htf_snaps:
                        shared_features.bulk_upsert(htf_snaps)

        logger.info("[WalkForward] Pre-computation done. Running %d folds.", n_folds)

        # ── Step 3: Run each fold with shared cache ───────────────────────────
        total_duration = end_time - start_time
        fold_duration = total_duration / n_folds

        for i in range(n_folds):
            fold_start = start_time + fold_duration * i
            fold_end = fold_start + fold_duration
            fold_job_id = f"{job_id}_fold_{i + 1}"

            logger.info(
                "[WalkForward] Fold %d/%d: %s → %s",
                i + 1, n_folds, fold_start.date(), fold_end.date(),
            )

            try:
                service = BacktestEngineService(self.db)
                bt_result = await service.run_backtest(
                    job_id=fold_job_id,
                    exchange=exchange,
                    symbols=symbols,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    start_time=fold_start,
                    end_time=fold_end,
                    initial_balance=initial_balance,
                    risk_level=risk_level,
                    use_btc_shield=use_btc_shield,
                    use_htf_shield=use_htf_shield,
                    use_regime_shield=use_regime_shield,
                    # Inject pre-warmed caches so the fold skips data fetching
                    _shared_candle_cache=shared_candles,
                    _shared_feature_cache=shared_features,
                )

                result.folds.append(
                    FoldResult(
                        fold=i + 1,
                        start_time=fold_start,
                        end_time=fold_end,
                        final_equity=float(bt_result.final_equity or initial_balance),
                        win_rate=float(bt_result.win_rate or 0.0),
                        max_drawdown=float(bt_result.max_drawdown or 0.0),
                        sharpe_ratio=float(bt_result.sharpe_ratio or 0.0),
                        sortino_ratio=float(bt_result.sortino_ratio or 0.0),
                        calmar_ratio=float(bt_result.calmar_ratio or 0.0),
                        profit_factor=float(bt_result.profit_factor or 0.0),
                        total_trades=bt_result.total_trades or 0,  # type: ignore
                    )
                )

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
                        sortino_ratio=0.0,
                        calmar_ratio=0.0,
                        profit_factor=0.0,
                        total_trades=0,
                    )
                )

        result.compute_aggregates()
        logger.info(
            "[WalkForward] Completed. avg_sharpe=%.3f avg_win=%.1f%% avg_dd=%.1f%%",
            result.avg_sharpe, result.avg_win_rate * 100, result.avg_max_drawdown * 100,
        )
        return result
