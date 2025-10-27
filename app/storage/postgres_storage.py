"""
PostgreSQL хранилище истории диалогов.
"""

import asyncio
import json
import logging
from typing import List, Optional

from app.providers.base import AIMessage
from app.config.settings import Settings
from .base import ConversationStorage

logger = logging.getLogger(__name__)


def _normalize_db_url(database_url: Optional[str]) -> Optional[str]:
    """Конвертирует sqlalchemy-style URL в asyncpg URL."""
    if not database_url:
        return database_url
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


class PostgresStorage(ConversationStorage):
    """Хранилище истории диалогов в PostgreSQL."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Инициализирует Postgres хранилище.

        Args:
            database_url: URL подключения к БД (если None, берётся из Settings)
        """
        if database_url is None:
            settings = Settings()
            database_url = settings.DATABASE_URL

        self.database_url = _normalize_db_url(database_url)
        self._pool = None
        self._pool_lock = asyncio.Lock()

    async def _get_pool(self):
        """Получает или создаёт connection pool (thread-safe)."""
        if self._pool is not None:
            return self._pool
        
        async with self._pool_lock:
            # Double-check после получения lock
            if self._pool is not None:
                return self._pool
            
            if not self.database_url:
                logger.warning("DATABASE_URL не задан, PostgresStorage недоступен")
                return None
            
            try:
                import asyncpg
                # SSL параметры для удалённых подключений
                ssl_context = 'prefer' if not ('localhost' in self.database_url or '127.0.0.1' in self.database_url) else None
                self._pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=30,
                    ssl=ssl_context,
                    timeout=30
                )
                logger.info("Connection pool для conversation storage создан")
            except Exception as e:
                logger.error(f"Ошибка создания connection pool для conversation storage: {e}")
                return None
        
        return self._pool

    async def _connect(self):
        """Получает соединение из pool."""
        pool = await self._get_pool()
        if not pool:
            return None
        
        try:
            conn = await pool.acquire()
            return conn
        except Exception as e:
            logger.error(f"Ошибка получения соединения из pool для conversation storage: {e}")
            return None

    async def save_message(
        self, user_id: int, provider_type: str, message: AIMessage
    ) -> None:
        """
        Сохраняет сообщение в БД.

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера
            message: Сообщение для сохранения
        """
        pool = await self._get_pool()
        if not pool:
            return

        try:
            # Сериализуем metadata в JSON
            metadata_json = json.dumps(message.metadata) if message.metadata else None

            async with pool.acquire() as conn:
                await conn.execute(
                """
                INSERT INTO conversations (user_id, provider_type, role, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """,
                user_id,
                provider_type,
                message.role,
                message.content,
                metadata_json,
            )
            logger.debug(
                f"Saved message to DB: user={user_id}, provider={provider_type}, role={message.role}"
            )
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения в БД: {e}")

    async def get_history(
        self, user_id: int, provider_type: str
    ) -> List[AIMessage]:
        """
        Получает историю активной сессии из БД.

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера

        Returns:
            Список сообщений в хронологическом порядке
        """
        pool = await self._get_pool()
        if not pool:
            return []

        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch(
                    """
                    SELECT role, content, metadata
                    FROM conversations
                    WHERE user_id = $1 AND provider_type = $2 AND finished_at IS NULL
                    ORDER BY created_at ASC
                    """,
                    user_id,
                    provider_type,
                )

                messages = []
                for row in rows:
                    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                    messages.append(
                        AIMessage(
                            role=row["role"],
                            content=row["content"],
                            metadata=metadata,
                        )
                    )

                logger.debug(
                    f"Loaded {len(messages)} messages from DB: user={user_id}, provider={provider_type}"
                )
                return messages

            except Exception as e:
                logger.error(f"Ошибка загрузки истории из БД: {e}")
                return []

    async def clear_history(self, user_id: int, provider_type: str) -> None:
        """
        Помечает активную сессию как завершённую (finished_at = NOW()).

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера
        """
        conn = await self._connect()
        if not conn:
            return

        try:
            result = await conn.execute(
                """
                UPDATE conversations
                SET finished_at = NOW()
                WHERE user_id = $1 AND provider_type = $2 AND finished_at IS NULL
                """,
                user_id,
                provider_type,
            )
            logger.debug(
                f"Cleared history in DB: user={user_id}, provider={provider_type}, result={result}"
            )
        except Exception as e:
            logger.error(f"Ошибка очистки истории в БД: {e}")
        finally:
            await conn.close()

    async def get_conversation_length(self, user_id: int, provider_type: str) -> int:
        """
        Возвращает количество сообщений в активной сессии.

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера

        Returns:
            Количество сообщений
        """
        conn = await self._connect()
        if not conn:
            return 0

        try:
            count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM conversations
                WHERE user_id = $1 AND provider_type = $2 AND finished_at IS NULL
                """,
                user_id,
                provider_type,
            )
            return count or 0
        except Exception as e:
            logger.error(f"Ошибка подсчёта сообщений в БД: {e}")
            return 0
        finally:
            await conn.close()

