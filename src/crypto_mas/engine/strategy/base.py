from typing import Protocol

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.strategy.schemas import TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class BaseStrategy(Protocol):
    def decide(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
        risk_level: int = 50,
        htf_snapshots: list[FeatureSnapshot] | None = None,
        config: dict | None = None,
        is_open: bool = False,
    ) -> TradingDecision | None:
        """
        Calculates a trading decision given historical feature snapshots.
        Returns None if there isn't enough data or no decision can be made.
        """
        ...
