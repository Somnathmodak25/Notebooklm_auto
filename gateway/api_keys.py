# gateway/api_keys.py
"""
API Key management backed by SQLite + optional Redis cache.
"""

import secrets
import json
import asyncio
from datetime import datetime
from typing import Optional, List, Any
import aiosqlite
import logging

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from gateway.models import APIKey

logger = logging.getLogger(__name__)


class APIKeyStore:
    """
    Persistent API key store.
    SQLite for durability, optional Redis for fast lookups.
    """

    def __init__(self, db_path: str, redis: Optional[Any] = None):
        self.db_path = db_path
        self.redis = redis

    async def init(self):
        """Create database tables if they do not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key            TEXT PRIMARY KEY,
                    name           TEXT NOT NULL,
                    account_id     TEXT NOT NULL,
                    permissions    TEXT NOT NULL DEFAULT '["read","write","chat","studio"]',
                    rate_limit     INTEGER NOT NULL DEFAULT 60,
                    created_at     TEXT NOT NULL,
                    last_used      TEXT,
                    total_requests INTEGER NOT NULL DEFAULT 0,
                    is_active      INTEGER NOT NULL DEFAULT 1
                )
            """)
            await db.commit()
        logger.info("API key store initialized at %s", self.db_path)

    async def create(
        self,
        account_id: str,
        name: str,
        permissions: Optional[List[str]] = None,
        rate_limit: int = 60,
    ) -> APIKey:
        """Generate and persist a new API key."""
        key = f"nlm_{secrets.token_urlsafe(32)}"
        now = datetime.utcnow().isoformat()

        api_key = APIKey(
            key=key,
            name=name,
            account_id=account_id,
            permissions=permissions or ["read", "write", "chat", "studio"],
            rate_limit=rate_limit,
            created_at=datetime.utcnow(),
        )

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO api_keys
                  (key, name, account_id, permissions, rate_limit, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    name,
                    account_id,
                    json.dumps(api_key.permissions),
                    rate_limit,
                    now,
                ),
            )
            await db.commit()

        if self.redis:
            try:
                await self.redis.set(
                    f"apikey:{key}",
                    api_key.model_dump_json(),
                    ex=86400,
                )
            except Exception as e:
                logger.warning("Redis set failed: %s", e)

        logger.info("API key created: %s (%s)", name, account_id)
        return api_key

    async def validate(self, key: str) -> APIKey:
        """Validate an API key. Returns APIKey or raises Exception."""
        if self.redis:
            try:
                cached = await self.redis.get(f"apikey:{key}")
                if cached:
                    data = json.loads(cached)
                    api_key = APIKey(**data)
                    if not api_key.is_active:
                        raise ValueError("API key revoked")
                    asyncio.create_task(self._increment_usage(key))
                    return api_key
            except ValueError:
                raise
            except Exception as exc:
                logger.debug("Redis cache miss or error: %s", exc)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM api_keys WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            raise ValueError("Invalid API key")

        if not row["is_active"]:
            raise ValueError("API key revoked")

        api_key = APIKey(
            key=row["key"],
            name=row["name"],
            account_id=row["account_id"],
            permissions=json.loads(row["permissions"]),
            rate_limit=row["rate_limit"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_used=(
                datetime.fromisoformat(row["last_used"])
                if row["last_used"] else None
            ),
            total_requests=row["total_requests"],
            is_active=bool(row["is_active"]),
        )

        if self.redis:
            try:
                await self.redis.set(
                    f"apikey:{key}",
                    api_key.model_dump_json(),
                    ex=3600,
                )
            except Exception:
                pass

        asyncio.create_task(self._increment_usage(key))
        return api_key

    async def _increment_usage(self, key: str):
        """Update usage stats asynchronously."""
        now = datetime.utcnow().isoformat()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE api_keys
                    SET total_requests = total_requests + 1,
                        last_used      = ?
                    WHERE key = ?
                    """,
                    (now, key),
                )
                await db.commit()
        except Exception as exc:
            logger.warning("Failed to update usage stats: %s", exc)

    async def revoke(self, key: str) -> bool:
        """Revoke an API key."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE api_keys SET is_active = 0 WHERE key = ?",
                (key,),
            )
            await db.commit()

        if self.redis:
            try:
                await self.redis.delete(f"apikey:{key}")
            except Exception:
                pass
        return True

    async def list_keys(self, account_id: Optional[str] = None) -> list:
        """List all API keys."""
        query = "SELECT * FROM api_keys"
        params = []
        if account_id:
            query += " WHERE account_id = ?"
            params = [account_id]

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        return [
            {
                "key": row["key"][:12] + "...",
                "name": row["name"],
                "account_id": row["account_id"],
                "total_requests": row["total_requests"],
                "last_used": row["last_used"],
                "is_active": bool(row["is_active"]),
            }
            for row in rows
        ]
