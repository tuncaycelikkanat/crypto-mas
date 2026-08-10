from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.engine.portfolio import PortfolioTarget
from crypto_mas.engine.portfolio.portfolio import PortfolioEngine
from crypto_mas.engine.risk import RiskDecisionStatus, RiskLimits
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider
from crypto_mas.apps.api.security import verify_api_key
from crypto_mas.services.decision_orchestrator.multi_symbol_runner import MultiSymbolDecisionRunner
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService

router = APIRouter(prefix="/api/v1/paper", tags=["Paper Trading"], dependencies=[Depends(verify_api_key)])

@router.post("/mock/account/init")
def initialize_mock_paper_account(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    repository = PaperAccountRepository(db)

    account = repository.create_if_not_exists(
        name="default-paper",
        exchange=Exchange.MOCK.value,
        base_currency="USDT",
        initial_balance=Decimal("10000"),
    )

    return {
        "name": account.name,
        "exchange": account.exchange,
        "base_currency": account.base_currency,
        "initial_balance": str(account.initial_balance),
        "cash_balance": str(account.cash_balance),
        "equity": str(account.equity),
    }

@router.get("/mock/account")
def get_mock_paper_account(
    db: Annotated[Session, Depends(get_db_session)],
    account_name: str | None = None,
) -> dict[str, object] | list[dict[str, object]]:
    account_repository = PaperAccountRepository(db)
    position_repository = PositionRepository(db)

    def _format_account(account):
        positions = position_repository.list_open_positions(account_name=account.name)
        return {
            "name": account.name,
            "exchange": account.exchange,
            "base_currency": account.base_currency,
            "initial_balance": str(account.initial_balance),
            "cash_balance": str(account.cash_balance),
            "equity": str(account.equity),
            "open_positions": [
                {
                    "symbol": position.symbol,
                    "exchange": position.exchange,
                    "side": position.side,
                    "status": position.status,
                    "quantity": str(position.quantity),
                    "entry_price": str(position.entry_price),
                    "current_price": str(position.current_price),
                    "notional_value": str(position.notional_value),
                    "unrealized_pnl": str(position.unrealized_pnl),
                    "realized_pnl": str(position.realized_pnl),
                    "opened_at": position.opened_at.isoformat(),
                }
                for position in positions
            ],
        }

    if account_name:
        account = account_repository.get_by_name(account_name)
        if account is None:
            raise HTTPException(status_code=404, detail="Paper account not found.")
        return _format_account(account)
    
    accounts = account_repository.get_all()
    return [_format_account(acc) for acc in accounts]

@router.post("/mock/execute-target")
def execute_mock_paper_target(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    account_repository = PaperAccountRepository(db)

    account = account_repository.create_if_not_exists(
        name="default-paper",
        exchange=Exchange.MOCK.value,
        base_currency="USDT",
        initial_balance=Decimal("10000"),
    )

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

    if assessment.status == RiskDecisionStatus.REJECTED or assessment.approved_target is None:
        return {
            "status": "REJECTED",
            "reason": assessment.reason,
            "issues": [issue.model_dump(mode="json") for issue in assessment.issues],
        }

    report = PaperBrokerService(db).execute_target_portfolio(
        account_name=account.name,
        target=assessment.approved_target,
    )

    return {
        "status": "EXECUTED",
        "risk_status": assessment.status.value,
        "execution_report": report.model_dump(mode="json"),
    }

@router.post("/mock/mark-to-market")
def mark_mock_paper_positions(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    report = PaperBrokerService(db).update_mark_prices(
        account_name="default-paper",
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS.value,
    )

    return {
        "status": "UPDATED",
        "mark_to_market_report": report.model_dump(mode="json"),
    }

@router.post("/mock/close-all")
def close_all_mock_paper_positions(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict[str, object]:
    empty_target = PortfolioTarget(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        target_positions=[],
        cash_weight=1.0,
        gross_exposure=0.0,
        reason="Manual close-all target.",
        created_at=SystemTimeProvider().now(),
    )

    report = PaperBrokerService(db).close_positions_not_in_target(
        account_name="default-paper",
        target=empty_target,
    )

    return {
        "status": "CLOSED",
        "execution_report": report.model_dump(mode="json"),
    }
