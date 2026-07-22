import asyncio
import uuid
import optuna
import os
import shutil
import logging
from datetime import datetime, timezone
import sys
from sqlalchemy import text

optuna.logging.set_verbosity(optuna.logging.INFO)
logging.getLogger("crypto_mas").setLevel(logging.CRITICAL)

sys.path.append("/home/tuncay/Notes/Projects/crypto-mas/src")

from crypto_mas.apps.api.routers.backtest import run_backtest_task
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.domain.repositories.backtest_result_repository import BacktestResultRepository

def cleanup_backtest(db, job_id: str):
    db.execute(text("DELETE FROM backtest_results WHERE job_id = :jid"), {"jid": job_id})
    db.execute(text("DELETE FROM paper_accounts WHERE name = :aname"), {"aname": f"backtest-{job_id}"})
    db.execute(text("DELETE FROM execution_logs WHERE account_name = :aname"), {"aname": f"backtest-{job_id}"})
    db.commit()
    archive_dir = f"data/backtests/{job_id}"
    if os.path.exists(archive_dir):
        shutil.rmtree(archive_dir)

# Default base config
BASE_CONFIG = {
    "bull_tactic": {"min_adx": 20.0, "rsi_threshold": 46.0, "max_dist_ema": 0.007, "tp_rsi": 72.0, "tp_dist_ema": 0.020, "max_rvol_pullback": 1.9},
    "bear_tactic": {"min_adx": 20.0, "rsi_threshold": 54.0, "min_dist_ema": 0.007, "max_dist_ema": 0.025, "tp_rsi": 28.0, "tp_dist_ema": -0.020, "max_rvol_pullback": 1.9},
    "sideways_tactic": {"rsi_oversold": 35.0, "rsi_overbought": 65.0, "min_adx": 0.0, "max_adx": 20.0}
}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"]

async def run_and_score(config: dict, start_time: datetime, end_time: datetime) -> float:
    db = SessionLocal()
    repo = BacktestResultRepository(db)
    job_id = str(uuid.uuid4())
    
    await run_backtest_task(
        job_id=job_id,
        exchange=Exchange.BINANCE,
        symbols=SYMBOLS,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        strategy_name="regime_adaptive",
        start_time=start_time,
        end_time=end_time,
        initial_balance=10000.0,
        risk_level=100,
        use_btc_shield=True,
        use_htf_shield=True,
        use_regime_shield=True,
        config_json=config
    )
    
    result = repo.get_by_job_id(job_id)
    score = 0.0
    if result and result.total_trades and result.total_trades > 3:
        equity = result.final_equity or 0.0
        win_rate = result.win_rate or 0.0
        score = equity + (win_rate * 1000.0)
    
    cleanup_backtest(db, job_id)
    db.close()
    return score

# --- BULL OPTIMIZATION ---
async def objective_bull(trial: optuna.Trial) -> float:
    config = BASE_CONFIG.copy()
    config["bull_tactic"] = {
        "min_adx": trial.suggest_float("min_adx", 15.0, 30.0, step=1.0),
        "rsi_threshold": trial.suggest_float("rsi_threshold", 35.0, 50.0, step=1.0),
        "tp_rsi": trial.suggest_float("tp_rsi", 70.0, 85.0, step=1.0),
        "max_dist_ema": trial.suggest_float("max_dist_ema", 0.005, 0.015, step=0.001),
        "tp_dist_ema": trial.suggest_float("tp_dist_ema", 0.015, 0.030, step=0.001),
        "max_rvol_pullback": trial.suggest_float("max_rvol_pullback", 1.2, 2.5, step=0.1)
    }
    start = datetime(2024, 2, 15, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 3, 1, 0, 0, tzinfo=timezone.utc) # 15 days
    return await run_and_score(config, start, end)

# --- BEAR OPTIMIZATION ---
async def objective_bear(trial: optuna.Trial) -> float:
    config = BASE_CONFIG.copy()
    config["bear_tactic"] = {
        "min_adx": trial.suggest_float("min_adx", 15.0, 30.0, step=1.0),
        "rsi_threshold": trial.suggest_float("rsi_threshold", 50.0, 65.0, step=1.0),
        "tp_rsi": trial.suggest_float("tp_rsi", 15.0, 30.0, step=1.0),
        "min_dist_ema": trial.suggest_float("min_dist_ema", 0.005, 0.015, step=0.001),
        "max_dist_ema": trial.suggest_float("max_dist_ema", 0.015, 0.035, step=0.001),
        "tp_dist_ema": trial.suggest_float("tp_dist_ema", -0.030, -0.015, step=0.001),
        "max_rvol_pullback": trial.suggest_float("max_rvol_pullback", 1.2, 2.5, step=0.1)
    }
    start = datetime(2024, 4, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2024, 4, 25, 0, 0, tzinfo=timezone.utc) # 15 days
    return await run_and_score(config, start, end)

# --- SIDEWAYS OPTIMIZATION ---
async def objective_sideways(trial: optuna.Trial) -> float:
    config = BASE_CONFIG.copy()
    config["sideways_tactic"] = {
        "min_adx": trial.suggest_float("min_adx", 0.0, 10.0, step=1.0),
        "max_adx": trial.suggest_float("max_adx", 15.0, 25.0, step=1.0),
        "rsi_oversold": trial.suggest_float("rsi_oversold", 25.0, 40.0, step=1.0),
        "rsi_overbought": trial.suggest_float("rsi_overbought", 60.0, 75.0, step=1.0)
    }
    start = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc) # 15 days
    return await run_and_score(config, start, end)

def run_study(name, objective_func, n_trials=5):
    print(f"\n{'='*40}")
    print(f"Starting Study: {name}")
    print(f"{'='*40}")
    study = optuna.create_study(study_name=name, direction="maximize")
    study.optimize(lambda t: asyncio.run(objective_func(t)), n_trials=n_trials, n_jobs=1)
    print(f"\nBest trial for {name}:")
    print(f"  Score: {study.best_trial.value}")
    for key, value in study.best_trial.params.items():
        print(f"  {key}: {value}")
    return study.best_trial.params

if __name__ == "__main__":
    bull_params = run_study("Bull_Regime_Optimization", objective_bull, n_trials=8)
    bear_params = run_study("Bear_Regime_Optimization", objective_bear, n_trials=8)
    sideways_params = run_study("Sideways_Regime_Optimization", objective_sideways, n_trials=8)
    
    print("\n\n" + "#"*40)
    print("FINAL MULTI-REGIME OPTIMAL PARAMETERS")
    print("#"*40)
    print("BULL TACTIC:", bull_params)
    print("BEAR TACTIC:", bear_params)
    print("SIDEWAYS TACTIC:", sideways_params)
