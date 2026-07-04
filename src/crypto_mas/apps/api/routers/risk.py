from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crypto_mas.engine.portfolio.portfolio import PortfolioEngine
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.engine.risk import RiskLimits
from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.services.decision_orchestrator.multi_symbol_runner import MultiSymbolDecisionRunner
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

router = APIRouter(prefix="/risk", tags=["Risk Engine"])

@router.get("/mock/assess")
def assess_mock_portfolio_risk(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    runner = MultiSymbolDecisionRunner(db)

    decision_result = runner.run(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        quote_asset="USDT",
        symbol_limit=10,
        snapshot_limit=200,
    )

    portfolio_target = PortfolioEngine(
        max_positions=3,
        max_gross_exposure=0.90,
        min_confidence=0.35,
    ).build_target_portfolio(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        decisions=decision_result.decisions,
    )

    assessment = RiskEngine(
        limits=RiskLimits(
            max_positions=3,
            max_gross_exposure=0.90,
            max_position_weight=0.35,
            min_cash_weight=0.10,
        )
    ).assess(portfolio_target)

    return assessment.model_dump(mode="json")
