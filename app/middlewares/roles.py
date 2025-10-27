from __future__ import annotations

from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from app.repositories.authorized_users import get_role_by_user_id


class RolesMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        role = None
        if user_id is not None:
            try:
                role = await get_role_by_user_id(user_id)
            except Exception:
                # Корректный фолбэк, когда БД недоступна или неправильно настроена
                role = None
        # Добавляем в контекст
        data["user_role"] = role
        data["is_admin"] = role == "admin"
        data["is_user"] = role == "user"

        return await handler(event, data)
