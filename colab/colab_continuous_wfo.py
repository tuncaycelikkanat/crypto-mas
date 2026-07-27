import sys
import os
import asyncio
import json
from datetime import datetime, timezone
import nest_asyncio

nest_asyncio.apply()

# Add project root and src/ to sys.path
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_src_dir = os.path.join(_project_root, 'src')
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.engine.optimization.fold_generator import FoldGenerator
from crypto_mas.engine.optimization.walk_forward_optimizer import WalkForwardOptimizer
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

# Same pools as mass_backtest.py
SYMBOL_POOLS = {
    "TOP10": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT"],
    "MEMES": ["DOGEUSDT", "SHIBUSDT", "FLOKIUSDT"],
    "L1": ["SOLUSDT", "ADAUSDT", "AVAXUSDT", "NEARUSDT", "FTMUSDT", "APTUSDT"],
    "AI_HYPE": ["INJUSDT", "RNDRUSDT", "FETUSDT", "OCEANUSDT"],
}

def run_continuous_wfo():
    db = SessionLocal()
    engine_service = BacktestEngineService(db)
    optimizer = WalkForwardOptimizer(db, engine_service)
    
    # 1 Yıllık Test Periyodu: 2023-01-01 -> 2024-01-01
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    
    # Train: 3 Ay, Test: 1 Ay
    # Örn: Oca-Şub-Mar Train -> Nis Test | Şub-Mar-Nis Train -> May Test
    folds = FoldGenerator.generate_rolling_folds(
        start_date=start_date,
        end_date=end_date,
        train_months=3,
        test_months=1
    )
    
    exchange = Exchange.BINANCE
    timeframe = Timeframe.ONE_HOUR
    strategy_name = "regime_adaptive"
    
    all_results = []
    
    print(f"Starting Continuous WFO Backtest (1-Year Period)")
    print(f"Generated {len(folds)} rolling folds (3M Train + 1M Test)")
    
    for pool_name, symbols in SYMBOL_POOLS.items():
        print(f"\n==================================================")
        print(f"🚀 Running Continuous WFO for Pool: {pool_name}")
        print(f"==================================================")
        
        try:
            # Her bir fold için 50 Trial optimizasyon yapılıp, Test seti değerlendirilir
            # test_results listesi o coin grubu için yıl boyunca elde edilen tüm "Test Aylarının" sırayla sonuçlarıdır.
            test_results = optimizer.optimize(
                folds=folds,
                exchange=exchange,
                symbols=symbols,
                timeframe=timeframe,
                strategy_name=strategy_name,
                n_trials=50,  # 50 is a good standard for Optuna
                min_trades=10
            )
            
            # Aggregate the continuous equity curve across the whole year
            total_net_profit = 0.0
            total_trades = 0
            pool_fold_data = []
            
            for idx, res in enumerate(test_results):
                net_profit = float(res.final_equity - res.initial_balance) if res.final_equity else 0.0
                trades = int(res.total_trades) if res.total_trades else 0
                total_net_profit += net_profit
                total_trades += trades
                
                pool_fold_data.append({
                    "fold": idx + 1,
                    "test_period": f"{folds[idx].test_start.strftime('%Y-%m')} -> {folds[idx].test_end.strftime('%Y-%m')}",
                    "net_profit": net_profit,
                    "trades": trades,
                    "win_rate": float(res.win_rate) if res.win_rate else 0.0
                })
                
            all_results.append({
                "pool_name": pool_name,
                "strategy": strategy_name,
                "timeframe": timeframe.value,
                "total_1_year_profit": total_net_profit,
                "total_trades": total_trades,
                "folds_detail": pool_fold_data
            })
            
            print(f"✅ Finished pool {pool_name}. 1-Year Profit: ${total_net_profit:.2f}")
            
        except Exception as e:
            print(f"❌ Error in pool {pool_name}: {str(e)}")
            all_results.append({
                "pool_name": pool_name,
                "error": str(e)
            })
            
        # Save progress incrementally
        with open("colab_wfo_results.json", "w") as f:
            json.dump(all_results, f, indent=2)
            
    print("\n🎉 Continuous WFO Backtest Completed! Results saved to colab_wfo_results.json")

if __name__ == "__main__":
    run_continuous_wfo()
