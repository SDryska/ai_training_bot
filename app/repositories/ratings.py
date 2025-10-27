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


RATING_QUESTIONS = [
    "overall_impression",
    "recommend_to_colleagues",
    "will_help_at_work",
]


async def upsert_rating(user_id: int, question: str, rating: int) -> None:
    if question not in RATING_QUESTIONS:
        raise ValueError("Unknown rating question")
    conn = await _connect()
    if conn is None:
        return None
    try:
        await conn.execute(
            """
            insert into bot_ratings (user_id, question, rating)
            values ($1, $2, $3)
            on conflict (user_id, question) do update
            set rating = excluded.rating, updated_at = now()
            """,
            user_id,
            question,
            rating,
        )
    finally:
        await conn.close()


async def get_user_ratings(user_id: int) -> Dict[str, int]:
    conn = await _connect()
    if conn is None:
        return {}
    try:
        rows = await conn.fetch(
            """
            select question, rating
            from bot_ratings
            where user_id = $1
            """,
            user_id,
        )
        return {str(r["question"]): int(r["rating"]) for r in rows}
    finally:
        await conn.close()


async def get_user_rating_for_question(user_id: int, question: str) -> Optional[int]:
    conn = await _connect()
    if conn is None:
        return None
    try:
        row = await conn.fetchrow(
            """
            select rating
            from bot_ratings
            where user_id = $1 and question = $2
            """,
            user_id,
            question,
        )
        return int(row["rating"]) if row else None
    finally:
        await conn.close()



async def insert_rating_comment(user_id: int, comment: str) -> None:
    """Добавляет новый текстовый комментарий; не перезаписывает существующие."""
    conn = await _connect()
    if conn is None:
        return None
    try:
        await conn.execute(
            """
            insert into rating_comments (user_id, comment)
            values ($1, $2)
            """,
            user_id,
            comment,
        )
    finally:
        await conn.close()
