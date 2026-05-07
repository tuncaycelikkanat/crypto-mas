from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider


class DomainEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    version: int = 1
    source: str
    payload: dict[str, Any]
    trace_id: str | None = None
    created_at: datetime = Field(default_factory=SystemTimeProvider().now)


def create_event(
    event_type: str,
    source: str,
    payload: dict[str, Any],
    trace_id: str | None = None,
    time_provider: TimeProvider | None = None,
) -> DomainEvent:
    provider = time_provider or SystemTimeProvider()

    return DomainEvent(
        event_type=event_type,
        source=source,
        payload=payload,
        trace_id=trace_id,
        created_at=provider.now(),
    )
