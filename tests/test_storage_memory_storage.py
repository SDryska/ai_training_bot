"""
Тесты для in-memory хранилища истории диалогов.

Тестируемый модуль:
- app/storage/memory_storage.py

Тестируемые компоненты:
- InMemoryStorage класс
- Методы: __init__, save_message, get_history, clear_history, get_conversation_length
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.storage.memory_storage import InMemoryStorage
from app.providers.base import AIMessage


class TestInMemoryStorageInit:
    """Тесты для __init__ метода"""

    def test_init(self):
        """Тест: инициализация хранилища"""
        storage = InMemoryStorage()
        
        assert storage._conversations == {}


class TestInMemoryStorageSaveMessage:
    """Тесты для метода save_message"""

    @pytest.mark.asyncio
    async def test_save_message_first_message(self):
        """Тест: сохранение первого сообщения"""
        storage = InMemoryStorage()
        message = AIMessage("user", "Hello")
        
        await storage.save_message(12345, "openai", message)
        
        assert (12345, "openai") in storage._conversations
        assert len(storage._conversations[(12345, "openai")]) == 1
        assert storage._conversations[(12345, "openai")][0] == message

    @pytest.mark.asyncio
    async def test_save_message_multiple_messages(self):
        """Тест: сохранение нескольких сообщений"""
        storage = InMemoryStorage()
        message1 = AIMessage("user", "Hello")
        message2 = AIMessage("assistant", "Hi there")
        
        await storage.save_message(12345, "openai", message1)
        await storage.save_message(12345, "openai", message2)
        
        assert len(storage._conversations[(12345, "openai")]) == 2
        assert storage._conversations[(12345, "openai")][0] == message1
        assert storage._conversations[(12345, "openai")][1] == message2

    @pytest.mark.asyncio
    async def test_save_message_different_providers(self):
        """Тест: сохранение сообщений для разных провайдеров"""
        storage = InMemoryStorage()
        message1 = AIMessage("user", "Hello")
        message2 = AIMessage("user", "Hi")
        
        await storage.save_message(12345, "openai", message1)
        await storage.save_message(12345, "gemini", message2)
        
        assert len(storage._conversations[(12345, "openai")]) == 1
        assert len(storage._conversations[(12345, "gemini")]) == 1

    @pytest.mark.asyncio
    async def test_save_message_different_users(self):
        """Тест: сохранение сообщений для разных пользователей"""
        storage = InMemoryStorage()
        message1 = AIMessage("user", "Hello")
        message2 = AIMessage("user", "Hi")
        
        await storage.save_message(12345, "openai", message1)
        await storage.save_message(67890, "openai", message2)
        
        assert len(storage._conversations[(12345, "openai")]) == 1
        assert len(storage._conversations[(67890, "openai")]) == 1

    @pytest.mark.asyncio
    async def test_save_message_with_metadata(self):
        """Тест: сохранение сообщения с metadata"""
        storage = InMemoryStorage()
        message = AIMessage("user", "Hello", {"key": "value"})
        
        await storage.save_message(12345, "openai", message)
        
        saved_message = storage._conversations[(12345, "openai")][0]
        assert saved_message.metadata == {"key": "value"}


class TestInMemoryStorageGetHistory:
    """Тесты для метода get_history"""

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        """Тест: получение пустой истории"""
        storage = InMemoryStorage()
        
        history = await storage.get_history(12345, "openai")
        
        assert history == []

    @pytest.mark.asyncio
    async def test_get_history_returns_messages(self):
        """Тест: получение истории с сообщениями"""
        storage = InMemoryStorage()
        message1 = AIMessage("user", "Hello")
        message2 = AIMessage("assistant", "Hi")
        
        await storage.save_message(12345, "openai", message1)
        await storage.save_message(12345, "openai", message2)
        
        history = await storage.get_history(12345, "openai")
        
        assert len(history) == 2
        assert history[0] == message1
        assert history[1] == message2

    @pytest.mark.asyncio
    async def test_get_history_different_provider(self):
        """Тест: получение истории для другого провайдера"""
        storage = InMemoryStorage()
        message = AIMessage("user", "Hello")
        
        await storage.save_message(12345, "openai", message)
        
        history = await storage.get_history(12345, "gemini")
        
        assert history == []

    @pytest.mark.asyncio
    async def test_get_history_nonexistent_user(self):
        """Тест: получение истории для несуществующего пользователя"""
        storage = InMemoryStorage()
        
        history = await storage.get_history(99999, "openai")
        
        assert history == []


class TestInMemoryStorageClearHistory:
    """Тесты для метода clear_history"""

    @pytest.mark.asyncio
    async def test_clear_history_exists(self):
        """Тест: очистка существующей истории"""
        storage = InMemoryStorage()
        message = AIMessage("user", "Hello")
        
        await storage.save_message(12345, "openai", message)
        await storage.clear_history(12345, "openai")
        
        assert (12345, "openai") not in storage._conversations

    @pytest.mark.asyncio
    async def test_clear_history_not_exists(self):
        """Тест: очистка несуществующей истории"""
        storage = InMemoryStorage()
        
        # Не должно быть исключения
        await storage.clear_history(12345, "openai")
        
        assert (12345, "openai") not in storage._conversations

    @pytest.mark.asyncio
    async def test_clear_history_one_provider(self):
        """Тест: очистка истории для одного провайдера"""
        storage = InMemoryStorage()
        message1 = AIMessage("user", "Hello")
        message2 = AIMessage("user", "Hi")
        
        await storage.save_message(12345, "openai", message1)
        await storage.save_message(12345, "gemini", message2)
        
        await storage.clear_history(12345, "openai")
        
        assert (12345, "openai") not in storage._conversations
        assert (12345, "gemini") in storage._conversations


class TestInMemoryStorageGetConversationLength:
    """Тесты для метода get_conversation_length"""

    @pytest.mark.asyncio
    async def test_get_conversation_length_empty(self):
        """Тест: получение длины пустой истории"""
        storage = InMemoryStorage()
        
        length = await storage.get_conversation_length(12345, "openai")
        
        assert length == 0

    @pytest.mark.asyncio
    async def test_get_conversation_length_one_message(self):
        """Тест: получение длины истории с одним сообщением"""
        storage = InMemoryStorage()
        message = AIMessage("user", "Hello")
        
        await storage.save_message(12345, "openai", message)
        
        length = await storage.get_conversation_length(12345, "openai")
        
        assert length == 1

    @pytest.mark.asyncio
    async def test_get_conversation_length_multiple_messages(self):
        """Тест: получение длины истории с несколькими сообщениями"""
        storage = InMemoryStorage()
        
        for i in range(5):
            message = AIMessage("user", f"Message {i}")
            await storage.save_message(12345, "openai", message)
        
        length = await storage.get_conversation_length(12345, "openai")
        
        assert length == 5

    @pytest.mark.asyncio
    async def test_get_conversation_length_different_provider(self):
        """Тест: получение длины для другого провайдера"""
        storage = InMemoryStorage()
        message = AIMessage("user", "Hello")
        
        await storage.save_message(12345, "openai", message)
        
        length = await storage.get_conversation_length(12345, "gemini")
        
        assert length == 0


class TestInMemoryStorageIntegration:
    """Интеграционные тесты для InMemoryStorage"""

    @pytest.mark.asyncio
    async def test_save_get_clear_flow(self):
        """Тест: полный цикл сохранения, получения и очистки"""
        storage = InMemoryStorage()
        message1 = AIMessage("user", "Hello")
        message2 = AIMessage("assistant", "Hi")
        
        # Сохраняем сообщения
        await storage.save_message(12345, "openai", message1)
        await storage.save_message(12345, "openai", message2)
        
        # Проверяем историю
        history = await storage.get_history(12345, "openai")
        assert len(history) == 2
        
        # Проверяем длину
        length = await storage.get_conversation_length(12345, "openai")
        assert length == 2
        
        # Очищаем историю
        await storage.clear_history(12345, "openai")
        
        # Проверяем, что история пуста
        history = await storage.get_history(12345, "openai")
        assert history == []
        
        length = await storage.get_conversation_length(12345, "openai")
        assert length == 0

    @pytest.mark.asyncio
    async def test_multiple_users_and_providers(self):
        """Тест: работа с несколькими пользователями и провайдерами"""
        storage = InMemoryStorage()
        
        # Пользователь 1, OpenAI
        await storage.save_message(1, "openai", AIMessage("user", "Hello 1"))
        
        # Пользователь 1, Gemini
        await storage.save_message(1, "gemini", AIMessage("user", "Hello 2"))
        
        # Пользователь 2, OpenAI
        await storage.save_message(2, "openai", AIMessage("user", "Hello 3"))
        
        # Проверяем изоляцию
        assert len(await storage.get_history(1, "openai")) == 1
        assert len(await storage.get_history(1, "gemini")) == 1
        assert len(await storage.get_history(2, "openai")) == 1
        
        # Очищаем только одного пользователя
        await storage.clear_history(1, "openai")
        
        assert len(await storage.get_history(1, "openai")) == 0
        assert len(await storage.get_history(1, "gemini")) == 1
        assert len(await storage.get_history(2, "openai")) == 1

