"""
Сервис для инициализации и управления AI провайдерами.
"""

import logging
from typing import List, Set

from app.config.provider_config import (
    CaseProviderConfig,
    ProviderSettings,
    get_case_provider_config,
)
from app.config.settings import Settings
from app.providers.base import AIResponse, ProviderType
from app.providers.gateway import gateway
from app.providers.gemini import GeminiProvider
from app.providers.openai import OpenAIProvider
from app.storage import PostgresStorage, InMemoryStorage

logger = logging.getLogger(__name__)


def initialize_ai_providers() -> None:
    """Инициализирует доступные AI провайдеры"""
    settings = Settings()
    
    # Выбираем хранилище: Postgres если DATABASE_URL задан, иначе память
    try:
        if settings.DATABASE_URL:
            storage = PostgresStorage(settings.DATABASE_URL)
            logger.info("Используется PostgreSQL хранилище для диалогов")
        else:
            storage = InMemoryStorage()
            logger.warning("DATABASE_URL не задан, используется in-memory хранилище (диалоги не сохраняются при перезапуске)")
    except Exception as e:
        logger.error(f"Ошибка создания хранилища диалогов: {e}, используем InMemoryStorage", exc_info=True)
        storage = InMemoryStorage()
    
    # Инициализируем OpenAI провайдер
    if settings.OPENAI_API_KEY:
        try:
            openai_provider = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model="gpt-3.5-turbo",
                storage=storage
            )
            gateway.register_provider(
                ProviderType.OPENAI, 
                openai_provider, 
                is_default=True
            )
            logger.info("OpenAI провайдер инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenAI провайдера: {e}", exc_info=True)
    else:
        logger.warning("OPENAI_API_KEY не найден - OpenAI провайдер недоступен")
    
    # Инициализируем Gemini провайдер
    if settings.GEMINI_API_KEY:
        try:
            gemini_provider = GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model="gemini-2.0-flash",
                storage=storage
            )
            gateway.register_provider(
                ProviderType.GEMINI, 
                gemini_provider,
                is_default=False
            )
            logger.info("Gemini провайдер инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации Gemini провайдера: {e}", exc_info=True)
    else:
        logger.info("GEMINI_API_KEY не найден - Gemini провайдер недоступен")
    
    # Здесь в будущем добавим другие провайдеры:
    # if settings.CLAUDE_API_KEY:
    #     claude_provider = ClaudeProvider(settings.CLAUDE_API_KEY)
    #     gateway.register_provider(ProviderType.CLAUDE, claude_provider)
    
    available_providers = [p.value for p in gateway.get_available_providers()]
    logger.info(f"Инициализированы AI провайдеры: {available_providers}")


def get_ai_gateway():
    """Возвращает глобальный экземпляр шлюза"""
    return gateway


async def send_case_message(
    *,
    case_id: str,
    channel: str,
    user_id: int,
    message: str,
    system_prompt: str | None = None,
    audio_bytes=None,
) -> AIResponse:
    """Отправляет сообщение, используя конфигурацию провайдеров кейса."""
    provider_chain = _get_provider_chain(case_id, channel)
    errors: List[str] = []

    for settings in provider_chain:
        logger.debug(
            "Case provider call: case=%s, channel=%s, provider=%s, model=%s",
            case_id,
            channel,
            settings.provider.value,
            settings.model,
        )
        response = await gateway.send_message(
            user_id=user_id,
            message=message,
            system_prompt=system_prompt,
            provider_type=settings.provider,
            model_override=settings.model,
            audio_bytes=audio_bytes,
        )
        if response.success:
            logger.info(
                "AI response: case=%s channel=%s provider=%s model=%s",
                case_id,
                channel,
                settings.provider.value,
                settings.model,
            )
            return response

        logger.warning(
            "AI fallback: case=%s channel=%s provider=%s model=%s error=%s",
            case_id,
            channel,
            settings.provider.value,
            settings.model,
            response.error or "unknown error",
        )
        errors.append(
            f"{settings.provider.value}:{settings.model} => {response.error or 'unknown error'}"
        )
        await gateway.clear_conversation(user_id, provider_type=settings.provider)

    logger.error(
        "AI failed: case=%s channel=%s errors=%s",
        case_id,
        channel,
        "; ".join(errors) if errors else "no providers",
    )
    return AIResponse(
        content="",
        success=False,
        error="; ".join(errors) if errors else "Все провайдеры недоступны",
    )


async def clear_case_conversations(case_id: str, user_id: int) -> None:
    """Очищает историю разговоров для всех провайдеров, связанных с кейсом."""
    unique_providers: Set[ProviderType] = set()
    case_config = get_case_provider_config(case_id)

    def collect(settings: ProviderSettings | None) -> None:
        if settings:
            unique_providers.add(settings.provider)

    collect(case_config.dialogue.primary)
    collect(case_config.dialogue.fallback)
    collect(case_config.reviewer.primary)
    collect(case_config.reviewer.fallback)

    for provider_type in unique_providers:
        await gateway.clear_conversation(user_id, provider_type=provider_type)


async def clear_all_conversations(user_id: int) -> None:
    """Очищает историю разговоров для всех доступных провайдеров (при /start, возврате в меню)."""
    available_providers = gateway.get_available_providers()
    for provider_type in available_providers:
        await gateway.clear_conversation(user_id, provider_type=provider_type)


async def send_dialogue_message(
    *,
    case_id: str,
    user_id: int,
    message: str,
    system_prompt: str | None = None,
) -> AIResponse:
    """Отправляет сообщение персонажу кейса."""
    return await send_case_message(
        case_id=case_id,
        channel="dialogue",
        user_id=user_id,
        message=message,
        system_prompt=system_prompt,
    )


async def send_reviewer_message(
    *,
    case_id: str,
    user_id: int,
    message: str,
    system_prompt: str | None = None,
) -> AIResponse:
    """Отправляет сообщение рецензенту кейса."""
    return await send_case_message(
        case_id=case_id,
        channel="reviewer",
        user_id=user_id,
        message=message,
        system_prompt=system_prompt,
    )


def _get_provider_chain(case_id: str, channel: str) -> List[ProviderSettings]:
    case_config: CaseProviderConfig = get_case_provider_config(case_id)
    try:
        provider_cfg = getattr(case_config, channel)
    except AttributeError as exc:
        raise ValueError(
            f"Для кейса '{case_id}' не настроен канал провайдера '{channel}'"
        ) from exc
    return provider_cfg.chain()
