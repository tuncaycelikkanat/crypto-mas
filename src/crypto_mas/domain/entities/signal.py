from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


@dataclass(frozen=True)
class SignalCandidate:
    """
    Pure domain representation of an actionable signal candidate.
    """
    symbol: str
    action: Literal["CONSIDER_LONG", "CONSIDER_SHORT", "HOLD", "AVOID"]
    confidence_score: float
    market_regime: str
    reason: str
    suggested_weight: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_actionable(self) -> bool:
        return self.action in ("CONSIDER_LONG", "CONSIDER_SHORT") and self.confidence_score > 0.0


@dataclass(frozen=True)
class RankedCandidate:
    """
    Candidate decorated with relative ranking across the asset universe.
    """
    candidate: SignalCandidate
    rank: int
    group_category: str | None = None
