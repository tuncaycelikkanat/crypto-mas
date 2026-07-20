import json
from typing import Any

from redis import Redis
from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.config_version_repository import ConfigVersionRepository


class ConfigService:
    def __init__(self, db: Session, redis: Redis | None = None) -> None:
        self.db = db
        self.redis = redis
        self.repository = ConfigVersionRepository(db)

    def get_config(self, name: str) -> dict[str, Any] | None:
        cache_key = f"config:{name}"

        if self.redis:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)  # type: ignore

        config_version = self.repository.get_active_config(name)
        if not config_version:
            return None

        if self.redis:
            self.redis.set(cache_key, json.dumps(config_version.config_json), ex=300)

        return config_version.config_json

    def set_active_version(self, name: str, version: str) -> None:
        self.repository.set_active(name, version)
        
        if self.redis:
            cache_key = f"config:{name}"
            self.redis.delete(cache_key)
