from typing import Protocol

from crypto_mas.domain.events.base import DomainEvent


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None:
        """Publish a domain event."""
        ...


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.events.append(event)

    def clear(self) -> None:
        self.events.clear()
