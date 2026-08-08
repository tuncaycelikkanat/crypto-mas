import pytest
from unittest.mock import AsyncMock, MagicMock
from crypto_mas.engine.llm_committee.cost_tracker import CostTracker

@pytest.mark.asyncio
async def test_cost_tracker_under_limit():
    tracker = CostTracker(daily_cap_usd=20.0)
    tracker._alerter = AsyncMock()
    
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 10.0
    
    allowed = await tracker.check_daily_limit(mock_db)
    assert allowed is True
    tracker._alerter.send.assert_not_called()

@pytest.mark.asyncio
async def test_cost_tracker_near_limit_warning():
    tracker = CostTracker(daily_cap_usd=20.0)
    tracker._alerter = AsyncMock()
    
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 18.0
    
    allowed = await tracker.check_daily_limit(mock_db)
    assert allowed is True
    tracker._alerter.send.assert_called_once()
    assert "UYARISI" in tracker._alerter.send.call_args[0][0]

@pytest.mark.asyncio
async def test_cost_tracker_over_limit():
    tracker = CostTracker(daily_cap_usd=20.0)
    tracker._alerter = AsyncMock()
    
    mock_db = MagicMock()
    mock_db.execute.return_value.scalar.return_value = 25.0
    
    allowed = await tracker.check_daily_limit(mock_db)
    assert allowed is False
    tracker._alerter.send.assert_called_once()
    assert "AŞILDI" in tracker._alerter.send.call_args[0][0]
