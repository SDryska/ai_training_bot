"""
Скрипт для тестирования диалоговых моделей вне интерфейса бота.

Позволяет:
- Выбрать кейс (career_dialog, fb_employee, fb_peer)
- Протестировать диалоговую модель (DIALOGUE_MODEL)
- Протестировать рецензента (REVIEWER_MODEL)
- Логировать все входы и выходы моделей

Запуск:
    python standalone/test_dialogue_models.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import Settings
from app.services.ai_service import initialize_ai_providers, get_ai_gateway
from app.providers.base import ProviderType

# Импорт конфигураций кейсов
from app.cases.career_dialog.config import CareerDialogConfig, DIALOGUE_MODEL as CAREER_DIALOGUE_MODEL, REVIEWER_MODEL as CAREER_REVIEWER_MODEL
from app.cases.fb_employee.config import AIDemoConfig, DIALOGUE_MODEL as FB_EMPLOYEE_DIALOGUE_MODEL, REVIEWER_MODEL as FB_EMPLOYEE_REVIEWER_MODEL
from app.cases.fb_peer.config import FBPeerConfig, DIALOGUE_MODEL as FB_PEER_DIALOGUE_MODEL, REVIEWER_MODEL as FB_PEER_REVIEWER_MODEL

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class DialogueTester:
    """Класс для тестирования диалоговых моделей"""
    
    def __init__(self, case_id: str):
        """
        Инициализирует тестер для конкретного кейса.
        
        Args:
            case_id: Идентификатор кейса (career_dialog, fb_employee, fb_peer)
        """
        self.case_id = case_id
        self.config = self._get_config()
        self.dialogue_model = self._get_dialogue_model()
        self.reviewer_model = self._get_reviewer_model()
        self.dialogue_entries = []
        self.turn_count = 0
        self.components_achieved = set()
        self.ai_gateway = get_ai_gateway()
        
        # Логирование в файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = project_root / "standalone" / f"dialogue_test_{case_id}_{timestamp}.log"
        self.log_file.parent.mkdir(exist_ok=True)
        
    def _get_config(self):
        """Возвращает конфигурацию для выбранного кейса"""
        configs = {
            "career_dialog": CareerDialogConfig,
            "fb_employee": AIDemoConfig,
            "fb_peer": FBPeerConfig,
        }
        if self.case_id not in configs:
            raise ValueError(f"Неизвестный кейс: {self.case_id}. Доступны: {list(configs.keys())}")
        return configs[self.case_id]
    
    def _get_dialogue_model(self) -> str:
        """Возвращает модель для диалога"""
        models = {
            "career_dialog": CAREER_DIALOGUE_MODEL,
            "fb_employee": FB_EMPLOYEE_DIALOGUE_MODEL,
            "fb_peer": FB_PEER_DIALOGUE_MODEL,
        }
        return models[self.case_id]
    
    def _get_reviewer_model(self) -> str:
        """Возвращает модель для рецензента"""
        models = {
            "career_dialog": CAREER_REVIEWER_MODEL,
            "fb_employee": FB_EMPLOYEE_REVIEWER_MODEL,
            "fb_peer": FB_PEER_REVIEWER_MODEL,
        }
        return models[self.case_id]
    
    def _log(self, message: str):
        """Логирует сообщение в файл и консоль"""
        logger.info(message)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | {message}\n")
    
    def _log_separator(self, title: str = ""):
        """Логирует разделитель"""
        separator = "=" * 80
        if title:
            self._log(f"\n{separator}")
            self._log(f"  {title}")
            self._log(separator)
        else:
            self._log(separator)
    
    def _parse_ai_response(self, response_text: str) -> dict:
        """Парсит JSON ответ от ИИ с fallback"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                if "ReplyText" in parsed:
                    return parsed
                    
        except (json.JSONDecodeError, ValueError) as e:
            self._log(f"⚠️  Ошибка парсинга JSON: {e}")
        
        # Fallback
        if self.case_id == "career_dialog":
            return {
                "ReplyText": response_text,
                "Aspirations": False,
                "Strengths": False,
                "Development": False,
                "Opportunities": False,
                "Plan": False
            }
        else:  # fb_employee или fb_peer
            return {
                "ReplyText": response_text,
                "Behavior": False,
                "Result": False,
                "Emotion": False,
                "Question": False,
                "Agreement": False
            }
    
    def _parse_reviewer_response(self, response_text: str) -> dict:
        """Парсит JSON ответ от рецензента"""
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                if "overall" in parsed:
                    return parsed
                    
        except (json.JSONDecodeError, ValueError) as e:
            self._log(f"⚠️  Ошибка парсинга JSON рецензента: {e}")
        
        return {
            "overall": response_text,
            "goodPoints": [],
            "improvementPoints": []
        }
    
    def _extract_dialogue_text(self) -> str:
        """Извлекает только диалог для рецензента"""
        dialogue_lines = []
        for entry in self.dialogue_entries:
            role = entry.get("role", "")
            text = entry.get("text", "")
            if role and text:
                dialogue_lines.append(f"{role}: {text}")
        return "\n\n".join(dialogue_lines)
    
    async def send_user_message(self, user_text: str) -> dict:
        """
        Отправляет сообщение пользователя модели и возвращает ответ.
        
        Args:
            user_text: Текст сообщения пользователя
            
        Returns:
            dict: Словарь с результатами (parsed_response, raw_response, etc.)
        """
        self.turn_count += 1
        
        self._log_separator(f"ХОД #{self.turn_count}")
        
        # Формируем промпт
        user_prompt = self.config.get_user_prompt(user_text)
        system_prompt = self.config.SYSTEM_PROMPT
        
        # Логируем входные данные
        self._log("\n📥 ВХОДНЫЕ ДАННЫЕ:")
        self._log(f"   Модель: {self.dialogue_model}")
        self._log(f"   User ID: 999999 (тестовый)")
        self._log(f"\n📝 USER MESSAGE (оригинал):")
        self._log(f"   {user_text}")
        self._log(f"\n📝 USER PROMPT (отправляется в модель):")
        self._log(f"   {user_prompt}")
        self._log(f"\n📝 SYSTEM PROMPT:")
        for line in system_prompt.split('\n')[:10]:  # Первые 10 строк
            self._log(f"   {line}")
        self._log(f"   ... (всего {len(system_prompt)} символов)")
        
        # Отправляем запрос
        self._log("\n⏳ Отправка запроса к AI...")
        response = await self.ai_gateway.send_message(
            user_id=999999,  # Тестовый ID
            message=user_prompt,
            system_prompt=system_prompt,
            provider_type=ProviderType.OPENAI,
            model_override=self.dialogue_model,
        )
        
        # Логируем сырой ответ
        self._log("\n📤 ОТВЕТ МОДЕЛИ (RAW):")
        if not response.success:
            self._log(f"   ❌ ОШИБКА: {response.error}")
            return {
                "success": False,
                "error": response.error,
                "turn": self.turn_count
            }
        
        raw_content = response.content or "(пустой ответ)"
        self._log(f"   {raw_content}")
        
        # Парсим JSON
        parsed_response = self._parse_ai_response(raw_content)
        
        self._log("\n📊 РАСПАРСЕННЫЙ ОТВЕТ:")
        self._log(f"   ReplyText: {parsed_response.get('ReplyText', 'N/A')}")
        
        # Логируем флаги компонентов
        self._log("\n🎯 ФЛАГИ КОМПОНЕНТОВ:")
        if self.case_id == "career_dialog":
            components = ["Aspirations", "Strengths", "Development", "Opportunities", "Plan"]
            labels = self.config.CAREER_LABELS
        else:
            components = ["Behavior", "Result", "Emotion", "Question", "Agreement"]
            labels = self.config.PROVD_LABELS
        
        for key in components:
            value = parsed_response.get(key, False)
            status = "✅" if value else "❌"
            label = labels.get(key, key)
            self._log(f"   {status} {label}: {value}")
            
            # Обновляем достигнутые компоненты
            if value:
                self.components_achieved.add(key)
        
        # Сохраняем в историю диалога
        if self.case_id == "career_dialog":
            user_role = "Руководитель"
            ai_role = "Максим"
        elif self.case_id == "fb_employee":
            user_role = "Руководитель"
            ai_role = "Евгений"
        else:  # fb_peer
            user_role = "Коллега"
            ai_role = "Александр"
        
        self.dialogue_entries.append({"role": user_role, "text": user_text})
        self.dialogue_entries.append({"role": ai_role, "text": parsed_response.get("ReplyText", "")})
        
        # Статус прогресса
        self._log(f"\n📈 ПРОГРЕСС:")
        self._log(f"   Ход: {self.turn_count}/{self.config.MAX_DIALOGUE_TURNS}")
        self._log(f"   Компоненты: {len(self.components_achieved)}/5")
        self._log(f"   Достигнуты: {', '.join(sorted(self.components_achieved))}")
        
        return {
            "success": True,
            "turn": self.turn_count,
            "raw_response": raw_content,
            "parsed_response": parsed_response,
            "user_prompt": user_prompt,
            "system_prompt": system_prompt,
            "components_achieved": self.components_achieved.copy(),
            "all_components_achieved": len(self.components_achieved) >= 5,
            "max_turns_reached": self.turn_count >= self.config.MAX_DIALOGUE_TURNS
        }
    
    async def request_review(self) -> dict:
        """
        Запрашивает анализ диалога у рецензента.
        
        Returns:
            dict: Словарь с результатами рецензирования
        """
        self._log_separator("ЗАПРОС РЕЦЕНЗИРОВАНИЯ")
        
        # Извлекаем диалог
        dialogue_text = self._extract_dialogue_text()
        
        if not dialogue_text.strip():
            self._log("❌ Диалог пустой, рецензирование невозможно")
            return {
                "success": False,
                "error": "Диалог слишком короткий"
            }
        
        # Формируем промпт для рецензента
        reviewer_prompt = self.config.get_reviewer_prompt(dialogue_text)
        reviewer_system_prompt = self.config.REVIEWER_SYSTEM_PROMPT
        
        # Логируем входные данные рецензента
        self._log("\n📥 ВХОДНЫЕ ДАННЫЕ РЕЦЕНЗЕНТА:")
        self._log(f"   Модель: {self.reviewer_model}")
        self._log(f"   User ID: 1999999 (тестовый рецензент)")
        
        self._log(f"\n📝 ДИАЛОГ ДЛЯ АНАЛИЗА:")
        for line in dialogue_text.split('\n')[:20]:  # Первые 20 строк
            self._log(f"   {line}")
        if len(dialogue_text.split('\n')) > 20:
            self._log(f"   ... (всего {len(dialogue_text.split(chr(10)))} строк)")
        
        self._log(f"\n📝 REVIEWER PROMPT:")
        for line in reviewer_prompt.split('\n')[:15]:
            self._log(f"   {line}")
        self._log(f"   ... (всего {len(reviewer_prompt)} символов)")
        
        self._log(f"\n📝 REVIEWER SYSTEM PROMPT:")
        for line in reviewer_system_prompt.split('\n')[:10]:
            self._log(f"   {line}")
        self._log(f"   ... (всего {len(reviewer_system_prompt)} символов)")
        
        # Очищаем контекст рецензента
        self.ai_gateway.clear_conversation(1999999)
        
        # Отправляем запрос
        self._log("\n⏳ Отправка запроса к рецензенту...")
        response = await self.ai_gateway.send_message(
            user_id=1999999,
            message=reviewer_prompt,
            system_prompt=reviewer_system_prompt,
            provider_type=ProviderType.OPENAI,
            model_override=self.reviewer_model
        )
        
        # Логируем ответ рецензента
        self._log("\n📤 ОТВЕТ РЕЦЕНЗЕНТА (RAW):")
        if not response.success:
            self._log(f"   ❌ ОШИБКА: {response.error}")
            return {
                "success": False,
                "error": response.error
            }
        
        raw_content = response.content or "(пустой ответ)"
        self._log(f"   {raw_content}")
        
        # Парсим ответ рецензента
        parsed_review = self._parse_reviewer_response(raw_content)
        
        self._log("\n📊 РАСПАРСЕННЫЙ АНАЛИЗ:")
        self._log(f"   Overall: {parsed_review.get('overall', 'N/A')}")
        
        good_points = parsed_review.get("goodPoints", [])
        if good_points:
            self._log(f"\n   ✅ Что получилось хорошо:")
            for i, point in enumerate(good_points, 1):
                self._log(f"      {i}. {point}")
        
        improvement_points = parsed_review.get("improvementPoints", [])
        if improvement_points:
            self._log(f"\n   💡 Что можно улучшить:")
            for i, point in enumerate(improvement_points, 1):
                self._log(f"      {i}. {point}")
        
        return {
            "success": True,
            "raw_response": raw_content,
            "parsed_review": parsed_review,
            "reviewer_prompt": reviewer_prompt,
            "dialogue_text": dialogue_text
        }
    
    def print_summary(self):
        """Выводит итоговую сводку по диалогу"""
        self._log_separator("ИТОГОВАЯ СВОДКА")
        self._log(f"📊 Кейс: {self.case_id}")
        self._log(f"📊 Всего ходов: {self.turn_count}")
        self._log(f"📊 Достигнуто компонентов: {len(self.components_achieved)}/5")
        self._log(f"📊 Список компонентов: {', '.join(sorted(self.components_achieved)) if self.components_achieved else 'нет'}")
        self._log(f"📊 Лог-файл: {self.log_file}")
        self._log_separator()


async def interactive_test(case_id: str):
    """
    Запускает интерактивное тестирование диалоговой модели.
    
    Args:
        case_id: Идентификатор кейса
    """
    print("\n" + "=" * 80)
    print(f"🧪 ТЕСТИРОВАНИЕ ДИАЛОГОВОЙ МОДЕЛИ: {case_id.upper()}")
    print("=" * 80)
    
    tester = DialogueTester(case_id)
    
    # Показываем информацию о кейсе
    print(f"\n📋 Конфигурация кейса:")
    print(f"   Case ID: {tester.case_id}")
    print(f"   Dialogue Model: {tester.dialogue_model}")
    print(f"   Reviewer Model: {tester.reviewer_model}")
    print(f"   Max Turns: {tester.config.MAX_DIALOGUE_TURNS}")
    print(f"   Лог-файл: {tester.log_file}")
    
    print(f"\n📝 Стартовое сообщение кейса:")
    print(tester.config.get_start_message())
    
    print("\n" + "-" * 80)
    print("💬 НАЧАЛО ДИАЛОГА")
    print("-" * 80)
    print("\nВведите реплику (или команды: 'review' - получить анализ, 'quit' - выход):\n")
    
    while True:
        try:
            # Получаем ввод пользователя
            user_input = input(f"Ход {tester.turn_count + 1}> ").strip()
            
            if not user_input:
                continue
            
            # Обработка команд
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Выход из тестирования...")
                break
            
            if user_input.lower() in ['review', 'r']:
                print("\n🔍 Запрос анализа диалога...")
                result = await tester.request_review()
                
                if result["success"]:
                    parsed_review = result["parsed_review"]
                    print(f"\n📊 АНАЛИЗ РЕЦЕНЗЕНТА:")
                    print(f"\n{parsed_review.get('overall', 'N/A')}")
                    
                    good_points = parsed_review.get("goodPoints", [])
                    if good_points:
                        print(f"\n✅ Что получилось хорошо:")
                        for i, point in enumerate(good_points, 1):
                            print(f"   {i}. {point}")
                    
                    improvement_points = parsed_review.get("improvementPoints", [])
                    if improvement_points:
                        print(f"\n💡 Что можно улучшить:")
                        for i, point in enumerate(improvement_points, 1):
                            print(f"   {i}. {point}")
                else:
                    print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                
                print("\n" + "-" * 80)
                continue
            
            # Отправляем сообщение
            result = await tester.send_user_message(user_input)
            
            if not result["success"]:
                print(f"\n❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
                continue
            
            # Выводим ответ модели
            parsed = result["parsed_response"]
            reply_text = parsed.get("ReplyText", "")
            
            # Определяем имя персонажа
            if case_id == "career_dialog":
                character_name = "Максим"
            elif case_id == "fb_employee":
                character_name = "Евгений"
            else:
                character_name = "Александр"
            
            print(f"\n{character_name}: {reply_text}")
            
            # Показываем флаги (если хотя бы один True)
            if case_id == "career_dialog":
                components = ["Aspirations", "Strengths", "Development", "Opportunities", "Plan"]
            else:
                components = ["Behavior", "Result", "Emotion", "Question", "Agreement"]
            
            detected = [k for k in components if parsed.get(k, False)]
            if detected:
                print(f"   [Обнаружено: {', '.join(detected)}]")
            
            # Показываем прогресс
            print(f"   📊 Прогресс: {len(result['components_achieved'])}/5 компонентов, ход {result['turn']}/{tester.config.MAX_DIALOGUE_TURNS}")
            
            # Проверяем условия завершения
            if result["all_components_achieved"]:
                print("\n✅ Все компоненты достигнуты!")
                
                auto_review = input("\n🔍 Запросить анализ автоматически? (y/n): ").strip().lower()
                if auto_review == 'y':
                    result = await tester.request_review()
                    if result["success"]:
                        parsed_review = result["parsed_review"]
                        print(f"\n📊 АНАЛИЗ РЕЦЕНЗЕНТА:")
                        print(f"\n{parsed_review.get('overall', 'N/A')}")
                        
                        good_points = parsed_review.get("goodPoints", [])
                        if good_points:
                            print(f"\n✅ Что получилось хорошо:")
                            for i, point in enumerate(good_points, 1):
                                print(f"   {i}. {point}")
                        
                        improvement_points = parsed_review.get("improvementPoints", [])
                        if improvement_points:
                            print(f"\n💡 Что можно улучшить:")
                            for i, point in enumerate(improvement_points, 1):
                                print(f"   {i}. {point}")
                break
            
            if result["max_turns_reached"]:
                print(f"\n⏱️ Достигнут лимит ходов ({tester.config.MAX_DIALOGUE_TURNS})")
                
                auto_review = input("\n🔍 Запросить анализ автоматически? (y/n): ").strip().lower()
                if auto_review == 'y':
                    result = await tester.request_review()
                    if result["success"]:
                        parsed_review = result["parsed_review"]
                        print(f"\n📊 АНАЛИЗ РЕЦЕНЗЕНТА:")
                        print(f"\n{parsed_review.get('overall', 'N/A')}")
                        
                        good_points = parsed_review.get("goodPoints", [])
                        if good_points:
                            print(f"\n✅ Что получилось хорошо:")
                            for i, point in enumerate(good_points, 1):
                                print(f"   {i}. {point}")
                        
                        improvement_points = parsed_review.get("improvementPoints", [])
                        if improvement_points:
                            print(f"\n💡 Что можно улучшить:")
                            for i, point in enumerate(improvement_points, 1):
                                print(f"   {i}. {point}")
                break
            
            print()  # Пустая строка для читаемости
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Прервано пользователем")
            break
        except Exception as e:
            print(f"\n❌ Неожиданная ошибка: {e}")
            logger.exception("Ошибка в интерактивном тестировании")
            break
    
    # Итоговая сводка
    print("\n" + "=" * 80)
    tester.print_summary()
    print("\n✅ Все логи сохранены в файл: " + str(tester.log_file))


async def main():
    """Главная функция"""
    print("\n" + "=" * 80)
    print("🧪 ТЕСТИРОВАНИЕ ДИАЛОГОВЫХ МОДЕЛЕЙ")
    print("=" * 80)
    
    # Инициализация AI провайдеров
    print("\n⏳ Инициализация AI провайдеров...")
    try:
        initialize_ai_providers()
        ai_gateway = get_ai_gateway()
        available = ai_gateway.get_available_providers()
        
        if not available:
            print("❌ AI провайдеры недоступны. Проверьте конфигурацию (OPENAI_API_KEY в .env)")
            return
        
        print(f"✅ Инициализированы провайдеры: {[p.value for p in available]}")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        logger.exception("Ошибка инициализации AI провайдеров")
        return
    
    # Выбор кейса
    print("\n📋 Доступные кейсы:")
    print("   1. career_dialog - Карьерный диалог")
    print("   2. fb_employee - Обратная связь сотруднику (ПРОВД)")
    print("   3. fb_peer - Обратная связь коллеге (ПРОВД)")
    
    while True:
        choice = input("\nВыберите кейс (1-3) или 'q' для выхода: ").strip()
        
        if choice.lower() in ['q', 'quit', 'exit']:
            print("👋 До свидания!")
            return
        
        case_map = {
            "1": "career_dialog",
            "2": "fb_employee",
            "3": "fb_peer"
        }
        
        if choice in case_map:
            case_id = case_map[choice]
            await interactive_test(case_id)
            
            # Спросить, хотим ли продолжить
            again = input("\n🔄 Протестировать другой кейс? (y/n): ").strip().lower()
            if again != 'y':
                print("👋 До свидания!")
                break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Программа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.exception("Критическая ошибка")

