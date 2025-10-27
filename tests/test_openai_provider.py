"""
Тесты для OpenAI провайдера.

Тестируемый модуль:
- app/providers/openai.py

Тестируемые компоненты:
- OpenAIProvider класс
- Методы: __init__, send_message, send_messages, _ask_gpt, _convert_to_openai_format
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.providers.openai import OpenAIProvider
from app.providers.base import AIMessage, AIResponse, ProviderType


class TestOpenAIProviderInit:
    """Тесты для __init__ метода"""

    def test_init_basic(self):
        """Тест: базовая инициализация"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        assert provider.api_key == "test-api-key"
        assert provider.model == "gpt-3.5-turbo"
        assert provider.provider_type == ProviderType.OPENAI
        assert provider.storage is None

    def test_init_with_storage(self):
        """Тест: инициализация с storage"""
        mock_storage = MagicMock()
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo", mock_storage)
        
        assert provider.storage == mock_storage

    def test_init_with_default_model(self):
        """Тест: инициализация с моделью по умолчанию"""
        provider = OpenAIProvider("test-api-key")
        
        assert provider.model == "gpt-3.5-turbo"


class TestOpenAIProviderAskGpt:
    """Тесты для метода _ask_gpt"""

    def test_ask_gpt_success(self):
        """Тест: успешный запрос к GPT"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        messages = [{"role": "user", "content": "Hello"}]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, how can I help?"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = provider._ask_gpt(messages)
        
        assert result == "Hello, how can I help?"

    def test_ask_gpt_gpt5_model(self):
        """Тест: запрос к GPT-5 модели"""
        provider = OpenAIProvider("test-api-key", "gpt-5")
        messages = [{"role": "user", "content": "Hello"}]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "GPT-5 response"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
            result = provider._ask_gpt(messages)
            
            assert result == "GPT-5 response"
            # Проверяем, что вызывается с reasoning_effort
            call_kwargs = mock_create.call_args[1]
            assert "reasoning_effort" in call_kwargs

    def test_ask_gpt_with_max_tokens(self):
        """Тест: запрос с max_tokens"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        messages = [{"role": "user", "content": "Hello"}]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response) as mock_create:
            result = provider._ask_gpt(messages)
            
            assert result == "Response"
            # Проверяем, что вызывается с max_tokens
            call_kwargs = mock_create.call_args[1]
            assert "max_tokens" in call_kwargs or "max_completion_tokens" in call_kwargs

    def test_ask_gpt_error(self):
        """Тест: обработка ошибки API"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch.object(provider.client.chat.completions, 'create', side_effect=Exception("API Error")):
            result = provider._ask_gpt(messages)
        
        assert result is None

    def test_ask_gpt_gpt5_first_fail_fallback(self):
        """Тест: GPT-5 модель с fallback на max_completion_tokens"""
        provider = OpenAIProvider("test-api-key", "gpt-5")
        messages = [{"role": "user", "content": "Hello"}]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "GPT-5 fallback response"
        
        # Первый вызов падает, второй успешен
        with patch.object(provider.client.chat.completions, 'create', side_effect=[
            Exception("First error"),
            mock_response
        ]) as mock_create:
            result = provider._ask_gpt(messages)
            
            assert result == "GPT-5 fallback response"
            assert mock_create.call_count == 2
            # Проверяем, что второй вызов был с его параметрами
            second_call = mock_create.call_args_list[1]
            assert "max_completion_tokens" in second_call[1]

    def test_ask_gpt_preferred_param_cache_reset(self):
        """Тест: сброс кэша параметров токенов при ошибке"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        messages = [{"role": "user", "content": "Hello"}]
        
        # Устанавливаем предпочтение
        provider._model_tokens_param["gpt-3.5-turbo"] = "max_tokens"
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        
        # Первый вызов с кэшированным параметром падает, второй (max_tokens) тоже, третий (max_completion_tokens) успешен
        with patch.object(provider.client.chat.completions, 'create', side_effect=[
            Exception("Cached param error"),
            Exception("max_tokens error"),
            mock_response
        ]) as mock_create:
            result = provider._ask_gpt(messages)
            
            assert result == "Response"
            # Проверяем, что было 3 вызова
            assert mock_create.call_count == 3
            # После сброса кэша и успешного вызова с max_completion_tokens
            assert provider._model_tokens_param.get("gpt-3.5-turbo") == "max_completion_tokens"

    def test_ask_gpt_max_completion_tokens_fallback(self):
        """Тест: fallback с max_tokens на max_completion_tokens"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        messages = [{"role": "user", "content": "Hello"}]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback response"
        
        # Первый вызов с max_tokens падает, второй с max_completion_tokens успешен
        with patch.object(provider.client.chat.completions, 'create', side_effect=[
            Exception("max_tokens error"),
            mock_response
        ]) as mock_create:
            result = provider._ask_gpt(messages)
            
            assert result == "Fallback response"
            assert mock_create.call_count == 2
            # Проверяем, что второй вызов был с max_completion_tokens
            second_call = mock_create.call_args_list[1]
            assert "max_completion_tokens" in second_call[1]
            # Проверяем, что кэш установлен
            assert provider._model_tokens_param["gpt-3.5-turbo"] == "max_completion_tokens"


class TestOpenAIProviderSendMessage:
    """Тесты для метода send_message"""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Тест: успешная отправка сообщения"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI Response"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = await provider.send_message(12345, "Hello")
        
        assert isinstance(result, AIResponse)
        assert result.success is True
        assert result.content == "AI Response"
        assert "model" in result.metadata
        assert "provider" in result.metadata

    @pytest.mark.asyncio
    async def test_send_message_with_system_prompt(self):
        """Тест: отправка сообщения с системным промптом"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI Response"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = await provider.send_message(12345, "Hello", system_prompt="You are a helpful assistant")
        
        assert result.success is True
        assert result.content == "AI Response"

    @pytest.mark.asyncio
    async def test_send_message_empty_response(self):
        """Тест: пустой ответ от API"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = await provider.send_message(12345, "Hello")
        
        assert isinstance(result, AIResponse)
        assert result.success is False
        assert "Пустой ответ" in result.error

    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        """Тест: ошибка API"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        # Патчим метод _ask_gpt чтобы он кидал исключение
        original_ask_gpt = provider._ask_gpt
        def raising_ask_gpt(*args, **kwargs):
            raise Exception("API Error")
        
        provider._ask_gpt = raising_ask_gpt
        
        result = await provider.send_message(12345, "Hello")
        
        assert isinstance(result, AIResponse)
        assert result.success is False
        assert "API Error" in result.error or "Ошибка при обращении к OpenAI API" in result.error

    @pytest.mark.asyncio
    async def test_send_message_with_storage(self):
        """Тест: отправка сообщения с использованием storage"""
        mock_storage = AsyncMock()
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo", mock_storage)
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI Response"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = await provider.send_message(12345, "Hello")
        
        assert result.success is True
        # Проверяем, что storage вызывался
        assert mock_storage.save_message.called

    @pytest.mark.asyncio
    async def test_send_message_with_model_override(self):
        """Тест: отправка сообщения с переопределением модели"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "GPT-4 Response"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = await provider.send_message(12345, "Hello", model_override="gpt-4")
        
        assert result.success is True
        assert result.metadata["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_send_message_exception_in_get_history(self):
        """Тест: исключение при получении истории в send_message"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        # Патчим get_conversation_history чтобы кидать исключение
        async def raising_get_history(*args, **kwargs):
            raise Exception("History error")
        
        provider.get_conversation_history = raising_get_history
        
        result = await provider.send_message(12345, "Hello")
        
        assert isinstance(result, AIResponse)
        assert result.success is False
        assert "History error" in result.error


class TestOpenAIProviderSendMessages:
    """Тесты для метода send_messages"""

    @pytest.mark.asyncio
    async def test_send_messages_success(self):
        """Тест: успешная отправка списка сообщений"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        messages = [
            AIMessage("user", "Hello"),
            AIMessage("assistant", "Hi there!")
        ]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI Response"
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = await provider.send_messages(12345, messages)
        
        assert isinstance(result, AIResponse)
        assert result.success is True
        assert result.content == "AI Response"

    @pytest.mark.asyncio
    async def test_send_messages_empty_response(self):
        """Тест: пустой ответ от API"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        messages = [AIMessage("user", "Hello")]
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        
        with patch.object(provider.client.chat.completions, 'create', return_value=mock_response):
            result = await provider.send_messages(12345, messages)
        
        assert isinstance(result, AIResponse)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_send_messages_api_error(self):
        """Тест: ошибка API"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        messages = [AIMessage("user", "Hello")]
        
        with patch.object(provider.client.chat.completions, 'create', side_effect=Exception("API Error")):
            result = await provider.send_messages(12345, messages)
        
        assert isinstance(result, AIResponse)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_send_messages_exception_in_clear_conversation(self):
        """Тест: исключение при очистке истории в send_messages"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        messages = [AIMessage("user", "Hello")]
        
        # Патчим clear_conversation чтобы кидать исключение
        async def raising_clear_conversation(*args, **kwargs):
            raise Exception("Clear error")
        
        provider.clear_conversation = raising_clear_conversation
        
        result = await provider.send_messages(12345, messages)
        
        assert isinstance(result, AIResponse)
        assert result.success is False
        assert "Clear error" in result.error


class TestOpenAIProviderConvertToOpenAIFormat:
    """Тесты для метода _convert_to_openai_format"""

    def test_convert_to_openai_format(self):
        """Тест: конвертация AIMessage в формат OpenAI"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        messages = [
            AIMessage("user", "Hello"),
            AIMessage("assistant", "Hi"),
            AIMessage("system", "You are helpful")
        ]
        
        result = provider._convert_to_openai_format(messages)
        
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi"
        assert result[2]["role"] == "system"
        assert result[2]["content"] == "You are helpful"


class TestOpenAIProviderConversationHistory:
    """Тесты для работы с историей разговора"""

    @pytest.mark.asyncio
    async def test_get_conversation_history_without_storage(self):
        """Тест: получение истории без storage"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        # Добавляем сообщение в память
        await provider.add_message_to_history(12345, AIMessage("user", "Hello"))
        
        history = await provider.get_conversation_history(12345)
        
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_clear_conversation_without_storage(self):
        """Тест: очистка истории без storage"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        # Добавляем сообщения
        await provider.add_message_to_history(12345, AIMessage("user", "Hello"))
        await provider.add_message_to_history(12345, AIMessage("assistant", "Hi"))
        
        # Очищаем
        await provider.clear_conversation(12345)
        
        history = await provider.get_conversation_history(12345)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_get_conversation_length_without_storage(self):
        """Тест: получение длины истории без storage"""
        provider = OpenAIProvider("test-api-key", "gpt-3.5-turbo")
        
        # Добавляем сообщения
        await provider.add_message_to_history(12345, AIMessage("user", "Hello"))
        await provider.add_message_to_history(12345, AIMessage("assistant", "Hi"))
        
        length = await provider.get_conversation_length(12345)
        
        assert length == 2
