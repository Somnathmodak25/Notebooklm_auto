# gateway/middleware.py
"""
Rate limiting middleware with sliding window mechanism.
"""

import time
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory / Redis sliding window rate limiter per API key.
    """

    _in_memory_counters: Dict[str, Dict[str, int]] = {}

    def __init__(self, redis: Optional[Any] = None):
        self.redis = redis

    async def check(self, api_key: str, limit_per_minute: int) -> dict:
        window = 60
        now = int(time.time())
        window_key = now // window
        redis_key = f"rl:{api_key}:{window_key}"

        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.incr(redis_key)
                pipe.expire(redis_key, window * 2)
                results = await pipe.execute()
                count = results[0]
            except Exception as e:
                logger.warning("Redis rate limit check failed, falling back: %s", e)
                count = self._check_in_memory(api_key, window_key)
        else:
            count = self._check_in_memory(api_key, window_key)

        if count > limit_per_minute:
            retry_after = window - (now % window)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "limit": limit_per_minute,
                    "window": "60s",
                    "current": count,
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return {
            "requests_this_minute": count,
            "limit": limit_per_minute,
            "remaining": max(0, limit_per_minute - count),
        }

    def _check_in_memory(self, api_key: str, window_key: int) -> int:
        entry = self._in_memory_counters.get(api_key, {})
        if entry.get("window") != window_key:
            entry = {"window": window_key, "count": 1}
        else:
            entry["count"] += 1
        self._in_memory_counters[api_key] = entry
        return entry["count"]
