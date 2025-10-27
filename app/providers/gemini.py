"""
Google Gemini провайдер для работы с Google Gemini API.
Поддерживает мультимодальность (текст + аудио).
"""

import asyncio
import logging
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import google.generativeai as genai

from .base import BaseAIProvider, ProviderType, AIMessage, AIResponse


logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini провайдер с поддержкой аудио."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", storage=None):
        """
        Инициализация Gemini провайдера.
        
        Args:
            api_key: API ключ для Google Gemini
            model: Модель для использования (по умолчанию gemini-2.0-flash)
            storage: Хранилище для истории диалогов (опционально)
        """
        super().__init__(api_key, model, storage)
        genai.configure(api_key=api_key)
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.GEMINI
    
    def _ask_gemini(
        self, 
        messages: list, 
        audio_bytes: Optional[BytesIO] = None,
        model_override: Optional[str] = None
    ) -> str:
        """
        Синхронная функция для запроса к Gemini API.
        Возвращает текст ответа или кидает исключение.
        """
        model = (model_override or self.model)
        
        model_obj = genai.GenerativeModel(model)
        
        # Если есть аудиофайл, добавляем его в запрос
        if audio_bytes:
            audio_bytes.seek(0)
            audio_data = audio_bytes.read()
            
            # Подготавливаем мультимодальный контент
            contents = {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "audio/ogg",
                            "data": audio_data
                        }
                    },
                    {"text": messages[-1].get("content", "")}
                ]
            }
            
            response = model_obj.generate_content(contents)
        else:
            # Текстовый запрос (как обычно)
            response = model_obj.generate_content(messages)
        
        if not response.text:
            raise ValueError("Пустой ответ от Gemini")
        
        return response.text
    
    async def send_message(
        self, 
        user_id: int, 
        message: str, 
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None,
        audio_bytes: Optional[BytesIO] = None
    ) -> AIResponse:
        """
        Отправляет сообщение в Gemini и возвращает ответ.
        
        Args:
            user_id: ID пользователя для ведения истории
            message: Сообщение пользователя
            system_prompt: Системный промпт (опционально)
            model_override: Модель для использования (опционально)
            audio_bytes: Аудиофайл в формате BytesIO (опционально)
            
        Returns:
            AIResponse с ответом от Gemini
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
            
            # Конвертируем в формат Gemini
            messages = self._convert_to_gemini_format(history)
            
            # Выполняем запрос
            loop = asyncio.get_event_loop()
            assistant_content = await loop.run_in_executor(
                self.executor,
                lambda: self._ask_gemini(messages, audio_bytes, model_override),
            )
            
            # Добавляем ответ ассистента в историю
            assistant_msg = AIMessage("assistant", assistant_content)
            await self.add_message_to_history(user_id, assistant_msg)
            
            return AIResponse(
                content=assistant_content,
                success=True,
                metadata={"model": (model_override or self.model), "provider": "gemini"}
            )
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к Gemini API: {e}")
            return AIResponse(
                content="",
                success=False,
                error=f"Ошибка при обращении к Gemini API: {e}"
            )
    
    async def send_messages(self, user_id: int, messages: List[AIMessage]) -> AIResponse:
        """
        Отправляет список сообщений в Gemini.
        
        Args:
            user_id: ID пользователя
            messages: Список сообщений
            
        Returns:
            AIResponse с ответом от Gemini
        """
        try:
            # Очищаем старую историю и сохраняем новые сообщения
            await self.clear_conversation(user_id)
            for msg in messages:
                await self.add_message_to_history(user_id, msg)
            
            # Конвертируем в формат Gemini
            gemini_messages = self._convert_to_gemini_format(messages)
            
            # Выполняем запрос
            loop = asyncio.get_event_loop()
            assistant_content = await loop.run_in_executor(
                self.executor, 
                lambda: self._ask_gemini(gemini_messages)
            )
            
            # Добавляем ответ ассистента в историю
            assistant_msg = AIMessage("assistant", assistant_content)
            await self.add_message_to_history(user_id, assistant_msg)
            
            return AIResponse(
                content=assistant_content,
                success=True,
                metadata={"model": self.model, "provider": "gemini"}
            )
                
        except Exception as e:
            logger.error(f"Ошибка при обращении к Gemini API: {e}")
            return AIResponse(
                content="",
                success=False,
                error=f"Ошибка при обращении к Gemini API: {e}"
            )
    
    def _convert_to_gemini_format(self, messages: List[AIMessage]) -> List[dict]:
        """Конвертирует AIMessage в формат Gemini"""
        gemini_messages = []
        for msg in messages:
            # Gemini не поддерживает "system" роль как в OpenAI
            # Система указывается отдельно через system_instruction
            if msg.role == "system":
                continue
            
            gemini_messages.append({
                "role": "user" if msg.role == "user" else "model",
                "parts": [{"text": msg.content}]
            })
        
        return gemini_messages
