"""Simple in-process TTL cache using cachetools."""
import time
from typing import Any, Optional
from cachetools import TTLCache
from app.config import settings

_cache: TTLCache = TTLCache(maxsize=128, ttl=settings.cache_ttl_seconds)


def get(key: str) -> Optional[Any]:
    return _cache.get(key)


def set_with_ts(key: str, value: Any) -> None:
    _cache[key] = value
    _cache[f"__ts_{key}"] = time.time()


def get_ts(key: str) -> Optional[float]:
    return _cache.get(f"__ts_{key}")
