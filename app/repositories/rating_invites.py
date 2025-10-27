from __future__ import annotations

from app.config.settings import Settings
from app.services.auth import normalize_db_url


async def _connect():
    settings = Settings()
    if not settings.DATABASE_URL:
        return None
    import asyncpg
    url = normalize_db_url(settings.DATABASE_URL)
    return await asyncpg.connect(url, timeout=10)


async def acquire_rating_invite_lock(user_id: int) -> bool:
    """Пытается вставить запись для пользователя. Возвращает True, если это первый раз.
    Используем уникальный primary key для атомарности.
    """
    conn = await _connect()
    if conn is None:
        return False
    try:
        try:
            await conn.execute(
                """
                insert into rating_invites (user_id) values ($1)
                """,
                user_id,
            )
            return True
        except Exception:
            return False
    finally:
        await conn.close()


