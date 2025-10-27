"""
Тесты для middleware обработки ошибок.

Модуль: app/middlewares/errors.py

Middleware перехватывает все необработанные исключения и:
1. Логирует их
2. Отправляет пользователю friendly сообщение
3. Предотвращает падение бота
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, call
from typing import Dict, Any

from aiogram.types import Message, CallbackQuery
from app.middlewares.errors import ErrorsMiddleware


class TestErrorsMiddlewareWithMessage:
    """Тесты middleware с Message событиями"""

    @pytest.mark.asyncio
    async def test_message_handler_success(self):
        """Тест: успешная обработка сообщения"""
        middleware = ErrorsMiddleware()
        
        # Создаем мок handler который успешно выполняется
        mock_handler = AsyncMock(return_value="success")
        
        # Создаем мок Message
        mock_message = Mock()
        mock_message.answer = AsyncMock()
        
        # Создаем data dict
        data = {"event_from_user": Mock()}
        
        result = await middleware(mock_handler, mock_message, data)
        
        assert result == "success"
        mock_handler.assert_called_once_with(mock_message, data)
        # При успехе не должно быть вызова answer
        mock_message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_message_handler_exception(self):
        """Тест: обработка исключения в Message handler"""
        middleware = ErrorsMiddleware()
        
        # Handler выбрасывает исключение
        mock_handler = AsyncMock(side_effect=Exception("Test error"))
        
        # Мок Message с spec чтобы isinstance() работал
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        data = {}
        
        result = await middleware(mock_handler, mock_message, data)
        
        # Middleware должен вернуть None (проглотить ошибку)
        assert result is None
        
        # Должен отправить сообщение об ошибке пользователю
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
        assert "ошибка" in call_args.lower()

    @pytest.mark.asyncio
    async def test_message_handler_exception_logging(self):
        """Тест: исключение логируется"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=ValueError("Test value error"))
        mock_message = Mock()
        mock_message.answer = AsyncMock()
        
        data = {}
        
        with patch('app.middlewares.errors.logger') as mock_logger:
            await middleware(mock_handler, mock_message, data)
            
            # Проверяем что было логирование
            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args[0][0]
            assert "Необработанное исключение" in call_args

    @pytest.mark.asyncio
    async def test_message_answer_also_fails(self):
        """Тест: если answer тоже падает, middleware не крашится"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Handler error"))
        mock_message = Mock()
        # answer тоже выбрасывает исключение
        mock_message.answer = AsyncMock(side_effect=Exception("Answer error"))
        
        data = {}
        
        # Не должно выбросить исключение
        result = await middleware(mock_handler, mock_message, data)
        
        assert result is None


class TestErrorsMiddlewareWithCallbackQuery:
    """Тесты middleware с CallbackQuery событиями"""

    @pytest.mark.asyncio
    async def test_callback_query_handler_success(self):
        """Тест: успешная обработка callback query"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(return_value="success")
        
        # Создаем мок CallbackQuery с spec
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.answer = AsyncMock()
        mock_callback.message = None
        
        data = {}
        
        result = await middleware(mock_handler, mock_callback, data)
        
        assert result == "success"
        # При успехе не должно быть answer
        mock_callback.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_query_handler_exception(self):
        """Тест: обработка исключения в CallbackQuery handler"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=RuntimeError("Callback error"))
        
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.answer = AsyncMock()
        mock_callback.message = Mock(spec=Message)
        mock_callback.message.answer = AsyncMock()
        
        data = {}
        
        result = await middleware(mock_handler, mock_callback, data)
        
        assert result is None
        
        # Должен вызвать answer с alert
        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "❌" in call_args[0][0]
        assert call_args[1]["show_alert"] is True
        
        # Также должен попытаться отправить сообщение
        mock_callback.message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_query_without_message(self):
        """Тест: CallbackQuery без message объекта"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Error"))
        
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.answer = AsyncMock()
        mock_callback.message = None  # Нет message
        
        data = {}
        
        result = await middleware(mock_handler, mock_callback, data)
        
        assert result is None
        # Должен вызвать answer
        mock_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_query_all_notifications_fail(self):
        """Тест: все попытки уведомить пользователя проваливаются"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Handler error"))
        
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.answer = AsyncMock(side_effect=Exception("Answer error"))
        mock_callback.message = Mock(spec=Message)
        mock_callback.message.answer = AsyncMock(side_effect=Exception("Message error"))
        
        data = {}
        
        # Не должно выбросить исключение
        result = await middleware(mock_handler, mock_callback, data)
        
        assert result is None


class TestErrorsMiddlewareWithOtherEvents:
    """Тесты middleware с другими типами событий"""

    @pytest.mark.asyncio
    async def test_unknown_event_type_success(self):
        """Тест: успешная обработка неизвестного типа события"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(return_value="ok")
        mock_event = Mock()  # Произвольное событие
        
        data = {}
        
        result = await middleware(mock_handler, mock_event, data)
        
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_unknown_event_type_exception(self):
        """Тест: исключение при обработке неизвестного события"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Unknown event error"))
        mock_event = Mock()
        # Неизвестный тип события - нет методов answer
        
        data = {}
        
        result = await middleware(mock_handler, mock_event, data)
        
        # Должен проглотить исключение
        assert result is None


class TestErrorMessageContent:
    """Тесты содержимого сообщений об ошибках"""

    @pytest.mark.asyncio
    async def test_error_message_user_friendly(self):
        """Тест: сообщение об ошибке понятное для пользователя"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Internal error"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        data = {}
        
        await middleware(mock_handler, mock_message, data)
        
        error_text = mock_message.answer.call_args[0][0]
        
        # Проверяем что сообщение дружелюбное
        assert "❌" in error_text
        assert "Произошла ошибка" in error_text or "ошибка" in error_text.lower()
        assert "позже" in error_text.lower()
        
        # Не должно содержать технических деталей
        assert "Internal error" not in error_text
        assert "Exception" not in error_text

    @pytest.mark.asyncio
    async def test_callback_alert_message_brief(self):
        """Тест: alert для callback краткий"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Error"))
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.answer = AsyncMock()
        mock_callback.message = None
        
        data = {}
        
        await middleware(mock_handler, mock_callback, data)
        
        alert_text = mock_callback.answer.call_args[0][0]
        
        # Alert должен быть коротким
        assert len(alert_text) < 100
        assert "❌" in alert_text


class TestDifferentExceptionTypes:
    """Тесты с разными типами исключений"""

    @pytest.mark.asyncio
    async def test_value_error(self):
        """Тест: ValueError обрабатывается"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=ValueError("Invalid value"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None
        mock_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_key_error(self):
        """Тест: KeyError обрабатывается"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=KeyError("missing_key"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None

    @pytest.mark.asyncio
    async def test_attribute_error(self):
        """Тест: AttributeError обрабатывается"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=AttributeError("No such attribute"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None

    @pytest.mark.asyncio
    async def test_type_error(self):
        """Тест: TypeError обрабатывается"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=TypeError("Type mismatch"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None

    @pytest.mark.asyncio
    async def test_generic_exception(self):
        """Тест: общее Exception обрабатывается"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Generic error"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None


class TestMiddlewareChaining:
    """Тесты цепочки middleware"""

    @pytest.mark.asyncio
    async def test_data_passed_to_handler(self):
        """Тест: data передается в handler"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(return_value="ok")
        mock_event = Mock()
        
        test_data = {"user_id": 123, "extra": "data"}
        
        await middleware(mock_handler, mock_event, test_data)
        
        # Проверяем что handler получил data
        mock_handler.assert_called_once_with(mock_event, test_data)

    @pytest.mark.asyncio
    async def test_handler_return_value_preserved(self):
        """Тест: возвращаемое значение handler сохраняется"""
        middleware = ErrorsMiddleware()
        
        return_value = {"result": "data", "status": "ok"}
        mock_handler = AsyncMock(return_value=return_value)
        mock_event = Mock()
        
        result = await middleware(mock_handler, mock_event, {})
        
        assert result == return_value


class TestRealWorldScenarios:
    """Тесты реальных сценариев"""

    @pytest.mark.asyncio
    async def test_scenario_database_connection_error(self):
        """Сценарий: ошибка подключения к БД"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=ConnectionError("Cannot connect to database"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None
        # Пользователь должен получить сообщение
        mock_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_scenario_timeout_error(self):
        """Сценарий: timeout при запросе"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=TimeoutError("Request timeout"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None

    @pytest.mark.asyncio
    async def test_scenario_ai_api_error(self):
        """Сценарий: ошибка AI API"""
        middleware = ErrorsMiddleware()
        
        # Имитируем ошибку от OpenAI API
        mock_handler = AsyncMock(side_effect=Exception("OpenAI API rate limit exceeded"))
        mock_callback = Mock(spec=CallbackQuery)
        mock_callback.answer = AsyncMock()
        mock_callback.message = Mock(spec=Message)
        mock_callback.message.answer = AsyncMock()
        
        result = await middleware(mock_handler, mock_callback, {})
        
        assert result is None
        # Пользователь должен получить уведомление
        mock_callback.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_scenario_multiple_errors_in_sequence(self):
        """Сценарий: несколько ошибок подряд"""
        middleware = ErrorsMiddleware()
        
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        # Первая ошибка
        mock_handler1 = AsyncMock(side_effect=Exception("Error 1"))
        await middleware(mock_handler1, mock_message, {})
        
        # Вторая ошибка
        mock_handler2 = AsyncMock(side_effect=Exception("Error 2"))
        await middleware(mock_handler2, mock_message, {})
        
        # Обе должны быть обработаны
        assert mock_message.answer.call_count == 2

    @pytest.mark.asyncio
    async def test_scenario_user_gets_graceful_error_message(self):
        """Сценарий: пользователь получает понятное сообщение при любой ошибке"""
        middleware = ErrorsMiddleware()
        
        # Разные типы ошибок
        errors = [
            ValueError("Invalid input"),
            KeyError("Missing key"),
            AttributeError("No attr"),
            Exception("Generic error"),
        ]
        
        for error in errors:
            mock_handler = AsyncMock(side_effect=error)
            mock_message = Mock(spec=Message)
            mock_message.answer = AsyncMock()
            
            result = await middleware(mock_handler, mock_message, {})
            
            # Всегда должен вернуть None (не упасть)
            assert result is None
            
            # Всегда должен уведомить пользователя
            mock_message.answer.assert_called_once()
            
            # Сообщение должно быть понятным
            error_msg = mock_message.answer.call_args[0][0]
            assert "❌" in error_msg


class TestBotStability:
    """Тесты стабильности бота"""

    @pytest.mark.asyncio
    async def test_middleware_never_crashes_bot(self):
        """Тест: middleware никогда не крашит бота"""
        middleware = ErrorsMiddleware()
        
        # Даже если handler выбрасывает критическую ошибку
        mock_handler = AsyncMock(side_effect=SystemError("Critical error"))
        mock_message = Mock(spec=Message)
        mock_message.answer = AsyncMock()
        
        # Не должно пробросить исключение наружу
        result = await middleware(mock_handler, mock_message, {})
        
        assert result is None

    @pytest.mark.asyncio
    async def test_middleware_handles_all_notification_failures(self):
        """Тест: middleware работает даже если все уведомления провалились"""
        middleware = ErrorsMiddleware()
        
        mock_handler = AsyncMock(side_effect=Exception("Handler error"))
        mock_callback = Mock(spec=CallbackQuery)
        # Все методы уведомления падают
        mock_callback.answer = AsyncMock(side_effect=Exception("Answer fails"))
        mock_callback.message = Mock(spec=Message)
        mock_callback.message.answer = AsyncMock(side_effect=Exception("Message fails"))
        
        # Все равно не должно крашнуть бота
        result = await middleware(mock_handler, mock_callback, {})
        
        assert result is None  # Просто возвращает None

