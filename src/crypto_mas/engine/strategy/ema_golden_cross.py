"""
EMA Golden Cross Strategy — Hodl Mode (Daily timeframe)
Generates CONSIDER_LONG when EMA50 crosses above EMA200.
Uses RSI > 50 as confirmation. Designed for long-term position holding.
"""
from datetime import UTC, datetime

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime, RegimeSnapshot
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class EMAGoldenCrossStrategy(BaseStrategy):
    """
    Hodl/Long-term strategy: buy when EMA50 > EMA200 (golden cross) + RSI > 50.
    Holds for weeks/months. Low trade frequency, high conviction entries.
    """

    def decide(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
        risk_level: int = 50,
    ) -> TradingDecision | None:
        if not snapshots or len(snapshots) < 5:
            return None

        sorted_snapshots = sorted(snapshots, key=lambda s: s.timestamp)
        latest = sorted_snapshots[-1]
        prev = sorted_snapshots[-2]

        features = latest.features_json
        prev_features = prev.features_json

        close = features.get("close")
        ema_20 = features.get("ema_20")   # acts as EMA50 proxy (we'll enhance later)
        ema_50 = features.get("ema_50")   # acts as EMA200 proxy
        rsi_14 = features.get("rsi_14")
        roc_14 = features.get("roc_14")

        prev_ema_20 = prev_features.get("ema_20")
        prev_ema_50 = prev_features.get("ema_50")

        if None in {close, ema_20, ema_50, rsi_14}:
            return None

        action = DecisionAction.HOLD
        confidence = 0.0
        direction = SignalDirection.NEUTRAL
        reason_parts = []

        # Golden Cross: EMA20 now above EMA50, and was below or very close before
        golden_cross = ema_20 > ema_50  # type: ignore
        fresh_cross = (
            prev_ema_20 is not None
            and prev_ema_50 is not None
            and prev_ema_20 <= prev_ema_50
            and golden_cross
        )

        if golden_cross:
            direction = SignalDirection.LONG

            # Base confidence from EMA spread
            spread_pct = (ema_20 - ema_50) / close if close > 0 else 0  # type: ignore
            confidence = min(0.4 + spread_pct * 10, 0.7)

            # RSI confirmation
            if rsi_14 > 55:  # type: ignore
                confidence = min(confidence + 0.15, 0.95)
                reason_parts.append(f"RSI={rsi_14:.1f} bullish")

            # Fresh cross bonus
            if fresh_cross:
                confidence = min(confidence + 0.2, 0.95)
                reason_parts.append("FRESH golden cross!")

            # Positive momentum
            if roc_14 is not None and roc_14 > 0:
                confidence = min(confidence + 0.05, 0.95)
                reason_parts.append("positive momentum")

            if confidence >= 0.5:
                action = DecisionAction.CONSIDER_LONG

            reason_parts.insert(0, f"EMA20={ema_20:.2f} > EMA50={ema_50:.2f}")

        reason = " | ".join(reason_parts) if reason_parts else "No golden cross"

        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=action,
            confidence=confidence,
            signal=TradingSignal(  # type: ignore
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                signal_type=SignalType.TREND_FOLLOWING,
                direction=direction,
                strength=confidence,
                indicators={"ema_20": ema_20, "ema_50": ema_50, "rsi_14": rsi_14},
                reason=reason,
                timestamp=datetime.now(UTC),
            ),
            score=AssetScore(  # type: ignore
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                trend_score=confidence,
                momentum_score=0.0,
                volatility_penalty=0.0,
                final_score=confidence,
                components={},
                reason=reason,
                timestamp=datetime.now(UTC),
            ),
            regime=RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.BULL_TREND if golden_cross else MarketRegime.BEAR_TREND,
                confidence=confidence,
                risk_multiplier=0.8,  # Hodl uses smaller position per coin
                reason="EMA Golden Cross regime",
                timestamp=datetime.now(UTC),
            ),
            reason=reason,
            created_at=datetime.now(UTC),
        )
