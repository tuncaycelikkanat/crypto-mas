from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crypto_mas.domain.events import InMemoryEventPublisher, create_event
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.engine.signal.trend import TrendSignalEngine
from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

router = APIRouter(prefix="/signals", tags=["Signals"])

@router.get("/mock/trend")
def generate_mock_trend_signal(
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

    publisher = InMemoryEventPublisher()

    event = create_event(
        event_type="signal.generated",
        source="trend_signal_agent",
        payload=signal.model_dump(mode="json"),
    )

    publisher.publish(event)

    return {
        "signal": signal.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in publisher.events],
    }
