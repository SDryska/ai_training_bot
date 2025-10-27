"""
Тесты для middleware ролей.

Тестируемый модуль:
- app/middlewares/roles.py

Тестируемые компоненты:
- RolesMiddleware класс
- Метод __call__
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, CallbackQuery, User, Chat

from app.middlewares.roles import RolesMiddleware


def create_mock_message(user_id: int = 12345, chat_id: int = 12345, text: str = "Test message") -> Message:
    """Создает мок-объект Message для тестов"""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = user_id
    message.chat = MagicMock(spec=Chat)
    message.chat.id = chat_id
    message.text = text
    return message


def create_mock_callback(user_id: int = 12345, data: str = "test") -> CallbackQuery:
    """Создает мок-объект CallbackQuery для тестов"""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=User)
    callback.from_user.id = user_id
    callback.data = data
    return callback


class TestRolesMiddleware:
    """Тесты для RolesMiddleware"""

    @pytest.mark.asyncio
    async def test_role_admin(self):
        """Тест: пользователь с ролью admin"""
        middleware = RolesMiddleware()
        message = create_mock_message(user_id=12345)
        handler = AsyncMock(return_value="response")
        data = {}
        
        with patch("app.middlewares.roles.get_role_by_user_id", return_value="admin"):
            result = await middleware(handler, message, data)
        
        assert result == "response"
        assert data["user_role"] == "admin"
        assert data["is_admin"] is True
        assert data["is_user"] is False
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_role_user(self):
        """Тест: пользователь с ролью user"""
        middleware = RolesMiddleware()
        message = create_mock_message(user_id=12345)
        handler = AsyncMock(return_value="response")
        data = {}
        
        with patch("app.middlewares.roles.get_role_by_user_id", return_value="user"):
            result = await middleware(handler, message, data)
        
        assert result == "response"
        assert data["user_role"] == "user"
        assert data["is_admin"] is False
        assert data["is_user"] is True
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_role_none(self):
        """Тест: пользователь без роли"""
        middleware = RolesMiddleware()
        message = create_mock_message(user_id=12345)
        handler = AsyncMock(return_value="response")
        data = {}
        
        with patch("app.middlewares.roles.get_role_by_user_id", return_value=None):
            result = await middleware(handler, message, data)
        
        assert result == "response"
        assert data["user_role"] is None
        assert data["is_admin"] is False
        assert data["is_user"] is False
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_callback_query(self):
        """Тест: обработка CallbackQuery события"""
        middleware = RolesMiddleware()
        callback = create_mock_callback(user_id=54321)
        handler = AsyncMock(return_value="response")
        data = {}
        
        with patch("app.middlewares.roles.get_role_by_user_id", return_value="admin"):
            result = await middleware(handler, callback, data)
        
        assert result == "response"
        assert data["user_role"] == "admin"
        assert data["is_admin"] is True
        handler.assert_called_once_with(callback, data)

    @pytest.mark.asyncio
    async def test_message_without_from_user(self):
        """Тест: сообщение без from_user"""
        middleware = RolesMiddleware()
        message = create_mock_message()
        message.from_user = None
        handler = AsyncMock(return_value="response")
        data = {}
        
        result = await middleware(handler, message, data)
        
        assert result == "response"
        assert data["user_role"] is None
        assert data["is_admin"] is False
        assert data["is_user"] is False
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_callback_without_from_user(self):
        """Тест: callback без from_user"""
        middleware = RolesMiddleware()
        callback = create_mock_callback()
        callback.from_user = None
        handler = AsyncMock(return_value="response")
        data = {}
        
        result = await middleware(handler, callback, data)
        
        assert result == "response"
        assert data["user_role"] is None
        assert data["is_admin"] is False
        assert data["is_user"] is False
        handler.assert_called_once_with(callback, data)

    @pytest.mark.asyncio
    async def test_db_exception(self):
        """Тест: обработка исключения при запросе к БД"""
        middleware = RolesMiddleware()
        message = create_mock_message(user_id=12345)
        handler = AsyncMock(return_value="response")
        data = {}
        
        with patch("app.middlewares.roles.get_role_by_user_id", side_effect=Exception("DB error")):
            result = await middleware(handler, message, data)
        
        assert result == "response"
        assert data["user_role"] is None
        assert data["is_admin"] is False
        assert data["is_user"] is False
        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_unknown_event_type(self):
        """Тест: обработка неизвестного типа события"""
        middleware = RolesMiddleware()
        event = MagicMock()  # Не Message и не CallbackQuery
        handler = AsyncMock(return_value="response")
        data = {}
        
        result = await middleware(handler, event, data)
        
        assert result == "response"
        assert data["user_role"] is None
        assert data["is_admin"] is False
        assert data["is_user"] is False
        handler.assert_called_once_with(event, data)

