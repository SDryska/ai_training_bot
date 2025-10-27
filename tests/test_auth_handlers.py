"""
Тесты для хэндлеров авторизации.

Тестируемый модуль:
- app/handlers/auth.py

Тестируемые хэндлеры:
- cmd_start - команда /start
- handle_password - обработка пароля
- cmd_dbping - команда /dbping
- cmd_whoami - команда /whoami
- cmd_change_role - команда /change_role
- cmd_relogin - команда /relogin
- send_welcome_with_image - отправка приветствия с изображением
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User, Chat
from pathlib import Path

from app.handlers.auth import (
    cmd_start,
    handle_password,
    cmd_dbping,
    cmd_whoami,
    cmd_change_role,
    cmd_relogin,
    send_welcome_with_image,
    AuthStates,
)


def create_mock_message(user_id: int = 12345, chat_id: int = 12345, text: str = "Test message") -> Message:
    """Создает мок-объект Message для тестов"""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = user_id
    message.chat = MagicMock(spec=Chat)
    message.chat.id = chat_id
    message.text = text
    message.answer = AsyncMock()
    message.answer_photo = AsyncMock()
    message.bot = MagicMock()
    return message


def create_mock_state(state_value=None, data: dict = None) -> FSMContext:
    """Создает мок-объект FSMContext для тестов"""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=state_value)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value=data or {})
    state.clear = AsyncMock()
    return state


class TestSendWelcomeWithImage:
    """Тесты для send_welcome_with_image"""

    @pytest.mark.asyncio
    async def test_send_welcome_with_image_exists(self):
        """Тест: отправка приветствия с существующим изображением"""
        message = create_mock_message()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.__init__", return_value=None), \
             patch("app.handlers.auth.FSInputFile", new_callable=MagicMock), \
             patch("app.handlers.auth.get_main_menu_inline", new_callable=MagicMock):
            
            await send_welcome_with_image(message)
            
            message.answer_photo.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_welcome_with_image_not_exists(self):
        """Тест: отправка приветствия без изображения"""
        message = create_mock_message()
        
        with patch("pathlib.Path.exists", return_value=False), \
             patch("app.handlers.auth.get_main_menu_inline", new_callable=MagicMock):
            
            await send_welcome_with_image(message)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_welcome_with_image_exception(self):
        """Тест: обработка исключения при отправке изображения"""
        message = create_mock_message()
        
        with patch("pathlib.Path.exists", side_effect=Exception("File error")), \
             patch("app.handlers.auth.get_main_menu_inline", new_callable=MagicMock):
            
            await send_welcome_with_image(message)
            
            message.answer.assert_called_once()


class TestCmdStart:
    """Тесты для cmd_start"""

    @pytest.mark.asyncio
    async def test_cmd_start_auth_disabled(self):
        """Тест: команда /start при отключенной авторизации"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.clear_all_conversations", new_callable=AsyncMock), \
             patch("app.handlers.auth.remove_reply_keyboard", new_callable=AsyncMock):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = None
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = None
            
            await cmd_start(message, state)
            
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_cmd_start_user_already_authorized(self):
        """Тест: команда /start для уже авторизованного пользователя"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.clear_all_conversations", new_callable=AsyncMock), \
             patch("app.handlers.auth.remove_reply_keyboard", new_callable=AsyncMock), \
             patch("app.handlers.auth.get_role_by_user_id", new_callable=AsyncMock, return_value="user"), \
             patch("app.handlers.auth.get_main_menu_inline", new_callable=MagicMock):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = "password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = None
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await cmd_start(message, state)
            
            message.answer_photo.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_start_admin_already_authorized(self):
        """Тест: команда /start для уже авторизованного админа"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.clear_all_conversations", new_callable=AsyncMock), \
             patch("app.handlers.auth.remove_reply_keyboard", new_callable=AsyncMock), \
             patch("app.handlers.auth.get_role_by_user_id", new_callable=AsyncMock, return_value="admin"):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = "password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = "admin_password"
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await cmd_start(message, state)
            
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_cmd_start_prompt_for_password(self):
        """Тест: команда /start запрашивает пароль"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.clear_all_conversations", new_callable=AsyncMock), \
             patch("app.handlers.auth.remove_reply_keyboard", new_callable=AsyncMock), \
             patch("app.handlers.auth.get_role_by_user_id", new_callable=AsyncMock, return_value=None):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = "password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = None
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await cmd_start(message, state)
            
            state.set_state.assert_called_with(AuthStates.waiting_password)
            message.answer.assert_called()


class TestHandlePassword:
    """Тесты для handle_password"""

    @pytest.mark.asyncio
    async def test_handle_password_user_correct(self):
        """Тест: правильный пароль пользователя"""
        message = create_mock_message(text="user_password")
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.upsert_authorized_user", new_callable=AsyncMock), \
             patch("app.handlers.auth.get_main_menu_inline", new_callable=MagicMock), \
             patch("app.handlers.auth.remove_reply_keyboard", new_callable=AsyncMock):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = "user_password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = "admin_password"
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await handle_password(message, state)
            
            message.answer_photo.assert_called_once()
            state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_password_admin_correct(self):
        """Тест: правильный пароль админа"""
        message = create_mock_message(text="admin_password")
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.upsert_authorized_user", new_callable=AsyncMock):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = "user_password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = "admin_password"
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await handle_password(message, state)
            
            message.answer.assert_called()
            state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_password_invalid(self):
        """Тест: неправильный пароль"""
        message = create_mock_message(text="wrong_password")
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings:
            mock_settings.return_value.AUTH_PASSWORD_USER = "user_password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = "admin_password"
            
            await handle_password(message, state)
            
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_handle_password_no_db(self):
        """Тест: авторизация без БД"""
        message = create_mock_message(text="user_password")
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.get_main_menu_inline", new_callable=MagicMock), \
             patch("app.handlers.auth.remove_reply_keyboard", new_callable=AsyncMock):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = "user_password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = None
            mock_settings.return_value.DATABASE_URL = None
            
            await handle_password(message, state)
            
            message.answer_photo.assert_called_once()
            state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_password_db_error(self):
        """Тест: ошибка при сохранении в БД"""
        message = create_mock_message(text="user_password")
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.upsert_authorized_user", new_callable=AsyncMock, side_effect=Exception("DB error")):
            
            mock_settings.return_value.AUTH_PASSWORD_USER = "user_password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = None
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await handle_password(message, state)
            
            message.answer.assert_called()
            state.clear.assert_called_once()


class TestCmdDbping:
    """Тесты для cmd_dbping"""

    @pytest.mark.asyncio
    async def test_cmd_dbping_no_db_url(self):
        """Тест: команда /dbping без настроенной БД"""
        message = create_mock_message()
        
        with patch("app.handlers.auth.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            
            await cmd_dbping(message)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_dbping_success(self):
        """Тест: успешная проверка подключения к БД"""
        message = create_mock_message()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("asyncpg.connect") as mock_connect, \
             patch("app.handlers.auth.normalize_db_url", return_value="postgresql://..."):
            
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=1)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await cmd_dbping(message)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_dbping_error(self):
        """Тест: ошибка при подключении к БД"""
        message = create_mock_message()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("asyncpg.connect") as mock_connect:
            
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            mock_connect.side_effect = Exception("Connection error")
            
            await cmd_dbping(message)
            
            message.answer.assert_called_once()


class TestCmdWhoami:
    """Тесты для cmd_whoami"""

    @pytest.mark.asyncio
    async def test_cmd_whoami_no_db_url(self):
        """Тест: команда /whoami без настроенной БД"""
        message = create_mock_message()
        
        with patch("app.handlers.auth.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            
            await cmd_whoami(message)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_whoami_user_found(self):
        """Тест: пользователь найден в БД"""
        message = create_mock_message()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.get_authorized_user", new_callable=AsyncMock, return_value={
                 "role": "user",
                 "created_at": "2024-01-01"
             }):
            
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await cmd_whoami(message)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_whoami_user_not_found(self):
        """Тест: пользователь не найден в БД"""
        message = create_mock_message()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.get_authorized_user", new_callable=AsyncMock, return_value=None):
            
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await cmd_whoami(message)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_whoami_db_error(self):
        """Тест: ошибка при запросе к БД"""
        message = create_mock_message()
        
        with patch("app.handlers.auth.Settings") as mock_settings, \
             patch("app.handlers.auth.get_authorized_user", new_callable=AsyncMock, side_effect=Exception("DB error")):
            
            mock_settings.return_value.DATABASE_URL = "postgresql://..."
            
            await cmd_whoami(message)
            
            message.answer.assert_called_once()


class TestCmdChangeRole:
    """Тесты для cmd_change_role"""

    @pytest.mark.asyncio
    async def test_cmd_change_role_auth_disabled(self):
        """Тест: команда /change_role при отключенной авторизации"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings:
            mock_settings.return_value.AUTH_PASSWORD_USER = None
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = None
            
            await cmd_change_role(message, state)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_change_role_requests_password(self):
        """Тест: команда /change_role запрашивает пароль"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.handlers.auth.Settings") as mock_settings:
            mock_settings.return_value.AUTH_PASSWORD_USER = "password"
            mock_settings.return_value.AUTH_PASSWORD_ADMIN = None
            
            await cmd_change_role(message, state)
            
            state.set_state.assert_called_with(AuthStates.waiting_password)
            message.answer.assert_called_once()


class TestCmdRelogin:
    """Тесты для cmd_relogin"""

    @pytest.mark.asyncio
    async def test_cmd_relogin_calls_change_role(self):
        """Тест: команда /relogin вызывает cmd_change_role"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.handlers.auth.cmd_change_role", new_callable=AsyncMock) as mock_change_role:
            await cmd_relogin(message, state)
            
            mock_change_role.assert_called_once_with(message, state)

