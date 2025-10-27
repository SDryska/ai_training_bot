"""
In-memory хранилище истории диалогов (для обратной совместимости и тестов).
"""

import logging
from typing import Dict, List

from app.providers.base import AIMessage
from .base import ConversationStorage

logger = logging.getLogger(__name__)


class InMemoryStorage(ConversationStorage):
    """Хранилище в памяти (как было раньше)."""

    def __init__(self):
        # Ключ: (user_id, provider_type)
        self._conversations: Dict[tuple, List[AIMessage]] = {}

    async def save_message(
        self, user_id: int, provider_type: str, message: AIMessage
    ) -> None:
        """Сохраняет сообщение в память."""
        key = (user_id, provider_type)
        if key not in self._conversations:
            self._conversations[key] = []
        self._conversations[key].append(message)

    async def get_history(
        self, user_id: int, provider_type: str
    ) -> List[AIMessage]:
        """Возвращает историю из памяти."""
        key = (user_id, provider_type)
        return self._conversations.get(key, [])

    async def clear_history(self, user_id: int, provider_type: str) -> None:
        """Удаляет историю из памяти."""
        key = (user_id, provider_type)
        if key in self._conversations:
            del self._conversations[key]
            logger.debug(f"Очищена история в памяти для user={user_id}, provider={provider_type}")

    async def get_conversation_length(self, user_id: int, provider_type: str) -> int:
        """Возвращает количество сообщений в памяти."""
        key = (user_id, provider_type)
        return len(self._conversations.get(key, []))

