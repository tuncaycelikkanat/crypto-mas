import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from crypto_mas.services.scheduler_service import SchedulerService

def test_scheduler_singleton():
    scheduler1 = SchedulerService()
    scheduler2 = SchedulerService()
    
    assert scheduler1 is scheduler2

def test_scheduler_status():
    scheduler = SchedulerService()
    
    # ensure clean state
    if scheduler._scheduler and scheduler._scheduler.running:
        scheduler.shutdown()
        
    status = scheduler.get_status()
    assert "bots" in status
    assert len(status["bots"]) == 0

@pytest.mark.asyncio
async def test_scheduler_start_stop():
    scheduler = SchedulerService()
    
    # Since we test without a real asyncio loop running for the scheduler, we might just assert properties
    if scheduler._scheduler and scheduler._scheduler.running:
        scheduler.shutdown()
        
    assert not scheduler._scheduler.running
    scheduler.start()
    assert scheduler._scheduler.running
    
    scheduler.start_bot("test_bot", interval_seconds=10, symbols=["BTCUSDT"])
    
    status = scheduler.get_status()
    assert len(status["bots"]) == 1
    assert status["bots"][0]["bot_id"] == "test_bot"
    
    scheduler.stop_bot("test_bot")
    status2 = scheduler.get_status()
    assert len(status2["bots"]) == 0
    
    scheduler.shutdown()

@pytest.mark.asyncio
async def test_update_symbols():
    scheduler = SchedulerService()
    scheduler.start()
    
    scheduler.start_bot("test_bot2", interval_seconds=10, symbols=["BTCUSDT"])
    scheduler.update_symbols("test_bot2", ["ETHUSDT", "BTCUSDT"])
    
    status = scheduler.get_status()
    bot = status["bots"][0]
    assert "ETHUSDT" in bot["symbols"]
    
    scheduler.stop_bot("test_bot2")
    scheduler.shutdown()
