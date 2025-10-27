from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.keyboards.menu import CALLBACK_NAV_RATE, get_main_menu_inline
from app.keyboards.ratings import CALLBACK_RATE_PREFIX, rating_scale_inline, rating_open_inline, rating_comment_inline
from app.repositories.ratings import upsert_rating, get_user_rating_for_question, RATING_QUESTIONS, insert_rating_comment
from app.repositories.case_stats import has_any_completed
from app.texts import Texts


router = Router(name="rating")


class RatingStates(StatesGroup):
    waiting_comment = State()


QUESTION_TEXTS = {
    "overall_impression": "Как ты оцениваешь общее впечатление от бота?",
    "recommend_to_colleagues": "Насколько ты готов рекомендовать бота коллегам?",
    "will_help_at_work": "Насколько бот пригодится тебе в работе?",
}


def _get_question_order() -> list[str]:
    return ["overall_impression", "recommend_to_colleagues", "will_help_at_work"]


@router.callback_query(F.data == CALLBACK_NAV_RATE)
async def open_rating(callback: CallbackQuery):
    user_id = callback.from_user.id
    # Пропускаем только если пользователь завершил хотя бы один кейс
    try:
        allowed = await has_any_completed(user_id)
    except Exception:
        allowed = False
    if not allowed:
        await _deny_rating(callback)
        return
    order = _get_question_order()
    first_q = order[0]
    # Покажем первый вопрос с клавиатурой 1..10 и, если была оценка, отобразим
    prev = await get_user_rating_for_question(user_id, first_q)
    header = Texts.RATE_INTRO
    text = f"{header}\n\n{QUESTION_TEXTS[first_q]}"
    if prev is not None:
        text += f"\n\nТвой предыдущий ответ: {prev}"

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=rating_scale_inline(first_q), parse_mode="Markdown")
        except Exception:
            await callback.message.answer(text, reply_markup=rating_scale_inline(first_q), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == f"{CALLBACK_RATE_PREFIX}open")
async def open_rating_from_start_button(callback: CallbackQuery):
    user_id = callback.from_user.id
    # Пропускаем только если пользователь завершил хотя бы один кейс
    try:
        allowed = await has_any_completed(user_id)
    except Exception:
        allowed = False
    if not allowed:
        await _deny_rating(callback)
        return
    order = _get_question_order()
    first_q = order[0]
    prev = await get_user_rating_for_question(user_id, first_q)
    header = Texts.RATE_INTRO
    text = f"{header}\n\n{QUESTION_TEXTS[first_q]}"
    if prev is not None:
        text += f"\n\nТвой предыдущий ответ: {prev}"

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=rating_scale_inline(first_q))
        except Exception:
            await callback.message.answer(text, reply_markup=rating_scale_inline(first_q))
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CALLBACK_RATE_PREFIX}set:"))
async def set_rating(callback: CallbackQuery, state: FSMContext):
    # Формат: rate:set:<вопрос>:<значение>
    try:
        _, _, question_key, value_str = callback.data.split(":", 3)
        value = int(value_str)
        if value < 1 or value > 10:
            raise ValueError("bad range")
    except Exception:
        await callback.answer("Некорректное значение", show_alert=True)
        return

    user_id = callback.from_user.id
    # Получаем предыдущую оценку до обновления
    prev_before = await get_user_rating_for_question(user_id, question_key)
    await upsert_rating(user_id, question_key, value)

    # Отобразить сразу над кнопками (редактированием того же сообщения)
    text = f"{QUESTION_TEXTS[question_key]}"
    if prev_before is not None:
        text += f"\n\nПредыдущая оценка: {prev_before}"
    text += f"\n\nТы поставил: {value}"
    await _edit_or_answer(callback, text, rating_scale_inline(question_key))

    # Переход к следующему вопросу
    order = _get_question_order()
    try:
        idx = order.index(question_key)
    except ValueError:
        idx = -1
    next_idx = idx + 1
    if 0 <= idx and next_idx < len(order):
        next_q = order[next_idx]
        prev = await get_user_rating_for_question(user_id, next_q)
        next_text = f"{QUESTION_TEXTS[next_q]}"
        if prev is not None:
            next_text += f"\n\nТвой предыдущий ответ: {prev}"
        # отправим новое сообщение с следующим вопросом
        await callback.message.answer(next_text, reply_markup=rating_scale_inline(next_q), parse_mode="Markdown")
    else:
        # завершение рейтинговых вопросов — запросим свободный комментарий
        await callback.message.answer(Texts.RATE_COMMENT_PROMPT, reply_markup=rating_comment_inline(), parse_mode="Markdown")
        await state.set_state(RatingStates.waiting_comment)
        await callback.answer()


async def _edit_or_answer(callback: CallbackQuery, text: str, markup):
    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=markup, parse_mode="Markdown")
            return
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=markup, parse_mode="Markdown")


async def _deny_rating(callback: CallbackQuery):
    msg = "Опрос доступен после завершения хотя бы одного кейса. Начни любой кейс из меню."
    if callback.message:
        try:
            await callback.message.edit_text(msg, reply_markup=get_main_menu_inline(), parse_mode="Markdown")
        except Exception:
            await callback.message.answer(msg, reply_markup=get_main_menu_inline(), parse_mode="Markdown")
    await callback.answer()



@router.callback_query(F.data == f"{CALLBACK_RATE_PREFIX}comment:skip")
async def skip_comment(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(Texts.RATE_THANKS, reply_markup=get_main_menu_inline(), parse_mode="Markdown")
    await callback.answer()


@router.message(RatingStates.waiting_comment, F.text.len() > 0)
async def receive_comment(message: Message, state: FSMContext):
    comment = (message.text or "").strip()
    if comment:
        try:
            await insert_rating_comment(message.from_user.id, comment)
        except Exception:
            pass
        await message.answer(Texts.RATE_COMMENT_SAVED, reply_markup=get_main_menu_inline(), parse_mode="Markdown")
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправь текстовый комментарий или нажми Пропустить.")
