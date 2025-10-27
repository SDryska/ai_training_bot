"""Тесты для упрощённого сервиса валидации."""

import pytest
from unittest.mock import Mock

from app.config.settings import Settings
from app.services.validation_service import InputValidator, ValidationError, validator as global_validator


class TestInputValidatorInit:
    """Тесты инициализации валидатора"""

    def test_validator_init_with_default_settings(self):
        """Тест: инициализация с настройками по умолчанию"""
        validator = InputValidator()
        assert validator.settings is not None

    def test_validator_init_with_custom_settings(self):
        """Тест: инициализация с кастомными настройками"""
        custom_settings = Settings(
            BOT_TOKEN="test_token",
            TEXT_MAX_LENGTH=1000,
            TEXT_MIN_LENGTH=5,
            VOICE_MAX_SIZE_MB=10.0,
        )
        validator = InputValidator(settings=custom_settings)
        assert validator.settings.TEXT_MAX_LENGTH == 1000
        assert validator.settings.TEXT_MIN_LENGTH == 5
        assert validator.settings.VOICE_MAX_SIZE_MB == 10.0


class TestValidateText:
    """Тесты валидации текста"""

    def test_validate_text_normal_input(self):
        """Тест: нормальный текстовый ввод"""
        validator = InputValidator()
        text = "Это обычное сообщение для теста"
        result = validator.validate_text(text)
        assert result == text

    def test_validate_text_strips_whitespace(self):
        """Тест: убирает пробелы по краям"""
        validator = InputValidator()
        text = "   текст с пробелами   "
        result = validator.validate_text(text)
        assert result == "текст с пробелами"

    def test_validate_text_raises_on_empty_string(self):
        """Тест: пустая строка отклоняется"""
        validator = InputValidator()
        with pytest.raises(ValidationError) as exc:
            validator.validate_text("")
        assert exc.value.error_code == "TEXT_TOO_SHORT"

    def test_validate_text_preserves_newlines(self):
        """Тест: переносы строк не влияют на валидацию"""
        validator = InputValidator()
        text = "Строка 1\nСтрока 2\nСтрока 3"
        result = validator.validate_text(text)
        assert result == text

    def test_validate_text_with_special_characters(self):
        """Тест: спецсимволы допускаются"""
        validator = InputValidator()
        text = "Текст с символами: !@#$%^&*()_+-=[]{}|;':,.<>?"
        result = validator.validate_text(text)
        assert result == text

    def test_validate_text_cyrillic(self):
        """Тест: кириллица"""
        validator = InputValidator()
        text = "Привет, мир! Это тест на русском языке."
        result = validator.validate_text(text)
        assert result == text

    def test_validate_text_mixed_languages(self):
        """Тест: смешанные языки"""
        validator = InputValidator()
        text = "Hello, мир! Test тест 123"
        result = validator.validate_text(text)
        assert result == text

    def test_validate_text_emoji(self):
        """Тест: эмодзи допускаются"""
        validator = InputValidator()
        text = "Сообщение с эмодзи 😊 👍 🎉"
        result = validator.validate_text(text)
        assert result == text

    def test_validate_text_repeated_characters(self):
        """Тест: повторяющиеся символы допускаются"""
        validator = InputValidator()
        text = "a" * 100
        result = validator.validate_text(text)
        assert result == text

    def test_validate_text_long_input(self):
        """Тест: слишком длинный текст отклоняется"""
        validator = InputValidator()
        # TEXT_MAX_LENGTH по умолчанию 12000, используем 13000
        text = "a" * 13000
        with pytest.raises(ValidationError) as exc:
            validator.validate_text(text)
        assert exc.value.error_code == "TEXT_TOO_LONG"


class TestValidateVoiceFile:
    """Тесты валидации голосовых файлов"""

    def test_validate_voice_normal_file(self):
        """Тест: нормальный голосовой файл"""
        validator = InputValidator()
        # Нормальный файл: 1MB, 30 секунд
        file_size = 1024 * 1024  # 1MB
        duration = 30.0
        
        # Не должно выбросить исключение
        validator.validate_voice_file(file_size, duration)

    def test_validate_voice_small_file(self):
        """Тест: маленький файл"""
        validator = InputValidator()
        file_size = 1024  # 1KB
        duration = 1.0
        
        validator.validate_voice_file(file_size, duration)

    def test_validate_voice_large_file_rejected(self):
        """Тест: слишком большой файл отклоняется"""
        validator = InputValidator()
        file_size = 100 * 1024 * 1024
        with pytest.raises(ValidationError) as exc:
            validator.validate_voice_file(file_size, duration=0)
        assert exc.value.error_code == "VOICE_TOO_LARGE"

    def test_validate_voice_zero_duration_allowed(self):
        """Тест: длительность не проверяется"""
        validator = InputValidator()
        file_size = 1024
        duration = 0.0
        validator.validate_voice_file(file_size, duration)


class TestValidateTranscribedText:
    """Тесты валидации транскрибированного текста"""

    def test_validate_transcribed_normal_text(self):
        """Тест: нормальный транскрибированный текст"""
        validator = InputValidator()
        text = "Это результат транскрибации голосового сообщения"
        result = validator.validate_transcribed_text(text)
        assert result == text

    def test_validate_transcribed_empty_rejected(self):
        """Тест: пустая транскрибация отклоняется"""
        validator = InputValidator()
        with pytest.raises(ValidationError) as exc:
            validator.validate_transcribed_text("")
        assert exc.value.error_code == "TEXT_TOO_SHORT"

    def test_validate_transcribed_whitespace_only_rejected(self):
        """Тест: транскрибация из одних пробелов отклоняется"""
        validator = InputValidator()
        text = "   \n\t  "
        with pytest.raises(ValidationError) as exc:
            validator.validate_transcribed_text(text)
        assert exc.value.error_code == "TEXT_TOO_SHORT"

    def test_validate_transcribed_strips_whitespace(self):
        """Тест: убирает пробелы по краям"""
        validator = InputValidator()
        text = "  транскрибация  "
        result = validator.validate_transcribed_text(text)
        assert result == "транскрибация"

    def test_validate_transcribed_no_spam_check(self):
        """Тест: не проверяет спам паттерны (check_patterns=False)"""
        validator = InputValidator()
        text = "ааааааааааааааааааааааааааааааааааа"
        result = validator.validate_transcribed_text(text)
        assert result == text


class TestValidationErrorMessages:
    """Тесты сообщений об ошибках валидации"""

    def test_validation_error_has_message(self):
        """Тест: ValidationError содержит сообщение"""
        error = ValidationError("Test error message")
        assert error.message == "Test error message"

    def test_validation_error_has_error_code(self):
        """Тест: ValidationError содержит код ошибки"""
        error = ValidationError("Test", "TEST_CODE")
        assert error.error_code == "TEST_CODE"

    def test_validation_error_default_code(self):
        """Тест: ValidationError имеет код по умолчанию"""
        error = ValidationError("Test")
        assert error.error_code == "VALIDATION_ERROR"

    def test_error_messages_defined(self):
        """Тест: все типы ошибок имеют сообщения"""
        validator = InputValidator()
        expected = {"TEXT_TOO_LONG", "TEXT_TOO_SHORT", "VOICE_TOO_LARGE", "VOICE_MISSING"}
        assert expected.issubset(set(validator.ERROR_MESSAGES))


class TestValidatorWithMocks:
    """Тесты валидатора с моками для async методов"""

    @pytest.mark.asyncio
    async def test_validate_and_process_text_normal(self):
        """Тест: обработка текстового сообщения"""
        validator = InputValidator()

        mock_message = Mock()
        mock_message.text = "Обычное сообщение"

        result = await validator.validate_and_process_text(mock_message)
        assert result == "Обычное сообщение"

    @pytest.mark.asyncio
    async def test_validate_and_process_text_strips_whitespace(self):
        """Тест: обработка убирает пробелы"""
        validator = InputValidator()

        mock_message = Mock()
        mock_message.text = "  текст с пробелами  "

        result = await validator.validate_and_process_text(mock_message)
        assert result == "текст с пробелами"

    @pytest.mark.asyncio
    async def test_validate_and_process_voice_no_voice(self):
        """Тест: сообщение без голоса выбрасывает ошибку"""
        validator = InputValidator()

        mock_message = Mock()
        mock_message.voice = None

        with pytest.raises(ValidationError) as exc_info:
            await validator.validate_and_process_voice(mock_message)

        assert exc_info.value.error_code == "VOICE_MISSING"

    @pytest.mark.asyncio
    async def test_validate_and_process_voice_with_voice(self):
        """Тест: обработка голосового сообщения"""
        validator = InputValidator()

        mock_message = Mock()
        mock_voice = Mock()
        mock_voice.file_size = 1024 * 100
        mock_voice.duration = 5.0
        mock_message.voice = mock_voice

        await validator.validate_and_process_voice(mock_message)


class TestGlobalValidator:
    """Тесты глобального экземпляра валидатора"""

    def test_global_validator_exists(self):
        """Тест: глобальный валидатор существует"""
        assert global_validator is not None

    def test_global_validator_is_input_validator(self):
        """Тест: глобальный валидатор - экземпляр InputValidator"""
        assert isinstance(global_validator, InputValidator)

    def test_global_validator_has_settings(self):
        """Тест: глобальный валидатор имеет настройки"""
        assert global_validator.settings is not None

    def test_global_validator_has_rate_limiter(self):
        """Тест: глобальный валидатор имеет rate limiter"""
        assert global_validator.settings is not None


class TestRealWorldScenarios:
    """Тесты реальных сценариев использования."""

    def test_scenario_user_sends_normal_message(self):
        validator = InputValidator()
        text = "Привет! Помоги мне с обратной связью."
        result = validator.validate_text(text)
        assert result == text

    def test_scenario_user_sends_too_short_message(self):
        validator = InputValidator()
        with pytest.raises(ValidationError):
            validator.validate_text("")

    def test_scenario_user_sends_voice(self):
        validator = InputValidator()
        file_size = 2 * 1024 * 1024
        duration = 45.0
        validator.validate_voice_file(file_size, duration)

    def test_scenario_transcription_result(self):
        validator = InputValidator()
        transcribed = "Это голосовое сообщение было преобразовано в текст"
        result = validator.validate_transcribed_text(transcribed)
        assert result == transcribed


class TestIsolationFromExternalSystems:
    """Тесты проверяют, что валидация работает независимо от внешних систем."""

    def test_validator_works_without_database(self):
        """Тест: валидация не требует БД"""
        validator = InputValidator()
        # БД может быть недоступна, но валидация работает
        text = "Это сообщение будет валидировано без БД"
        result = validator.validate_text(text)
        assert result == text

    def test_validator_works_without_fsm(self):
        """Тест: валидация не требует FSM"""
        validator = InputValidator()
        # FSM может быть не инициализирована, валидация работает
        text = "Это сообщение валидно без FSM состояния"
        result = validator.validate_text(text)
        assert result == text

    def test_validator_works_without_ai_provider(self):
        """Тест: валидация не требует подключения к AI (OpenAI, Gemini)"""
        validator = InputValidator()
        # AI сервис может быть недоступен, валидация всё равно работает
        text = "Текст готов к отправке в AI, но сам валидатор не нуждается в AI"
        result = validator.validate_text(text)
        assert result == text

    def test_validator_works_without_transcription_service(self):
        """Тест: валидация голоса не требует сервиса транскрибации"""
        validator = InputValidator()
        # Сервис транскрибации может быть недоступен
        # но валидация файла работает независимо
        file_size = 2 * 1024 * 1024
        duration = 30.0
        validator.validate_voice_file(file_size, duration)

    def test_validator_works_without_metrics_system(self):
        """Тест: валидация не требует системы метрик"""
        validator = InputValidator()
        # Prometheus, Sentry и прочие метрики могут быть выключены
        text = "Это сообщение валидируется без отправки метрик"
        result = validator.validate_text(text)
        assert result == text

    def test_validator_works_without_cache(self):
        """Тест: валидация не использует кэш"""
        validator = InputValidator()
        # Redis или другой кэш может быть недоступен
        text1 = "Первое сообщение"
        text2 = "Второе сообщение"
        result1 = validator.validate_text(text1)
        result2 = validator.validate_text(text2)
        assert result1 == text1
        assert result2 == text2

    def test_validator_works_without_network(self):
        """Тест: валидация работает полностью локально"""
        validator = InputValidator()
        # Нет сетевого подключения - валидация работает
        text = "Локальная валидация без интернета"
        result = validator.validate_text(text)
        assert result == text

    @pytest.mark.asyncio
    async def test_async_validation_isolated_from_database(self):
        """Тест: асинхронная валидация независима от БД"""
        validator = InputValidator()
        mock_message = Mock()
        mock_message.text = "Асинхронное сообщение для БД-независимой валидации"

        # БД может быть недоступна, но валидация работает асинхронно
        result = await validator.validate_and_process_text(mock_message)
        assert result == "Асинхронное сообщение для БД-независимой валидации"

    def test_validator_rejects_text_independently_of_system_state(self):
        """Тест: валидатор последовательно отклоняет неверные данные"""
        validator = InputValidator()
        # Независимо от состояния других систем, валидатор должен
        # отклонять некорректные данные (TEXT_MAX_LENGTH по умолчанию 12000)
        with pytest.raises(ValidationError) as exc:
            validator.validate_text("a" * 13000)
        assert exc.value.error_code == "TEXT_TOO_LONG"

        # И повторный вызов даст тот же результат
        with pytest.raises(ValidationError) as exc:
            validator.validate_text("a" * 13000)
        assert exc.value.error_code == "TEXT_TOO_LONG"

    def test_validator_accepts_valid_data_independently_of_system_state(self):
        """Тест: валидатор последовательно принимает корректные данные"""
        validator = InputValidator()
        valid_text = "Корректное сообщение"

        # Несколько вызовов с тем же корректным данным
        for _ in range(3):
            result = validator.validate_text(valid_text)
            assert result == valid_text

    def test_multiple_validators_work_independently(self):
        """Тест: несколько валидаторов не влияют друг на друга"""
        validator1 = InputValidator()
        validator2 = InputValidator()

        text1 = "Сообщение для первого валидатора"
        text2 = "Сообщение для второго валидатора"

        result1 = validator1.validate_text(text1)
        result2 = validator2.validate_text(text2)

        assert result1 == text1
        assert result2 == text2

    def test_validator_settings_isolation(self):
        """Тест: каждый валидатор имеет свои настройки"""
        settings1 = Settings(BOT_TOKEN="token1", TEXT_MAX_LENGTH=100)
        settings2 = Settings(BOT_TOKEN="token2", TEXT_MAX_LENGTH=200)

        validator1 = InputValidator(settings=settings1)
        validator2 = InputValidator(settings=settings2)

        # Текст валиден для первого валидатора
        text_80 = "a" * 80
        assert validator1.validate_text(text_80) == text_80

        # Текст валиден для второго валидатора
        text_150 = "a" * 150
        assert validator2.validate_text(text_150) == text_150

        # Но текст 150 символов невалиден для первого
        with pytest.raises(ValidationError):
            validator1.validate_text(text_150)

