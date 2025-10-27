from __future__ import annotations

from typing import Optional, Dict, Any

from app.config.settings import Settings
from app.services.auth import normalize_db_url


async def _connect():
    settings = Settings()
    if not settings.DATABASE_URL:
        return None
    import asyncpg  # локальный импорт, чтобы избежать импорта если не используется

    url = normalize_db_url(settings.DATABASE_URL)
    conn = await asyncpg.connect(url, timeout=10)
    return conn


async def get_role_by_user_id(user_id: int) -> Optional[str]:
    conn = await _connect()
    if conn is None:
        return None
    try:
        role = await conn.fetchval(
            "select role from authorized_users where user_id=$1",
            user_id,
        )
        return role
    finally:
        await conn.close()


async def upsert_authorized_user(user_id: int, role: str) -> None:
    conn = await _connect()
    if conn is None:
        return None
    try:
        await conn.execute(
            """
            insert into authorized_users (user_id, role)
            values ($1, $2)
            on conflict (user_id) do update set role=excluded.role
            """,
            user_id,
            role,
        )
    finally:
        await conn.close()


async def get_authorized_user(user_id: int) -> Optional[Dict[str, Any]]:
    conn = await _connect()
    if conn is None:
        return None
    try:
        row = await conn.fetchrow(
            "select user_id, role, created_at from authorized_users where user_id=$1",
            user_id,
        )
        if row is None:
            return None
        return {"user_id": row["user_id"], "role": row["role"], "created_at": row["created_at"]}
    finally:
        await conn.close()
