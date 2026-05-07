from datetime import UTC, datetime

from crypto_mas.domain.events.base import create_event
from crypto_mas.domain.events.publisher import InMemoryEventPublisher
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider


def test_create_event_uses_fixed_time_provider() -> None:
    fixed_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    event = create_event(
        event_type="signal.generated",
        source="test",
        payload={"symbol": "BTCUSDT"},
        time_provider=FixedTimeProvider(fixed_time),
    )

    assert event.event_type == "signal.generated"
    assert event.source == "test"
    assert event.payload == {"symbol": "BTCUSDT"}
    assert event.created_at == fixed_time


def test_in_memory_event_publisher_stores_events() -> None:
    publisher = InMemoryEventPublisher()

    event = create_event(
        event_type="score.computed",
        source="test",
        payload={"score": 0.5},
    )

    publisher.publish(event)

    assert len(publisher.events) == 1
    assert publisher.events[0].event_type == "score.computed"
