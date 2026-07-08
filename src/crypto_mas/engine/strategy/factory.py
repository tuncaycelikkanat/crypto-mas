from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.macd_cross import MACDStrategy
from crypto_mas.engine.strategy.multi_agent import MultiAgentStrategy
from crypto_mas.engine.strategy.rsi_oversold import RSIOversoldStrategy
from crypto_mas.engine.strategy.ema_golden_cross import EMAGoldenCrossStrategy
from crypto_mas.infrastructure.time.time_provider import TimeProvider


class StrategyFactory:
    @staticmethod
    def create(strategy_name: str, time_provider: TimeProvider | None = None) -> BaseStrategy:
        strategies = {
            "macd_cross":       MACDStrategy,
            "rsi_oversold":     RSIOversoldStrategy,
            "ema_golden_cross": EMAGoldenCrossStrategy,
            "multi_agent":      lambda: MultiAgentStrategy(time_provider=time_provider),
        }

        if strategy_name in strategies:
            factory = strategies[strategy_name]
            if callable(factory) and strategy_name == "multi_agent":
                return factory()
            return factory()

        raise ValueError(f"Unknown strategy: '{strategy_name}'. Available: {list(strategies.keys())}")
