import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
import websockets

from crypto_mas.services.market_data_service.websocket_client import BinanceWebsocketClient


@pytest.mark.asyncio
async def test_add_remove_subscription():
    client = BinanceWebsocketClient()
    client._connection = MagicMock()
    client._connection.state = websockets.State.OPEN
    
    client._send_payload = AsyncMock()
    
    # Add subscription
    client.add_subscription("BTCUSDT", "trade")
    assert "btcusdt@trade" in client._subscriptions
    assert client._send_payload.called
        
    # Remove subscription
    client._send_payload.reset_mock()
    client.remove_subscription("BTCUSDT", "trade")
    assert "btcusdt@trade" not in client._subscriptions
    assert client._send_payload.called
        
@pytest.mark.asyncio
async def test_send_payload():
    client = BinanceWebsocketClient()
    client._connection = MagicMock()
    client._connection.state = websockets.State.OPEN
    
    # Provide an async mock for send
    client._connection.send = MagicMock(return_value=asyncio.Future())
    client._connection.send.return_value.set_result(None)
    
    await client._send_payload({"method": "SUBSCRIBE"})
    client._connection.send.assert_called_once()
