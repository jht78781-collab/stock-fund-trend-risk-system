import json
import logging
import time
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._client: Redis | None = None
        self._memory_cache: dict[str, tuple[float, Any]] = {}

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._client = Redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def get_json(self, key: str) -> Any | None:
        try:
            raw_value = self.client.get(key)
            if raw_value is not None:
                return json.loads(raw_value)
        except RedisError as exc:
            logger.warning("Redis read failed, falling back to memory cache: %s", exc)

        cached = self._memory_cache.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at < time.time():
            self._memory_cache.pop(key, None)
            return None
        return value

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        payload = json.dumps(value, ensure_ascii=False, default=str)
        try:
            self.client.setex(key, ttl_seconds, payload)
        except RedisError as exc:
            logger.warning("Redis write failed, storing in memory cache: %s", exc)

        self._memory_cache[key] = (time.time() + ttl_seconds, value)


cache = RedisCache(settings.REDIS_URL)

