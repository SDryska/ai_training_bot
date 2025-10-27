"""
Тесты для хэндлеров помощи.

Тестируемый модуль:
- app/handlers/help.py

Тестируемые хэндлеры:
- cmd_help - команда /help
- cmd_faq - команда /faq
- nav_help - обработчик кнопки 'Команды'
- nav_faq - обработчик кнопки 'FAQ'
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, CallbackQuery, User, Chat

from app.handlers.help import cmd_help, cmd_faq, nav_help, nav_faq
from app.keyboards.menu import CALLBACK_NAV_HELP, CALLBACK_NAV_FAQ


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
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    return callback


class TestCmdHelp:
    """Тесты для cmd_help"""

    @pytest.mark.asyncio
    async def test_cmd_help_basic(self):
        """Тест: команда /help"""
        message = create_mock_message()
        
        with patch("app.handlers.help.get_back_menu_inline", new_callable=MagicMock):
            await cmd_help(message)
            
            message.answer.assert_called_once()


class TestCmdFaq:
    """Тесты для cmd_faq"""

    @pytest.mark.asyncio
    async def test_cmd_faq_basic(self):
        """Тест: команда /faq"""
        message = create_mock_message()
        
        with patch("app.handlers.help.get_back_menu_inline", new_callable=MagicMock):
            await cmd_faq(message)
            
            message.answer.assert_called_once()


class TestNavHelp:
    """Тесты для nav_help"""

    @pytest.mark.asyncio
    async def test_nav_help_success(self):
        """Тест: успешное редактирование сообщения для nav_help"""
        callback = create_mock_callback(data=CALLBACK_NAV_HELP)
        
        with patch("app.handlers.help.get_back_menu_inline", new_callable=MagicMock):
            await nav_help(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_nav_help_no_message(self):
        """Тест: nav_help без сообщения"""
        callback = create_mock_callback(data=CALLBACK_NAV_HELP)
        callback.message = None
        
        await nav_help(callback)
        
        callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_nav_help_edit_fails(self):
        """Тест: fallback на answer при ошибке edit_text"""
        callback = create_mock_callback(data=CALLBACK_NAV_HELP)
        callback.message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))
        
        with patch("app.handlers.help.get_back_menu_inline", new_callable=MagicMock):
            await nav_help(callback)
            
            callback.message.answer.assert_called_once()
            callback.answer.assert_called_once()


class TestNavFaq:
    """Тесты для nav_faq"""

    @pytest.mark.asyncio
    async def test_nav_faq_success(self):
        """Тест: успешное редактирование сообщения для nav_faq"""
        callback = create_mock_callback(data=CALLBACK_NAV_FAQ)
        
        with patch("app.handlers.help.get_back_menu_inline", new_callable=MagicMock):
            await nav_faq(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_nav_faq_no_message(self):
        """Тест: nav_faq без сообщения"""
        callback = create_mock_callback(data=CALLBACK_NAV_FAQ)
        callback.message = None
        
        await nav_faq(callback)
        
        callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_nav_faq_edit_fails(self):
        """Тест: fallback на answer при ошибке edit_text"""
        callback = create_mock_callback(data=CALLBACK_NAV_FAQ)
        callback.message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))
        
        with patch("app.handlers.help.get_back_menu_inline", new_callable=MagicMock):
            await nav_faq(callback)
            
            callback.message.answer.assert_called_once()
            callback.answer.assert_called_once()

