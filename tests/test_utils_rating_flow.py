"""
Тесты для утилит потока рейтингов.

Тестируемый модуль:
- app/utils/rating_flow.py

Тестируемые компоненты:
- send_survey_invitation функция
- send_intro_and_first_question функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.rating_flow import (
    send_survey_invitation,
    send_intro_and_first_question,
    INTRO_LINE,
)


class TestSendSurveyInvitation:
    """Тесты для функции send_survey_invitation"""

    @pytest.mark.asyncio
    async def test_send_survey_invitation_calls_bot(self):
        """Тест: отправка приглашения вызывает bot.send_message"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        chat_id = 12345
        user_id = 67890
        
        await send_survey_invitation(mock_bot, chat_id, user_id)
        
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        
        assert call_kwargs["chat_id"] == chat_id
        assert call_kwargs["text"] == INTRO_LINE
        assert call_kwargs["parse_mode"] == "Markdown"
        assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_send_survey_invitation_text_content(self):
        """Тест: содержимое текста приглашения"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        await send_survey_invitation(mock_bot, 12345, 67890)
        
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["text"] == INTRO_LINE
        assert "коротких вопроса" in INTRO_LINE

    @pytest.mark.asyncio
    async def test_send_survey_invitation_has_keyboard(self):
        """Тест: приглашение содержит клавиатуру"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        await send_survey_invitation(mock_bot, 12345, 67890)
        
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["reply_markup"] is not None


class TestSendIntroAndFirstQuestion:
    """Тесты для функции send_intro_and_first_question"""

    @pytest.mark.asyncio
    async def test_send_intro_and_first_question_calls_bot(self):
        """Тест: отправка первого вопроса вызывает bot.send_message"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        chat_id = 12345
        user_id = 67890
        
        with patch("app.utils.rating_flow.get_user_rating_for_question", new_callable=AsyncMock, return_value=None):
            await send_intro_and_first_question(mock_bot, chat_id, user_id)
            
            mock_bot.send_message.assert_called_once()
            call_kwargs = mock_bot.send_message.call_args.kwargs
            
            assert call_kwargs["chat_id"] == chat_id
            assert call_kwargs["parse_mode"] == "Markdown"
            assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_send_intro_and_first_question_no_previous_answer(self):
        """Тест: без предыдущего ответа"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        with patch("app.utils.rating_flow.get_user_rating_for_question", new_callable=AsyncMock, return_value=None):
            await send_intro_and_first_question(mock_bot, 12345, 67890)
            
            call_kwargs = mock_bot.send_message.call_args.kwargs
            text = call_kwargs["text"]
            assert INTRO_LINE in text
            assert "Ваш предыдущий ответ" not in text

    @pytest.mark.asyncio
    async def test_send_intro_and_first_question_with_previous_answer(self):
        """Тест: с предыдущим ответом"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        previous_answer = 7
        
        with patch("app.utils.rating_flow.get_user_rating_for_question", new_callable=AsyncMock, return_value=previous_answer):
            await send_intro_and_first_question(mock_bot, 12345, 67890)
            
            call_kwargs = mock_bot.send_message.call_args.kwargs
            text = call_kwargs["text"]
            assert INTRO_LINE in text
            assert "Ваш предыдущий ответ" in text
            assert str(previous_answer) in text

    @pytest.mark.asyncio
    async def test_send_intro_and_first_question_fetches_first_question(self):
        """Тест: получение первого вопроса из RATING_QUESTIONS"""
        from app.repositories.ratings import RATING_QUESTIONS
        
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        with patch("app.utils.rating_flow.get_user_rating_for_question", new_callable=AsyncMock, return_value=None):
            await send_intro_and_first_question(mock_bot, 12345, 67890)
            
            # Проверяем, что вызван get_user_rating_for_question с первым вопросом
            with patch("app.utils.rating_flow.get_user_rating_for_question") as mock_get:
                mock_get.return_value = None
                await send_intro_and_first_question(mock_bot, 12345, 67890)
                mock_get.assert_called_once()
                assert mock_get.call_args[0][1] == RATING_QUESTIONS[0]

    @pytest.mark.asyncio
    async def test_send_intro_and_first_question_has_keyboard(self):
        """Тест: первый вопрос содержит клавиатуру"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        with patch("app.utils.rating_flow.get_user_rating_for_question", new_callable=AsyncMock, return_value=None):
            await send_intro_and_first_question(mock_bot, 12345, 67890)
            
            call_kwargs = mock_bot.send_message.call_args.kwargs
            assert call_kwargs["reply_markup"] is not None


class TestRatingFlowIntegration:
    """Интеграционные тесты для потока рейтингов"""

    @pytest.mark.asyncio
    async def test_invitation_and_first_question_flow(self):
        """Тест: последовательность приглашения и первого вопроса"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        
        # Отправляем приглашение
        await send_survey_invitation(mock_bot, 12345, 67890)
        
        # Отправляем первый вопрос
        with patch("app.utils.rating_flow.get_user_rating_for_question", new_callable=AsyncMock, return_value=None):
            await send_intro_and_first_question(mock_bot, 12345, 67890)
        
        # Проверяем, что оба сообщения отправлены
        assert mock_bot.send_message.call_count == 2
        
        # Первое сообщение - приглашение
        first_call = mock_bot.send_message.call_args_list[0]
        assert INTRO_LINE in first_call.kwargs["text"]
        
        # Второе сообщение - первый вопрос
        second_call = mock_bot.send_message.call_args_list[1]
        assert INTRO_LINE in second_call.kwargs["text"]

