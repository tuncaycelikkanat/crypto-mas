import pytest
from decimal import Decimal
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.services.market_data_service.schemas import Exchange
from crypto_mas.domain.models.position import Position
from crypto_mas.domain.value_objects.enums import PositionSide, PositionStatus
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider

@pytest.fixture
def repo(db_session):
    return PaperAccountRepository(db_session)

def test_multiple_accounts_creation(db_session, repo):
    # Test creation
    acc1 = repo.create_if_not_exists("bot-swing", Exchange.MOCK.value, "USDT", Decimal("10000"))
    acc2 = repo.create_if_not_exists("bot-scalping", Exchange.MOCK.value, "USDT", Decimal("10000"))
    
    assert acc1.name == "bot-swing"
    assert acc2.name == "bot-scalping"
    
    # Test get_all
    accounts = repo.get_all()
    assert len(accounts) == 2
    names = [a.name for a in accounts]
    assert "bot-swing" in names
    assert "bot-scalping" in names

def test_isolated_positions(db_session, repo):
    repo.create_if_not_exists("bot-A", Exchange.MOCK.value, "USDT", Decimal("10000"))
    repo.create_if_not_exists("bot-B", Exchange.MOCK.value, "USDT", Decimal("10000"))
    
    pos_repo = PositionRepository(db_session)
    
    # Create isolated positions
    time_provider = SystemTimeProvider()
    pos_repo.create_open_position(
        account_name="bot-A",
        exchange=Exchange.MOCK.value,
        symbol="BTCUSDT",
        quantity=Decimal("1.0"),
        entry_price=Decimal("50000.0"),
        notional_value=Decimal("50000.0"),
        opened_at=time_provider.now(),
        side=PositionSide.LONG,
    )
    
    pos_repo.create_open_position(
        account_name="bot-B",
        exchange=Exchange.MOCK.value,
        symbol="ETHUSDT",
        quantity=Decimal("10.0"),
        entry_price=Decimal("3000.0"),
        notional_value=Decimal("30000.0"),
        opened_at=time_provider.now(),
        side=PositionSide.SHORT,
    )
    
    db_session.commit()
    
    # Verify isolation
    pos_a = pos_repo.list_open_positions("bot-A")
    pos_b = pos_repo.list_open_positions("bot-B")
    
    assert len(pos_a) == 1
    assert pos_a[0].symbol == "BTCUSDT"
    
    assert len(pos_b) == 1
    assert pos_b[0].symbol == "ETHUSDT"
