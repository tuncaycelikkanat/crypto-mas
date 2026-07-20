from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import crypto_mas.domain.models  # noqa: F401
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
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
        initial_balance=Decimal("10000"),
    )


def _add_feature_snapshot(
    db: Session,
    symbol: str,
    close: float,
    timestamp: datetime,
) -> None:
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


def _make_entry_target() -> PortfolioTarget:
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
            )
        ],
        cash_weight=0.70,
        gross_exposure=0.30,
        reason="entry target",
        created_at=created_at,
    )


def _make_empty_target() -> PortfolioTarget:
    created_at = datetime(2026, 1, 1, tzinfo=UTC)

    return PortfolioTarget(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        target_positions=[],
        cash_weight=1.0,
        gross_exposure=0.0,
        reason="exit target",
        created_at=created_at,
    )


def test_paper_broker_closes_positions_not_in_target(db_session: Session) -> None:
    fixed_time = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    _create_account(db_session)

    _add_feature_snapshot(
        db=db_session,
        symbol="BTCUSDT",
        close=100.0,
        timestamp=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
    )

    broker = PaperBrokerService(
        db=db_session,
        time_provider=FixedTimeProvider(fixed_time),
    )

    broker.execute_target_portfolio(
        account_name="default-paper",
        target=_make_entry_target(),
    )

    _add_feature_snapshot(
        db=db_session,
        symbol="BTCUSDT",
        close=110.0,
        timestamp=datetime(2026, 1, 1, 4, 0, tzinfo=UTC),
    )

    report = broker.close_positions_not_in_target(
        account_name="default-paper",
        target=_make_empty_target(),
    )

    assert len(report.executed) == 1
    assert report.executed[0].symbol == "BTCUSDT"
    assert report.executed[0].status == PaperExecutionStatus.EXECUTED
    assert report.ending_cash == pytest.approx(10019.8, abs=0.1)
    assert report.ending_equity == pytest.approx(10019.8, abs=0.1)

    positions = PositionRepository(db_session).list_open_positions("default-paper")

    assert positions == []

    account = PaperAccountRepository(db_session).get_by_name("default-paper")

    assert account is not None
    assert float(account.cash_balance) == pytest.approx(10019.8, abs=0.1)
    assert float(account.equity) == pytest.approx(10019.8, abs=0.1)
