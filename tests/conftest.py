import pytest

from crypto_mas.services.trading_cycle_service.executor_queue import OrderExecutorQueue


@pytest.fixture(autouse=True)
def reset_executor_queue_singleton():
    """
    Ensures the OrderExecutorQueue singleton is clean for each test.
    This prevents cross-test contamination where a closed DB session is kept in the broker factory.
    """
    queue = OrderExecutorQueue.get_instance()
    queue.sync_mode = False
    queue._broker_factory = None
    
    yield
    
    queue.sync_mode = False
    queue._broker_factory = None
