import abc
from typing import Any
from crypto_mas.engine.strategy.schemas import TradingDecision


class BaseRiskModel(abc.ABC):
    """
    Abstract Base Class for all Risk and Shield models.
    Like QuantConnect's RiskManagementModel, this inspects generated trading decisions
    and can override them to HOLD or AVOID if market conditions are too risky.
    """

    @abc.abstractmethod
    def evaluate(
        self,
        decision: TradingDecision,
        context: dict[str, Any]
    ) -> TradingDecision:
        """
        Evaluate a trading decision and potentially override it.
        context: Contains cycle-level data like 'btc_is_crashing', 'htf_trend', etc.
        """
        pass
