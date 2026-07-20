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
    ) -> TradingDecision | None:
        
        if not snapshots:
            return None

        features = snapshots[-1].features_json
        
        last_price = features.get("close")
        ema_20 = features.get("ema_20")
        ema_50 = features.get("ema_50")
        adx_14 = features.get("adx_14")
        rsi_14 = features.get("rsi_14")
        stoch_k = features.get("stoch_k")
        
        if None in (last_price, ema_20, ema_50, adx_14, rsi_14):
            return None

        # --- Parameters ---
        min_adx = params.get("min_adx", 25.0)
        max_dist_ema = params.get("max_dist_ema", 0.006)
        min_dist_ema = params.get("min_dist_ema", -0.012)
        rsi_threshold = params.get("rsi_threshold", 42.0)
        stoch_threshold = params.get("stoch_threshold", 20.0)
        min_confidence = params.get("min_confidence", 0.70)
        
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
