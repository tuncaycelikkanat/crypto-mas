import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta

from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.services.backtesting.engine import BacktestEngineService

logging.basicConfig(level=logging.WARNING)

async def main():
    db = SessionLocal()
    engine = BacktestEngineService(db)
    
    end = datetime(2026, 6, 30, tzinfo=UTC)
    start = end - timedelta(days=14) # 14 days = 20160 cycles
    
    t0 = time.time()
    await engine.run_backtest(
        job_id="CLI_TEST_PROFILER_14DAYS",
        exchange=__import__("crypto_mas.services.market_data_service.schemas", fromlist=["Exchange"]).Exchange.BINANCE,
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe=__import__("crypto_mas.services.market_data_service.schemas", fromlist=["Timeframe"]).Timeframe.ONE_MINUTE,
        strategy_name="hft_momentum",
        start_time=start,
        end_time=end,
        initial_balance=1000.0,
        risk_level=100,
        use_btc_shield=False,
        use_htf_shield=False,
        use_regime_shield=False
    )
    t1 = time.time()
    result = db.query(__import__("crypto_mas.domain.models.backtest_result").domain.models.backtest_result.BacktestResult).filter_by(job_id="CLI_TEST_PROFILER_14DAYS").first()
    print(f"Total time for 14 days (20,160 cycles): {t1-t0:.2f}s | Trades: {result.total_trades if result else 0}")
    
if __name__ == "__main__":
    asyncio.run(main())
