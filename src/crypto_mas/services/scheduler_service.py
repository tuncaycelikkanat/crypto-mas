import logging
from datetime import UTC
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService

logger = logging.getLogger("crypto_mas.scheduler_service")

# Mode → (timeframe, strategy_name, default_interval_seconds)
MODE_CONFIG: dict[str, tuple[str, str, int]] = {
    "scalping": ("15m", "rsi_oversold", 30),
    "swing":    ("4h",  "macd_cross",   120),
    "hodl":     ("1d",  "ema_golden_cross", 3600),
}


class SchedulerService:
    _instance = None
    _scheduler: AsyncIOScheduler | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerService, cls).__new__(cls)
            cls._instance._scheduler = AsyncIOScheduler(timezone=UTC)
        return cls._instance

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Scheduler Service started.")

    def shutdown(self):
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler Service shut down.")

    def is_bot_running(self, bot_id: str) -> bool:
        if not self._scheduler.running:
            return False
        return self._scheduler.get_job(bot_id) is not None

    def get_status(self) -> dict[str, Any]:
        """Returns a list of all active bots."""
        if not self._scheduler.running:
            return {"bots": []}
            
        jobs = self._scheduler.get_jobs()
        active_bots = []
        for job in jobs:
            args = job.args or []
            active_bots.append({
                "bot_id": job.id,
                "status": "RUNNING",
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
                "symbols": args[0] if len(args) > 0 else [],
                "mode": args[1] if len(args) > 1 else "swing",
                "exchange": args[2] if len(args) > 2 else "BINANCE",
            })
            
        return {"bots": active_bots}

    def start_bot(
        self,
        bot_id: str,
        interval_seconds: int | None = None,
        symbols: list[str] | None = None,
        mode: str = "swing",
        exchange: str = "BINANCE",
    ) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            return self.get_status()

        if symbols is None:
            symbols = ["BTCUSDT"]

        # Resolve mode config
        mode = mode.lower() if mode else "swing"
        _, _, default_interval = MODE_CONFIG.get(mode, MODE_CONFIG["swing"])
        effective_interval = interval_seconds if interval_seconds is not None else default_interval

        interval_trigger = IntervalTrigger(seconds=effective_interval, timezone=UTC)

        self._scheduler.add_job(
            self._run_cycle_task,
            trigger=interval_trigger,
            args=[symbols, mode, exchange.upper()],
            id=bot_id,
            name=f"Bot Instance: {bot_id}",
            replace_existing=True,
        )

        logger.info(f"Bot {bot_id} started | mode={mode} | exchange={exchange.upper()} | interval={effective_interval}s | {len(symbols)} symbols")
        return self.get_status()

    def stop_bot(self, bot_id: str) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            self._scheduler.remove_job(bot_id)
            logger.info(f"Bot {bot_id} stopped.")
        return self.get_status()

    def update_symbols(self, bot_id: str, symbols: list[str]) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            job = self._scheduler.get_job(bot_id)
            if job and job.args:
                current_args = list(job.args)
                current_args[0] = symbols
                self._scheduler.modify_job(bot_id, args=current_args)
                logger.info(f"Bot {bot_id} updated | new symbols: {len(symbols)}")
        return self.get_status()

    async def _run_cycle_task(self, symbols: list[str], mode: str = "swing", exchange_str: str = "BINANCE") -> None:
        logger.info(f"[{mode.upper()}][{exchange_str}] Running cycle for {len(symbols)} symbols...")

        timeframe_str, strategy_name, _ = MODE_CONFIG.get(mode, MODE_CONFIG["swing"])

        # Map timeframe string to enum
        tf_map = {
            "15m": Timeframe.FIFTEEN_MINUTES,
            "4h":  Timeframe.FOUR_HOURS,
            "1d":  Timeframe.ONE_DAY,
        }
        timeframe = tf_map.get(timeframe_str, Timeframe.FOUR_HOURS)

        db = SessionLocal()
        try:
            exchange = Exchange(exchange_str)
            provider = get_market_data_provider(exchange)

            service = TradingCycleService(db=db, market_provider=provider, strategy_mode=mode)

            cycle = await service.run_cycle(
                account_name="default-paper",
                symbols=symbols,
                timeframe=timeframe,
                strategy_name=strategy_name,
                trigger="SCHEDULED",
            )

            logger.info(f"[{mode.upper()}] Cycle {cycle.id} done. PnL: {cycle.cycle_pnl}")
        except Exception as e:
            logger.exception(f"[{mode.upper()}] Cycle failed: {e}")
        finally:
            db.close()
