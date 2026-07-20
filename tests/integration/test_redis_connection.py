import pytest

from crypto_mas.infrastructure.cache.redis_client import check_redis_connection


@pytest.mark.skip(reason="Redis not guaranteed to be running in CI/CD tests.")
def test_redis_connection() -> None:
    assert check_redis_connection() is True
