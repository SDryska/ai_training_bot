"""
Тесты для утилит статистики кейсов.

Тестируемый модуль:
- app/utils/case_stats.py

Тестируемые компоненты:
- mark_case_started функция
- mark_case_completed функция
- mark_case_out_of_moves функция
- mark_case_auto_finished функция
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.utils.case_stats import (
    mark_case_started,
    mark_case_completed,
    mark_case_out_of_moves,
    mark_case_auto_finished,
)


class TestMarkCaseStarted:
    """Тесты для функции mark_case_started"""

    @pytest.mark.asyncio
    async def test_mark_case_started_calls_increment(self):
        """Тест: вызов increment_case_stat с правильными параметрами"""
        user_id = 12345
        case_id = "test_case"
        
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            await mark_case_started(user_id, case_id)
            
            mock_increment.assert_called_once_with(user_id, case_id, "started")

    @pytest.mark.asyncio
    async def test_mark_case_started_with_different_ids(self):
        """Тест: вызов с разными ID"""
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            await mark_case_started(111, "case1")
            await mark_case_started(222, "case2")
            
            assert mock_increment.call_count == 2
            assert mock_increment.call_args_list[0][0] == (111, "case1", "started")
            assert mock_increment.call_args_list[1][0] == (222, "case2", "started")


class TestMarkCaseCompleted:
    """Тесты для функции mark_case_completed"""

    @pytest.mark.asyncio
    async def test_mark_case_completed_calls_increment(self):
        """Тест: вызов increment_case_stat с правильными параметрами"""
        user_id = 12345
        case_id = "test_case"
        
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            await mark_case_completed(user_id, case_id)
            
            mock_increment.assert_called_once_with(user_id, case_id, "completed")

    @pytest.mark.asyncio
    async def test_mark_case_completed_with_long_case_id(self):
        """Тест: вызов с длинным case_id"""
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            long_case_id = "very_long_case_id_" * 10
            await mark_case_completed(12345, long_case_id)
            
            mock_increment.assert_called_once_with(12345, long_case_id, "completed")


class TestMarkCaseOutOfMoves:
    """Тесты для функции mark_case_out_of_moves"""

    @pytest.mark.asyncio
    async def test_mark_case_out_of_moves_calls_increment(self):
        """Тест: вызов increment_case_stat с правильными параметрами"""
        user_id = 12345
        case_id = "test_case"
        
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            await mark_case_out_of_moves(user_id, case_id)
            
            mock_increment.assert_called_once_with(user_id, case_id, "out_of_moves")

    @pytest.mark.asyncio
    async def test_mark_case_out_of_moves_exception_handling(self):
        """Тест: обработка исключений"""
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock, side_effect=Exception("DB error")):
            # Функция должна пробросить исключение
            with pytest.raises(Exception):
                await mark_case_out_of_moves(12345, "test_case")


class TestMarkCaseAutoFinished:
    """Тесты для функции mark_case_auto_finished"""

    @pytest.mark.asyncio
    async def test_mark_case_auto_finished_calls_increment(self):
        """Тест: вызов increment_case_stat с правильными параметрами"""
        user_id = 12345
        case_id = "test_case"
        
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            await mark_case_auto_finished(user_id, case_id)
            
            mock_increment.assert_called_once_with(user_id, case_id, "auto_finished")

    @pytest.mark.asyncio
    async def test_mark_case_auto_finished_multiple_calls(self):
        """Тест: множественные вызовы"""
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            await mark_case_auto_finished(1, "case1")
            await mark_case_auto_finished(2, "case2")
            await mark_case_auto_finished(3, "case3")
            
            assert mock_increment.call_count == 3


class TestAllMarkFunctions:
    """Тесты для проверки всех функций вместе"""

    @pytest.mark.asyncio
    async def test_all_functions_use_same_repository(self):
        """Тест: все функции используют одинаковый репозиторий"""
        user_id = 12345
        case_id = "test_case"
        
        with patch("app.utils.case_stats.increment_case_stat", new_callable=AsyncMock) as mock_increment:
            await mark_case_started(user_id, case_id)
            await mark_case_completed(user_id, case_id)
            await mark_case_out_of_moves(user_id, case_id)
            await mark_case_auto_finished(user_id, case_id)
            
            assert mock_increment.call_count == 4
            # Проверяем, что каждая функция использует правильный статус
            calls = [call[0][2] for call in mock_increment.call_args_list]
            assert calls == ["started", "completed", "out_of_moves", "auto_finished"]

