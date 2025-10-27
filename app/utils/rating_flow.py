from __future__ import annotations

from aiogram import Bot

from app.texts import Texts
from app.repositories.ratings import get_user_rating_for_question, RATING_QUESTIONS
from app.keyboards.ratings import rating_scale_inline, rating_open_inline
from app.handlers.rating import QUESTION_TEXTS


INTRO_LINE = "Пожалуйста, ответьте на три коротких вопроса. Позже сможете изменить ответ через кнопку в главном меню."


async def send_survey_invitation(bot: Bot, chat_id: int, user_id: int) -> None:
    """Отправляет приглашение к опросу с кнопкой для его начала."""
    text = f"{INTRO_LINE}"
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=rating_open_inline(), parse_mode="Markdown")


async def send_intro_and_first_question(bot: Bot, chat_id: int, user_id: int) -> None:
    first_q = RATING_QUESTIONS[0]
    prev = await get_user_rating_for_question(user_id, first_q)
    text = f"{INTRO_LINE}\n\n{Texts.RATE_INTRO}\n\n{QUESTION_TEXTS[first_q]}"
    if prev is not None:
        text += f"\n\nВаш предыдущий ответ: {prev}"
    await bot.send_message(chat_id=chat_id, text=text, reply_markup=rating_scale_inline(first_q), parse_mode="Markdown")


