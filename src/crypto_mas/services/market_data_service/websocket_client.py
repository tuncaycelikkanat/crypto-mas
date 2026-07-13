import asyncio
import json
import logging
from collections.abc import Callable, Coroutine

import websockets

logger = logging.getLogger("crypto_mas.websocket")

class BinanceWebsocketClient:
    def __init__(self):
        self.base_url = "wss://stream.binance.com:9443/ws"
        self._connection = None
        self._is_running = False
        self._loop = None
        self._callbacks: list[Callable[[dict], Coroutine]] = []
        self._subscriptions: set[str] = set()
        
    def _run_task(self, coro: Coroutine):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)
        else:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                logger.error("No event loop available to run websocket task.")
                
    def add_callback(self, callback: Callable[[dict], Coroutine]):
        self._callbacks.append(callback)
        
    def add_subscription(self, symbol: str, stream_type: str = "trade"):
        """
        stream_type can be 'trade' or 'depth5@100ms'
        """
        stream_name = f"{symbol.lower()}@{stream_type}"
        if stream_name not in self._subscriptions:
            self._subscriptions.add(stream_name)
            if self._connection and self._connection.state == websockets.State.OPEN:
                # Send subscribe dynamically
                payload = {
                    "method": "SUBSCRIBE",
                    "params": [stream_name],
                    "id": len(self._subscriptions)
                }
                self._run_task(self._send_payload(payload))

    def remove_subscription(self, symbol: str, stream_type: str = "trade"):
        stream_name = f"{symbol.lower()}@{stream_type}"
        if stream_name in self._subscriptions:
            self._subscriptions.remove(stream_name)
            if self._connection and self._connection.state == websockets.State.OPEN:
                payload = {
                    "method": "UNSUBSCRIBE",
                    "params": [stream_name],
                    "id": len(self._subscriptions) + 1000
                }
                self._run_task(self._send_payload(payload))

    async def _send_payload(self, payload: dict):
        try:
            if self._connection and self._connection.state == websockets.State.OPEN:
                await self._connection.send(json.dumps(payload))
                logger.debug(f"Binance WS sent: {payload}")
        except Exception as e:
            logger.error(f"Binance WS send error: {e}")

    async def _handle_messages(self):
        while self._is_running:
            try:
                # Connect to raw stream, without ?streams=
                url = self.base_url
                
                logger.info(f"Connecting to Binance WS: {url}")
                async with websockets.connect(url) as websocket:
                    self._connection = websocket
                    logger.info("Binance WS Connected.")
                    
                    # Send initial subscriptions if we have any
                    if self._subscriptions:
                        payload = {
                            "method": "SUBSCRIBE",
                            "params": list(self._subscriptions),
                            "id": 1
                        }
                        await self._send_payload(payload)
                    
                    while self._is_running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Handle stream messages. Note: When connecting to /ws, the format is slightly different 
                        # than /stream. If using /ws, it just sends the raw data without the {"stream": ..., "data": ...} wrapper
                        # unless we connect to /stream. Actually, if we use /stream without streams params, it might fail.
                        # Wait, Binance /ws streams send raw data. To get the {"stream": ..., "data": ...} wrapper, 
                        # we MUST connect to /stream (or /stream?streams=...).
                        # So let's connect to /stream but with an initial valid stream, or just handle raw format!
                        # But wait! If we send SUBSCRIBE, how do we know which stream it belongs to?
                        # Binance raw format contains "s" (symbol) and "e" (event type) or similar fields.
                        
                        if "e" in data and "s" in data:
                            symbol = data["s"]
                            event_type = data["e"]
                            stream_name = f"{symbol.lower()}@{event_type}"
                            
                            # Dispatch to callbacks asynchronously
                            for callback in self._callbacks:
                                asyncio.create_task(callback(stream_name, data))
                        elif "stream" in data and "data" in data:
                            # Fallback if we accidentally get the combined stream format
                            stream_name = data["stream"]
                            payload = data["data"]
                            for callback in self._callbacks:
                                asyncio.create_task(callback(stream_name, payload))
                        elif "result" in data:
                            # Response to SUBSCRIBE/UNSUBSCRIBE
                            logger.debug(f"Binance WS Subscription result: {data}")
                                
            except websockets.ConnectionClosed:
                logger.warning("Binance WS Connection closed. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Binance WS Error: {e}")
                await asyncio.sleep(5)

    def start(self):
        if not self._is_running:
            self._is_running = True
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            asyncio.create_task(self._handle_messages())
            logger.info("WebSocket Client background task started.")
            
    def stop(self):
        self._is_running = False
        if self._connection:
            self._run_task(self._connection.close())
        logger.info("WebSocket Client stopped.")
