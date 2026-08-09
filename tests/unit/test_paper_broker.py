from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.infrastructure.time.time_provider import TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
from crypto_mas.services.paper_trading.schemas import PaperExecutionStatus


def get_mocked_broker():
    db_mock = MagicMock()
    time_provider_mock = MagicMock(spec=TimeProvider)
    time_provider_mock.now.return_value = datetime.now(UTC)
    
    broker = PaperBrokerService(db=db_mock, time_provider=time_provider_mock)
    
    # Mock repositories
    account_repo_mock = MagicMock()
    position_repo_mock = MagicMock()
    feature_snapshot_repo_mock = MagicMock()
    trade_repo_mock = MagicMock()
    order_repo_mock = MagicMock()
    log_repo_mock = MagicMock()
    
    # Assign them directly to broker for easy access in tests
    broker.account_repository = account_repo_mock
    broker.position_repository = position_repo_mock
    broker.feature_snapshot_repository = feature_snapshot_repo_mock
    broker.trade_repository = trade_repo_mock
    broker.order_repository = order_repo_mock
    broker.log_repository = log_repo_mock
    
    # Override in sub-components
    broker.position_manager.account_repository = account_repo_mock
    broker.position_manager.position_repository = position_repo_mock
    broker.position_manager.feature_snapshot_repository = feature_snapshot_repo_mock
    
    broker.mark_to_market.account_repository = account_repo_mock
    broker.mark_to_market.position_repository = position_repo_mock
    broker.mark_to_market.feature_snapshot_repository = feature_snapshot_repo_mock
    
    broker.reporter.trade_repository = trade_repo_mock
    broker.reporter.order_repository = order_repo_mock
    broker.reporter.log_repository = log_repo_mock
    
    return broker

def _mock_account(cash=10000.0):
    m = MagicMock()
    m.name = "test_acc"
    m.cash_balance = Decimal(str(cash))
    m.equity = Decimal("10000.0")
    m.base_currency = "USDT"
    m.initial_balance = Decimal("10000.0")
    return m

def _mock_position(sym="BTCUSDT", qty=0.1, price=50000.0, tp=None, sl=None):
    m = MagicMock()
    m.id = 1
    m.account_name = "test_acc"
    m.exchange = "BINANCE"
    m.symbol = sym
    m.side = "LONG"
    m.quantity = Decimal(str(qty))
    m.entry_price = Decimal(str(price))
    m.notional_value = Decimal(str(qty * price))
    m.current_price = Decimal(str(price))
    m.unrealized_pnl = Decimal("0.0")
    m.realized_pnl = Decimal("0.0")
    m.take_profit_price = Decimal(str(tp)) if tp else None
    m.stop_loss_price = Decimal(str(sl)) if sl else None
    return m

def test_execute_target_portfolio_success():
    broker = get_mocked_broker()
    account_mock = _mock_account(10000.0)
    broker.account_repository.get_by_name.return_value = account_mock
    broker.account_repository.update_balances.return_value = account_mock
    
    broker.position_repository.get_open_position.return_value = None
    
    snapshot_mock = FeatureSnapshot(
        exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe=Timeframe.FOUR_HOURS.value,
        timestamp=datetime.now(UTC), features_json={"close": 50000.0}
    )
    broker.feature_snapshot_repository.get_latest.return_value = snapshot_mock
    
    position_mock = _mock_position("BTCUSDT", 0.1, 50000.0)
    broker.position_repository.create_open_position.return_value = position_mock
    broker.position_repository.list_open_positions.return_value = [position_mock]
    
    target = PortfolioTarget(
        exchange=Exchange.BINANCE, timeframe=Timeframe.FOUR_HOURS,
        target_positions=[TargetPosition(symbol="BTCUSDT", target_weight=0.5, confidence=0.8, final_score=0.8, reason="test")],
        cash_weight=0.5, gross_exposure=0.5, reason="test", created_at=datetime.now(UTC)
    )
    
    report = broker.execute_target_portfolio("test_acc", target)
    
    assert report.account_name == "test_acc"
    assert len(report.executed) == 1
    assert report.executed[0].symbol == "BTCUSDT"
    assert report.executed[0].status == PaperExecutionStatus.EXECUTED
    assert len(report.skipped) == 0

def test_execute_target_portfolio_insufficient_cash():
    broker = get_mocked_broker()
    account_mock = _mock_account(100.0)
    broker.account_repository.get_by_name.return_value = account_mock
    broker.account_repository.update_balances.return_value = account_mock
    
    broker.position_repository.get_open_position.return_value = None
    
    snapshot_mock = FeatureSnapshot(
        exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe=Timeframe.FOUR_HOURS.value,
        timestamp=datetime.now(UTC), features_json={"close": 50000.0}
    )
    broker.feature_snapshot_repository.get_latest.return_value = snapshot_mock
    
    target = PortfolioTarget(
        exchange=Exchange.BINANCE, timeframe=Timeframe.FOUR_HOURS,
        target_positions=[TargetPosition(symbol="BTCUSDT", target_weight=0.5, confidence=0.8, final_score=0.8, reason="test")],
        cash_weight=0.5, gross_exposure=0.5, reason="test", created_at=datetime.now(UTC)
    )
    
    report = broker.execute_target_portfolio("test_acc", target)
    
    assert len(report.executed) == 0
    assert len(report.skipped) == 1
    assert report.skipped[0].status == PaperExecutionStatus.REJECTED

def test_close_positions_not_in_target():
    broker = get_mocked_broker()
    account_mock = _mock_account(5000.0)
    broker.account_repository.get_by_name.return_value = account_mock
    broker.account_repository.update_balances.return_value = account_mock
    
    pos_btc = _mock_position("BTCUSDT", 0.1, 50000.0)
    pos_eth = _mock_position("ETHUSDT", 1.0, 2000.0)
    broker.position_repository.list_open_positions.side_effect = [[pos_btc, pos_eth], [pos_eth]]
    
    snapshot_mock = FeatureSnapshot(
        exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe=Timeframe.FOUR_HOURS.value,
        timestamp=datetime.now(UTC), features_json={"close": 55000.0}
    )
    broker.feature_snapshot_repository.get_latest.return_value = snapshot_mock
    
    closed_pos = _mock_position("BTCUSDT", 0.1, 50000.0)
    closed_pos.realized_pnl = Decimal("500.0")
    broker.position_repository.close_position.return_value = closed_pos
    
    target = PortfolioTarget(
        exchange=Exchange.BINANCE, timeframe=Timeframe.FOUR_HOURS,
        target_positions=[TargetPosition(symbol="ETHUSDT", target_weight=0.5, confidence=0.8, final_score=0.8, reason="test")],
        cash_weight=0.5, gross_exposure=0.5, reason="test", created_at=datetime.now(UTC)
    )
    
    report = broker.close_positions_not_in_target("test_acc", target)
    
    assert len(report.executed) == 1
    assert report.executed[0].symbol == "BTCUSDT"
    assert len(report.skipped) == 1
    assert report.skipped[0].symbol == "ETHUSDT"

def test_update_mark_prices_and_hit_tp():
    broker = get_mocked_broker()
    account_mock = _mock_account(5000.0)
    broker.account_repository.get_by_name.return_value = account_mock
    broker.account_repository.update_balances.return_value = account_mock
    
    pos_btc = _mock_position("BTCUSDT", 0.1, 50000.0, tp=55000.0, sl=45000.0)
    broker.position_repository.list_open_positions.return_value = [pos_btc]
    broker.position_repository.update_mark_price.return_value = pos_btc
    
    updated_sl_pos = _mock_position("BTCUSDT", 0.1, 50000.0, tp=55000.0, sl=58200.0)
    broker.position_repository.update_stop_loss.return_value = updated_sl_pos
    
    snapshot_mock = FeatureSnapshot(
        exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe=Timeframe.FOUR_HOURS.value,
        timestamp=datetime.now(UTC), features_json={"close": 60000.0}
    )
    broker.feature_snapshot_repository.get_latest.return_value = snapshot_mock
    
    closed_pos = _mock_position("BTCUSDT", 0.1, 50000.0)
    closed_pos.realized_pnl = Decimal("1000.0")
    broker.position_repository.close_position.return_value = closed_pos
    
    report = broker.update_mark_prices("test_acc", Exchange.BINANCE, Timeframe.FOUR_HOURS.value)
    
    assert len(report.executed) == 1
    assert report.executed[0].reason == "TAKE_PROFIT"

def test_update_mark_prices_trailing_sl():
    broker = get_mocked_broker()
    account_mock = _mock_account(5000.0)
    broker.account_repository.get_by_name.return_value = account_mock
    broker.account_repository.update_balances.return_value = account_mock
    
    pos_btc = _mock_position("BTCUSDT", 0.1, 50000.0, tp=60000.0, sl=45000.0)
    broker.position_repository.list_open_positions.return_value = [pos_btc]
    broker.position_repository.update_mark_price.return_value = pos_btc
    
    snapshot_mock = FeatureSnapshot(
        exchange=Exchange.BINANCE.value, symbol="BTCUSDT", timeframe=Timeframe.FOUR_HOURS.value,
        timestamp=datetime.now(UTC), features_json={"close": 55000.0}
    )
    broker.feature_snapshot_repository.get_latest.return_value = snapshot_mock
    
    updated_sl_pos = _mock_position("BTCUSDT", 0.1, 50000.0, tp=60000.0, sl=53350.0)
    broker.position_repository.update_stop_loss.return_value = updated_sl_pos
    
    report = broker.update_mark_prices("test_acc", Exchange.BINANCE, Timeframe.FOUR_HOURS.value)
    
    assert broker.position_repository.update_stop_loss.called
    assert len(report.executed) == 1
    assert "marked to latest close price" in report.executed[0].reason
