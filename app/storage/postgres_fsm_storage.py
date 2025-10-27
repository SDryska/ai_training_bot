"""
PostgreSQL-based FSM storage для aiogram.

Сохраняет состояния FSM и данные пользователей в БД,
что позволяет восстанавливать сессии после перезапуска бота.
"""

import json
import logging
from typing import Any, Dict, Optional

from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from app.config.settings import Settings

logger = logging.getLogger(__name__)


def _normalize_db_url(database_url: Optional[str]) -> Optional[str]:
    """Конвертирует sqlalchemy-style URL в asyncpg URL."""
    if not database_url:
        return database_url
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


class PostgresFSMStorage(BaseStorage):
    """
    PostgreSQL хранилище для FSM состояний aiogram.
    
    Сохраняет:
    - Состояния FSM (state)
    - Данные пользователей (data)
    
    Это позволяет восстанавливать активные диалоги после перезапуска бота.
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Инициализирует Postgres FSM хранилище.

        Args:
            database_url: URL подключения к БД (если None, берётся из Settings)
        """
        if database_url is None:
            settings = Settings()
            database_url = settings.DATABASE_URL

        self.database_url = _normalize_db_url(database_url)

    async def _connect(self):
        """Создаёт подключение к БД."""
        if not self.database_url:
            logger.warning("DATABASE_URL не задан, PostgresFSMStorage недоступен")
            return None

        try:
            import asyncpg
            # SSL параметры для удалённых подключений
            ssl_context = 'prefer' if not ('localhost' in self.database_url or '127.0.0.1' in self.database_url) else None
            conn = await asyncpg.connect(
                self.database_url, 
                timeout=30,
                ssl=ssl_context,
                command_timeout=30
            )
            return conn
        except Exception as e:
            logger.error(f"Ошибка подключения к БД для FSM storage: {e}")
            return None

    def _make_key(self, key: StorageKey) -> str:
        """
        Создаёт уникальный ключ для записи в БД.
        
        Args:
            key: StorageKey от aiogram
            
        Returns:
            Строковый ключ вида "bot_id:chat_id:user_id"
        """
        parts = []
        if key.bot_id:
            parts.append(str(key.bot_id))
        if key.chat_id:
            parts.append(str(key.chat_id))
        if key.user_id:
            parts.append(str(key.user_id))
        return ":".join(parts)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        """
        Сохраняет состояние FSM в БД.
        
        Args:
            key: Ключ хранилища
            state: Состояние FSM (строка или None для очистки)
        """
        conn = await self._connect()
        if not conn:
            return

        try:
            storage_key = self._make_key(key)
            state_str = state.state if state else None

            await conn.execute(
                """
                INSERT INTO fsm_storage (storage_key, bot_id, chat_id, user_id, state, data, updated_at)
                VALUES ($1, $2, $3, $4, $5, '{}', NOW())
                ON CONFLICT (storage_key) 
                DO UPDATE SET state = $5, updated_at = NOW()
                """,
                storage_key,
                key.bot_id,
                key.chat_id,
                key.user_id,
                state_str,
            )
            logger.debug(f"Saved FSM state: key={storage_key}, state={state_str}")
        except Exception as e:
            logger.error(f"Ошибка сохранения FSM state в БД: {e}")
        finally:
            await conn.close()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        """
        Получает состояние FSM из БД.
        
        Args:
            key: Ключ хранилища
            
        Returns:
            Строка состояния или None
        """
        conn = await self._connect()
        if not conn:
            return None

        try:
            storage_key = self._make_key(key)
            row = await conn.fetchrow(
                """
                SELECT state FROM fsm_storage
                WHERE storage_key = $1
                """,
                storage_key,
            )

            if row:
                state = row["state"]
                logger.debug(f"Loaded FSM state: key={storage_key}, state={state}")
                return state
            return None

        except Exception as e:
            logger.error(f"Ошибка загрузки FSM state из БД: {e}")
            return None
        finally:
            await conn.close()

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        """
        Сохраняет данные FSM в БД.
        
        Args:
            key: Ключ хранилища
            data: Словарь с данными
        """
        conn = await self._connect()
        if not conn:
            return

        try:
            storage_key = self._make_key(key)
            
            # Конвертируем set в list для JSON сериализации
            serializable_data = {}
            for k, v in data.items():
                if isinstance(v, set):
                    serializable_data[k] = list(v)
                else:
                    serializable_data[k] = v
            
            data_json = json.dumps(serializable_data)

            await conn.execute(
                """
                INSERT INTO fsm_storage (storage_key, bot_id, chat_id, user_id, state, data, updated_at)
                VALUES ($1, $2, $3, $4, NULL, $5, NOW())
                ON CONFLICT (storage_key) 
                DO UPDATE SET data = $5, updated_at = NOW()
                """,
                storage_key,
                key.bot_id,
                key.chat_id,
                key.user_id,
                data_json,
            )
            logger.debug(f"Saved FSM data: key={storage_key}, data_size={len(data)}")
        except Exception as e:
            logger.error(f"Ошибка сохранения FSM data в БД: {e}")
        finally:
            await conn.close()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        """
        Получает данные FSM из БД.
        
        Args:
            key: Ключ хранилища
            
        Returns:
            Словарь с данными
        """
        conn = await self._connect()
        if not conn:
            return {}

        try:
            storage_key = self._make_key(key)
            row = await conn.fetchrow(
                """
                SELECT data FROM fsm_storage
                WHERE storage_key = $1
                """,
                storage_key,
            )

            if row and row["data"]:
                data = json.loads(row["data"])
                
                # Восстанавливаем set из list (для total_provd_achieved и т.д.)
                if "total_provd_achieved" in data and isinstance(data["total_provd_achieved"], list):
                    data["total_provd_achieved"] = set(data["total_provd_achieved"])
                
                logger.debug(f"Loaded FSM data: key={storage_key}, data_size={len(data)}")
                return data
            return {}

        except Exception as e:
            logger.error(f"Ошибка загрузки FSM data из БД: {e}")
            return {}
        finally:
            await conn.close()

    async def close(self) -> None:
        """Закрывает соединение с БД (если нужно)."""
        # В текущей реализации каждый запрос открывает/закрывает соединение
        # Можно оптимизировать с connection pool, но для начала достаточно
        pass

