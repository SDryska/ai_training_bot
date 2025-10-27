from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import List, Dict

# Централизованная конфигурация меню
MENU_ITEMS: List[Dict[str, str]] = [
    {"id": "fb_employee", "title": "📋 Обратная связь подчиненному"},
    {"id": "fb_peer", "title": "👥 Обратная связь коллеге"},
    {"id": "career_dialog", "title": "🚀 Карьерный диалог"},
]

BACK_TO_MENU_TITLE: str = "🏠 Главное меню"
CALLBACK_PREFIX_MENU: str = "menu:"
CALLBACK_NAV_MENU: str = "nav:menu"
CALLBACK_NAV_RATE: str = "nav:rate"
CALLBACK_NAV_HELP: str = "nav:help"
CALLBACK_NAV_FAQ: str = "nav:faq"

# Управления, специфичные для кейсов
CALLBACK_CASE_PREFIX: str = "case:"
CALLBACK_CASE_RESTART_TEMPLATE: str = CALLBACK_CASE_PREFIX + "{case_id}:restart"
CALLBACK_CASE_REVIEW_TEMPLATE: str = CALLBACK_CASE_PREFIX + "{case_id}:review"

# Для обратной совместимости с существующим кодом
CALLBACK_CASE_RESTART: str = "case:fb_employee:restart"
CALLBACK_CASE_REVIEW: str = "case:fb_employee:review"

# Case action callbacks
CALLBACK_CASE_START: str = "start_dialog"
CALLBACK_CASE_THEORY: str = "theory"

# Reply keyboard button texts
KB_CASE_RESTART: str = "🔄 Начать заново"
KB_CASE_REVIEW: str = "📊 Получить анализ"
KB_BACK_TO_MENU: str = "🏠 В главное меню"


# Устаревшие вспомогательные функции ReplyKeyboard удалены; остаётся только inline UI


def get_main_menu_inline() -> InlineKeyboardMarkup:
    # Основные кейсы
    rows = [
        [InlineKeyboardButton(text=item["title"], callback_data=f"{CALLBACK_PREFIX_MENU}{item['id']}")]
        for item in MENU_ITEMS
    ]
    
    # Добавляем кнопки помощи
    help_row = [
        InlineKeyboardButton(text="❓ FAQ", callback_data=CALLBACK_NAV_FAQ),
        InlineKeyboardButton(text="⭐ Оценить бота", callback_data=CALLBACK_NAV_RATE),
    ]
    rows.append(help_row)
    
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_back_menu_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BACK_TO_MENU_TITLE, callback_data=CALLBACK_NAV_MENU)]]
    )


def get_case_controls_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data=CALLBACK_CASE_RESTART),
                InlineKeyboardButton(text="📊 Получить анализ", callback_data=CALLBACK_CASE_REVIEW),
            ],
            [InlineKeyboardButton(text=BACK_TO_MENU_TITLE, callback_data=CALLBACK_NAV_MENU)],
        ]
    )


def get_case_controls_reply() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=KB_CASE_RESTART), KeyboardButton(text=KB_CASE_REVIEW)],
            [KeyboardButton(text=KB_BACK_TO_MENU)]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
        input_field_placeholder="Введите ваше сообщение...",
    )


def get_case_after_review_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data=CALLBACK_CASE_RESTART)],
            [InlineKeyboardButton(text=BACK_TO_MENU_TITLE, callback_data=CALLBACK_NAV_MENU)],
        ]
    )


def get_case_after_review_inline_by_case(case_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру после рецензии с правильным callback для каждого кейса."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔄 Попробовать еще раз", 
                callback_data=CALLBACK_CASE_RESTART_TEMPLATE.format(case_id=case_id)
            )],
            [InlineKeyboardButton(text=BACK_TO_MENU_TITLE, callback_data=CALLBACK_NAV_MENU)],
        ]
    )


def get_case_controls_inline_by_case(case_id: str) -> InlineKeyboardMarkup:
    """Создает контрольные кнопки с правильным callback для каждого кейса."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Попробовать еще раз", 
                    callback_data=CALLBACK_CASE_RESTART_TEMPLATE.format(case_id=case_id)
                ),
                InlineKeyboardButton(
                    text="📊 Получить анализ", 
                    callback_data=CALLBACK_CASE_REVIEW_TEMPLATE.format(case_id=case_id)
                ),
            ],
            [InlineKeyboardButton(text=BACK_TO_MENU_TITLE, callback_data=CALLBACK_NAV_MENU)],
        ]
    )


def get_case_description_inline(case_id: str) -> InlineKeyboardMarkup:
    """Создает клавиатуру для описания кейса с кнопками действий."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Начать тренировку", callback_data=f"case:{case_id}:start")],
            [InlineKeyboardButton(text="📚 Изучить теорию", callback_data=f"case:{case_id}:theory")],
            [InlineKeyboardButton(text=BACK_TO_MENU_TITLE, callback_data=CALLBACK_NAV_MENU)],
        ]
    )


def get_disabled_buttons_markup() -> InlineKeyboardMarkup:
    """Создает клавиатуру с отключенными кнопками (пустую)."""
    return InlineKeyboardMarkup(inline_keyboard=[])


async def disable_previous_buttons(message, bot=None):
    """Отключает инлайн-кнопки в сообщении, заменяя их на пустую клавиатуру."""
    if not message:
        return
    
    try:
        # Используем bot из message если не передан отдельно
        if bot is None:
            bot = message.bot
            
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=get_disabled_buttons_markup()
        )
    except Exception:
        # Игнорируем ошибки (сообщение могло быть уже изменено или удалено)
        pass


async def remove_reply_keyboard(message):
    """Скрывает reply-клавиатуру, не оставляя видимых сообщений в чате."""
    from aiogram.types import ReplyKeyboardRemove
    import asyncio
    try:
        # Отправляем неразрывный пробел и сразу удаляем сообщение
        tmp = await message.answer("\u00A0", reply_markup=ReplyKeyboardRemove())
        # Даем клиенту время применить удаление клавиатуры
        await asyncio.sleep(0.4)
        try:
            await message.bot.delete_message(chat_id=tmp.chat.id, message_id=tmp.message_id)
        except Exception:
            # Если удаление не удалось — просто игнорируем, это не критично
            pass
    except Exception:
        # Если отправка не удалась — пропускаем, чтобы не ломать поток
        pass


async def disable_buttons_by_id(bot, chat_id: int, message_id: int) -> None:
    """Отключает инлайн-кнопки у сообщения по id."""
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=get_disabled_buttons_markup())
    except Exception:
        # Сообщение уже изменено/удалено — пропускаем
        pass
