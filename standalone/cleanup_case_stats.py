#!/usr/bin/env python3
"""
Удаление статистики по указанным case_id из таблицы case_stats.

Использование:
  python standalone/cleanup_case_stats.py ai_demo another_case
  python standalone/cleanup_case_stats.py --yes ai_demo another_case   # без подтверждения
  python standalone/cleanup_case_stats.py --show ai_demo another_case  # только показать количество к удалению
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import List

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from dotenv import load_dotenv
from app.services.auth import normalize_db_url


load_dotenv()


def _get_database_url() -> str | None:
    return os.getenv("DATABASE_URL")


async def delete_case_stats(case_ids: List[str]) -> int:
    """Удаляет записи из case_stats для указанных case_id. Возвращает кол-во удалённых строк."""
    database_url = _get_database_url()
    if not database_url:
        print("❌ DATABASE_URL не настроен в .env файле")
        return 0

    url = normalize_db_url(database_url)

    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(url, timeout=10)

        # Посчитаем, сколько будет удалено
        to_delete = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM case_stats
            WHERE case_id = ANY($1::text[])
            """,
            case_ids,
        )

        if to_delete == 0:
            print("ℹ️  Записей для удаления не найдено")
            return 0

        result = await conn.execute(
            """
            DELETE FROM case_stats
            WHERE case_id = ANY($1::text[])
            """,
            case_ids,
        )
        # asyncpg возвращает строку вида "DELETE <n>"
        deleted = int(result.split()[-1]) if result else 0
        return deleted
    finally:
        if conn:
            await conn.close()


async def count_case_stats(case_ids: List[str]) -> int:
    database_url = _get_database_url()
    if not database_url:
        print("❌ DATABASE_URL не настроен в .env файле")
        return 0
    url = normalize_db_url(database_url)
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(url, timeout=10)
        return await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM case_stats
            WHERE case_id = ANY($1::text[])
            """,
            case_ids,
        )
    finally:
        if conn:
            await conn.close()


def print_usage() -> None:
    print(
        """
Удаление статистики по указанным case_id из case_stats.

Использование:
  python standalone/cleanup_case_stats.py ai_demo another_case
  python standalone/cleanup_case_stats.py --yes ai_demo another_case   # без подтверждения
  python standalone/cleanup_case_stats.py --show ai_demo another_case  # только показать количество к удалению
""".strip()
    )


async def main() -> None:
    args = [a for a in sys.argv[1:] if a.strip()]
    if not args:
        print_usage()
        return

    confirm = True
    show_only = False
    if "--yes" in args:
        confirm = False
        args.remove("--yes")
    if "--show" in args:
        show_only = True
        args.remove("--show")

    case_ids = args
    if not case_ids:
        print("❌ Не указаны case_id")
        print_usage()
        return

    total = await count_case_stats(case_ids)
    print(f"📊 Найдено записей к удалению: {total}")
    if show_only or total == 0:
        return

    if confirm:
        answer = input(
            f"⚠️  Удалить {total} записей из case_stats для case_id={case_ids}? (yes/no): "
        ).strip().lower()
        if answer != "yes":
            print("Операция отменена")
            return

    deleted = await delete_case_stats(case_ids)
    print(f"✅ Удалено записей: {deleted}")


if __name__ == "__main__":
    asyncio.run(main())


