from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class RiskShieldStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class RiskShieldEvaluation:
    """
    Pure domain representation of multi-layered risk shield evaluation.
    """
    symbol: str
    status: RiskShieldStatus
    btc_crash_shield_triggered: bool = False
    regime_shield_triggered: bool = False
    htf_shield_triggered: bool = False
    reason: str = "Passed all risk shields."
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_safe_to_execute(self) -> bool:
        return self.status != RiskShieldStatus.BLOCKED


@dataclass(frozen=True)
class DrawdownLimitState:
    """
    Domain entity tracking portfolio peak and max drawdown threshold breaches.
    """
    peak_equity: float
    current_equity: float
    max_drawdown_limit_pct: float

    @property
    def current_drawdown_pct(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return float((self.peak_equity - self.current_equity) / self.peak_equity) * 100.0

    @property
    def is_breached(self) -> bool:
        return self.current_drawdown_pct >= self.max_drawdown_limit_pct
