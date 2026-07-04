from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.macd_cross import MACDStrategy
from crypto_mas.engine.strategy.multi_agent import MultiAgentStrategy
from crypto_mas.infrastructure.time.time_provider import TimeProvider

class StrategyFactory:
    @staticmethod
    def create(strategy_name: str, time_provider: TimeProvider | None = None) -> BaseStrategy:
        if strategy_name == "macd_cross":
            return MACDStrategy()
        elif strategy_name == "multi_agent":
            return MultiAgentStrategy(time_provider=time_provider)
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
