"""
Тесты для Gemini провайдера.

Тестируемый модуль:
- app/providers/gemini.py

Тестируемые компоненты:
- GeminiProvider класс
- Методы: __init__, send_message, send_messages, _ask_gemini, _convert_to_gemini_format
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

from app.providers.gemini import GeminiProvider
from app.providers.base import AIMessage, AIResponse, ProviderType


class TestGeminiProviderInit:
    """Тесты для __init__ метода"""

    def test_init_basic(self):
        """Тест: базовая инициализация"""
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            assert provider.api_key == "test-api-key"
            assert provider.model == "gemini-2.0-flash"
            assert provider.provider_type == ProviderType.GEMINI
            assert provider.storage is None

    def test_init_with_storage(self):
        """Тест: инициализация с storage"""
        mock_storage = MagicMock()
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash", mock_storage)
            
            assert provider.storage == mock_storage

    def test_init_with_default_model(self):
        """Тест: инициализация с моделью по умолчанию"""
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key")
            
            assert provider.model == "gemini-2.0-flash"


class TestGeminiProviderAskGemini:
    """Тесты для метода _ask_gemini"""

    def test_ask_gemini_text_only(self):
        """Тест: текстовый запрос без аудио"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Hello, how can I help?"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            messages = [{"role": "user", "content": "Hello"}]
            result = provider._ask_gemini(messages)
            
            assert result == "Hello, how can I help?"
            mock_model.generate_content.assert_called_once()

    def test_ask_gemini_with_audio(self):
        """Тест: запрос с аудио"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Transcribed audio"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            messages = [{"role": "user", "content": "What did I say?"}]
            audio_bytes = BytesIO(b"fake audio data")
            result = provider._ask_gemini(messages, audio_bytes)
            
            assert result == "Transcribed audio"
            mock_model.generate_content.assert_called_once()

    def test_ask_gemini_empty_response(self):
        """Тест: пустой ответ от API"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = None
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(ValueError, match="Пустой ответ от Gemini"):
                provider._ask_gemini(messages)

    def test_ask_gemini_error(self):
        """Тест: обработка ошибки API"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_model_class.return_value = mock_model
            
            messages = [{"role": "user", "content": "Hello"}]
            with pytest.raises(Exception, match="API Error"):
                provider._ask_gemini(messages)


class TestGeminiProviderSendMessage:
    """Тесты для метода send_message"""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Тест: успешная отправка сообщения"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "AI Response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            result = await provider.send_message(12345, "Hello")
            
            assert isinstance(result, AIResponse)
            assert result.success is True
            assert result.content == "AI Response"
            assert "model" in result.metadata
            assert "provider" in result.metadata

    @pytest.mark.asyncio
    async def test_send_message_with_system_prompt(self):
        """Тест: отправка сообщения с системным промптом"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "AI Response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            result = await provider.send_message(12345, "Hello", system_prompt="You are helpful")
            
            assert result.success is True
            assert result.content == "AI Response"

    @pytest.mark.asyncio
    async def test_send_message_with_audio(self):
        """Тест: отправка сообщения с аудио"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Audio transcription"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            audio_bytes = BytesIO(b"fake audio data")
            result = await provider.send_message(12345, "What did I say?", audio_bytes=audio_bytes)
            
            assert result.success is True
            assert result.content == "Audio transcription"

    @pytest.mark.asyncio
    async def test_send_message_empty_response(self):
        """Тест: пустой ответ от API"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = None
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            result = await provider.send_message(12345, "Hello")
            
            assert isinstance(result, AIResponse)
            assert result.success is False
            assert "Пустой ответ от Gemini" in result.error

    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        """Тест: ошибка API"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_model_class.return_value = mock_model
            
            result = await provider.send_message(12345, "Hello")
            
            assert isinstance(result, AIResponse)
            assert result.success is False
            assert "API Error" in result.error or "Ошибка при обращении к Gemini API" in result.error

    @pytest.mark.asyncio
    async def test_send_message_with_storage(self):
        """Тест: отправка сообщения с использованием storage"""
        mock_storage = AsyncMock()
        
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash", mock_storage)
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "AI Response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            result = await provider.send_message(12345, "Hello")
            
            assert result.success is True
            # Проверяем, что storage вызывался
            assert mock_storage.save_message.called

    @pytest.mark.asyncio
    async def test_send_message_with_model_override(self):
        """Тест: отправка сообщения с переопределением модели"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Gemini Pro Response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            result = await provider.send_message(12345, "Hello", model_override="gemini-pro")
            
            assert result.success is True
            assert result.metadata["model"] == "gemini-pro"


class TestGeminiProviderSendMessages:
    """Тесты для метода send_messages"""

    @pytest.mark.asyncio
    async def test_send_messages_success(self):
        """Тест: успешная отправка списка сообщений"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            messages = [
                AIMessage("user", "Hello"),
                AIMessage("assistant", "Hi there!")
            ]
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "AI Response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            result = await provider.send_messages(12345, messages)
            
            assert isinstance(result, AIResponse)
            assert result.success is True
            assert result.content == "AI Response"

    @pytest.mark.asyncio
    async def test_send_messages_empty_response(self):
        """Тест: пустой ответ от API"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            messages = [AIMessage("user", "Hello")]
            
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = None
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model
            
            result = await provider.send_messages(12345, messages)
            
            assert isinstance(result, AIResponse)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_send_messages_api_error(self):
        """Тест: ошибка API"""
        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_class:
            
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            messages = [AIMessage("user", "Hello")]
            
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_model_class.return_value = mock_model
            
            result = await provider.send_messages(12345, messages)
            
            assert isinstance(result, AIResponse)
            assert result.success is False


class TestGeminiProviderConvertToGeminiFormat:
    """Тесты для метода _convert_to_gemini_format"""

    def test_convert_to_gemini_format(self):
        """Тест: конвертация AIMessage в формат Gemini"""
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            messages = [
                AIMessage("user", "Hello"),
                AIMessage("assistant", "Hi"),
                AIMessage("system", "You are helpful")  # System messages should be skipped
            ]
            
            result = provider._convert_to_gemini_format(messages)
            
            # System message должен быть пропущен
            assert len(result) == 2
            assert result[0]["role"] == "user"
            assert "parts" in result[0]
            assert result[1]["role"] == "model"
            assert "parts" in result[1]

    def test_convert_to_gemini_format_no_system(self):
        """Тест: конвертация без system сообщений"""
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            messages = [
                AIMessage("user", "Hello"),
                AIMessage("assistant", "Hi")
            ]
            
            result = provider._convert_to_gemini_format(messages)
            
            assert len(result) == 2
            assert result[0]["role"] == "user"
            assert result[1]["role"] == "model"


class TestGeminiProviderConversationHistory:
    """Тесты для работы с историей разговора"""

    @pytest.mark.asyncio
    async def test_get_conversation_history_without_storage(self):
        """Тест: получение истории без storage"""
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            # Добавляем сообщение в память
            await provider.add_message_to_history(12345, AIMessage("user", "Hello"))
            
            history = await provider.get_conversation_history(12345)
            
            assert len(history) == 1
            assert history[0].role == "user"
            assert history[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_clear_conversation_without_storage(self):
        """Тест: очистка истории без storage"""
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
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
        with patch("google.generativeai.configure"):
            provider = GeminiProvider("test-api-key", "gemini-2.0-flash")
            
            # Добавляем сообщения
            await provider.add_message_to_history(12345, AIMessage("user", "Hello"))
            await provider.add_message_to_history(12345, AIMessage("assistant", "Hi"))
            
            length = await provider.get_conversation_length(12345)
            
            assert length == 2

