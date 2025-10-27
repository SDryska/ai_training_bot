"""
Тесты для вспомогательных функций хэндлеров кейсов.

Тестируемые модули:
- app/cases/career_dialog/handler.py
- app/cases/fb_peer/handler.py
- app/cases/fb_employee/handler.py

Тестируемые функции:
- format_career_response / format_provd_response
- parse_reviewer_response
- format_review_response
- extract_dialogue_text
"""

import pytest
import json

from app.cases.career_dialog.handler import (
    format_career_response,
    parse_reviewer_response as parse_reviewer_career,
    format_review_response as format_review_career,
    extract_dialogue_text as extract_dialogue_career,
)
from app.cases.fb_peer.handler import (
    format_provd_response as format_provd_peer,
    parse_reviewer_response as parse_reviewer_peer,
    format_review_response as format_review_peer,
    extract_dialogue_text as extract_dialogue_peer,
)
from app.cases.fb_employee.handler import (
    format_provd_response as format_provd_employee,
    parse_reviewer_response as parse_reviewer_employee,
    format_review_response as format_review_employee,
    extract_dialogue_text as extract_dialogue_employee,
)


class TestFormatCareerResponse:
    """Тесты для функции format_career_response (career_dialog)"""

    def test_format_without_analysis(self):
        """Тест: форматирование без анализа (для обычных пользователей)"""
        parsed = {
            "ReplyText": "Давай обсудим твои цели",
            "Aspirations": True,
            "Strengths": False
        }
        
        result = format_career_response(parsed, show_analysis=False)
        
        assert "👨‍💻 *Максим:* Давай обсудим твои цели" in result
        assert "Анализ" not in result
        assert "✅" not in result
        assert "❌" not in result

    def test_format_with_analysis(self):
        """Тест: форматирование с анализом (для админов)"""
        parsed = {
            "ReplyText": "Хорошо, спасибо",
            "Aspirations": True,
            "Strengths": True,
            "Development": False,
            "Opportunities": False,
            "Plan": False
        }
        
        result = format_career_response(parsed, show_analysis=True)
        
        assert "👨‍💻 *Максим:* Хорошо, спасибо" in result
        assert "📊 *Анализ карьерного диалога:*" in result
        assert "✅ 🎯 Устремления" in result
        assert "✅ 💪 Сильные стороны" in result
        assert "❌ 📈 Развитие" in result

    def test_format_empty_reply(self):
        """Тест: форматирование с пустым ответом"""
        parsed = {
            "ReplyText": "",
            "Aspirations": False
        }
        
        result = format_career_response(parsed, show_analysis=False)
        
        assert "👨‍💻 *Максим:*" in result

    def test_format_all_components_achieved(self):
        """Тест: все компоненты достигнуты"""
        parsed = {
            "ReplyText": "Отличный план!",
            "Aspirations": True,
            "Strengths": True,
            "Development": True,
            "Opportunities": True,
            "Plan": True
        }
        
        result = format_career_response(parsed, show_analysis=True)
        
        # Все компоненты должны быть помечены как достигнутые
        assert result.count("✅") == 5
        assert result.count("❌") == 0


class TestFormatProvdResponse:
    """Тесты для функции format_provd_response (fb_peer и fb_employee)"""

    def test_format_peer_without_analysis(self):
        """Тест: форматирование ответа коллеги без анализа"""
        parsed = {
            "ReplyText": "Да, понимаю. Буду внимательнее.",
            "Behavior": True,
            "Result": False
        }
        
        result = format_provd_peer(parsed, show_analysis=False)
        
        assert "👥 *Александр:* Да, понимаю. Буду внимательнее." in result
        assert "Анализ" not in result

    def test_format_peer_with_analysis(self):
        """Тест: форматирование ответа коллеги с анализом"""
        parsed = {
            "ReplyText": "Хорошо, договорились",
            "Behavior": True,
            "Result": True,
            "Emotion": False,
            "Question": False,
            "Agreement": True
        }
        
        result = format_provd_peer(parsed, show_analysis=True)
        
        assert "👥 *Александр:* Хорошо, договорились" in result
        assert "📊 *Анализ ПРОВД:*" in result
        assert "✅ П - Поведение" in result
        assert "✅ Р - Результат" in result
        assert "❌ О - Отношение" in result
        assert "✅ Д - Договорённости" in result

    def test_format_employee_without_analysis(self):
        """Тест: форматирование ответа сотрудника без анализа"""
        parsed = {
            "ReplyText": "Спасибо за обратную связь",
            "Emotion": True
        }
        
        result = format_provd_employee(parsed, show_analysis=False)
        
        assert "💬 *Евгений:* Спасибо за обратную связь" in result

    def test_format_employee_with_analysis(self):
        """Тест: форматирование ответа сотрудника с анализом"""
        parsed = {
            "ReplyText": "Понял, буду работать над этим",
            "Behavior": False,
            "Result": False,
            "Emotion": True,
            "Question": False,
            "Agreement": True
        }
        
        result = format_provd_employee(parsed, show_analysis=True)
        
        assert "💬 *Евгений:* Понял, буду работать над этим" in result
        assert "📊 *Анализ ПРОВД:*" in result
        assert "❌ П - Поведение" in result
        assert "✅ О - Отношение" in result


class TestParseReviewerResponse:
    """Тесты для функции parse_reviewer_response"""

    ALL_PARSERS = [
        pytest.param(parse_reviewer_career, id="career_dialog"),
        pytest.param(parse_reviewer_peer, id="fb_peer"),
        pytest.param(parse_reviewer_employee, id="fb_employee"),
    ]

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_valid_json(self, parser):
        """Тест: парсинг валидного JSON ответа рецензента"""
        response = json.dumps({
            "overall": "Хороший диалог",
            "goodPoints": ["Конкретные факты", "Открытые вопросы"],
            "improvementPoints": ["Больше эмпатии"]
        })
        
        result = parser(response)
        
        assert result["overall"] == "Хороший диалог"
        assert len(result["goodPoints"]) == 2
        assert len(result["improvementPoints"]) == 1

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_text_around(self, parser):
        """Тест: JSON с текстом вокруг"""
        response = "Вот мой анализ: " + json.dumps({
            "overall": "Отличная работа",
            "goodPoints": ["Эмпатия"],
            "improvementPoints": []
        }) + " Конец анализа."
        
        result = parser(response)
        
        assert result["overall"] == "Отличная работа"
        assert result["goodPoints"] == ["Эмпатия"]
        assert result["improvementPoints"] == []

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_empty_arrays(self, parser):
        """Тест: пустые массивы в JSON"""
        response = json.dumps({
            "overall": "Нейтральный результат",
            "goodPoints": [],
            "improvementPoints": []
        })
        
        result = parser(response)
        
        assert result["overall"] == "Нейтральный результат"
        assert result["goodPoints"] == []
        assert result["improvementPoints"] == []

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_malformed_json(self, parser):
        """Тест: некорректный JSON (fallback)"""
        response = '{"overall": "Незакрытый JSON'
        
        result = parser(response)
        
        # Должен вернуть исходный текст как overall
        assert result["overall"] == response
        assert result["goodPoints"] == []
        assert result["improvementPoints"] == []

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_plain_text(self, parser):
        """Тест: обычный текст без JSON (fallback)"""
        response = "Это просто текстовый отзыв без структуры"
        
        result = parser(response)
        
        assert result["overall"] == response
        assert result["goodPoints"] == []
        assert result["improvementPoints"] == []

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_without_overall(self, parser):
        """Тест: JSON без обязательного поля overall (fallback)"""
        response = json.dumps({
            "goodPoints": ["Что-то хорошее"],
            "improvementPoints": ["Что-то плохое"]
        })
        
        result = parser(response)
        
        # Без overall — должен быть fallback
        assert result["overall"] == response

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_long_review(self, parser):
        """Тест: длинный отзыв с множеством пунктов"""
        good_points = [f"Хороший момент {i}" for i in range(10)]
        improvement_points = [f"Улучшение {i}" for i in range(5)]
        
        response = json.dumps({
            "overall": "Детальный анализ диалога показывает смешанные результаты",
            "goodPoints": good_points,
            "improvementPoints": improvement_points
        })
        
        result = parser(response)
        
        assert len(result["goodPoints"]) == 10
        assert len(result["improvementPoints"]) == 5


class TestFormatReviewResponse:
    """Тесты для функции format_review_response"""

    ALL_FORMATTERS = [
        pytest.param(format_review_career, id="career_dialog"),
        pytest.param(format_review_peer, id="fb_peer"),
        pytest.param(format_review_employee, id="fb_employee"),
    ]

    @pytest.mark.parametrize("formatter", ALL_FORMATTERS)
    def test_format_full_review(self, formatter):
        """Тест: форматирование полного отзыва"""
        parsed = {
            "overall": "Хороший диалог в целом",
            "goodPoints": ["Конкретика", "Эмпатия"],
            "improvementPoints": ["Больше вопросов"]
        }
        
        result = formatter(parsed)
        
        assert "Хороший диалог в целом" in result
        assert "1. Конкретика" in result
        assert "2. Эмпатия" in result
        assert "1. Больше вопросов" in result

    @pytest.mark.parametrize("formatter", ALL_FORMATTERS)
    def test_format_only_overall(self, formatter):
        """Тест: только общая оценка, без списков"""
        parsed = {
            "overall": "Нейтральный результат",
            "goodPoints": [],
            "improvementPoints": []
        }
        
        result = formatter(parsed)
        
        assert "Нейтральный результат" in result
        # Проверяем, что заголовки списков не включены
        assert "Что получилось хорошо" not in result or result.count("Что получилось хорошо") == 0

    @pytest.mark.parametrize("formatter", ALL_FORMATTERS)
    def test_format_only_good_points(self, formatter):
        """Тест: только положительные моменты"""
        parsed = {
            "overall": "Отличная работа!",
            "goodPoints": ["Все отлично", "Продолжай в том же духе"],
            "improvementPoints": []
        }
        
        result = formatter(parsed)
        
        assert "Отличная работа!" in result
        assert "Все отлично" in result
        assert "Продолжай в том же духе" in result

    @pytest.mark.parametrize("formatter", ALL_FORMATTERS)
    def test_format_only_improvement_points(self, formatter):
        """Тест: только точки улучшения"""
        parsed = {
            "overall": "Есть над чем поработать",
            "goodPoints": [],
            "improvementPoints": ["Больше конкретики", "Слушать активнее"]
        }
        
        result = formatter(parsed)
        
        assert "Есть над чем поработать" in result
        assert "Больше конкретики" in result
        assert "Слушать активнее" in result

    @pytest.mark.parametrize("formatter", ALL_FORMATTERS)
    def test_format_numbered_lists(self, formatter):
        """Тест: нумерация списков"""
        parsed = {
            "overall": "Анализ",
            "goodPoints": ["Первое", "Второе", "Третье"],
            "improvementPoints": ["Раз", "Два"]
        }
        
        result = formatter(parsed)
        
        # Проверяем нумерацию
        assert "1. Первое" in result
        assert "2. Второе" in result
        assert "3. Третье" in result
        assert "1. Раз" in result
        assert "2. Два" in result


class TestExtractDialogueText:
    """Тесты для функции extract_dialogue_text"""

    ALL_EXTRACTORS = [
        pytest.param(extract_dialogue_career, id="career_dialog"),
        pytest.param(extract_dialogue_peer, id="fb_peer"),
        pytest.param(extract_dialogue_employee, id="fb_employee"),
    ]

    @pytest.mark.parametrize("extractor", ALL_EXTRACTORS)
    def test_extract_simple_dialogue(self, extractor):
        """Тест: извлечение простого диалога"""
        entries = [
            {"role": "Руководитель", "text": "Привет, как дела?"},
            {"role": "Максим", "text": "Хорошо, спасибо."},
            {"role": "Руководитель", "text": "Давай обсудим твои цели."},
        ]
        
        result = extractor(entries)
        
        assert "Руководитель: Привет, как дела?" in result
        assert "Максим: Хорошо, спасибо." in result
        assert "Руководитель: Давай обсудим твои цели." in result
        # Проверяем разделители между репликами
        assert "\n\n" in result

    @pytest.mark.parametrize("extractor", ALL_EXTRACTORS)
    def test_extract_empty_dialogue(self, extractor):
        """Тест: пустой диалог"""
        entries = []
        
        result = extractor(entries)
        
        assert result == ""

    @pytest.mark.parametrize("extractor", ALL_EXTRACTORS)
    def test_extract_dialogue_with_empty_entries(self, extractor):
        """Тест: диалог с пустыми записями"""
        entries = [
            {"role": "Руководитель", "text": "Первая реплика"},
            {"role": "", "text": "Нет роли"},
            {"role": "Максим", "text": ""},
            {"role": "Руководитель", "text": "Вторая реплика"},
        ]
        
        result = extractor(entries)
        
        # Записи с пустой ролью или текстом должны игнорироваться
        assert "Первая реплика" in result
        assert "Вторая реплика" in result
        assert "Нет роли" not in result

    @pytest.mark.parametrize("extractor", ALL_EXTRACTORS)
    def test_extract_dialogue_with_special_characters(self, extractor):
        """Тест: диалог со спецсимволами"""
        entries = [
            {"role": "Руководитель", "text": "Текст с \"кавычками\" и \nпереносами"},
            {"role": "Максим", "text": "Ответ с символами: !@#$%"},
        ]
        
        result = extractor(entries)
        
        assert "кавычками" in result
        assert "переносами" in result
        assert "!@#$%" in result

    @pytest.mark.parametrize("extractor", ALL_EXTRACTORS)
    def test_extract_long_dialogue(self, extractor):
        """Тест: длинный диалог"""
        entries = []
        for i in range(20):
            role = "Руководитель" if i % 2 == 0 else "Максим"
            entries.append({"role": role, "text": f"Реплика номер {i}"})
        
        result = extractor(entries)
        
        # Проверяем что все реплики присутствуют
        assert "Реплика номер 0" in result
        assert "Реплика номер 19" in result
        # Проверяем количество разделителей (должно быть на 1 меньше чем записей)
        assert result.count("\n\n") == 19

    @pytest.mark.parametrize("extractor", ALL_EXTRACTORS)
    def test_extract_dialogue_preserves_order(self, extractor):
        """Тест: порядок реплик сохраняется"""
        entries = [
            {"role": "Руководитель", "text": "Первое"},
            {"role": "Максим", "text": "Второе"},
            {"role": "Руководитель", "text": "Третье"},
        ]
        
        result = extractor(entries)
        
        # Проверяем порядок через индексы
        idx_first = result.find("Первое")
        idx_second = result.find("Второе")
        idx_third = result.find("Третье")
        
        assert idx_first < idx_second < idx_third


class TestEdgeCases:
    """Тесты граничных случаев для всех функций"""

    def test_format_career_with_missing_keys(self):
        """Тест: форматирование с отсутствующими ключами"""
        parsed = {"ReplyText": "Ответ"}
        
        result = format_career_response(parsed, show_analysis=True)
        
        # Должно корректно обработать отсутствующие флаги
        assert "Ответ" in result

    def test_format_provd_with_none_values(self):
        """Тест: форматирование с None значениями"""
        parsed = {
            "ReplyText": "Текст",
            "Behavior": None,
            "Result": None
        }
        
        result = format_provd_peer(parsed, show_analysis=True)
        
        assert "Текст" in result

    def test_parse_reviewer_with_nested_structures(self):
        """Тест: парсинг рецензента с вложенными структурами"""
        response = json.dumps({
            "overall": "Анализ",
            "goodPoints": [
                "Простой пункт",
                {"nested": "Вложенная структура"}  # Некорректная вложенность
            ],
            "improvementPoints": []
        })
        
        result = parse_reviewer_career(response)
        
        # Должен обработать некорректную структуру
        assert result["overall"] == "Анализ"

    def test_extract_dialogue_with_missing_keys(self):
        """Тест: извлечение диалога с отсутствующими ключами"""
        entries = [
            {"role": "Руководитель"},  # Нет text
            {"text": "Нет роли"},  # Нет role
            {"role": "Максим", "text": "Нормальная запись"},
        ]
        
        result = extract_dialogue_career(entries)
        
        # Только нормальная запись должна быть включена
        assert "Нормальная запись" in result
        assert result.count("\n\n") == 0  # Только одна запись, нет разделителей


class TestCyrillicAndUnicode:
    """Тесты работы с кириллицей и Unicode"""

    def test_format_career_with_cyrillic(self):
        """Тест: форматирование с кириллицей"""
        parsed = {
            "ReplyText": "Отличный план карьерного роста!",
            "Aspirations": True
        }
        
        result = format_career_response(parsed, show_analysis=False)
        
        assert "Отличный план карьерного роста!" in result

    def test_format_provd_with_emoji(self):
        """Тест: форматирование с эмодзи"""
        parsed = {
            "ReplyText": "Хорошо! 👍 Договорились 🤝",
            "Agreement": True
        }
        
        result = format_provd_peer(parsed, show_analysis=False)
        
        assert "👍" in result
        assert "🤝" in result

    def test_extract_dialogue_with_mixed_languages(self):
        """Тест: извлечение диалога со смешанными языками"""
        entries = [
            {"role": "Руководитель", "text": "Hello, как дела? 你好"},
            {"role": "Максим", "text": "Хорошо, thanks! 谢谢"},
        ]
        
        result = extract_dialogue_career(entries)
        
        assert "Hello, как дела? 你好" in result
        assert "Хорошо, thanks! 谢谢" in result

