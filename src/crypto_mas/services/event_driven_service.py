import logging
from typing import Any

from crypto_mas.engine.strategy.event_engine import EventEngine
from crypto_mas.services.market_data_service.websocket_client import BinanceWebsocketClient

logger = logging.getLogger("crypto_mas.event_driven_service")


class EventDrivenService:
    def __init__(self):
        self._ws_client = BinanceWebsocketClient()
        self._event_engine = EventEngine()
        self._ws_client.add_callback(self._event_engine.process_websocket_message)
        self._event_bots = {}

    def start(self):
        self._ws_client.start()
        logger.info("Event Driven Service (WS Client) started.")

    def shutdown(self):
        self._ws_client.stop()
        logger.info("Event Driven Service (WS Client) shut down.")

    def is_bot_running(self, bot_id: str) -> bool:
        return bot_id in self._event_bots

    def get_status(self) -> dict[str, Any]:
        active_bots = []
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

    def start_bot(self, bot_id: str, symbols: list[str], mode: str = "scalping", exchange: str = "BINANCE", risk_level: int = 50) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            return self.get_status()

        self._event_bots[bot_id] = {
            "symbols": symbols,
            "mode": mode,
            "exchange": exchange.upper(),
            "risk_level": risk_level,
        }
        logger.info(f"Bot {bot_id} started (EVENT_DRIVEN) | mode={mode} | exchange={exchange.upper()} | {len(symbols)} symbols | risk={risk_level}")
        
        for sym in symbols:
            if sym not in ("AUTO_GAINERS", "HIDDEN_GEMS"):
                self._ws_client.add_subscription(sym, "trade")

        return self.get_status()

    def stop_bot(self, bot_id: str) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            symbols_to_remove = self._event_bots[bot_id].get("symbols", [])
            del self._event_bots[bot_id]
            logger.info(f"Bot {bot_id} (EVENT_DRIVEN) stopped.")
            
            for sym in symbols_to_remove:
                self._ws_client.remove_subscription(sym, "trade")
                
        return self.get_status()

    def update_symbols(self, bot_id: str, symbols: list[str]) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            old_symbols = self._event_bots[bot_id].get("symbols", [])
            self._event_bots[bot_id]["symbols"] = symbols
            for sym in old_symbols:
                if sym not in symbols:
                    self._ws_client.remove_subscription(sym, "trade")
            for sym in symbols:
                if sym not in old_symbols:
                    self._ws_client.add_subscription(sym, "trade")
            logger.info(f"Bot {bot_id} (EVENT_DRIVEN) updated | new symbols: {len(symbols)}")
        return self.get_status()

    def update_risk(self, bot_id: str, risk_level: int) -> dict[str, Any]:
        if self.is_bot_running(bot_id):
            self._event_bots[bot_id]["risk_level"] = risk_level
            logger.info(f"Bot {bot_id} (EVENT_DRIVEN) updated | new risk_level: {risk_level}")
        return self.get_status()

    def get_ws_client(self):
        return self._ws_client
