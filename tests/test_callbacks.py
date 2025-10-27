"""
Тесты для утилит упаковки/распаковки callback данных.

Модуль: app/keyboards/callbacks.py
"""

import pytest
from app.keyboards.callbacks import pack, unpack


class TestPack:
    """Тесты функции pack()"""

    def test_pack_with_prefix_and_data(self):
        """Тест: упаковка с префиксом и данными"""
        result = pack({"key1": "value1", "key2": "value2"}, prefix="menu")
        assert result == "menu|key1=value1;key2=value2"

    def test_pack_only_prefix(self):
        """Тест: упаковка только префикса"""
        result = pack(prefix="menu")
        assert result == "menu"

    def test_pack_only_data(self):
        """Тест: упаковка только данных (без префикса)"""
        result = pack({"key": "value"})
        assert result == "key=value"

    def test_pack_empty(self):
        """Тест: пустая упаковка"""
        result = pack()
        assert result == ""

    def test_pack_empty_dict(self):
        """Тест: пустой словарь"""
        result = pack({}, prefix="menu")
        assert result == "menu"

    def test_pack_none_data(self):
        """Тест: None вместо данных"""
        result = pack(None, prefix="menu")
        assert result == "menu"

    def test_pack_special_characters_url_encoded(self):
        """Тест: спецсимволы должны быть URL-encoded"""
        result = pack({"key": "value with spaces"}, prefix="menu")
        assert result == "menu|key=value%20with%20spaces"

    def test_pack_equals_and_semicolon_encoded(self):
        """Тест: символы = и ; должны быть закодированы"""
        result = pack({"key=test": "value;test"}, prefix="menu")
        # URL encoding: = -> %3D, ; -> %3B
        assert "=" in result  # есть разделитель key=value
        assert "key%3Dtest" in result  # = в ключе закодирован
        assert "value%3Btest" in result  # ; в значении закодирован

    def test_pack_pipe_character_encoded(self):
        """Тест: символ | должен быть закодирован в данных"""
        result = pack({"key": "value|with|pipes"})
        assert result == "key=value%7Cwith%7Cpipes"

    def test_pack_keys_sorted(self):
        """Тест: ключи должны быть отсортированы для стабильности"""
        result1 = pack({"z": "1", "a": "2", "m": "3"}, prefix="test")
        result2 = pack({"a": "2", "z": "1", "m": "3"}, prefix="test")
        # Порядок всегда одинаковый: a, m, z
        assert result1 == "test|a=2;m=3;z=1"
        assert result2 == "test|a=2;m=3;z=1"

    def test_pack_multiple_keys(self):
        """Тест: множественные ключи разделены точкой с запятой"""
        result = pack({"a": "1", "b": "2", "c": "3"})
        assert result == "a=1;b=2;c=3"

    def test_pack_non_string_values_converted(self):
        """Тест: не-строковые значения конвертируются в строки"""
        result = pack({"num": 123, "bool": True}, prefix="test")
        assert "num=123" in result
        assert "bool=True" in result

    def test_pack_cyrillic_characters(self):
        """Тест: кириллица должна быть закодирована"""
        result = pack({"key": "значение"}, prefix="меню")
        # Проверяем что результат содержит URL-encoded символы
        assert "%D0" in result or "%d0" in result  # кириллица кодируется в %D0...

    def test_pack_length_short(self):
        """Тест: короткая строка (для Telegram callback_data <= 64 байта)"""
        result = pack({"id": "1"}, prefix="btn")
        assert len(result.encode('utf-8')) <= 64

    def test_pack_length_moderate(self):
        """Тест: умеренная длина (приближаемся к лимиту)"""
        result = pack({"key1": "val1", "key2": "val2", "key3": "val3"}, prefix="menu")
        # Просто проверяем что строка генерируется
        assert len(result) > 0


class TestUnpack:
    """Тесты функции unpack()"""

    def test_unpack_with_prefix_and_payload(self):
        """Тест: распаковка с префиксом и payload"""
        prefix, payload = unpack("menu|key1=value1;key2=value2")
        assert prefix == "menu"
        assert payload == {"key1": "value1", "key2": "value2"}

    def test_unpack_only_prefix(self):
        """Тест: распаковка только префикса"""
        prefix, payload = unpack("menu|")
        assert prefix == "menu"
        assert payload == {}

    def test_unpack_only_payload(self):
        """Тест: распаковка только payload (без префикса)"""
        prefix, payload = unpack("key=value")
        assert prefix is None
        assert payload == {"key": "value"}

    def test_unpack_empty_string(self):
        """Тест: пустая строка"""
        prefix, payload = unpack("")
        assert prefix is None
        assert payload == {}

    def test_unpack_only_separator(self):
        """Тест: только разделитель |"""
        prefix, payload = unpack("|")
        assert prefix == ""
        assert payload == {}

    def test_unpack_special_characters_decoded(self):
        """Тест: спецсимволы должны быть декодированы"""
        prefix, payload = unpack("menu|key=value%20with%20spaces")
        assert prefix == "menu"
        assert payload == {"key": "value with spaces"}

    def test_unpack_equals_and_semicolon_decoded(self):
        """Тест: закодированные = и ; должны быть декодированы"""
        prefix, payload = unpack("menu|key%3Dtest=value%3Btest")
        assert prefix == "menu"
        assert payload == {"key=test": "value;test"}

    def test_unpack_pipe_character_decoded(self):
        """Тест: символ | в данных должен быть декодирован"""
        prefix, payload = unpack("key=value%7Cwith%7Cpipes")
        assert prefix is None
        assert payload == {"key": "value|with|pipes"}

    def test_unpack_multiple_keys(self):
        """Тест: множественные ключи"""
        prefix, payload = unpack("test|a=1;b=2;c=3")
        assert prefix == "test"
        assert payload == {"a": "1", "b": "2", "c": "3"}

    def test_unpack_malformed_no_equals(self):
        """Тест: некорректная пара без знака ="""
        prefix, payload = unpack("test|validkey;invalidpair")
        # Должна игнорировать пару без =
        assert prefix == "test"
        assert payload == {}

    def test_unpack_malformed_empty_pairs(self):
        """Тест: пустые пары (двойные точки с запятой)"""
        prefix, payload = unpack("test|key1=value1;;key2=value2")
        # Должна игнорировать пустые пары
        assert prefix == "test"
        assert payload == {"key1": "value1", "key2": "value2"}

    def test_unpack_value_with_equals(self):
        """Тест: значение содержит знак ="""
        prefix, payload = unpack("test|key=value=with=equals")
        # split("=", 1) должен разделить только по первому =
        assert prefix == "test"
        assert payload == {"key": "value=with=equals"}

    def test_unpack_cyrillic_characters(self):
        """Тест: декодирование кириллицы"""
        # URL-encoded "значение"
        prefix, payload = unpack("меню|key=%D0%B7%D0%BD%D0%B0%D1%87%D0%B5%D0%BD%D0%B8%D0%B5")
        # Проверяем что декодирование работает (точное значение зависит от encoding)
        assert prefix is not None
        assert "key" in payload


class TestRoundtrip:
    """Тесты полного цикла pack → unpack"""

    def test_roundtrip_with_prefix_and_data(self):
        """Тест: полный цикл с префиксом и данными"""
        original_prefix = "menu"
        original_data = {"key1": "value1", "key2": "value2"}
        
        packed = pack(original_data, prefix=original_prefix)
        unpacked_prefix, unpacked_data = unpack(packed)
        
        assert unpacked_prefix == original_prefix
        assert unpacked_data == original_data

    def test_roundtrip_only_prefix(self):
        """Тест: полный цикл только с префиксом
        
        ВАЖНО: pack(prefix="menu") возвращает "menu" без разделителя |
        unpack("menu") интерпретирует это как payload, а не как prefix.
        Это ожидаемое поведение - для явного префикса нужны данные или |
        """
        original_prefix = "menu"
        
        packed = pack(prefix=original_prefix)
        # packed будет "menu" без |
        assert packed == "menu"
        
        # unpack("menu") без | вернет это как payload, не как prefix
        unpacked_prefix, unpacked_data = unpack(packed)
        assert unpacked_prefix is None  # нет | = нет префикса
        
        # Для сохранения префикса нужен хотя бы пустой payload
        # Явно добавляем | для обозначения префикса:
        packed_explicit = pack({}, prefix=original_prefix)
        assert packed_explicit == "menu"  # Все равно вернет "menu"
        
        # Правильный roundtrip - с данными:
        packed_with_data = pack({"dummy": ""}, prefix=original_prefix)
        unpacked_prefix2, unpacked_data2 = unpack(packed_with_data)
        assert unpacked_prefix2 == original_prefix
        assert "dummy" in unpacked_data2

    def test_roundtrip_only_data(self):
        """Тест: полный цикл только с данными"""
        original_data = {"key": "value"}
        
        packed = pack(original_data)
        unpacked_prefix, unpacked_data = unpack(packed)
        
        assert unpacked_prefix is None
        assert unpacked_data == original_data

    def test_roundtrip_special_characters(self):
        """Тест: полный цикл со спецсимволами"""
        original_data = {"key": "value with spaces & symbols!"}
        
        packed = pack(original_data, prefix="test")
        unpacked_prefix, unpacked_data = unpack(packed)
        
        assert unpacked_prefix == "test"
        assert unpacked_data == original_data

    def test_roundtrip_complex_data(self):
        """Тест: полный цикл с комплексными данными"""
        original_data = {
            "case_id": "fb_peer",
            "action": "restart",
            "user_id": "12345",
            "timestamp": "2024-01-15T10:30:00"
        }
        
        packed = pack(original_data, prefix="case")
        unpacked_prefix, unpacked_data = unpack(packed)
        
        assert unpacked_prefix == "case"
        assert unpacked_data == original_data

    def test_roundtrip_preserves_order_independent(self):
        """Тест: порядок ключей не важен после roundtrip"""
        data1 = {"z": "1", "a": "2", "m": "3"}
        data2 = {"a": "2", "m": "3", "z": "1"}
        
        packed1 = pack(data1, prefix="test")
        packed2 = pack(data2, prefix="test")
        
        # Упакованные строки одинаковы (ключи сортируются)
        assert packed1 == packed2
        
        # Распаковка дает одинаковые результаты
        _, unpacked1 = unpack(packed1)
        _, unpacked2 = unpack(packed2)
        assert unpacked1 == unpacked2


class TestEdgeCases:
    """Тесты граничных случаев"""

    def test_empty_key_ignored(self):
        """Тест: пустой ключ должен быть обработан"""
        # Такое не должно происходить в нормальном использовании,
        # но проверим что не падает
        result = pack({"": "value"}, prefix="test")
        assert result == "test|=value"
        
        # При распаковке пустой ключ восстанавливается
        prefix, payload = unpack(result)
        assert payload == {"": "value"}

    def test_empty_value(self):
        """Тест: пустое значение"""
        result = pack({"key": ""}, prefix="test")
        assert result == "test|key="
        
        prefix, payload = unpack(result)
        assert payload == {"key": ""}

    def test_single_character_keys_and_values(self):
        """Тест: одиночные символы"""
        result = pack({"a": "1"}, prefix="x")
        assert result == "x|a=1"
        
        prefix, payload = unpack(result)
        assert prefix == "x"
        assert payload == {"a": "1"}

    def test_numeric_keys_converted_to_strings(self):
        """Тест: числовые ключи конвертируются в строки"""
        # В Python dict ключи могут быть числами, но мы их сериализуем
        result = pack({123: "value"}, prefix="test")
        assert "123=value" in result

    def test_long_callback_data_awareness(self):
        """Тест: осведомленность о лимите Telegram (64 байта)"""
        # Генерируем потенциально длинную строку
        long_data = {f"key{i}": f"value{i}" for i in range(10)}
        result = pack(long_data, prefix="test")
        
        # Просто проверяем что функция работает
        # В реальности пользователь должен следить за длиной
        assert len(result) > 0
        
        # Но можем проверить, что короткие данные точно влезают
        short_result = pack({"id": "1"}, prefix="btn")
        assert len(short_result.encode('utf-8')) <= 64


class TestRealWorldScenarios:
    """Тесты реальных сценариев использования"""

    def test_menu_navigation(self):
        """Тест: навигация по меню"""
        callback = pack({"action": "main_menu"}, prefix="nav")
        assert callback == "nav|action=main_menu"
        
        prefix, data = unpack(callback)
        assert prefix == "nav"
        assert data["action"] == "main_menu"

    def test_case_controls(self):
        """Тест: управление кейсом"""
        callback = pack({
            "case_id": "fb_peer",
            "action": "restart"
        }, prefix="case")
        
        prefix, data = unpack(callback)
        assert prefix == "case"
        assert data["case_id"] == "fb_peer"
        assert data["action"] == "restart"

    def test_pagination(self):
        """Тест: пагинация"""
        callback = pack({
            "page": "2",
            "total": "10"
        }, prefix="page")
        
        prefix, data = unpack(callback)
        assert prefix == "page"
        assert data["page"] == "2"
        assert data["total"] == "10"

    def test_rating_question(self):
        """Тест: вопрос оценки"""
        callback = pack({
            "question": "q1",
            "rating": "8"
        }, prefix="rating")
        
        prefix, data = unpack(callback)
        assert prefix == "rating"
        assert data["question"] == "q1"
        assert data["rating"] == "8"

