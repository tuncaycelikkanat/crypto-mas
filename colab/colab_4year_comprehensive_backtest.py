"""
colab_4year_comprehensive_backtest.py — Institutional 4.5-Year (54 Months & 230+ Weeks, 2022-01-01 -> 2026-07-01) WFO & Sensitivity Suite.

Usage in Google Colab or CLI:
    python colab/colab_4year_comprehensive_backtest.py --mode all
    python colab/colab_4year_comprehensive_backtest.py --mode monthly
    python colab/colab_4year_comprehensive_backtest.py --mode weekly
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import UTC, datetime, timezone
from typing import Any

try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# Add project root and src/ to sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_src_dir = os.path.join(_project_root, 'src')
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

os.environ.setdefault("DATABASE_URL", "sqlite:///crypto_mas.db")

from crypto_mas.domain.models.backtest_result import BacktestResult
from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.engine.optimization.fold_generator import Fold, FoldGenerator
from crypto_mas.engine.optimization.walk_forward_optimizer import WalkForwardOptimizer
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.infrastructure.db.session import SessionLocal, engine
from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

# Auto-create SQLite database tables if they do not exist
Base.metadata.create_all(bind=engine)

# Institutional 4-Year Symbol Pools
SYMBOL_POOLS = {
    "TOP10": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT", "DOTUSDT"],
    "L1_BLUECHIP": ["SOLUSDT", "AVAXUSDT", "NEARUSDT", "INJUSDT", "APTUSDT"],
    "AI_HYPE": ["FETUSDT", "RNDRUSDT", "NEARUSDT", "INJUSDT", "OCEANUSDT"],
    "MEME_ALPHA": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "FLOKIUSDT"],
    "DEFI_MAJOR": ["LINKUSDT", "UNIUSDT", "AAVEUSDT", "MKRUSDT"],
}


def create_results_dir():
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    return results_dir


def evaluate_pool(
    optimizer: WalkForwardOptimizer,
    pool_name: str,
    symbols: list[str],
    folds: list[Fold],
    timeframe: Timeframe,
    strategy_name: str,
    granularity: str = "monthly",
    n_jobs: int = 1,
    n_trials: int | None = None,
) -> dict[str, Any]:
    print(f"\n====================================================================")
    print(f"🚀 [{granularity.upper()}] Running 4-Year WFO for Pool: {pool_name} ({len(symbols)} coins)")
    print(f"    Total Rolling Periods: {len(folds)}")
    print(f"====================================================================")

    try:
        # Run Optuna optimization on rolling folds
        effective_trials = n_trials if n_trials is not None else (15 if granularity == "monthly" else 8)
        test_results = optimizer.optimize(
            folds=folds,
            exchange=Exchange.BINANCE,
            symbols=symbols,
            timeframe=timeframe,
            strategy_name=strategy_name,
            n_trials=effective_trials,
            min_trades=5,
            n_jobs=n_jobs,
        )

        total_net_profit = 0.0
        total_trades = 0
        periods_detail = []
        positive_periods = 0

        for idx, res in enumerate(test_results):
            net_profit = float(res.final_equity - res.initial_balance) if res.final_equity else 0.0
            trades = int(res.total_trades) if res.total_trades else 0
            win_rate = float(res.win_rate) if res.win_rate else 0.0
            total_net_profit += net_profit
            total_trades += trades

            if net_profit > 0:
                positive_periods += 1

            if granularity == "monthly":
                period_label = f"{folds[idx].test_start.strftime('%Y-%m')}"
            else:
                period_label = f"W{idx+1}: {folds[idx].test_start.strftime('%Y-%m-%d')} -> {folds[idx].test_end.strftime('%m-%d')}"

            periods_detail.append({
                "period_index": idx + 1,
                "period_label": period_label,
                "net_profit": round(net_profit, 2),
                "trades": trades,
                "win_rate": round(win_rate, 2),
                "oos_status": "PROFIT" if net_profit >= 0 else "DRAWDOWN",
            })

        consistency_ratio = (positive_periods / len(test_results) * 100.0) if test_results else 0.0
        print(f"\n╔═════════════════════════════════════════════════════════════════╗", flush=True)
        print(f"║ ✅ HAVUZ TAMAMLANDI: {pool_name:<20}                        ║", flush=True)
        print(f"║    • 4 Yıllık Toplam PnL  : ${total_net_profit:+,.2f}            ║", flush=True)
        print(f"║    • Toplam İşlem Sayısı  : {total_trades:<20}               ║", flush=True)
        print(f"║    • Tutarlılık Oranı     : %{consistency_ratio:<19.1f}              ║", flush=True)
        print(f"╚═════════════════════════════════════════════════════════════════╝\n", flush=True)

        return {
            "pool_name": pool_name,
            "strategy": strategy_name,
            "granularity": granularity,
            "total_4_year_profit_usd": round(total_net_profit, 2),
            "total_trades": total_trades,
            "consistency_ratio_pct": round(consistency_ratio, 1),
            "total_periods_evaluated": len(periods_detail),
            "periods_detail": periods_detail,
        }

    except Exception as exc:
        print(f"❌ Error in pool {pool_name}: {exc}")
        return {
            "pool_name": pool_name,
            "error": str(exc),
        }


def run_4year_comprehensive_suite(mode: str = "all", max_folds: int | None = None, n_jobs: int = 1, part: str = "all", n_trials: int | None = None):
    db = SessionLocal()
    engine_service = BacktestEngineService(db)
    optimizer = WalkForwardOptimizer(db, engine_service)

    # Modular 4.5-Year Breakdown (Zero OOS Gaps, Zero Overlaps)
    if part == "1":
        start_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        file_suffix = "_part1"
    elif part == "2":
        start_date = datetime(2022, 10, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        file_suffix = "_part2"
    elif part == "3":
        start_date = datetime(2023, 10, 1, tzinfo=timezone.utc)
        end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        file_suffix = "_part3"
    elif part == "4":
        start_date = datetime(2024, 10, 1, tzinfo=timezone.utc)
        end_date = datetime(2026, 7, 1, tzinfo=timezone.utc)
        file_suffix = "_part4"
    else:
        start_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2026, 7, 1, tzinfo=timezone.utc)
        file_suffix = ""

    timeframe = Timeframe.ONE_HOUR
    strategy_name = "regime_adaptive"

    results_dir = create_results_dir()

    print("====================================================================")
    print("      CRYPTO MAS — 4.5-YEAR COMPREHENSIVE BACKTEST SUITE           ")
    print(f"      Period: {start_date.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}")
    print(f"      Mode:   {mode.upper()}")
    print("====================================================================")

    monthly_results = []
    weekly_results = []

    # 1. Monthly Granular Breakdown (48 Months)
    if mode in ["monthly", "all"]:
        print("\n--- Generating Rolling Monthly Folds (3M Train / 1M Test) ---")
        monthly_folds = FoldGenerator.generate_rolling_folds(
            start_date=start_date,
            end_date=end_date,
            train_months=3,
            test_months=1,
        )
        if max_folds is not None:
            monthly_folds = monthly_folds[:max_folds]
        print(f"Generated {len(monthly_folds)} rolling out-of-sample monthly periods.")

        for pool_name, symbols in SYMBOL_POOLS.items():
            res = evaluate_pool(optimizer, pool_name, symbols, monthly_folds, timeframe, strategy_name, granularity="monthly", n_jobs=n_jobs, n_trials=n_trials)
            monthly_results.append(res)

        monthly_path = os.path.join(results_dir, f"4year_monthly_wfo{file_suffix}.json")
        with open(monthly_path, "w", encoding="utf-8") as f:
            json.dump({"mode": "monthly", "period": f"2022-2026 (Part {part})", "results": monthly_results}, f, indent=2)
        print(f"💾 Saved monthly WFO report to: {monthly_path}")

    # 2. Weekly Granular Breakdown (Hafta Hafta)
    if mode in ["weekly", "all"]:
        print("\n--- Generating Rolling Weekly Folds (4W Train / 1W Test) ---")
        weekly_folds = FoldGenerator.generate_weekly_rolling_folds(
            start_date=start_date,
            end_date=end_date,
            train_weeks=4,
            test_weeks=1,
            step_weeks=1,
        )
        if max_folds is not None:
            weekly_folds = weekly_folds[:max_folds]
        print(f"Generated {len(weekly_folds)} rolling out-of-sample weekly periods.")

        for pool_name, symbols in SYMBOL_POOLS.items():
            res = evaluate_pool(optimizer, pool_name, symbols, weekly_folds, timeframe, strategy_name, granularity="weekly", n_jobs=n_jobs, n_trials=n_trials)
            weekly_results.append(res)

        weekly_path = os.path.join(results_dir, f"4year_weekly_wfo{file_suffix}.json")
        with open(weekly_path, "w", encoding="utf-8") as f:
            json.dump({"mode": "weekly", "period": f"2022-2026 (Part {part})", "results": weekly_results}, f, indent=2)
        print(f"💾 Saved weekly WFO report to: {weekly_path}")

    print("\n🎉 4-Year Comprehensive Backtest Suite Completed Successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Crypto MAS 4-Year Comprehensive Backtest")
    parser.add_argument("--mode", type=str, default="all", choices=["monthly", "weekly", "all"], help="Granularity mode: monthly, weekly, or all")
    parser.add_argument("--max-folds", type=int, default=None, help="Limit number of rolling folds for fast speed testing")
    parser.add_argument("--n-jobs", type=int, default=1, help="Number of parallel CPU workers (1 for SQLite safety)")
    parser.add_argument("--part", type=str, default="all", choices=["1", "2", "3", "4", "all"], help="Chronological part to run (1: 2022, 2: 2023, 3: 2024, 4: 2025-2026, all: full)")
    parser.add_argument("--n-trials", type=int, default=None, help="Optuna trials per fold (default 15 for monthly)")
    args = parser.parse_args()
    run_4year_comprehensive_suite(mode=args.mode, max_folds=args.max_folds, n_jobs=args.n_jobs, part=args.part, n_trials=args.n_trials)
