from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import crypto_mas.domain.models  # noqa: F401
from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
from crypto_mas.services.paper_trading.schemas import PaperExecutionStatus


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _create_account(db: Session) -> None:
    PaperAccountRepository(db).create_if_not_exists(
        name="default-paper",
        exchange=Exchange.MOCK.value,
        base_currency="USDT",
        initial_balance=__import__("decimal").Decimal("10000"),
    )


def _add_feature_snapshot(
    db: Session,
    symbol: str,
    close: float = 100.0,
) -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    snapshot = FeatureSnapshot(
        exchange=Exchange.MOCK.value,
        symbol=symbol,
        timeframe=Timeframe.FOUR_HOURS.value,
        timestamp=timestamp,
        available_at=timestamp,
        features_json={
            "close": close,
            "ema_20": close,
            "ema_50": close,
            "rsi_14": 60.0,
            "atr_14": 1.0,
            "roc_14": 2.0,
        },
    )

    db.add(snapshot)
    db.commit()


def _make_target() -> PortfolioTarget:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)

    return PortfolioTarget(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        target_positions=[
            TargetPosition(
                symbol="BTCUSDT",
                target_weight=0.30,
                confidence=0.50,
                final_score=0.50,
                reason="test",
            ),
            TargetPosition(
                symbol="ETHUSDT",
                target_weight=0.20,
                confidence=0.45,
                final_score=0.45,
                reason="test",
            ),
        ],
        cash_weight=0.50,
        gross_exposure=0.50,
        reason="test target",
        created_at=created_at,
    )


def test_paper_broker_executes_target_portfolio(db_session: Session) -> None:
    fixed_time = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    _create_account(db_session)
    _add_feature_snapshot(db_session, "BTCUSDT", close=100.0)
    _add_feature_snapshot(db_session, "ETHUSDT", close=100.0)

    report = PaperBrokerService(
        db=db_session,
        time_provider=FixedTimeProvider(fixed_time),
    ).execute_target_portfolio(
        account_name="default-paper",
        target=_make_target(),
    )

    assert report.account_name == "default-paper"
    assert report.starting_cash == 10000.0
    assert report.ending_cash == 5000.0
    assert report.starting_equity == 10000.0
    assert report.ending_equity == 10000.0
    assert len(report.executed) == 2
    assert report.skipped == []

    assert {item.symbol for item in report.executed} == {"BTCUSDT", "ETHUSDT"}
    assert all(item.status == PaperExecutionStatus.EXECUTED for item in report.executed)

    positions = PositionRepository(db_session).list_open_positions("default-paper")

    assert len(positions) == 2
    assert {position.symbol for position in positions} == {"BTCUSDT", "ETHUSDT"}

    account = PaperAccountRepository(db_session).get_by_name("default-paper")

    assert account is not None
    assert str(account.cash_balance) == "5000.00000000"
    assert str(account.equity) == "10000.00000000"


def test_paper_broker_skips_existing_open_positions(db_session: Session) -> None:
    fixed_time = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    _create_account(db_session)
    _add_feature_snapshot(db_session, "BTCUSDT", close=100.0)
    _add_feature_snapshot(db_session, "ETHUSDT", close=100.0)

    broker = PaperBrokerService(
        db=db_session,
        time_provider=FixedTimeProvider(fixed_time),
    )

    first_report = broker.execute_target_portfolio(
        account_name="default-paper",
        target=_make_target(),
    )

    second_report = broker.execute_target_portfolio(
        account_name="default-paper",
        target=_make_target(),
    )

    assert len(first_report.executed) == 2
    assert second_report.executed == []
    assert len(second_report.skipped) == 2
    assert all(item.status == PaperExecutionStatus.SKIPPED for item in second_report.skipped)

    positions = PositionRepository(db_session).list_open_positions("default-paper")

    assert len(positions) == 2
