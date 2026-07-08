import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import websockets

from crypto_mas.services.market_data_service.websocket_client import BinanceWebsocketClient


@pytest.fixture
def ws_client():
    return BinanceWebsocketClient()


def test_add_subscription_and_callback(ws_client):
    ws_client.add_subscription("BTCUSDT", "trade")
    assert "btcusdt@trade" in ws_client._subscriptions

    def dummy_callback(stream, payload):
        pass

    ws_client.add_callback(dummy_callback)
    assert len(ws_client._callbacks) == 1
    assert ws_client._callbacks[0] == dummy_callback


@pytest.mark.asyncio
async def test_handle_messages_dispatch(ws_client):
    ws_client.add_subscription("BTCUSDT", "trade")
    
    mock_callback = AsyncMock()
    ws_client.add_callback(mock_callback)
    
    # We will mock the websocket connection and its recv method
    mock_ws = AsyncMock()
    
    # First recv returns a message, second recv raises an exception to break the loop
    mock_ws.recv.side_effect = [
        json.dumps({"stream": "btcusdt@trade", "data": {"p": "50000", "q": "1"}}),
        Exception("Break loop")
    ]
    
    ws_client._is_running = True
    
    # Create an async context manager mock for websockets.connect
    mock_connect_cm = AsyncMock()
    mock_connect_cm.__aenter__.return_value = mock_ws
    
    with patch("crypto_mas.services.market_data_service.websocket_client.websockets.connect", return_value=mock_connect_cm):
        # We run the loop. It should process one message, then hit the exception.
        # The exception is caught by the broad except block, which does asyncio.sleep(5).
        # We need to stop _is_running so the outer while loop breaks too.
        
        # We can patch asyncio.sleep to break the loop
        async def mock_sleep(seconds):
            ws_client._is_running = False
            
        with patch("crypto_mas.services.market_data_service.websocket_client.asyncio.sleep", side_effect=mock_sleep):
            await ws_client._handle_messages()
            
    # Allow dispatched tasks to run
    await asyncio.sleep(0)
    
    mock_callback.assert_called_once_with("btcusdt@trade", {"p": "50000", "q": "1"})


@pytest.mark.asyncio
async def test_handle_messages_reconnects_on_close(ws_client):
    ws_client.add_subscription("BTCUSDT", "trade")
    
    mock_ws = AsyncMock()
    mock_ws.recv.side_effect = websockets.exceptions.ConnectionClosedOK(None, None)
    
    ws_client._is_running = True
    
    mock_connect_cm = AsyncMock()
    mock_connect_cm.__aenter__.return_value = mock_ws
    
    with patch("crypto_mas.services.market_data_service.websocket_client.websockets.connect", return_value=mock_connect_cm):
        async def mock_sleep(seconds):
            ws_client._is_running = False  # Break outer loop after first reconnect attempt
            
        with patch("crypto_mas.services.market_data_service.websocket_client.asyncio.sleep", side_effect=mock_sleep) as sleep_mock:
            await ws_client._handle_messages()
            
            sleep_mock.assert_called_once_with(5)


@pytest.mark.asyncio
async def test_start_and_stop(ws_client):
    # Mock handle_messages so start doesn't actually try to connect
    with patch.object(ws_client, "_handle_messages", new_callable=AsyncMock) as mock_handle:
        ws_client.start()
        assert ws_client._is_running is True
        
        # Allow the created task to start executing
        await asyncio.sleep(0)
        mock_handle.assert_called_once()
        
        ws_client._connection = AsyncMock()
        ws_client.stop()
        
        assert ws_client._is_running is False
        await asyncio.sleep(0)
        ws_client._connection.close.assert_called_once()
