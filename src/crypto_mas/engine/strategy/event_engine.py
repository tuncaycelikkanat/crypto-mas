import asyncio
import logging
from collections import defaultdict
from typing import Any

from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from crypto_mas.services.market_data_service.schemas import Timeframe

logger = logging.getLogger("crypto_mas.event_engine")

class EventEngine:
    def __init__(self):
        self._volume_windows = defaultdict(lambda: {"buy": 0.0, "sell": 0.0})
        self._last_trigger_time = defaultdict(float)
        
        # Debounce to avoid triggering cycles constantly
        self.TRIGGER_COOLDOWN_SECONDS = 30 
        
    async def process_websocket_message(self, stream: str, payload: dict[str, Any]):
        try:
            # stream format: btcusdt@trade or btcusdt@depth10@100ms
            parts = stream.split('@')
            if len(parts) < 2:
                return
                
            symbol = parts[0].upper()
            stream_type = parts[1]
            
            if stream_type == "trade":
                await self._process_trade(symbol, payload)
            elif stream_type.startswith("depth"):
                await self._process_depth(symbol, payload)
                
        except Exception as e:
            logger.error(f"EventEngine error processing msg: {e}")
            
    async def _process_trade(self, symbol: str, payload: dict[str, Any]):
        # Binance trade payload: 
        # { 'p': price, 'q': quantity, 'm': is_buyer_maker (True=sell order hit bid, False=buy order hit ask) }
        price = float(payload.get('p', 0))
        qty = float(payload.get('q', 0))
        is_buyer_maker = payload.get('m', False)
        
        volume = price * qty
        
        if is_buyer_maker:
            self._volume_windows[symbol]["sell"] += volume
        else:
            self._volume_windows[symbol]["buy"] += volume
            
        # Detect Spike
        buy_vol = self._volume_windows[symbol]["buy"]
        sell_vol = self._volume_windows[symbol]["sell"]
        total_vol = buy_vol + sell_vol
        
        if total_vol > 50000: # Threshold of $50k rolling volume before reset
            imbalance = (buy_vol - sell_vol) / total_vol
            
            # Reset window
            self._volume_windows[symbol]["buy"] = 0.0
            self._volume_windows[symbol]["sell"] = 0.0
            
            import time
            now = time.time()
            if imbalance > 0.60: # 80% Buy Volume / 20% Sell Volume ratio
                logger.info(f"💥 [EVENT] Volume Spike Detected for {symbol}! Imbalance: {imbalance*100:.1f}% BUY")
                
                # Check cooldown
                if now - self._last_trigger_time[symbol] > self.TRIGGER_COOLDOWN_SECONDS:
                    self._last_trigger_time[symbol] = now
                    # Trigger an immediate out-of-band cycle!
                    asyncio.create_task(self._trigger_cycle(symbol))
                else:
                    logger.debug(f"[EVENT] Cooldown active for {symbol}, skipped trigger.")

    async def _process_depth(self, symbol: str, payload: dict[str, Any]):
        # Payload has 'bids' and 'asks' lists of [price, qty]
        # Currently we just log or use it if needed, but volume spike is our primary trigger.
        pass
        
    async def _trigger_cycle(self, symbol: str):
        logger.warning(f"🚀 FIRING EVENT-DRIVEN CYCLE FOR {symbol}!")
        from crypto_mas.infrastructure.db.session import SessionLocal
        from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
        from crypto_mas.services.market_data_service.schemas import Exchange

        db = SessionLocal()
        try:
            exchange = Exchange("BINANCE")
            provider = get_market_data_provider(exchange)
            cycle_service = TradingCycleService(db=db, market_provider=provider, strategy_mode="scalping")

            # We run a 15m Scalping cycle triggered by the event
            await cycle_service.run_cycle(
                account_name="default-paper",
                symbols=[symbol],
                timeframe=Timeframe.FIFTEEN_MINUTES,
                strategy_name="rsi_oversold",
                trigger="EVENT_TRIGGERED"
            )
        except Exception as e:
            logger.error(f"Event-driven cycle failed for {symbol}: {e}")
        finally:
            db.close()
