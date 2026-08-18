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
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService

router = APIRouter(prefix="/api/v1/paper", tags=["Paper Trading"])

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
        open_positions = position_repository.list_open_positions(account_name=account.name)
        closed_positions = position_repository.list_closed_positions(account_name=account.name, limit=50)

        def _format_pos(p):
            return {
                "symbol": p.symbol,
                "exchange": p.exchange,
                "side": p.side,
                "status": p.status,
                "quantity": str(p.quantity),
                "entry_price": str(p.entry_price),
                "current_price": str(p.current_price) if p.current_price else str(p.entry_price),
                "notional_value": str(p.notional_value),
                "unrealized_pnl": str(p.unrealized_pnl),
                "realized_pnl": str(p.realized_pnl),
                "opened_at": p.opened_at.isoformat(),
                "closed_at": p.closed_at.isoformat() if p.closed_at else None,
                "close_reason": p.close_reason,
            }

        return {
            "name": account.name,
            "exchange": account.exchange,
            "base_currency": account.base_currency,
            "initial_balance": str(account.initial_balance),
            "cash_balance": str(account.cash_balance),
            "equity": str(account.equity),
            "open_positions": [_format_pos(p) for p in open_positions],
            "closed_positions": [_format_pos(p) for p in closed_positions],
        }

    if account_name:
        account = account_repository.get_by_name(account_name)
        if account is None:
            # Auto-initialize the slot if queried directly and it doesn't exist
            account = account_repository.create_if_not_exists(
                name=account_name,
                exchange=Exchange.MOCK.value,
                base_currency="USDT",
                initial_balance=Decimal("10000"),
            )
        return _format_account(account)
    
    # Return exactly 4 fixed slots for the UI
    slot_names = ["main", "slot-2", "slot-3", "slot-4"]
    accounts = []
    for s_name in slot_names:
        acc = account_repository.get_by_name(s_name)
        if acc is None:
            acc = account_repository.create_if_not_exists(
                name=s_name,
                exchange=Exchange.MOCK.value,
                base_currency="USDT",
                initial_balance=Decimal("10000"),
            )
        accounts.append(acc)

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
