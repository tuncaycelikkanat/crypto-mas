import sys

sys.path.append("/home/tuncay/Notes/Projects/crypto-mas/src")

from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.engine.backtest.engine import BacktestEngine
from crypto_mas.engine.strategy.rsi_oversold import RSIOversoldStrategy
from crypto_mas.infrastructure.db.session import SessionLocal


def optimize():
    db = SessionLocal()
    try:
        repo = CandleRepository(db)
        symbol = "BTCUSDT"
        
        print(f"Loading candles from DB for {symbol}...")
        candles = repo.list_by_symbol(
            exchange="BINANCE",
            symbol=symbol,
            timeframe="15m"
        )
        
        if not candles:
            print("No candles found in DB. Please run history_fetcher.py first.")
            return
            
        print(f"Loaded {len(candles)} candles. Starting Grid Search Optimization...")
        
        # Grid of parameters to test
        rsi_thresholds = [20.0, 25.0, 30.0, 35.0, 40.0]
        
        best_pnl = -float('inf')
        best_params = None
        
        results = []
        
        for threshold in rsi_thresholds:
            # We initialize a new engine and strategy for each test run to avoid state leakage
            engine = BacktestEngine(initial_balance=1000.0, fee_rate=0.001, slippage_pct=0.0005)
            strategy = RSIOversoldStrategy(oversold_threshold=threshold)
            
            report = engine.run(symbol=symbol, candles=candles, strategy=strategy)
            
            results.append((threshold, report))
            
            if report['total_pnl'] > best_pnl:
                best_pnl = report['total_pnl']
                best_params = threshold
                
        print("\n" + "="*50)
        print("OPTIMIZATION RESULTS (Ranked by Total PnL)")
        print("="*50)
        
        # Sort by PnL descending
        results.sort(key=lambda x: x[1]['total_pnl'], reverse=True)
        
        print(f"{'RSI Threshold':<15} | {'PnL ($)':<10} | {'Win Rate':<10} | {'Trades':<8} | {'Max DD (%)':<10}")
        print("-" * 65)
        for threshold, r in results:
            print(f"{threshold:<15.1f} | {r['total_pnl']:<10.2f} | {r['win_rate']:<10.2f} | {r['total_trades']:<8} | {r['max_drawdown_pct']:<10.2f}")
            
        print("\n" + "="*50)
        print(f"BEST PARAMETER: RSI Threshold = {best_params}")
        print("="*50)
        
    finally:
        db.close()

if __name__ == "__main__":
    optimize()
