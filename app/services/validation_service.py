"""Упрощённый сервис валидации пользовательского ввода."""

from typing import Optional

from aiogram.types import Message

from app.config.settings import Settings


class ValidationError(Exception):
    """Исключение валидации с пользовательским сообщением."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class InputValidator:
    """Проверяет только те ограничения, которые критичны для диалога."""

    ERROR_MESSAGES = {
        "TEXT_TOO_LONG": "📝 Сообщение слишком длинное (макс. {limit} символов). Попробуйте сократить.",
        "TEXT_TOO_SHORT": "📝 Сообщение слишком короткое. Напишите что-нибудь содержательное.",
        "VOICE_TOO_LARGE": "🎤 Аудиофайл слишком большой (макс. {limit}МБ). Запишите покороче.",
        "VOICE_MISSING": "🎤 Не удалось получить голосовое сообщение.",
    }

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()

    def _format_text_too_long(self) -> str:
        return self.ERROR_MESSAGES["TEXT_TOO_LONG"].format(limit=self.settings.TEXT_MAX_LENGTH)

    def _format_voice_too_large(self) -> str:
        return self.ERROR_MESSAGES["VOICE_TOO_LARGE"].format(limit=self.settings.VOICE_MAX_SIZE_MB)

    def validate_text(self, text: str) -> str:
        """Возвращает очищенный текст, проверяя только длину."""

        cleaned_text = (text or "").strip()
        length = len(cleaned_text)

        if length < self.settings.TEXT_MIN_LENGTH:
            raise ValidationError(self.ERROR_MESSAGES["TEXT_TOO_SHORT"], "TEXT_TOO_SHORT")

        if length > self.settings.TEXT_MAX_LENGTH:
            raise ValidationError(self._format_text_too_long(), "TEXT_TOO_LONG")

        return cleaned_text

    def validate_voice_file(self, file_size: int, duration: float | None = None) -> None:
        """Проверяет только размер аудио-файла."""

        size_mb = file_size / (1024 * 1024)
        if size_mb > self.settings.VOICE_MAX_SIZE_MB:
            raise ValidationError(self._format_voice_too_large(), "VOICE_TOO_LARGE")

    def validate_transcribed_text(self, text: str) -> str:
        """Используется тем же образом, что и validate_text."""

        return self.validate_text(text)

    async def validate_and_process_text(self, message: Message) -> str:
        """Готовит текст к передаче в диалоговую модель."""

        return self.validate_text(message.text or "")

    async def validate_and_process_voice(self, message: Message) -> None:
        """Проверяет, что голосовой ввод пригоден для транскрибации."""

        if not message.voice:
            raise ValidationError(self.ERROR_MESSAGES["VOICE_MISSING"], "VOICE_MISSING")

        self.validate_voice_file(message.voice.file_size, message.voice.duration)


validator = InputValidator()
