from __future__ import annotations

from typing import Optional

from app.config.settings import Settings
from app.services.auth import normalize_db_url


async def _connect():
    settings = Settings()
    if not settings.DATABASE_URL:
        return None
    import asyncpg
    url = normalize_db_url(settings.DATABASE_URL)
    return await asyncpg.connect(url, timeout=10)


VALID_STATS = {"started", "completed", "out_of_moves", "auto_finished"}


async def increment_case_stat(user_id: int, case_id: str, stat: str) -> None:
    if stat not in VALID_STATS:
        raise ValueError("Unknown stat")
    conn = await _connect()
    if conn is None:
        return None
    try:
        await conn.execute(
            """
            insert into case_stats (user_id, case_id, stat, cnt)
            values ($1, $2, $3, 1)
            on conflict (user_id, case_id, stat)
            do update set cnt = case_stats.cnt + 1, updated_at = now()
            """,
            user_id,
            case_id,
            stat,
        )
    finally:
        await conn.close()


async def has_any_completed(user_id: int) -> bool:
    conn = await _connect()
    if conn is None:
        return False
    try:
        row = await conn.fetchrow(
            """
            select 1 from case_stats
            where user_id = $1 and stat = 'completed' and cnt > 0
            limit 1
            """,
            user_id,
        )
        return row is not None
    finally:
        await conn.close()


