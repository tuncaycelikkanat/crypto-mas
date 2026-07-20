from abc import ABC, abstractmethod
from typing import Any

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.strategy.schemas import TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class BaseTactic(ABC):
    """
    A Tactic is a specialized execution logic for a specific market regime.
    """

    @abstractmethod
    def evaluate(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
        params: dict[str, Any],
        is_open: bool = False,
    ) -> TradingDecision | None:
        """
        Evaluate the market conditions and return a TradingDecision if a setup is found.
        If no setup is found, return None.

        Args:
            exchange: The exchange (e.g., Exchange.BINANCE)
            symbol: The trading pair (e.g., 'BTCUSDT')
            timeframe: The timeframe (e.g., Timeframe.M15)
            snapshots: A list of feature snapshots for the symbol
            params: Tactic-specific configuration parameters
        """
        pass
