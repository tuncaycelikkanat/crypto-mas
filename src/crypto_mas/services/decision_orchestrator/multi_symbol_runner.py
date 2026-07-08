from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.symbol_repository import SymbolRepository
from crypto_mas.services.decision_orchestrator.multi_symbol import MultiSymbolDecisionResult
from crypto_mas.engine.strategy.factory import StrategyFactory
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class MultiSymbolDecisionRunner:
    def __init__(self, db: Session, strategy_name: str = "multi_agent") -> None:
        self.symbol_repository = SymbolRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)
        self.strategy = StrategyFactory.create(strategy_name)

    def run(
        self,
        exchange: Exchange,
        timeframe: Timeframe,
        quote_asset: str = "USDT",
        symbol_limit: int | None = None,
        snapshot_limit: int = 200,
    ) -> MultiSymbolDecisionResult:
        symbols = self.symbol_repository.list_active_symbols(
            exchange=exchange.value,
            quote_asset=quote_asset,
            limit=symbol_limit,
        )

        decisions: list[TradingDecision] = []

        for symbol in symbols:
            snapshots = self.feature_snapshot_repository.list_by_symbol(
                exchange=exchange.value,
                symbol=symbol.symbol,
                timeframe=timeframe.value,
                limit=snapshot_limit,
            )

            decision = self.strategy.decide(
                exchange=exchange,
                symbol=symbol.symbol,
                timeframe=timeframe,
                snapshots=snapshots,
            )

            if decision is not None:
                decisions.append(decision)

        sorted_decisions = sorted(
            decisions,
            key=self._decision_sort_key,
            reverse=True,
        )

        return MultiSymbolDecisionResult(
            exchange=exchange,
            timeframe=timeframe,
            requested_symbols=len(symbols),
            processed_symbols=len(sorted_decisions),
            decisions=sorted_decisions,
        )

    @staticmethod
    def _decision_sort_key(decision: TradingDecision) -> tuple[int, float]:
        action_priority = {
            DecisionAction.CONSIDER_LONG: 4,
            DecisionAction.CONSIDER_SHORT: 3,
            DecisionAction.HOLD: 2,
            DecisionAction.AVOID: 1,
        }

        return (
            action_priority.get(decision.action, 0),
            decision.confidence,
        )
