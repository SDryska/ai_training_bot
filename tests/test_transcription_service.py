"""
Тесты для сервиса транскрибации.

Тестируемый модуль:
- app/services/transcription_service.py

Тестируемые компоненты:
- transcribe_voice_ogg функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

from app.services.transcription_service import transcribe_voice_ogg

# Добавляем импорт AsyncMock для использования в patch


def create_test_audio_bytes() -> BytesIO:
    """Создает тестовый BytesIO с аудио данными"""
    return BytesIO(b"fake audio data")


class TestTranscribeVoiceOgg:
    """Тесты для функции transcribe_voice_ogg"""

    @pytest.mark.asyncio
    async def test_transcribe_success(self):
        """Тест: успешная транскрибация"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 3
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Transcribed text"
            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == "Transcribed text"
            assert mock_client.audio.transcriptions.create.called

    @pytest.mark.asyncio
    async def test_transcribe_empty_result(self):
        """Тест: пустой результат транскрибации"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 1
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = ""
            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == ""

    @pytest.mark.asyncio
    async def test_transcribe_fallback_model(self):
        """Тест: использование fallback модели whisper-1"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 1
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            
            # Первая модель возвращает пустой результат
            mock_response_empty = MagicMock()
            mock_response_empty.text = ""
            
            # Fallback модель возвращает результат
            mock_response_success = MagicMock()
            mock_response_success.text = "Fallback result"
            
            mock_client.audio.transcriptions.create.side_effect = [
                mock_response_empty,
                mock_response_success
            ]
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == "Fallback result"
            assert mock_client.audio.transcriptions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_transcribe_with_retries(self):
        """Тест: повторные попытки при ошибке"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 3
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Success after retry"
            
            # Первые две попытки падают с ошибкой, третья успешна
            # Каждая попытка делает вызов основной модели + fallback модели при ошибке основной
            mock_client.audio.transcriptions.create.side_effect = [
                Exception("Error 1"),  # Попытка 1 - основная модель
                Exception("Error 1 fallback"),  # Попытка 1 - fallback
                Exception("Error 2"),  # Попытка 2 - основная модель
                Exception("Error 2 fallback"),  # Попытка 2 - fallback
                mock_response  # Попытка 3 - успех
            ]
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == "Success after retry"
            assert mock_client.audio.transcriptions.create.call_count == 5  # 2 попытки * 2 модели + 1 успешная
            assert mock_sleep.call_count == 2  # Sleep после первой и второй попытки

    @pytest.mark.asyncio
    async def test_transcribe_timeout(self):
        """Тест: обработка таймаута"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class, \
             patch("asyncio.wait_for") as mock_wait_for:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 2
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 5.0
            
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client
            
            # Все попытки падают с таймаутом
            import asyncio
            mock_wait_for.side_effect = asyncio.TimeoutError()
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == ""

    @pytest.mark.asyncio
    async def test_transcribe_dict_response(self):
        """Тест: обработка ответа в виде словаря"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 1
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            # Возвращаем словарь вместо объекта с атрибутом text
            mock_client.audio.transcriptions.create.return_value = {"text": "Dict response"}
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == "Dict response"

    @pytest.mark.asyncio
    async def test_transcribe_no_text_attr(self):
        """Тест: обработка ответа без атрибута text"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 1
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            mock_response = MagicMock()
            del mock_response.text  # Удаляем атрибут text
            mock_client.audio.transcriptions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == ""

    @pytest.mark.asyncio
    async def test_transcribe_all_retries_fail(self):
        """Тест: все попытки завершились ошибкой"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 2
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 1.0
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            # Каждая попытка вызывает основную модель и fallback
            mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == ""
            assert mock_client.audio.transcriptions.create.call_count == 4  # 2 попытки * 2 модели

    @pytest.mark.asyncio
    async def test_transcribe_with_non_timeout_exception(self):
        """Тест: обработка исключения кроме TimeoutError"""
        audio_bytes = create_test_audio_bytes()
        
        with patch("app.services.transcription_service.Settings") as mock_settings, \
             patch("app.services.transcription_service.OpenAI") as mock_openai_class:
            
            mock_settings.return_value.OPENAI_API_KEY = "test-key"
            mock_settings.return_value.TRANSCRIBE_MAX_RETRIES = 1
            mock_settings.return_value.TRANSCRIBE_RETRY_BACKOFF_SEC = 0.1
            mock_settings.return_value.TRANSCRIBE_TIMEOUT_SEC = 30.0
            
            mock_client = MagicMock()
            mock_client.audio.transcriptions.create.side_effect = ValueError("Different error")
            mock_openai_class.return_value = mock_client
            
            result = await transcribe_voice_ogg(audio_bytes)
            
            assert result == ""

