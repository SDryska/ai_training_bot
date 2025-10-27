"""
Сервис для транскрибации голосовых сообщений через OpenAI API.
"""

import asyncio
import logging
from io import BytesIO

from openai import OpenAI
from app.config.settings import Settings

logger = logging.getLogger(__name__)


async def transcribe_voice_ogg(bytes_io: BytesIO) -> str:
    """Транскрибирует голосовое через OpenAI gpt-4o-transcribe с ретраями и таймаутом."""
    settings = Settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def _call_once(model_name: str) -> str:
        try:
            # openai-python метод синхронный — оборачиваем в executor
            def _sync_call():
                # Важно: у BytesIO должен быть name с расширением
                bytes_io.seek(0)
                file_tuple = ("audio.ogg", bytes_io, "audio/ogg")
                result = client.audio.transcriptions.create(
                    model=model_name,
                    file=file_tuple,
                )
                text = getattr(result, "text", None)
                if not text and isinstance(result, dict):
                    text = result.get("text")
                return text or ""

            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _sync_call)
        except Exception as e:
            logger.warning("Transcribe call failed: %s (%s)", e, type(e).__name__, exc_info=True)
            return ""

    max_retries = max(1, settings.TRANSCRIBE_MAX_RETRIES)
    backoff = max(0.0, settings.TRANSCRIBE_RETRY_BACKOFF_SEC)
    timeout_sec = max(1.0, settings.TRANSCRIBE_TIMEOUT_SEC)

    last_text = ""
    for attempt in range(1, max_retries + 1):
        try:
            # Первая попытка — основная модель
            last_text = await asyncio.wait_for(_call_once("gpt-4o-transcribe"), timeout=timeout_sec)
            if last_text:
                return last_text
            else:
                logger.info("Transcribe empty result on attempt %d/%d", attempt, max_retries)
                # Fallback-модель при пустом ответе
                last_text = await asyncio.wait_for(_call_once("whisper-1"), timeout=timeout_sec)
                if last_text:
                    logger.info("Transcribe succeeded with fallback model 'whisper-1' on attempt %d/%d", attempt, max_retries)
                    return last_text
        except asyncio.TimeoutError:
            logger.warning("Transcribe timeout on attempt %d/%d (timeout=%.1fs)", attempt, max_retries, timeout_sec)
        except Exception as e:
            logger.warning("Transcribe exception on attempt %d/%d: %s", attempt, max_retries, e, exc_info=True)

        if attempt < max_retries:
            await asyncio.sleep(backoff * attempt)

    logger.error("Transcribe failed after %d attempts", max_retries)
    return last_text
