"""
Redis client for MireApprove.

Provides connection management, caching, and session storage
to replace in-memory dictionaries (user_states, marking_sessions).
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from backend.config import (
    CACHE_TTL_SECONDS,
    REDIS_PREFIX,
    REDIS_URL,
    SESSION_TTL_SECONDS,
)

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client with connection pooling."""

    def __init__(self, url: str = REDIS_URL, prefix: str = REDIS_PREFIX) -> None:
        """
        Initialize Redis client.

        Args:
            url: Redis connection URL
            prefix: Prefix for all keys
        """
        self.url = url
        self.prefix = prefix
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Create Redis connection pool."""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.url,
                max_connections=10,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
            logger.info("Redis connection pool created")

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            logger.info("Redis connection pool closed")

    async def ping(self) -> bool:
        """Check Redis connection."""
        try:
            if self._client:
                await self._client.ping()
                return True
            return False
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def _key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.prefix}{key}"

    # Generic cache methods

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            if self._client:
                return await self._client.get(self._key(key))
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> bool:
        """Set value with TTL."""
        try:
            if self._client:
                await self._client.set(self._key(key), value, ex=ttl)
                return True
            return False
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key."""
        try:
            if self._client:
                await self._client.delete(self._key(key))
                return True
            return False
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            if self._client:
                return await self._client.exists(self._key(key)) > 0
            return False
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    # JSON helpers

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self, key: str, value: Any, ttl: int = CACHE_TTL_SECONDS
    ) -> bool:
        """Set JSON value."""
        try:
            return await self.set(key, json.dumps(value), ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"Redis set_json error: {e}")
            return False

    # User states (for Telegram bot)

    async def get_user_state(self, tg_userid: int) -> Optional[dict]:
        """Get user state."""
        return await self.get_json(f"user_state:{tg_userid}")

    async def set_user_state(
        self, tg_userid: int, state: dict, ttl: int = SESSION_TTL_SECONDS
    ) -> bool:
        """Set user state."""
        return await self.set_json(f"user_state:{tg_userid}", state, ttl)

    async def delete_user_state(self, tg_userid: int) -> bool:
        """Delete user state."""
        return await self.delete(f"user_state:{tg_userid}")

    # Marking sessions

    async def get_marking_session(self, session_id: str) -> Optional[dict]:
        """Get marking session."""
        return await self.get_json(f"marking_session:{session_id}")

    async def set_marking_session(
        self, session_id: str, session_data: dict, ttl: int = 3600
    ) -> bool:
        """Set marking session (1 hour TTL by default)."""
        return await self.set_json(f"marking_session:{session_id}", session_data, ttl)

    async def delete_marking_session(self, session_id: str) -> bool:
        """Delete marking session."""
        return await self.delete(f"marking_session:{session_id}")

    async def update_marking_session(self, session_id: str, updates: dict) -> bool:
        """Update marking session data."""
        session = await self.get_marking_session(session_id)
        if session:
            session.update(updates)
            return await self.set_marking_session(session_id, session)
        return False

    # Rate limiting

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """
        Check rate limit for identifier.

        Args:
            identifier: User ID or IP address
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        try:
            if not self._client:
                return True, max_requests

            key = self._key(f"rate_limit:{identifier}")

            # Get current count
            current = await self._client.get(key)

            if current is None:
                # First request in window
                await self._client.set(key, "1", ex=window_seconds)
                return True, max_requests - 1

            count = int(current)

            if count >= max_requests:
                # Rate limit exceeded
                return False, 0

            # Increment counter
            await self._client.incr(key)
            return True, max_requests - count - 1

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open - allow request if Redis fails
            return True, max_requests

    # Schedule cache

    async def get_schedule_cache(self, tg_userid: int, date: str) -> Optional[dict]:
        """Get cached schedule for user and date."""
        return await self.get_json(f"schedule:{tg_userid}:{date}")

    async def set_schedule_cache(
        self, tg_userid: int, date: str, schedule: dict, ttl: int = 300
    ) -> bool:
        """Cache schedule for user and date (5 min TTL)."""
        return await self.set_json(f"schedule:{tg_userid}:{date}", schedule, ttl)

    async def invalidate_schedule_cache(self, tg_userid: int) -> bool:
        """Invalidate all schedule cache for user."""
        try:
            if self._client:
                pattern = self._key(f"schedule:{tg_userid}:*")
                keys = []
                async for key in self._client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await self._client.delete(*keys)
                return True
            return False
        except Exception as e:
            logger.error(f"Schedule cache invalidation error: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()
