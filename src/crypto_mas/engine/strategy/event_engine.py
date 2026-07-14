"""
EventEngine — Real-time WebSocket stream processor.

Key upgrades:
  - 60-second sliding window (deque) instead of cumulative reset
  - Dynamic RVOL threshold: fires only when volume > 2× coin's own average
  - CVD (Cumulative Volume Delta) tracking
  - Order book depth imbalance stored for strategy use
"""
import asyncio
import logging
import time
from collections import defaultdict, deque
from typing import Any

from crypto_mas.engine.strategy.realtime_metrics import RealtimeMetricsStore
from crypto_mas.services.market_data_service.schemas import Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService

logger = logging.getLogger("crypto_mas.event_engine")

# Window length in seconds for sliding volume aggregation
WINDOW_SECONDS = 60

# Minimum RVOL multiplier to trigger a cycle (2× average volume = real spike)
RVOL_TRIGGER_THRESHOLD = 2.0

# Minimum imbalance skew to consider directional (60% buy or 40% buy)
IMBALANCE_THRESHOLD = 0.60

# Debounce: minimum seconds between two triggered cycles for the same symbol
TRIGGER_COOLDOWN_SECONDS = 30

# Minimum total traded USDT in window before we evaluate (avoid dust trades)
MIN_WINDOW_NOTIONAL = 5_000  # $5k minimum window volume


class _TradeRecord:
    __slots__ = ("ts", "notional", "is_buy")

    def __init__(self, ts: float, notional: float, is_buy: bool):
        self.ts = ts
        self.notional = notional
        self.is_buy = is_buy


class EventEngine:
    def __init__(self):
        # Per-symbol sliding windows of recent trades
        self._windows: dict[str, deque[_TradeRecord]] = defaultdict(deque)

        # Per-symbol CVD (Cumulative Volume Delta = running buy_vol - sell_vol)
        self._cvd: dict[str, float] = defaultdict(float)

        # Cooldown: last time we fired a cycle for each symbol
        self._last_trigger_time: dict[str, float] = defaultdict(float)

        # Periodic reporting throttle
        self._last_report_time: dict[str, float] = defaultdict(float)

        self.metrics_store = RealtimeMetricsStore()
        
        # Cache for RVOL baseline (baseline_notional, timestamp)
        self._rvol_cache: dict[str, tuple[float, float]] = {}

    # ── Public interface ─────────────────────────────────────────
    async def process_websocket_message(self, stream: str, payload: dict[str, Any]):
        try:
            parts = stream.split("@")
            if len(parts) < 2:
                return
            symbol = parts[0].upper()
            stream_type = parts[1]

            if stream_type == "trade":
                await self._process_trade(symbol, payload)
            elif stream_type.startswith("depth"):
                await self._process_depth(symbol, payload)

        except Exception as exc:
            logger.error(f"EventEngine processing error: {exc}", exc_info=True)

    # ── Trade processing ─────────────────────────────────────────
    async def _process_trade(self, symbol: str, payload: dict[str, Any]):
        price = float(payload.get("p", 0))
        qty   = float(payload.get("q", 0))
        # Binance: m=True means buyer is maker → sell aggressor
        is_buy = not bool(payload.get("m", False))
        notional = price * qty

        now = time.time()

        # ── Update CVD (never resets, long-running delta) ────────
        self._cvd[symbol] += notional if is_buy else -notional
        self.metrics_store.set_metric(symbol, "cvd", self._cvd[symbol])
        self.metrics_store.set_metric(symbol, "last_price", price)

        # ── VWAP from sliding window ─────────────────────────────
        window = self._windows[symbol]
        window.append(_TradeRecord(ts=now, notional=notional, is_buy=is_buy))

        # Evict trades older than WINDOW_SECONDS
        cutoff = now - WINDOW_SECONDS
        while window and window[0].ts < cutoff:
            window.popleft()

        # Aggregate window stats
        buy_notional  = sum(r.notional for r in window if r.is_buy)
        sell_notional = sum(r.notional for r in window if not r.is_buy)
        total_notional = buy_notional + sell_notional

        if total_notional > 0:
            vwap_approx = sum(r.notional for r in window) / len(window)
            self.metrics_store.set_metric(symbol, "vwap", price)  # last trade price as proxy
            imbalance = buy_notional / total_notional
            self.metrics_store.set_metric(symbol, "imbalance", imbalance)
            self.metrics_store.set_metric(symbol, "window_notional", total_notional)

        # ── Periodic log (every 10 s) ────────────────────────────
        if now - self._last_report_time[symbol] > 10 and total_notional >= MIN_WINDOW_NOTIONAL:
            self._last_report_time[symbol] = now
            imb = buy_notional / total_notional if total_notional else 0.5
            cvd = self._cvd[symbol]
            logger.info(
                f"📊 [WS] {symbol} | Price: {price:.6f} | "
                f"Window: ${total_notional:,.0f} | Buy%: {imb*100:.1f}% | CVD: {cvd:+,.0f}"
            )

        # ── Spike detection ──────────────────────────────────────
        if total_notional < MIN_WINDOW_NOTIONAL:
            return  # Too little volume to be meaningful

        imbalance = buy_notional / total_notional
        strongly_directional = imbalance > IMBALANCE_THRESHOLD or imbalance < (1 - IMBALANCE_THRESHOLD)

        if not strongly_directional:
            self.metrics_store.set_metric(symbol, "volume_spike", False)
            return

        # ── RVOL check — use feature snapshot for coin's average volume ──
        rvol = self._get_rvol(symbol, total_notional)
        self.metrics_store.set_metric(symbol, "rvol_live", rvol)

        if rvol < RVOL_TRIGGER_THRESHOLD:
            # Volume directional but not unusual for this coin
            self.metrics_store.set_metric(symbol, "volume_spike", False)
            logger.debug(
                f"[EVENT] {symbol} directional but RVOL={rvol:.2f}x < {RVOL_TRIGGER_THRESHOLD}x, skip."
            )
            return

        # ── Real spike! ──────────────────────────────────────────
        self.metrics_store.set_metric(symbol, "volume_spike", True)
        logger.info(
            f"💥 [SPIKE] {symbol}! RVOL={rvol:.2f}x | Buy%={imbalance*100:.1f}% | "
            f"Window=${total_notional:,.0f} | CVD={self._cvd[symbol]:+,.0f}"
        )

        # Cooldown check
        if now - self._last_trigger_time[symbol] > TRIGGER_COOLDOWN_SECONDS:
            self._last_trigger_time[symbol] = now
            asyncio.create_task(self._trigger_cycle(symbol))
        else:
            remaining = TRIGGER_COOLDOWN_SECONDS - (now - self._last_trigger_time[symbol])
            logger.debug(f"[EVENT] {symbol} cooldown active ({remaining:.0f}s remaining).")

    # ── Order book processing ────────────────────────────────────
    async def _process_depth(self, symbol: str, payload: dict[str, Any]):
        bids = payload.get("bids", [])
        asks = payload.get("asks", [])
        bid_vol = sum(float(p) * float(q) for p, q in bids)
        ask_vol = sum(float(p) * float(q) for p, q in asks)
        total_depth = bid_vol + ask_vol
        if total_depth > 0:
            depth_imbalance = bid_vol / total_depth
            self.metrics_store.set_metric(symbol, "depth_imbalance", depth_imbalance)
            logger.debug(f"[DEPTH] {symbol} | Bid%: {depth_imbalance*100:.1f}% | Depth: ${total_depth:,.0f}")

    # ── RVOL estimation ──────────────────────────────────────────
    def _get_rvol(self, symbol: str, window_notional: float) -> float:
        """
        Compare current 60-second window notional against the coin's
        volume_sma_20 feature (candle-based). If no snapshot is available,
        fall back to a conservative 3× the raw notional threshold.
        """
        now = time.time()
        if symbol in self._rvol_cache:
            baseline, cache_time = self._rvol_cache[symbol]
            if now - cache_time < 900:  # 15 minutes TTL
                if baseline > 0:
                    return round(window_notional / baseline, 2)
                    
        try:
            from crypto_mas.domain.repositories.feature_snapshot_repository import (
                FeatureSnapshotRepository,
            )
            from crypto_mas.infrastructure.db.session import SessionLocal
            from crypto_mas.services.market_data_service.schemas import Exchange

            db = SessionLocal()
            try:
                repo = FeatureSnapshotRepository(db)
                snapshot = repo.get_latest(
                    exchange=Exchange.BINANCE.value,
                    symbol=symbol,
                    timeframe="15m",
                )
                if snapshot and snapshot.features_json:
                    vol_sma = snapshot.features_json.get("volume_sma_20")
                    last_price = self.metrics_store.get_metric(symbol, "last_price", 0.0)
                    if vol_sma and vol_sma > 0 and last_price > 0:
                        # Convert candle volume (coins) → notional (USDT) per 60s slice
                        # 15m candle has 900s; our window is 60s → scale factor ~1/15
                        candle_notional_60s = vol_sma * last_price / 15.0
                        if candle_notional_60s > 0:
                            self._rvol_cache[symbol] = (candle_notional_60s, now)
                            return round(window_notional / candle_notional_60s, 2)
            finally:
                db.close()
        except Exception as exc:
            logger.debug(f"RVOL DB lookup failed for {symbol}: {exc}")

        # Fallback: if we can't get baseline, require $50k to trigger
        return window_notional / 25_000.0

    # ── Cycle trigger ─────────────────────────────────────────────
    async def _trigger_cycle(self, symbol: str):
        logger.warning(f"🚀 [TRIGGER] Firing event-driven HFT cycle for {symbol}")
        from crypto_mas.infrastructure.db.session import SessionLocal
        from crypto_mas.services.market_data_service.provider_factory import (
            get_market_data_provider,
        )
        from crypto_mas.services.market_data_service.schemas import Exchange

        db = SessionLocal()
        try:
            exchange = Exchange("BINANCE")
            provider = get_market_data_provider(exchange)
            cycle_service = TradingCycleService(
                db=db, market_provider=provider, strategy_mode="scalping"
            )
            await cycle_service.run_cycle(
                account_name="default-paper",
                symbols=[symbol],
                timeframe=Timeframe.ONE_MINUTE,
                strategy_name="hft_momentum",
                trigger="EVENT_TRIGGERED",
            )
        except Exception as exc:
            logger.error(f"Event-driven cycle failed for {symbol}: {exc}", exc_info=True)
        finally:
            db.close()
