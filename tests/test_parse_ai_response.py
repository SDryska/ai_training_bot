"""
Тесты для парсинга AI ответов из всех кейсов.

Модули:
- app/cases/fb_peer/handler.py::parse_ai_response
- app/cases/fb_employee/handler.py::parse_ai_response
- app/cases/career_dialog/handler.py::parse_ai_response

Все три функции имеют одинаковую логику парсинга, но разные fallback поля.
"""

import pytest
import json

from app.cases.fb_peer.handler import parse_ai_response as parse_fb_peer
from app.cases.fb_employee.handler import parse_ai_response as parse_fb_employee
from app.cases.career_dialog.handler import parse_ai_response as parse_career_dialog


# Все три парсера для параметризованных тестов
ALL_PARSERS = [
    pytest.param(parse_fb_peer, id="fb_peer"),
    pytest.param(parse_fb_employee, id="fb_employee"),
    pytest.param(parse_career_dialog, id="career_dialog"),
]


class TestParseAIResponseValidJSON:
    """Тесты парсинга валидных JSON ответов"""

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_clean_json(self, parser):
        """Тест: чистый JSON ответ"""
        response = json.dumps({
            "ReplyText": "Это тестовый ответ",
            "Behavior": True,
            "Result": False
        })
        
        result = parser(response)
        
        assert result["ReplyText"] == "Это тестовый ответ"
        assert result["Behavior"] is True
        assert result["Result"] is False

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_text_before(self, parser):
        """Тест: JSON с текстом до него"""
        response = "Вот мой ответ: " + json.dumps({
            "ReplyText": "Основной текст",
            "Question": True
        })
        
        result = parser(response)
        
        assert result["ReplyText"] == "Основной текст"
        assert result["Question"] is True

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_text_after(self, parser):
        """Тест: JSON с текстом после него"""
        response = json.dumps({
            "ReplyText": "Ответ от AI",
            "Emotion": True
        }) + "\nДополнительный текст"
        
        result = parser(response)
        
        assert result["ReplyText"] == "Ответ от AI"
        assert result["Emotion"] is True

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_surrounded_by_text(self, parser):
        """Тест: JSON окружен текстом с обеих сторон"""
        response = "Префикс " + json.dumps({
            "ReplyText": "Центральный текст",
            "Agreement": False
        }) + " Суффикс"
        
        result = parser(response)
        
        assert result["ReplyText"] == "Центральный текст"
        assert result["Agreement"] is False

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_newlines(self, parser):
        """Тест: JSON с переносами строк"""
        response = """
        {
            "ReplyText": "Многострочный\nответ",
            "Behavior": true
        }
        """
        
        result = parser(response)
        
        assert "Многострочный" in result["ReplyText"]
        assert "\n" in result["ReplyText"]

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_cyrillic(self, parser):
        """Тест: JSON с кириллицей"""
        response = json.dumps({
            "ReplyText": "Привет! Это ответ на русском языке.",
            "Result": True
        }, ensure_ascii=False)
        
        result = parser(response)
        
        assert result["ReplyText"] == "Привет! Это ответ на русском языке."

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_special_characters(self, parser):
        """Тест: JSON со спецсимволами"""
        response = json.dumps({
            "ReplyText": "Текст с символами: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "Question": False
        })
        
        result = parser(response)
        
        assert "!@#$%^&*()" in result["ReplyText"]

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_emoji(self, parser):
        """Тест: JSON с эмодзи"""
        response = json.dumps({
            "ReplyText": "Отлично! 👍 Продолжайте в том же духе! 🎉",
            "Emotion": True
        }, ensure_ascii=False)
        
        result = parser(response)
        
        assert "👍" in result["ReplyText"]
        assert "🎉" in result["ReplyText"]

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_minimal_required_field(self, parser):
        """Тест: только обязательное поле ReplyText"""
        response = json.dumps({
            "ReplyText": "Минимальный ответ"
        })
        
        result = parser(response)
        
        assert result["ReplyText"] == "Минимальный ответ"

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_extra_fields(self, parser):
        """Тест: JSON с дополнительными полями"""
        response = json.dumps({
            "ReplyText": "Ответ",
            "ExtraField": "extra_value",
            "AnotherField": 123,
            "Behavior": True
        })
        
        result = parser(response)
        
        assert result["ReplyText"] == "Ответ"
        assert "ExtraField" in result  # Дополнительные поля сохраняются


class TestParseAIResponseInvalidJSON:
    """Тесты парсинга невалидных JSON ответов (fallback)"""

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_plain_text(self, parser):
        """Тест: обычный текст без JSON"""
        response = "Это просто текстовый ответ без JSON"
        
        result = parser(response)
        
        assert result["ReplyText"] == response
        # Все остальные поля должны быть False
        for key, value in result.items():
            if key != "ReplyText":
                assert value is False

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_malformed_json(self, parser):
        """Тест: некорректный JSON"""
        response = '{"ReplyText": "Незакрытый JSON'
        
        result = parser(response)
        
        assert result["ReplyText"] == response

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_without_reply_text(self, parser):
        """Тест: JSON без обязательного поля ReplyText"""
        response = json.dumps({
            "Behavior": True,
            "Result": False
        })
        
        result = parser(response)
        
        # Должен вернуть весь ответ как ReplyText (fallback)
        assert result["ReplyText"] == response

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_empty_string(self, parser):
        """Тест: пустая строка"""
        response = ""
        
        result = parser(response)
        
        assert result["ReplyText"] == ""
        for key, value in result.items():
            if key != "ReplyText":
                assert value is False

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_only_braces(self, parser):
        """Тест: только фигурные скобки"""
        response = "{}"
        
        result = parser(response)
        
        # Пустой JSON без ReplyText -> fallback
        assert result["ReplyText"] == "{}"

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_nested_json_structure(self, parser):
        """Тест: вложенная JSON структура"""
        response = json.dumps({
            "ReplyText": "Основной ответ",
            "Nested": {
                "Field1": "value1",
                "Field2": "value2"
            }
        })
        
        result = parser(response)
        
        assert result["ReplyText"] == "Основной ответ"
        # Вложенная структура должна сохраниться
        assert "Nested" in result

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_array(self, parser):
        """Тест: JSON массив вместо объекта"""
        response = json.dumps([
            {"ReplyText": "Первый"},
            {"ReplyText": "Второй"}
        ])
        
        result = parser(response)
        
        # Массив не имеет ReplyText -> fallback
        assert result["ReplyText"] == response

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_multiple_json_objects(self, parser):
        """Тест: несколько JSON объектов в ответе
        
        Парсер использует find('{') и rfind('}'), что берет от первой до ПОСЛЕДНЕЙ
        скобки. При двух JSON объектах это дает невалидный JSON → fallback.
        """
        response = json.dumps({"ReplyText": "Первый"}) + " " + json.dumps({"ReplyText": "Второй"})
        
        result = parser(response)
        
        # Невалидный JSON (два объекта) → fallback на весь текст
        assert result["ReplyText"] == response
        # Все остальные поля False
        for key, value in result.items():
            if key != "ReplyText":
                assert value is False

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_parse_json_with_null_values(self, parser):
        """Тест: JSON с null значениями"""
        response = json.dumps({
            "ReplyText": "Ответ",
            "Behavior": None,
            "Result": None
        })
        
        result = parser(response)
        
        assert result["ReplyText"] == "Ответ"
        assert result["Behavior"] is None
        assert result["Result"] is None


class TestParseFBPeerSpecific:
    """Специфичные тесты для FB Peer парсера"""

    def test_fb_peer_fallback_fields(self):
        """Тест: fallback поля для FB Peer"""
        result = parse_fb_peer("Plain text")
        
        assert result["ReplyText"] == "Plain text"
        assert result["Behavior"] is False
        assert result["Result"] is False
        assert result["Emotion"] is False
        assert result["Question"] is False
        assert result["Agreement"] is False

    def test_fb_peer_all_provd_fields(self):
        """Тест: все ПРОВД поля"""
        response = json.dumps({
            "ReplyText": "Полный ответ",
            "Behavior": True,
            "Result": True,
            "Emotion": True,
            "Question": True,
            "Agreement": True
        })
        
        result = parse_fb_peer(response)
        
        assert all(result[key] is True for key in ["Behavior", "Result", "Emotion", "Question", "Agreement"])


class TestParseFBEmployeeSpecific:
    """Специфичные тесты для FB Employee парсера"""

    def test_fb_employee_fallback_fields(self):
        """Тест: fallback поля для FB Employee"""
        result = parse_fb_employee("Plain text")
        
        assert result["ReplyText"] == "Plain text"
        assert result["Behavior"] is False
        assert result["Result"] is False
        assert result["Emotion"] is False
        assert result["Question"] is False
        assert result["Agreement"] is False


class TestParseCareerDialogSpecific:
    """Специфичные тесты для Career Dialog парсера"""

    def test_career_dialog_fallback_fields(self):
        """Тест: fallback поля для Career Dialog"""
        result = parse_career_dialog("Plain text")
        
        assert result["ReplyText"] == "Plain text"
        assert result["Aspirations"] is False
        assert result["Strengths"] is False
        assert result["Development"] is False
        assert result["Opportunities"] is False
        assert result["Plan"] is False

    def test_career_dialog_all_fields(self):
        """Тест: все карьерные поля"""
        response = json.dumps({
            "ReplyText": "Карьерный совет",
            "Aspirations": True,
            "Strengths": True,
            "Development": True,
            "Opportunities": True,
            "Plan": True
        })
        
        result = parse_career_dialog(response)
        
        assert all(result[key] is True for key in ["Aspirations", "Strengths", "Development", "Opportunities", "Plan"])


class TestRealWorldScenarios:
    """Тесты реальных сценариев от AI"""

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_scenario_typical_ai_response(self, parser):
        """Сценарий: типичный ответ от AI"""
        response = json.dumps({
            "ReplyText": "Спасибо за ваш вопрос. Давайте обсудим это подробнее.",
            "Question": True,
            "Emotion": True
        })
        
        result = parser(response)
        
        assert "Спасибо" in result["ReplyText"]
        assert result["Question"] is True

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_scenario_ai_response_with_markdown(self, parser):
        """Сценарий: AI возвращает markdown"""
        response = json.dumps({
            "ReplyText": "**Важно:** обратите внимание на *детали*.",
            "Behavior": True
        })
        
        result = parser(response)
        
        assert "**Важно:**" in result["ReplyText"]
        assert "*детали*" in result["ReplyText"]

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_scenario_ai_explains_json(self, parser):
        """Сценарий: AI объясняет что возвращает JSON"""
        response = 'Вот мой ответ в формате JSON:\n{"ReplyText": "Фактический ответ", "Result": true}'
        
        result = parser(response)
        
        assert result["ReplyText"] == "Фактический ответ"

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_scenario_ai_forgets_json_format(self, parser):
        """Сценарий: AI забывает вернуть JSON"""
        response = "Извините, вот просто текстовый ответ без JSON структуры."
        
        result = parser(response)
        
        # Должен gracefully вернуть текст как ReplyText
        assert result["ReplyText"] == response
        assert all(value is False for key, value in result.items() if key != "ReplyText")

    @pytest.mark.parametrize("parser", ALL_PARSERS)
    def test_scenario_long_reply_text(self, parser):
        """Сценарий: длинный ответ"""
        long_text = "Это очень длинный ответ. " * 100
        response = json.dumps({
            "ReplyText": long_text,
            "Agreement": True
        })
        
        result = parser(response)
        
        assert len(result["ReplyText"]) > 1000
        assert result["Agreement"] is True

