"""
Шлюз для выбора и управления AI провайдерами.
"""

import logging
from typing import Dict, Optional, Type
from enum import Enum

from .base import BaseAIProvider, ProviderType, AIResponse
from app.config.settings import Settings
import asyncio
from .openai import OpenAIProvider
from app.services.validation_service import validator, ValidationError


logger = logging.getLogger(__name__)


class AIProviderGateway:
    """Шлюз для управления AI провайдерами"""
    
    def __init__(self):
        self._providers: Dict[ProviderType, BaseAIProvider] = {}
        self._default_provider: Optional[ProviderType] = None
    
    def register_provider(
        self, 
        provider_type: ProviderType, 
        provider: BaseAIProvider,
        is_default: bool = False
    ) -> None:
        """
        Регистрирует провайдера в шлюзе.
        
        Args:
            provider_type: Тип провайдера
            provider: Экземпляр провайдера
            is_default: Использовать как провайдер по умолчанию
        """
        self._providers[provider_type] = provider
        
        if is_default or self._default_provider is None:
            self._default_provider = provider_type
        
        logger.info(f"Зарегистрирован провайдер: {provider_type.value}")
    
    def get_provider(self, provider_type: Optional[ProviderType] = None) -> Optional[BaseAIProvider]:
        """
        Получает провайдера по типу или провайдера по умолчанию.
        
        Args:
            provider_type: Тип провайдера (если None, возвращает провайдер по умолчанию)
            
        Returns:
            Экземпляр провайдера или None
        """
        if provider_type is None:
            provider_type = self._default_provider
        
        return self._providers.get(provider_type)
    
    def get_available_providers(self) -> list[ProviderType]:
        """Возвращает список доступных провайдеров"""
        return list(self._providers.keys())
    
    async def send_message(
        self,
        user_id: int,
        message: str,
        system_prompt: Optional[str] = None,
        provider_type: Optional[ProviderType] = None,
        model_override: Optional[str] = None,
        audio_bytes = None
    ) -> AIResponse:
        """
        Отправляет сообщение через указанный или дефолтный провайдер.
        
        Args:
            user_id: ID пользователя
            message: Сообщение
            system_prompt: Системный промпт
            provider_type: Тип провайдера (если None, использует дефолтный)
            model_override: Модель для использования (опционально)
            audio_bytes: Аудиофайл для мультимодальных провайдеров (опционально)
            
        Returns:
            AIResponse с ответом
        """
        logger.debug(f"Gateway.send_message: user={user_id}, provider_type={provider_type}, model={model_override}")
        
        provider = self.get_provider(provider_type)
        
        if not provider:
            available = [p.value for p in self.get_available_providers()]
            error_msg = f"Провайдер недоступен. Запрошен: {provider_type}, Доступные: {available}"
            logger.error(error_msg)
            return AIResponse(
                content="",
                success=False,
                error=error_msg
            )
        
        # Валидация пользовательского ввода выполняется на уровне хэндлеров.
        # На уровне gateway не валидируем, чтобы не затрагивать системные промпты/AI ответы.
        validated_message = message
        validated_system_prompt = system_prompt
        
        settings = Settings()
        max_retries = max(1, settings.AI_REQUEST_MAX_RETRIES)
        timeout_sec = max(1.0, settings.AI_REQUEST_TIMEOUT_SEC)
        backoff = max(0.0, settings.AI_REQUEST_RETRY_BACKOFF_SEC)

        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                # Для Gemini провайдера передаём аудиобайты
                if audio_bytes and hasattr(provider, 'send_message') and provider.provider_type == ProviderType.GEMINI:
                    coro = provider.send_message(
                        user_id, 
                        validated_message, 
                        validated_system_prompt, 
                        model_override,
                        audio_bytes=audio_bytes
                    )
                else:
                    coro = provider.send_message(user_id, validated_message, validated_system_prompt, model_override)

                # Таймаут на уровне шлюза
                return await asyncio.wait_for(coro, timeout=timeout_sec)
            except Exception as e:
                last_error = e
                logger.warning(
                    "Gateway attempt %d/%d failed for provider=%s model=%s: %s",
                    attempt, max_retries, getattr(provider, 'provider_type', '?'), model_override, e,
                    exc_info=True,
                )
                if attempt < max_retries:
                    await asyncio.sleep(backoff * attempt)
                else:
                    error_msg = f"Ошибка провайдера {getattr(provider, 'provider_type', '?')}: {e}"
                    return AIResponse(content="", success=False, error=error_msg)
    
    async def clear_conversation(self, user_id: int, provider_type: Optional[ProviderType] = None) -> None:
        """Очищает историю разговора у провайдера"""
        provider = self.get_provider(provider_type)
        if provider:
            await provider.clear_conversation(user_id)


# Глобальный экземпляр шлюза
gateway = AIProviderGateway()
