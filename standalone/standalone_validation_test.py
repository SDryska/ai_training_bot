#!/usr/bin/env python3
"""
Автономный тестовый скрипт для проверки логики валидации.
НЕ требует установки зависимостей проекта.
Безопасен - не использует API ключи и не делает внешние запросы.
"""

import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional


class ValidationError(Exception):
    """Исключение валидации с пользовательским сообщением"""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class MockSettings:
    """Мок настроек для тестирования"""
    TEXT_MAX_LENGTH = 4000
    TEXT_MAX_LINES = 50
    TEXT_MIN_LENGTH = 1
    VOICE_MAX_SIZE_MB = 25.0
    VOICE_MAX_DURATION_SEC = 300
    VOICE_MIN_DURATION_SEC = 0.5
    MAX_REQUESTS_PER_MINUTE = 20
    MAX_REQUESTS_PER_HOUR = 100


class RateLimiter:
    """Простой rate limiter для ограничения частоты запросов"""
    
    def __init__(self):
        self.requests = defaultdict(list)  # user_id -> [timestamps]
    
    def check_rate_limit(self, user_id: int, max_per_minute: int, max_per_hour: int) -> Optional[int]:
        """
        Проверяет лимиты запросов. Возвращает None если OK, иначе секунды до разблокировки.
        """
        now = datetime.now()
        user_requests = self.requests[user_id]
        
        # Очищаем старые запросы (старше часа)
        hour_ago = now - timedelta(hours=1)
        user_requests[:] = [req_time for req_time in user_requests if req_time > hour_ago]
        
        # Проверяем лимит за час
        if len(user_requests) >= max_per_hour:
            return 3600  # Ждать час
        
        # Проверяем лимит за минуту
        minute_ago = now - timedelta(minutes=1)
        recent_requests = [req_time for req_time in user_requests if req_time > minute_ago]
        
        if len(recent_requests) >= max_per_minute:
            return 60  # Ждать минуту
        
        # Добавляем текущий запрос
        user_requests.append(now)
        return None


class StandaloneValidator:
    """Автономный валидатор для тестирования"""
    
    # Паттерны для обнаружения спама/некорректного контента
    FORBIDDEN_PATTERNS = [
        r'(.)\1{50,}',                    # 50+ повторяющихся символов подряд
        r'[^\w\s\.\,\!\?\-\:\;\(\)]{20,}', # 20+ специальных символов подряд
        r'^[\s\n\r\t]*$',                # только пробельные символы
    ]
    
    # Дружелюбные сообщения об ошибках
    ERROR_MESSAGES = {
        "TEXT_TOO_LONG": "📝 Сообщение слишком длинное (макс. {limit} символов). Попробуйте сократить.",
        "TEXT_TOO_SHORT": "📝 Сообщение слишком короткое. Напишите что-нибудь содержательное.",
        "TEXT_TOO_MANY_LINES": "📝 Слишком много строк (макс. {limit}). Структурируйте сообщение компактнее.",
        "TEXT_EMPTY": "📝 Пустое сообщение. Напишите что-нибудь.",
        "VOICE_TOO_LARGE": "🎤 Аудиофайл слишком большой (макс. {limit}МБ). Запишите покороче.",
        "VOICE_TOO_LONG": "🎤 Аудио слишком длинное (макс. {limit} сек). Запишите покороче.",
        "VOICE_TOO_SHORT": "🎤 Аудио слишком короткое. Говорите чуть дольше.",
        "CONTENT_SPAM": "🚫 Обнаружен спам или некорректный контент. Напишите осмысленное сообщение.",
        "RATE_LIMIT": "⏰ Слишком много запросов. Подождите {seconds} секунд.",
        "TRANSCRIPTION_EMPTY": "🎤 Не удалось распознать речь. Попробуйте записать заново или напишите текстом.",
    }
    
    def __init__(self):
        self.settings = MockSettings()
        self.rate_limiter = RateLimiter()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Компилируем регулярные выражения для производительности"""
        self.compiled_patterns = [re.compile(pattern) for pattern in self.FORBIDDEN_PATTERNS]
    
    def _check_rate_limit(self, user_id: int) -> None:
        """Проверяет rate limit и выбрасывает исключение при превышении"""
        wait_seconds = self.rate_limiter.check_rate_limit(
            user_id, 
            self.settings.MAX_REQUESTS_PER_MINUTE,
            self.settings.MAX_REQUESTS_PER_HOUR
        )
        
        if wait_seconds:
            raise ValidationError(
                self.ERROR_MESSAGES["RATE_LIMIT"].format(seconds=wait_seconds),
                "RATE_LIMIT"
            )
    
    def _check_forbidden_patterns(self, text: str) -> None:
        """Проверяет текст на спам-паттерны"""
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                raise ValidationError(
                    self.ERROR_MESSAGES["CONTENT_SPAM"],
                    "CONTENT_SPAM"
                )
    
    def validate_text(self, text: str, check_patterns: bool = True) -> str:
        """Валидация текстового ввода. Возвращает очищенный текст."""
        if not text:
            raise ValidationError(
                self.ERROR_MESSAGES["TEXT_EMPTY"],
                "TEXT_EMPTY"
            )
        
        # Убираем лишние пробелы по краям
        cleaned_text = text.strip()
        
        if not cleaned_text:
            raise ValidationError(
                self.ERROR_MESSAGES["TEXT_EMPTY"],
                "TEXT_EMPTY"
            )
        
        # Проверяем длину
        if len(cleaned_text) < self.settings.TEXT_MIN_LENGTH:
            raise ValidationError(
                self.ERROR_MESSAGES["TEXT_TOO_SHORT"],
                "TEXT_TOO_SHORT"
            )
        
        if len(cleaned_text) > self.settings.TEXT_MAX_LENGTH:
            raise ValidationError(
                self.ERROR_MESSAGES["TEXT_TOO_LONG"].format(limit=self.settings.TEXT_MAX_LENGTH),
                "TEXT_TOO_LONG"
            )
        
        # Проверяем количество строк
        line_count = len(cleaned_text.split('\n'))
        if line_count > self.settings.TEXT_MAX_LINES:
            raise ValidationError(
                self.ERROR_MESSAGES["TEXT_TOO_MANY_LINES"].format(limit=self.settings.TEXT_MAX_LINES),
                "TEXT_TOO_MANY_LINES"
            )
        
        # Проверяем на спам-паттерны
        if check_patterns:
            self._check_forbidden_patterns(cleaned_text)
        
        return cleaned_text
    
    def validate_voice_file(self, file_size: int, duration: float) -> None:
        """Валидация голосового файла."""
        # Проверяем размер файла
        size_mb = file_size / (1024 * 1024)
        if size_mb > self.settings.VOICE_MAX_SIZE_MB:
            raise ValidationError(
                self.ERROR_MESSAGES["VOICE_TOO_LARGE"].format(limit=self.settings.VOICE_MAX_SIZE_MB),
                "VOICE_TOO_LARGE"
            )
        
        # Проверяем длительность
        if duration > self.settings.VOICE_MAX_DURATION_SEC:
            raise ValidationError(
                self.ERROR_MESSAGES["VOICE_TOO_LONG"].format(limit=self.settings.VOICE_MAX_DURATION_SEC),
                "VOICE_TOO_LONG"
            )
        
        if duration < self.settings.VOICE_MIN_DURATION_SEC:
            raise ValidationError(
                self.ERROR_MESSAGES["VOICE_TOO_SHORT"],
                "VOICE_TOO_SHORT"
            )
    
    def validate_transcribed_text(self, text: str) -> str:
        """Валидация транскрибированного текста."""
        if not text or not text.strip():
            raise ValidationError(
                self.ERROR_MESSAGES["TRANSCRIPTION_EMPTY"],
                "TRANSCRIPTION_EMPTY"
            )
        
        # Применяем стандартную валидацию текста, но без проверки на спам
        return self.validate_text(text, check_patterns=False)


class ValidationTester:
    """Класс для тестирования валидации"""
    
    def __init__(self):
        self.validator = StandaloneValidator()
        self.test_results = []
    
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Логирует результат теста"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append((test_name, passed))
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
    
    def test_text_validation_basic(self):
        """Тест базовой валидации текста"""
        print("\n🔤 Тестирование текстовой валидации:")
        
        test_cases = [
            ("Обычный текст", "Привет! Как дела?", True),
            ("Пустой текст", "", False),
            ("Только пробелы", "   ", False),
            ("Слишком длинный текст", "А" * 5000, False),
            ("Много строк", "\n".join(["строка"] * 60), False),
            ("Спам символы", "а" * 60, False),
            ("Эмодзи текст", "Привет! 😊 Как дела?", True),
            ("Текст с числами", "У меня 5 яблок и 3 апельсина", True),
        ]
        
        for name, text, should_pass in test_cases:
            try:
                result = self.validator.validate_text(text)
                if should_pass:
                    self.log_test(name, True, f"Результат: '{result[:30]}{'...' if len(result) > 30 else ''}'")
                else:
                    self.log_test(name, False, "Должна была быть ошибка")
            except ValidationError as e:
                if not should_pass:
                    self.log_test(name, True, f"Правильно отклонён: {e.message[:60]}...")
                else:
                    self.log_test(name, False, f"Неожиданная ошибка: {e.message}")
            except Exception as e:
                self.log_test(name, False, f"Критическая ошибка: {e}")
    
    def test_voice_validation(self):
        """Тест валидации голосовых сообщений"""
        print("\n🎤 Тестирование валидации голосовых сообщений:")
        
        test_cases = [
            ("Нормальный файл", 1024 * 1024, 30.0, True),  # 1MB, 30 сек
            ("Маленький файл", 1024, 1.0, True),  # 1KB, 1 сек
            ("Большой файл", int(30 * 1024 * 1024), 60.0, False),  # 30MB, 60 сек
            ("Длинное аудио", 1024 * 1024, 400.0, False),  # 1MB, 400 сек
            ("Короткое аудио", 1024, 0.1, False),  # 1KB, 0.1 сек
            ("Граничный размер", int(25 * 1024 * 1024), 60.0, True),  # ровно 25MB
            ("Граничная длительность", 1024, 300.0, True),  # ровно 300 сек
        ]
        
        for name, size, duration, should_pass in test_cases:
            try:
                self.validator.validate_voice_file(size, duration)
                if should_pass:
                    self.log_test(name, True, f"{size/(1024*1024):.1f}MB, {duration}сек")
                else:
                    self.log_test(name, False, "Должна была быть ошибка")
            except ValidationError as e:
                if not should_pass:
                    self.log_test(name, True, f"Правильно отклонён: {e.message[:60]}...")
                else:
                    self.log_test(name, False, f"Неожиданная ошибка: {e.message}")
            except Exception as e:
                self.log_test(name, False, f"Критическая ошибка: {e}")
    
    def test_transcription_validation(self):
        """Тест валидации транскрибированного текста"""
        print("\n📝 Тестирование валидации транскрибации:")
        
        test_cases = [
            ("Чистая транскрибация", "Привет, как дела?", True),
            ("Транскрибация с артефактами", "эээ... ну... типа того...", True),
            ("Пустая транскрибация", "", False),
            ("Только пробелы", "   ", False),
            ("Длинная транскрибация", "А" * 5000, False),
            ("Много строк", "\n".join(["слово"] * 60), False),
        ]
        
        for name, text, should_pass in test_cases:
            try:
                result = self.validator.validate_transcribed_text(text)
                if should_pass:
                    self.log_test(name, True, f"Результат: '{result[:30]}{'...' if len(result) > 30 else ''}'")
                else:
                    self.log_test(name, False, "Должна была быть ошибка")
            except ValidationError as e:
                if not should_pass:
                    self.log_test(name, True, f"Правильно отклонена: {e.message[:60]}...")
                else:
                    self.log_test(name, False, f"Неожиданная ошибка: {e.message}")
            except Exception as e:
                self.log_test(name, False, f"Критическая ошибка: {e}")
    
    def test_rate_limiting(self):
        """Тест rate limiting"""
        print("\n⏰ Тестирование rate limiting:")
        
        user_id = 99999  # тестовый ID
        
        # Тест: много быстрых запросов от одного пользователя
        rate_limited = False
        requests_made = 0
        try:
            for i in range(self.validator.settings.MAX_REQUESTS_PER_MINUTE + 5):
                self.validator._check_rate_limit(user_id)
                requests_made = i + 1
        except ValidationError as e:
            rate_limited = True
            self.log_test("Rate limiting per minute", True, 
                         f"Заблокировано после {requests_made} запросов: {e.message[:50]}...")
        
        if not rate_limited:
            self.log_test("Rate limiting per minute", False, 
                         f"Rate limit не сработал после {requests_made} запросов")
    
    def test_edge_cases(self):
        """Тест граничных случаев"""
        print("\n🔍 Тестирование граничных случаев:")
        
        # Граничные длины текста
        try:
            # Минимальная длина
            result = self.validator.validate_text("а")
            self.log_test("Минимальная длина текста", True, "1 символ принят")
        except Exception as e:
            self.log_test("Минимальная длина текста", False, str(e))
        
        try:
            # Максимальная длина (но не спам)
            max_text = ("Это предложение. " * 250)[:self.validator.settings.TEXT_MAX_LENGTH]
            result = self.validator.validate_text(max_text)
            self.log_test("Максимальная длина текста", True, f"{len(result)} символов принято")
        except Exception as e:
            self.log_test("Максимальная длина текста", False, str(e))
        
        # Граничные случаи для голоса
        try:
            # Минимальная длительность
            self.validator.validate_voice_file(1024, self.validator.settings.VOICE_MIN_DURATION_SEC)
            self.log_test("Минимальная длительность голоса", True, "0.5 сек принято")
        except Exception as e:
            self.log_test("Минимальная длительность голоса", False, str(e))
    
    def print_summary(self):
        """Выводит итоговую сводку"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed in self.test_results if passed)
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 Итоговая сводка:")
        print(f"Всего тестов: {total_tests}")
        print(f"✅ Прошло: {passed_tests}")
        print(f"❌ Провалилось: {failed_tests}")
        print(f"Успешность: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 Все тесты прошли успешно! Логика валидации работает корректно.")
        else:
            print(f"\n⚠️  Найдено {failed_tests} проблем. Проверьте результаты выше.")
        
        return failed_tests == 0


def main():
    """Главная функция тестирования"""
    print("🧪 Автономное тестирование логики валидации")
    print("=" * 50)
    print("💡 Этот скрипт НЕ требует зависимостей проекта")
    print("💡 Никаких внешних запросов НЕ делается")
    print("💡 Ваши лимиты в безопасности!")
    print("=" * 50)
    
    tester = ValidationTester()
    
    try:
        # Запускаем все тесты
        tester.test_text_validation_basic()
        tester.test_voice_validation()
        tester.test_transcription_validation()
        tester.test_rate_limiting()
        tester.test_edge_cases()
        
        # Выводим итоги
        success = tester.print_summary()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n💥 Критическая ошибка при тестировании: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
