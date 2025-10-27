#!/usr/bin/env python3
"""
Проверка здоровья БД после миграций.
Скрипт проверяет:
1. Подключение к БД
2. Наличие всех обязательных таблиц
3. Версию миграций Alembic
4. Корректность структуры таблиц
5. Работоспособность основных операций

Использование:
    python standalone/check_db_health.py
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from dotenv import load_dotenv
from app.services.auth import normalize_db_url

load_dotenv()


class DatabaseHealthChecker:
    """Проверка здоровья базы данных."""
    
    # Обязательные таблицы для работы бота
    REQUIRED_TABLES = [
        'authorized_users',
        'bot_ratings',
        'case_stats',
        'rating_invites',
        'conversations',
        'fsm_storage',
        'alembic_version',
        'rating_comments',
    ]
    
    # Ожидаемая структура ключевых таблиц
    EXPECTED_COLUMNS = {
        'authorized_users': ['user_id', 'role', 'created_at'],
        'bot_ratings': ['user_id', 'question', 'rating', 'updated_at'],
        'case_stats': ['user_id', 'case_id', 'stat', 'cnt', 'updated_at'],
        'conversations': ['id', 'user_id', 'provider_type', 'role', 'content', 'created_at'],
        'fsm_storage': ['storage_key', 'user_id', 'chat_id', 'state', 'data', 'updated_at'],
        'alembic_version': ['version_num'],
    }
    
    def __init__(self):
        self.conn = None
        self.errors = []
        self.warnings = []
        self.success = []
    
    async def connect(self) -> bool:
        """Подключение к БД."""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            self.errors.append("❌ DATABASE_URL не задана в .env")
            return False
        
        try:
            url = normalize_db_url(database_url)
            print(f"🔗 Подключение к БД...")
            self.conn = await asyncpg.connect(url, timeout=10)
            self.success.append("✅ Подключение к БД установлено")
            return True
        except asyncpg.PostgresConnectionError as e:
            self.errors.append(f"❌ Не удалось подключиться к БД: {e}")
            return False
        except Exception as e:
            self.errors.append(f"❌ Ошибка подключения: {e}")
            return False
    
    async def check_tables_exist(self) -> bool:
        """Проверка наличия всех обязательных таблиц."""
        print(f"\n📋 Проверка наличия таблиц...")
        
        query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename
        """
        
        try:
            rows = await self.conn.fetch(query)
            existing_tables = [row['tablename'] for row in rows]
            
            missing_tables = []
            for table in self.REQUIRED_TABLES:
                if table in existing_tables:
                    self.success.append(f"  ✅ Таблица '{table}' существует")
                else:
                    missing_tables.append(table)
                    self.errors.append(f"  ❌ Таблица '{table}' НЕ НАЙДЕНА")
            
            if missing_tables:
                self.errors.append(f"❌ Отсутствуют таблицы: {', '.join(missing_tables)}")
                return False
            
            self.success.append(f"✅ Все {len(self.REQUIRED_TABLES)} обязательных таблиц найдены")
            return True
            
        except Exception as e:
            self.errors.append(f"❌ Ошибка при проверке таблиц: {e}")
            return False
    
    async def check_alembic_version(self) -> bool:
        """Проверка версии миграций Alembic."""
        print(f"\n🔍 Проверка версии миграций...")
        
        try:
            query = "SELECT version_num FROM alembic_version"
            rows = await self.conn.fetch(query)
            
            if not rows:
                self.errors.append("❌ Таблица alembic_version пуста - миграции не применены!")
                return False
            
            version = rows[0]['version_num']
            self.success.append(f"✅ Версия миграций: {version}")
            
            # Проверяем что это не самая первая миграция (должна быть актуальная)
            if len(version) < 12:
                self.warnings.append(f"⚠️  Подозрительная версия миграции: {version}")
            
            return True
            
        except Exception as e:
            self.errors.append(f"❌ Ошибка при проверке версии: {e}")
            return False
    
    async def check_table_structure(self) -> bool:
        """Проверка структуры ключевых таблиц."""
        print(f"\n🏗️  Проверка структуры таблиц...")
        
        all_ok = True
        
        for table_name, expected_columns in self.EXPECTED_COLUMNS.items():
            try:
                query = """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = $1
                ORDER BY ordinal_position
                """
                
                rows = await self.conn.fetch(query, table_name)
                existing_columns = [row['column_name'] for row in rows]
                
                missing_columns = [col for col in expected_columns if col not in existing_columns]
                
                if missing_columns:
                    self.errors.append(f"  ❌ Таблица '{table_name}': отсутствуют колонки {missing_columns}")
                    all_ok = False
                else:
                    self.success.append(f"  ✅ Таблица '{table_name}': структура корректна")
                    
            except Exception as e:
                self.errors.append(f"  ❌ Ошибка при проверке '{table_name}': {e}")
                all_ok = False
        
        if all_ok:
            self.success.append("✅ Структура всех таблиц корректна")
        
        return all_ok
    
    async def check_basic_operations(self) -> bool:
        """Проверка базовых операций с БД."""
        print(f"\n⚙️  Проверка базовых операций...")
        
        try:
            # Проверка чтения
            count = await self.conn.fetchval("SELECT COUNT(*) FROM authorized_users")
            self.success.append(f"  ✅ Чтение: найдено {count} пользователей")
            
            # Проверка записи (транзакция с откатом)
            async with self.conn.transaction():
                test_user_id = 999999999
                # Используем корректную роль 'user' (есть CHECK constraint на роль)
                await self.conn.execute(
                    "INSERT INTO authorized_users (user_id, role) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    test_user_id, 'user'
                )
                # Проверим что запись появилась
                exists = await self.conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM authorized_users WHERE user_id = $1)",
                    test_user_id
                )
                if exists:
                    self.success.append("  ✅ Запись: тестовая вставка успешна")
                else:
                    self.warnings.append("  ⚠️  Запись: тестовая вставка не выполнена (возможно уже существует)")
                
                # Откат транзакции (не сохраняем тестовые данные)
                raise Exception("Test rollback")
                
        except Exception as e:
            if "Test rollback" in str(e):
                self.success.append("  ✅ Транзакции: откат работает корректно")
            else:
                self.errors.append(f"  ❌ Ошибка при проверке операций: {e}")
                return False
        
        self.success.append("✅ Базовые операции работают корректно")
        return True
    
    async def check_indexes(self) -> bool:
        """Проверка наличия индексов."""
        print(f"\n📇 Проверка индексов...")
        
        try:
            query = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
            """
            
            rows = await self.conn.fetch(query)
            
            if not rows:
                self.warnings.append("⚠️  Индексы не найдены (может быть нормально для новой БД)")
                return True
            
            index_count = len(rows)
            self.success.append(f"✅ Найдено индексов: {index_count}")
            
            # Группируем по таблицам
            tables_with_indexes = {}
            for row in rows:
                table = row['tablename']
                if table not in tables_with_indexes:
                    tables_with_indexes[table] = []
                tables_with_indexes[table].append(row['indexname'])
            
            for table, indexes in tables_with_indexes.items():
                self.success.append(f"  ✅ {table}: {len(indexes)} индексов")
            
            return True
            
        except Exception as e:
            self.warnings.append(f"⚠️  Не удалось проверить индексы: {e}")
            return True  # Не критично
    
    async def disconnect(self):
        """Закрытие подключения."""
        if self.conn:
            await self.conn.close()
            print(f"\n🔌 Соединение закрыто")
    
    def print_report(self):
        """Вывод итогового отчёта."""
        print("\n" + "="*70)
        print("📊 ИТОГОВЫЙ ОТЧЁТ О ЗДОРОВЬЕ БД")
        print("="*70)
        
        if self.success:
            print(f"\n✅ УСПЕШНО ({len(self.success)}):")
            for msg in self.success:
                print(f"   {msg}")
        
        if self.warnings:
            print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЯ ({len(self.warnings)}):")
            for msg in self.warnings:
                print(f"   {msg}")
        
        if self.errors:
            print(f"\n❌ ОШИБКИ ({len(self.errors)}):")
            for msg in self.errors:
                print(f"   {msg}")
        
        print("\n" + "="*70)
        
        if self.errors:
            print("🔴 СТАТУС: БД НЕ ГОТОВА К РАБОТЕ")
            print("   Необходимо исправить ошибки выше")
            return False
        elif self.warnings:
            print("🟡 СТАТУС: БД РАБОТОСПОСОБНА С ПРЕДУПРЕЖДЕНИЯМИ")
            print("   Рекомендуется проверить предупреждения")
            return True
        else:
            print("🟢 СТАТУС: БД ПОЛНОСТЬЮ ИСПРАВНА")
            print("   Все проверки пройдены успешно!")
            return True
    
    async def run_all_checks(self) -> bool:
        """Запуск всех проверок."""
        try:
            if not await self.connect():
                return False
            
            checks = [
                self.check_tables_exist(),
                self.check_alembic_version(),
                self.check_table_structure(),
                self.check_basic_operations(),
                self.check_indexes(),
            ]
            
            # Выполняем все проверки
            for check in checks:
                await check
            
            return True
            
        except Exception as e:
            self.errors.append(f"❌ Критическая ошибка: {e}")
            return False
        finally:
            await self.disconnect()


async def main():
    """Главная функция."""
    print("🚀 ПРОВЕРКА ЗДОРОВЬЯ БД - EMCO Assessment Bot")
    print("="*70)
    
    checker = DatabaseHealthChecker()
    await checker.run_all_checks()
    is_healthy = checker.print_report()
    
    # Возвращаем код выхода
    sys.exit(0 if is_healthy else 1)


if __name__ == "__main__":
    asyncio.run(main())

