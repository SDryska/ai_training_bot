#!/usr/bin/env python3
"""
Интерактивный тестовый скрипт для ручной проверки системы валидации.
Позволяет вводить текст и проверять, как работает валидация.
Безопасен - не использует API ключи и не делает реальных запросов.
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию проекта в PATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.validation_service import InputValidator, ValidationError
from app.config.settings import Settings

class InteractiveValidator:
    """Интерактивный валидатор для ручного тестирования"""
    
    def __init__(self):
        self.validator = InputValidator()
        self.settings = Settings()
        
    def print_config(self):
        """Показывает текущие настройки валидации"""
        print("⚙️  Текущие лимиты валидации:")
        print(f"   📝 Текст: {self.settings.TEXT_MIN_LENGTH}-{self.settings.TEXT_MAX_LENGTH} символов")
        print(f"   📝 Строки: максимум {self.settings.TEXT_MAX_LINES}")
        print(f"   🎤 Аудио: {self.settings.VOICE_MIN_DURATION_SEC}-{self.settings.VOICE_MAX_DURATION_SEC} сек")
        print(f"   🎤 Размер: максимум {self.settings.VOICE_MAX_SIZE_MB} МБ")
        print(f"   ⏰ Лимит: {self.settings.MAX_REQUESTS_PER_MINUTE}/мин, {self.settings.MAX_REQUESTS_PER_HOUR}/час")
        print()
    
    def test_text(self, text: str) -> bool:
        """Тестирует валидацию текста"""
        try:
            result = self.validator.validate_text(text)
            print(f"✅ Текст принят: '{result[:50]}{'...' if len(result) > 50 else ''}'")
            print(f"   Длина: {len(result)} символов")
            print(f"   Строк: {len(result.split(chr(10)))}")
            return True
        except ValidationError as e:
            print(f"❌ Текст отклонён: {e.message}")
            print(f"   Код ошибки: {e.error_code}")
            return False
        except Exception as e:
            print(f"💥 Неожиданная ошибка: {e}")
            return False
    
    def test_voice_params(self, size_mb: float, duration_sec: float) -> bool:
        """Тестирует валидацию параметров голосового файла"""
        try:
            size_bytes = int(size_mb * 1024 * 1024)
            self.validator.validate_voice_file(size_bytes, duration_sec)
            print(f"✅ Голосовой файл принят: {size_mb}МБ, {duration_sec}сек")
            return True
        except ValidationError as e:
            print(f"❌ Голосовой файл отклонён: {e.message}")
            print(f"   Код ошибки: {e.error_code}")
            return False
        except Exception as e:
            print(f"💥 Неожиданная ошибка: {e}")
            return False
    
    def test_transcription(self, text: str) -> bool:
        """Тестирует валидацию транскрибированного текста"""
        try:
            result = self.validator.validate_transcribed_text(text)
            print(f"✅ Транскрибация принята: '{result[:50]}{'...' if len(result) > 50 else ''}'")
            return True
        except ValidationError as e:
            print(f"❌ Транскрибация отклонена: {e.message}")
            print(f"   Код ошибки: {e.error_code}")
            return False
        except Exception as e:
            print(f"💥 Неожиданная ошибка: {e}")
            return False
    
    def run_interactive(self):
        """Запускает интерактивный режим"""
        print("🧪 Интерактивное тестирование системы валидации")
        print("=" * 55)
        print("💡 Безопасно - никаких API запросов не делается!")
        print("=" * 55)
        print()
        
        self.print_config()
        
        while True:
            print("Выберите тип теста:")
            print("1. 📝 Тест валидации текста")
            print("2. 🎤 Тест параметров голосового файла")  
            print("3. 📜 Тест валидации транскрибации")
            print("4. ⚙️  Показать настройки")
            print("5. 🚪 Выход")
            print()
            
            choice = input("Ваш выбор (1-5): ").strip()
            print()
            
            if choice == "1":
                self.interactive_text_test()
            elif choice == "2":
                self.interactive_voice_test()
            elif choice == "3":
                self.interactive_transcription_test()
            elif choice == "4":
                self.print_config()
            elif choice == "5":
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор. Попробуйте снова.")
            
            print("-" * 55)
    
    def interactive_text_test(self):
        """Интерактивный тест валидации текста"""
        print("📝 Тест валидации текста")
        print("Введите текст для проверки (или 'назад' для возврата):")
        print()
        
        while True:
            text = input("Текст: ")
            if text.lower() == "назад":
                break
            
            print()
            self.test_text(text)
            print()
            print("Введите следующий текст или 'назад':")
    
    def interactive_voice_test(self):
        """Интерактивный тест валидации голосового файла"""
        print("🎤 Тест параметров голосового файла")
        print("Введите параметры файла (или 'назад' для возврата):")
        print()
        
        while True:
            try:
                size_input = input("Размер файла в МБ: ")
                if size_input.lower() == "назад":
                    break
                
                duration_input = input("Длительность в секундах: ")
                if duration_input.lower() == "назад":
                    break
                
                size_mb = float(size_input)
                duration_sec = float(duration_input)
                
                print()
                self.test_voice_params(size_mb, duration_sec)
                print()
                print("Введите параметры следующего файла или 'назад':")
                
            except ValueError:
                print("❌ Ошибка: введите числовые значения")
                print()
    
    def interactive_transcription_test(self):
        """Интерактивный тест валидации транскрибации"""
        print("📜 Тест валидации транскрибации")
        print("Введите результат транскрибации (или 'назад' для возврата):")
        print("💡 Для транскрибации не применяются проверки на спам")
        print()
        
        while True:
            text = input("Транскрибация: ")
            if text.lower() == "назад":
                break
            
            print()
            self.test_transcription(text)
            print()
            print("Введите следующую транскрибацию или 'назад':")

def run_predefined_tests():
    """Запускает набор предопределённых тестов"""
    print("🔬 Запуск предопределённых тестов")
    print("=" * 40)
    
    validator = InteractiveValidator()
    
    test_cases = [
        # Текстовые тесты
        ("Обычный текст", "text", "Привет! Как дела?"),
        ("Пустой текст", "text", ""),
        ("Очень длинный текст", "text", "А" * 5000),
        ("Много строк", "text", "\n".join(["строка"] * 60)),
        ("Спам символы", "text", "а" * 60),
        ("Эмодзи", "text", "Привет! 😊 Как дела? 🎉"),
        
        # Голосовые тесты
        ("Нормальный голос", "voice", (1.5, 30.0)),  # 1.5МБ, 30сек
        ("Большой файл", "voice", (30.0, 60.0)),     # 30МБ, 60сек
        ("Длинное аудио", "voice", (2.0, 400.0)),    # 2МБ, 400сек
        ("Короткое аудио", "voice", (0.1, 0.1)),     # 0.1МБ, 0.1сек
        
        # Транскрибация
        ("Чистая транскрибация", "transcription", "Добро пожаловать в наш сервис"),
        ("Транскрибация с артефактами", "transcription", "эээ... ну... типа того..."),
        ("Пустая транскрибация", "transcription", ""),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for name, test_type, data in test_cases:
        print(f"\nТест: {name}")
        
        if test_type == "text":
            result = validator.test_text(data)
        elif test_type == "voice":
            size_mb, duration_sec = data
            result = validator.test_voice_params(size_mb, duration_sec)
        elif test_type == "transcription":
            result = validator.test_transcription(data)
        else:
            result = False
        
        if result:
            passed += 1
    
    print(f"\n📊 Результаты: {passed}/{total} тестов прошли успешно")
    print(f"Успешность: {(passed/total*100):.1f}%")

def main():
    """Главная функция"""
    # Убеждаемся, что не используем реальные API ключи
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("BOT_TOKEN", None)
    
    print("Выберите режим:")
    print("1. 🎮 Интерактивное тестирование")
    print("2. 🔬 Автоматические тесты")
    print()
    
    choice = input("Ваш выбор (1-2): ").strip()
    print()
    
    if choice == "1":
        validator = InteractiveValidator()
        validator.run_interactive()
    elif choice == "2":
        run_predefined_tests()
    else:
        print("❌ Неверный выбор")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
