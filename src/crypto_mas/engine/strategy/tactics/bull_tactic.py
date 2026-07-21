from typing import Any

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.engine.strategy.schemas import (
    DecisionAction,
    TradingDecision,
)
from crypto_mas.engine.strategy.tactics.base_tactic import BaseTactic
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class BullTactic(BaseTactic):
    """
    Bull Market Tactic: Hunts for micro-pullbacks in an established uptrend.
    Only generates CONSIDER_LONG signals.
    """

    def evaluate(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
        params: dict[str, Any],
        is_open: bool = False,
    ) -> TradingDecision | None:
        
        if not snapshots:
            return None

        features = snapshots[-1].features_json
        
        last_price = features.get("close")
        ema_20 = features.get("ema_20")
        ema_50 = features.get("ema_50")
        adx_14 = features.get("adx_14")
        rsi_14 = features.get("rsi_14")
        stoch_k = features.get("stoch_rsi_k")
        
        if None in (last_price, ema_20, ema_50, adx_14, rsi_14):
            return None

        # --- Exit Logic (if position is already open) ---
        if is_open:
            # Simple take profit logic for scalping: 
            # If price extended above EMA20 and RSI is overbought, close.
            dist_to_ema = (last_price - ema_20) / ema_20  # type: ignore
            
            close_factors = []
            should_close = False
            
            # Rule 1: Take Profit (High RSI / Overextended)
            if rsi_14 > 75.0 and dist_to_ema > 0.02:
                should_close = True
                close_factors.append(f"RSI_TP={rsi_14:.1f}")
                close_factors.append(f"EXT={dist_to_ema*100:.2f}%")
                
            # Rule 2: Trend Breakdown (Price crosses below EMA50)
            elif last_price < ema_50:
                should_close = True
                close_factors.append(f"EMA50_BREAK={last_price:.2f}<{ema_50:.2f}")
                
            if should_close:
                return TradingDecision(
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    action=DecisionAction.CLOSE_LONG,
                    confidence=0.9,
                    signal=TradingSignal(
                        symbol=symbol,
                        exchange=exchange,
                        timeframe=timeframe,
                        direction=SignalDirection.NEUTRAL,
                        signal_type=SignalType.MEAN_REVERSION,
                        strength=0.9,
                        timestamp=snapshots[-1].timestamp,
                        reason=f"Exit Setup: {', '.join(close_factors)}"
                    ),
                    score=AssetScore(exchange=exchange, timeframe=timeframe, direction=SignalDirection.NEUTRAL, reason=f"Exit Setup: {', '.join(close_factors)}", timestamp=snapshots[-1].timestamp, symbol=symbol, final_score=0.9, trend_score=0, momentum_score=0, volatility_penalty=0),
                    reason=f"Taking Profit / Closing Long: {', '.join(close_factors)}"
                )
            # If no exit condition is met, hold!
            return TradingDecision(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                action=DecisionAction.HOLD,
                confidence=1.0,
                signal=TradingSignal(
                    symbol=symbol, exchange=exchange, timeframe=timeframe,
                    direction=SignalDirection.LONG, signal_type=SignalType.TREND_FOLLOWING, strength=1.0, timestamp=snapshots[-1].timestamp, reason="Holding"
                ),
                score=AssetScore(exchange=exchange, timeframe=timeframe, direction=SignalDirection.LONG, reason="Holding", timestamp=snapshots[-1].timestamp, symbol=symbol, final_score=1.0, trend_score=1.0, momentum_score=1.0, volatility_penalty=0),
                reason="Holding open long position."
            )

        # --- Parameters ---
        min_adx = params.get("min_adx", 25.0)
        max_dist_ema = params.get("max_dist_ema", 0.006)
        min_dist_ema = params.get("min_dist_ema", -0.012)
        rsi_threshold = params.get("rsi_threshold", 42.0)
        stoch_threshold = params.get("stoch_threshold", 20.0)
        min_confidence = params.get("min_confidence", 0.55)
        
        confidence = 0.0
        factors = []

        # ── Gate 1: Trend Identification ────────────────────────
        if adx_14 < min_adx:
            return None
            
        factors.append(f"TREND(ADX={adx_14:.1f})")

        # ── Gate 2: Micro-Pullback to EMA 20 ────────────────────
        dist_to_ema = (last_price - ema_20) / ema_20  # type: ignore
        
        if dist_to_ema > max_dist_ema or dist_to_ema < min_dist_ema:
            return None
            
        factors.append(f"LONG_PB({dist_to_ema*100:.2f}%)")
        confidence += 0.55

        # ── Gate 3: Oversold Momentum ───────────────────────────
        if rsi_14 < rsi_threshold:
            bonus = min(0.25, (rsi_threshold - rsi_14) * 0.015)
            confidence += 0.10 + bonus
            factors.append(f"RSI={rsi_14:.1f}")
        elif stoch_k is not None and stoch_k < stoch_threshold:
            bonus = min(0.25, (stoch_threshold - stoch_k) * 0.015)
            confidence += 0.10 + bonus
            factors.append(f"STOCH={stoch_k:.1f}")
        else:
            return None

        # ── Bonus Factors (Scalping Logic) ────────────────────────
        from crypto_mas.engine.strategy.realtime_metrics import RealtimeMetricsStore
        store = RealtimeMetricsStore()
        
        imbalance = store.get_metric(symbol, "imbalance", 0.5)
        if imbalance > 0.60:
            confidence += 0.15
            factors.append(f"TF_IMB={imbalance*100:.1f}%")
            
        depth_imbalance = store.get_metric(symbol, "depth_imbalance", 0.5)
        if depth_imbalance > 0.55:
            confidence += 0.10
            factors.append(f"DEPTH={depth_imbalance*100:.1f}%")

        confidence = max(0.0, min(confidence, 0.99))

        if confidence < min_confidence:
            return None

        reason = " | ".join(factors)

        now = snapshots[-1].timestamp if snapshots else None

        signal = TradingSignal(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            signal_type=SignalType.TREND_FOLLOWING,
            direction=SignalDirection.LONG,
            strength=confidence,
            reason=reason,
            timestamp=now  # type: ignore
        )

        score = AssetScore(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            direction=SignalDirection.LONG,
            final_score=confidence,
            trend_score=min(1.0, adx_14 / 50.0),  # type: ignore
            momentum_score=min(1.0, (100.0 - rsi_14) / 100.0),  # type: ignore
            volatility_penalty=0.0,
            reason=reason,
            timestamp=now  # type: ignore
        )

        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=DecisionAction.CONSIDER_LONG,
            confidence=confidence,
            signal=signal,
            score=score,
            reason=reason,
        )
