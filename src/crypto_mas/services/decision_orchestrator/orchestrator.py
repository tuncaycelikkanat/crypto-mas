from crypto_mas.agents.regime_agent.regime_agent import RegimeAgent
from crypto_mas.agents.regime_agent.schemas import MarketRegime
from crypto_mas.agents.scoring_agent.scoring_agent import ScoringAgent
from crypto_mas.agents.signal_agent.schemas import SignalDirection
from crypto_mas.agents.signal_agent.trend_agent import TrendSignalAgent
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.decision_orchestrator.schemas import DecisionAction, TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class DecisionOrchestrator:
    def __init__(
        self,
        signal_agent: TrendSignalAgent | None = None,
        scoring_agent: ScoringAgent | None = None,
        regime_agent: RegimeAgent | None = None,
        time_provider: TimeProvider | None = None,
    ) -> None:
        self.signal_agent = signal_agent or TrendSignalAgent()
        self.scoring_agent = scoring_agent or ScoringAgent()
        self.regime_agent = regime_agent or RegimeAgent()
        self.time_provider = time_provider or SystemTimeProvider()

    def run(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
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
        )

        confidence = self._calculate_confidence(
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
    ) -> DecisionAction:
        if regime == MarketRegime.HIGH_VOLATILITY:
            return DecisionAction.AVOID

        if direction == SignalDirection.LONG:
            if regime == MarketRegime.BEAR_TREND:
                return DecisionAction.AVOID

            if final_score >= 0.35:
                return DecisionAction.CONSIDER_LONG

            return DecisionAction.HOLD

        if direction == SignalDirection.SHORT:
            if regime == MarketRegime.BULL_TREND:
                return DecisionAction.AVOID

            if final_score >= 0.35:
                return DecisionAction.CONSIDER_SHORT

            return DecisionAction.HOLD

        return DecisionAction.HOLD

    @staticmethod
    def _calculate_confidence(
        score: float,
        regime_confidence: float,
        risk_multiplier: float,
    ) -> float:
        raw = score * 0.65 + regime_confidence * 0.35
        adjusted = raw * risk_multiplier

        return max(0.0, min(adjusted, 1.0))

    @staticmethod
    def _build_reason(
        action: DecisionAction,
        final_score: float,
        regime: MarketRegime,
    ) -> str:
        return (
            f"Action={action.value}. Final score={final_score:.3f}. Market regime={regime.value}."
        )
