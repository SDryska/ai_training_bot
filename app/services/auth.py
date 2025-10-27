from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def normalize_db_url(database_url: Optional[str]) -> Optional[str]:
    """Конвертирует sqlalchemy-style async URL в asyncpg URL при необходимости."""
    if not database_url:
        return database_url
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


def run_migrations(logger: logging.Logger, database_url: Optional[str] = None) -> None:
    """Запускает миграции Alembic для инициализации/обновления схемы БД."""
    if not database_url:
        logger.info("DATABASE_URL не задан, миграции пропущены")
        return

    project_root = Path(__file__).resolve().parents[2]
    alembic_ini = project_root / "alembic.ini"

    if not alembic_ini.exists():
        logger.warning("Файл alembic.ini не найден, миграции пропущены")
        return

    try:
        import importlib

        importlib.import_module("alembic")
    except ModuleNotFoundError:
        logger.error("❌ Alembic НЕ УСТАНОВЛЕН! Таблицы БД не будут созданы. Установите: pip install alembic sqlalchemy")
        return
    except Exception as e:
        logger.warning("Не удалось инициализировать Alembic: %s", e)
        return

    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    env["ALEMBIC_CONFIG"] = str(alembic_ini)

    existing_pythonpath = env.get("PYTHONPATH", "")
    project_path = str(project_root)
    env["PYTHONPATH"] = project_path if not existing_pythonpath else f"{project_path}{os.pathsep}{existing_pythonpath}"

    command = [sys.executable, "-m", "alembic", "upgrade", "head"]

    try:
        logger.info("⏳ Применение миграций БД...")
        result = subprocess.run(
            command,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=300,  # Увеличил с 60 до 300 секунд (5 минут)
            env=env,
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                "❌ Ошибка при применении миграций:\n%s",
                result.stderr.strip() or result.stdout.strip() or "unknown error",
            )
            return
        logger.info("✅ Миграции БД применены успешно (conversations, fsm_storage)")
    except subprocess.TimeoutExpired:
        logger.warning("❌ Превышено время ожидания применения миграций (>300s)")
    except Exception as e:
        logger.warning("❌ Не удалось применить миграции БД: %s", e)
