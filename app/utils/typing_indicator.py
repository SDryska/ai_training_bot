"""
Утилиты для индикаторов загрузки и "печатания" персонажей.
"""

import asyncio
from aiogram.types import Message
from aiogram import Bot


class TypingIndicator:
    """Класс для управления индикаторами загрузки."""
    
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.indicator_message = None
        
    async def show_character_typing(self, character_name: str, character_emoji: str = "💬") -> None:
        """Показывает индикатор что персонаж думает."""
        try:
            typing_text = f"{character_emoji} **{character_name} думает...**"
            self.indicator_message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=typing_text,
                parse_mode="Markdown"
            )
        except Exception:
            # Если не удалось показать индикатор - не критично
            pass
    
    async def show_character_listening(self, character_name: str, character_emoji: str = "🎧") -> None:
        """Показывает индикатор что персонаж слушает аудио."""
        try:
            listening_text = f"{character_emoji} **{character_name} слушает аудио...**"
            self.indicator_message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=listening_text,
                parse_mode="Markdown"
            )
        except Exception:
            # Если не удалось показать индикатор - не критично
            pass
    
    async def show_analysis_indicator(self) -> None:
        """Показывает индикатор анализа диалога."""
        try:
            analysis_text = "🔍 **Анализирую диалог...**\n\n⏳ Это займет несколько секунд"
            self.indicator_message = await self.bot.send_message(
                chat_id=self.chat_id,
                text=analysis_text,
                parse_mode="Markdown"
            )
        except Exception:
            # Если не удалось показать индикатор - не критично
            pass
    
    async def hide_indicator(self) -> None:
        """Скрывает индикатор загрузки."""
        if self.indicator_message:
            try:
                await self.bot.delete_message(
                    chat_id=self.chat_id,
                    message_id=self.indicator_message.message_id
                )
            except Exception:
                # Сообщение уже удалено или недоступно - игнорируем
                pass
            finally:
                self.indicator_message = None


async def with_typing_indicator(
    bot: Bot, 
    chat_id: int, 
    character_name: str, 
    character_emoji: str,
    async_operation
) -> any:
    """
    Выполняет асинхронную операцию с индикатором размышлений персонажа.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        character_name: Имя персонажа
        character_emoji: Эмодзи персонажа
        async_operation: Асинхронная функция для выполнения
    
    Returns:
        Результат выполнения async_operation
    """
    indicator = TypingIndicator(bot, chat_id)
    
    try:
        # Показываем индикатор размышлений
        await indicator.show_character_typing(character_name, character_emoji)
        
        # Небольшая задержка для визуального эффекта
        await asyncio.sleep(0.5)
        
        # Выполняем операцию
        result = await async_operation()
        
        return result
        
    finally:
        # Всегда скрываем индикатор
        await indicator.hide_indicator()


async def with_listening_indicator(
    bot: Bot, 
    chat_id: int, 
    character_name: str, 
    character_emoji: str,
    async_operation
) -> any:
    """
    Выполняет асинхронную операцию с индикатором прослушивания аудио персонажем.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        character_name: Имя персонажа
        character_emoji: Эмодзи персонажа
        async_operation: Асинхронная функция для выполнения
    
    Returns:
        Результат выполнения async_operation
    """
    indicator = TypingIndicator(bot, chat_id)
    
    try:
        # Показываем индикатор прослушивания
        await indicator.show_character_listening(character_name, character_emoji)
        
        # Небольшая задержка для визуального эффекта
        await asyncio.sleep(0.3)
        
        # Выполняем операцию
        result = await async_operation()
        
        return result
        
    finally:
        # Всегда скрываем индикатор
        await indicator.hide_indicator()


async def with_analysis_indicator(
    bot: Bot,
    chat_id: int,
    async_operation
) -> any:
    """
    Выполняет асинхронную операцию с индикатором анализа.
    
    Args:
        bot: Экземпляр бота
        chat_id: ID чата
        async_operation: Асинхронная функция для выполнения
    
    Returns:
        Результат выполнения async_operation
    """
    indicator = TypingIndicator(bot, chat_id)
    
    try:
        # Показываем индикатор анализа
        await indicator.show_analysis_indicator()
        
        # Небольшая задержка для визуального эффекта
        await asyncio.sleep(0.8)
        
        # Выполняем операцию
        result = await async_operation()
        
        return result
        
    finally:
        # Всегда скрываем индикатор
        await indicator.hide_indicator()
