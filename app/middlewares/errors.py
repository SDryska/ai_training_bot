from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.texts import Texts


logger = logging.getLogger("errors_middleware")


class ErrorsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Необработанное исключение при обработке обновления")
            # Пытаемся уведомить пользователя ненавязчивым способом
            try:
                if isinstance(event, CallbackQuery):
                    # Показываем небольшое уведомление, плюс пытаемся отправить сообщение если возможно
                    await event.answer("❌ Ошибка. Попробуйте ещё раз позже.", show_alert=True)
                    if event.message:
                        await event.message.answer("❌ Произошла ошибка. Попробуйте позже.")
                elif isinstance(event, Message):
                    await event.answer("❌ Произошла ошибка. Попробуйте позже.")
            except Exception:
                # Не даём вторичным ошибкам упасть боту
                pass
            # Подавляем ошибку для продолжения работы бота
            return None
