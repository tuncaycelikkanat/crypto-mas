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


class BearTactic(BaseTactic):
    """
    Bear Market Tactic: Hunts for micro-pullbacks (upwards) in an established downtrend.
    Only generates CONSIDER_SHORT signals.
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
        rvol = features.get("rvol")
        macd_hist = features.get("macd_hist")
        
        # Get previous macd to check momentum
        prev_macd_hist = None
        if len(snapshots) > 1:
            prev_macd_hist = snapshots[-2].features_json.get("macd_hist")
        
        if last_price is None or ema_20 is None or ema_50 is None or adx_14 is None or rsi_14 is None:
            return None

        # --- Exit Logic (if position is already open) ---
        if is_open:
            # Simple take profit logic for scalping: 
            # If price extended below EMA20 and RSI is oversold, close.
            dist_to_ema = (last_price - ema_20) / ema_20  # type: ignore
            
            close_factors = []
            should_close = False
            
            # Rule 1: Low RSI (Oversold) + Overextended downwards
            # Rule 1: Low RSI (Oversold) + Overextended downwards
            tp_rsi = params.get("tp_rsi", 36.0)
            tp_dist_ema = params.get("tp_dist_ema", -0.007)
            
            if rsi_14 < tp_rsi and dist_to_ema < tp_dist_ema:
                should_close = True
                close_factors.append(f"RSI={rsi_14:.1f}")
                close_factors.append(f"EXT={dist_to_ema*100:.2f}%")
                
            # Rule 2: Trend Breakdown (Price crosses above EMA50 robustly)
            panic_drop_pct = params.get("panic_drop_pct", 0.02)
            deep_break = last_price > (ema_50 * (1.0 + panic_drop_pct))
            
            prev_close = snapshots[-2].features_json.get("close") if len(snapshots) >= 2 else None
            prev_ema50 = snapshots[-2].features_json.get("ema_50") if len(snapshots) >= 2 else None
            
            consecutive_break = False
            if prev_close and prev_ema50:
                if prev_close > prev_ema50 and last_price > (ema_50 * (1.0 + (panic_drop_pct / 2))):
                    consecutive_break = True
                    
            if deep_break or consecutive_break:
                should_close = True
                close_factors.append(f"EMA50_BREAK={last_price:.2f}>{ema_50:.2f}")

            # Rule 3: Fast Momentum Exit (Capital Preservation in Bear Rallies)
            if macd_hist is not None and prev_macd_hist is not None:
                if macd_hist > 0 and prev_macd_hist <= 0:
                    should_close = True
                    close_factors.append("MACD_FLIP_BULLISH")
                
            if should_close:
                return TradingDecision(
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    action=DecisionAction.CLOSE_SHORT,
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
                    reason=f"Taking Profit / Closing Short: {', '.join(close_factors)}"
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
                    direction=SignalDirection.SHORT, signal_type=SignalType.TREND_FOLLOWING, strength=1.0, timestamp=snapshots[-1].timestamp, reason="Holding"
                ),
                score=AssetScore(exchange=exchange, timeframe=timeframe, direction=SignalDirection.SHORT, reason="Holding", timestamp=snapshots[-1].timestamp, symbol=symbol, final_score=1.0, trend_score=1.0, momentum_score=1.0, volatility_penalty=0),
                reason="Holding open short position."
            )

        # --- Parameters ---
        min_adx = params.get("min_adx", 24.0)
        min_dist_ema = params.get("min_dist_ema", 0.014)
        max_dist_ema = params.get("max_dist_ema", 0.030)
        rsi_threshold = params.get("rsi_threshold", 50.0)
        stoch_threshold = params.get("stoch_threshold", 80.0)
        min_confidence = params.get("min_confidence", 0.45)
        
        # Override ATR multipliers for broker execution
        sl_mult_override = params.get("sl_mult", 1.5)
        tp_mult_override = params.get("tp_mult", 2.0)

        confidence = 0.0
        factors = []

        # ── Gate 1: Trend Identification ────────────────────────
        if adx_14 < min_adx:
            return None
            
        factors.append(f"TREND(ADX={adx_14:.1f})")

        # ── Gate 2: Entry Triggers (Pullback OR Breakdown) ──────
        dist_to_ema = (last_price - ema_20) / ema_20  # type: ignore
        
        is_pullback = min_dist_ema <= dist_to_ema <= max_dist_ema
        
        # Breakdown condition: Price is below EMA20, MACD is negative and dropping, RSI is not yet oversold (< 25)
        is_breakdown = False
        if dist_to_ema < 0 and macd_hist is not None and prev_macd_hist is not None:
            if macd_hist < 0 and macd_hist < prev_macd_hist:
                if 25.0 <= rsi_14 < 45.0:
                    is_breakdown = True
                    
        if not is_pullback and not is_breakdown:
            return None

        max_rvol_pullback = params.get("max_rvol_pullback", 1.5)

        if is_pullback:
            # ── Gate 2.1: Volume Filter (Don't short squeezes) ──────
            if rvol is not None and rvol > max_rvol_pullback:
                return None
                
            # ── Gate 2.2: Momentum Confirmation (MACD) ──────────────
            if macd_hist is not None and prev_macd_hist is not None:
                if macd_hist > 0 and macd_hist > prev_macd_hist:
                    return None
                
            factors.append(f"SHORT_PB({dist_to_ema*100:.2f}%)")
            confidence += 0.40  # Base confidence (C-Grade)

            # ── Gate 3: Overbought Momentum & Bonuses ───────────────
            if rsi_14 > rsi_threshold:
                factors.append(f"RSI={rsi_14:.1f}")
                if rsi_14 > 60.0:
                    confidence += 0.20
                else:
                    confidence += 0.10
            elif stoch_k is not None and stoch_k > stoch_threshold:
                factors.append(f"STOCH={stoch_k:.1f}")
                if stoch_k > 80.0:
                    confidence += 0.15
                else:
                    confidence += 0.05
            else:
                return None
                
        elif is_breakdown:
            factors.append(f"SHORT_BREAKDOWN(MACD={macd_hist:.2f})")
            confidence += 0.60  # Base confidence (B-Grade)
            if rvol is not None and rvol > 1.2:
                factors.append(f"RVOL={rvol:.1f}")
                confidence += 0.20  # A-Grade if high volume breakdown
            
            # For breakdowns, use tighter overrides for the broker
            sl_mult_override = params.get("breakdown_sl_mult", 1.2)
            tp_mult_override = params.get("breakdown_tp_mult", 1.5)
            
        # ── Bonus Factors (A-Grade Boosters) ────────────────────
        # 1. MACD strong deterioration
        if macd_hist is not None and prev_macd_hist is not None:
            if macd_hist < prev_macd_hist * 1.5 or macd_hist < 0:
                confidence += 0.15
                factors.append("MACD_DUMP")

        # 2. Volume confirmation
        if rvol is not None and 1.0 < rvol <= max_rvol_pullback:
            confidence += 0.10
            factors.append(f"RVOL={rvol:.1f}")

        from crypto_mas.engine.strategy.realtime_metrics import RealtimeMetricsStore
        store = RealtimeMetricsStore()
        
        imbalance = store.get_metric(symbol, "imbalance", 0.5)
        if imbalance < 0.40:
            confidence += 0.10
            factors.append(f"TF_IMB={imbalance*100:.0f}%")
            
        depth_imbalance = store.get_metric(symbol, "depth_imbalance", 0.5)
        if depth_imbalance < 0.45:
            confidence += 0.10
            factors.append(f"DEPTH={depth_imbalance*100:.0f}%")

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
            direction=SignalDirection.SHORT,
            strength=confidence,
            reason=reason,
            timestamp=now  # type: ignore
        )

        score = AssetScore(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            direction=SignalDirection.SHORT,
            final_score=confidence,
            trend_score=min(1.0, adx_14 / 50.0),  # type: ignore
            momentum_score=min(1.0, rsi_14 / 100.0),  # type: ignore
            volatility_penalty=0.0,
            reason=reason,
            timestamp=now  # type: ignore
        )

        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=DecisionAction.CONSIDER_SHORT,
            confidence=confidence,
            signal=signal,
            score=score,
            reason=reason,
            metadata={
                "sl_mult_override": sl_mult_override,
                "tp_mult_override": tp_mult_override,
            }
        )
