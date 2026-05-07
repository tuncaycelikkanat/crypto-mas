from crypto_mas.infrastructure.cache.redis_client import check_redis_connection


def test_redis_connection() -> None:
    assert check_redis_connection() is True
