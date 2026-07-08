import asyncio
import json
import logging
from typing import Callable, Coroutine

import websockets

logger = logging.getLogger("crypto_mas.websocket")

class BinanceWebsocketClient:
    def __init__(self):
        self.base_url = "wss://stream.binance.com:9443/ws"
        self._connection = None
        self._is_running = False
        self._callbacks: list[Callable[[dict], Coroutine]] = []
        self._subscriptions: set[str] = set()
        
    def add_callback(self, callback: Callable[[dict], Coroutine]):
        self._callbacks.append(callback)
        
    def add_subscription(self, symbol: str, stream_type: str = "trade"):
        """
        stream_type can be 'trade' or 'depth10@100ms'
        """
        stream_name = f"{symbol.lower()}@{stream_type}"
        self._subscriptions.add(stream_name)

    async def _handle_messages(self):
        while self._is_running:
            try:
                # Combine subscriptions into a single URL if less than 1024 chars, or use multiple connections.
                # For simplicity, if we have many streams, Binance supports connecting to /stream?streams=s1/s2/s3
                if not self._subscriptions:
                    await asyncio.sleep(1)
                    continue
                    
                stream_path = "/".join(self._subscriptions)
                url = f"wss://stream.binance.com:9443/stream?streams={stream_path}"
                
                logger.info(f"Connecting to Binance WS: {url}")
                async with websockets.connect(url) as websocket:
                    self._connection = websocket
                    logger.info("Binance WS Connected.")
                    
                    while self._is_running:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Data comes in as {"stream": "btcusdt@trade", "data": {...}}
                        if "data" in data:
                            payload = data["data"]
                            stream = data["stream"]
                            
                            # Dispatch to callbacks asynchronously
                            for callback in self._callbacks:
                                asyncio.create_task(callback(stream, payload))
                                
            except websockets.ConnectionClosed:
                logger.warning("Binance WS Connection closed. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Binance WS Error: {e}")
                await asyncio.sleep(5)

    def start(self):
        if not self._is_running:
            self._is_running = True
            asyncio.create_task(self._handle_messages())
            logger.info("WebSocket Client background task started.")
            
    def stop(self):
        self._is_running = False
        if self._connection:
            asyncio.create_task(self._connection.close())
        logger.info("WebSocket Client stopped.")
