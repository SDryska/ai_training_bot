from aiogram import Router
from aiogram.types import Message, CallbackQuery

from app.texts import Texts
from app.metrics import measure

router = Router(name="fallback")


@router.message()
@measure(case="fallback", step="unknown_message")
async def unknown_message(message: Message) -> None:
    await message.answer(Texts.UNKNOWN_COMMAND)


@router.callback_query()
@measure(case="fallback", step="unknown_callback")
async def unknown_callback(callback: CallbackQuery) -> None:
    # Показываем небольшой alert без изменения сообщения
    await callback.answer(Texts.UNKNOWN_CALLBACK, show_alert=True)
