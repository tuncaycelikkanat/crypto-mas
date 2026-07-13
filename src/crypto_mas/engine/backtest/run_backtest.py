import sys

sys.path.append("/home/tuncay/Notes/Projects/crypto-mas/src")

from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.engine.backtest.engine import BacktestEngine
from crypto_mas.engine.strategy.rsi_oversold import RSIOversoldStrategy
from crypto_mas.infrastructure.db.session import SessionLocal


def run():
    db = SessionLocal()
    try:
        repo = CandleRepository(db)
        
        symbol = "BTCUSDT"
        
        # Load all candles we fetched for this symbol
        print(f"Loading candles from DB for {symbol}...")
        candles = repo.list_by_symbol(
            exchange="BINANCE",
            symbol=symbol,
            timeframe="15m"
        )
        
        if not candles:
            print("No candles found in DB. Please run history_fetcher.py first.")
            return
            
        print(f"Loaded {len(candles)} candles. Starting backtest...")
        
        engine = BacktestEngine(initial_balance=1000.0, fee_rate=0.001, slippage_pct=0.0005)
        strategy = RSIOversoldStrategy()
        
        report = engine.run(symbol=symbol, candles=candles, strategy=strategy)
        
        print("\n" + "="*40)
        print(f"BACKTEST REPORT: {symbol} - {strategy.__class__.__name__}")
        print("="*40)
        for k, v in report.items():
            if isinstance(v, float):
                print(f"{k.ljust(20)}: {v:.2f}")
            else:
                print(f"{k.ljust(20)}: {v}")
        print("="*40)
        
    finally:
        db.close()

if __name__ == "__main__":
    run()
