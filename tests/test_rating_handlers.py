"""
Тесты для хэндлеров рейтинга.

Тестируемый модуль:
- app/handlers/rating.py

Тестируемые хэндлеры:
- open_rating - открытие опроса через навигацию
- open_rating_from_start_button - открытие через кнопку start
- set_rating - установка оценки
- skip_comment - пропуск комментария
- receive_comment - получение текстового комментария
- _deny_rating - отказ в доступе
- _edit_or_answer - вспомогательная функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User, Chat
from aiogram.fsm.state import State

from app.handlers.rating import (
    open_rating,
    open_rating_from_start_button,
    set_rating,
    skip_comment,
    receive_comment,
    _deny_rating,
    _edit_or_answer,
    _get_question_order,
    RatingStates,
    QUESTION_TEXTS,
)
from app.keyboards.menu import CALLBACK_NAV_RATE
from app.keyboards.ratings import CALLBACK_RATE_PREFIX


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
    callback.message.edit_reply_markup = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = MagicMock()
    return callback


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


def create_mock_state(state_value=None, data: dict = None) -> FSMContext:
    """Создает мок-объект FSMContext для тестов"""
    state = AsyncMock(spec=FSMContext)
    state.get_state = AsyncMock(return_value=state_value)
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value=data or {})
    state.clear = AsyncMock()
    return state


class TestGetQuestionOrder:
    """Тесты для функции _get_question_order"""

    def test_get_question_order(self):
        """Тест: получение порядка вопросов"""
        order = _get_question_order()
        assert isinstance(order, list)
        assert len(order) == 3
        assert order == ["overall_impression", "recommend_to_colleagues", "will_help_at_work"]


class TestOpenRating:
    """Тесты для open_rating"""

    @pytest.mark.asyncio
    async def test_open_rating_allowed_with_previous_rating(self):
        """Тест: открытие рейтинга при наличии доступа и предыдущей оценки"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        
        with patch("app.handlers.rating.has_any_completed", new_callable=AsyncMock, return_value=True), \
             patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=7), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock):
            
            await open_rating(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_rating_allowed_without_previous_rating(self):
        """Тест: открытие рейтинга при наличии доступа без предыдущей оценки"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        
        with patch("app.handlers.rating.has_any_completed", new_callable=AsyncMock, return_value=True), \
             patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=None), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock):
            
            await open_rating(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_rating_not_allowed(self):
        """Тест: открытие рейтинга без доступа"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        
        with patch("app.handlers.rating.has_any_completed", new_callable=AsyncMock, return_value=False), \
             patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            
            await open_rating(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_rating_db_error(self):
        """Тест: открытие рейтинга при ошибке базы данных"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        
        with patch("app.handlers.rating.has_any_completed", new_callable=AsyncMock, side_effect=Exception("DB error")), \
             patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            
            await open_rating(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_rating_edit_fails_fallback_to_answer(self):
        """Тест: fallback на answer при ошибке edit_text"""
        callback = create_mock_callback(data=CALLBACK_NAV_RATE)
        callback.message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))
        
        with patch("app.handlers.rating.has_any_completed", new_callable=AsyncMock, return_value=True), \
             patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=None), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock):
            
            await open_rating(callback)
            
            callback.message.answer.assert_called_once()


class TestOpenRatingFromStartButton:
    """Тесты для open_rating_from_start_button"""

    @pytest.mark.asyncio
    async def test_open_rating_from_start_button_allowed(self):
        """Тест: открытие рейтинга через кнопку start при наличии доступа"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}open")
        
        with patch("app.handlers.rating.has_any_completed", new_callable=AsyncMock, return_value=True), \
             patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=None), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock):
            
            await open_rating_from_start_button(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_open_rating_from_start_button_not_allowed(self):
        """Тест: открытие рейтинга через кнопку start без доступа"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}open")
        
        with patch("app.handlers.rating.has_any_completed", new_callable=AsyncMock, return_value=False), \
             patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            
            await open_rating_from_start_button(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()


class TestSetRating:
    """Тесты для set_rating"""

    @pytest.mark.asyncio
    async def test_set_rating_first_question(self):
        """Тест: установка рейтинга для первого вопроса"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:overall_impression:7")
        state = create_mock_state()
        
        with patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=None), \
             patch("app.handlers.rating.upsert_rating", new_callable=AsyncMock), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock):
            
            await set_rating(callback, state)
            
            callback.message.edit_text.assert_called()
            callback.message.answer.assert_called()
            # callback.answer не вызывается для первых двух вопросов

    @pytest.mark.asyncio
    async def test_set_rating_second_question(self):
        """Тест: установка рейтинга для второго вопроса"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:recommend_to_colleagues:8")
        state = create_mock_state()
        
        with patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=None), \
             patch("app.handlers.rating.upsert_rating", new_callable=AsyncMock), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock):
            
            await set_rating(callback, state)
            
            callback.message.edit_text.assert_called()
            callback.message.answer.assert_called()
            # callback.answer не вызывается для первых двух вопросов

    @pytest.mark.asyncio
    async def test_set_rating_last_question(self):
        """Тест: установка рейтинга для последнего вопроса - переход к комментарию"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:will_help_at_work:9")
        state = create_mock_state()
        
        with patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=None), \
             patch("app.handlers.rating.upsert_rating", new_callable=AsyncMock), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock), \
             patch("app.handlers.rating.rating_comment_inline", new_callable=MagicMock):
            
            await set_rating(callback, state)
            
            callback.message.edit_text.assert_called()
            callback.message.answer.assert_called()
            state.set_state.assert_called_with(RatingStates.waiting_comment)
            callback.answer.assert_called()

    @pytest.mark.asyncio
    async def test_set_rating_with_previous_value(self):
        """Тест: установка рейтинга с отображением предыдущего значения"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:overall_impression:5")
        state = create_mock_state()
        
        with patch("app.handlers.rating.get_user_rating_for_question", new_callable=AsyncMock, return_value=7), \
             patch("app.handlers.rating.upsert_rating", new_callable=AsyncMock), \
             patch("app.handlers.rating.rating_scale_inline", new_callable=MagicMock):
            
            await set_rating(callback, state)
            
            callback.message.edit_text.assert_called()
            callback.message.answer.assert_called()

    @pytest.mark.asyncio
    async def test_set_rating_invalid_value_too_low(self):
        """Тест: установка невалидного рейтинга (меньше 1)"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:overall_impression:0")
        state = create_mock_state()
        
        await set_rating(callback, state)
        
        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "Некорректное значение" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_rating_invalid_value_too_high(self):
        """Тест: установка невалидного рейтинга (больше 10)"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:overall_impression:11")
        state = create_mock_state()
        
        await set_rating(callback, state)
        
        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "Некорректное значение" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_rating_invalid_format(self):
        """Тест: установка рейтинга с некорректным форматом данных"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:invalid")
        state = create_mock_state()
        
        await set_rating(callback, state)
        
        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "Некорректное значение" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_rating_invalid_non_numeric(self):
        """Тест: установка рейтинга с нечисловым значением"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}set:overall_impression:abc")
        state = create_mock_state()
        
        await set_rating(callback, state)
        
        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "Некорректное значение" in call_args[0][0]


class TestSkipComment:
    """Тесты для skip_comment"""

    @pytest.mark.asyncio
    async def test_skip_comment(self):
        """Тест: пропуск комментария"""
        callback = create_mock_callback(data=f"{CALLBACK_RATE_PREFIX}comment:skip")
        state = create_mock_state()
        
        with patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            await skip_comment(callback, state)
            
            state.clear.assert_called_once()
            callback.message.answer.assert_called_once()
            callback.answer.assert_called_once()


class TestReceiveComment:
    """Тесты для receive_comment"""

    @pytest.mark.asyncio
    async def test_receive_comment_success(self):
        """Тест: успешное получение комментария"""
        message = create_mock_message(text="Отличный бот!")
        state = create_mock_state(state_value=RatingStates.waiting_comment)
        
        with patch("app.handlers.rating.insert_rating_comment", new_callable=AsyncMock), \
             patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            
            await receive_comment(message, state)
            
            message.answer.assert_called_once()
            state.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_comment_empty_text(self):
        """Тест: получение пустого комментария"""
        message = create_mock_message(text="   ")
        state = create_mock_state(state_value=RatingStates.waiting_comment)
        
        await receive_comment(message, state)
        
        # Должно быть сообщение о необходимости отправить текст
        message.answer.assert_called_once()
        assert "текстовый комментарий" in message.answer.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_receive_comment_db_error(self):
        """Тест: обработка ошибки при сохранении комментария"""
        message = create_mock_message(text="Комментарий")
        state = create_mock_state(state_value=RatingStates.waiting_comment)
        
        with patch("app.handlers.rating.insert_rating_comment", new_callable=AsyncMock, side_effect=Exception("DB error")), \
             patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            
            await receive_comment(message, state)
            
            # Комментарий должен быть сохранен даже при ошибке
            message.answer.assert_called_once()


class TestDenyRating:
    """Тесты для _deny_rating"""

    @pytest.mark.asyncio
    async def test_deny_rating(self):
        """Тест: отказ в доступе к рейтингу"""
        callback = create_mock_callback()
        
        with patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            await _deny_rating(callback)
            
            callback.message.edit_text.assert_called_once()
            callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_deny_rating_edit_fails(self):
        """Тест: fallback на answer при ошибке edit_text"""
        callback = create_mock_callback()
        callback.message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))
        
        with patch("app.handlers.rating.get_main_menu_inline", new_callable=MagicMock):
            await _deny_rating(callback)
            
            callback.message.answer.assert_called_once()
            callback.answer.assert_called_once()


class TestEditOrAnswer:
    """Тесты для _edit_or_answer"""

    @pytest.mark.asyncio
    async def test_edit_or_answer_success(self):
        """Тест: успешное редактирование сообщения"""
        callback = create_mock_callback()
        callback.message.edit_text = AsyncMock()
        
        mock_markup = MagicMock()
        await _edit_or_answer(callback, "Test text", mock_markup)
        
        callback.message.edit_text.assert_called_once_with("Test text", reply_markup=mock_markup, parse_mode="Markdown")

    @pytest.mark.asyncio
    async def test_edit_or_answer_fallback_to_answer(self):
        """Тест: fallback на answer при ошибке edit_text"""
        callback = create_mock_callback()
        callback.message.edit_text = AsyncMock(side_effect=Exception("Edit failed"))
        
        mock_markup = MagicMock()
        await _edit_or_answer(callback, "Test text", mock_markup)
        
        callback.message.answer.assert_called_once_with("Test text", reply_markup=mock_markup, parse_mode="Markdown")


class TestQuestionTexts:
    """Тесты для константы QUESTION_TEXTS"""

    def test_question_texts_keys(self):
        """Тест: проверка наличия всех ключей вопросов"""
        assert "overall_impression" in QUESTION_TEXTS
        assert "recommend_to_colleagues" in QUESTION_TEXTS
        assert "will_help_at_work" in QUESTION_TEXTS

    def test_question_texts_values(self):
        """Тест: проверка непустых значений вопросов"""
        for key, value in QUESTION_TEXTS.items():
            assert isinstance(value, str)
            assert len(value) > 0


class TestRatingStates:
    """Тесты для класса RatingStates"""

    def test_rating_states_structure(self):
        """Тест: проверка структуры RatingStates"""
        assert hasattr(RatingStates, 'waiting_comment')
        assert isinstance(RatingStates.waiting_comment, State)

