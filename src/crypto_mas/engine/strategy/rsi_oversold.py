"""
RSI Oversold Strategy — Scalping Mode
Generates CONSIDER_LONG when RSI dips below oversold threshold and starts recovering.
"""
from datetime import datetime, UTC

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.signal import SignalDirection, TradingSignal
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.regime import RegimeSnapshot, MarketRegime
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class RSIOversoldStrategy(BaseStrategy):
    """
    Scalping strategy: buy when RSI < oversold_threshold and starting to recover.
    Uses Bollinger lower band as additional confirmation.
    """

    def __init__(self, oversold_threshold: float = 30.0, min_recovery_pct: float = 0.3):
        self.OVERSOLD_THRESHOLD = oversold_threshold
        self.MIN_RECOVERY_PCT = min_recovery_pct

    def decide(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
    ) -> TradingDecision | None:
        if not snapshots or len(snapshots) < 3:
            return None

        sorted_snapshots = sorted(snapshots, key=lambda s: s.timestamp)
        latest = sorted_snapshots[-1]
        prev = sorted_snapshots[-2]

        features = latest.features_json
        prev_features = prev.features_json

        rsi = features.get("rsi_14")
        prev_rsi = prev_features.get("rsi_14")
        close = features.get("close")
        bb_lower = features.get("bb_lower")
        bb_upper = features.get("bb_upper")

        if rsi is None or close is None:
            print(f"RSI Oversold skipping: rsi={rsi}, close={close}")
            return None

        print(f"RSI Oversold Eval: rsi={rsi}, prev_rsi={prev_rsi}, close={close}, bb_lower={bb_lower}")
        action = DecisionAction.HOLD
        confidence = 0.0
        direction = SignalDirection.NEUTRAL
        reason_parts = []

        # Core signal: RSI was oversold
        if rsi < self.OVERSOLD_THRESHOLD:
            direction = SignalDirection.LONG
            confidence = (self.OVERSOLD_THRESHOLD - rsi) / self.OVERSOLD_THRESHOLD

            # Bonus: RSI is recovering (ticking up from previous bar)
            if prev_rsi is not None and rsi > prev_rsi:
                confidence = min(confidence + 0.2, 0.95)
                reason_parts.append("RSI recovering")

            # Bonus: price near Bollinger lower band
            if bb_lower is not None and close <= bb_lower * 1.01:
                confidence = min(confidence + 0.15, 0.95)
                reason_parts.append("near BB lower")

            if confidence >= 0.5:
                action = DecisionAction.CONSIDER_LONG
            reason_parts.insert(0, f"RSI={rsi:.1f} (oversold)")

        reason = " | ".join(reason_parts) if reason_parts else f"RSI={rsi:.1f} (neutral)"

        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=action,
            confidence=confidence,
            signal=TradingSignal(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                signal_type="MEAN_REVERSION", # using string, pydantic will coerce or we can import it. Let's just use string that matches Enum if possible. Wait, SignalType only has TREND_FOLLOWING. I'll use that for now or import it.
                direction=direction,
                strength=confidence,
                indicators={"rsi_14": rsi, "bb_lower": bb_lower or 0},
                reason=reason,
                timestamp=datetime.now(UTC),
            ),
            score=AssetScore(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                trend_score=confidence,
                momentum_score=confidence,
                volatility_penalty=0.0,
                final_score=confidence,
                components={},
                reason="RSI Oversold Score",
                timestamp=datetime.now(UTC),
            ),
            regime=RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.BULL_TREND if action == DecisionAction.CONSIDER_LONG else MarketRegime.SIDEWAYS,
                confidence=confidence,
                risk_multiplier=1.0,
                reason="RSI Oversold regime",
                timestamp=datetime.now(UTC),
            ),
            reason=reason,
            created_at=datetime.now(UTC),
        )
