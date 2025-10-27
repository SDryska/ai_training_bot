"""
Тесты для навигационных хэндлеров.

Тестируемый модуль:
- app/handlers/nav.py

Тестируемые хэндлеры:
- back_to_menu - возврат в главное меню
- open_rate_from_menu - открытие рейтинга из меню
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User, Chat, Message

from app.handlers.nav import back_to_menu, open_rate_from_menu
from app.keyboards.menu import CALLBACK_NAV_MENU, CALLBACK_NAV_RATE


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


def create_mock_state(state_value=None, data: dict = None) -> FSMContext:
    """Создает мок-объект FSMContext для тестов"""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=state_value)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value=data or {})
    state.clear = AsyncMock()
    return state


class TestBackToMenu:
    """Тесты для back_to_menu"""

    @pytest.mark.asyncio
    async def test_back_to_menu_success(self):
        """Тест: успешный возврат в главное меню"""
        callback = create_mock_callback(data=CALLBACK_NAV_MENU)
        state = create_mock_state()
        
        with patch("app.handlers.nav.clear_all_conversations", new_callable=AsyncMock), \
             patch("app.handlers.nav.get_main_menu_inline", new_callable=MagicMock), \
             patch("app.handlers.nav.remove_reply_keyboard", new_callable=AsyncMock):
            
            await back_to_menu(callback, state)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()
            state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_back_to_menu_edit_fails(self):
        """Тест: fallback на answer при ошибке edit_text"""
        callback = create_mock_callback(data=CALLBACK_NAV_MENU)
        callback.message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))
        state = create_mock_state()
        
        with patch("app.handlers.nav.clear_all_conversations", new_callable=AsyncMock), \
             patch("app.handlers.nav.get_main_menu_inline", new_callable=MagicMock), \
             patch("app.handlers.nav.remove_reply_keyboard", new_callable=AsyncMock):
            
            await back_to_menu(callback, state)
            
            # callback.message.answer вызывается и для fallback, и в remove_reply_keyboard
            assert callback.message.answer.call_count >= 1
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_back_to_menu_clear_conversations_error(self):
        """Тест: обработка ошибки при очистке диалогов"""
        callback = create_mock_callback(data=CALLBACK_NAV_MENU)
        state = create_mock_state()
        
        with patch("app.handlers.nav.clear_all_conversations", new_callable=AsyncMock, side_effect=Exception("Error")), \
             patch("app.handlers.nav.get_main_menu_inline", new_callable=MagicMock), \
             patch("app.handlers.nav.remove_reply_keyboard", new_callable=AsyncMock):
            
            await back_to_menu(callback, state)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_back_to_menu_state_clear_error(self):
        """Тест: обработка ошибки при очистке состояния"""
        callback = create_mock_callback(data=CALLBACK_NAV_MENU)
        state = create_mock_state()
        state.clear = AsyncMock(side_effect=Exception("Error"))
        
        with patch("app.handlers.nav.clear_all_conversations", new_callable=AsyncMock), \
             patch("app.handlers.nav.get_main_menu_inline", new_callable=MagicMock), \
             patch("app.handlers.nav.remove_reply_keyboard", new_callable=AsyncMock):
            
            await back_to_menu(callback, state)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()


class TestOpenRateFromMenu:
    """Тесты для open_rate_from_menu"""

    @pytest.mark.asyncio
    async def test_open_rate_from_menu_success(self):
        """Тест: успешное открытие рейтинга из меню"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        
        with patch("app.handlers.nav.rating_open_inline", new_callable=MagicMock):
            await open_rate_from_menu(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_rate_from_menu_edit_fails(self):
        """Тест: fallback на answer при ошибке edit_text"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        callback.message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))
        
        with patch("app.handlers.nav.rating_open_inline", new_callable=MagicMock):
            await open_rate_from_menu(callback)
            
            callback.message.answer.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_rate_from_menu_no_message(self):
        """Тест: open_rate_from_menu без сообщения"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        callback.message = None
        
        await open_rate_from_menu(callback)
        
        callback.answer.assert_called_once()

