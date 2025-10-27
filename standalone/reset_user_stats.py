#!/usr/bin/env python3
"""
Служебный скрипт для сброса статистики пользователя.
Позволяет тестировать логику опроса для "новых" пользователей.

Использование:
    python reset_user_stats.py <user_id>
    python reset_user_stats.py --all  # Сброс для всех пользователей (ОСТОРОЖНО!)

Примеры:
    python reset_user_stats.py 123456789
    python reset_user_stats.py --all
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


async def reset_user_stats(user_id: Optional[int] = None, reset_all: bool = False) -> None:
    """Сброс статистики пользователя или всех пользователей."""
    settings = Settings()
    
    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL не настроен в .env файле")
        return
    
    url = normalize_db_url(settings.DATABASE_URL)
    
    try:
        conn = await asyncpg.connect(url, timeout=10)
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return
    
    try:
        if reset_all:
            print("🔄 Сброс статистики для ВСЕХ пользователей...")
            
            # Сброс счетчиков кейсов
            result1 = await conn.execute("DELETE FROM case_stats")
            print(f"   Удалено записей case_stats: {result1.split()[-1]}")
            
            # Сброс приглашений к опросу
            result2 = await conn.execute("DELETE FROM rating_invites") 
            print(f"   Удалено записей rating_invites: {result2.split()[-1]}")
            
            # Сброс оценок (опционально - раскомментируйте если нужно)
            # result3 = await conn.execute("DELETE FROM bot_ratings")
            # print(f"   Удалено записей bot_ratings: {result3.split()[-1]}")
            
            print("✅ Статистика всех пользователей сброшена!")
            
        elif user_id:
            print(f"🔄 Сброс статистики для пользователя {user_id}...")
            
            # Проверяем, есть ли данные пользователя
            stats_count = await conn.fetchval(
                "SELECT COUNT(*) FROM case_stats WHERE user_id = $1", user_id
            )
            invite_exists = await conn.fetchval(
                "SELECT COUNT(*) FROM rating_invites WHERE user_id = $1", user_id
            )
            ratings_count = await conn.fetchval(
                "SELECT COUNT(*) FROM bot_ratings WHERE user_id = $1", user_id
            )
            
            print(f"   Найдено записей case_stats: {stats_count}")
            print(f"   Найдено записей rating_invites: {invite_exists}")
            print(f"   Найдено записей bot_ratings: {ratings_count}")
            
            if stats_count == 0 and invite_exists == 0 and ratings_count == 0:
                print("   Пользователь уже выглядит как новый (нет данных)")
                return
            
            # Сброс счетчиков кейсов
            result1 = await conn.execute(
                "DELETE FROM case_stats WHERE user_id = $1", user_id
            )
            print(f"   Удалено записей case_stats: {result1.split()[-1]}")
            
            # Сброс приглашений к опросу
            result2 = await conn.execute(
                "DELETE FROM rating_invites WHERE user_id = $1", user_id
            )
            print(f"   Удалено записей rating_invites: {result2.split()[-1]}")
            
            # Сброс оценок (опционально - раскомментируйте если нужно)
            # result3 = await conn.execute(
            #     "DELETE FROM bot_ratings WHERE user_id = $1", user_id
            # )
            # print(f"   Удалено записей bot_ratings: {result3.split()[-1]}")
            
            print(f"✅ Статистика пользователя {user_id} сброшена!")
            print("   Теперь этот пользователь будет получать приглашение к опросу после первого завершенного кейса")
        
        else:
            print("❌ Не указан user_id или флаг --all")
            
    except Exception as e:
        print(f"❌ Ошибка выполнения запросов: {e}")
        
    finally:
        await conn.close()


async def show_user_stats(user_id: int) -> None:
    """Показать текущую статистику пользователя."""
    settings = Settings()
    
    if not settings.DATABASE_URL:
        print("❌ DATABASE_URL не настроен в .env файле")
        return
    
    url = normalize_db_url(settings.DATABASE_URL)
    
    try:
        conn = await asyncpg.connect(url, timeout=10)
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return
    
    try:
        print(f"📊 Статистика пользователя {user_id}:")
        
        # Статистика кейсов
        case_stats = await conn.fetch(
            """
            SELECT case_id, stat, cnt, updated_at 
            FROM case_stats 
            WHERE user_id = $1 
            ORDER BY case_id, stat
            """, 
            user_id
        )
        
        if case_stats:
            print("\n   Статистика кейсов:")
            for row in case_stats:
                print(f"     {row['case_id']}.{row['stat']}: {row['cnt']} (обновлено: {row['updated_at']})")
        else:
            print("   Статистика кейсов: отсутствует")
        
        # Приглашения к опросу
        invite = await conn.fetchrow(
            "SELECT sent_at FROM rating_invites WHERE user_id = $1", user_id
        )
        
        if invite:
            print(f"   Приглашение к опросу: отправлено {invite['sent_at']}")
        else:
            print("   Приглашение к опросу: не отправлялось")
        
        # Оценки
        ratings = await conn.fetch(
            "SELECT question, rating, updated_at FROM bot_ratings WHERE user_id = $1", user_id
        )
        
        if ratings:
            print("\n   Оценки бота:")
            for row in ratings:
                print(f"     {row['question']}: {row['rating']}/10 (обновлено: {row['updated_at']})")
        else:
            print("   Оценки бота: отсутствуют")
            
    except Exception as e:
        print(f"❌ Ошибка выполнения запросов: {e}")
        
    finally:
        await conn.close()


def print_usage():
    """Показать справку по использованию."""
    print("""
Служебный скрипт для сброса статистики пользователя

Использование:
    python reset_user_stats.py <user_id>           # Сброс для конкретного пользователя
    python reset_user_stats.py --all               # Сброс для ВСЕХ пользователей (ОСТОРОЖНО!)
    python reset_user_stats.py --show <user_id>    # Показать статистику пользователя
    python reset_user_stats.py --help              # Показать эту справку

Примеры:
    python reset_user_stats.py 123456789
    python reset_user_stats.py --show 123456789
    python reset_user_stats.py --all

Что сбрасывается:
    - Счетчики кейсов (started, completed, out_of_moves, auto_finished)
    - Приглашения к опросу (флаг отправки)
    - Оценки бота (закомментировано по умолчанию)

После сброса пользователь будет получать приглашение к опросу после первого завершенного кейса.
""")


async def main():
    if len(sys.argv) < 2:
        print_usage()
        return
    
    arg = sys.argv[1]
    
    if arg in ("--help", "-h"):
        print_usage()
        return
    
    if arg == "--all":
        response = input("⚠️  ВНИМАНИЕ! Это сбросит статистику ВСЕХ пользователей. Продолжить? (yes/no): ")
        if response.lower() == "yes":
            await reset_user_stats(reset_all=True)
        else:
            print("Операция отменена")
        return
    
    if arg == "--show":
        if len(sys.argv) < 3:
            print("❌ Не указан user_id для показа статистики")
            print("Использование: python reset_user_stats.py --show <user_id>")
            return
        
        try:
            user_id = int(sys.argv[2])
            await show_user_stats(user_id)
        except ValueError:
            print("❌ user_id должен быть числом")
        return
    
    # Обычный сброс для конкретного пользователя
    try:
        user_id = int(arg)
        await reset_user_stats(user_id=user_id)
    except ValueError:
        print("❌ user_id должен быть числом")
        print_usage()


if __name__ == "__main__":
    asyncio.run(main())
