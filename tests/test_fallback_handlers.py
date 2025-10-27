"""
Тесты для fallback хэндлеров.

Тестируемый модуль:
- app/handlers/fallback.py

Тестируемые хэндлеры:
- unknown_message - обработка неизвестных сообщений
- unknown_callback - обработка неизвестных callback'ов
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, CallbackQuery, User, Chat

from app.handlers.fallback import unknown_message, unknown_callback


def create_mock_message(user_id: int = 12345, chat_id: int = 12345, text: str = "Test message") -> Message:
    """Создает мок-объект Message для тестов"""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = user_id
    message.chat = MagicMock(spec=Chat)
    message.chat.id = chat_id
    message.text = text
    message.answer = AsyncMock()
    message.bot = MagicMock()
    return message


def create_mock_callback(
    user_id: int = 12345,
    chat_id: int = 12345,
    message_id: int = 100,
    data: str = "test"
) -> CallbackQuery:
    """Создает мок-объект CallbackQuery для тестов"""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=User)
    callback.from_user.id = user_id
    callback.data = data
    callback.message = MagicMock()
    callback.message.message_id = message_id
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    return callback


class TestUnknownMessage:
    """Тесты для unknown_message"""

    @pytest.mark.asyncio
    async def test_unknown_message_basic(self):
        """Тест: обработка неизвестного сообщения"""
        message = create_mock_message(text="Случайный текст")
        
        await unknown_message(message)
        
        message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_message_empty_text(self):
        """Тест: обработка сообщения с пустым текстом"""
        message = create_mock_message(text="")
        
        await unknown_message(message)
        
        message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_message_special_chars(self):
        """Тест: обработка сообщения со специальными символами"""
        message = create_mock_message(text="!@#$%^&*()")
        
        await unknown_message(message)
        
        message.answer.assert_called_once()


class TestUnknownCallback:
    """Тесты для unknown_callback"""

    @pytest.mark.asyncio
    async def test_unknown_callback_basic(self):
        """Тест: обработка неизвестного callback"""
        callback = create_mock_callback(data="unknown:callback:data")
        
        await unknown_callback(callback)
        
        callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_callback_empty_data(self):
        """Тест: обработка callback с пустыми данными"""
        callback = create_mock_callback(data="")
        
        await unknown_callback(callback)
        
        callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_callback_invalid_format(self):
        """Тест: обработка callback с некорректным форматом"""
        callback = create_mock_callback(data="random:data:here")
        
        await unknown_callback(callback)
        
        callback.answer.assert_called_once()

