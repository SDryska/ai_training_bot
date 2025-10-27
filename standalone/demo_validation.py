#!/usr/bin/env python3
"""
Быстрое демо системы валидации с интерактивными примерами.
Показывает, как работает валидация в реальном времени.
"""

import sys
import time
from pathlib import Path

# Добавляем корневую директорию проекта в PATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Импортируем автономный валидатор
from standalone_validation_test import StandaloneValidator, ValidationError


def print_header():
    """Выводит заголовок демо"""
    print("🎬 ДЕМО: Система валидации входных данных")
    print("=" * 55)
    print("💡 Безопасно - никаких API запросов!")
    print("🎯 Показывает реальную работу валидации")
    print("=" * 55)
    print()


def demo_text_validation():
    """Демонстрирует валидацию текста"""
    validator = StandaloneValidator()
    
    print("📝 ДЕМО: Валидация текстовых сообщений")
    print("-" * 40)
    
    test_texts = [
        ("✅ Нормальный текст", "Привет! Как дела? Хочу пройти обучение."),
        ("❌ Пустое сообщение", ""),
        ("❌ Слишком длинное", "А" * 100 + "... (представьте здесь 4000+ символов)"),
        ("❌ Спам", "ааааааааааааааааааааааааааааааааааааааааааааааааааааааа"),
        ("✅ С эмодзи", "Отлично! 😊 Жду ответа! 🚀"),
        ("❌ Много строк", "\n".join([f"Строка {i}" for i in range(15)]) + "\n... (представьте 50+ строк)"),
    ]
    
    for status, text in test_texts:
        print(f"\n{status} Тестируем: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        try:
            result = validator.validate_text(text)
            print(f"   ✅ Принято: '{result[:40]}{'...' if len(result) > 40 else ''}'")
            print(f"   📏 Длина: {len(result)} символов, строк: {len(result.split(chr(10)))}")
        except ValidationError as e:
            print(f"   ❌ Отклонено: {e.message}")
        
        time.sleep(0.5)  # Небольшая пауза для читаемости


def demo_voice_validation():
    """Демонстрирует валидацию голосовых файлов"""
    validator = StandaloneValidator()
    
    print("\n\n🎤 ДЕМО: Валидация голосовых сообщений")
    print("-" * 40)
    
    test_voices = [
        ("✅ Нормальный файл", 1.5 * 1024 * 1024, 30.0),  # 1.5MB, 30 сек
        ("✅ Короткое сообщение", 0.5 * 1024 * 1024, 5.0),  # 0.5MB, 5 сек
        ("❌ Слишком большой", 30 * 1024 * 1024, 60.0),  # 30MB, 60 сек  
        ("❌ Слишком длинное", 2 * 1024 * 1024, 400.0),  # 2MB, 400 сек
        ("❌ Слишком короткое", 1024, 0.1),  # 1KB, 0.1 сек
        ("✅ Граничный случай", 25 * 1024 * 1024, 300.0),  # 25MB, 300 сек
    ]
    
    for status, size_bytes, duration in test_voices:
        size_mb = size_bytes / (1024 * 1024)
        print(f"\n{status} Файл: {size_mb:.1f}МБ, {duration}сек")
        
        try:
            validator.validate_voice_file(int(size_bytes), duration)
            print(f"   ✅ Принят: размер и длительность в пределах нормы")
        except ValidationError as e:
            print(f"   ❌ Отклонён: {e.message}")
        
        time.sleep(0.3)


def demo_rate_limiting():
    """Демонстрирует работу rate limiting"""
    validator = StandaloneValidator()
    
    print("\n\n⏰ ДЕМО: Rate Limiting (ограничение частоты запросов)")
    print("-" * 40)
    
    user_id = 12345
    print(f"👤 Пользователь {user_id} отправляет много сообщений подряд...")
    print(f"📊 Лимит: {validator.settings.MAX_REQUESTS_PER_MINUTE} запросов/минуту")
    
    for i in range(validator.settings.MAX_REQUESTS_PER_MINUTE + 3):
        try:
            validator._check_rate_limit(user_id)
            if i < 5 or i % 5 == 0:  # Показываем первые 5 и каждый 5-й
                print(f"   ✅ Запрос {i+1}: разрешён")
        except ValidationError as e:
            print(f"   ❌ Запрос {i+1}: заблокирован - {e.message}")
            break
        
        if i == 4:
            print("   ... (пропускаем промежуточные запросы)")
    
    print("💡 Rate limiting защищает от спама и злоупотреблений!")


def demo_transcription():
    """Демонстрирует валидацию транскрибации"""
    validator = StandaloneValidator()
    
    print("\n\n📜 ДЕМО: Валидация транскрибированного текста")
    print("-" * 40)
    print("💡 Для транскрибации отключены проверки на спам")
    
    test_transcriptions = [
        ("✅ Чистая речь", "Добро пожаловать в наш сервис обучения"),
        ("✅ С артефактами", "эээ... ну... в общем... хочу... типа... узнать"),
        ("✅ Неформальная", "ага, понял, спасибо, буду делать"),
        ("❌ Пустая", ""),
        ("❌ Слишком длинная", "слово " * 1000 + "... (представьте 4000+ символов)"),
    ]
    
    for status, text in test_transcriptions:
        print(f"\n{status} Транскрибация: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        try:
            result = validator.validate_transcribed_text(text)
            print(f"   ✅ Принята: '{result[:40]}{'...' if len(result) > 40 else ''}'")
        except ValidationError as e:
            print(f"   ❌ Отклонена: {e.message}")
        
        time.sleep(0.4)


def demo_real_scenarios():
    """Демонстрирует реальные сценарии использования"""
    validator = StandaloneValidator()
    
    print("\n\n🎭 ДЕМО: Реальные сценарии использования")
    print("-" * 40)
    
    scenarios = [
        ("Обычный диалог", "Привет! Я хочу пройти курс по обратной связи."),
        ("Длинный вопрос", "Здравствуйте! Подскажите, пожалуйста, как правильно давать обратную связь коллегам? У меня часто возникают сложности в общении, особенно когда нужно указать на ошибки. Хочется делать это деликатно, но эффективно."),
        ("Эмоциональное сообщение", "Очень расстроен! 😢 Коллега опять не выполнил задачу вовремя! Как с этим работать?"),
        ("Попытка спама", "Купите наши услуги!!! Лучшие цены!!! Звоните прямо сейчас!!!!!!!!!!!!!!!!!!!!!!!!"),
        ("Техническая ошибка", "   "),  # только пробелы
    ]
    
    for scenario_name, text in scenarios:
        print(f"\n🎬 Сценарий: {scenario_name}")
        print(f"   📝 Сообщение: '{text[:60]}{'...' if len(text) > 60 else ''}'")
        
        try:
            result = validator.validate_text(text)
            print(f"   ✅ Обработка: сообщение принято и будет передано в AI")
            print(f"   📊 Статистика: {len(result)} символов, {len(result.split())} слов")
        except ValidationError as e:
            print(f"   ❌ Блокировка: {e.message}")
            print(f"   💡 Результат: пользователь получит понятное объяснение")
        
        time.sleep(0.6)


def print_summary():
    """Выводит итоговую сводку возможностей"""
    print("\n\n📋 ИТОГИ ДЕМОНСТРАЦИИ")
    print("=" * 55)
    print("✅ Система валидации успешно:")
    print("   • Принимает корректные сообщения любой длины (до лимита)")
    print("   • Блокирует слишком длинный или пустой контент")
    print("   • Определяет и останавливает спам")
    print("   • Контролирует размер и длительность голосовых файлов")
    print("   • Ограничивает частоту запросов (rate limiting)")
    print("   • Обрабатывает транскрибацию с артефактами")
    print("   • Даёт понятные сообщения об ошибках на русском языке")
    print()
    print("🛡️ Защита LLM:")
    print("   • Экономит токены, блокируя невалидный контент")
    print("   • Предотвращает дорогие запросы с некорректными данными")
    print("   • Защищает от злоупотреблений и спама")
    print()
    print("💡 Готово к использованию в продакшене!")
    print("   • Настраиваемые лимиты через .env")
    print("   • Метрики для мониторинга")
    print("   • Многоуровневая защита (handlers → gateway → LLM)")


def main():
    """Главная функция демо"""
    print_header()
    
    try:
        demo_text_validation()
        demo_voice_validation()
        demo_rate_limiting()
        demo_transcription()
        demo_real_scenarios()
        print_summary()
        
        print("\n🎉 Демонстрация завершена!")
        print("💡 Запустите 'python standalone_validation_test.py' для полного тестирования")
        
    except KeyboardInterrupt:
        print("\n\n👋 Демонстрация прервана пользователем")
    except Exception as e:
        print(f"\n💥 Ошибка демонстрации: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
