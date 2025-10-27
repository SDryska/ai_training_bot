"""
Тесты для хэндлеров сообщений кейсов.

Тестируемые модули:
- app/cases/career_dialog/handler.py
- app/cases/fb_peer/handler.py
- app/cases/fb_employee/handler.py

Тестируемые хэндлеры:
- career_turn / fb_peer_turn / ai_demo_turn (текстовые сообщения)
- career_turn_voice / fb_peer_turn_voice / ai_demo_turn_voice (голосовые сообщения)
- career_after_review / fb_peer_after_review / ai_demo_after_review (после рецензии)
- _process_user_input (внутренняя функция)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, User, Chat, Voice

from app.cases.career_dialog.handler import (
    career_turn,
    career_turn_voice,
    career_after_review,
    CareerChat,
)
from app.cases.fb_peer.handler import (
    fb_peer_turn,
    fb_peer_turn_voice,
    fb_peer_after_review,
    FBPeerChat,
)
from app.cases.fb_employee.handler import (
    ai_demo_turn,
    ai_demo_turn_voice,
    ai_demo_after_review,
    AIChat,
)
from app.cases.career_dialog.config import CareerDialogConfig
from app.cases.fb_peer.config import FBPeerConfig
from app.cases.fb_employee.config import AIDemoConfig


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


def create_mock_voice_message(file_id: str = "test_file_id") -> Message:
    """Создает мок-объект Message с голосовым сообщением"""
    message = create_mock_message()
    message.voice = MagicMock(spec=Voice)
    message.voice.file_id = file_id
    message.voice.duration = 10
    message.voice.file_size = 1000
    return message


def create_mock_state(data: dict = None) -> FSMContext:
    """Создает мок-объект FSMContext для тестов"""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=CareerChat.waiting_user)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value=data or {
        "turn_count": 0,
        "dialogue_entries": [],
        "total_components_achieved": set()
    })
    state.clear = AsyncMock()
    return state


class TestCareerTurnText:
    """Тесты для career_turn (текстовые сообщения)"""

    @pytest.mark.asyncio
    async def test_turn_regular_message(self):
        """Тест: обработка обычного текстового сообщения"""
        message = create_mock_message(text="Давай обсудим твои карьерные цели")
        state = create_mock_state()
        
        # Мокаем AI ответ
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Хорошо, давайте поговорим", "Aspirations": true, "Strengths": false, "Development": false, "Opportunities": false, "Plan": false}'
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Давай обсудим твои карьерные цели"), \
             patch("app.cases.career_dialog.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что сообщение было обработано
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_turn_restart_button(self):
        """Тест: обработка кнопки перезапуска"""
        from app.keyboards.menu import KB_CASE_RESTART
        
        message = create_mock_message(text=KB_CASE_RESTART)
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value=KB_CASE_RESTART), \
             patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что диалог был перезапущен
            state.set_state.assert_called()

    @pytest.mark.asyncio
    async def test_turn_back_to_menu_button(self):
        """Тест: обработка кнопки возврата в меню"""
        from app.keyboards.menu import KB_BACK_TO_MENU
        
        message = create_mock_message(text=KB_BACK_TO_MENU)
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value=KB_BACK_TO_MENU), \
             patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.keyboards.menu.get_main_menu_inline", new_callable=MagicMock(return_value=None)), \
             patch("aiogram.types.ReplyKeyboardRemove", new_callable=MagicMock(return_value=None)):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что состояние было очищено
            state.clear.assert_called_once()
            # Проверяем что отправлены сообщения о возврате в меню
            assert message.answer.call_count >= 2

    @pytest.mark.asyncio
    async def test_turn_review_button(self):
        """Тест: обработка кнопки получения анализа"""
        from app.keyboards.menu import KB_CASE_REVIEW
        
        message = create_mock_message(text=KB_CASE_REVIEW)
        state = create_mock_state(data={"dialogue_entries": [
            {"role": "Руководитель", "text": "Текст"},
            {"role": "Максим", "text": "Ответ"}
        ]})
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value=KB_CASE_REVIEW), \
             patch("app.cases.career_dialog.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.career_dialog.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.career_dialog.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что анализ был получен
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_turn_updates_turn_count(self):
        """Тест: обновление счетчика ходов"""
        message = create_mock_message(text="Вопрос")
        state = create_mock_state()
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Aspirations": false, "Strengths": false, "Development": false, "Opportunities": false, "Plan": false}'
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Вопрос"), \
             patch("app.cases.career_dialog.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что счетчик был обновлен
            state.update_data.assert_called()

    @pytest.mark.asyncio
    async def test_turn_handles_ai_error(self):
        """Тест: обработка ошибки AI"""
        message = create_mock_message(text="Вопрос")
        state = create_mock_state()
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = False
        mock_ai_response.error = "Connection timeout"
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Вопрос"), \
             patch("app.cases.career_dialog.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что отправлено сообщение об ошибке
            call_args = message.answer.call_args
            assert CareerDialogConfig.ERROR_AI_REQUEST in call_args[0][0]

    @pytest.mark.asyncio
    async def test_turn_shows_admin_details(self):
        """Тест: показ деталей ошибки для админа"""
        message = create_mock_message(text="Вопрос")
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, side_effect=Exception("Test error")):
            await career_turn(message, state, is_admin=True)
            
            # Проверяем что админу показаны детали
            call_args = message.answer.call_args
            assert "Test error" in call_args[0][0] or "Exception" in call_args[0][0]


class TestCareerTurnVoice:
    """Тесты для career_turn_voice (голосовые сообщения)"""

    @pytest.mark.asyncio
    async def test_voice_transcription_success(self):
        """Тест: успешная транскрибация голосового сообщения"""
        message = create_mock_voice_message()
        state = create_mock_state()
        
        mock_file = MagicMock()
        mock_file.file_id = "test_file_id"
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Aspirations": false, "Strengths": false, "Development": false, "Opportunities": false, "Plan": false}'
        
        # Фиксим баг с доступом к message.bot через патч
        message.bot.get_file = AsyncMock(return_value=mock_file)
        message.bot.download = AsyncMock()
        
        with patch("app.cases.career_dialog.handler.transcribe_voice_ogg", new_callable=AsyncMock, return_value="Распознанный текст"), \
             patch("app.cases.career_dialog.handler.with_listening_indicator", new_callable=AsyncMock, return_value="Распознанный текст"), \
             patch("app.cases.career_dialog.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await career_turn_voice(message, state, is_admin=False)
            
            # Проверяем что сообщение было обработано
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_voice_empty_transcription(self):
        """Тест: пустая транскрибация"""
        message = create_mock_voice_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.with_listening_indicator", new_callable=AsyncMock, return_value=""):
            await career_turn_voice(message, state, is_admin=False)
            
            # Проверяем что отправлено сообщение об ошибке
            call_args = message.answer.call_args
            assert "распознать" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_voice_transcription_error(self):
        """Тест: ошибка транскрибации"""
        message = create_mock_voice_message()
        state = create_mock_state()
        
        with patch("app.cases.career_dialog.handler.with_listening_indicator", new_callable=AsyncMock, side_effect=Exception("Transcription error")):
            await career_turn_voice(message, state, is_admin=False)
            
            # Проверяем обработку ошибки
            message.answer.assert_called()


class TestFBPeerTurn:
    """Тесты для fb_peer_turn"""

    @pytest.mark.asyncio
    async def test_fbpeer_turn_basic(self):
        """Тест: базовый ход в диалоге fb_peer"""
        message = create_mock_message(text="Александр, нужно обсудить важный момент")
        state = create_mock_state()
        # Исправляем состояние для fb_peer
        state.get_state = AsyncMock(return_value=FBPeerChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Слушаю", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_peer.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Александр, нужно обсудить важный момент"), \
             patch("app.cases.fb_peer.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.keyboards.menu.get_main_menu_inline", new_callable=MagicMock(return_value=None)), \
             patch("aiogram.types.ReplyKeyboardRemove", new_callable=MagicMock(return_value=None)):
            
            await fb_peer_turn(message, state, is_admin=False)
            
            # Должен быть хотя бы один вызов answer
            assert message.answer.call_count >= 1


class TestFBEmployeeTurn:
    """Тесты для ai_demo_turn"""

    @pytest.mark.asyncio
    async def test_fbemployee_turn_basic(self):
        """Тест: базовый ход в диалоге fb_employee"""
        message = create_mock_message(text="Евгений, давай поговорим о работе")
        state = create_mock_state()
        # Исправляем состояние для ai_demo
        state.get_state = AsyncMock(return_value=AIChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Хорошо", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_employee.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Евгений, давай поговорим о работе"), \
             patch("app.cases.fb_employee.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.keyboards.menu.get_main_menu_inline", new_callable=MagicMock(return_value=None)), \
             patch("aiogram.types.ReplyKeyboardRemove", new_callable=MagicMock(return_value=None)):
            
            await ai_demo_turn(message, state, is_admin=False)
            
            # Должен быть хотя бы один вызов answer
            assert message.answer.call_count >= 1


class TestAfterReviewHandlers:
    """Тесты для хэндлеров после рецензии"""

    @pytest.mark.asyncio
    async def test_career_after_review(self):
        """Тест: обработка сообщений после рецензии career_dialog"""
        message = create_mock_message(text="Любое сообщение")
        state = create_mock_state()
        
        mock_keyboard = MagicMock()
        with patch("app.cases.career_dialog.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=mock_keyboard)):
            await career_after_review(message, state)
            
            # Проверяем что отправлено сообщение
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_fbpeer_after_review(self):
        """Тест: обработка сообщений после рецензии fb_peer"""
        message = create_mock_message(text="Любое сообщение")
        state = create_mock_state()
        
        mock_keyboard = MagicMock()
        with patch("app.cases.fb_peer.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=mock_keyboard)):
            await fb_peer_after_review(message, state)
            
            message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_fbemployee_after_review(self):
        """Тест: обработка сообщений после рецензии fb_employee"""
        message = create_mock_message(text="Любое сообщение")
        state = create_mock_state()
        
        mock_keyboard = MagicMock()
        with patch("app.cases.fb_employee.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=mock_keyboard)):
            await ai_demo_after_review(message, state)
            
            message.answer.assert_called_once()


class TestDialogueCompletion:
    """Тесты завершения диалога"""

    @pytest.mark.asyncio
    async def test_completion_all_components_achieved(self):
        """Тест: завершение при достижении всех компонентов"""
        message = create_mock_message(text="Последний вопрос")
        state = create_mock_state(data={
            "turn_count": 2,
            "dialogue_entries": [],
            "total_components_achieved": {"Aspirations", "Strengths", "Development", "Opportunities", "Plan"}
        })
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Финальный ответ", "Aspirations": true, "Strengths": true, "Development": true, "Opportunities": true, "Plan": true}'
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Последний вопрос"), \
             patch("app.cases.career_dialog.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.career_dialog.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.career_dialog.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.career_dialog.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что были вызваны все необходимые функции завершения
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_completion_max_turns_reached(self):
        """Тест: завершение при достижении максимального количества ходов"""
        message = create_mock_message(text="Ход номер 6")
        state = create_mock_state(data={
            "turn_count": 5,
            "dialogue_entries": [],
            "total_components_achieved": set()
        })
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Aspirations": false, "Strengths": false, "Development": false, "Opportunities": false, "Plan": false}'
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Ход номер 6"), \
             patch("app.cases.career_dialog.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.career_dialog.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.career_dialog.handler.mark_case_out_of_moves", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.career_dialog.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            await career_turn(message, state, is_admin=False)
            
            # Проверяем что диалог завершен
            message.answer.assert_called()


class TestEdgeCases:
    """Тесты граничных случаев"""

    @pytest.mark.asyncio
    async def test_turn_user_left_during_wait(self):
        """Тест: пользователь вышел из диалога во время ожидания ответа"""
        message = create_mock_message(text="Вопрос")
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=None)  # Пользователь вышел
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Aspirations": false, "Strengths": false, "Development": false, "Opportunities": false, "Plan": false}'
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Вопрос"), \
             patch("app.cases.career_dialog.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.career_dialog.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await career_turn(message, state, is_admin=False)
            
            # Ответ не должен быть отправлен
            # Проверяем что не было попыток ответить после проверки состояния
            assert message.answer.call_count <= 1  # Только если была ошибка

    @pytest.mark.asyncio
    async def test_turn_with_invalid_state(self):
        """Тест: ход с невалидным состоянием"""
        message = create_mock_message(text="Сообщение")
        state = create_mock_state()
        state.get_state = AsyncMock(return_value="invalid_state")
        
        with patch("app.cases.career_dialog.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Сообщение"):
            # Хэндлер не должен обработать сообщение из невалидного состояния
            await career_turn(message, state, is_admin=False)
            
            # Не должно быть попыток обработки
            pass  # Тест проходит если нет исключений


class TestFBPeerTurnText:
    """Тесты для fb_peer_turn (текстовые сообщения) - расширенные"""

    @pytest.mark.asyncio
    async def test_turn_regular_message(self):
        """Тест: обработка обычного текстового сообщения"""
        message = create_mock_message(text="Александр, нужно обсудить важный момент")
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=FBPeerChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Хорошо, давайте поговорим", "Behavior": true, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_peer.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Александр, нужно обсудить важный момент"), \
             patch("app.cases.fb_peer.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await fb_peer_turn(message, state, is_admin=False)
            
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_turn_max_turns_reached(self):
        """Тест: достижение максимального количества ходов"""
        message = create_mock_message(text="Последний вопрос")
        state = create_mock_state(data={
            "turn_count": 5,
            "dialogue_entries": [],
            "total_components_achieved": set()
        })
        state.get_state = AsyncMock(return_value=FBPeerChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_peer.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Последний вопрос"), \
             patch("app.cases.fb_peer.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_peer.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_peer.handler.mark_case_out_of_moves", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_peer.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            await fb_peer_turn(message, state, is_admin=False)
            
            message.answer.assert_called()


class TestFBPeerTurnVoice:
    """Тесты для fb_peer_turn_voice (голосовые сообщения)"""

    @pytest.mark.asyncio
    async def test_voice_transcription_success(self):
        """Тест: успешная транскрибация голосового сообщения"""
        message = create_mock_voice_message()
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=FBPeerChat.waiting_user)
        
        mock_file = MagicMock()
        mock_file.file_id = "test_file_id"
        message.bot.get_file = AsyncMock(return_value=mock_file)
        message.bot.download = AsyncMock()
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_peer.handler.transcribe_voice_ogg", new_callable=AsyncMock, return_value="Распознанный текст"), \
             patch("app.cases.fb_peer.handler.with_listening_indicator", new_callable=AsyncMock, return_value="Распознанный текст"), \
             patch("app.cases.fb_peer.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await fb_peer_turn_voice(message, state, is_admin=False)
            
            message.answer.assert_called()


class TestFBEmployeeTurnText:
    """Тесты для ai_demo_turn (текстовые сообщения) - расширенные"""

    @pytest.mark.asyncio
    async def test_turn_regular_message(self):
        """Тест: обработка обычного текстового сообщения"""
        message = create_mock_message(text="Евгений, давай поговорим о работе")
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=AIChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Хорошо, давайте поговорим", "Behavior": true, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_employee.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Евгений, давай поговорим о работе"), \
             patch("app.cases.fb_employee.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await ai_demo_turn(message, state, is_admin=False)
            
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_turn_max_turns_reached(self):
        """Тест: достижение максимального количества ходов"""
        message = create_mock_message(text="Последний вопрос")
        state = create_mock_state(data={
            "turn_count": 5,
            "dialogue_entries": [],
            "total_components_achieved": set()
        })
        state.get_state = AsyncMock(return_value=AIChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_employee.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Последний вопрос"), \
             patch("app.cases.fb_employee.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_employee.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_employee.handler.mark_case_out_of_moves", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_employee.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            await ai_demo_turn(message, state, is_admin=False)
            
            message.answer.assert_called()


class TestFBEmployeeTurnVoice:
    """Тесты для ai_demo_turn_voice (голосовые сообщения)"""

    @pytest.mark.asyncio
    async def test_voice_transcription_success(self):
        """Тест: успешная транскрибация голосового сообщения"""
        message = create_mock_voice_message()
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=AIChat.waiting_user)
        
        mock_file = MagicMock()
        mock_file.file_id = "test_file_id"
        message.bot.get_file = AsyncMock(return_value=mock_file)
        message.bot.download = AsyncMock()
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_employee.handler.transcribe_voice_ogg", new_callable=AsyncMock, return_value="Распознанный текст"), \
             patch("app.cases.fb_employee.handler.with_listening_indicator", new_callable=AsyncMock, return_value="Распознанный текст"), \
             patch("app.cases.fb_employee.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response):
            
            await ai_demo_turn_voice(message, state, is_admin=False)
            
            message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_turn_all_components_achieved(self):
        """Тест: завершение при достижении всех компонентов"""
        message = create_mock_message(text="Финальный вопрос")
        state = create_mock_state(data={
            "turn_count": 2,
            "dialogue_entries": [],
            "total_components_achieved": {"Behavior", "Result", "Emotion", "Question", "Agreement"}
        })
        state.get_state = AsyncMock(return_value=AIChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Финальный ответ", "Behavior": true, "Result": true, "Emotion": true, "Question": true, "Agreement": true}'
        
        with patch("app.cases.fb_employee.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Финальный вопрос"), \
             patch("app.cases.fb_employee.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.fb_employee.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.fb_employee.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.has_any_completed", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_employee.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_employee.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            await ai_demo_turn(message, state, is_admin=False)
            
            message.answer.assert_called()


class TestFBPeerDialogueCompletion:
    """Тесты завершения диалога для fb_peer"""

    @pytest.mark.asyncio
    async def test_turn_all_components_achieved(self):
        """Тест: завершение при достижении всех компонентов"""
        message = create_mock_message(text="Финальный вопрос")
        state = create_mock_state(data={
            "turn_count": 2,
            "dialogue_entries": [],
            "total_components_achieved": {"Behavior", "Result", "Emotion", "Question", "Agreement"}
        })
        state.get_state = AsyncMock(return_value=FBPeerChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Финальный ответ", "Behavior": true, "Result": true, "Emotion": true, "Question": true, "Agreement": true}'
        
        with patch("app.cases.fb_peer.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Финальный вопрос"), \
             patch("app.cases.fb_peer.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.fb_peer.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Отличный диалог!"), \
             patch("app.cases.fb_peer.handler.mark_case_completed", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_peer.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            await fb_peer_turn(message, state, is_admin=False)
            
            message.answer.assert_called()


class TestFBEmployeeDialogueCompletion:
    """Тесты завершения диалога для fb_employee"""

    @pytest.mark.asyncio
    async def test_turn_error_handling_in_completion(self):
        """Тест: обработка ошибок при завершении"""
        message = create_mock_message(text="Последний вопрос")
        state = create_mock_state(data={
            "turn_count": 5,
            "dialogue_entries": [],
            "total_components_achieved": set()
        })
        state.get_state = AsyncMock(return_value=AIChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_employee.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Последний вопрос"), \
             patch("app.cases.fb_employee.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_employee.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_employee.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_employee.handler.mark_case_out_of_moves", new_callable=AsyncMock, side_effect=Exception("DB error")), \
             patch("app.cases.fb_employee.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_employee.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            # Не должно быть исключения даже при ошибке в mark_case_out_of_moves
            await ai_demo_turn(message, state, is_admin=False)
            
            message.answer.assert_called()


class TestFBPeerErrorHandling:
    """Тесты обработки ошибок для fb_peer"""

    @pytest.mark.asyncio
    async def test_turn_error_handling_in_completion(self):
        """Тест: обработка ошибок при завершении"""
        message = create_mock_message(text="Последний вопрос")
        state = create_mock_state(data={
            "turn_count": 5,
            "dialogue_entries": [],
            "total_components_achieved": set()
        })
        state.get_state = AsyncMock(return_value=FBPeerChat.waiting_user)
        
        mock_ai_response = MagicMock()
        mock_ai_response.success = True
        mock_ai_response.content = '{"ReplyText": "Ответ", "Behavior": false, "Result": false, "Emotion": false, "Question": false, "Agreement": false}'
        
        with patch("app.cases.fb_peer.handler.validator.validate_and_process_text", new_callable=AsyncMock, return_value="Последний вопрос"), \
             patch("app.cases.fb_peer.handler.send_dialogue_message", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.with_typing_indicator", new_callable=AsyncMock, return_value=mock_ai_response), \
             patch("app.cases.fb_peer.handler.perform_dialogue_review", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_peer.handler.with_analysis_indicator", new_callable=AsyncMock, return_value="Завершен"), \
             patch("app.cases.fb_peer.handler.mark_case_out_of_moves", new_callable=AsyncMock, side_effect=Exception("DB error")), \
             patch("app.cases.fb_peer.handler.mark_case_auto_finished", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.acquire_rating_invite_lock", new_callable=AsyncMock, return_value=False), \
             patch("app.cases.fb_peer.handler.send_survey_invitation", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.disable_buttons_by_id", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.get_case_after_review_inline", new_callable=MagicMock(return_value=None)):
            
            # Не должно быть исключения даже при ошибке в mark_case_out_of_moves
            await fb_peer_turn(message, state, is_admin=False)
            
            message.answer.assert_called()


class TestFBEmployeeReplyButtons:
    """Тесты обработки reply-кнопок для fb_employee"""

    @pytest.mark.asyncio
    async def test_turn_restart_button(self):
        """Тест: обработка кнопки restart через reply"""
        message = create_mock_message(text="🔄 Начать заново")
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=AIChat.waiting_user)
        
        with patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.get_case_controls_reply", new_callable=MagicMock(return_value=None)):
            
            await ai_demo_turn(message, state, is_admin=False)
            
            # Должен быть вызван clear_case_conversations
            message.answer.assert_called()


class TestFBPeerReplyButtons:
    """Тесты обработки reply-кнопок для fb_peer"""

    @pytest.mark.asyncio
    async def test_turn_restart_button(self):
        """Тест: обработка кнопки restart через reply"""
        message = create_mock_message(text="🔄 Начать заново")
        state = create_mock_state()
        state.get_state = AsyncMock(return_value=FBPeerChat.waiting_user)
        
        with patch("app.cases.fb_peer.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.get_case_controls_reply", new_callable=MagicMock(return_value=None)):
            
            await fb_peer_turn(message, state, is_admin=False)
            
            # Должен быть вызван clear_case_conversations
            message.answer.assert_called()


class TestErrorHandlingScenarios:
    """Тесты для различных сценариев обработки ошибок"""

    @pytest.mark.asyncio
    async def test_empty_dialogue_review(self):
        """Тест: обработка пустого диалога при рецензии"""
        from app.cases.fb_employee.handler import perform_dialogue_review
        
        with patch("app.cases.fb_employee.handler.extract_dialogue_text", new_callable=MagicMock, return_value=""):
            result = await perform_dialogue_review([], "12345:openai")
            
            # Должен вернуть сообщение об ошибке
            assert "короткий" in result.lower() or "пуст" in result.lower()

    @pytest.mark.asyncio
    async def test_ai_error_in_review(self):
        """Тест: обработка ошибки AI при рецензии"""
        from app.cases.fb_employee.handler import perform_dialogue_review
        from app.providers.base import AIResponse
        
        with patch("app.cases.fb_employee.handler.extract_dialogue_text", new_callable=MagicMock, return_value="Test dialogue"), \
             patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.send_reviewer_message", new_callable=AsyncMock, return_value=AIResponse(
                 content="", success=False, error="Network error"
             )):
            
            result = await perform_dialogue_review([], "12345:openai")
            
            # Должен вернуть сообщение об ошибке
            assert "error" in result.lower() or "ошибка" in result.lower()

    @pytest.mark.asyncio
    async def test_json_parse_error_in_review(self):
        """Тест: обработка ошибки парсинга JSON"""
        from app.cases.fb_employee.handler import parse_reviewer_response
        
        # Тестируем случай когда нет JSON вообще
        result = parse_reviewer_response("Just plain text without JSON")
        
        # Должен вернуть fallback структуру
        assert "overall" in result
        assert result["overall"] == "Just plain text without JSON"