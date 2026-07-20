import logging
from datetime import UTC
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from crypto_mas.engine.strategy.event_engine import EventEngine
from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.market_data_service.websocket_client import BinanceWebsocketClient
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService

logger = logging.getLogger("crypto_mas.scheduler_service")

# Mode → (timeframe, strategy_name, default_interval_seconds)
MODE_CONFIG: dict[str, tuple[str, str, int]] = {
    "scalping": ("15m", "hft_momentum", 60),
    "swing":    ("4h",  "macd_cross",   120),
    "hodl":     ("1d",  "ema_golden_cross", 3600),
}


class SchedulerService:
    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone=UTC)
        
        # Phase 4: Event Driven Architecture
        self._ws_client = BinanceWebsocketClient()
        self._event_engine = EventEngine()
        self._ws_client.add_callback(self._event_engine.process_websocket_message)
        self._event_bots = {} # Track event-driven bots

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            self._ws_client.start()
            logger.info("Scheduler Service and WS Client started.")

    def shutdown(self):
        if self._scheduler.running:
            self._scheduler.shutdown()
            self._ws_client.stop()
            logger.info("Scheduler Service and WS Client shut down.")

    def is_bot_running(self, bot_id: str) -> bool:
        if not self._scheduler.running:
            return False
        return self._scheduler.get_job(bot_id) is not None or bot_id in self._event_bots

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
                "risk_level": args[3] if len(args) > 3 else 50,
            })
            
        for bot_id, bot_data in self._event_bots.items():
            active_bots.append({
                "bot_id": bot_id,
                "status": "RUNNING",
                "next_run_time": "EVENT_DRIVEN",
                "trigger": "WEBSOCKET_HFT",
                "symbols": bot_data.get("symbols", []),
                "mode": bot_data.get("mode", "scalping"),
                "exchange": bot_data.get("exchange", "BINANCE"),
                "risk_level": bot_data.get("risk_level", 50),
            })
            
        return {"bots": active_bots}

    def start_bot(
        self,
        bot_id: str,
        interval_seconds: int | None = None,
        symbols: list[str] | None = None,
        mode: str = "swing",
        exchange: str = "BINANCE",
        risk_level: int = 50,
    ) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            return self.get_status()

        if symbols is None:
            symbols = ["BTCUSDT"]

        # Resolve mode config
        mode = mode.lower() if mode else "swing"
        _, _, default_interval = MODE_CONFIG.get(mode, MODE_CONFIG["swing"])
        effective_interval = interval_seconds if interval_seconds is not None else default_interval

        if mode == "scalping" and "AUTO_GAINERS" not in symbols and "HIDDEN_GEMS" not in symbols:
            # Event-Driven HFT approach: No APScheduler polling.
            self._event_bots[bot_id] = {
                "symbols": symbols,
                "mode": mode,
                "exchange": exchange.upper(),
                "risk_level": risk_level,
            }
            logger.info(f"Bot {bot_id} started (EVENT_DRIVEN) | mode={mode} | exchange={exchange.upper()} | {len(symbols)} symbols | risk={risk_level}")
        else:
            # Polling approach
            interval_trigger = IntervalTrigger(seconds=effective_interval, timezone=UTC)
            self._scheduler.add_job(
                self._run_cycle_task,
                trigger=interval_trigger,
                args=[symbols, mode, exchange.upper(), risk_level],
                id=bot_id,
                name=f"Bot Instance: {bot_id}",
                replace_existing=True,
            )
            logger.info(f"Bot {bot_id} started (POLLING) | mode={mode} | exchange={exchange.upper()} | interval={effective_interval}s | {len(symbols)} symbols | risk={risk_level}")
        
        # Add to real-time WS tracking for Micro-structure Volume Spikes (for both, but essential for scalping)
        for sym in symbols:
            if sym not in ("AUTO_GAINERS", "HIDDEN_GEMS"):
                self._ws_client.add_subscription(sym, "trade")

        return self.get_status()

    def stop_bot(self, bot_id: str) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            symbols_to_remove = []
            
            if bot_id in self._event_bots:
                symbols_to_remove = self._event_bots[bot_id].get("symbols", [])
                del self._event_bots[bot_id]
                logger.info(f"Bot {bot_id} (EVENT_DRIVEN) stopped.")
            else:
                job = self._scheduler.get_job(bot_id)
                if job and job.args:
                    symbols_to_remove = job.args[0]
                self._scheduler.remove_job(bot_id)
                logger.info(f"Bot {bot_id} (POLLING) stopped.")
                
            # Remove subscriptions if they aren't used by other bots (simplified approach: just unsubscribe, but in a real app we would ref-count them)
            # For this exercise, we will just remove them, though a production app needs a ref-counter.
            for sym in symbols_to_remove:
                self._ws_client.remove_subscription(sym, "trade")
                
        return self.get_status()

    def update_symbols(self, bot_id: str, symbols: list[str]) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            if bot_id in self._event_bots:
                old_symbols = self._event_bots[bot_id].get("symbols", [])
                self._event_bots[bot_id]["symbols"] = symbols
                # Diffing subscriptions
                for sym in old_symbols:
                    if sym not in symbols:
                        self._ws_client.remove_subscription(sym, "trade")
                for sym in symbols:
                    if sym not in old_symbols:
                        self._ws_client.add_subscription(sym, "trade")
                logger.info(f"Bot {bot_id} updated | new symbols: {len(symbols)}")
            else:
                job = self._scheduler.get_job(bot_id)
                if job and job.args:
                    current_args = list(job.args)
                    old_symbols = current_args[0]
                    current_args[0] = symbols
                    self._scheduler.modify_job(bot_id, args=current_args)
                    
                    for sym in old_symbols:
                        if sym not in symbols:
                            self._ws_client.remove_subscription(sym, "trade")
                    for sym in symbols:
                        if sym not in old_symbols:
                            self._ws_client.add_subscription(sym, "trade")
                            
                    logger.info(f"Bot {bot_id} updated | new symbols: {len(symbols)}")
        return self.get_status()

    def update_risk(self, bot_id: str, risk_level: int) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            if bot_id in self._event_bots:
                self._event_bots[bot_id]["risk_level"] = risk_level
                logger.info(f"Bot {bot_id} (EVENT_DRIVEN) updated | new risk_level: {risk_level}")
            else:
                job = self._scheduler.get_job(bot_id)
                if job and job.args:
                    current_args = list(job.args)
                    # Extend args if risk_level wasn't originally passed
                    if len(current_args) < 4:
                        current_args.extend([False] * (4 - len(current_args)))
                    current_args[3] = risk_level
                    self._scheduler.modify_job(bot_id, args=current_args)
                    logger.info(f"Bot {bot_id} (POLLING) updated | new risk_level: {risk_level}")
        return self.get_status()

    async def _run_cycle_task(self, symbols: list[str], mode: str = "swing", exchange_str: str = "BINANCE", risk_level: int = 50) -> None:
        logger.info(f"[{mode.upper()}][{exchange_str}] Running cycle for {len(symbols)} symbols... (risk={risk_level})")

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

            service = TradingCycleService(
                db=db, 
                market_provider=provider, 
                strategy_mode=mode,
                ws_client=self._ws_client
            )

            cycle = await service.run_cycle(
                account_name="default-paper",
                symbols=symbols,
                timeframe=timeframe,
                strategy_name=strategy_name,
                trigger="SCHEDULED",
                risk_level=risk_level,
            )

            logger.info(f"[{mode.upper()}] Cycle {cycle.id} done. PnL: {cycle.cycle_pnl}")
        except Exception as e:
            logger.exception(f"[{mode.upper()}] Cycle failed: {e}")
        finally:
            db.close()
