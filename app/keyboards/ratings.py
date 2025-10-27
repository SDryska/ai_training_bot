from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


CALLBACK_RATE_PREFIX = "rate:"
# rate:open, rate:set:<question>:<value>, rate:next, rate:done


def rating_scale_inline(question_key: str) -> InlineKeyboardMarkup:
    rows = []
    # 1..10 inline buttons, two rows of five
    buttons = [
        InlineKeyboardButton(text=str(i), callback_data=f"{CALLBACK_RATE_PREFIX}set:{question_key}:{i}")
        for i in range(1, 11)
    ]
    rows.append(buttons[:5])
    rows.append(buttons[5:])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def rating_open_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать оценку ⭐", callback_data=f"{CALLBACK_RATE_PREFIX}open")]]
    )



def rating_comment_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data=f"{CALLBACK_RATE_PREFIX}comment:skip")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="nav:menu")],
        ]
    )
