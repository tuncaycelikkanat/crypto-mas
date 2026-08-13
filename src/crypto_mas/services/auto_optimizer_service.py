# ruff: noqa: B023
import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime

import optuna
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from crypto_mas.engine.optimization.composite_score import FitnessCalculator
from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.domain.models.optimization_history import OptimizationHistory

logger = logging.getLogger(__name__)

# Config save path
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(DATA_DIR, 'current_optimal_config.json')


class AutoOptimizerService:
    def __init__(self, db: Session):
        self.db = db
        self.engine_service = BacktestEngineService(db)

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

    def run_optimization_job(self, symbols: list[str], timeframe: Timeframe, strategy_name: str = "regime_adaptive", lookback_months: int = 3, n_trials: int = 50, triggered_by: str = "SCHEDULED"):
        """
        Runs optimization on the past `lookback_months` to find the best parameters for LIVE trading,
        and saves them to a JSON config file and DB.
        """
        logger.info("Starting %s Auto-Optimization for %s on %s symbols over the last %s months.", triggered_by, strategy_name, len(symbols), lookback_months)
        
        # 0. Initialize DB History Record
        history_record = OptimizationHistory(
            status="RUNNING",
            triggered_by=triggered_by,
            strategy_name=strategy_name,
            symbols_json=symbols,
            lookback_months=lookback_months
        )
        self.db.add(history_record)
        self.db.commit()
        self.db.refresh(history_record)
        
        # Intercept magic symbol lists like AUTO_GAINERS to train on historically volatile assets
        if symbols and symbols[0] in ("AUTO_GAINERS", "HIDDEN_GEMS"):
            logger.info("Optimizer intercepted '%s' magic symbol. Using High-Beta Dynamic Gainers Universe for backtest training.", symbols[0])
            symbols = ["WIFUSDT", "PEPEUSDT", "FLOKIUSDT", "SHIBUSDT", "DOGEUSDT"]
        
        now = datetime.now(UTC)
        train_start = now - relativedelta(months=lookback_months)
        train_end = now
        exchange = Exchange.BINANCE
        
        # 1. Pre-warm memory caches for speed
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
        
        provider = get_market_data_provider(exchange)
        fetcher = HistoricalFetcherService(provider=provider, db=self.db)
        
        async def warmup():  # noqa: B023
            delta = get_timedelta(timeframe)
            fetch_symbols = list(set(symbols + ["BTCUSDT"]))
            await fetcher.backfill_universe(fetch_symbols, timeframe, train_start - delta*60, train_end)
            
            temp_feature_svc = FeaturePipelineService(self.db, candle_repo=CandleRepository(self.db), feature_repo=FeatureSnapshotRepository(self.db))
            for sym in fetch_symbols:
                all_candles = CandleRepository(self.db).list_by_symbol(exchange.value, sym, timeframe.value, end_time=train_end, limit=None)
                if all_candles:
                    all_snaps = temp_feature_svc.calculator.calculate(all_candles)
                    if all_snaps:
                        shared_feature_cache.bulk_upsert(all_snaps)
                        
        self._run_async(warmup())
        logger.info("Memory caches warmed up. Starting live adaptation trials...")

        def objective(trial):
            # Widened search space for high-beta / highly volatile tokens
            tp_mult = trial.suggest_float("tp_mult", 1.5, 6.0, step=0.1)
            sl_mult = trial.suggest_float("sl_mult", 0.5, 3.0, step=0.1)
            breakdown_tp_mult = trial.suggest_float("breakdown_tp_mult", 1.0, 4.0, step=0.1)
            breakdown_sl_mult = trial.suggest_float("breakdown_sl_mult", 0.5, 2.0, step=0.1)
            max_dist_ema = trial.suggest_float("max_dist_ema", 0.010, 0.150, step=0.005)
            
            config_json = {
                "tp_mult": tp_mult,
                "sl_mult": sl_mult,
                "breakdown_tp_mult": breakdown_tp_mult,
                "breakdown_sl_mult": breakdown_sl_mult,
                "max_dist_ema": max_dist_ema,
            }
            
            run_id = uuid.uuid4().hex[:6]
            job_id = f"auto-opt-t{trial.number}-{run_id}"
            
            async def run_trial():  # noqa: B023
                return await self.engine_service.run_backtest(
                    job_id=job_id,
                    exchange=exchange,
                    symbols=symbols,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    start_time=train_start,
                    end_time=train_end,
                    initial_balance=10000.0,
                    config_json=config_json,
                    _shared_candle_cache=shared_candle_cache,
                    _shared_feature_cache=shared_feature_cache
                )
                
            result = self._run_async(run_trial())
            score = FitnessCalculator.calculate_composite_score(result, min_trades=10)
            return score
            
        try:
            study = optuna.create_study(direction="maximize", pruner=optuna.pruners.MedianPruner(n_warmup_steps=5))
            optuna.logging.set_verbosity(optuna.logging.WARNING)
            study.optimize(objective, n_trials=n_trials)
            
            best_params = study.best_params
            logger.info("Auto-Optimization complete! Best params found: %s", best_params)
            
            # Save to DB
            history_record.status = "COMPLETED"
            history_record.best_params_json = best_params
            history_record.completed_at = datetime.now(UTC)
            self.db.commit()
            
            # Save to JSON for quick read by scheduler
            with open(CONFIG_PATH, "w") as f:
                json.dump({
                    "last_optimized_at": now.isoformat(),
                    "strategy": strategy_name,
                    "symbols": symbols,
                    "best_params": best_params,
                    "history_id": history_record.id
                }, f, indent=4)
                
            logger.info("New optimal config saved to DB and %s", CONFIG_PATH)
            return best_params
        except Exception as e:
            logger.error("Auto-Optimization failed: %s", e)
            history_record.status = "FAILED"
            history_record.error_message = str(e)
            history_record.completed_at = datetime.now(UTC)
            self.db.commit()
            raise e

