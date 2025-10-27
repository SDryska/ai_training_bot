from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.keyboards.menu import (
    CALLBACK_NAV_MENU,
    CALLBACK_NAV_RATE,
    get_main_menu_inline,
    remove_reply_keyboard,
)
from app.keyboards.ratings import rating_open_inline
from app.texts import Texts
from app.metrics import measure
from app.services.ai_service import clear_all_conversations

router = Router(name="nav")


@router.callback_query(F.data == CALLBACK_NAV_MENU)
@measure(case="nav", step="back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    # КРИТИЧНО: Очищаем все диалоги при возврате в главное меню
    try:
        await clear_all_conversations(callback.from_user.id)
    except Exception:
        pass
    
    # Очищаем FSM состояние
    try:
        await state.clear()
    except Exception:
        pass
    
    if callback.message:
        try:
            await callback.message.edit_text(Texts.WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=get_main_menu_inline())
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await callback.message.answer(Texts.WELCOME_MESSAGE, parse_mode="Markdown", reply_markup=get_main_menu_inline())
        
        # Скрываем reply-клавиатуру корректно (без пустых сообщений)
        from app.keyboards.menu import remove_reply_keyboard
        await remove_reply_keyboard(callback.message)
    await callback.answer()


@router.callback_query(F.data == CALLBACK_NAV_RATE)
@measure(case="nav", step="open_rate")
async def open_rate_from_menu(callback: CallbackQuery):
    if callback.message:
        try:
            await callback.message.edit_text(Texts.RATE_INTRO, reply_markup=rating_open_inline(), parse_mode="Markdown")
        except Exception:
            await callback.message.answer(Texts.RATE_INTRO, reply_markup=rating_open_inline(), parse_mode="Markdown")
    await callback.answer()

