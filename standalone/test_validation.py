#!/usr/bin/env python3
"""
Безопасный тестовый скрипт для проверки системы валидации входных данных.
Не использует реальные API ключи и не делает запросы к LLM сервисам.
"""

import asyncio
import sys
import os
from pathlib import Path
from io import BytesIO
from unittest.mock import Mock

# Добавляем корневую директорию проекта в PATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Мокаем aiogram для тестирования без Telegram API
class MockMessage:
    def __init__(self, text=None, voice=None, from_user_id=12345):
        self.text = text
        self.voice = voice
        self.from_user = Mock()
        self.from_user.id = from_user_id

class MockVoice:
    def __init__(self, file_size, duration):
        self.file_size = file_size
        self.duration = duration
        self.file_id = "mock_file_id"

# Импортируем после мокинга
from app.services.validation_service import InputValidator, ValidationError
from app.config.settings import Settings

class ValidationTester:
    """Класс для безопасного тестирования валидации"""
    
    def __init__(self):
        self.validator = InputValidator()
        self.settings = Settings()
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
        
        # Тест 1: Нормальный текст
        try:
            result = self.validator.validate_text("Привет! Как дела?")
            self.log_test("Обычный текст", True, f"Результат: '{result}'")
        except Exception as e:
            self.log_test("Обычный текст", False, str(e))
        
        # Тест 2: Пустой текст
        try:
            self.validator.validate_text("")
            self.log_test("Пустой текст", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Пустой текст", True, f"Правильно отклонён: {e.message}")
        
        # Тест 3: Слишком длинный текст
        long_text = "А" * (self.settings.TEXT_MAX_LENGTH + 1)
        try:
            self.validator.validate_text(long_text)
            self.log_test("Слишком длинный текст", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Слишком длинный текст", True, f"Правильно отклонён: {e.message}")
        
        # Тест 4: Слишком много строк
        many_lines = "\n".join(["строка"] * (self.settings.TEXT_MAX_LINES + 1))
        try:
            self.validator.validate_text(many_lines)
            self.log_test("Слишком много строк", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Слишком много строк", True, f"Правильно отклонён: {e.message}")
        
        # Тест 5: Спам (много повторяющихся символов)
        spam_text = "а" * 60  # больше 50 повторяющихся символов
        try:
            self.validator.validate_text(spam_text)
            self.log_test("Спам-текст", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Спам-текст", True, f"Правильно отклонён: {e.message}")
    
    def test_voice_validation(self):
        """Тест валидации голосовых сообщений"""
        print("\n🎤 Тестирование валидации голосовых сообщений:")
        
        # Тест 1: Нормальный голосовой файл
        try:
            self.validator.validate_voice_file(1024 * 1024, 30.0)  # 1MB, 30 сек
            self.log_test("Нормальный голосовой файл", True)
        except Exception as e:
            self.log_test("Нормальный голосовой файл", False, str(e))
        
        # Тест 2: Слишком большой файл
        try:
            big_size = int(self.settings.VOICE_MAX_SIZE_MB * 1024 * 1024 * 1.1)  # на 10% больше лимита
            self.validator.validate_voice_file(big_size, 30.0)
            self.log_test("Слишком большой файл", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Слишком большой файл", True, f"Правильно отклонён: {e.message}")
        
        # Тест 3: Слишком длинное аудио
        try:
            self.validator.validate_voice_file(1024, self.settings.VOICE_MAX_DURATION_SEC + 10)
            self.log_test("Слишком длинное аудио", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Слишком длинное аудио", True, f"Правильно отклонён: {e.message}")
        
        # Тест 4: Слишком короткое аудио
        try:
            self.validator.validate_voice_file(1024, 0.1)  # 0.1 сек
            self.log_test("Слишком короткое аудио", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Слишком короткое аудио", True, f"Правильно отклонён: {e.message}")
    
    def test_transcription_validation(self):
        """Тест валидации транскрибированного текста"""
        print("\n📝 Тестирование валидации транскрибации:")
        
        # Тест 1: Нормальная транскрибация
        try:
            result = self.validator.validate_transcribed_text("Привет, как дела?")
            self.log_test("Нормальная транскрибация", True, f"Результат: '{result}'")
        except Exception as e:
            self.log_test("Нормальная транскрибация", False, str(e))
        
        # Тест 2: Пустая транскрибация
        try:
            self.validator.validate_transcribed_text("")
            self.log_test("Пустая транскрибация", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Пустая транскрибация", True, f"Правильно отклонена: {e.message}")
        
        # Тест 3: Транскрибация с артефактами (не должна отклоняться как спам)
        weird_transcription = "эээ... ммм... ну... типа того..."
        try:
            result = self.validator.validate_transcribed_text(weird_transcription)
            self.log_test("Транскрибация с артефактами", True, "Корректно принята")
        except Exception as e:
            self.log_test("Транскрибация с артефактами", False, str(e))
    
    async def test_message_validation(self):
        """Тест валидации Telegram сообщений"""
        print("\n💬 Тестирование валидации сообщений:")
        
        # Тест 1: Нормальное текстовое сообщение
        try:
            mock_msg = MockMessage(text="Привет! Как дела?")
            result = await self.validator.validate_and_process_text(mock_msg)
            self.log_test("Нормальное сообщение", True, f"Результат: '{result}'")
        except Exception as e:
            self.log_test("Нормальное сообщение", False, str(e))
        
        # Тест 2: Сообщение без текста
        try:
            mock_msg = MockMessage(text=None)
            await self.validator.validate_and_process_text(mock_msg)
            self.log_test("Сообщение без текста", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Сообщение без текста", True, f"Правильно отклонено: {e.message}")
        
        # Тест 3: Голосовое сообщение
        try:
            mock_voice = MockVoice(1024 * 1024, 30.0)  # 1MB, 30 сек
            mock_msg = MockMessage(voice=mock_voice)
            await self.validator.validate_and_process_voice(mock_msg)
            self.log_test("Нормальное голосовое", True)
        except Exception as e:
            self.log_test("Нормальное голосовое", False, str(e))
        
        # Тест 4: Сообщение без голоса
        try:
            mock_msg = MockMessage(voice=None)
            await self.validator.validate_and_process_voice(mock_msg)
            self.log_test("Сообщение без голоса", False, "Должна была быть ошибка")
        except ValidationError as e:
            self.log_test("Сообщение без голоса", True, f"Правильно отклонено: {e.message}")
    
    def test_rate_limiting(self):
        """Тест rate limiting (осторожно, не истощает реальные лимиты)"""
        print("\n⏰ Тестирование rate limiting:")
        
        user_id = 99999  # тестовый ID
        
        # Тест: много быстрых запросов от одного пользователя
        rate_limited = False
        try:
            for i in range(self.settings.MAX_REQUESTS_PER_MINUTE + 1):
                self.validator._check_rate_limit(user_id)
        except ValidationError as e:
            rate_limited = True
            self.log_test("Rate limiting", True, f"Заблокировано после {i+1} запросов: {e.message}")
        
        if not rate_limited:
            self.log_test("Rate limiting", False, "Rate limit не сработал")
    
    def test_configuration(self):
        """Тест конфигурации"""
        print("\n⚙️ Тестирование конфигурации:")
        
        # Проверяем, что лимиты загружены корректно
        config_ok = True
        config_details = []
        
        if self.settings.TEXT_MAX_LENGTH <= 0:
            config_ok = False
            config_details.append("TEXT_MAX_LENGTH должен быть > 0")
        else:
            config_details.append(f"TEXT_MAX_LENGTH = {self.settings.TEXT_MAX_LENGTH}")
        
        if self.settings.VOICE_MAX_SIZE_MB <= 0:
            config_ok = False
            config_details.append("VOICE_MAX_SIZE_MB должен быть > 0")
        else:
            config_details.append(f"VOICE_MAX_SIZE_MB = {self.settings.VOICE_MAX_SIZE_MB}")
        
        if self.settings.MAX_REQUESTS_PER_MINUTE <= 0:
            config_ok = False
            config_details.append("MAX_REQUESTS_PER_MINUTE должен быть > 0")
        else:
            config_details.append(f"MAX_REQUESTS_PER_MINUTE = {self.settings.MAX_REQUESTS_PER_MINUTE}")
        
        self.log_test("Конфигурация", config_ok, "; ".join(config_details))
    
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
            print("\n🎉 Все тесты прошли успешно! Система валидации работает корректно.")
        else:
            print(f"\n⚠️  Найдено {failed_tests} проблем. Проверьте результаты выше.")
        
        return failed_tests == 0

async def main():
    """Главная функция тестирования"""
    print("🧪 Запуск безопасного тестирования системы валидации")
    print("=" * 60)
    print("💡 Этот скрипт НЕ использует реальные API ключи")
    print("💡 Никаких запросов к внешним сервисам НЕ делается")
    print("💡 Ваши лимиты в безопасности!")
    print("=" * 60)
    
    tester = ValidationTester()
    
    try:
        # Запускаем все тесты
        tester.test_configuration()
        tester.test_text_validation_basic()
        tester.test_voice_validation()
        tester.test_transcription_validation()
        await tester.test_message_validation()
        tester.test_rate_limiting()
        
        # Выводим итоги
        success = tester.print_summary()
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n💥 Критическая ошибка при тестировании: {e}")
        print("Проверьте, что все зависимости установлены и проект настроен корректно.")
        return 2

if __name__ == "__main__":
    # Убеждаемся, что не используем реальные API ключи
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("BOT_TOKEN", None)
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
