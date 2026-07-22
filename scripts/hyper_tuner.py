import asyncio
import uuid
import optuna
import os
import shutil
import logging
from datetime import datetime, timezone
import sys
from sqlalchemy import text

# Configure optuna logging
optuna.logging.set_verbosity(optuna.logging.INFO)
# Mute application logs to keep console clean
logging.getLogger("crypto_mas").setLevel(logging.CRITICAL)

sys.path.append("/home/tuncay/Notes/Projects/crypto-mas/src")

from crypto_mas.apps.api.routers.backtest import run_backtest_task
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.domain.repositories.backtest_result_repository import BacktestResultRepository

def cleanup_backtest(db, job_id: str):
    """Deletes backtest artifacts and DB entries to prevent DB bloat during tuning."""
    db.execute(text("DELETE FROM backtest_results WHERE job_id = :jid"), {"jid": job_id})
    db.execute(text("DELETE FROM paper_accounts WHERE name = :aname"), {"aname": f"backtest-{job_id}"})
    db.execute(text("DELETE FROM execution_logs WHERE account_name = :aname"), {"aname": f"backtest-{job_id}"})
    db.commit()
    
    archive_dir = f"data/backtests/{job_id}"
    if os.path.exists(archive_dir):
        shutil.rmtree(archive_dir)

async def objective_async(trial: optuna.Trial) -> float:
    db = SessionLocal()
    repo = BacktestResultRepository(db)
    job_id = str(uuid.uuid4())
    
    # Define search space
    min_adx = trial.suggest_float("min_adx", 20.0, 35.0, step=1.0)
    
    # Bull Tactic specific
    bull_rsi_threshold = trial.suggest_float("bull_rsi_threshold", 35.0, 50.0, step=1.0)
    bull_tp_rsi = trial.suggest_float("bull_tp_rsi", 70.0, 85.0, step=1.0)
    
    # Distance to EMA
    max_dist_ema = trial.suggest_float("max_dist_ema", 0.004, 0.015, step=0.001)
    bull_tp_dist_ema = trial.suggest_float("bull_tp_dist_ema", 0.012, 0.025, step=0.001)
    
    # Shields & Risk
    max_rvol_pullback = trial.suggest_float("max_rvol_pullback", 1.1, 2.0, step=0.1)
    
    config = {
        "bull_tactic": {
            "min_adx": min_adx,
            "rsi_threshold": bull_rsi_threshold,
            "max_dist_ema": max_dist_ema,
            "tp_rsi": bull_tp_rsi,
            "tp_dist_ema": bull_tp_dist_ema,
            "max_rvol_pullback": max_rvol_pullback
        },
        "bear_tactic": {
            "min_adx": min_adx,
            "rsi_threshold": 100 - bull_rsi_threshold, # Mirror
            "max_dist_ema": max_dist_ema,
            "tp_rsi": 100 - bull_tp_rsi, # Mirror
            "tp_dist_ema": bull_tp_dist_ema,
            "max_rvol_pullback": max_rvol_pullback
        },
        "sideways_tactic": {"rsi_oversold": 35.0, "rsi_overbought": 65.0}
    }
    
    # Top highly liquid symbols to ensure representativeness
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
    
    # Run backtest for a smaller 7-day subset for fast evaluation
    await run_backtest_task(
        job_id=job_id,
        exchange=Exchange.BINANCE,
        symbols=symbols,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        strategy_name="regime_adaptive",
        start_time=datetime(2026, 6, 23, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 6, 30, 0, 0, tzinfo=timezone.utc),
        initial_balance=10000.0,
        risk_level=100,
        use_btc_shield=True,
        use_htf_shield=True,
        use_regime_shield=True,
        config_json=config
    )
    
    result = repo.get_by_job_id(job_id)
    
    score = 0.0
    if result and result.total_trades and result.total_trades > 5:
        equity = result.final_equity or 0.0
        win_rate = result.win_rate or 0.0
        
        # We want to maximize equity primarily, but penalize bad win rates.
        # Score = Final Equity + (Win Rate * 1000)
        # e.g. $10050 equity + 0.60 WR * 1000 = 10050 + 600 = 10650
        score = equity + (win_rate * 1000.0)
    else:
        # Penalize if not enough trades were taken
        score = 0.0
        
    # Cleanup to save disk/DB space
    cleanup_backtest(db, job_id)
    db.close()
    
    return score

def objective(trial: optuna.Trial) -> float:
    return asyncio.run(objective_async(trial))

if __name__ == "__main__":
    print("Starting Optuna Hyperparameter Optimization...")
    print("Objective: Maximize [Final Equity + (Win Rate * 1000)]")
    
    # Use an SQLite backend to save the study progress, enabling pause/resume
    study_name = "kanas_optimization"
    storage_url = "sqlite:///optuna_study.db"
    
    study = optuna.create_study(
        study_name=study_name, 
        storage=storage_url, 
        load_if_exists=True,
        direction="maximize"
    )
    
    try:
        # Run 10 trials
        study.optimize(objective, n_trials=10, n_jobs=1)
    except KeyboardInterrupt:
        print("\nOptimization interrupted by user.")
        
    print("\n==============================")
    print("Best trial:")
    trial = study.best_trial
    print(f"  Value (Score): {trial.value}")
    print("  Params: ")
    for key, value in trial.params.items():
        print(f"    {key}: {value}")
