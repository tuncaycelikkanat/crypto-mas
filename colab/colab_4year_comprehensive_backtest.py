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
from crypto_mas.engine.optimization.fold_generator import FoldGenerator
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


def evaluate_pool(optimizer: WalkForwardOptimizer, pool_name: str, symbols: list[str], folds: list, timeframe: Timeframe, strategy_name: str, granularity: str):
    print(f"\n====================================================================")
    print(f"🚀 [{granularity.upper()}] Running 4-Year WFO for Pool: {pool_name} ({len(symbols)} coins)")
    print(f"    Total Rolling Periods: {len(folds)}")
    print(f"====================================================================")

    try:
        # Run Optuna optimization on rolling folds
        test_results = optimizer.optimize(
            folds=folds,
            exchange=Exchange.BINANCE,
            symbols=symbols,
            timeframe=timeframe,
            strategy_name=strategy_name,
            n_trials=40,
            min_trades=5,
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

        print(f"✅ [{pool_name}] 4-Year Total PnL: ${total_net_profit:,.2f} | Trades: {total_trades} | OOS Consistency: {consistency_ratio:.1f}%")

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


def run_4year_comprehensive_suite(mode: str = "all"):
    db = SessionLocal()
    engine_service = BacktestEngineService(db)
    optimizer = WalkForwardOptimizer(db, engine_service)

    # 4.5-Year Institutional Window: 2022-01-01 -> 2026-07-01 (54 Months & 230+ Weeks)
    start_date = datetime(2022, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2026, 7, 1, tzinfo=timezone.utc)
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
        print(f"Generated {len(monthly_folds)} rolling out-of-sample monthly periods.")

        for pool_name, symbols in SYMBOL_POOLS.items():
            res = evaluate_pool(optimizer, pool_name, symbols, monthly_folds, timeframe, strategy_name, granularity="monthly")
            monthly_results.append(res)

        monthly_path = os.path.join(results_dir, "4year_monthly_wfo.json")
        with open(monthly_path, "w", encoding="utf-8") as f:
            json.dump({"mode": "monthly", "period": "2022-2026", "results": monthly_results}, f, indent=2)
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
        print(f"Generated {len(weekly_folds)} rolling out-of-sample weekly periods.")

        for pool_name, symbols in SYMBOL_POOLS.items():
            res = evaluate_pool(optimizer, pool_name, symbols, weekly_folds, timeframe, strategy_name, granularity="weekly")
            weekly_results.append(res)

        weekly_path = os.path.join(results_dir, "4year_weekly_wfo.json")
        with open(weekly_path, "w", encoding="utf-8") as f:
            json.dump({"mode": "weekly", "period": "2022-2026", "results": weekly_results}, f, indent=2)
        print(f"💾 Saved weekly WFO report to: {weekly_path}")

    print("\n🎉 4-Year Comprehensive Backtest Suite Completed Successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Crypto MAS 4-Year Comprehensive Backtest")
    parser.add_argument("--mode", type=str, default="all", choices=["monthly", "weekly", "all"], help="Granularity mode: monthly, weekly, or all")
    args = parser.parse_args()
    run_4year_comprehensive_suite(mode=args.mode)
