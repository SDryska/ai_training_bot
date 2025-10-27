"""
Базовый абстрактный класс для всех AI провайдеров.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from app.storage.base import ConversationStorage


class ProviderType(Enum):
    """Типы AI провайдеров"""
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    YANDEX = "yandex"


class AIMessage:
    """Универсальная структура сообщения"""
    
    def __init__(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.role = role  # "system", "user", "assistant"
        self.content = content
        self.metadata = metadata or {}


class AIResponse:
    """Универсальная структура ответа от AI"""
    
    def __init__(
        self, 
        content: str, 
        success: bool = True, 
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.success = success
        self.error = error
        self.metadata = metadata or {}


class BaseAIProvider(ABC):
    """Базовый класс для всех AI провайдеров"""
    
    def __init__(self, api_key: str, model: str, storage: Optional["ConversationStorage"] = None):
        self.api_key = api_key
        self.model = model
        self.storage = storage
        # Для обратной совместимости: если storage не передан, используем память
        self.conversations: Dict[int, List[AIMessage]] = {}
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Тип провайдера"""
        pass
    
    @abstractmethod
    async def send_message(
        self, 
        user_id: int, 
        message: str, 
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> AIResponse:
        """
        Отправляет сообщение и возвращает ответ.
        
        Args:
            user_id: ID пользователя для ведения истории
            message: Сообщение пользователя
            system_prompt: Системный промпт (опционально)
            model_override: Модель, которой принудительно выполнить запрос (опционально)
            
        Returns:
            AIResponse с ответом провайдера
        """
        pass
    
    @abstractmethod
    async def send_messages(
        self, 
        user_id: int, 
        messages: List[AIMessage]
    ) -> AIResponse:
        """
        Отправляет список сообщений и возвращает ответ.
        
        Args:
            user_id: ID пользователя
            messages: Список сообщений
            
        Returns:
            AIResponse с ответом провайдера
        """
        pass
    
    async def clear_conversation(self, user_id: int) -> None:
        """Очищает историю разговора для пользователя"""
        if self.storage:
            await self.storage.clear_history(user_id, self.provider_type.value)
        else:
            # Fallback на память
            if user_id in self.conversations:
                del self.conversations[user_id]
    
    async def get_conversation_length(self, user_id: int) -> int:
        """Возвращает количество сообщений в разговоре"""
        if self.storage:
            return await self.storage.get_conversation_length(user_id, self.provider_type.value)
        else:
            return len(self.conversations.get(user_id, []))
    
    async def add_message_to_history(self, user_id: int, message: AIMessage) -> None:
        """Добавляет сообщение в историю"""
        if self.storage:
            await self.storage.save_message(user_id, self.provider_type.value, message)
        else:
            # Fallback на память
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            self.conversations[user_id].append(message)
    
    async def get_conversation_history(self, user_id: int) -> List[AIMessage]:
        """Получает историю разговора"""
        if self.storage:
            return await self.storage.get_history(user_id, self.provider_type.value)
        else:
            return self.conversations.get(user_id, [])
