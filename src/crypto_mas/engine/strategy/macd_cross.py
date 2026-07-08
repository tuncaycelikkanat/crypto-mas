from datetime import datetime, UTC

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.regime import RegimeSnapshot, MarketRegime
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
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
        features = latest.features_json
        
        macd = features.get("macd")
        macd_signal = features.get("macd_signal")
        macd_hist = features.get("macd_hist")
        
        if macd is None or macd_signal is None or macd_hist is None:
            return None
            
        action = DecisionAction.HOLD
        confidence = 0.0
        direction = SignalDirection.NEUTRAL

        # Normalize histogram vs price to get a meaningful confidence
        price = features.get("close") or 1.0
        hist_pct = abs(macd_hist) / price if price > 0 else 0.0

        # Minimum threshold: histogram must be at least 0.02% of price (filters noise)
        MIN_HIST_PCT = 0.0002

        if macd > macd_signal and macd_hist > 0 and hist_pct >= MIN_HIST_PCT:
            direction = SignalDirection.LONG
            action = DecisionAction.CONSIDER_LONG
            # Confidence scales with signal strength, capped at 0.95
            confidence = min(0.5 + (hist_pct * 200), 0.95)
        elif macd < macd_signal and macd_hist < 0 and hist_pct >= MIN_HIST_PCT:
            direction = SignalDirection.SHORT
            # For paper trading we don't short, but we track the direction
            action = DecisionAction.HOLD
            confidence = 0.0

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
                signal_type=SignalType.TREND_FOLLOWING,
                direction=direction,
                strength=confidence,
                indicators={"macd": macd, "macd_signal": macd_signal},
                reason="MACD Cross",
                timestamp=datetime.now(UTC),
            ),
            score=AssetScore(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                trend_score=confidence,
                momentum_score=0.0,
                volatility_penalty=0.0,
                final_score=confidence,
                components={},
                reason="MACD Cross",
                timestamp=datetime.now(UTC),
            ),
            regime=RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.BULL_TREND,
                confidence=1.0,
                risk_multiplier=1.0,
                reason="Default",
                timestamp=datetime.now(UTC),
            ),
            reason=f"MACD={macd:.2f}, Signal={macd_signal:.2f}, Hist={macd_hist:.2f}",
            created_at=datetime.now(UTC),
        )
