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


class SidewaysTactic(BaseTactic):
    """
    Sideways Market Tactic: Hunts for mean reversion opportunities when the market is ranging.
    Can generate both CONSIDER_LONG (at support) and CONSIDER_SHORT (at resistance).
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
        rsi_14 = features.get("rsi_14")
        bb_upper = features.get("bb_upper")
        bb_lower = features.get("bb_lower")
        
        if None in (last_price, rsi_14, bb_upper, bb_lower):
            return None

        # --- Exit Logic (if position is already open) ---
        if is_open:
            # In sideways, we close when it reaches the middle band or the opposite band
            close_factors = []
            should_close_long = False
            should_close_short = False
            
            # If price hits upper band, close long
            if last_price >= bb_upper:
                should_close_long = True
                close_factors.append(f"HIT_RESISTANCE={last_price:.2f}")
            # If price hits lower band, close short
            elif last_price <= bb_lower:
                should_close_short = True
                close_factors.append(f"HIT_SUPPORT={last_price:.2f}")
            # Close anything if RSI flips extreme
            elif rsi_14 > 65.0:
                should_close_long = True
                close_factors.append(f"RSI_HIGH={rsi_14:.1f}")
            elif rsi_14 < 35.0:
                should_close_short = True
                close_factors.append(f"RSI_LOW={rsi_14:.1f}")

            # Note: We don't know the exact side of the open position here.
            # But PortfolioEngine will close whatever position is open if we emit CLOSE_LONG or CLOSE_SHORT
            # To be safe, we can just emit both or just HOLD if we don't have enough confidence.
            # Actually, `PortfolioEngine` removes the symbol if CLOSE_LONG or CLOSE_SHORT is emitted.
            # So emitting CLOSE_LONG will close a SHORT position too in our current paper broker logic!
            if should_close_long or should_close_short:
                return TradingDecision(
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    action=DecisionAction.CLOSE_LONG,  # Just sending CLOSE to drop it from target
                    confidence=0.9,
                    signal=TradingSignal(
                        symbol=symbol, exchange=exchange, timeframe=timeframe,
                        direction=SignalDirection.NEUTRAL, signal_type=SignalType.MEAN_REVERSION, strength=0.9, timestamp=snapshots[-1].timestamp, reason="Exit Sideways"
                    ),
                    score=AssetScore(exchange=exchange, timeframe=timeframe, direction=SignalDirection.NEUTRAL, reason=f"Closing Sideways Trade: {', '.join(close_factors)}", timestamp=snapshots[-1].timestamp, symbol=symbol, final_score=0.9, trend_score=0, momentum_score=0, volatility_penalty=0),
                    reason=f"Closing Sideways Trade: {', '.join(close_factors)}"
                )
            
            return TradingDecision(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                action=DecisionAction.HOLD,
                confidence=1.0,
                signal=TradingSignal(
                    symbol=symbol, exchange=exchange, timeframe=timeframe,
                    direction=SignalDirection.NEUTRAL, signal_type=SignalType.MEAN_REVERSION, strength=1.0, timestamp=snapshots[-1].timestamp, reason="Holding"
                ),
                score=AssetScore(exchange=exchange, timeframe=timeframe, direction=SignalDirection.NEUTRAL, reason="Holding open sideways position.", timestamp=snapshots[-1].timestamp, symbol=symbol, final_score=1.0, trend_score=0, momentum_score=0, volatility_penalty=0),
                reason="Holding open sideways position."
            )

        # --- Parameters ---
        # Sideways markets require wider RSI extremes to avoid chop
        rsi_oversold = params.get("rsi_oversold", 30.0)
        rsi_overbought = params.get("rsi_overbought", 70.0)
        min_confidence = params.get("min_confidence", 0.70)
        
        # In sideways, we want tighter TP (revert to mean) and wider SL (allow chop)
        sl_mult_override = params.get("sl_mult", 2.5)
        tp_mult_override = params.get("tp_mult", 2.0)

        confidence = 0.0
        factors = []
        action = DecisionAction.HOLD
        direction = SignalDirection.NEUTRAL

        # ── Gate 1: Mean Reversion using Bollinger Bands & RSI ──
        if last_price <= bb_lower and rsi_14 < rsi_oversold:  # type: ignore
            action = DecisionAction.CONSIDER_LONG
            direction = SignalDirection.LONG
            confidence = 0.75
            factors.append("BB_LOWER_TOUCH")
            factors.append(f"RSI={rsi_14:.1f}")

        elif last_price >= bb_upper and rsi_14 > rsi_overbought:  # type: ignore
            action = DecisionAction.CONSIDER_SHORT
            direction = SignalDirection.SHORT
            confidence = 0.75
            factors.append("BB_UPPER_TOUCH")
            factors.append(f"RSI={rsi_14:.1f}")

        else:
            return None

        if confidence < min_confidence:
            return None

        reason = " | ".join(factors)

        now = snapshots[-1].timestamp if snapshots else None

        signal = TradingSignal(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            signal_type=SignalType.MEAN_REVERSION,
            direction=direction,
            strength=confidence,
            reason=reason,
            timestamp=now  # type: ignore
        )

        score = AssetScore(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            final_score=confidence,
            trend_score=0.5,
            momentum_score=0.8,
            volatility_penalty=0.0,
            reason=reason,
            timestamp=now  # type: ignore
        )

        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=action,
            confidence=confidence,
            signal=signal,
            score=score,
            reason=reason,
            metadata={
                "sl_mult_override": sl_mult_override,
                "tp_mult_override": tp_mult_override,
            }
        )
