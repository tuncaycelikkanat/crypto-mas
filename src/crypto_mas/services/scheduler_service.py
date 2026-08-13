import logging
from datetime import UTC
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.services.event_driven_service import EventDrivenService
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService

logger = logging.getLogger("crypto_mas.scheduler_service")

from crypto_mas.infrastructure.config.settings import get_settings

# Mode → (timeframe, strategy_name, default_interval_seconds)
MODE_CONFIG: dict[str, tuple[str, str, int]] = get_settings().mode_config


class SchedulerService:
    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone=UTC)
        self._event_service = EventDrivenService()

    def start(self):
        if not self._scheduler.running:
            self._scheduler.start()
            self._event_service.start()
            logger.info("Scheduler Service started.")

    def shutdown(self):
        if self._scheduler.running:
            self._scheduler.shutdown()
            self._event_service.shutdown()
            logger.info("Scheduler Service shut down.")

    def is_bot_running(self, bot_id: str) -> bool:
        if not self._scheduler.running:
            return False
        return self._scheduler.get_job(bot_id) is not None or self._event_service.is_bot_running(bot_id)

    def get_status(self) -> dict[str, Any]:
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
                "use_btc_shield": args[4] if len(args) > 4 else True,
                "use_htf_shield": args[5] if len(args) > 5 else True,
                "use_regime_shield": args[6] if len(args) > 6 else True,
            })
            
        # Merge with event driven bots
        event_status = self._event_service.get_status()
        active_bots.extend(event_status.get("bots", []))
            
        return {"bots": active_bots}

    def start_bot(
        self,
        bot_id: str,
        interval_seconds: int | None = None,
        symbols: list[str] | None = None,
        mode: str = "swing",
        exchange: str = "BINANCE",
        risk_level: int = 50,
        use_btc_shield: bool = True,
        use_htf_shield: bool = True,
        use_regime_shield: bool = True,
    ) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            return self.get_status()

        if symbols is None:
            symbols = ["BTCUSDT"]

        # Create isolated paper account
        db = SessionLocal()
        try:
            from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
            from crypto_mas.services.market_data_service.schemas import Exchange
            from decimal import Decimal
            PaperAccountRepository(db).create_if_not_exists(
                name=bot_id,
                exchange=Exchange.MOCK.value,
                base_currency="USDT",
                initial_balance=Decimal("10000"),
            )
        finally:
            db.close()

        mode = mode.lower() if mode else "swing"
        _, _, default_interval = MODE_CONFIG.get(mode, MODE_CONFIG["swing"])
        effective_interval = interval_seconds if interval_seconds is not None else default_interval

        if mode == "scalping" and "AUTO_GAINERS" not in symbols and "HIDDEN_GEMS" not in symbols:
            # Scalping with fixed symbols → event_service
            self._event_service.start_bot(bot_id, symbols, mode, exchange, risk_level)
        else:
            interval_trigger = IntervalTrigger(seconds=effective_interval, timezone=UTC)
            self._scheduler.add_job(
                self._run_cycle_task,
                trigger=interval_trigger,
                args=[symbols, mode, exchange.upper(), risk_level, use_btc_shield, use_htf_shield, use_regime_shield, bot_id],
                id=bot_id,
                name=f"Bot Instance: {bot_id}",
                replace_existing=True,
            )
            logger.info(f"Bot {bot_id} started (POLLING) | mode={mode} | exchange={exchange.upper()} | interval={effective_interval}s | {len(symbols)} symbols | risk={risk_level}")
            
            for sym in symbols:
                if sym not in ("AUTO_GAINERS", "HIDDEN_GEMS"):
                    self._event_service.get_ws_client().add_subscription(sym, "trade")
        
        return self.get_status()

    def stop_bot(self, bot_id: str) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            if self._event_service.is_bot_running(bot_id):
                self._event_service.stop_bot(bot_id)
            else:
                job = self._scheduler.get_job(bot_id)
                symbols_to_remove = job.args[0] if job and job.args else []
                self._scheduler.remove_job(bot_id)
                logger.info(f"Bot {bot_id} (POLLING) stopped.")
                for sym in symbols_to_remove:
                    self._event_service.get_ws_client().remove_subscription(sym, "trade")
                
        return self.get_status()

    def update_symbols(self, bot_id: str, symbols: list[str]) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            if self._event_service.is_bot_running(bot_id):
                self._event_service.update_symbols(bot_id, symbols)
            else:
                job = self._scheduler.get_job(bot_id)
                if job and job.args:
                    current_args = list(job.args)
                    old_symbols = current_args[0]
                    current_args[0] = symbols
                    self._scheduler.modify_job(bot_id, args=current_args)
                    for sym in old_symbols:
                        if sym not in symbols:
                            self._event_service.get_ws_client().remove_subscription(sym, "trade")
                    for sym in symbols:
                        if sym not in old_symbols:
                            self._event_service.get_ws_client().add_subscription(sym, "trade")
                    logger.info(f"Bot {bot_id} updated | new symbols: {len(symbols)}")
        return self.get_status()

    def update_risk(self, bot_id: str, risk_level: int) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            if self._event_service.is_bot_running(bot_id):
                self._event_service.update_risk(bot_id, risk_level)
            else:
                job = self._scheduler.get_job(bot_id)
                if job and job.args:
                    current_args = list(job.args)
                    if len(current_args) < 4:
                        current_args.extend([False] * (4 - len(current_args)))
                    current_args[3] = risk_level
                    self._scheduler.modify_job(bot_id, args=current_args)
                    logger.info(f"Bot {bot_id} (POLLING) updated | new risk_level: {risk_level}")
        return self.get_status()

    async def _run_cycle_task(self, symbols: list[str], mode: str = "swing", exchange_str: str = "BINANCE", risk_level: int = 50, use_btc_shield: bool = True, use_htf_shield: bool = True, use_regime_shield: bool = True, bot_id: str = "default-paper") -> None:
        logger.info(f"[{mode.upper()}][{exchange_str}] Running cycle for {len(symbols)} symbols... (account={bot_id}, risk={risk_level})")

        timeframe_str, strategy_name, _ = MODE_CONFIG.get(mode, MODE_CONFIG["swing"])

        tf_map = {
            "15m": Timeframe.FIFTEEN_MINUTES,
            "4h":  Timeframe.FOUR_HOURS,
            "1d":  Timeframe.ONE_DAY,
        }
        timeframe = tf_map.get(timeframe_str, Timeframe.FOUR_HOURS)

        import os
        import json
        config_json = {}
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
        config_path = os.path.join(data_dir, 'current_optimal_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config_json = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load optimal config: {e}")

        db = SessionLocal()
        try:
            exchange = Exchange(exchange_str)
            provider = get_market_data_provider(exchange)

            service = TradingCycleService(
                db=db, 
                market_provider=provider, 
                strategy_mode=mode,
                ws_client=self._event_service.get_ws_client()
            )

            cycle = await service.run_cycle(
                account_name=bot_id,
                symbols=symbols,
                timeframe=timeframe,
                strategy_name=strategy_name,
                trigger="SCHEDULED",
                risk_level=risk_level,
                use_btc_shield=use_btc_shield,
                use_htf_shield=use_htf_shield,
                use_regime_shield=use_regime_shield,
                config_json=config_json,
            )

            logger.info(f"[{mode.upper()}] Cycle {cycle.id} done. PnL: {cycle.cycle_pnl}")
        except Exception as e:
            logger.exception(f"[{mode.upper()}] Cycle failed: {e}")
        finally:
            db.close()
