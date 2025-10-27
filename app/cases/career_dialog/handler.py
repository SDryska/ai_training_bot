"""
Обработчик для кейса "Карьерный диалог".
Содержит логику карьерного диалога с сотрудником,
запуск по кнопке меню и поддержку голосовых сообщений.
"""

import json
import logging
import asyncio
from io import BytesIO
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove

from app.services.transcription_service import transcribe_voice_ogg
from app.services.validation_service import validator, ValidationError

from app.metrics import measure
from app.services.ai_service import (
    clear_case_conversations,
    send_dialogue_message,
    send_reviewer_message,
)
from app.utils.typing_indicator import with_typing_indicator, with_analysis_indicator, with_listening_indicator
from app.utils.case_stats import (
    mark_case_started,
    mark_case_completed,
    mark_case_out_of_moves,
    mark_case_auto_finished,
)
from app.repositories.case_stats import has_any_completed
from app.utils.rating_flow import send_survey_invitation
from app.repositories.rating_invites import acquire_rating_invite_lock
from app.keyboards.menu import (
    CALLBACK_PREFIX_MENU,
    get_case_controls_inline,
    get_case_controls_reply,
    CALLBACK_CASE_RESTART,
    CALLBACK_CASE_REVIEW,
    KB_CASE_RESTART,
    KB_CASE_REVIEW,
    KB_BACK_TO_MENU,
    get_case_after_review_inline,
    get_case_after_review_inline_by_case,
    get_case_controls_inline_by_case,
    get_case_description_inline,
    disable_previous_buttons,
    remove_reply_keyboard,
    disable_buttons_by_id,
)
from app.texts import Texts
from .config import CareerDialogConfig

logger = logging.getLogger(__name__)
router = Router(name="case_career_dialog")
# Ключ для хранения id последнего сообщения с инлайн-кнопками в FSM
ACTIVE_INLINE_MSG_ID_KEY = "active_inline_message_id"


def parse_ai_response(response_text: str) -> dict:
    """Парсит JSON ответ от ИИ с fallback на обычный текст."""
    try:
        # Пытаемся найти JSON в ответе
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Проверяем обязательные поля
            if "ReplyText" in parsed:
                return parsed
                
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse AI JSON response: %s", e)
    
    # Fallback: возвращаем весь текст как ReplyText
    return {
        "ReplyText": response_text,
        "Aspirations": False,
        "Strengths": False,
        "Development": False,
        "Opportunities": False,
        "Plan": False
    }


def format_career_response(parsed_response: dict, show_analysis: bool = False) -> str:
    """Форматирует ответ для отображения пользователю."""
    reply_text = parsed_response.get("ReplyText", "")
    
    if not show_analysis:
        return f"{CareerDialogConfig.MAXIM_EMOJI} *Максим:* {reply_text}"
    
    # Для админов показываем анализ компонентов карьерного диалога
    analysis_parts = []
    
    for key, label in CareerDialogConfig.CAREER_LABELS.items():
        status = "✅" if parsed_response.get(key, False) else "❌"
        analysis_parts.append(f"{status} {label}")
    
    analysis = "\n".join(analysis_parts)
    
    return f"""{CareerDialogConfig.MAXIM_EMOJI} *Максим:* {reply_text}

{CareerDialogConfig.ANALYSIS_EMOJI} *Анализ карьерного диалога:*
{analysis}"""


def parse_reviewer_response(response_text: str) -> dict:
    """Парсит JSON ответ от рецензента с fallback."""
    try:
        # Пытаемся найти JSON в ответе
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            # Проверяем обязательные поля
            if "overall" in parsed:
                return parsed
                
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse reviewer JSON response: %s", e)
    
    # Fallback: простая структура с исходным текстом
    return {
        "overall": response_text,
        "goodPoints": [],
        "improvementPoints": []
    }


def format_review_response(parsed_review: dict) -> str:
    """Форматирует финальный отзыв рецензента для пользователя."""
    overall = parsed_review.get("overall", "")
    good_points = parsed_review.get("goodPoints", [])
    improvement_points = parsed_review.get("improvementPoints", [])
    
    # Формируем красивое сообщение
    message_parts = [
        CareerDialogConfig.REVIEW_TITLE,
        CareerDialogConfig.REVIEW_OVERALL_LABEL.format(overall=overall)
    ]
    
    if good_points:
        message_parts.append(CareerDialogConfig.REVIEW_GOOD_POINTS_LABEL)
        for i, point in enumerate(good_points, 1):
            message_parts.append(f"{i}. {point}")
        message_parts.append("")
    
    if improvement_points:
        message_parts.append(CareerDialogConfig.REVIEW_IMPROVEMENT_LABEL)
        for i, point in enumerate(improvement_points, 1):
            message_parts.append(f"{i}. {point}")
        message_parts.append("")
    
    message_parts.append(CareerDialogConfig.REVIEW_RESTART_MESSAGE)
    
    return "\n".join(message_parts)


def extract_dialogue_text(dialogue_entries: list) -> str:
    """Извлекает только диалог для рецензента (без анализа компонентов)."""
    dialogue_lines = []
    for entry in dialogue_entries:
        role = entry.get("role", "")
        text = entry.get("text", "")
        if role and text:
            dialogue_lines.append(f"{role}: {text}")
    return "\n\n".join(dialogue_lines)


async def perform_dialogue_review(dialogue_entries: list, session_id: str) -> str:
    """Вызывает рецензента для анализа завершенного диалога."""
    
    try:
        # Извлекаем чистый диалог без анализа компонентов
        dialogue_text = extract_dialogue_text(dialogue_entries)
        
        if not dialogue_text.strip():
            return CareerDialogConfig.ERROR_SHORT_DIALOGUE
        
        # Формируем промпт для рецензента
        reviewer_prompt = CareerDialogConfig.get_reviewer_prompt(dialogue_text)
        
        # Отправляем на новую сессию рецензента
        logger.info(
            "Reviewer call: session=%s_review, dialogue_len=%d, prompt_len=%d",
            session_id,
            len(dialogue_text or ""),
            len(reviewer_prompt or ""),
        )
        
        # Используем отдельную сессию для рецензента (очищаем контекст)
        reviewer_user_id = int(session_id.split(':')[0]) + 999999  # Отдельный ID для рецензента
        await clear_case_conversations(CareerDialogConfig.CASE_ID, reviewer_user_id)

        response = await send_reviewer_message(
            case_id=CareerDialogConfig.CASE_ID,
            user_id=reviewer_user_id,
            message=reviewer_prompt,
            system_prompt=CareerDialogConfig.REVIEWER_SYSTEM_PROMPT,
        )

        if not response.success:
            return CareerDialogConfig.ERROR_DIALOGUE_REVIEW.format(
                error_type="AI_Error",
                error_message=response.error or "Не получен ответ от AI",
            )
        
        # Парсим ответ рецензента
        parsed_review = parse_reviewer_response(response.content)
        
        # Форматируем финальный ответ
        return format_review_response(parsed_review)
        
    except Exception as e:
        logger.error("Error in dialogue review: %s (%s)", e, type(e).__name__)
        return CareerDialogConfig.ERROR_DIALOGUE_REVIEW.format(
            error_type=type(e).__name__, 
            error_message=str(e)
        )


class CareerChat(StatesGroup):
    waiting_user = State()
    review_complete = State()  # Состояние после завершения рецензирования




# Запуск по команде (для тестирования)
@router.message(Command("career"))
@measure(case=CareerDialogConfig.CASE_ID, step="start")
async def career_start(message: Message, state: FSMContext) -> None:
    """Enter career dialogue mode. Initialize dialogue tracking."""
    
    # КРИТИЧНО: Очищаем контекст AI перед началом нового кейса
    await clear_case_conversations(CareerDialogConfig.CASE_ID, message.from_user.id)
    
    await state.set_state(CareerChat.waiting_user)
    
    # Инициализируем данные для отслеживания диалога
    await state.update_data(
        turn_count=0,
        dialogue_entries=[],
        total_components_achieved=set(),  # Для накопления достигнутых компонентов карьерного диалога
    )
    
    await message.answer(
        CareerDialogConfig.get_start_message(), 
        parse_mode="Markdown", 
        reply_markup=get_case_controls_reply()
    )


# Запуск по нажатию кнопки меню - показываем описание кейса
@router.callback_query(F.data == f"{CALLBACK_PREFIX_MENU}career_dialog")
@measure(case=CareerDialogConfig.CASE_ID, step="show_description")
async def case_career_dialog_description(callback: CallbackQuery, state: FSMContext):
    if not callback.message:
        await callback.answer()
        return

    # Отключаем предыдущее сообщение с инлайн-кнопками, если оно было и это другой message_id
    prev_id = (await state.get_data()).get(ACTIVE_INLINE_MSG_ID_KEY)
    if prev_id and prev_id != callback.message.message_id:
        await disable_buttons_by_id(callback.bot, callback.message.chat.id, prev_id)
    
    # Показываем описание кейса с кнопками действий
    # Всегда отправляем описание кейса новым сообщением
    msg = await callback.message.answer(
        Texts.CASE_CAREER_DIALOG_DESCRIPTION, 
        parse_mode="Markdown",
        reply_markup=get_case_description_inline("career_dialog")
    )
    # Фиксируем новое активное сообщение
    await state.update_data(**{ACTIVE_INLINE_MSG_ID_KEY: msg.message_id})
    await callback.answer()


# Начало диалога по кнопке "Начать диалог"
@router.callback_query(F.data == "case:career_dialog:start")
@measure(case=CareerDialogConfig.CASE_ID, step="start_dialog")
async def case_career_dialog_start_dialog(callback: CallbackQuery, state: FSMContext):
    if not callback.message:
        await callback.answer()
        return
    
    # Проверяем, что пользователь не находится в активном диалоге
    current_state = await state.get_state()
    if current_state == CareerChat.waiting_user:
        await callback.answer("Диалог уже активен! Завершите текущий диалог или начните заново.")
        return
    
    # Отключаем инлайн-кнопки у предыдущего активного сообщения (например, экрана описания)
    data = await state.get_data()
    prev_id = data.get(ACTIVE_INLINE_MSG_ID_KEY)
    if prev_id:
        await disable_buttons_by_id(callback.bot, callback.message.chat.id, prev_id)

    # КРИТИЧНО: Очищаем контекст AI перед началом нового кейса
    await clear_case_conversations(CareerDialogConfig.CASE_ID, callback.from_user.id)
    
    await state.set_state(CareerChat.waiting_user)
    await state.update_data(turn_count=0, dialogue_entries=[], total_components_achieved=set(), **{ACTIVE_INLINE_MSG_ID_KEY: None})
    
    # Отправляем стартовое сообщение с поддержкой Markdown
    await callback.message.answer(
        CareerDialogConfig.get_start_message(), 
        parse_mode="Markdown", 
        reply_markup=get_case_controls_reply()
    )
    # Счетчик старта кейса
    try:
        await mark_case_started(callback.from_user.id, CareerDialogConfig.CASE_ID)
    except Exception:
        pass
    
    # Отправляем дополнительное сообщение про аудиозапись
    await callback.message.answer(
        CareerDialogConfig.AUDIO_PROMPT_MESSAGE,
        parse_mode="Markdown"
    )
    await callback.answer("Диалог начат")


# Обработчик кнопки "Ознакомиться с теорией" - отправляет PDF сразу
@router.callback_query(F.data == "case:career_dialog:theory")
@measure(case=CareerDialogConfig.CASE_ID, step="show_theory")
async def case_career_dialog_theory(callback: CallbackQuery, state: FSMContext):
    """Отправляет PDF-памятку по кейсу 'Карьерный диалог' и возвращает к описанию кейса."""
    if not callback.message:
        await callback.answer()
        return
    
    # Отключаем предыдущее активное сообщение с инлайн-кнопками
    prev_id = (await state.get_data()).get(ACTIVE_INLINE_MSG_ID_KEY)
    if prev_id and prev_id != callback.message.message_id:
        await disable_buttons_by_id(callback.bot, callback.message.chat.id, prev_id)
    
    try:
        # Путь к PDF-файлу
        pdf_path = "static/pdfs/karierny_dialog.pdf"
        
        # Отправляем документ
        from aiogram.types import FSInputFile
        document = FSInputFile(pdf_path)
        
        await callback.message.answer_document(
            document,
            caption="📚 *Памятка по карьерному диалогу*\n\nИзучи материал и применяй на практике!",
            parse_mode="Markdown"
        )
        
        await callback.answer("📄 PDF отправлен ✅")
        
    except FileNotFoundError:
        logger.error("PDF file not found: static/pdfs/karierny_dialog.pdf")
        await callback.answer("❌ Файл не найден. Обратитесь к администратору.", show_alert=True)
    except Exception as e:
        logger.error(f"Error sending PDF: {type(e).__name__}: {e}")
        await callback.answer("❌ Ошибка при отправке файла", show_alert=True)


@router.message(Command("career_stop"))
@measure(case=CareerDialogConfig.CASE_ID, step="finish")
async def career_stop(message: Message, state: FSMContext) -> None:
    """Exit career dialogue mode and clear conversation."""
    await clear_case_conversations(CareerDialogConfig.CASE_ID, message.from_user.id)

    await state.clear()
    await message.answer(CareerDialogConfig.STOP_MESSAGE, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())


async def _process_user_input(user_text: str, message: Message, state: FSMContext, is_admin: bool) -> None:
    """Общий обработчик шага диалога для текстов из чата и из распознавания."""
    session_id = f"{message.from_user.id}:{CareerDialogConfig.CASE_ID}"
    # Получаем данные состояния
    data = await state.get_data()
    turn_count = data.get("turn_count", 0)
    dialogue_entries = data.get("dialogue_entries", [])
    total_components_achieved = data.get("total_components_achieved", set())
    # Гарантируем, что это множество (а не список из FSM)
    if isinstance(total_components_achieved, list):
        total_components_achieved = set(total_components_achieved)

    # Формируем структурированный промпт
    user_prompt = CareerDialogConfig.get_user_prompt(user_text)

    # Отправляем запрос к AI с системным промптом и индикатором печатания
    async def ai_request():
        return await send_dialogue_message(
            case_id=CareerDialogConfig.CASE_ID,
            user_id=message.from_user.id,
            message=user_prompt,
            system_prompt=CareerDialogConfig.SYSTEM_PROMPT,
        )
    
    response = await with_typing_indicator(
        bot=message.bot,
        chat_id=message.chat.id,
        character_name="Максим",
        character_emoji="👨‍💻",
        async_operation=ai_request
    )

    if not response.success:
        await message.answer(f"{CareerDialogConfig.ERROR_AI_REQUEST}\nОшибка: {response.error}")
        return

    # Проверяем, что пользователь всё ещё в диалоге (не нажал "Главное меню" во время ожидания)
    current_state = await state.get_state()
    if current_state != CareerChat.waiting_user:
        # Пользователь вышел из диалога, не отправляем ответ
        return

    generated = response.content or CareerDialogConfig.FALLBACK_REPLY_TEXT

    # Парсим JSON ответ
    parsed_response = parse_ai_response(generated)
    maxim_reply = parsed_response.get("ReplyText", "")

    # Сохраняем ход в диалоге
    dialogue_entries.append({"role": "Руководитель", "text": user_text})
    dialogue_entries.append({"role": "Максим", "text": maxim_reply})

    # Обновляем флаги компонентов карьерного диалога
    career_keys = ["Aspirations", "Strengths", "Development", "Opportunities", "Plan"]
    for key in career_keys:
        if parsed_response.get(key, False):
            total_components_achieved.add(key)

    turn_count += 1

    # Обновляем состояние
    await state.update_data(
        turn_count=turn_count,
        dialogue_entries=dialogue_entries,
        total_components_achieved=total_components_achieved,
    )

    # Форматируем для показа (анализ только для админов)
    formatted_message = format_career_response(parsed_response, show_analysis=is_admin)

    # Проверяем условия завершения
    all_components_achieved = len(total_components_achieved) >= 5 and turn_count >= 2
    max_turns_reached = turn_count >= CareerDialogConfig.MAX_DIALOGUE_TURNS

    if all_components_achieved or max_turns_reached:
        # Всегда отправляем последний ответ AI перед сообщениями о завершении и анализе
        await message.answer(formatted_message, parse_mode="Markdown")
        # Задержка перед следующим сообщением
        await asyncio.sleep(1)
        
        completion_msg = (
            CareerDialogConfig.COMPLETION_ALL_COMPONENTS
            if all_components_achieved
            else CareerDialogConfig.get_completion_max_turns_message()
        )
        await message.answer(completion_msg, parse_mode="Markdown")
        # Инкременты завершений и возможное авто-приглашение к опросу (одноразово по замку)
        try:
            if all_components_achieved:
                await mark_case_completed(message.from_user.id, CareerDialogConfig.CASE_ID)
                await mark_case_auto_finished(message.from_user.id, CareerDialogConfig.CASE_ID)
            else:
                await mark_case_out_of_moves(message.from_user.id, CareerDialogConfig.CASE_ID)
                await mark_case_auto_finished(message.from_user.id, CareerDialogConfig.CASE_ID)

        except Exception:
            pass
        
        # Показываем индикатор анализа при автоматическом завершении
        async def review_operation():
            return await perform_dialogue_review(dialogue_entries, session_id)
        
        review_result = await with_analysis_indicator(
            bot=message.bot,
            chat_id=message.chat.id,
            async_operation=review_operation
        )
        # Скрываем reply-клавиатуру при завершении
        await message.answer(review_result, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
        
        # Задержка перед следующим сообщением
        await asyncio.sleep(1)
        
        # И показываем инлайн-опции после рецензии
        prev_id = (await state.get_data()).get(ACTIVE_INLINE_MSG_ID_KEY)
        if prev_id:
            await disable_buttons_by_id(message.bot, message.chat.id, prev_id)
        after_msg = await message.answer(CareerDialogConfig.AFTER_REVIEW_MESSAGE, parse_mode="Markdown", reply_markup=get_case_after_review_inline())
        await state.update_data(**{ACTIVE_INLINE_MSG_ID_KEY: after_msg.message_id})
        await state.set_state(CareerChat.review_complete)
        
        # В САМОМ КОНЦЕ отправляем приглашение к опросу
        try:
            if await acquire_rating_invite_lock(message.from_user.id):
                await send_survey_invitation(message.bot, message.chat.id, message.from_user.id)
        except Exception:
            pass
    else:
        if CareerDialogConfig.SHOW_PROGRESS_INFO:
            progress_msg = (
                f"\n\n{CareerDialogConfig.PROGRESS_EMOJI} Ход {turn_count}/{CareerDialogConfig.MAX_DIALOGUE_TURNS} | Компоненты: {len(total_components_achieved)}/5"
            )
            await message.answer(formatted_message + progress_msg, parse_mode="Markdown")
        else:
            await message.answer(formatted_message, parse_mode="Markdown")


@router.message(StateFilter(CareerChat.waiting_user), F.text.len() > 0)
@measure(case=CareerDialogConfig.CASE_ID, step="user_turn")
async def career_turn(message: Message, state: FSMContext, is_admin: bool) -> None:
    try:
        # Валидация входного текста (временное упрощение)
        user_text = await validator.validate_and_process_text(message)
        
        # Обработка reply-кнопок
        if user_text == KB_CASE_RESTART:
            # эмулируем клик по callback-кнопке
            await clear_case_conversations(CareerDialogConfig.CASE_ID, message.from_user.id)
            await state.set_state(CareerChat.waiting_user)
            await state.update_data(turn_count=0, dialogue_entries=[], total_components_achieved=set())
            await message.answer(
                CareerDialogConfig.get_start_message(), 
                parse_mode="Markdown", 
                reply_markup=get_case_controls_reply()
            )
            return
        if user_text == KB_BACK_TO_MENU:
            # Возврат в главное меню
            await clear_case_conversations(CareerDialogConfig.CASE_ID, message.from_user.id)
            await state.clear()
            from app.keyboards.menu import get_main_menu_inline
            await message.answer(
                "🏠 Главное меню",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )
            await message.answer(
                "Выберите кейс для тренировки:",
                reply_markup=get_main_menu_inline()
            )
            return
        if user_text == KB_CASE_REVIEW:
            data = await state.get_data()
            dialogue_entries = data.get("dialogue_entries", [])
            session_id = f"{message.from_user.id}:{CareerDialogConfig.CASE_ID}"
            
            # Инкрементируем completed при ручном завершении
            try:
                await mark_case_completed(message.from_user.id, CareerDialogConfig.CASE_ID)
            except Exception:
                pass
            
            # Показываем индикатор анализа при принудительном запросе
            async def review_operation():
                return await perform_dialogue_review(dialogue_entries, session_id)
            
            review_result = await with_analysis_indicator(
                bot=message.bot,
                chat_id=message.chat.id,
                async_operation=review_operation
            )
            # Скрываем reply-клавиатуру и показываем инлайн-опции
            await message.answer(review_result, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            
            # Задержка перед следующим сообщением
            await asyncio.sleep(1)
            
            prev_id = (await state.get_data()).get(ACTIVE_INLINE_MSG_ID_KEY)
            if prev_id:
                await disable_buttons_by_id(message.bot, message.chat.id, prev_id)
            after_msg = await message.answer(CareerDialogConfig.AFTER_REVIEW_MESSAGE, parse_mode="Markdown", reply_markup=get_case_after_review_inline())
            await state.update_data(**{ACTIVE_INLINE_MSG_ID_KEY: after_msg.message_id})
            await state.set_state(CareerChat.review_complete)
            
            # В САМОМ КОНЦЕ отправляем приглашение к опросу
            try:
                if await acquire_rating_invite_lock(message.from_user.id):
                    await send_survey_invitation(message.bot, message.chat.id, message.from_user.id)
            except Exception:
                pass
            return

        # user_text уже валидирован выше
        await _process_user_input(user_text, message, state, is_admin)
    except Exception as e:
        if is_admin:
            await message.answer(f"{CareerDialogConfig.ERROR_AI_REQUEST}\nАдмин-детали: {type(e).__name__}: {e}")
        else:
            await message.answer(CareerDialogConfig.ERROR_AI_REQUEST)


# Голосовой ввод: транскрибация → в общий процесс
@router.message(StateFilter(CareerChat.waiting_user), F.voice)
@measure(case=CareerDialogConfig.CASE_ID, step="user_turn_voice")
async def career_turn_voice(message: Message, state: FSMContext, is_admin: bool) -> None:
    try:
        # Временное отключение валидации голосового сообщения для повышения робастности
        # (проверка размера/длительности отключена)
        
        logger.info(f"Voice message received: file_id={message.voice.file_id}, duration={message.voice.duration}s, size={message.voice.file_size}B")
        
        # Функция для транскрибации с индикатором прослушивания
        async def transcription_operation():
            try:
                # Скачиваем файл в память
                logger.debug(f"Downloading voice file: {message.voice.file_id}")
                file = await message.bot.get_file(message.voice.file_id)
                buffer = BytesIO()
                await message.bot.download(file, buffer)
                logger.debug(f"File downloaded: {len(buffer.getvalue())} bytes")
                # Транскрибуем
                result = await transcribe_voice_ogg(buffer)
                logger.info(f"Transcription completed: got {len(result)} characters")
                return result
            except Exception as inner_e:
                logger.error(f"Error in transcription_operation: {inner_e}", exc_info=True)
                raise
        
        # Показываем "Максим слушает аудио" во время транскрибации
        text = await with_listening_indicator(
            bot=message.bot,
            chat_id=message.chat.id,
            character_name="Максим",
            character_emoji="🎧",
            async_operation=transcription_operation
        )
        
        logger.info(f"After listening indicator: text={repr(text[:50] if text else '')}")
        
        # Временное отключение валидации транскрибированного текста
        validated_text = (text or "").strip()
        if not validated_text:
            # Если транскрипция пустая — дружелюбный ответ и выход
            logger.warning(f"Empty transcription for user {message.from_user.id}")
            await message.answer("❌ Не удалось распознать голосовое. Попробуйте ещё раз.")
            return
        
        logger.info(f"Processing validated text: {validated_text[:50]}...")
        # Продолжаем как с текстом (здесь уже будет показан "Максим думает...")
        await _process_user_input(validated_text, message, state, is_admin)
    except Exception as e:
        logger.error(f"Voice turn error: {e}", exc_info=True)
        if is_admin:
            await message.answer(f"Ошибка транскрибации: {type(e).__name__}: {e}")
        else:
            await message.answer("❌ Не удалось распознать голосовое. Попробуйте ещё раз.")


@router.message(StateFilter(CareerChat.review_complete))
@measure(case=CareerDialogConfig.CASE_ID, step="after_review")
async def career_after_review(message: Message, state: FSMContext) -> None:
    """Handle messages after dialogue review is complete."""
    # Скрываем reply-клавиатуру (покажем пустую) и выводим инлайн-опции
    await message.answer(CareerDialogConfig.AFTER_REVIEW_MESSAGE, parse_mode="Markdown", reply_markup=get_case_after_review_inline())


# Управляющие кнопки кейса
@router.callback_query(F.data.startswith("case:career_dialog:"))
async def case_controls_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик всех контрольных кнопок для career_dialog"""
    
    # Определяем какую кнопку нажали
    if callback.data.endswith("restart"):
        # === КНОПКА RESTART ===
        await clear_case_conversations(CareerDialogConfig.CASE_ID, callback.from_user.id)
        await state.clear()
        await state.set_state(CareerChat.waiting_user)
        await state.update_data(
            turn_count=0, 
            dialogue_entries=[], 
            total_components_achieved=set(),
            **{ACTIVE_INLINE_MSG_ID_KEY: None}
        )
        
        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            
            await callback.message.answer(
                CareerDialogConfig.get_start_message(), 
                parse_mode="Markdown", 
                reply_markup=get_case_controls_inline_by_case(CareerDialogConfig.CASE_ID)
            )
        await callback.answer("Диалог принудительно перезапущен")
    
    elif callback.data.endswith("review"):
        # === КНОПКА REVIEW ===
        current_state = await state.get_state()
        if current_state != CareerChat.waiting_user:
            await callback.answer("Анализ доступен только во время активного диалога.")
            return
        
        # Принудительный запуск рецензента по текущему диалогу
        data = await state.get_data()
        dialogue_entries = data.get("dialogue_entries", [])
        session_id = f"{callback.from_user.id}:{CareerDialogConfig.CASE_ID}"
        
        # Инкрементируем completed при ручном завершении и отправляем приглашение к опросу
        try:
            await mark_case_completed(callback.from_user.id, CareerDialogConfig.CASE_ID)
            if await acquire_rating_invite_lock(callback.from_user.id):
                await send_survey_invitation(callback.bot, callback.message.chat.id, callback.from_user.id)
        except Exception:
            pass
        
        # Показываем индикатор анализа при принудительном запросе через callback
        async def review_operation():
            return await perform_dialogue_review(dialogue_entries, session_id)
        
        review_result = await with_analysis_indicator(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            async_operation=review_operation
        )
        if callback.message:
            # Отключаем кнопки в предыдущем инлайн-сообщении
            data = await state.get_data()
            prev_id = data.get(ACTIVE_INLINE_MSG_ID_KEY)
            if prev_id:
                await disable_buttons_by_id(callback.bot, callback.message.chat.id, prev_id)
            # Скрываем reply и показываем инлайн-опции
            await callback.message.answer(review_result, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            
            # Задержка перед следующим сообщением
            await asyncio.sleep(1)
            
            # Показываем кнопки после рецензии
            prev_id = (await state.get_data()).get(ACTIVE_INLINE_MSG_ID_KEY)
            if prev_id:
                await disable_buttons_by_id(callback.bot, callback.message.chat.id, prev_id)
            after_msg = await callback.message.answer(
                CareerDialogConfig.AFTER_REVIEW_MESSAGE, 
                parse_mode="Markdown", 
                reply_markup=get_case_after_review_inline_by_case(CareerDialogConfig.CASE_ID)
            )
            await state.update_data(**{ACTIVE_INLINE_MSG_ID_KEY: after_msg.message_id})
            await state.set_state(CareerChat.review_complete)