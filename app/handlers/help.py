"""
Обработчики для команд помощи, FAQ и списка команд.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.texts import Texts
from app.keyboards.menu import (
    get_back_menu_inline,
    CALLBACK_NAV_HELP,
    CALLBACK_NAV_FAQ
)

router = Router(name="help")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Показывает список доступных команд."""
    await message.answer(
        Texts.HELP_COMMANDS,
        parse_mode="Markdown",
        reply_markup=get_back_menu_inline()
    )


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    """Показывает часто задаваемые вопросы."""
    await message.answer(
        Texts.FAQ_CONTENT,
        parse_mode="Markdown",
        reply_markup=get_back_menu_inline()
    )


@router.callback_query(F.data == CALLBACK_NAV_HELP)
async def nav_help(callback: CallbackQuery):
    """Обработчик кнопки 'Команды' в меню."""
    if not callback.message:
        await callback.answer()
        return
    
    try:
        await callback.message.edit_text(
            Texts.HELP_COMMANDS,
            parse_mode="Markdown",
            reply_markup=get_back_menu_inline()
        )
    except Exception:
        # Если не удалось отредактировать, отправляем новое сообщение
        await callback.message.answer(
            Texts.HELP_COMMANDS,
            parse_mode="Markdown",
            reply_markup=get_back_menu_inline()
        )
    
    await callback.answer()


@router.callback_query(F.data == CALLBACK_NAV_FAQ)
async def nav_faq(callback: CallbackQuery):
    """Обработчик кнопки 'FAQ' в меню."""
    if not callback.message:
        await callback.answer()
        return
    
    try:
        await callback.message.edit_text(
            Texts.FAQ_CONTENT,
            parse_mode="Markdown",
            reply_markup=get_back_menu_inline()
        )
    except Exception:
        # Если не удалось отредактировать, отправляем новое сообщение
        await callback.message.answer(
            Texts.FAQ_CONTENT,
            parse_mode="Markdown",
            reply_markup=get_back_menu_inline()
        )
    
    await callback.answer()
