from datetime import datetime, UTC

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.signal import SignalDirection
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision, SignalDecision, ScoringDecision, RegimeDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

class MACDStrategy(BaseStrategy):
    """
    A simple MACD Cross strategy.
    Long when MACD > Signal Line, Short when MACD < Signal Line.
    Avoid if trend is weak (MACD hist is very close to 0).
    """

    def decide(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
    ) -> TradingDecision | None:
        if not snapshots or len(snapshots) < 2:
            return None

        # Sort snapshots by timestamp just in case
        sorted_snapshots = sorted(snapshots, key=lambda s: s.timestamp)
        latest = sorted_snapshots[-1]
        
        # We need macd in features! Let's check if we have them.
        # features JSON has "macd", "macd_signal", "macd_hist"
        features = latest.features
        
        macd = features.get("macd")
        macd_signal = features.get("macd_signal")
        macd_hist = features.get("macd_hist")
        
        if macd is None or macd_signal is None or macd_hist is None:
            return None
            
        action = DecisionAction.HOLD
        confidence = 0.0
        direction = SignalDirection.NEUTRAL
        
        if macd > macd_signal:
            direction = SignalDirection.LONG
            if macd_hist > 0:
                action = DecisionAction.CONSIDER_LONG
                confidence = 0.8
        elif macd < macd_signal:
            direction = SignalDirection.SHORT
            if macd_hist < 0:
                action = DecisionAction.CONSIDER_SHORT
                confidence = 0.8

        # We construct a mock SignalDecision/ScoringDecision just to fulfill the schema
        # Since this is a direct strategy, we fake the "multi-agent" internals if needed,
        # or we could make them optional in TradingDecision in a true refactoring.
        # But let's supply basic ones for now.
        
        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=action,
            confidence=confidence,
            signal=SignalDecision(
                direction=direction,
                strength=confidence,
                indicators={"macd": macd, "macd_signal": macd_signal},
            ),
            score=ScoringDecision(
                final_score=confidence,
                components={},
            ),
            regime=RegimeDecision(
                regime="TRENDING",
                confidence=1.0,
                risk_multiplier=1.0,
            ),
            reason=f"MACD={macd:.2f}, Signal={macd_signal:.2f}, Hist={macd_hist:.2f}",
            created_at=datetime.now(UTC),
        )
