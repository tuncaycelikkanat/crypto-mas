from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.math.jit_calculators import jit_calculate_confidence
from crypto_mas.engine.regime import MarketRegime
from crypto_mas.engine.regime.regime import RegimeEngine
from crypto_mas.engine.scoring.scoring import ScoringEngine
from crypto_mas.engine.signal import SignalDirection
from crypto_mas.engine.signal.trend import TrendSignalEngine
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class MultiAgentStrategy(BaseStrategy):
    def __init__(
        self,
        signal_agent: TrendSignalEngine | None = None,
        scoring_agent: ScoringEngine | None = None,
        regime_agent: RegimeEngine | None = None,
        time_provider: TimeProvider | None = None,
    ) -> None:
        self.signal_agent = signal_agent or TrendSignalEngine()
        self.scoring_agent = scoring_agent or ScoringEngine()
        self.regime_agent = regime_agent or RegimeEngine()
        self.time_provider = time_provider or SystemTimeProvider()

    def decide(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
        risk_level: int = 50,
        use_regime_shield: bool = True,
    ) -> TradingDecision | None:
        signal = self.signal_agent.generate(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            snapshots=snapshots,
        )

        if signal is None:
            return None

        score = self.scoring_agent.score(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            snapshots=snapshots,
        )

        if score is None:
            return None

        regime = self.regime_agent.detect(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            snapshots=snapshots,
        )

        if regime is None:
            return None

        action = self._decide_action(
            direction=signal.direction,
            final_score=score.final_score,
            regime=regime.regime,
            risk_level=risk_level,
            use_regime_shield=use_regime_shield,
        )

        confidence = jit_calculate_confidence(
            score=score.final_score,
            regime_confidence=regime.confidence,
            risk_multiplier=regime.risk_multiplier,
        )

        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=action,
            confidence=confidence,
            signal=signal,
            score=score,
            regime=regime,
            reason=self._build_reason(action, score.final_score, regime.regime),
            created_at=self.time_provider.now(),
        )

    @staticmethod
    def _decide_action(
        direction: SignalDirection,
        final_score: float,
        regime: MarketRegime,
        risk_level: int = 50,
        use_regime_shield: bool = True,
    ) -> DecisionAction:
        # Dynamic threshold: risk=0→0.50, risk=50→0.375, risk=100→0.25 (allows negative threshold if risk > 200)
        threshold = max(-1.0, 0.50 - (risk_level / 100) * 0.25)

        if use_regime_shield:
            if regime == MarketRegime.HIGH_VOLATILITY:
                return DecisionAction.AVOID

        if direction == SignalDirection.LONG:
            if use_regime_shield and regime == MarketRegime.BEAR_TREND:
                threshold += 0.15  # Require stronger signal instead of outright AVOID

            if final_score >= threshold:
                return DecisionAction.CONSIDER_LONG

            return DecisionAction.HOLD

        if direction == SignalDirection.SHORT:
            if use_regime_shield and regime == MarketRegime.BULL_TREND:
                threshold += 0.15  # Require stronger signal instead of outright AVOID

            if final_score >= threshold:
                return DecisionAction.CONSIDER_SHORT

            return DecisionAction.HOLD

        return DecisionAction.HOLD



    @staticmethod
    def _build_reason(
        action: DecisionAction,
        final_score: float,
        regime: MarketRegime,
    ) -> str:
        return (
            f"Action={action.value}. Final score={final_score:.3f}. Market regime={regime.value}."
        )
