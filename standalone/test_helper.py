#!/usr/bin/env python3
"""
Интерактивный помощник для тестирования бота.
Позволяет легко управлять статистикой пользователей для тестирования.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from app.config.settings import Settings
from app.services.auth import normalize_db_url


class TestHelper:
    def __init__(self):
        self.settings = Settings()
        self.conn: Optional[asyncpg.Connection] = None
    
    async def connect(self) -> bool:
        """Подключение к базе данных."""
        if not self.settings.DATABASE_URL:
            print("❌ DATABASE_URL не настроен в .env файле")
            return False
        
        url = normalize_db_url(self.settings.DATABASE_URL)
        
        try:
            self.conn = await asyncpg.connect(url, timeout=10)
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от базы данных."""
        if self.conn:
            await self.conn.close()
    
    async def find_users(self) -> list:
        """Найти всех пользователей с какой-либо активностью."""
        if not self.conn:
            return []
        
        users = await self.conn.fetch("""
            SELECT DISTINCT user_id, 
                   (SELECT role FROM authorized_users WHERE user_id = u.user_id) as role,
                   (SELECT COUNT(*) FROM case_stats WHERE user_id = u.user_id AND stat = 'completed') as completed_cases,
                   (SELECT sent_at FROM rating_invites WHERE user_id = u.user_id) as invite_sent,
                   (SELECT COUNT(*) FROM bot_ratings WHERE user_id = u.user_id) as ratings_given
            FROM (
                SELECT user_id FROM case_stats
                UNION 
                SELECT user_id FROM rating_invites
                UNION 
                SELECT user_id FROM bot_ratings
                UNION
                SELECT user_id FROM authorized_users
            ) u
            ORDER BY user_id
        """)
        
        return users
    
    async def show_user_details(self, user_id: int):
        """Показать подробную информацию о пользователе."""
        if not self.conn:
            return
        
        print(f"\n📊 Подробная статистика пользователя {user_id}:")
        
        # Роль пользователя
        role = await self.conn.fetchval(
            "SELECT role FROM authorized_users WHERE user_id = $1", user_id
        )
        print(f"   Роль: {role or 'не авторизован'}")
        
        # Статистика кейсов
        case_stats = await self.conn.fetch("""
            SELECT case_id, stat, cnt, updated_at 
            FROM case_stats 
            WHERE user_id = $1 
            ORDER BY case_id, stat
        """, user_id)
        
        if case_stats:
            print("\n   📈 Статистика кейсов:")
            current_case = None
            for row in case_stats:
                if current_case != row['case_id']:
                    current_case = row['case_id']
                    print(f"     🎯 {current_case}:")
                print(f"       {row['stat']}: {row['cnt']} (обновлено: {row['updated_at'].strftime('%Y-%m-%d %H:%M')})")
        else:
            print("   📈 Статистика кейсов: отсутствует")
        
        # Приглашения к опросу
        invite = await self.conn.fetchrow(
            "SELECT sent_at FROM rating_invites WHERE user_id = $1", user_id
        )
        
        if invite:
            print(f"\n   📧 Приглашение к опросу: отправлено {invite['sent_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\n   📧 Приглашение к опросу: не отправлялось")
        
        # Оценки
        ratings = await self.conn.fetch(
            "SELECT question, rating, updated_at FROM bot_ratings WHERE user_id = $1 ORDER BY updated_at", user_id
        )
        
        if ratings:
            print("\n   ⭐ Оценки бота:")
            for row in ratings:
                print(f"     {row['question']}: {row['rating']}/10 (дата: {row['updated_at'].strftime('%Y-%m-%d %H:%M')})")
        else:
            print("\n   ⭐ Оценки бота: отсутствуют")
    
    async def reset_user(self, user_id: int, include_ratings: bool = False):
        """Сброс статистики пользователя."""
        if not self.conn:
            return
        
        print(f"🔄 Сброс статистики для пользователя {user_id}...")
        
        # Сброс счетчиков кейсов
        result1 = await self.conn.execute(
            "DELETE FROM case_stats WHERE user_id = $1", user_id
        )
        deleted_stats = int(result1.split()[-1])
        
        # Сброс приглашений к опросу
        result2 = await self.conn.execute(
            "DELETE FROM rating_invites WHERE user_id = $1", user_id
        )
        deleted_invites = int(result2.split()[-1])
        
        deleted_ratings = 0
        if include_ratings:
            # Сброс оценок
            result3 = await self.conn.execute(
                "DELETE FROM bot_ratings WHERE user_id = $1", user_id
            )
            deleted_ratings = int(result3.split()[-1])
        
        print(f"   ✅ Удалено записей case_stats: {deleted_stats}")
        print(f"   ✅ Удалено записей rating_invites: {deleted_invites}")
        if include_ratings:
            print(f"   ✅ Удалено записей bot_ratings: {deleted_ratings}")
        
        print(f"✅ Пользователь {user_id} теперь выглядит как новый!")
    
    async def show_menu(self):
        """Показать главное меню."""
        while True:
            print("\n" + "="*50)
            print("🤖 ТЕСТОВЫЙ ПОМОЩНИК ДЛЯ БОТА EMCO")
            print("="*50)
            print("1. Показать всех пользователей")
            print("2. Подробная информация о пользователе")
            print("3. Сбросить статистику пользователя")
            print("4. Сбросить статистику пользователя (включая оценки)")
            print("5. Найти пользователей, готовых к опросу")
            print("0. Выход")
            print("="*50)
            
            choice = input("Выберите действие (0-5): ").strip()
            
            if choice == "0":
                print("👋 До свидания!")
                break
            elif choice == "1":
                await self.show_all_users()
            elif choice == "2":
                await self.show_user_info()
            elif choice == "3":
                await self.reset_user_stats(include_ratings=False)
            elif choice == "4":
                await self.reset_user_stats(include_ratings=True)
            elif choice == "5":
                await self.show_survey_ready_users()
            else:
                print("❌ Неверный выбор. Попробуйте еще раз.")
    
    async def show_all_users(self):
        """Показать всех пользователей."""
        users = await self.find_users()
        
        if not users:
            print("\n📭 Пользователи не найдены")
            return
        
        print(f"\n👥 Найдено пользователей: {len(users)}")
        print("-" * 80)
        print(f"{'ID':>12} | {'Роль':>8} | {'Завершено':>10} | {'Опрос':>15} | {'Оценок':>7}")
        print("-" * 80)
        
        for user in users:
            user_id = user['user_id']
            role = user['role'] or 'нет'
            completed = user['completed_cases']
            invite_status = "отправлен" if user['invite_sent'] else "нет"
            ratings = user['ratings_given']
            
            print(f"{user_id:>12} | {role:>8} | {completed:>10} | {invite_status:>15} | {ratings:>7}")
    
    async def show_user_info(self):
        """Показать информацию о конкретном пользователе."""
        try:
            user_id = int(input("\nВведите ID пользователя: ").strip())
            await self.show_user_details(user_id)
        except ValueError:
            print("❌ ID пользователя должен быть числом")
    
    async def reset_user_stats(self, include_ratings: bool):
        """Сбросить статистику пользователя."""
        try:
            user_id = int(input("\nВведите ID пользователя для сброса: ").strip())
            
            # Показываем текущую статистику
            await self.show_user_details(user_id)
            
            confirm = input(f"\n⚠️  Сбросить статистику пользователя {user_id}? (yes/no): ").strip().lower()
            if confirm == "yes":
                await self.reset_user(user_id, include_ratings)
            else:
                print("Операция отменена")
                
        except ValueError:
            print("❌ ID пользователя должен быть числом")
    
    async def show_survey_ready_users(self):
        """Показать пользователей, которые готовы получить опрос."""
        if not self.conn:
            return
        
        # Пользователи с завершенными кейсами, но без отправленного опроса
        users = await self.conn.fetch("""
            SELECT cs.user_id, 
                   COUNT(DISTINCT cs.case_id) as completed_cases,
                   ri.sent_at as invite_sent
            FROM case_stats cs
            LEFT JOIN rating_invites ri ON cs.user_id = ri.user_id
            WHERE cs.stat = 'completed' AND cs.cnt > 0
            GROUP BY cs.user_id, ri.sent_at
            ORDER BY completed_cases DESC, cs.user_id
        """)
        
        ready_users = [u for u in users if not u['invite_sent']]
        already_invited = [u for u in users if u['invite_sent']]
        
        print(f"\n🎯 Пользователи, готовые к опросу: {len(ready_users)}")
        if ready_users:
            print("-" * 40)
            print(f"{'ID':>12} | {'Завершено кейсов':>15}")
            print("-" * 40)
            for user in ready_users:
                print(f"{user['user_id']:>12} | {user['completed_cases']:>15}")
        
        print(f"\n📧 Пользователи, уже получившие опрос: {len(already_invited)}")
        if already_invited:
            print("-" * 60)
            print(f"{'ID':>12} | {'Завершено кейсов':>15} | {'Опрос отправлен':>20}")
            print("-" * 60)
            for user in already_invited:
                invite_date = user['invite_sent'].strftime('%Y-%m-%d %H:%M')
                print(f"{user['user_id']:>12} | {user['completed_cases']:>15} | {invite_date:>20}")


async def main():
    helper = TestHelper()
    
    if not await helper.connect():
        return
    
    try:
        await helper.show_menu()
    finally:
        await helper.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
