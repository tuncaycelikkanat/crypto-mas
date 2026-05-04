from redis import Redis

from infrastructure.config.settings import get_settings

settings = get_settings()


def get_redis_client() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


def check_redis_connection() -> bool:
    try:
        client = get_redis_client()
        return bool(client.ping())
    except Exception:
        return False
