# ruff: noqa: B023
import asyncio
import logging
import uuid

import optuna
from sqlalchemy.orm import Session

from crypto_mas.domain.models.backtest_result import BacktestResult
from crypto_mas.engine.optimization.composite_score import FitnessCalculator
from crypto_mas.engine.optimization.schemas import Fold
from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

logger = logging.getLogger(__name__)

class WalkForwardOptimizer:
    def __init__(self, db: Session, engine_service: BacktestEngineService):
        self.db = db
        self.engine_service = engine_service
        
    def _run_async(self, coro):
        try:
            asyncio.get_running_loop()
            in_loop = True
        except RuntimeError:
            in_loop = False

        if not in_loop:
            return asyncio.run(coro)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()

    def optimize(
        self,
        folds: list[Fold],
        exchange: Exchange,
        symbols: list[str],
        timeframe: Timeframe,
        strategy_name: str,
        n_trials: int = 50,
        min_trades: int = 30
    ) -> list[BacktestResult]:
        
        test_results = []
        
        for fold in folds:
            logger.info(f"\n{'='*50}\nStarting Walk-Forward Fold {fold.fold_id}\n{'='*50}")
            logger.info(f"Train: {fold.train_start} -> {fold.train_end}")
            logger.info(f"Test:  {fold.test_start} -> {fold.test_end}")
            
            # --- 1. Pre-fetch Data for Train (Memory Caching) ---
            from crypto_mas.domain.repositories.candle_repository import CandleRepository
            from crypto_mas.domain.repositories.feature_snapshot_repository import (
                FeatureSnapshotRepository,
            )
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
            from crypto_mas.services.trading_cycle_service.utils import get_timedelta
            
            shared_candle_cache = InMemoryCandleRepository(CandleRepository(self.db))
            shared_feature_cache = InMemoryFeatureSnapshotRepository(FeatureSnapshotRepository(self.db))
            
            logger.info("Pre-warming memory caches for Train Fold...")
            provider = get_market_data_provider(exchange)
            fetcher = HistoricalFetcherService(provider=provider, db=self.db)
            
            async def warmup():  # noqa: B023
                delta = get_timedelta(timeframe)
                fetch_symbols = list(set(symbols + ["BTCUSDT"]))
                await fetcher.backfill_universe(fetch_symbols, timeframe, fold.train_start - delta*60, fold.train_end)
                
                temp_feature_svc = FeaturePipelineService(self.db, candle_repo=CandleRepository(self.db), feature_repo=FeatureSnapshotRepository(self.db))
                for sym in fetch_symbols:
                    all_candles = CandleRepository(self.db).list_by_symbol(exchange.value, sym, timeframe.value, end_time=fold.train_end, limit=None)
                    if all_candles:
                        all_snaps = temp_feature_svc.calculator.calculate(all_candles)
                        if all_snaps:
                            shared_feature_cache.bulk_upsert(all_snaps)
                            
            self._run_async(warmup())
            logger.info("Memory caches warmed up. Starting Optuna study...")
            
            def objective(trial):
                # Restricted Search Space to avoid overfitting
                tp_mult = trial.suggest_float("tp_mult", 1.2, 2.5, step=0.1)
                sl_mult = trial.suggest_float("sl_mult", 0.8, 1.8, step=0.1)
                breakdown_tp_mult = trial.suggest_float("breakdown_tp_mult", 1.0, 2.0, step=0.1)
                breakdown_sl_mult = trial.suggest_float("breakdown_sl_mult", 0.8, 1.5, step=0.1)
                max_dist_ema = trial.suggest_float("max_dist_ema", 0.020, 0.040, step=0.005)
                
                config_json = {
                    "tp_mult": tp_mult,
                    "sl_mult": sl_mult,
                    "breakdown_tp_mult": breakdown_tp_mult,
                    "breakdown_sl_mult": breakdown_sl_mult,
                    "max_dist_ema": max_dist_ema,
                }
                
                run_id = uuid.uuid4().hex[:6]
                job_id = f"wfo-train-f{fold.fold_id}-t{trial.number}-{run_id}"
                
                async def run_trial():  # noqa: B023
                    return await self.engine_service.run_backtest(
                        job_id=job_id,
                        exchange=exchange,
                        symbols=symbols,
                        timeframe=timeframe,
                        strategy_name=strategy_name,
                        start_time=fold.train_start,
                        end_time=fold.train_end,
                        initial_balance=10000.0,
                        config_json=config_json,
                        _shared_candle_cache=shared_candle_cache,
                        _shared_feature_cache=shared_feature_cache
                    )
                    
                result = self._run_async(run_trial())
                score = FitnessCalculator.calculate_composite_score(result, min_trades=min_trades)
                
                return score
                
            study = optuna.create_study(
                direction="maximize",
                pruner=optuna.pruners.MedianPruner(n_warmup_steps=5)
            )
            
            # Reduce verbosity
            optuna.logging.set_verbosity(optuna.logging.WARNING)
            study.optimize(objective, n_trials=n_trials)
            
            logger.info(f"Fold {fold.fold_id} Best Params: {study.best_params}")
            logger.info(f"Fold {fold.fold_id} Best Train Score: {study.best_value}")
            
            # --- 2. Sensitivity Analysis (Optional / Log only for now) ---
            # ...
            
            # --- 3. Evaluate Best Params on Test Fold ---
            logger.info(f"\nEvaluating Fold {fold.fold_id} Best Params on UNSEEN TEST DATA...")
            test_run_id = uuid.uuid4().hex[:6]
            test_job_id = f"wfo-test-f{fold.fold_id}-{test_run_id}"
            
            async def run_test():  # noqa: B023
                return await self.engine_service.run_backtest(
                    job_id=test_job_id,
                    exchange=exchange,
                    symbols=symbols,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    start_time=fold.test_start,
                    end_time=fold.test_end,
                    initial_balance=10000.0,
                    config_json=study.best_params,
                )
                
            test_result = self._run_async(run_test())
            test_score = FitnessCalculator.calculate_composite_score(test_result, min_trades=1)
            
            logger.info(f"Fold {fold.fold_id} Test Score: {test_score}, PnL: {test_result.final_equity}, WinRate: {test_result.win_rate}")
            test_results.append(test_result)
            
        return test_results
