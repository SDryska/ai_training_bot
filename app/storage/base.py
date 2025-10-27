"""
Абстрактный интерфейс для хранения истории диалогов.
"""

from abc import ABC, abstractmethod
from typing import List

from app.providers.base import AIMessage


class ConversationStorage(ABC):
    """Абстрактное хранилище истории диалогов."""

    @abstractmethod
    async def save_message(
        self, user_id: int, provider_type: str, message: AIMessage
    ) -> None:
        """
        Сохраняет одно сообщение в историю.

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера (openai, gemini и т.д.)
            message: Сообщение для сохранения
        """
        pass

    @abstractmethod
    async def get_history(
        self, user_id: int, provider_type: str
    ) -> List[AIMessage]:
        """
        Получает историю диалога пользователя с провайдером.

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера

        Returns:
            Список сообщений в порядке от старых к новым
        """
        pass

    @abstractmethod
    async def clear_history(self, user_id: int, provider_type: str) -> None:
        """
        Очищает историю диалога (помечает сессию завершённой).

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера
        """
        pass

    @abstractmethod
    async def get_conversation_length(self, user_id: int, provider_type: str) -> int:
        """
        Возвращает количество сообщений в активной сессии.

        Args:
            user_id: ID пользователя
            provider_type: Тип провайдера

        Returns:
            Количество сообщений
        """
        pass

