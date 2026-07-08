from unittest.mock import MagicMock, patch, AsyncMock
from datetime import timedelta
import pytest

from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService
from crypto_mas.services.market_data_service.schemas import Timeframe, Exchange
from crypto_mas.engine.strategy.schemas import DecisionAction

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_provider():
    p = MagicMock()
    p.exchange.value = "BINANCE"
    return p

def test_get_timedelta():
    assert TradingCycleService._get_timedelta(Timeframe.ONE_MINUTE) == timedelta(minutes=1)
    assert TradingCycleService._get_timedelta(Timeframe.FIFTEEN_MINUTES) == timedelta(minutes=15)
    assert TradingCycleService._get_timedelta(Timeframe.ONE_HOUR) == timedelta(hours=1)
    assert TradingCycleService._get_timedelta(Timeframe.FOUR_HOURS) == timedelta(hours=4)
    assert TradingCycleService._get_timedelta(Timeframe.ONE_DAY) == timedelta(days=1)
    
    # Test fallback
    assert TradingCycleService._get_timedelta("invalid") == timedelta(hours=1)

@pytest.mark.asyncio
async def test_run_cycle_btc_crash_and_htf_overrides(mock_db, mock_provider):
    service = TradingCycleService(db=mock_db, market_provider=mock_provider)
    
    service.fetcher_service = AsyncMock()
    service.feature_service = MagicMock()
    
    # Force BTC crash
    btc_snapshot_mock = MagicMock()
    btc_snapshot_mock.features_json = {"roc_14": -3.0}
    
    # Simulate htf_long_allowed=False, htf_short_allowed=False
    service.htf_manager = MagicMock()
    service.htf_manager.is_long_allowed.return_value = False
    service.htf_manager.is_short_allowed.return_value = False
    
    service.feature_snapshot_repository = MagicMock()
    # List by symbol side effect to return btc crash, then ETH snapshots
    def list_by_symbol_mock(exchange, symbol, timeframe, limit):
        if symbol == "BTCUSDT" and timeframe == "15m":
            return [btc_snapshot_mock]
        if symbol == "ETHUSDT" and timeframe == "15m":
            s = MagicMock()
            s.features_json = {}
            return [s]
        if symbol == "ETHUSDT" and timeframe == "4h":
            s = MagicMock()
            s.features_json = {}
            return [s]
        return []
        
    service.feature_snapshot_repository.list_by_symbol.side_effect = list_by_symbol_mock
    
    # Mock strategy
    mock_strategy = MagicMock()
    decision_mock = MagicMock()
    decision_mock.action = DecisionAction.CONSIDER_LONG
    decision_mock.reason = "Test"
    mock_strategy.decide.return_value = decision_mock
    
    with patch("crypto_mas.services.trading_cycle_service.cycle_orchestrator.StrategyFactory.create", return_value=mock_strategy):
        # We need to mock Risk and Portfolio
        service.portfolio_engine = MagicMock()
        target_portfolio_mock = MagicMock()
        target_portfolio_mock.exchange = Exchange.BINANCE
        target_portfolio_mock.timeframe = Timeframe.FIFTEEN_MINUTES
        service.portfolio_engine.build_target_portfolio.return_value = target_portfolio_mock
        
        service.risk_engine = MagicMock()
        assessment_mock = MagicMock()
        assessment_mock.approved_target = None # Force line 237-240
        assessment_mock.reason = "Too risky"
        service.risk_engine.assess.return_value = assessment_mock
        
        close_report_mock = MagicMock()
        close_report_mock.executed = []
        close_report_mock.starting_equity = 1000.0
        
        execute_report_mock = MagicMock()
        execute_report_mock.executed = []
        execute_report_mock.ending_equity = 1010.0
        
        service.paper_broker = MagicMock()
        service.paper_broker.close_positions_not_in_target.return_value = close_report_mock
        service.paper_broker.execute_target_portfolio.return_value = execute_report_mock
        
        cycle = await service.run_cycle(
            account_name="test_acc",
            symbols=["ETHUSDT"],
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )
        
        # ETHUSDT CONSIDER_LONG was rejected by BTC Crash
        assert decision_mock.action == DecisionAction.HOLD
        assert "REJECTED by BTC Crash Filter" in decision_mock.reason
        
        # Next let's test htf_long_allowed = False without BTC crash
        btc_snapshot_mock.features_json = {"roc_14": 1.0}
        decision_mock.action = DecisionAction.CONSIDER_LONG
        decision_mock.reason = "Test"
        await service.run_cycle(
            account_name="test_acc",
            symbols=["ETHUSDT"],
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )
        assert decision_mock.action == DecisionAction.HOLD
        assert "REJECTED by HTF Bear Trend" in decision_mock.reason
        
        # Next test htf_short_allowed = False
        decision_mock.action = DecisionAction.CONSIDER_SHORT
        decision_mock.reason = "Test"
        await service.run_cycle(
            account_name="test_acc",
            symbols=["ETHUSDT"],
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )
        assert decision_mock.action == DecisionAction.HOLD
        assert "REJECTED by HTF Bull Trend" in decision_mock.reason
