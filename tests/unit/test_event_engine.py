from unittest.mock import MagicMock, patch

import pytest

from crypto_mas.engine.strategy.event_engine import EventEngine


@pytest.mark.asyncio
async def test_process_websocket_message_invalid():
    engine = EventEngine()
    # Should not raise any error, just return
    await engine.process_websocket_message("invalid_stream", {})

@pytest.mark.asyncio
async def test_process_websocket_message_trade():
    engine = EventEngine()
    
    with patch.object(engine, '_process_trade') as mock_trade:
        await engine.process_websocket_message("btcusdt@trade", {"p": "50000", "q": "0.1"})
        mock_trade.assert_called_once_with("BTCUSDT", {"p": "50000", "q": "0.1"})

@pytest.mark.asyncio
async def test_process_websocket_message_depth():
    engine = EventEngine()
    
    with patch.object(engine, '_process_depth') as mock_depth:
        await engine.process_websocket_message("ethusdt@depth10@100ms", {})
        mock_depth.assert_called_once_with("ETHUSDT", {})

@pytest.mark.asyncio
async def test_process_trade_spike():
    engine = EventEngine()
    
    with patch.object(engine, '_trigger_cycle') as mock_trigger:
        with patch.object(engine, '_get_rvol', return_value=(3.0, 2.0)):
            # Trigger spike by making buy vol large
            await engine._process_trade("BTCUSDT", {"p": "60000", "q": "1.0", "m": False}) # 60000 buy vol
            
            mock_trigger.assert_called_once_with("BTCUSDT")

@pytest.mark.asyncio
async def test_process_trade_cooldown():
    engine = EventEngine()
    
    with patch.object(engine, '_trigger_cycle') as mock_trigger:
        with patch.object(engine, '_get_rvol', return_value=(3.0, 2.0)):
            # First spike
            await engine._process_trade("BTCUSDT", {"p": "60000", "q": "1.0", "m": False})
            assert mock_trigger.call_count == 1
            
            # Second spike immediately after
            await engine._process_trade("BTCUSDT", {"p": "60000", "q": "1.0", "m": False})
            assert mock_trigger.call_count == 1 # Shouldn't trigger again

@pytest.mark.asyncio
async def test_process_depth():
    engine = EventEngine()
    await engine._process_depth("BTCUSDT", {})

@pytest.mark.asyncio
@patch("crypto_mas.services.trading_cycle_service.cycle_orchestrator.TradingCycleService")
@patch("crypto_mas.services.market_data_service.provider_factory.get_market_data_provider")
@patch("crypto_mas.infrastructure.db.session.SessionLocal")
async def test_trigger_cycle(mock_session, mock_get_provider, mock_cycle_service):
    engine = EventEngine()
    
    db_mock = MagicMock()
    mock_session.return_value = db_mock
    
    provider_mock = MagicMock()
    mock_get_provider.return_value = provider_mock
    
    cycle_inst_mock = MagicMock()
    mock_cycle_service.return_value = cycle_inst_mock
    
    # We mock cycle_inst_mock.run_cycle to be an async function that just returns
    async def mock_run_cycle(*args, **kwargs):
        pass
    
    cycle_inst_mock.run_cycle = mock_run_cycle
    
    await engine._trigger_cycle("BTCUSDT")
    
    db_mock.close.assert_called_once()
