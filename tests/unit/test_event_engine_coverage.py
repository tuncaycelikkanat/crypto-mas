from unittest.mock import patch

import pytest

from crypto_mas.engine.strategy.event_engine import EventEngine


@pytest.mark.asyncio
async def test_process_trade():
    engine = EventEngine()
    
    # Send a small buy trade
    await engine.process_websocket_message("BTCUSDT@trade", {"p": "50000", "q": "0.1", "m": False})
    assert engine.metrics_store.get_metric("BTCUSDT", "last_price") == 50000.0
    
    # Send a massive buy trade to trigger volume spike
    # Total volume > 50000 to trigger spike check
    with patch("crypto_mas.engine.strategy.event_engine.asyncio.create_task") as mock_task:
        with patch.object(engine, '_get_rvol', return_value=(3.0, 2.0)):
            await engine.process_websocket_message("BTCUSDT@trade", {"p": "50000", "q": "2.0", "m": False})
            
            assert engine.metrics_store.get_metric("BTCUSDT", "volume_spike") is True
            assert mock_task.called

@pytest.mark.asyncio
async def test_process_depth():
    engine = EventEngine()
    
    await engine.process_websocket_message("ETHUSDT@depth5@100ms", {
        "bids": [["1000", "1"]],
        "asks": [["1001", "0.5"]]
    })
    
    depth_imbalance = engine.metrics_store.get_metric("ETHUSDT", "depth_imbalance")
    assert depth_imbalance > 0.6  # Bid is 1000, ask is 500. Total 1500. Bid ratio is 0.666
