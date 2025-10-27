from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from pathlib import Path

from app.config.settings import Settings
from app.metrics import METRIC_UPDATES_TOTAL, METRIC_HANDLER_LATENCY
from app.services.auth import normalize_db_url
from app.services.ai_service import clear_all_conversations
from app.texts import Texts
from app.keyboards.menu import get_main_menu_inline, remove_reply_keyboard
from app.repositories.authorized_users import (
    get_role_by_user_id,
    upsert_authorized_user,
    get_authorized_user,
)

router = Router(name="auth")


class AuthStates(StatesGroup):
    waiting_password = State()


async def send_welcome_with_image(message: Message):
    """Отправляет приветственное сообщение с изображением"""
    try:
        # Путь к изображению относительно корня проекта
        image_path = Path(__file__).parent.parent.parent / "imgs" / "greeting_img.jpg"
        
        if image_path.exists():
            # Отправляем изображение с приветственным текстом
            photo = FSInputFile(image_path)
            await message.answer_photo(
                photo=photo,
                caption=Texts.WELCOME_MESSAGE,
                parse_mode="Markdown",
                reply_markup=get_main_menu_inline()
            )
        else:
            # Если изображение не найдено, отправляем только текст
            await message.answer(
                Texts.WELCOME_MESSAGE,
                parse_mode="Markdown",
                reply_markup=get_main_menu_inline()
            )
    except Exception:
        # В случае ошибки отправляем только текст
        await message.answer(
            Texts.WELCOME_MESSAGE,
            parse_mode="Markdown",
            reply_markup=get_main_menu_inline()
        )


@router.message(CommandStart())
@METRIC_HANDLER_LATENCY.time()
async def cmd_start(message: Message, state: FSMContext):
    """Старт: запрашивает пароль, если пользователь ещё не авторизован."""
    METRIC_UPDATES_TOTAL.inc()
    settings = Settings()

    # При любом /start выходим из текущего сценария и скрываем reply-клавиатуру
    try:
        await state.clear()
    except Exception:
        pass
    try:
        from app.keyboards.menu import remove_reply_keyboard
        await remove_reply_keyboard(message)
    except Exception:
        pass
    
    # КРИТИЧНО: Очищаем все диалоги при возврате в главное меню
    try:
        await clear_all_conversations(message.from_user.id)
    except Exception:
        pass

    # Авторизация включена, если задан хотя бы один пароль
    if not (settings.AUTH_PASSWORD_USER or settings.AUTH_PASSWORD_ADMIN):
        await message.answer(Texts.AUTH_DISABLED)
        return

    role = None
    if settings.DATABASE_URL:
        try:
            role = await get_role_by_user_id(message.from_user.id)
        except Exception:
            # Молча пропускаем ошибку, пользователь перейдёт к авторизации
            pass

    if role:
        if role == "user":
            # Показываем приветственное сообщение с меню
            await send_welcome_with_image(message)
            # Скрываем reply-клавиатуру корректно (без пустых сообщений)
            from app.keyboards.menu import remove_reply_keyboard
            await remove_reply_keyboard(message)
        else:
            await message.answer(Texts.ALREADY_AUTH.format(role=role))
        return

    await message.answer(Texts.AUTH_PROMPT)
    await state.set_state(AuthStates.waiting_password)


@router.message(AuthStates.waiting_password)
@METRIC_HANDLER_LATENCY.time()
async def handle_password(message: Message, state: FSMContext):
    settings = Settings()
    pwd = (message.text or "").strip()

    # Принимаем как admin, так и user, но дальнейшие фичи пока делаем для user
    role: str | None = None
    if settings.AUTH_PASSWORD_ADMIN and pwd == settings.AUTH_PASSWORD_ADMIN:
        role = "admin"
    elif settings.AUTH_PASSWORD_USER and pwd == settings.AUTH_PASSWORD_USER:
        role = "user"

    if not role:
        await message.answer(Texts.AUTH_INVALID)
        return

    # Если БД не настроена, то просто завершаем
    if not settings.DATABASE_URL:
        if role == "user":
            await send_welcome_with_image(message)
            from app.keyboards.menu import remove_reply_keyboard
            await remove_reply_keyboard(message)
        else:
            await message.answer(Texts.AUTH_CONFIRMED.format(role=role))
        await state.clear()
        return

    try:
        await upsert_authorized_user(message.from_user.id, role)
        if role == "user":
            await send_welcome_with_image(message)
            from app.keyboards.menu import remove_reply_keyboard
            await remove_reply_keyboard(message)
        else:
            await message.answer(Texts.AUTH_CONFIRMED.format(role=role))
    except Exception as e:
        await message.answer(Texts.DB_ERROR.format(error=e))
    finally:
        await state.clear()


@router.message(Command("dbping"))
@METRIC_HANDLER_LATENCY.time()
async def cmd_dbping(message: Message):
    try:
        import asyncpg

        settings = Settings()
        if not settings.DATABASE_URL:
            await message.answer(Texts.DB_NOT_CONFIGURED)
            return

        url = normalize_db_url(settings.DATABASE_URL)
        conn = await asyncpg.connect(url, timeout=10)
        result = await conn.fetchval("SELECT 1")
        await conn.close()

        await message.answer(Texts.DB_CONNECTED.format(result=result))
    except Exception as e:
        await message.answer(Texts.DB_ERROR.format(error=str(e)))


@router.message(Command("whoami"))
@METRIC_HANDLER_LATENCY.time()
async def cmd_whoami(message: Message):
    settings = Settings()
    if not settings.DATABASE_URL:
        await message.answer(Texts.DB_NOT_CONFIGURED)
        return

    try:
        user = await get_authorized_user(message.from_user.id)
        if user:
            await message.answer(
                Texts.WHOAMI_FOUND.format(role=user["role"], created_at=user["created_at"]) 
            )
        else:
            await message.answer(Texts.WHOAMI_NOT_FOUND)
    except Exception as e:
        await message.answer(Texts.DB_ERROR.format(error=e))


@router.message(Command("change_role"))
@METRIC_HANDLER_LATENCY.time()
async def cmd_change_role(message: Message, state: FSMContext):
    """Переавторизация: запрашиваем пароль снова, переиспользуем состояние waiting_password."""
    settings = Settings()
    if not (settings.AUTH_PASSWORD_USER or settings.AUTH_PASSWORD_ADMIN):
        await message.answer(Texts.AUTH_DISABLED)
        return
    await message.answer(Texts.AUTH_PROMPT_CHANGE)
    await state.set_state(AuthStates.waiting_password)


@router.message(Command("relogin"))
@METRIC_HANDLER_LATENCY.time()
async def cmd_relogin(message: Message, state: FSMContext):
    """Псевдоним для change_role."""
    await cmd_change_role(message, state)
