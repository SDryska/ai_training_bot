"""
OpenAI провайдер для работы с OpenAI API.
"""

import asyncio
import logging
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

from .base import BaseAIProvider, ProviderType, AIMessage, AIResponse


logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """OpenAI провайдер."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", storage=None):
        """
        Инициализация OpenAI провайдера.
        
        Args:
            api_key: API ключ для OpenAI
            model: Модель для использования (по умолчанию gpt-3.5-turbo)
            storage: Хранилище для истории диалогов (опционально)
        """
        super().__init__(api_key, model, storage)
        self.client = OpenAI(api_key=api_key)
        self.executor = ThreadPoolExecutor(max_workers=5)
        # Кэш предпочтительного параметра токенов для модели: "max_tokens" или "max_completion_tokens"
        self._model_tokens_param: dict[str, str] = {}
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    def _ask_gpt(self, messages: list, model_override: Optional[str] = None) -> Optional[str]:
        """
        Синхронная функция для запроса к OpenAI (как в вашем рабочем коде).
        """
        model = (model_override or self.model)
        # Явная ветка для семейств GPT-5: сначала без лимита (позволяем серверу решить),
        # затем пробуем max_completion_tokens, и только потом общий авто-детект
        model_lc = (model or "").lower()
        if model_lc.startswith("gpt-5"):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    reasoning_effort="low",
                )
                self._model_tokens_param[model] = "none"
                return response.choices[0].message.content
            except Exception as e:
                # Пробуем с max_completion_tokens
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_completion_tokens=500,
                        reasoning_effort="low",
                    )
                    self._model_tokens_param[model] = "max_completion_tokens"
                    return response.choices[0].message.content
                except Exception as e2:
                    logger.warning("OpenAI API gpt-5 branch fallback failed: %s", e2)
                    # Падаем дальше на универсальную попытку/фолбэк

        preferred = self._model_tokens_param.get(model)

        def _call_with(param_name: str):
            if param_name == "max_completion_tokens":
                return self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_completion_tokens=500,
                    reasoning_effort="low",
                )
            else:
                return self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=500,
                    reasoning_effort="low",
                )

        # Если предпочтение уже известно — используем его без пробного запроса
        if preferred in {"max_tokens", "max_completion_tokens"}:
            try:
                response = _call_with(preferred)
                return response.choices[0].message.content
            except Exception as e:
                # Сбрасываем предпочтение и перейдём к авто-детекту ниже
                logger.warning(
                    "Сброс кэша параметра токенов для модели %s из-за ошибки: %s",
                    model,
                    e,
                )
                self._model_tokens_param.pop(model, None)

        # Авто-детект: сперва max_tokens, при 400 — переключаемся и кэшируем
        try:
            response = _call_with("max_tokens")
            self._model_tokens_param[model] = "max_tokens"
            return response.choices[0].message.content
        except Exception as e_first:
            try:
                response = _call_with("max_completion_tokens")
                self._model_tokens_param[model] = "max_completion_tokens"
                return response.choices[0].message.content
            except Exception as e_second:
                logger.error(
                    "Ошибка при обращении к OpenAI API: first=%s; retry(max_completion_tokens)=%s",
                    e_first,
                    e_second,
                )
                return None
    
    async def send_message(
        self, 
        user_id: int, 
        message: str, 
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None
    ) -> AIResponse:
        """
        Отправляет сообщение в OpenAI и возвращает ответ.
        
        Args:
            user_id: ID пользователя для ведения истории
            message: Сообщение пользователя
            system_prompt: Системный промпт (опционально)
            
        Returns:
            AIResponse с ответом от OpenAI
        """
        try:
            # Получаем историю разговора из storage или памяти
            history = await self.get_conversation_history(user_id)
            
            # Если это первое сообщение и есть системный промпт
            if not history and system_prompt:
                system_msg = AIMessage("system", system_prompt)
                await self.add_message_to_history(user_id, system_msg)
                history = await self.get_conversation_history(user_id)
            
            # Добавляем сообщение пользователя в историю
            user_msg = AIMessage("user", message)
            await self.add_message_to_history(user_id, user_msg)
            
            # Получаем обновлённую историю
            history = await self.get_conversation_history(user_id)
            
            # Конвертируем в формат OpenAI
            messages = self._convert_to_openai_format(history)
            
            # Выполняем запрос
            loop = asyncio.get_event_loop()
            error_msg = None
            try:
                assistant_content = await loop.run_in_executor(
                    self.executor,
                    lambda: self._ask_gpt(messages, model_override),
                )
            except Exception as e:
                logger.error(f"Ошибка при обращении к OpenAI API: {e}")
                error_msg = str(e)
                assistant_content = None
            
            if assistant_content:
                # Добавляем ответ ассистента в историю
                assistant_msg = AIMessage("assistant", assistant_content)
                await self.add_message_to_history(user_id, assistant_msg)
                
                return AIResponse(
                    content=assistant_content,
                    success=True,
                    metadata={"model": (model_override or self.model), "provider": "openai"}
                )
            else:
                return AIResponse(
                    content="",
                    success=False,
                    error=error_msg or "Пустой ответ от OpenAI"
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI API: {e}")
            return AIResponse(
                content="",
                success=False,
                error=f"Ошибка при обращении к OpenAI API: {e}"
            )
    
    async def send_messages(self, user_id: int, messages: List[AIMessage]) -> AIResponse:
        """
        Отправляет список сообщений в OpenAI.
        
        Args:
            user_id: ID пользователя
            messages: Список сообщений
            
        Returns:
            AIResponse с ответом от OpenAI
        """
        try:
            # Очищаем старую историю и сохраняем новые сообщения
            await self.clear_conversation(user_id)
            for msg in messages:
                await self.add_message_to_history(user_id, msg)
            
            # Конвертируем в формат OpenAI
            openai_messages = self._convert_to_openai_format(messages)
            
            # Выполняем запрос
            loop = asyncio.get_event_loop()
            assistant_content = await loop.run_in_executor(
                self.executor, 
                self._ask_gpt, 
                openai_messages
            )
            
            if assistant_content:
                # Добавляем ответ ассистента в историю
                assistant_msg = AIMessage("assistant", assistant_content)
                await self.add_message_to_history(user_id, assistant_msg)
                
                return AIResponse(
                    content=assistant_content,
                    success=True,
                    metadata={"model": self.model, "provider": "openai"}
                )
            else:
                return AIResponse(
                    content="",
                    success=False,
                    error="Пустой ответ от OpenAI"
                )
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI API: {e}")
            return AIResponse(
                content="",
                success=False,
                error=str(e)
            )
    
    def _convert_to_openai_format(self, messages: List[AIMessage]) -> List[dict]:
        """Конвертирует AIMessage в формат OpenAI"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]


# Удобные алиасы для обратной совместимости
OpenAIChat = OpenAIProvider
