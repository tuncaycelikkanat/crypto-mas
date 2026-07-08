from enum import StrEnum

from pydantic import BaseModel, Field

from crypto_mas.engine.portfolio import PortfolioTarget


class RiskDecisionStatus(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REDUCED = "REDUCED"


class RiskCheckIssue(BaseModel):
    code: str
    message: str
    severity: str = "ERROR"


class RiskLimits(BaseModel):
    max_positions: int = Field(default=10, ge=1)
    max_gross_exposure: float = Field(default=0.50, ge=0.0, le=1.0)
    max_position_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    min_cash_weight: float = Field(default=0.50, ge=0.0, le=1.0)


class RiskAssessment(BaseModel):
    status: RiskDecisionStatus
    approved_target: PortfolioTarget | None
    original_target: PortfolioTarget
    issues: list[RiskCheckIssue]
    reason: str
