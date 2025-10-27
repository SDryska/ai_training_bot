"""
Тесты для шлюза провайдеров.

Тестируемый модуль:
- app/providers/gateway.py

Тестируемые компоненты:
- AIProviderGateway класс
- gateway экземпляр
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from app.providers.gateway import AIProviderGateway, gateway
from app.providers.base import ProviderType, AIResponse


class TestAIProviderGatewayInit:
    """Тесты для инициализации AIProviderGateway"""

    def test_init(self):
        """Тест: инициализация класса"""
        gateway_instance = AIProviderGateway()
        
        assert gateway_instance._providers == {}
        assert gateway_instance._default_provider is None


class TestAIProviderGatewayRegisterProvider:
    """Тесты для метода register_provider"""

    def test_register_provider(self):
        """Тест: регистрация провайдера"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        assert ProviderType.OPENAI in gateway_instance._providers
        assert gateway_instance._providers[ProviderType.OPENAI] == mock_provider
        assert gateway_instance._default_provider == ProviderType.OPENAI

    def test_register_provider_sets_as_default(self):
        """Тест: регистрация провайдера как дефолтного"""
        gateway_instance = AIProviderGateway()
        mock_provider1 = MagicMock()
        mock_provider1.provider_type = ProviderType.OPENAI
        mock_provider2 = MagicMock()
        mock_provider2.provider_type = ProviderType.GEMINI
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider1)
        gateway_instance.register_provider(ProviderType.GEMINI, mock_provider2, is_default=True)
        
        assert gateway_instance._default_provider == ProviderType.GEMINI

    def test_register_provider_first_becomes_default(self):
        """Тест: первый провайдер становится дефолтным"""
        gateway_instance = AIProviderGateway()
        mock_provider1 = MagicMock()
        mock_provider1.provider_type = ProviderType.OPENAI
        mock_provider2 = MagicMock()
        mock_provider2.provider_type = ProviderType.GEMINI
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider1)
        gateway_instance.register_provider(ProviderType.GEMINI, mock_provider2)
        
        assert gateway_instance._default_provider == ProviderType.OPENAI


class TestAIProviderGatewayGetProvider:
    """Тесты для метода get_provider"""

    def test_get_provider_by_type(self):
        """Тест: получение провайдера по типу"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        result = gateway_instance.get_provider(ProviderType.OPENAI)
        assert result == mock_provider

    def test_get_provider_default(self):
        """Тест: получение дефолтного провайдера"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        result = gateway_instance.get_provider()
        assert result == mock_provider

    def test_get_provider_not_found(self):
        """Тест: получение несуществующего провайдера"""
        gateway_instance = AIProviderGateway()
        
        result = gateway_instance.get_provider(ProviderType.OPENAI)
        assert result is None


class TestAIProviderGatewayGetAvailableProviders:
    """Тесты для метода get_available_providers"""

    def test_get_available_providers(self):
        """Тест: получение списка доступных провайдеров"""
        gateway_instance = AIProviderGateway()
        mock_provider1 = MagicMock()
        mock_provider1.provider_type = ProviderType.OPENAI
        mock_provider2 = MagicMock()
        mock_provider2.provider_type = ProviderType.GEMINI
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider1)
        gateway_instance.register_provider(ProviderType.GEMINI, mock_provider2)
        
        available = gateway_instance.get_available_providers()
        
        assert len(available) == 2
        assert ProviderType.OPENAI in available
        assert ProviderType.GEMINI in available

    def test_get_available_providers_empty(self):
        """Тест: получение списка когда провайдеров нет"""
        gateway_instance = AIProviderGateway()
        
        available = gateway_instance.get_available_providers()
        
        assert available == []


class TestAIProviderGatewaySendMessage:
    """Тесты для метода send_message"""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Тест: успешная отправка сообщения"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.send_message = AsyncMock(return_value=AIResponse(
            content="Hello", success=True
        ))
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        response = await gateway_instance.send_message(
            user_id=12345,
            message="Test",
            provider_type=ProviderType.OPENAI
        )
        
        assert response.success is True
        assert response.content == "Hello"
        mock_provider.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_provider(self):
        """Тест: отправка сообщения без провайдера"""
        gateway_instance = AIProviderGateway()
        
        response = await gateway_instance.send_message(
            user_id=12345,
            message="Test",
            provider_type=ProviderType.OPENAI
        )
        
        assert response.success is False
        assert "недоступен" in response.error

    @pytest.mark.asyncio
    async def test_send_message_with_system_prompt(self):
        """Тест: отправка сообщения с системным промптом"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.send_message = AsyncMock(return_value=AIResponse(
            content="Hello", success=True
        ))
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        await gateway_instance.send_message(
            user_id=12345,
            message="Test",
            system_prompt="You are a helpful assistant",
            provider_type=ProviderType.OPENAI
        )
        
        call_args = mock_provider.send_message.call_args
        # system_prompt передается как позиционный аргумент
        assert call_args[0][2] == "You are a helpful assistant"

    @pytest.mark.asyncio
    async def test_send_message_with_model_override(self):
        """Тест: отправка сообщения с переопределением модели"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.send_message = AsyncMock(return_value=AIResponse(
            content="Hello", success=True
        ))
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        await gateway_instance.send_message(
            user_id=12345,
            message="Test",
            model_override="gpt-4",
            provider_type=ProviderType.OPENAI
        )
        
        call_args = mock_provider.send_message.call_args
        # model_override передается как позиционный аргумент
        assert call_args[0][3] == "gpt-4"

    @pytest.mark.asyncio
    async def test_send_message_retry_on_failure(self):
        """Тест: повторная попытка при неудаче"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        
        # Первый вызов падает, второй успешен
        mock_provider.send_message = AsyncMock(side_effect=[
            Exception("Network error"),
            AIResponse(content="Hello", success=True)
        ])
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        with patch("app.providers.gateway.Settings") as mock_settings:
            mock_settings.return_value.AI_REQUEST_MAX_RETRIES = 2
            mock_settings.return_value.AI_REQUEST_TIMEOUT_SEC = 10.0
            mock_settings.return_value.AI_REQUEST_RETRY_BACKOFF_SEC = 0.1
            
            response = await gateway_instance.send_message(
                user_id=12345,
                message="Test",
                provider_type=ProviderType.OPENAI
            )
            
            assert response.success is True
            assert mock_provider.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_timeout(self):
        """Тест: таймаут при отправке сообщения"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        
        async def slow_operation():
            await asyncio.sleep(2)
            return AIResponse(content="Hello", success=True)
        
        mock_provider.send_message = AsyncMock(side_effect=slow_operation)
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        with patch("app.providers.gateway.Settings") as mock_settings:
            mock_settings.return_value.AI_REQUEST_MAX_RETRIES = 1
            mock_settings.return_value.AI_REQUEST_TIMEOUT_SEC = 0.1
            mock_settings.return_value.AI_REQUEST_RETRY_BACKOFF_SEC = 0.1
            
            response = await gateway_instance.send_message(
                user_id=12345,
                message="Test",
                provider_type=ProviderType.OPENAI
            )
            
            assert response.success is False


class TestAIProviderGatewayClearConversation:
    """Тесты для метода clear_conversation"""

    @pytest.mark.asyncio
    async def test_clear_conversation_success(self):
        """Тест: успешная очистка истории"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.clear_conversation = AsyncMock()
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        await gateway_instance.clear_conversation(12345, ProviderType.OPENAI)
        
        mock_provider.clear_conversation.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_clear_conversation_no_provider(self):
        """Тест: очистка истории без провайдера"""
        gateway_instance = AIProviderGateway()
        
        # Не должно быть исключения
        await gateway_instance.clear_conversation(12345, ProviderType.OPENAI)


class TestGatewayWithAudioBytes:
    """Тесты для gateway с аудиобайтами"""

    @pytest.mark.asyncio
    async def test_send_message_with_audio_bytes_gemini(self):
        """Тест: отправка сообщения с аудиобайтами для Gemini"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.GEMINI
        mock_provider.send_message = AsyncMock(return_value=AIResponse(
            content="Audio response", success=True
        ))
        
        gateway_instance.register_provider(ProviderType.GEMINI, mock_provider)
        
        audio_bytes = b"fake audio data"
        
        await gateway_instance.send_message(
            user_id=12345,
            message="Test",
            provider_type=ProviderType.GEMINI,
            audio_bytes=audio_bytes
        )
        
        # Проверяем, что send_message вызван с audio_bytes
        call_args = mock_provider.send_message.call_args
        assert call_args[1]["audio_bytes"] == audio_bytes

    @pytest.mark.asyncio
    async def test_send_message_with_audio_bytes_non_gemini(self):
        """Тест: отправка сообщения с аудиобайтами для не-Gemini провайдера"""
        gateway_instance = AIProviderGateway()
        mock_provider = MagicMock()
        mock_provider.provider_type = ProviderType.OPENAI
        mock_provider.send_message = AsyncMock(return_value=AIResponse(
            content="Response", success=True
        ))
        
        gateway_instance.register_provider(ProviderType.OPENAI, mock_provider)
        
        audio_bytes = b"fake audio data"
        
        await gateway_instance.send_message(
            user_id=12345,
            message="Test",
            provider_type=ProviderType.OPENAI,
            audio_bytes=audio_bytes
        )
        
        # Проверяем, что send_message вызван без audio_bytes для не-Gemini
        call_args = mock_provider.send_message.call_args
        assert "audio_bytes" not in call_args[1]


class TestGatewayInstance:
    """Тесты для глобального экземпляра gateway"""

    def test_gateway_is_instance(self):
        """Тест: gateway является экземпляром AIProviderGateway"""
        assert isinstance(gateway, AIProviderGateway)

