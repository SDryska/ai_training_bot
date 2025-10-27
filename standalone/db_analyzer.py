#!/usr/bin/env python3
"""
Скрипт для анализа базы данных EMCO Assessment Bot
Показывает размер БД, статистику таблиц и экспортирует все данные в человекочитаемом формате
"""

import asyncio
import asyncpg
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., description="postgresql+asyncpg://...")
    
    model_config = {
        'env_file': '.env',
        'case_sensitive': False,
        'extra': 'ignore'  # Игнорируем дополнительные поля из .env
    }


def normalize_db_url(database_url: str) -> str:
    """Нормализуем URL для asyncpg"""
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://")
    return database_url


def format_bytes(size_bytes: int) -> str:
    """Форматирует размер в байтах в человекочитаемый формат"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"


def format_datetime(dt) -> str:
    """Форматирует datetime в читаемый формат"""
    if dt is None:
        return "N/A"
    if hasattr(dt, 'strftime'):
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return str(dt)


class DatabaseAnalyzer:
    def __init__(self):
        self.settings = Settings()
        self.conn: Optional[asyncpg.Connection] = None
    
    async def connect(self):
        """Подключение к базе данных"""
        url = normalize_db_url(self.settings.DATABASE_URL)
        print(f"🔗 Подключение к базе данных...")
        self.conn = await asyncpg.connect(url, timeout=30)
        print("✅ Подключение установлено")
    
    async def disconnect(self):
        """Отключение от базы данных"""
        if self.conn:
            await self.conn.close()
            print("🔌 Соединение закрыто")
    
    async def get_database_size(self) -> Dict[str, Any]:
        """Получает информацию о размере базы данных"""
        print("\n📊 Анализ размера базы данных...")
        
        # Общий размер текущей БД
        db_size_query = """
        SELECT pg_size_pretty(pg_database_size(current_database())) as size,
               pg_database_size(current_database()) as size_bytes
        """
        
        db_size = await self.conn.fetchrow(db_size_query)
        
        # Размеры таблиц
        tables_size_query = """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
            pg_relation_size(schemaname||'.'||tablename) as table_size_bytes,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """
        
        tables_info = await self.conn.fetch(tables_size_query)
        
        return {
            'database_size': db_size['size'],
            'database_size_bytes': db_size['size_bytes'],
            'tables': [dict(row) for row in tables_info]
        }
    
    async def get_table_statistics(self) -> Dict[str, Any]:
        """Получает статистику по таблицам"""
        print("📈 Сбор статистики по таблицам...")
        
        stats = {}
        
        # Список наших основных таблиц
        tables = ['authorized_users', 'bot_ratings', 'case_stats', 'rating_invites']
        
        for table in tables:
            # Проверяем существование таблицы
            exists_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
            """
            
            exists = await self.conn.fetchval(exists_query, table)
            
            if not exists:
                stats[table] = {'exists': False}
                continue
            
            # Подсчет записей
            count_query = f"SELECT COUNT(*) FROM {table}"
            count = await self.conn.fetchval(count_query)
            
            # Информация о колонках
            columns_query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
            """
            
            columns = await self.conn.fetch(columns_query, table)
            
            stats[table] = {
                'exists': True,
                'row_count': count,
                'columns': [dict(col) for col in columns]
            }
        
        return stats
    
    async def export_all_data(self) -> Dict[str, Any]:
        """Экспортирует все данные из базы"""
        print("📤 Экспорт всех данных...")
        
        data = {}
        
        # authorized_users
        try:
            users_query = """
            SELECT user_id, role, created_at
            FROM authorized_users
            ORDER BY created_at DESC
            """
            users = await self.conn.fetch(users_query)
            data['authorized_users'] = [
                {
                    'user_id': row['user_id'],
                    'role': row['role'],
                    'created_at': format_datetime(row['created_at'])
                }
                for row in users
            ]
        except Exception as e:
            data['authorized_users'] = {'error': str(e)}
        
        # bot_ratings
        try:
            ratings_query = """
            SELECT user_id, question, rating, updated_at
            FROM bot_ratings
            ORDER BY updated_at DESC
            """
            ratings = await self.conn.fetch(ratings_query)
            data['bot_ratings'] = [
                {
                    'user_id': row['user_id'],
                    'question': row['question'],
                    'rating': row['rating'],
                    'updated_at': format_datetime(row['updated_at'])
                }
                for row in ratings
            ]
        except Exception as e:
            data['bot_ratings'] = {'error': str(e)}
        
        # case_stats
        try:
            stats_query = """
            SELECT user_id, case_id, stat, cnt, updated_at
            FROM case_stats
            ORDER BY updated_at DESC
            """
            stats = await self.conn.fetch(stats_query)
            data['case_stats'] = [
                {
                    'user_id': row['user_id'],
                    'case_id': row['case_id'],
                    'stat': row['stat'],
                    'count': row['cnt'],
                    'updated_at': format_datetime(row['updated_at'])
                }
                for row in stats
            ]
        except Exception as e:
            data['case_stats'] = {'error': str(e)}
        
        # rating_invites
        try:
            invites_query = """
            SELECT user_id, sent_at
            FROM rating_invites
            ORDER BY sent_at DESC
            """
            invites = await self.conn.fetch(invites_query)
            data['rating_invites'] = [
                {
                    'user_id': row['user_id'],
                    'sent_at': format_datetime(row['sent_at'])
                }
                for row in invites
            ]
        except Exception as e:
            data['rating_invites'] = {'error': str(e)}
        
        return data
    
    async def get_aggregated_statistics(self) -> Dict[str, Any]:
        """Получает агрегированную статистику"""
        print("🔢 Подсчет агрегированной статистики...")
        
        stats = {}
        
        try:
            # Статистика пользователей по ролям
            users_by_role_query = """
            SELECT role, COUNT(*) as count
            FROM authorized_users
            GROUP BY role
            ORDER BY count DESC
            """
            users_by_role = await self.conn.fetch(users_by_role_query)
            stats['users_by_role'] = {row['role']: row['count'] for row in users_by_role}
            
            # Статистика рейтингов
            ratings_stats_query = """
            SELECT 
                question,
                COUNT(*) as total_responses,
                AVG(rating::float) as avg_rating,
                MIN(rating) as min_rating,
                MAX(rating) as max_rating
            FROM bot_ratings
            GROUP BY question
            ORDER BY question
            """
            ratings_stats = await self.conn.fetch(ratings_stats_query)
            stats['ratings_by_question'] = [
                {
                    'question': row['question'],
                    'total_responses': row['total_responses'],
                    'average_rating': round(float(row['avg_rating']), 2) if row['avg_rating'] else 0,
                    'min_rating': row['min_rating'],
                    'max_rating': row['max_rating']
                }
                for row in ratings_stats
            ]
            
            # Статистика по кейсам
            case_stats_query = """
            SELECT 
                case_id,
                stat,
                COUNT(*) as user_count,
                SUM(cnt) as total_count
            FROM case_stats
            GROUP BY case_id, stat
            ORDER BY case_id, stat
            """
            case_stats = await self.conn.fetch(case_stats_query)
            stats['case_statistics'] = [
                {
                    'case_id': row['case_id'],
                    'stat_type': row['stat'],
                    'unique_users': row['user_count'],
                    'total_occurrences': row['total_count']
                }
                for row in case_stats
            ]
            
            # Активность пользователей
            user_activity_query = """
            SELECT 
                COUNT(DISTINCT user_id) as total_active_users,
                COUNT(DISTINCT CASE WHEN rating IS NOT NULL THEN user_id END) as users_with_ratings,
                COUNT(DISTINCT CASE WHEN cnt > 0 THEN user_id END) as users_with_case_activity
            FROM authorized_users au
            LEFT JOIN bot_ratings br ON au.user_id = br.user_id
            LEFT JOIN case_stats cs ON au.user_id = cs.user_id
            """
            activity = await self.conn.fetchrow(user_activity_query)
            stats['user_activity'] = dict(activity) if activity else {}
            
        except Exception as e:
            stats['error'] = str(e)
        
        return stats
    
    def print_size_report(self, size_info: Dict[str, Any]):
        """Выводит отчет о размере БД"""
        print("\n" + "="*60)
        print("📊 ОТЧЕТ О РАЗМЕРЕ БАЗЫ ДАННЫХ")
        print("="*60)
        
        print(f"\n🗄️  Общий размер базы данных: {size_info['database_size']}")
        print(f"    ({format_bytes(size_info['database_size_bytes'])})")
        
        print(f"\n📋 Размеры таблиц:")
        for table in size_info['tables']:
            print(f"  • {table['tablename']}: {table['size']}")
            print(f"    - Данные: {table['table_size']}")
            print(f"    - Индексы: {table['indexes_size']}")
    
    def print_statistics_report(self, stats: Dict[str, Any]):
        """Выводит статистический отчет"""
        print("\n" + "="*60)
        print("📈 СТАТИСТИКА ТАБЛИЦ")
        print("="*60)
        
        for table_name, table_stats in stats.items():
            print(f"\n📊 Таблица: {table_name}")
            
            if not table_stats.get('exists', True):
                print("  ❌ Таблица не существует")
                continue
            
            print(f"  📝 Количество записей: {table_stats['row_count']:,}")
            print(f"  🏗️  Структура:")
            
            for col in table_stats['columns']:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"    - {col['column_name']}: {col['data_type']} {nullable}{default}")
    
    def print_aggregated_report(self, agg_stats: Dict[str, Any]):
        """Выводит агрегированный отчет"""
        print("\n" + "="*60)
        print("🔢 АГРЕГИРОВАННАЯ СТАТИСТИКА")
        print("="*60)
        
        if 'users_by_role' in agg_stats:
            print(f"\n👥 Пользователи по ролям:")
            for role, count in agg_stats['users_by_role'].items():
                print(f"  • {role}: {count:,} пользователей")
        
        if 'ratings_by_question' in agg_stats:
            print(f"\n⭐ Статистика рейтингов:")
            for rating in agg_stats['ratings_by_question']:
                print(f"  • {rating['question']}:")
                print(f"    - Ответов: {rating['total_responses']:,}")
                print(f"    - Средний рейтинг: {rating['average_rating']}/10")
                print(f"    - Диапазон: {rating['min_rating']}-{rating['max_rating']}")
        
        if 'case_statistics' in agg_stats:
            print(f"\n📊 Статистика по кейсам:")
            current_case = None
            for case_stat in agg_stats['case_statistics']:
                if case_stat['case_id'] != current_case:
                    current_case = case_stat['case_id']
                    print(f"  • Кейс: {current_case}")
                
                print(f"    - {case_stat['stat_type']}: {case_stat['unique_users']} пользователей, {case_stat['total_occurrences']} раз")
        
        if 'user_activity' in agg_stats:
            activity = agg_stats['user_activity']
            print(f"\n🎯 Активность пользователей:")
            print(f"  • Всего активных пользователей: {activity.get('total_active_users', 0):,}")
            print(f"  • Пользователей с рейтингами: {activity.get('users_with_ratings', 0):,}")
            print(f"  • Пользователей с активностью по кейсам: {activity.get('users_with_case_activity', 0):,}")
    
    def save_data_to_files(self, data: Dict[str, Any], size_info: Dict[str, Any], 
                          stats: Dict[str, Any], agg_stats: Dict[str, Any]):
        """Сохраняет все данные в файлы"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Полный дамп данных в JSON
        full_data = {
            'export_timestamp': datetime.now().isoformat(),
            'database_size': size_info,
            'table_statistics': stats,
            'aggregated_statistics': agg_stats,
            'raw_data': data
        }
        
        json_filename = f"db_export_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, ensure_ascii=False, indent=2, default=str)
        
        # Человекочитаемый отчет
        report_filename = f"db_report_{timestamp}.txt"
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write("EMCO Assessment Bot - Анализ базы данных\n")
            f.write(f"Дата создания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            
            # Размер БД
            f.write(f"РАЗМЕР БАЗЫ ДАННЫХ\n")
            f.write(f"Общий размер: {size_info['database_size']}\n\n")
            
            f.write("Размеры таблиц:\n")
            for table in size_info['tables']:
                f.write(f"  {table['tablename']}: {table['size']}\n")
            f.write("\n")
            
            # Статистика
            f.write("СТАТИСТИКА ТАБЛИЦ\n")
            for table_name, table_stats in stats.items():
                if table_stats.get('exists', True):
                    f.write(f"{table_name}: {table_stats['row_count']:,} записей\n")
            f.write("\n")
            
            # Данные
            f.write("СОДЕРЖИМОЕ ТАБЛИЦ\n")
            f.write("-" * 40 + "\n\n")
            
            for table_name, table_data in data.items():
                f.write(f"{table_name.upper()}:\n")
                if isinstance(table_data, list):
                    for i, record in enumerate(table_data, 1):
                        f.write(f"  Запись {i}:\n")
                        for key, value in record.items():
                            f.write(f"    {key}: {value}\n")
                        f.write("\n")
                else:
                    f.write(f"  Ошибка: {table_data}\n")
                f.write("-" * 40 + "\n")
        
        print(f"\n💾 Данные сохранены:")
        print(f"  📄 JSON дамп: {json_filename}")
        print(f"  📄 Текстовый отчет: {report_filename}")
    
    async def run_full_analysis(self):
        """Запускает полный анализ базы данных"""
        try:
            await self.connect()
            
            # Получаем всю информацию
            size_info = await self.get_database_size()
            stats = await self.get_table_statistics()
            agg_stats = await self.get_aggregated_statistics()
            data = await self.export_all_data()
            
            # Выводим отчеты
            self.print_size_report(size_info)
            self.print_statistics_report(stats)
            self.print_aggregated_report(agg_stats)
            
            # Сохраняем в файлы
            self.save_data_to_files(data, size_info, stats, agg_stats)
            
            print(f"\n✅ Анализ завершен успешно!")
            
        except Exception as e:
            print(f"\n❌ Ошибка при анализе: {e}")
            raise
        finally:
            await self.disconnect()


async def main():
    """Главная функция"""
    print("🚀 EMCO Assessment Bot - Анализатор базы данных")
    print("="*60)
    
    # Проверяем наличие переменных окружения
    if not os.getenv('DATABASE_URL'):
        print("❌ Ошибка: не найдена переменная окружения DATABASE_URL")
        print("Убедитесь, что файл .env существует и содержит DATABASE_URL")
        return
    
    analyzer = DatabaseAnalyzer()
    await analyzer.run_full_analysis()


if __name__ == "__main__":
    asyncio.run(main())
