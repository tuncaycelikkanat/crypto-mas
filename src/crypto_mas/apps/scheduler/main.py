import asyncio
import logging
from datetime import UTC

import uvloop
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.infrastructure.logging.setup import setup_logging
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue
from crypto_mas.services.auto_optimizer_service import AutoOptimizerService
import os
import json

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

setup_logging(env="dev")  # Production'da env var'dan okunabilir
logger = logging.getLogger("crypto_mas.scheduler")

settings = get_settings()

async def scheduled_trading_cycle() -> None:
    """Zamanlanmış görev olarak Trading Cycle'ı çalıştırır."""
    logger.info("Starting scheduled trading cycle execution...")
    
    # Yeni bir veritabanı oturumu oluştur
    db = SessionLocal()
    
    try:
        # Provider oluştur (Örneğin varsayılan olarak BINANCE kullanılabilir. 
        # Test/Geliştirme için ayarlardan okumak daha iyi ama basitçe MOCK veya BINANCE seçilebilir)
        # Şimdilik PAPER modu ise MOCK, değilse BINANCE varsayalım
        exchange_str = "MOCK" if settings.trading_mode == "PAPER" else "BINANCE"
        exchange = Exchange(exchange_str)
        provider = get_market_data_provider(exchange)
        
        service = TradingCycleService(db=db, market_provider=provider)
        
        timeframe = Timeframe(settings.scheduled_timeframe)
        symbols = settings.scheduled_symbols
        
        # Read the latest optimal configuration from DB
        config_json = {}
        from crypto_mas.domain.models.optimization_history import OptimizationHistory
        latest_opt = db.query(OptimizationHistory).filter(OptimizationHistory.status == 'COMPLETED').order_by(OptimizationHistory.id.desc()).first()
        if latest_opt and latest_opt.best_params_json:
            config_json = latest_opt.best_params_json
            logger.info(f"Loaded auto-optimized config from DB: {config_json}")
        
        cycle = await service.run_cycle(
            account_name="default-paper",  # Daha dinamik hale getirilebilir
            symbols=symbols,
            timeframe=timeframe,
            trigger="SCHEDULED",
            config_json=config_json,
        )
        
        logger.info(f"Scheduled cycle {cycle.id} completed with status: {cycle.status}. PnL: {cycle.cycle_pnl}")
        
    except Exception as e:
        logger.exception(f"Scheduled cycle failed: {e}")
    finally:
        db.close()

async def scheduled_optimization_cycle() -> None:
    """Zamanlanmış görev olarak Geçmiş Veriyi Optimize Eder ve Config dosyasını günceller."""
    logger.info("Starting background Auto-Optimization cycle...")
    db = SessionLocal()
    try:
        service = AutoOptimizerService(db=db)
        timeframe = Timeframe(settings.scheduled_timeframe)
        symbols = settings.scheduled_symbols
        # Runs 50 trials on the past 3 months to find optimal settings for these symbols
        service.run_optimization_job(symbols=symbols, timeframe=timeframe, lookback_months=3, n_trials=50)
        logger.info("Background Auto-Optimization cycle completed successfully.")
    except Exception as e:
        logger.exception(f"Scheduled optimization failed: {e}")
    finally:
        db.close()



def main() -> None:
    logger.info("Initializing APScheduler...")
    scheduler = AsyncIOScheduler(timezone=UTC)
    
    # Cron ifadesini ayrıştır (Örn: "0 * * * *")
    # APScheduler CronTrigger.from_crontab metodunu kullanabilir.
    cron_trigger = CronTrigger.from_crontab(settings.schedule_cron, timezone=UTC)
    
    scheduler.add_job(
        scheduled_trading_cycle,
        trigger=cron_trigger,
        id="trading_cycle_job",
        name="Main Trading Cycle",
        replace_existing=True,
    )
    
    # Yeni eklendi: Pazar geceleri otomatik optimizasyon!
    # Saat Pazar 00:00 (UTC)
    opt_trigger = CronTrigger(day_of_week="sun", hour=0, minute=0, timezone=UTC)
    scheduler.add_job(
        scheduled_optimization_cycle,
        trigger=opt_trigger,
        id="optimization_cycle_job",
        name="Weekly Auto Optimization",
        replace_existing=True,
    )
    
    queue = OrderExecutorQueue.get_instance()
    def broker_factory():
        db = SessionLocal()
        return PaperBrokerService(db=db)
    queue.set_broker_factory(broker_factory)
    queue.start()
    
    scheduler.start()
    logger.info(f"Scheduler started. Scheduled tasks: {settings.scheduled_symbols} at '{settings.schedule_cron}'")
    
    # Sonsuz döngü
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler and queue...")
        queue.stop()
        scheduler.shutdown()

if __name__ == "__main__":
    main()
