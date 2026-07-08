from datetime import datetime, timedelta, UTC
import pytest
from crypto_mas.infrastructure.time.time_provider import SimulatedTimeProvider, FixedTimeProvider

def test_simulated_time_provider():
    # Test without tzinfo
    dt = datetime(2023, 1, 1, 12, 0, 0)
    provider = SimulatedTimeProvider(start_time=dt)
    
    assert provider.now() == datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
    
    provider.tick(timedelta(hours=1))
    assert provider.now() == datetime(2023, 1, 1, 13, 0, 0, tzinfo=UTC)
    
    # Test set_time without tzinfo
    dt_new = datetime(2023, 2, 1, 12, 0, 0)
    provider.set_time(dt_new)
    assert provider.now() == datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC)
    
    # Test set_time with tzinfo
    dt_new_tz = datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC)
    provider.set_time(dt_new_tz)
    assert provider.now() == datetime(2023, 2, 1, 12, 0, 0, tzinfo=UTC)
