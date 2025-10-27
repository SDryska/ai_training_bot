#!/usr/bin/env python3
"""
Периодическая выгрузка статистики из БД в Google Sheets.

Требования окружения (.env):
  - DATABASE_URL=postgresql+asyncpg://...
  - ОДИН из вариантов аутентификации сервис-аккаунта:
      - GSPREAD_SERVICE_ACCOUNT_FILE=./gsa.json         (путь к JSON ключу)
      - GSPREAD_SERVICE_ACCOUNT_JSON={...}               (сам JSON строкой)
      - GSPREAD_SERVICE_ACCOUNT_JSON_B64=base64(...)     (тот же JSON в base64)
  - GSHEETS_SPREADSHEET_ID=...              (ID существующей таблицы, опционально)
  - GSHEETS_SPREADSHEET_NAME=EMCO Stats     (название таблицы, если ID не задан)
  - GSHEETS_ALLOW_CREATE=true               (разрешить авто-создание при отсутствии, опционально)
  - EXPORT_INTERVAL_SECONDS=900             (интервал в секундах)

Страницы (листы) Google Sheets:
  - Summary
  - UsersByRole
  - RatingsByQuestion
  - CaseStatistics
  - TableStats
"""

import asyncio
import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

import gspread
from gspread.exceptions import SpreadsheetNotFound
from google.oauth2.service_account import Credentials

# Обеспечиваем доступность корня проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Локальный реюз существующего анализатора
from standalone.db_analyzer import DatabaseAnalyzer


load_dotenv()


class ExportSettings(BaseSettings):
    DATABASE_URL: str = Field(...)
    GSPREAD_SERVICE_ACCOUNT_FILE: str | None = Field(default=None)
    GSPREAD_SERVICE_ACCOUNT_JSON: str | None = Field(default=None)
    GSPREAD_SERVICE_ACCOUNT_JSON_B64: str | None = Field(default=None)
    GSHEETS_SPREADSHEET_ID: str | None = Field(default=None)
    GSHEETS_SPREADSHEET_NAME: str = Field(...)
    EXPORT_INTERVAL_SECONDS: int = Field(900)
    GSHEETS_SHARE_WITH: str | None = Field(default=None, description="Email для шаринга таблицы (опционально)")
    GSHEETS_ALLOW_CREATE: bool = Field(default=True)

    model_config = {
        'env_file': '.env',
        'case_sensitive': False,
        'extra': 'ignore',
    }


SHEET_TITLES = {
    'summary': 'Summary',
    'users_by_role': 'UsersByRole',
    'ratings_by_question': 'RatingsByQuestion',
    'case_statistics': 'CaseStatistics',
    'table_stats': 'TableStats',
    'user_comments': 'Комментарии',
}


def _ensure_worksheet(spreadsheet: gspread.Spreadsheet, title: str) -> gspread.Worksheet:
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=100, cols=20)


def _clear_and_update(ws: gspread.Worksheet, rows: List[List[Any]]) -> None:
    ws.clear()
    if not rows:
        return
    ws.update(rows, value_input_option='RAW')


def _format_summary_rows(now_iso: str, db_size_info: Dict[str, Any], agg: Dict[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = [
        ['Время генерации', now_iso],
        ['Размер базы данных', db_size_info.get('database_size', '')],
        [],
    ]

    users_by_role = agg.get('users_by_role', {})
    rows.append(['Пользователи по ролям:'])
    rows.append(['Роль', 'Количество'])
    for role, cnt in users_by_role.items():
        rows.append([role, cnt])
    rows.append([])

    activity = agg.get('user_activity', {})
    if activity:
        rows.append(['Активность пользователей:'])
        rows.append(['Всего активных пользователей', activity.get('total_active_users', 0)])
        rows.append(['Пользователей с оценками', activity.get('users_with_ratings', 0)])
        rows.append(['Пользователей с активностью по кейсам', activity.get('users_with_case_activity', 0)])
    return rows


def _format_users_by_role_rows(agg: Dict[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = [['Роль', 'Количество']]
    for role, cnt in agg.get('users_by_role', {}).items():
        rows.append([role, cnt])
    return rows


def _format_ratings_by_question_rows(agg: Dict[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = [['Вопрос', 'Всего ответов', 'Средняя оценка', 'Мин', 'Макс']]
    for item in agg.get('ratings_by_question', []):
        rows.append([
            item.get('question', ''),
            item.get('total_responses', 0),
            item.get('average_rating', 0),
            item.get('min_rating', 0),
            item.get('max_rating', 0),
        ])
    return rows


def _format_case_statistics_rows(agg: Dict[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = [['Кейс', 'Тип статистики', 'Уникальных пользователей', 'Всего случаев']]
    for item in agg.get('case_statistics', []):
        rows.append([
            item.get('case_id', ''),
            item.get('stat_type', ''),
            item.get('unique_users', 0),
            item.get('total_occurrences', 0),
        ])
    return rows


def _format_table_stats_rows(table_stats: Dict[str, Any]) -> List[List[Any]]:
    rows: List[List[Any]] = [['Таблица', 'Есть', 'Количество записей']]
    for table_name, info in table_stats.items():
        exists = info.get('exists', True)
        rows.append([table_name, 'Да' if exists else 'Нет', info.get('row_count', 0) if exists else 0])
    return rows


def _format_user_comments_rows(comments: List[Dict[str, Any]]) -> List[List[Any]]:
    rows: List[List[Any]] = [['Пользователь (ID)', 'Комментарий', 'Дата/время']]
    for row in comments:
        rows.append([
            row.get('user_id', ''),
            row.get('comment', ''),
            row.get('created_at', ''),
        ])
    return rows


async def _export_once(settings: ExportSettings) -> None:
    analyzer = DatabaseAnalyzer()
    await analyzer.connect()
    try:
        db_size = await analyzer.get_database_size()
        table_stats = await analyzer.get_table_statistics()
        agg = await analyzer.get_aggregated_statistics()
        # Комментарии пользователей
        comments_query = """
        SELECT user_id, comment, to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS UTC') as created_at
        FROM rating_comments
        ORDER BY created_at DESC
        """
        comments_rows = await analyzer.conn.fetch(comments_query)  # type: ignore[attr-defined]
        user_comments: List[Dict[str, Any]] = [dict(r) for r in comments_rows]
    finally:
        await analyzer.disconnect()

    # Формируем Credentials из файла или из JSON/BASE64 переменных
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds: Credentials
    if settings.GSPREAD_SERVICE_ACCOUNT_JSON_B64:
        info_str = base64.b64decode(settings.GSPREAD_SERVICE_ACCOUNT_JSON_B64).decode('utf-8')
        info = json.loads(info_str)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    elif settings.GSPREAD_SERVICE_ACCOUNT_JSON:
        info = json.loads(settings.GSPREAD_SERVICE_ACCOUNT_JSON)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    elif settings.GSPREAD_SERVICE_ACCOUNT_FILE:
        creds = Credentials.from_service_account_file(settings.GSPREAD_SERVICE_ACCOUNT_FILE, scopes=scopes)
    else:
        raise ValueError("Не задан способ аутентификации: требуется один из GSPREAD_SERVICE_ACCOUNT_FILE | _JSON | _JSON_B64")
    gc = gspread.authorize(creds)
    # Открываем таблицу по ID (если задан), иначе по имени
    if settings.GSHEETS_SPREADSHEET_ID:
        sh = gc.open_by_key(settings.GSHEETS_SPREADSHEET_ID)
    else:
        try:
            sh = gc.open(settings.GSHEETS_SPREADSHEET_NAME)
        except SpreadsheetNotFound:
            if not settings.GSHEETS_ALLOW_CREATE:
                raise RuntimeError("Таблица не найдена, а авто-создание запрещено (GSHEETS_ALLOW_CREATE=false)")
            sh = gc.create(settings.GSHEETS_SPREADSHEET_NAME)
            if settings.GSHEETS_SHARE_WITH:
                try:
                    sh.share(settings.GSHEETS_SHARE_WITH, perm_type='user', role='writer')
                except Exception:
                    pass

    now_iso = datetime.now(timezone.utc).isoformat()

    # Summary
    ws_summary = _ensure_worksheet(sh, SHEET_TITLES['summary'])
    _clear_and_update(ws_summary, _format_summary_rows(now_iso, db_size, agg))

    # UsersByRole
    ws_users = _ensure_worksheet(sh, SHEET_TITLES['users_by_role'])
    _clear_and_update(ws_users, _format_users_by_role_rows(agg))

    # RatingsByQuestion
    ws_ratings = _ensure_worksheet(sh, SHEET_TITLES['ratings_by_question'])
    _clear_and_update(ws_ratings, _format_ratings_by_question_rows(agg))

    # CaseStatistics
    ws_cases = _ensure_worksheet(sh, SHEET_TITLES['case_statistics'])
    _clear_and_update(ws_cases, _format_case_statistics_rows(agg))

    # TableStats
    ws_tables = _ensure_worksheet(sh, SHEET_TITLES['table_stats'])
    _clear_and_update(ws_tables, _format_table_stats_rows(table_stats))

    # User comments
    ws_comments = _ensure_worksheet(sh, SHEET_TITLES['user_comments'])
    _clear_and_update(ws_comments, _format_user_comments_rows(user_comments))

    print(f"✅ Экспорт в Google Sheets завершен: {now_iso}")


async def main() -> None:
    settings = ExportSettings()
    interval = max(30, int(settings.EXPORT_INTERVAL_SECONDS))
    print(
        f"Запуск экспортера: каждые {interval} секунд в '{settings.GSHEETS_SPREADSHEET_NAME}'"
    )

    # Первый запуск сразу
    while True:
        try:
            await _export_once(settings)
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
        await asyncio.sleep(interval)


if __name__ == '__main__':
    asyncio.run(main())


