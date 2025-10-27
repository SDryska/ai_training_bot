"""
Тесты для клавиатур меню.

Тестируемый модуль:
- app/keyboards/menu.py

Тестируемые компоненты:
- get_main_menu_inline функция
- get_back_menu_inline функция
- get_case_controls_inline функция
- get_case_after_review_inline функция
- get_case_description_inline функция
- get_disabled_buttons_markup функция
- disable_previous_buttons функция
- remove_reply_keyboard функция
- disable_buttons_by_id функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.keyboards.menu import (
    get_main_menu_inline,
    get_back_menu_inline,
    get_case_controls_inline,
    get_case_after_review_inline,
    get_case_after_review_inline_by_case,
    get_case_controls_inline_by_case,
    get_case_description_inline,
    get_disabled_buttons_markup,
    disable_previous_buttons,
    remove_reply_keyboard,
    disable_buttons_by_id,
    MENU_ITEMS,
    CALLBACK_PREFIX_MENU,
    CALLBACK_NAV_MENU,
    CALLBACK_NAV_RATE,
    CALLBACK_NAV_FAQ,
)


class TestGetMainMenuInline:
    """Тесты для функции get_main_menu_inline"""

    def test_get_main_menu_inline_structure(self):
        """Тест: структура главного меню"""
        keyboard = get_main_menu_inline()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == len(MENU_ITEMS) + 1  # Все кейсы + кнопки помощи
        
        # Проверяем, что каждый кейс имеет свою кнопку
        for i, item in enumerate(MENU_ITEMS):
            row = keyboard.inline_keyboard[i]
            assert len(row) == 1
            assert row[0].text == item["title"]
            assert row[0].callback_data == f"{CALLBACK_PREFIX_MENU}{item['id']}"
        
        # Проверяем кнопки помощи
        help_row = keyboard.inline_keyboard[-1]
        assert len(help_row) == 2
        assert help_row[0].text == "❓ FAQ"
        assert help_row[0].callback_data == CALLBACK_NAV_FAQ
        assert help_row[1].text == "⭐ Оценить бота"
        assert help_row[1].callback_data == CALLBACK_NAV_RATE


class TestGetBackMenuInline:
    """Тесты для функции get_back_menu_inline"""

    def test_get_back_menu_inline_structure(self):
        """Тест: структура кнопки возврата в меню"""
        keyboard = get_back_menu_inline()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 1
        
        row = keyboard.inline_keyboard[0]
        assert len(row) == 1
        assert row[0].text == "🏠 Главное меню"
        assert row[0].callback_data == CALLBACK_NAV_MENU


class TestGetCaseControlsInline:
    """Тесты для функции get_case_controls_inline"""

    def test_get_case_controls_inline_structure(self):
        """Тест: структура контрольных кнопок кейса"""
        keyboard = get_case_controls_inline()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2
        
        # Проверяем первый ряд с кнопками действий
        first_row = keyboard.inline_keyboard[0]
        assert len(first_row) == 2
        assert "🔄" in first_row[0].text
        assert "📊" in first_row[1].text
        
        # Проверяем кнопку возврата в меню
        second_row = keyboard.inline_keyboard[1]
        assert len(second_row) == 1
        assert second_row[0].text == "🏠 Главное меню"


class TestGetCaseAfterReviewInline:
    """Тесты для функции get_case_after_review_inline"""

    def test_get_case_after_review_inline_structure(self):
        """Тест: структура клавиатуры после рецензии"""
        keyboard = get_case_after_review_inline()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2
        
        # Проверяем кнопку повторной попытки
        first_row = keyboard.inline_keyboard[0]
        assert len(first_row) == 1
        assert "🔄" in first_row[0].text
        
        # Проверяем кнопку возврата в меню
        second_row = keyboard.inline_keyboard[1]
        assert len(second_row) == 1
        assert second_row[0].text == "🏠 Главное меню"


class TestGetCaseAfterReviewInlineByCase:
    """Тесты для функции get_case_after_review_inline_by_case"""

    def test_get_case_after_review_inline_by_case_structure(self):
        """Тест: структура клавиатуры после рецензии для конкретного кейса"""
        case_id = "test_case"
        keyboard = get_case_after_review_inline_by_case(case_id)
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2
        
        # Проверяем callback с правильным case_id
        first_row = keyboard.inline_keyboard[0]
        assert f"case:{case_id}:restart" in first_row[0].callback_data

    def test_get_case_after_review_inline_by_case_different_ids(self):
        """Тест: разные case_id генерируют разные callbacks"""
        keyboard1 = get_case_after_review_inline_by_case("case1")
        keyboard2 = get_case_after_review_inline_by_case("case2")
        
        assert keyboard1.inline_keyboard[0][0].callback_data != keyboard2.inline_keyboard[0][0].callback_data


class TestGetCaseControlsInlineByCase:
    """Тесты для функции get_case_controls_inline_by_case"""

    def test_get_case_controls_inline_by_case_structure(self):
        """Тест: структура контрольных кнопок для конкретного кейса"""
        case_id = "test_case"
        keyboard = get_case_controls_inline_by_case(case_id)
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 2
        
        # Проверяем callbacks с правильным case_id
        first_row = keyboard.inline_keyboard[0]
        assert f"case:{case_id}:restart" in first_row[0].callback_data
        assert f"case:{case_id}:review" in first_row[1].callback_data


class TestGetCaseDescriptionInline:
    """Тесты для функции get_case_description_inline"""

    def test_get_case_description_inline_structure(self):
        """Тест: структура клавиатуры описания кейса"""
        case_id = "test_case"
        keyboard = get_case_description_inline(case_id)
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 3
        
        # Проверяем кнопку начала тренировки
        first_row = keyboard.inline_keyboard[0]
        assert len(first_row) == 1
        assert "🎬" in first_row[0].text
        assert f"case:{case_id}:start" in first_row[0].callback_data
        
        # Проверяем кнопку изучения теории
        second_row = keyboard.inline_keyboard[1]
        assert len(second_row) == 1
        assert "📚" in second_row[0].text
        assert f"case:{case_id}:theory" in second_row[0].callback_data
        
        # Проверяем кнопку возврата в меню
        third_row = keyboard.inline_keyboard[2]
        assert len(third_row) == 1
        assert third_row[0].text == "🏠 Главное меню"


class TestGetDisabledButtonsMarkup:
    """Тесты для функции get_disabled_buttons_markup"""

    def test_get_disabled_buttons_markup_structure(self):
        """Тест: структура пустой клавиатуры"""
        keyboard = get_disabled_buttons_markup()
        
        assert keyboard is not None
        assert len(keyboard.inline_keyboard) == 0


class TestDisablePreviousButtons:
    """Тесты для функции disable_previous_buttons"""

    @pytest.mark.asyncio
    async def test_disable_previous_buttons_success(self):
        """Тест: успешное отключение кнопок"""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.message_id = 123
        mock_bot = MagicMock()
        mock_bot.edit_message_reply_markup = AsyncMock()
        mock_message.bot = mock_bot
        
        await disable_previous_buttons(mock_message)
        
        mock_bot.edit_message_reply_markup.assert_called_once()
        call_kwargs = mock_bot.edit_message_reply_markup.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        assert call_kwargs["message_id"] == 123

    @pytest.mark.asyncio
    async def test_disable_previous_buttons_with_bot_param(self):
        """Тест: отключение кнопок с явным bot параметром"""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.message_id = 123
        mock_bot = MagicMock()
        mock_bot.edit_message_reply_markup = AsyncMock()
        
        await disable_previous_buttons(mock_message, bot=mock_bot)
        
        mock_bot.edit_message_reply_markup.assert_called_once()

    @pytest.mark.asyncio
    async def test_disable_previous_buttons_exception_handling(self):
        """Тест: обработка исключений при отключении кнопок"""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.message_id = 123
        mock_bot = MagicMock()
        mock_bot.edit_message_reply_markup = AsyncMock(side_effect=Exception("Edit error"))
        mock_message.bot = mock_bot
        
        # Не должно быть исключения
        await disable_previous_buttons(mock_message)

    @pytest.mark.asyncio
    async def test_disable_previous_buttons_no_message(self):
        """Тест: отключение кнопок когда сообщения нет"""
        # Не должно быть исключения
        await disable_previous_buttons(None)


class TestRemoveReplyKeyboard:
    """Тесты для функции remove_reply_keyboard"""

    @pytest.mark.asyncio
    async def test_remove_reply_keyboard_success(self):
        """Тест: успешное удаление reply клавиатуры"""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.bot = MagicMock()
        mock_tmp_message = MagicMock()
        mock_tmp_message.chat.id = 12345
        mock_tmp_message.message_id = 456
        mock_message.answer = AsyncMock(return_value=mock_tmp_message)
        mock_message.bot.delete_message = AsyncMock()
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await remove_reply_keyboard(mock_message)
        
        # Проверяем, что были вызваны оба метода
        assert mock_message.answer.call_count == 1
        assert mock_message.bot.delete_message.call_count == 1

    @pytest.mark.asyncio
    async def test_remove_reply_keyboard_exception_handling(self):
        """Тест: обработка исключений при удалении клавиатуры"""
        mock_message = MagicMock()
        mock_message.chat.id = 12345
        mock_message.bot = MagicMock()
        mock_message.bot.send_message = AsyncMock(side_effect=Exception("Send error"))
        
        # Не должно быть исключения
        await remove_reply_keyboard(mock_message)


class TestDisableButtonsById:
    """Тесты для функции disable_buttons_by_id"""

    @pytest.mark.asyncio
    async def test_disable_buttons_by_id_success(self):
        """Тест: успешное отключение кнопок по ID"""
        mock_bot = MagicMock()
        mock_bot.edit_message_reply_markup = AsyncMock()
        
        await disable_buttons_by_id(mock_bot, 12345, 123)
        
        mock_bot.edit_message_reply_markup.assert_called_once()
        call_kwargs = mock_bot.edit_message_reply_markup.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        assert call_kwargs["message_id"] == 123

    @pytest.mark.asyncio
    async def test_disable_buttons_by_id_exception_handling(self):
        """Тест: обработка исключений при отключении кнопок по ID"""
        mock_bot = MagicMock()
        mock_bot.edit_message_reply_markup = AsyncMock(side_effect=Exception("Edit error"))
        
        # Не должно быть исключения
        await disable_buttons_by_id(mock_bot, 12345, 123)

