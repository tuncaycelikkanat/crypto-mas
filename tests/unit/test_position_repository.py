from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from crypto_mas.domain.models.position import Position
from crypto_mas.domain.repositories.position_repository import PositionRepository


def test_update_mark_price():
    db_mock = MagicMock()
    repo = PositionRepository(db_mock)
    
    pos = Position(entry_price=Decimal("50000"), quantity=Decimal("0.1"), notional_value=Decimal("5000"))
    
    # Test positive PnL
    updated = repo.update_mark_price(pos, Decimal("60000"))
    assert updated.current_price == Decimal("60000.00000000")
    assert updated.unrealized_pnl == Decimal("1000.00000000")
    assert updated.notional_value == Decimal("6000.00000000")
    db_mock.commit.assert_called()
    db_mock.refresh.assert_called_with(pos)

def test_update_mark_price_zero_pnl():
    db_mock = MagicMock()
    repo = PositionRepository(db_mock)
    
    pos = Position(entry_price=Decimal("50000"), quantity=Decimal("0.1"), notional_value=Decimal("5000"))
    
    # Test exactly zero PnL
    updated = repo.update_mark_price(pos, Decimal("50000"))
    assert updated.current_price == Decimal("50000.00000000")
    assert updated.unrealized_pnl == Decimal("0.00000000")
    assert updated.notional_value == Decimal("5000.00000000")

def test_update_stop_loss():
    db_mock = MagicMock()
    repo = PositionRepository(db_mock)
    
    pos = Position()
    updated = repo.update_stop_loss(pos, Decimal("45000"))
    
    assert updated.stop_loss_price == Decimal("45000.00000000")
    db_mock.commit.assert_called()
    db_mock.refresh.assert_called_with(pos)

def test_close_position():
    db_mock = MagicMock()
    repo = PositionRepository(db_mock)
    
    pos = Position(entry_price=Decimal("50000"), quantity=Decimal("0.1"), notional_value=Decimal("5000"))
    dt = datetime.now(UTC)
    
    updated = repo.close_position(pos, Decimal("60000"), closed_at=dt, close_reason="TAKE_PROFIT")
    
    assert updated.status == "CLOSED"
    assert updated.closed_at == dt
    assert updated.close_reason == "TAKE_PROFIT"
    assert updated.realized_pnl == Decimal("1000.00000000")
    assert updated.unrealized_pnl == Decimal("0.00000000")
    assert updated.notional_value == Decimal("6000.00000000")
    db_mock.commit.assert_called()

def test_close_position_zero_pnl():
    db_mock = MagicMock()
    repo = PositionRepository(db_mock)
    
    pos = Position(entry_price=Decimal("50000"), quantity=Decimal("0.1"), notional_value=Decimal("5000"))
    dt = datetime.now(UTC)
    
    updated = repo.close_position(pos, Decimal("50000"), closed_at=dt)
    
    assert updated.status == "CLOSED"
    assert updated.realized_pnl == Decimal("0.00000000")
    assert updated.notional_value == Decimal("5000.00000000")

def test_zero_if_tiny():
    assert PositionRepository._zero_if_tiny(Decimal("0.000000001")) == Decimal("0.00000000")
    assert PositionRepository._zero_if_tiny(Decimal("-0.000000001")) == Decimal("0.00000000")
    assert PositionRepository._zero_if_tiny(Decimal("0.1")) == Decimal("0.10000000")
