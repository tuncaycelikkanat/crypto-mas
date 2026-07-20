import logging
from typing import Any

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime
from crypto_mas.engine.regime.regime import RegimeEngine
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.schemas import TradingDecision
from crypto_mas.engine.strategy.tactics.base_tactic import BaseTactic
from crypto_mas.engine.strategy.tactics.bear_tactic import BearTactic
from crypto_mas.engine.strategy.tactics.bull_tactic import BullTactic
from crypto_mas.engine.strategy.tactics.sideways_tactic import SidewaysTactic
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

logger = logging.getLogger(__name__)


class RegimeAdaptiveStrategy(BaseStrategy):
    """
    A dynamic strategy that detects the current market regime and delegates
    the trading decision to a specialized tactic for that regime.
    """

    def __init__(self, time_provider: TimeProvider | None = None) -> None:
        self.time_provider = time_provider or SystemTimeProvider()
        self.regime_engine = RegimeEngine()
        
        # Initialize tactics
        self.tactics: dict[MarketRegime, BaseTactic] = {
            MarketRegime.BULL_TREND: BullTactic(),
            MarketRegime.BEAR_TREND: BearTactic(),
            MarketRegime.SIDEWAYS: SidewaysTactic(),
        }

    def decide(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
        risk_level: int = 50,
        **kwargs: Any
    ) -> TradingDecision | None:
        
        if not snapshots:
            return None

        # 1. Detect Market Regime
        regime_snapshot = self.regime_engine.detect(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            snapshots=snapshots,
        )

        regime = regime_snapshot.regime  # type: ignore
        
        # 2. Extract Nested Parameters or use Defaults
        # config_json from the UI is passed via kwargs (or kwargs could contain a 'config' dict)
        config = kwargs.get("config", {})
        
        tactic_params = {}
        if regime == MarketRegime.BULL_TREND:
            tactic_params = config.get("bull_tactic", {})
        elif regime == MarketRegime.BEAR_TREND:
            tactic_params = config.get("bear_tactic", {})
        elif regime == MarketRegime.SIDEWAYS:
            tactic_params = config.get("sideways_tactic", {})

        # Add the global risk_level so tactics can use it if they want
        tactic_params["risk_level"] = risk_level

        # 3. Route to the appropriate Tactic
        tactic = self.tactics.get(regime)
        
        if not tactic:
            # E.g. HIGH_VOLATILITY has no tactic, so we hold.
            logger.info(f"[{symbol}] Regime {regime.name} has no associated tactic. Holding.")
            return None

        # 4. Evaluate
        decision = tactic.evaluate(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            snapshots=snapshots,
            params=tactic_params,
        )

        if decision:
            # Attach the detected regime to the decision for downstream systems (like RiskManager)
            decision.regime = regime_snapshot
            # Prepend the regime name to the reason
            decision.reason = f"[{regime.name}] {decision.reason}"

        return decision
