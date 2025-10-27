"""
Тесты для клавиатур рейтингов.

Тестируемый модуль:
- app/keyboards/ratings.py

Тестируемые компоненты:
- rating_scale_inline функция
- rating_open_inline функция
- rating_comment_inline функция
"""

import pytest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.ratings import (
    rating_scale_inline,
    rating_open_inline,
    rating_comment_inline,
    CALLBACK_RATE_PREFIX,
)


class TestRatingScaleInline:
    """Тесты для функции rating_scale_inline"""

    def test_rating_scale_inline_structure(self):
        """Тест: структура клавиатуры с 10 кнопками"""
        question_key = "test_question"
        keyboard = rating_scale_inline(question_key)
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 3  # 2 ряда по 5 кнопок + главное меню
        
        # Проверяем первый ряд (кнопки 1-5)
        first_row = keyboard.inline_keyboard[0]
        assert len(first_row) == 5
        for i, button in enumerate(first_row, start=1):
            assert isinstance(button, InlineKeyboardButton)
            assert button.text == str(i)
            assert button.callback_data == f"{CALLBACK_RATE_PREFIX}set:{question_key}:{i}"
        
        # Проверяем второй ряд (кнопки 6-10 vulns)
        second_row = keyboard.inline_keyboard[1]
        assert len(second_row) == 5
        for i, button in enumerate(second_row, start=6):
            assert isinstance(button, InlineKeyboardButton)
            assert button.text == str(i)
            assert button.callback_data == f"{CALLBACK_RATE_PREFIX}set:{question_key}:{i}"
        
        # Проверяем кнопку главного меню
        menu_row = keyboard.inline_keyboard[2]
        assert len(menu_row) == 1
        assert menu_row[0].text == "🏠 Главное меню"
        assert menu_row[0].callback_data == "nav:menu"

    def test_rating_scale_inline_different_question_key(self):
        """Тест: разные question_key генерируют разные callback_data"""
        keyboard1 = rating_scale_inline("question1")
        keyboard2 = rating_scale_inline("question2")
        
        assert keyboard1.inline_keyboard[0][0].callback_data != keyboard2.inline_keyboard[0][0].callback_data
        assert "question1" in keyboard1.inline_keyboard[0][0].callback_data
        assert "question2" in keyboard2.inline_keyboard[0][0].callback_data


class TestRatingOpenInline:
    """Тесты для функции rating_open_inline"""

    def test_rating_open_inline_structure(self):
        """Тест: структура клавиатуры для начала оценки"""
        keyboard = rating_open_inline()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 1
        
        row = keyboard.inline_keyboard[0]
        assert len(row) == 1
        
        button = row[0]
        assert isinstance(button, InlineKeyboardButton)
        assert button.text == "Начать оценку ⭐"
        assert button.callback_data == f"{CALLBACK_RATE_PREFIX}open"


class TestRatingCommentInline:
    """Тесты для функции rating_comment_inline"""

    def test_rating_comment_inline_structure(self):
        """Тест: структура клавиатуры для комментария"""
        keyboard = rating_comment_inline()
        
        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) == 2
        
        # Проверяем кнопку "Пропустить"
        skip_row = keyboard.inline_keyboard[0]
        assert len(skip_row) == 1
        assert skip_row[0].text == "Пропустить"
        assert skip_row[0].callback_data == f"{CALLBACK_RATE_PREFIX}comment:skip"
        
        # Проверяем кнопку главного меню
        menu_row = keyboard.inline_keyboard[1]
        assert len(menu_row) == 1
        assert menu_row[0].text == "🏠 Главное меню"
        assert menu_row[0].callback_data == "nav:menu"


class TestRatingCallbacks:
    """Тесты для констант и callback структуры"""

    def test_callback_rate_prefix(self):
        """Тест: правильный префикс для callbacks рейтинга"""
        assert CALLBACK_RATE_PREFIX == "rate:"
        
        keyboard = rating_open_inline()
        assert keyboard.inline_keyboard[0][0].callback_data.startswith(CALLBACK_RATE_PREFIX)

