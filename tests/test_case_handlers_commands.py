"""
Тесты для хэндлеров команд кейсов.

Тестируемые модули:
- app/cases/career_dialog/handler.py
- app/cases/fb_peer/handler.py
- app/cases/fb_employee/handler.py

Тестируемые хэндлеры:
- career_start / fb_peer_start / ai_demo_start
- career_stop / fb_peer_stop / ai_demo_stop
- case_*_description
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, User, Chat

from app.cases.career_dialog.handler import (
    career_start,
    career_stop,
    case_career_dialog_description,
    CareerChat,
)
from app.cases.fb_peer.handler import (
    fb_peer_start,
    fb_peer_stop,
    case_fb_peer_description,
    FBPeerChat,
)
from app.cases.fb_employee.handler import (
    ai_demo_start,
    ai_demo_stop,
    case_fb_employee_description,
    AIChat,
)
from app.cases.career_dialog.config import CareerDialogConfig
from app.cases.fb_peer.config import FBPeerConfig
from app.cases.fb_employee.config import AIDemoConfig


def create_mock_message(user_id: int = 12345, chat_id: int = 12345) -> Message:
    """Создает мок-объект Message для тестов"""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = user_id
    message.chat = MagicMock(spec=Chat)
    message.chat.id = chat_id
    message.answer = AsyncMock()
    message.answer_document = AsyncMock()
    message.bot = MagicMock()
    return message


def create_mock_callback(user_id: int = 12345, chat_id: int = 12345, message_id: int = 100) -> CallbackQuery:
    """Создает мок-объект CallbackQuery для тестов"""
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = MagicMock(spec=User)
    callback.from_user.id = user_id
    callback.message = create_mock_message(user_id, chat_id)
    callback.message.message_id = message_id
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    return callback


def create_mock_state() -> FSMContext:
    """Создает мок-объект FSMContext для тестов"""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=None)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state


class TestCareerStartCommand:
    """Тесты для команды /career (career_start)"""

    @pytest.mark.asyncio
    async def test_career_start_basic(self):
        """Тест: базовый запуск команды /career"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await career_start(message, state)
            
            # Проверяем что контекст AI был очищен
            mock_clear.assert_called_once_with(CareerDialogConfig.CASE_ID, message.from_user.id)
            
            # Проверяем что состояние установлено
            state.set_state.assert_called_once_with(CareerChat.waiting_user)
            
            # Проверяем что данные инициализированы
            state.update_data.assert_called_once()
            call_kwargs = state.update_data.call_args[1]
            assert call_kwargs["turn_count"] == 0
            assert call_kwargs["dialogue_entries"] == []
            assert isinstance(call_kwargs["total_components_achieved"], set)
            
            # Проверяем что отправлено стартовое сообщение
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_career_start_sends_correct_message(self):
        """Тест: отправка правильного стартового сообщения"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_start(message, state)
            
            # Проверяем содержимое сообщения
            call_args = message.answer.call_args
            sent_text = call_args[0][0]
            assert "АЛГОРИТМ" in sent_text or "Максим" in sent_text
            assert call_args[1]["parse_mode"] == "Markdown"


class TestFBPeerStartCommand:
    """Тесты для команды /fbpeer (fb_peer_start)"""

    @pytest.mark.asyncio
    async def test_fbpeer_start_basic(self):
        """Тест: базовый запуск команды /fbpeer"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.fb_peer.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await fb_peer_start(message, state)
            
            # Проверяем что контекст AI был очищен
            mock_clear.assert_called_once_with(FBPeerConfig.CASE_ID, message.from_user.id)
            
            # Проверяем что состояние установлено
            state.set_state.assert_called_once_with(FBPeerChat.waiting_user)
            
            # Проверяем что данные инициализированы
            state.update_data.assert_called_once()
            call_kwargs = state.update_data.call_args[1]
            assert call_kwargs["turn_count"] == 0
            assert call_kwargs["dialogue_entries"] == []
            assert isinstance(call_kwargs["total_provd_achieved"], set)


class TestAIDemoStartCommand:
    """Тесты для команды /aidemo (ai_demo_start)"""

    @pytest.mark.asyncio
    async def test_aidemo_start_sends_multiple_messages(self):
        """Тест: отправка нескольких сообщений при старте"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock):
            await ai_demo_start(message, state)
            
            # Проверяем что отправлено как минимум 2 сообщения (стартовое + про аудио)
            assert message.answer.call_count == 2


class TestCareerStopCommand:
    """Тесты для команды /career_stop (career_stop)"""

    @pytest.mark.asyncio
    async def test_career_stop_clears_conversation(self):
        """Тест: очистка разговора при остановке"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await career_stop(message, state)
            
            # Проверяем что контекст AI был очищен
            mock_clear.assert_called_once_with(CareerDialogConfig.CASE_ID, message.from_user.id)

    @pytest.mark.asyncio
    async def test_career_stop_clears_state(self):
        """Тест: очистка состояния при остановке"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_stop(message, state)
            
            # Проверяем что состояние очищено
            state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_career_stop_sends_message(self):
        """Тест: отправка сообщения о завершении"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_stop(message, state)
            
            # Проверяем что отправлено сообщение
            message.answer.assert_called_once()
            call_args = message.answer.call_args
            sent_text = call_args[0][0]
            assert CareerDialogConfig.STOP_MESSAGE == sent_text


class TestFBPeerStopCommand:
    """Тесты для команды /fbpeer_stop (fb_peer_stop)"""

    @pytest.mark.asyncio
    async def test_fbpeer_stop_basic(self):
        """Тест: базовая остановка fb_peer"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.fb_peer.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await fb_peer_stop(message, state)
            
            mock_clear.assert_called_once_with(FBPeerConfig.CASE_ID, message.from_user.id)
            state.clear.assert_called_once()
            message.answer.assert_called_once()


class TestAIDemoStopCommand:
    """Тесты для команды /aidemo_stop (ai_demo_stop)"""

    @pytest.mark.asyncio
    async def test_aidemo_stop_basic(self):
        """Тест: базовая остановка aidemo"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await ai_demo_stop(message, state)
            
            mock_clear.assert_called_once_with(AIDemoConfig.CASE_ID, message.from_user.id)
            state.clear.assert_called_once()


class TestCareerDialogDescription:
    """Тесты для case_career_dialog_description"""

    @pytest.mark.asyncio
    async def test_description_shows_case_info(self):
        """Тест: показ описания кейса"""
        callback = create_mock_callback()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            await case_career_dialog_description(callback, state)
            
            # Проверяем что отправлено сообщение с описанием
            callback.message.answer.assert_called_once()
            
            # Проверяем что callback был отвечен
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_description_disables_previous_buttons(self):
        """Тест: отключение предыдущих кнопок при показе описания"""
        callback = create_mock_callback()
        state = create_mock_state()
        state.get_data = AsyncMock(return_value={"active_inline_message_id": 99})
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock) as mock_disable:
            await case_career_dialog_description(callback, state)
            
            # Проверяем что предыдущие кнопки были отключены
            mock_disable.assert_called_once()

    @pytest.mark.asyncio
    async def test_description_saves_message_id(self):
        """Тест: сохранение ID сообщения"""
        callback = create_mock_callback()
        state = create_mock_state()
        
        # Мокаем возвращаемое сообщение
        mock_sent_message = MagicMock()
        mock_sent_message.message_id = 123
        callback.message.answer = AsyncMock(return_value=mock_sent_message)
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            await case_career_dialog_description(callback, state)
            
            # Проверяем что ID сохранен
            state.update_data.assert_called_once()
            call_kwargs = state.update_data.call_args[1]
            assert call_kwargs.get("active_inline_message_id") == 123

    @pytest.mark.asyncio
    async def test_description_handles_missing_message(self):
        """Тест: обработка отсутствующего сообщения"""
        callback = create_mock_callback()
        callback.message = None
        state = create_mock_state()
        
        await case_career_dialog_description(callback, state)
        
        # Должен просто ответить на callback без ошибок
        callback.answer.assert_called_once()


class TestFBPeerDescription:
    """Тесты для case_fb_peer_description"""

    @pytest.mark.asyncio
    async def test_fbpeer_description_basic(self):
        """Тест: базовое описание fb_peer"""
        callback = create_mock_callback()
        state = create_mock_state()
        
        with patch("app.cases.fb_peer.handler.disable_buttons_by_id", new_callable=AsyncMock):
            await case_fb_peer_description(callback, state)
            
            callback.message.answer.assert_called_once()
            callback.answer.assert_called_once()


class TestFBEmployeeDescription:
    """Тесты для case_fb_employee_description"""

    @pytest.mark.asyncio
    async def test_fbemployee_description_basic(self):
        """Тест: базовое описание fb_employee"""
        callback = create_mock_callback()
        state = create_mock_state()
        
        with patch("app.cases.fb_employee.handler.disable_buttons_by_id", new_callable=AsyncMock):
            await case_fb_employee_description(callback, state)
            
            callback.message.answer.assert_called_once()
            callback.answer.assert_called_once()


class TestEdgeCases:
    """Тесты граничных случаев для команд"""

    @pytest.mark.asyncio
    async def test_start_with_exception_in_clear(self):
        """Тест: исключение при очистке контекста"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock, side_effect=Exception("Clear error")):
            # Должен выбросить исключение или обработать его
            with pytest.raises(Exception):
                await career_start(message, state)

    @pytest.mark.asyncio
    async def test_description_with_same_message_id(self):
        """Тест: описание с тем же message_id (не должно отключать кнопки)"""
        callback = create_mock_callback(message_id=100)
        state = create_mock_state()
        state.get_data = AsyncMock(return_value={"active_inline_message_id": 100})
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock) as mock_disable:
            await case_career_dialog_description(callback, state)
            
            # Не должно вызывать disable для того же message_id
            mock_disable.assert_not_called()


class TestMultipleUsers:
    """Тесты с разными пользователями"""

    @pytest.mark.asyncio
    async def test_start_different_users(self):
        """Тест: старт для разных пользователей"""
        message1 = create_mock_message(user_id=111)
        message2 = create_mock_message(user_id=222)
        state1 = create_mock_state()
        state2 = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await career_start(message1, state1)
            await career_start(message2, state2)
            
            # Проверяем что для каждого пользователя вызвана очистка
            assert mock_clear.call_count == 2
            
            # Проверяем что вызваны с правильными user_id
            calls = mock_clear.call_args_list
            assert calls[0][0][1] == 111
            assert calls[1][0][1] == 222

    @pytest.mark.asyncio
    async def test_stop_independent_users(self):
        """Тест: остановка независима для разных пользователей"""
        message1 = create_mock_message(user_id=333)
        message2 = create_mock_message(user_id=444)
        state1 = create_mock_state()
        state2 = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await career_stop(message1, state1)
            await career_stop(message2, state2)
            
            # Оба должны завершиться успешно
            assert mock_clear.call_count == 2
            state1.clear.assert_called_once()
            state2.clear.assert_called_once()


class TestStateTransitions:
    """Тесты переходов состояний"""

    @pytest.mark.asyncio
    async def test_start_sets_waiting_user_state(self):
        """Тест: старт устанавливает состояние waiting_user"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_start(message, state)
            
            state.set_state.assert_called_once_with(CareerChat.waiting_user)

    @pytest.mark.asyncio
    async def test_stop_clears_any_state(self):
        """Тест: остановка очищает любое состояние"""
        message = create_mock_message()
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=CareerChat.waiting_user)
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_stop(message, state)
            
            state.clear.assert_called_once()


class TestMessageFormatting:
    """Тесты форматирования сообщений"""

    @pytest.mark.asyncio
    async def test_start_message_markdown(self):
        """Тест: стартовое сообщение в формате Markdown"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_start(message, state)
            
            call_args = message.answer.call_args
            assert call_args[1].get("parse_mode") == "Markdown"

    @pytest.mark.asyncio
    async def test_stop_message_markdown(self):
        """Тест: сообщение об остановке в формате Markdown"""
        message = create_mock_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_stop(message, state)
            
            call_args = message.answer.call_args
            assert call_args[1].get("parse_mode") == "Markdown"

