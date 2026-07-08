from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.engine.regime.regime import RegimeEngine
from crypto_mas.engine.scoring.scoring import ScoringEngine
from crypto_mas.engine.signal.trend import TrendSignalEngine
from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.services.decision_orchestrator.multi_symbol_runner import MultiSymbolDecisionRunner
from crypto_mas.engine.strategy.factory import StrategyFactory
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

router = APIRouter(tags=["Decision Engine"])

@router.get("/scores/mock/trend")
def generate_mock_trend_score(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object] | None:
    repository = FeatureSnapshotRepository(db)

    snapshots = repository.list_by_symbol(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS.value,
        limit=200,
    )

    signal = TrendSignalEngine().generate(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=snapshots,
    )

    if signal is None:
        return None

    score = ScoringEngine().score(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        signal=signal,
        snapshots=snapshots,
    )

    if score is None:
        return None

    return score.model_dump(mode="json")


@router.get("/regime/mock")
def detect_mock_regime(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object] | None:
    repository = FeatureSnapshotRepository(db)

    snapshots = repository.list_by_symbol(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS.value,
        limit=200,
    )

    regime = RegimeEngine().detect(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=snapshots,
    )

    if regime is None:
        return None

    return regime.model_dump(mode="json")


@router.get("/decision/mock/run")
def run_mock_decision(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object] | None:
    repository = FeatureSnapshotRepository(db)

    snapshots = repository.list_by_symbol(
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS.value,
        limit=200,
    )

    strategy = StrategyFactory.create("multi_agent")
    decision = strategy.decide(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        snapshots=snapshots,
    )

    if decision is None:
        return None

    return decision.model_dump(mode="json")


@router.get("/decision/mock/run-all")
def run_all_mock_decisions(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    runner = MultiSymbolDecisionRunner(db)

    result = runner.run(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        quote_asset="USDT",
        symbol_limit=10,
        snapshot_limit=200,
    )

    return result.model_dump(mode="json")
