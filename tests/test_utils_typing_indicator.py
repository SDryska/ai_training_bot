"""
Тесты для утилит индикаторов печатания.

Тестируемый модуль:
- app/utils/typing_indicator.py

Тестируемые компоненты:
- TypingIndicator класс
- with_typing_indicator функция
- with_listening_indicator функция
- with_analysis_indicator функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.utils.typing_indicator import (
    TypingIndicator,
    with_typing_indicator,
    with_listening_indicator,
    with_analysis_indicator,
)


class TestTypingIndicatorInit:
    """Тесты для инициализации TypingIndicator"""

    def test_init(self):
        """Тест: инициализация класса"""
        mock_bot = MagicMock()
        chat_id = 12345
        
        indicator = TypingIndicator(mock_bot, chat_id)
        
        assert indicator.bot == mock_bot
        assert indicator.chat_id == chat_id
        assert indicator.indicator_message is None


class TestTypingIndicatorShowCharacterTyping:
    """Тесты для метода show_character_typing"""

    @pytest.mark.asyncio
    async def test_show_character_typing_success(self):
        """Тест: успешное отображение индикатора печатания"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        await indicator.show_character_typing("TestCharacter", "💬")
        
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        assert "TestCharacter думает" in call_kwargs["text"]
        assert call_kwargs["parse_mode"] == "Markdown"
        assert indicator.indicator_message == mock_message

    @pytest.mark.asyncio
    async def test_show_character_typing_default_emoji(self):
        """Тест: индикатор с emoji по умолчанию"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        await indicator.show_character_typing("TestCharacter")
        
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "💬" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_show_character_typing_exception_handling(self):
        """Тест: обработка исключений при отображении индикатора"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Send error"))
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        # Не должно быть исключения
        await indicator.show_character_typing("TestCharacter")
        
        assert indicator.indicator_message is None


class TestTypingIndicatorShowCharacterListening:
    """Тесты для метода show_character_listening"""

    @pytest.mark.asyncio
    async def test_show_character_listening_success(self):
        """Тест: успешное отображение индикатора прослушивания"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        await indicator.show_character_listening("TestCharacter", "🎧")
        
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        assert "TestCharacter слушает" in call_kwargs["text"]
        assert call_kwargs["parse_mode"] == "Markdown"
        assert indicator.indicator_message == mock_message

    @pytest.mark.asyncio
    async def test_show_character_listening_default_emoji(self):
        """Тест: индикатор прослушивания с emoji по умолчанию"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        await indicator.show_character_listening("TestCharacter")
        
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "🎧" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_show_character_listening_exception_handling(self):
        """Тест: обработка исключений при отображении индикатора прослушивания"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Send error"))
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        # Не должно быть исключения
        await indicator.show_character_listening("TestCharacter")
        
        assert indicator.indicator_message is None


class TestTypingIndicatorShowAnalysisIndicator:
    """Тесты для метода show_analysis_indicator"""

    @pytest.mark.asyncio
    async def test_show_analysis_indicator_success(self):
        """Тест: успешное отображение индикатора анализа"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        await indicator.show_analysis_indicator()
        
        mock_bot.send_message.assert_called_once()
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        assert "Анализирую диалог" in call_kwargs["text"]
        assert call_kwargs["parse_mode"] == "Markdown"
        assert indicator.indicator_message == mock_message

    @pytest.mark.asyncio
    async def test_show_analysis_indicator_exception_handling(self):
        """Тест: обработка исключений при отображении индикатора анализа"""
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Send error"))
        
        indicator = TypingIndicator(mock_bot, 12345)
        
        # Не должно быть исключения
        await indicator.show_analysis_indicator()
        
        assert indicator.indicator_message is None


class TestTypingIndicatorHideIndicator:
    """Тесты для метода hide_indicator"""

    @pytest.mark.asyncio
    async def test_hide_indicator_success(self):
        """Тест: успешное скрытие индикатора"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot.delete_message = AsyncMock()
        
        indicator = TypingIndicator(mock_bot, 12345)
        indicator.indicator_message = mock_message
        
        await indicator.hide_indicator()
        
        mock_bot.delete_message.assert_called_once()
        call_kwargs = mock_bot.delete_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        assert call_kwargs["message_id"] == 123
        assert indicator.indicator_message is None

    @pytest.mark.asyncio
    async def test_hide_indicator_no_message(self):
        """Тест: скрытие индикатора когда сообщения нет"""
        mock_bot = MagicMock()
        mock_bot.delete_message = AsyncMock()
        
        indicator = TypingIndicator(mock_bot, 12345)
        indicator.indicator_message = None
        
        await indicator.hide_indicator()
        
        mock_bot.delete_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_hide_indicator_exception_handling(self):
        """Тест: обработка исключений при скрытии индикатора"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.delete_message = AsyncMock(side_effect=Exception("Delete error"))
        
        indicator = TypingIndicator(mock_bot, 12345)
        indicator.indicator_message = mock_message
        
        # Не должно быть исключения
        await indicator.hide_indicator()
        
        # После finally сообщение должно быть очищено
        assert indicator.indicator_message is None


class TestWithTypingIndicator:
    """Тесты для функции with_typing_indicator"""

    @pytest.mark.asyncio
    async def test_with_typing_indicator_shows_and_hides(self):
        """Тест: функция показывает и скрывает индикатор"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot.delete_message = AsyncMock()
        
        async def async_operation():
            return "result"
        
        result = await with_typing_indicator(
            mock_bot, 12345, "TestCharacter", "💬", async_operation
        )
        
        assert result == "result"
        assert mock_bot.send_message.call_count == 1
        assert mock_bot.delete_message.call_count == 1

    @pytest.mark.asyncio
    async def test_with_typing_indicator_exception_in_operation(self):
        """Тест: обработка исключения в операции"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot.delete_message = AsyncMock()
        
        async def async_operation():
            raise Exception("Operation error")
        
        with pytest.raises(Exception):
            await with_typing_indicator(
                mock_bot, 12345, "TestCharacter", "💬", async_operation
            )
        
        # Индикатор должен быть скрыт даже при исключении
        assert mock_bot.delete_message.call_count == 1


class TestWithListeningIndicator:
    """Тесты для функции with_listening_indicator"""

    @pytest.mark.asyncio
    async def test_with_listening_indicator_shows_and_hides(self):
        """Тест: функция показывает и скрывает индикатор прослушивания"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot.delete_message = AsyncMock()
        
        async def async_operation():
            return "result"
        
        result = await with_listening_indicator(
            mock_bot, 12345, "TestCharacter", "🎧", async_operation
        )
        
        assert result == "result"
        assert mock_bot.send_message.call_count == 1
        assert mock_bot.delete_message.call_count == 1

    @pytest.mark.asyncio
    async def test_with_listening_indicator_calls_listening_method(self):
        """Тест: функция вызывает метод прослушивания"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot.delete_message = AsyncMock()
        
        async def async_operation():
            return "result"
        
        await with_listening_indicator(
            mock_bot, 12345, "TestCharacter", "🎧", async_operation
        )
        
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "слушает" in call_kwargs["text"]


class TestWithAnalysisIndicator:
    """Тесты для функции with_analysis_indicator"""

    @pytest.mark.asyncio
    async def test_with_analysis_indicator_shows_and_hides(self):
        """Тест: функция показывает и скрывает индикатор анализа"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot.delete_message = AsyncMock()
        
        async def async_operation():
            return "result"
        
        result = await with_analysis_indicator(
            mock_bot, 12345, async_operation
        )
        
        assert result == "result"
        assert mock_bot.send_message.call_count == 1
        assert mock_bot.delete_message.call_count == 1

    @pytest.mark.asyncio
    async def test_with_analysis_indicator_shows_analysis_text(self):
        """Тест: функция показывает текст анализа"""
        mock_bot = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = 123
        mock_bot.send_message = AsyncMock(return_value=mock_message)
        mock_bot.delete_message = AsyncMock()
        
        async def async_operation():
            return "result"
        
        await with_analysis_indicator(mock_bot, 12345, async_operation)
        
        call_kwargs = mock_bot.send_message.call_args.kwargs
        assert "Анализирую диалог" in call_kwargs["text"]

