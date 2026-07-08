from unittest.mock import MagicMock
from decimal import Decimal
import pytest

from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.order_repository import OrderRepository
from crypto_mas.domain.repositories.trade_repository import TradeRepository
from crypto_mas.domain.repositories.trading_cycle_repository import TradingCycleRepository
from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.domain.repositories.execution_log_repository import ExecutionLogRepository
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.backfill_state_repository import BackfillStateRepository

def test_paper_account_create_if_not_exists():
    db = MagicMock()
    repo = PaperAccountRepository(db)
    
    # Exists
    repo.get_by_name = MagicMock(return_value="existing_account")
    assert repo.create_if_not_exists("test", "BINANCE", "USDT", Decimal("1000")) == "existing_account"
    
    # Does not exist
    repo.get_by_name = MagicMock(return_value=None)
    acc = repo.create_if_not_exists("test2", "BINANCE", "USDT", Decimal("1000"))
    assert acc.name == "test2"
    assert acc.initial_balance == Decimal("1000")
    db.add.assert_called_once()
    db.commit.assert_called()
    db.refresh.assert_called()

def test_order_repository_methods():
    db = MagicMock()
    repo = OrderRepository(db)
    
    order = MagicMock()
    repo.add(order)
    db.add.assert_called_with(order)
    db.flush.assert_called()
    
    db.get.return_value = order
    assert repo.get_by_id(1) == order
    
    db.scalars.return_value.all.return_value = [order]
    assert repo.list_open_orders("acc") == [order]
    
    repo.update_status(1, "FILLED")
    db.execute.assert_called()
    db.flush.assert_called()

def test_trade_repository_methods():
    db = MagicMock()
    repo = TradeRepository(db)
    
    trade = MagicMock()
    repo.add(trade)
    db.add.assert_called_with(trade)
    db.flush.assert_called()
    
    db.scalars.return_value.all.return_value = [trade]
    assert repo.list_by_account("acc") == [trade]
    assert repo.list_by_cycle(1) == [trade]

def test_trading_cycle_repository_methods():
    db = MagicMock()
    repo = TradingCycleRepository(db)
    
    cycle = MagicMock()
    repo.add(cycle)
    db.add.assert_called_with(cycle)
    db.flush.assert_called()
    
    db.get.return_value = cycle
    assert repo.get_by_id(1) == cycle
    
    db.execute.return_value = None
    repo.update_status(1, "COMPLETED")
    db.execute.assert_called()
    db.flush.assert_called()

def test_candle_repository_methods():
    db = MagicMock()
    repo = CandleRepository(db)
    
    # Test bulk_upsert empty
    assert repo.bulk_upsert([]) == 0
    
    # Test bulk_upsert
    candle_mock = MagicMock()
    candle_mock.exchange.value = "BINANCE"
    candle_mock.timeframe.value = "15m"
    repo.bulk_upsert([candle_mock])
    db.execute.assert_called()
    db.commit.assert_called()
    
    # Test list_by_symbol with limit
    db.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]
    assert len(repo.list_by_symbol("BINANCE", "BTCUSDT", "15m", limit=10, start_time="start", end_time="end")) == 2

def test_execution_log_repository_methods():
    db = MagicMock()
    repo = ExecutionLogRepository(db)
    
    log = MagicMock()
    repo.add(log)
    db.add.assert_called_with(log)
    db.flush.assert_called()
    
    db.scalars.return_value.all.return_value = [log]
    assert repo.list_by_cycle(1) == [log]
    assert repo.list_recent("acc") == [log]

def test_feature_snapshot_repository_methods():
    db = MagicMock()
    repo = FeatureSnapshotRepository(db)
    
    db.scalars.return_value.first.return_value = "snapshot"
    assert repo.get_latest("BINANCE", "BTCUSDT", "15m") == "snapshot"

def test_backfill_state_repository_methods():
    db = MagicMock()
    repo = BackfillStateRepository(db)
    
    # Exists
    state = MagicMock()
    repo.get_state = MagicMock(return_value=state)
    repo.upsert_state("BINANCE", "BTCUSDT", "15m", "time")
    assert state.last_fetched_at == "time"
    db.commit.assert_called()
    db.refresh.assert_called()
    
    # Not exists
    repo.get_state = MagicMock(return_value=None)
    repo.upsert_state("BINANCE", "ETHUSDT", "15m", "time")
    db.add.assert_called()
    db.commit.assert_called()
    db.refresh.assert_called()
