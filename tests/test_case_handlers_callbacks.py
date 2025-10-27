"""
Тесты для callback хэндлеров кейсов.

Тестируемые модули:
- app/cases/career_dialog/handler.py
- app/cases/fb_peer/handler.py
- app/cases/fb_employee/handler.py

Тестируемые хэндлеры:
- case_*_start_dialog (начало диалога)
- case_*_theory (теория/PDF)
- case_controls_handler (restart/review кнопки)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, User, Chat, Message, FSInputFile

from app.cases.career_dialog.handler import (
    case_career_dialog_start_dialog,
    case_career_dialog_theory,
    case_controls_handler as career_controls_handler,
    CareerChat,
)
from app.cases.fb_peer.handler import (
    case_fb_peer_start_dialog,
    case_fb_peer_theory,
    case_controls_handler as peer_controls_handler,
    FBPeerChat,
)
from app.cases.fb_employee.handler import (
    case_fb_employee_start_dialog,
    case_fb_employee_theory,
    case_controls_handler as employee_controls_handler,
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
    message.message_id = 100
    message.answer = AsyncMock()
    message.answer_document = AsyncMock()
    message.edit_reply_markup = AsyncMock()
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
    callback.message = create_mock_message(user_id, chat_id)
    callback.message.message_id = message_id
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


class TestCareerDialogStartDialog:
    """Тесты для case_career_dialog_start_dialog"""

    @pytest.mark.asyncio
    async def test_start_dialog_from_idle(self):
        """Тест: начало диалога из неактивного состояния"""
        callback = create_mock_callback(data="case:career_dialog:start")
        state = create_mock_state(state_value=None)
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear, \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.mark_case_started", new_callable=AsyncMock):
            
            await case_career_dialog_start_dialog(callback, state)
            
            # Проверяем что AI контекст был очищен
            mock_clear.assert_called_once_with(CareerDialogConfig.CASE_ID, callback.from_user.id)
            
            # Проверяем установку состояния
            state.set_state.assert_called_with(CareerChat.waiting_user)
            
            # Проверяем отправку сообщений
            assert callback.message.answer.call_count >= 2  # Стартовое + про аудио

    @pytest.mark.asyncio
    async def test_start_dialog_already_active(self):
        """Тест: попытка начать диалог когда он уже активен"""
        callback = create_mock_callback(data="case:career_dialog:start")
        state = create_mock_state(state_value=CareerChat.waiting_user)
        
        await case_career_dialog_start_dialog(callback, state)
        
        # Должен отправить предупреждение
        callback.answer.assert_called_once()
        answer_text = callback.answer.call_args[0][0]
        assert "уже активен" in answer_text.lower()

    @pytest.mark.asyncio
    async def test_start_dialog_initializes_data(self):
        """Тест: инициализация данных при старте диалога"""
        callback = create_mock_callback(data="case:career_dialog:start")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.mark_case_started", new_callable=AsyncMock):
            
            await case_career_dialog_start_dialog(callback, state)
            
            # Проверяем инициализацию данных
            state.update_data.assert_called()
            call_kwargs = state.update_data.call_args[1]
            assert call_kwargs["turn_count"] == 0
            assert call_kwargs["dialogue_entries"] == []
            assert isinstance(call_kwargs["total_components_achieved"], set)

    @pytest.mark.asyncio
    async def test_start_dialog_marks_case_started(self):
        """Тест: пометка о старте кейса в статистике"""
        callback = create_mock_callback(data="case:career_dialog:start")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.mark_case_started", new_callable=AsyncMock) as mock_mark:
            
            await case_career_dialog_start_dialog(callback, state)
            
            # Проверяем что статистика обновлена
            mock_mark.assert_called_once_with(callback.from_user.id, CareerDialogConfig.CASE_ID)

    @pytest.mark.asyncio
    async def test_start_dialog_handles_missing_message(self):
        """Тест: обработка отсутствующего сообщения"""
        callback = create_mock_callback(data="case:career_dialog:start")
        callback.message = None
        state = create_mock_state()
        
        await case_career_dialog_start_dialog(callback, state)
        
        # Должен просто ответить на callback
        callback.answer.assert_called_once()


class TestFBPeerStartDialog:
    """Тесты для case_fb_peer_start_dialog"""

    @pytest.mark.asyncio
    async def test_fbpeer_start_dialog_basic(self):
        """Тест: базовый старт диалога fb_peer"""
        callback = create_mock_callback(data="case:fb_peer:start")
        state = create_mock_state()
        
        with patch("app.cases.fb_peer.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.mark_case_started", new_callable=AsyncMock):
            
            await case_fb_peer_start_dialog(callback, state)
            
            state.set_state.assert_called_with(FBPeerChat.waiting_user)
            assert callback.message.answer.call_count >= 2


class TestFBEmployeeStartDialog:
    """Тесты для case_fb_employee_start_dialog"""

    @pytest.mark.asyncio
    async def test_fbemployee_start_dialog_basic(self):
        """Тест: базовый старт диалога fb_employee"""
        callback = create_mock_callback(data="case:fb_employee:start")
        state = create_mock_state()
        
        with patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.mark_case_started", new_callable=AsyncMock):
            
            await case_fb_employee_start_dialog(callback, state)
            
            state.set_state.assert_called_with(AIChat.waiting_user)
            assert callback.message.answer.call_count >= 2


class TestCareerDialogTheory:
    """Тесты для case_career_dialog_theory"""

    @pytest.mark.asyncio
    async def test_theory_sends_pdf(self):
        """Тест: отправка PDF с теорией"""
        callback = create_mock_callback(data="case:career_dialog:theory")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("builtins.open", mock_open(read_data=b"PDF content")):
            
            await case_career_dialog_theory(callback, state)
            
            # Проверяем что PDF был отправлен
            callback.message.answer_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_theory_handles_missing_file(self):
        """Тест: обработка отсутствующего файла"""
        callback = create_mock_callback(data="case:career_dialog:theory")
        state = create_mock_state()
        
        # Мокаем answer_document чтобы выбросить FileNotFoundError
        callback.message.answer_document = AsyncMock(side_effect=FileNotFoundError("File not found"))
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            await case_career_dialog_theory(callback, state)
            
            # Должен отправить уведомление об ошибке
            callback.answer.assert_called_once()
            answer_kwargs = callback.answer.call_args[1]
            assert answer_kwargs.get("show_alert") is True

    @pytest.mark.asyncio
    async def test_theory_disables_previous_buttons(self):
        """Тест: отключение предыдущих кнопок"""
        callback = create_mock_callback(data="case:career_dialog:theory")
        state = create_mock_state(data={"active_inline_message_id": 99})
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock) as mock_disable, \
             patch("builtins.open", mock_open(read_data=b"PDF content")):
            
            await case_career_dialog_theory(callback, state)
            
            # Проверяем что предыдущие кнопки отключены
            mock_disable.assert_called_once()


class TestFBPeerTheory:
    """Тесты для case_fb_peer_theory"""

    @pytest.mark.asyncio
    async def test_fbpeer_theory_sends_correct_pdf(self):
        """Тест: отправка правильного PDF для fb_peer"""
        callback = create_mock_callback(data="case:fb_peer:theory")
        state = create_mock_state()
        
        with patch("app.cases.fb_peer.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("builtins.open", mock_open(read_data=b"PDF content")):
            
            await case_fb_peer_theory(callback, state)
            
            callback.message.answer_document.assert_called_once()


class TestFBEmployeeTheory:
    """Тесты для case_fb_employee_theory"""

    @pytest.mark.asyncio
    async def test_fbemployee_theory_sends_correct_pdf(self):
        """Тест: отправка правильного PDF для fb_employee"""
        callback = create_mock_callback(data="case:fb_employee:theory")
        state = create_mock_state()
        
        with patch("app.cases.fb_employee.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("builtins.open", mock_open(read_data=b"PDF content")):
            
            await case_fb_employee_theory(callback, state)
            
            callback.message.answer_document.assert_called_once()


class TestCareerControlsRestart:
    """Тесты для кнопки restart (career_dialog)"""

    @pytest.mark.asyncio
    async def test_restart_clears_and_restarts(self):
        """Тест: перезапуск диалога"""
        callback = create_mock_callback(data="case:career_dialog:restart")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await career_controls_handler(callback, state)
            
            # Проверяем очистку контекста
            mock_clear.assert_called_once_with(CareerDialogConfig.CASE_ID, callback.from_user.id)
            
            # Проверяем очистку состояния
            state.clear.assert_called_once()
            
            # Проверяем установку нового состояния
            state.set_state.assert_called_with(CareerChat.waiting_user)

    @pytest.mark.asyncio
    async def test_restart_initializes_fresh_data(self):
        """Тест: инициализация свежих данных при перезапуске"""
        callback = create_mock_callback(data="case:career_dialog:restart")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_controls_handler(callback, state)
            
            # Проверяем инициализацию данных
            state.update_data.assert_called()
            call_kwargs = state.update_data.call_args[1]
            assert call_kwargs["turn_count"] == 0
            assert call_kwargs["dialogue_entries"] == []

    @pytest.mark.asyncio
    async def test_restart_disables_buttons(self):
        """Тест: отключение кнопок при перезапуске"""
        callback = create_mock_callback(data="case:career_dialog:restart")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            await career_controls_handler(callback, state)
            
            # Проверяем что кнопки были отключены
            callback.message.edit_reply_markup.assert_called()


class TestCareerControlsReview:
    """Тесты для кнопки review (career_dialog)"""

    @pytest.mark.asyncio
    async def test_review_from_waiting_user_state(self):
        """Тест: получение анализа из активного диалога"""
        callback = create_mock_callback(data="case:career_dialog:review")
        state = create_mock_state(
            state_value=CareerChat.waiting_user,
            data={"dialogue_entries": [
                {"role": "Руководитель", "text": "Привет"},
                {"role": "Максим", "text": "Здравствуйте"}
            ]}
        )
        
        # Мокаем рецензента
        mock_review_result = "Хороший диалог!"
        
        with patch("app.cases.career_dialog.handler.perform_dialogue_review", new_callable=AsyncMock, return_value=mock_review_result), \
             patch("app.cases.career_dialog.handler.with_analysis_indicator", new_callable=AsyncMock, return_value=mock_review_result), \
             patch("app.cases.career_dialog.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            
            await career_controls_handler(callback, state)
            
            # Проверяем что отправлен результат анализа
            callback.message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_review_from_non_active_state(self):
        """Тест: попытка получить анализ не из активного диалога"""
        callback = create_mock_callback(data="case:career_dialog:review")
        state = create_mock_state(state_value=None)
        
        await career_controls_handler(callback, state)
        
        # Должен отправить уведомление об ошибке
        callback.answer.assert_called_once()
        answer_text = callback.answer.call_args[0][0]
        assert "активного диалога" in answer_text.lower()

    @pytest.mark.asyncio
    async def test_review_marks_completed(self):
        """Тест: пометка кейса как завершенного при ручном анализе"""
        callback = create_mock_callback(data="case:career_dialog:review")
        state = create_mock_state(
            state_value=CareerChat.waiting_user,
            data={"dialogue_entries": [{"role": "Руководитель", "text": "Текст"}]}
        )
        
        with patch("app.cases.career_dialog.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.career_dialog.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.career_dialog.handler.mark_case_completed", new_callable=AsyncMock) as mock_mark, \
             patch("app.cases.career_dialog.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            
            await career_controls_handler(callback, state)
            
            # Проверяем что кейс отмечен как завершенный
            mock_mark.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_sends_survey_invitation(self):
        """Тест: отправка приглашения к опросу после анализа"""
        callback = create_mock_callback(data="case:career_dialog:review")
        state = create_mock_state(
            state_value=CareerChat.waiting_user,
            data={"dialogue_entries": [{"role": "Руководитель", "text": "Текст"}]}
        )
        
        with patch("app.cases.career_dialog.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.career_dialog.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.career_dialog.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=True), \
             patch("app.cases.career_dialog.handler.send_survey_invitation", new_callable=AsyncMock) as mock_survey, \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            
            await career_controls_handler(callback, state)
            
            # Проверяем что приглашение к опросу отправлено
            mock_survey.assert_called_once()


class TestPeerControlsHandlers:
    """Тесты для кнопок управления fb_peer"""

    @pytest.mark.asyncio
    async def test_peer_restart(self):
        """Тест: перезапуск диалога fb_peer"""
        callback = create_mock_callback(data="case:fb_peer:restart")
        state = create_mock_state()
        
        with patch("app.cases.fb_peer.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await peer_controls_handler(callback, state)
            
            mock_clear.assert_called_once_with(FBPeerConfig.CASE_ID, callback.from_user.id)
            state.set_state.assert_called_with(FBPeerChat.waiting_user)

    @pytest.mark.asyncio
    async def test_peer_review(self):
        """Тест: получение анализа fb_peer"""
        callback = create_mock_callback(data="case:fb_peer:review")
        state = create_mock_state(
            state_value=FBPeerChat.waiting_user,
            data={"dialogue_entries": [{"role": "Коллега", "text": "Текст"}]}
        )
        
        with patch("app.cases.fb_peer.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.fb_peer.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.fb_peer.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_peer.handler.disable_buttons_by_id", new_callable=AsyncMock):
            
            await peer_controls_handler(callback, state)
            
            callback.message.answer.assert_called()


class TestEmployeeControlsHandlers:
    """Тесты для кнопок управления fb_employee"""

    @pytest.mark.asyncio
    async def test_employee_restart(self):
        """Тест: перезапуск диалога fb_employee"""
        callback = create_mock_callback(data="case:fb_employee:restart")
        state = create_mock_state()
        
        with patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear:
            await employee_controls_handler(callback, state)
            
            mock_clear.assert_called_once_with(AIDemoConfig.CASE_ID, callback.from_user.id)
            state.set_state.assert_called_with(AIChat.waiting_user)

    @pytest.mark.asyncio
    async def test_employee_review(self):
        """Тест: получение анализа fb_employee"""
        callback = create_mock_callback(data="case:fb_employee:review")
        state = create_mock_state(
            state_value=AIChat.waiting_user,
            data={"dialogue_entries": [{"role": "Руководитель", "text": "Текст"}]}
        )
        
        with patch("app.cases.fb_employee.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.fb_employee.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="OK"), \
             patch("app.cases.fb_employee.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_employee.handler.disable_buttons_by_id", new_callable=AsyncMock):
            
            await employee_controls_handler(callback, state)
            
            callback.message.answer.assert_called()


class TestEdgeCases:
    """Тесты граничных случаев для callback хэндлеров"""

    @pytest.mark.asyncio
    async def test_theory_with_permission_error(self):
        """Тест: ошибка доступа при отправке PDF"""
        callback = create_mock_callback(data="case:career_dialog:theory")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("builtins.open", side_effect=PermissionError):
            
            await case_career_dialog_theory(callback, state)
            
            # Должен обработать ошибку и уведомить пользователя
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_with_exception(self):
        """Тест: исключение при перезапуске"""
        callback = create_mock_callback(data="case:career_dialog:restart")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock, side_effect=Exception("Test error")):
            
            # Должно выбросить исключение
            with pytest.raises(Exception):
                await career_controls_handler(callback, state)

    @pytest.mark.asyncio
    async def test_review_with_empty_dialogue(self):
        """Тест: анализ пустого диалога"""
        callback = create_mock_callback(data="case:career_dialog:review")
        state = create_mock_state(
            state_value=CareerChat.waiting_user,
            data={"dialogue_entries": []}
        )
        
        with patch("app.cases.career_dialog.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Диалог слишком короткий"), \
             patch("app.cases.career_dialog.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Диалог слишком короткий"), \
             patch("app.cases.career_dialog.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            
            await career_controls_handler(callback, state)
            
            # Должен обработать и отправить результат
            callback.message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_start_dialog_with_exception_in_mark_started(self):
        """Тест: исключение при вызове mark_case_started"""
        callback = create_mock_callback(data="case:career_dialog:start")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.mark_case_started", new_callable=AsyncMock, side_effect=Exception("DB error")):
            
            # Не должно быть исключения, так как оно перехватывается
            await case_career_dialog_start_dialog(callback, state)
            
            # Должно отправить сообщения
            assert callback.message.answer.call_count >= 1

    @pytest.mark.asyncio
    async def test_start_dialog_disables_previous_inline_buttons(self):
        """Тест: отключение предыдущих инлайн-кнопок при старте"""
        callback = create_mock_callback(data="case:career_dialog:start")
        callback.message.chat.id = 12345
        state = create_mock_state(
            data={"active_inline_message_id": 100}
        )
        
        with patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock) as mock_disable, \
             patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.mark_case_started", new_callable=AsyncMock):
            
            await case_career_dialog_start_dialog(callback, state)
            
            # Должен вызвать disable_buttons_by_id
            mock_disable.assert_called()

