from unittest.mock import MagicMock, patch

from crypto_mas.services.decision_orchestrator.multi_symbol_runner import MultiSymbolDecisionRunner
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.engine.strategy.schemas import TradingDecision, DecisionAction
from crypto_mas.domain.models.symbol import Symbol

@patch("crypto_mas.services.decision_orchestrator.multi_symbol_runner.SymbolRepository")
@patch("crypto_mas.services.decision_orchestrator.multi_symbol_runner.FeatureSnapshotRepository")
@patch("crypto_mas.services.decision_orchestrator.multi_symbol_runner.StrategyFactory")
def test_multi_symbol_runner_run(mock_factory, mock_snapshot_repo, mock_symbol_repo):
    db_mock = MagicMock()
    
    symbol_1 = Symbol(symbol="BTCUSDT", exchange=Exchange.BINANCE.value, quote_asset="USDT")
    symbol_2 = Symbol(symbol="ETHUSDT", exchange=Exchange.BINANCE.value, quote_asset="USDT")
    
    repo_inst = mock_symbol_repo.return_value
    repo_inst.list_active_symbols.return_value = [symbol_1, symbol_2]
    
    snapshot_repo_inst = mock_snapshot_repo.return_value
    snapshot_repo_inst.list_by_symbol.return_value = []
    
    strategy_mock = MagicMock()
    mock_factory.create.return_value = strategy_mock
    
    dec_btc = MagicMock(spec=TradingDecision)
    dec_btc.symbol = "BTCUSDT"
    dec_btc.action = DecisionAction.CONSIDER_LONG
    dec_btc.confidence = 0.9
    
    dec_eth = MagicMock(spec=TradingDecision)
    dec_eth.symbol = "ETHUSDT"
    dec_eth.action = DecisionAction.CONSIDER_SHORT
    dec_eth.confidence = 0.8
    
    strategy_mock.decide.side_effect = [dec_btc, dec_eth]
    
    runner = MultiSymbolDecisionRunner(db=db_mock, strategy_name="multi_agent")
    result = runner.run(Exchange.BINANCE, Timeframe.FOUR_HOURS)
    
    assert result.requested_symbols == 2
    assert result.processed_symbols == 2
    assert len(result.decisions) == 2
    
    # Check sorting
    assert result.decisions[0].symbol == "BTCUSDT"
    assert result.decisions[1].symbol == "ETHUSDT"

@patch("crypto_mas.services.decision_orchestrator.multi_symbol_runner.SymbolRepository")
@patch("crypto_mas.services.decision_orchestrator.multi_symbol_runner.FeatureSnapshotRepository")
@patch("crypto_mas.services.decision_orchestrator.multi_symbol_runner.StrategyFactory")
def test_multi_symbol_runner_none_decision(mock_factory, mock_snapshot_repo, mock_symbol_repo):
    db_mock = MagicMock()
    
    symbol_1 = Symbol(symbol="BTCUSDT", exchange=Exchange.BINANCE.value, quote_asset="USDT")
    
    repo_inst = mock_symbol_repo.return_value
    repo_inst.list_active_symbols.return_value = [symbol_1]
    
    strategy_mock = MagicMock()
    mock_factory.create.return_value = strategy_mock
    strategy_mock.decide.return_value = None
    
    runner = MultiSymbolDecisionRunner(db=db_mock)
    result = runner.run(Exchange.BINANCE, Timeframe.FOUR_HOURS)
    
    assert result.requested_symbols == 1
    assert result.processed_symbols == 0
    assert len(result.decisions) == 0

def test_decision_sort_key():
    runner = MultiSymbolDecisionRunner(db=MagicMock())
    
    dec1 = MagicMock(spec=TradingDecision)
    dec1.symbol = "BTCUSDT"
    dec1.action = DecisionAction.CONSIDER_LONG
    dec1.confidence = 0.9
    
    dec2 = MagicMock(spec=TradingDecision)
    dec2.symbol = "ETHUSDT"
    dec2.action = DecisionAction.CONSIDER_SHORT
    dec2.confidence = 0.9
    
    dec3 = MagicMock(spec=TradingDecision)
    dec3.symbol = "SOLUSDT"
    dec3.action = DecisionAction.CONSIDER_LONG
    dec3.confidence = 0.95
    
    key1 = runner._decision_sort_key(dec1)
    key2 = runner._decision_sort_key(dec2)
    key3 = runner._decision_sort_key(dec3)
    
    assert key1 == (4, 0.9)
    assert key2 == (3, 0.9)
    assert key3 == (4, 0.95)
