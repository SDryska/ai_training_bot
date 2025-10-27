"""
Тесты для сервиса AI.

Тестируемый модуль:
- app/services/ai_service.py

Тестируемые компоненты:
- initialize_ai_providers функция
- get_ai_gateway функция
- send_case_message функция
- clear_case_conversations функция
- clear_all_conversations функция
- send_dialogue_message функция
- send_reviewer_message функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_service import (
    initialize_ai_providers,
    get_ai_gateway,
    send_case_message,
    clear_case_conversations,
    clear_all_conversations,
    send_dialogue_message,
    send_reviewer_message,
)
from app.providers.base import AIResponse, ProviderType


class TestInitializeAIProviders:
    """Тесты для функции initialize_ai_providers"""

    def test_initialize_ai_providers_with_postgres(self):
        """Тест: инициализация с PostgreSQL хранилищем"""
        with patch("app.services.ai_service.Settings") as mock_settings, \
             patch("app.services.ai_service.PostgresStorage") as mock_postgres, \
             patch("app.services.ai_service.OpenAIProvider") as mock_openai, \
             patch("app.services.ai_service.GeminiProvider") as mock_gemini, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_settings.return_value.DATABASE_URL = "postgresql://test"
            mock_settings.return_value.OPENAI_API_KEY = "test_key"
            mock_settings.return_value.GEMINI_API_KEY = "test_key"
            
            mock_storage = MagicMock()
            mock_postgres.return_value = mock_storage
            
            initialize_ai_providers()
            
            mock_postgres.assert_called_once()
            mock_openai.assert_called_once()
            mock_gateway.register_provider.assert_called()

    def test_initialize_ai_providers_without_database(self):
        """Тест: инициализация без DATABASE_URL"""
        with patch("app.services.ai_service.Settings") as mock_settings, \
             patch("app.services.ai_service.InMemoryStorage") as mock_memory, \
             patch("app.services.ai_service.OpenAIProvider") as mock_openai, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_settings.return_value.DATABASE_URL = None
            mock_settings.return_value.OPENAI_API_KEY = "test_key"
            
            initialize_ai_providers()
            
            mock_memory.assert_called_once()

    def test_initialize_ai_providers_without_openai_key(self):
        """Тест: инициализация без OPENAI_API_KEY"""
        with patch("app.services.ai_service.Settings") as mock_settings, \
             patch("app.services.ai_service.PostgresStorage") as mock_postgres, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_settings.return_value.DATABASE_URL = "postgresql://test"
            mock_settings.return_value.OPENAI_API_KEY = None
            
            initialize_ai_providers()
            
            # Проверяем, что OpenAI провайдер не был зарегистрирован
            calls = [call[0][0] for call in mock_gateway.register_provider.call_args_list]
            assert ProviderType.OPENAI not in calls

    def test_initialize_ai_providers_storage_exception(self):
        """Тест: обработка исключения при создании хранилища"""
        with patch("app.services.ai_service.Settings") as mock_settings, \
             patch("app.services.ai_service.PostgresStorage", side_effect=Exception("Storage error")) as mock_postgres, \
             patch("app.services.ai_service.InMemoryStorage") as mock_memory:
            
            mock_settings.return_value.DATABASE_URL = "postgresql://test"
            mock_settings.return_value.OPENAI_API_KEY = "test_key"
            
            initialize_ai_providers()
            
            # Должен быть использован InMemoryStorage как fallback
            mock_memory.assert_called()

    def test_initialize_ai_providers_openai_provider_exception(self):
        """Тест: обработка исключения при инициализации OpenAI провайдера"""
        with patch("app.services.ai_service.Settings") as mock_settings, \
             patch("app.services.ai_service.PostgresStorage") as mock_postgres, \
             patch("app.services.ai_service.OpenAIProvider", side_effect=Exception("OpenAI error")) as mock_openai, \
             patch("app.services.ai_service.logger") as mock_logger:
            
            mock_settings.return_value.DATABASE_URL = "postgresql://test"
            mock_settings.return_value.OPENAI_API_KEY = "test_key"
            mock_settings.return_value.GEMINI_API_KEY = None
            
            initialize_ai_providers()
            
            # Проверяем, что ошибка была залогирована
            mock_logger.error.assert_called()

    def test_initialize_ai_providers_gemini_provider_exception(self):
        """Тест: обработка исключения при инициализации Gemini провайдера"""
        with patch("app.services.ai_service.Settings") as mock_settings, \
             patch("app.services.ai_service.PostgresStorage") as mock_postgres, \
             patch("app.services.ai_service.GeminiProvider", side_effect=Exception("Gemini error")) as mock_gemini, \
             patch("app.services.ai_service.logger") as mock_logger:
            
            mock_settings.return_value.DATABASE_URL = "postgresql://test"
            mock_settings.return_value.OPENAI_API_KEY = "test_key"
            mock_settings.return_value.GEMINI_API_KEY = "test_key"
            
            initialize_ai_providers()
            
            # Проверяем, что ошибка была залогирована
            mock_logger.error.assert_called()


class TestGetAIGateway:
    """Тесты для функции get_ai_gateway"""

    def test_get_ai_gateway_returns_gateway(self):
        """Тест: функция возвращает gateway"""
        result = get_ai_gateway()
        
        assert result is not None


class TestSendCaseMessage:
    """Тесты для функции send_case_message"""

    @pytest.mark.asyncio
    async def test_send_case_message_success(self):
        """Тест: успешная отправка сообщения кейса"""
        response = AIResponse(content="Hello", success=True)
        
        with patch("app.services.ai_service._get_provider_chain") as mock_chain, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_provider_settings = MagicMock()
            mock_provider_settings.provider = ProviderType.OPENAI
            mock_provider_settings.model = "gpt-3.5-turbo"
            mock_chain.return_value = [mock_provider_settings]
            
            mock_gateway.send_message = AsyncMock(return_value=response)
            
            result = await send_case_message(
                case_id="test_case",
                channel="dialogue",
                user_id=12345,
                message="Test"
            )
            
            assert result.success is True
            assert result.content == "Hello"

    @pytest.mark.asyncio
    async def test_send_case_message_fallback(self):
        """Тест: fallback на следующий провайдер при неудаче"""
        failed_response = AIResponse(content="", success=False, error="Error")
        success_response = AIResponse(content="Hello", success=True)
        
        with patch("app.services.ai_service._get_provider_chain") as mock_chain, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_provider_settings1 = MagicMock()
            mock_provider_settings1.provider = ProviderType.OPENAI
            mock_provider_settings1.model = "gpt-3.5-turbo"
            
            mock_provider_settings2 = MagicMock()
            mock_provider_settings2.provider = ProviderType.GEMINI
            mock_provider_settings2.model = "gemini-2.0-flash"
            
            mock_chain.return_value = [mock_provider_settings1, mock_provider_settings2]
            
            mock_gateway.send_message = AsyncMock(side_effect=[failed_response, success_response])
            mock_gateway.clear_conversation = AsyncMock()
            
            result = await send_case_message(
                case_id="test_case",
                channel="dialogue",
                user_id=12345,
                message="Test"
            )
            
            assert result.success is True
            assert mock_gateway.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_case_message_all_fail(self):
        """Тест: все провайдеры недоступны"""
        failed_response = AIResponse(content="", success=False, error="Error")
        
        with patch("app.services.ai_service._get_provider_chain") as mock_chain, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_provider_settings = MagicMock()
            mock_provider_settings.provider = ProviderType.OPENAI
            mock_provider_settings.model = "gpt-3.5-turbo"
            
            mock_chain.return_value = [mock_provider_settings]
            
            mock_gateway.send_message = AsyncMock(return_value=failed_response)
            mock_gateway.clear_conversation = AsyncMock()
            
            result = await send_case_message(
                case_id="test_case",
                channel="dialogue",
                user_id=12345,
                message="Test"
            )
            
            assert result.success is False
            # Проверяем, что в ошибке есть информация о провайдере
            assert "openai" in result.error.lower() or "недоступны" in result.error

    @pytest.mark.asyncio
    async def test_send_case_message_with_audio(self):
        """Тест: отправка сообщения с аудио"""
        response = AIResponse(content="Hello", success=True)
        audio_bytes = b"test_audio_data"
        
        with patch("app.services.ai_service._get_provider_chain") as mock_chain, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_provider_settings = MagicMock()
            mock_provider_settings.provider = ProviderType.GEMINI
            mock_provider_settings.model = "gemini-2.0-flash"
            
            mock_chain.return_value = [mock_provider_settings]
            
            mock_gateway.send_message = AsyncMock(return_value=response)
            
            result = await send_case_message(
                case_id="test_case",
                channel="dialogue",
                user_id=12345,
                message="Test",
                audio_bytes=audio_bytes
            )
            
            assert result.success is True
            call_kwargs = mock_gateway.send_message.call_args.kwargs
            assert call_kwargs["audio_bytes"] == audio_bytes


class TestClearCaseConversations:
    """Тесты для функции clear_case_conversations"""

    @pytest.mark.asyncio
    async def test_clear_case_conversations(self):
        """Тест: очистка истории для всех провайдеров кейса"""
        with patch("app.services.ai_service.get_case_provider_config") as mock_config, \
             patch("app.services.ai_service.gateway") as mock_gateway:
            
            mock_config_obj = MagicMock()
            mock_config_obj.dialogue.primary.provider = ProviderType.OPENAI
            mock_config_obj.dialogue.fallback.provider = ProviderType.GEMINI
            mock_config_obj.reviewer.primary.provider = ProviderType.OPENAI
            mock_config_obj.reviewer.fallback = None
            
            mock_config.return_value = mock_config_obj
            
            mock_gateway.clear_conversation = AsyncMock()
            
            await clear_case_conversations("test_case", 12345)
            
            # Должны быть очищены уникальные провайдеры
            assert mock_gateway.clear_conversation.call_count == 2


class TestClearAllConversations:
    """Тесты для функции clear_all_conversations"""

    @pytest.mark.asyncio
    async def test_clear_all_conversations(self):
        """Тест: очистка истории для всех провайдеров"""
        with patch("app.services.ai_service.gateway") as mock_gateway:
            mock_gateway.get_available_providers.return_value = [
                ProviderType.OPENAI,
                ProviderType.GEMINI
            ]
            mock_gateway.clear_conversation = AsyncMock()
            
            await clear_all_conversations(12345)
            
            assert mock_gateway.clear_conversation.call_count == 2


class TestSendDialogueMessage:
    """Тесты для функции send_dialogue_message"""

    @pytest.mark.asyncio
    async def test_send_dialogue_message(self):
        """Тест: отправка сообщения персонажу"""
        response = AIResponse(content="Hello", success=True)
        
        with patch("app.services.ai_service.send_case_message", new_callable=AsyncMock, return_value=response) as mock_send:
            result = await send_dialogue_message(
                case_id="test_case",
                user_id=12345,
                message="Test"
            )
            
            assert result.success is True
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["channel"] == "dialogue"


class TestSendReviewerMessage:
    """Тесты для функции send_reviewer_message"""

    @pytest.mark.asyncio
    async def test_send_reviewer_message(self):
        """Тест: отправка сообщения рецензенту"""
        response = AIResponse(content="Hello", success=True)
        
        with patch("app.services.ai_service.send_case_message", new_callable=AsyncMock, return_value=response) as mock_send:
            result = await send_reviewer_message(
                case_id="test_case",
                user_id=12345,
                message="Test"
            )
            
            assert result.success is True
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["channel"] == "reviewer"

