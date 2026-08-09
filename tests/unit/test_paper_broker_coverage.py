from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService


def _setup_mock_broker():
    db_mock = MagicMock()
    broker = PaperBrokerService(db=db_mock)
    
    account_repo_mock = MagicMock()
    position_repo_mock = MagicMock()
    feature_snapshot_repo_mock = MagicMock()
    trade_repo_mock = MagicMock()
    order_repo_mock = MagicMock()
    log_repo_mock = MagicMock()
    
    broker.account_repository = account_repo_mock
    broker.position_repository = position_repo_mock
    broker.feature_snapshot_repository = feature_snapshot_repo_mock
    broker.trade_repository = trade_repo_mock
    broker.order_repository = order_repo_mock
    broker.log_repository = log_repo_mock
    
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

def test_execute_target_portfolio_account_not_found():
    broker = _setup_mock_broker()
    broker.account_repository.get_by_name.return_value = None
    
    target = MagicMock(spec=PortfolioTarget)
    
    with pytest.raises(ValueError):
        broker.execute_target_portfolio("missing_acc", target)

def test_execute_target_portfolio_existing_position():
    broker = _setup_mock_broker()
    
    account_mock = MagicMock()
    account_mock.name = "test_acc"
    broker.account_repository.get_by_name.return_value = account_mock
    
    existing_pos_mock = MagicMock()
    existing_pos_mock.current_price = Decimal("100")
    existing_pos_mock.quantity = Decimal("1")
    broker.position_repository.get_open_position.return_value = existing_pos_mock
    
    target = MagicMock(spec=PortfolioTarget)
    target.exchange = Exchange.BINANCE
    target.timeframe = Timeframe.FIFTEEN_MINUTES
    tp = TargetPosition(symbol="BTCUSDT", target_weight=0.5, confidence=0.8, final_score=0.8, reason="test")
    target.target_positions = [tp]
    
    report = broker.execute_target_portfolio("test_acc", target)
    assert len(report.skipped) == 1
    assert report.skipped[0].reason == "Open position already exists."

def test_execute_target_portfolio_missing_price():
    broker = _setup_mock_broker()
    
    account_mock = MagicMock()
    account_mock.name = "test_acc"
    broker.account_repository.get_by_name.return_value = account_mock
    
    broker.position_repository.get_open_position.return_value = None
    broker.feature_snapshot_repository.get_latest.return_value = None # No snapshot -> No price
    
    target = MagicMock(spec=PortfolioTarget)
    target.exchange = Exchange.BINANCE
    target.timeframe = Timeframe.FIFTEEN_MINUTES
    tp = TargetPosition(symbol="BTCUSDT", target_weight=0.5, confidence=0.8, final_score=0.8, reason="test")
    target.target_positions = [tp]
    
    report = broker.execute_target_portfolio("test_acc", target)
    assert len(report.skipped) == 1
    assert report.skipped[0].reason == "Latest close price not available."

def test_execute_target_portfolio_zero_notional():
    broker = _setup_mock_broker()
    
    account_mock = MagicMock()
    account_mock.name = "test_acc"
    account_mock.equity = Decimal("0") # Equity is 0 -> target notional is 0
    account_mock.cash_balance = Decimal("0")
    broker.account_repository.get_by_name.return_value = account_mock
    
    broker.position_repository.get_open_position.return_value = None
    
    snapshot_mock = MagicMock(spec=FeatureSnapshot)
    snapshot_mock.features_json = {"close": "100"}
    broker.feature_snapshot_repository.get_latest.return_value = snapshot_mock
    
    target = MagicMock(spec=PortfolioTarget)
    target.exchange = Exchange.BINANCE
    target.timeframe = Timeframe.FIFTEEN_MINUTES
    tp = TargetPosition(symbol="BTCUSDT", target_weight=0.5, confidence=0.8, final_score=0.8, reason="test")
    target.target_positions = [tp]
    
    report = broker.execute_target_portfolio("test_acc", target)
    assert len(report.skipped) == 1
    assert report.skipped[0].reason == "Target notional is zero."

def test_close_positions_not_in_target_account_not_found():
    broker = _setup_mock_broker()
    broker.account_repository.get_by_name.return_value = None
    
    target = MagicMock(spec=PortfolioTarget)
    target.target_positions = []
    
    with pytest.raises(ValueError):
        broker.close_positions_not_in_target("missing_acc", target)

def test_close_positions_not_in_target_missing_price():
    broker = _setup_mock_broker()
    
    account_mock = MagicMock()
    account_mock.name = "test_acc"
    account_mock.cash_balance = Decimal("0")
    account_mock.equity = Decimal("0")
    broker.account_repository.get_by_name.return_value = account_mock
    
    pos_mock = MagicMock()
    pos_mock.symbol = "ETHUSDT"
    pos_mock.notional_value = Decimal("100")
    pos_mock.quantity = Decimal("1")
    pos_mock.side = "LONG"
    pos_mock.current_price = Decimal("100")
    broker.position_repository.list_open_positions.return_value = [pos_mock]
    
    broker.feature_snapshot_repository.get_latest.return_value = None # Missing price
    
    target = MagicMock(spec=PortfolioTarget)
    target.exchange = Exchange.BINANCE
    target.timeframe = Timeframe.FIFTEEN_MINUTES
    target.target_positions = []
    
    report = broker.close_positions_not_in_target("test_acc", target)
    assert len(report.skipped) == 1
    assert report.skipped[0].reason == "Latest close price not available for paper SELL."

def test_extract_close_price_edge_cases():
    from crypto_mas.services.paper_trading.risk_calculator import RiskCalculator
    assert RiskCalculator.extract_close_price(None) is None
    
    s1 = MagicMock(spec=FeatureSnapshot)
    s1.features_json = {}
    assert RiskCalculator.extract_close_price(s1) is None
    
    s2 = MagicMock(spec=FeatureSnapshot)
    s2.features_json = {"close": "invalid"}
    assert RiskCalculator.extract_close_price(s2) is None

def test_update_mark_prices_missing_price():
    broker = _setup_mock_broker()
    
    account_mock = MagicMock()
    account_mock.name = "test_acc"
    account_mock.cash_balance = Decimal("0")
    account_mock.equity = Decimal("0")
    broker.account_repository.get_by_name.return_value = account_mock
    
    pos_mock = MagicMock()
    pos_mock.symbol = "ETHUSDT"
    pos_mock.notional_value = Decimal("100")
    pos_mock.quantity = Decimal("1")
    pos_mock.side = "LONG"
    pos_mock.current_price = Decimal("100")
    broker.position_repository.list_open_positions.return_value = [pos_mock]
    
    broker.feature_snapshot_repository.get_latest.return_value = None # Missing price
    
    report = broker.update_mark_prices("test_acc", Exchange.BINANCE, "15m")
    assert len(report.skipped) == 1
    assert report.skipped[0].reason == "Latest close price not available for mark-to-market."

def test_zero_if_tiny():
    from crypto_mas.services.paper_trading.risk_calculator import RiskCalculator
    assert RiskCalculator._money(Decimal("0.000000001")) == Decimal("0.00000000")
    assert RiskCalculator._money(Decimal("0.1")) == Decimal("0.10000000")
