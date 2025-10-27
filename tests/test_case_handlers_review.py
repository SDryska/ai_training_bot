"""
Тесты для функции perform_dialogue_review в хэндлерах кейсов.

Тестируемые модули:
- app/cases/career_dialog/handler.py::perform_dialogue_review
- app/cases/fb_peer/handler.py::perform_dialogue_review
- app/cases/fb_employee/handler.py::perform_dialogue_review
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.cases.career_dialog.handler import (
    perform_dialogue_review as perform_review_career,
)
from app.cases.fb_peer.handler import (
    perform_dialogue_review as perform_review_peer,
)
from app.cases.fb_employee.handler import (
    perform_dialogue_review as perform_review_employee,
)
from app.cases.career_dialog.config import CareerDialogConfig
from app.cases.fb_peer.config import FBPeerConfig
from app.cases.fb_employee.config import AIDemoConfig


class TestPerformDialogueReviewCareer:
    """Тесты для perform_dialogue_review (career_dialog)"""

    @pytest.mark.asyncio
    async def test_successful_review(self):
        """Тест: успешное рецензирование диалога"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Привет, Максим. Давай обсудим твои цели."},
            {"role": "Максим", "text": "Здравствуйте. Хорошо."},
            {"role": "Руководитель", "text": "Какие у тебя карьерные планы?"},
            {"role": "Максим", "text": "Хочу стать техническим экспертом."},
        ]
        session_id = "12345:career_dialog"
        
        # Мокаем AI ответ
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "Хороший диалог", "goodPoints": ["Открытые вопросы"], "improvementPoints": []}'
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear, \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response) as mock_send:
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            # Проверяем что AI был вызван
            mock_send.assert_called_once()
            # Проверяем что контекст был очищен
            mock_clear.assert_called_once()
            # Проверяем результат
            assert "Хороший диалог" in result
            assert "Открытые вопросы" in result

    @pytest.mark.asyncio
    async def test_review_with_empty_dialogue(self):
        """Тест: рецензирование пустого диалога"""
        dialogue_entries = []
        session_id = "12345:career_dialog"
        
        result = await perform_review_career(dialogue_entries, session_id)
        
        # Должен вернуть ошибку о коротком диалоге
        assert CareerDialogConfig.ERROR_SHORT_DIALOGUE in result

    @pytest.mark.asyncio
    async def test_review_with_whitespace_only_dialogue(self):
        """Тест: рецензирование диалога только с пробелами"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "   "},
            {"role": "Максим", "text": "\n\n"},
        ]
        session_id = "12345:career_dialog"
        
        # Мокаем extract_dialogue_text чтобы вернуть пустую строку
        with patch("app.cases.career_dialog.handler.extract_dialogue_text", return_value=""):
            result = await perform_review_career(dialogue_entries, session_id)
        
        # Должен вернуть ошибку о коротком диалоге
        assert CareerDialogConfig.ERROR_SHORT_DIALOGUE in result

    @pytest.mark.asyncio
    async def test_review_with_ai_error(self):
        """Тест: ошибка AI при рецензировании"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Привет"},
            {"role": "Максим", "text": "Здравствуйте"},
        ]
        session_id = "12345:career_dialog"
        
        # Мокаем AI ответ с ошибкой
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error = "Connection timeout"
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            # Проверяем сообщение об ошибке
            assert "AI_Error" in result or "Connection timeout" in result

    @pytest.mark.asyncio
    async def test_review_with_exception(self):
        """Тест: исключение во время рецензирования"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Текст"},
            {"role": "Максим", "text": "Ответ"},
        ]
        session_id = "12345:career_dialog"
        
        # Мокаем исключение
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, side_effect=ValueError("Test error")):
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            # Проверяем что ошибка обработана корректно
            assert "ValueError" in result or "Test error" in result

    @pytest.mark.asyncio
    async def test_review_with_malformed_ai_response(self):
        """Тест: некорректный JSON от AI"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Вопрос"},
            {"role": "Максим", "text": "Ответ"},
        ]
        session_id = "12345:career_dialog"
        
        # Мокаем AI ответ с некорректным JSON
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "Это просто текст без JSON структуры"
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            # Должен обработать fallback и вернуть какой-то результат
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_review_uses_correct_case_id(self):
        """Тест: проверка использования правильного case_id"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Диалог"},
            {"role": "Максим", "text": "Ответ"},
        ]
        session_id = "12345:career_dialog"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "OK", "goodPoints": [], "improvementPoints": []}'
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear, \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response) as mock_send:
            
            await perform_review_career(dialogue_entries, session_id)
            
            # Проверяем что используется правильный case_id
            args, kwargs = mock_send.call_args
            assert kwargs.get("case_id") == CareerDialogConfig.CASE_ID

    @pytest.mark.asyncio
    async def test_review_creates_separate_reviewer_session(self):
        """Тест: создание отдельной сессии для рецензента"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Текст"},
            {"role": "Максим", "text": "Ответ"},
        ]
        session_id = "12345:career_dialog"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "OK", "goodPoints": [], "improvementPoints": []}'
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock) as mock_clear, \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response) as mock_send:
            
            await perform_review_career(dialogue_entries, session_id)
            
            # Проверяем что рецензент использует отдельный user_id
            args, kwargs = mock_send.call_args
            reviewer_user_id = kwargs.get("user_id")
            # Рецензент должен иметь ID = оригинальный ID + 999999
            assert reviewer_user_id == 12345 + 999999


class TestPerformDialogueReviewPeer:
    """Тесты для perform_dialogue_review (fb_peer)"""

    @pytest.mark.asyncio
    async def test_successful_review_peer(self):
        """Тест: успешное рецензирование диалога с коллегой"""
        dialogue_entries = [
            {"role": "Коллега", "text": "Александр, мне нужно обсудить важный момент."},
            {"role": "Александр", "text": "Да, слушаю."},
        ]
        session_id = "67890:fb_peer"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "Конструктивный диалог", "goodPoints": ["Уважительный тон"], "improvementPoints": ["Больше конкретики"]}'
        
        with patch("app.cases.fb_peer.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_peer(dialogue_entries, session_id)
            
            assert "Конструктивный диалог" in result
            assert "Уважительный тон" in result
            assert "Больше конкретики" in result

    @pytest.mark.asyncio
    async def test_review_peer_with_empty_dialogue(self):
        """Тест: пустой диалог для fb_peer"""
        result = await perform_review_peer([], "67890:fb_peer")
        
        assert FBPeerConfig.ERROR_SHORT_DIALOGUE in result

    @pytest.mark.asyncio
    async def test_review_peer_uses_correct_prompts(self):
        """Тест: использование правильных промптов для fb_peer"""
        dialogue_entries = [
            {"role": "Коллега", "text": "Текст"},
            {"role": "Александр", "text": "Ответ"},
        ]
        session_id = "67890:fb_peer"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "OK", "goodPoints": [], "improvementPoints": []}'
        
        with patch("app.cases.fb_peer.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_peer.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response) as mock_send:
            
            await perform_review_peer(dialogue_entries, session_id)
            
            # Проверяем что используется правильный system_prompt
            args, kwargs = mock_send.call_args
            assert kwargs.get("system_prompt") == FBPeerConfig.REVIEWER_SYSTEM_PROMPT


class TestPerformDialogueReviewEmployee:
    """Тесты для perform_dialogue_review (fb_employee)"""

    @pytest.mark.asyncio
    async def test_successful_review_employee(self):
        """Тест: успешное рецензирование диалога с сотрудником"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Евгений, хочу дать тебе обратную связь."},
            {"role": "Евгений", "text": "Хорошо, я слушаю."},
        ]
        session_id = "11111:fb_employee"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "Эффективный диалог", "goodPoints": ["ПРОВД структура"], "improvementPoints": []}'
        
        with patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_employee(dialogue_entries, session_id)
            
            assert "Эффективный диалог" in result
            assert "ПРОВД структура" in result

    @pytest.mark.asyncio
    async def test_review_employee_with_long_dialogue(self):
        """Тест: рецензирование длинного диалога"""
        dialogue_entries = []
        for i in range(50):
            role = "Руководитель" if i % 2 == 0 else "Евгений"
            dialogue_entries.append({"role": role, "text": f"Реплика {i}"})
        
        session_id = "11111:fb_employee"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "Длинный диалог", "goodPoints": ["Детальность"], "improvementPoints": []}'
        
        with patch("app.cases.fb_employee.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.fb_employee.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_employee(dialogue_entries, session_id)
            
            assert "Длинный диалог" in result


class TestReviewEdgeCases:
    """Тесты граничных случаев для всех рецензентов"""

    @pytest.mark.asyncio
    async def test_review_with_special_characters_in_dialogue(self):
        """Тест: спецсимволы в диалоге"""
        dialogue_entries = [
            {"role": "Руководитель", "text": 'Текст с "кавычками" и \\слэшами\\'},
            {"role": "Максим", "text": "Ответ с !@#$% символами"},
        ]
        session_id = "12345:career_dialog"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "OK", "goodPoints": [], "improvementPoints": []}'
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            # Должен корректно обработать спецсимволы
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_review_with_cyrillic_and_emoji(self):
        """Тест: кириллица и эмодзи в диалоге"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Отличная работа! 👍"},
            {"role": "Максим", "text": "Спасибо! 😊"},
        ]
        session_id = "12345:career_dialog"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "Позитивный диалог 🎉", "goodPoints": ["Эмодзи"], "improvementPoints": []}'
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            assert "🎉" in result or "Позитивный диалог" in result

    @pytest.mark.asyncio
    async def test_review_with_none_content_in_response(self):
        """Тест: None в content ответа AI"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Текст"},
            {"role": "Максим", "text": "Ответ"},
        ]
        session_id = "12345:career_dialog"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = None
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            # Должен обработать None и вернуть какой-то результат
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_review_with_very_long_text(self):
        """Тест: очень длинный текст в диалоге"""
        long_text = "Очень длинный текст. " * 500
        dialogue_entries = [
            {"role": "Руководитель", "text": long_text},
            {"role": "Максим", "text": "Короткий ответ"},
        ]
        session_id = "12345:career_dialog"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "Длинный диалог", "goodPoints": [], "improvementPoints": []}'
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response):
            
            result = await perform_review_career(dialogue_entries, session_id)
            
            assert "Длинный диалог" in result


class TestReviewLogging:
    """Тесты логирования в функции review"""

    @pytest.mark.asyncio
    async def test_review_logs_session_info(self):
        """Тест: логирование информации о сессии"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Текст"},
            {"role": "Максим", "text": "Ответ"},
        ]
        session_id = "12345:career_dialog"
        
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = '{"overall": "OK", "goodPoints": [], "improvementPoints": []}'
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, return_value=mock_response), \
             patch("app.cases.career_dialog.handler.logger") as mock_logger:
            
            await perform_review_career(dialogue_entries, session_id)
            
            # Проверяем что логирование было вызвано
            assert mock_logger.info.called or mock_logger.debug.called

    @pytest.mark.asyncio
    async def test_review_logs_errors(self):
        """Тест: логирование ошибок"""
        dialogue_entries = [
            {"role": "Руководитель", "text": "Текст"},
            {"role": "Максим", "text": "Ответ"},
        ]
        session_id = "12345:career_dialog"
        
        with patch("app.cases.career_dialog.handler.clear_case_conversations", new_callable=AsyncMock), \
             patch("app.cases.career_dialog.handler.send_reviewer_message", new_callable=AsyncMock, side_effect=Exception("Test error")), \
             patch("app.cases.career_dialog.handler.logger") as mock_logger:
            
            await perform_review_career(dialogue_entries, session_id)
            
            # Проверяем что ошибка была залогирована
            assert mock_logger.error.called

