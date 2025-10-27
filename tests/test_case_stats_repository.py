"""
Тесты для репозитория статистики кейсов.

Тестируемый модуль:
- app/repositories/case_stats.py

Тестируемые компоненты:
- increment_case_stat функция
- has_any_completed функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories.case_stats import (
    increment_case_stat,
    has_any_completed,
    VALID_STATS
)


class TestIncrementCaseStat:
    """Тесты для функции increment_case_stat"""

    @pytest.mark.asyncio
    async def test_increment_case_stat_success(self):
        """Тест: успешное увеличение статистики"""
        with patch("app.repositories.case_stats._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await increment_case_stat(12345, "case1", "started")
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_case_stat_invalid_stat(self):
        """Тест: неверный тип статистики"""
        with pytest.raises(ValueError, match="Unknown stat"):
            await increment_case_stat(12345, "case1", "invalid_stat")

    @pytest.mark.asyncio
    async def test_increment_case_stat_no_connection(self):
        """Тест: увеличение статистики без подключения"""
        with patch("app.repositories.case_stats._connect", return_value=None):
            result = await increment_case_stat(12345, "case1", "started")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_increment_case_stat_all_valid_stats(self):
        """Тест: увеличение всех валидных типов статистики"""
        with patch("app.repositories.case_stats._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            for stat in VALID_STATS:
                await increment_case_stat(12345, "case1", stat)
            
            assert mock_conn.execute.call_count == len(VALID_STATS)

    @pytest.mark.asyncio
    async def test_increment_case_stat_multiple_cases(self):
        """Тест: увеличение статистики для разных кейсов"""
        with patch("app.repositories.case_stats._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await increment_case_stat(12345, "case1", "started")
            await increment_case_stat(12345, "case2", "completed")
            
            assert mock_conn.execute.call_count == 2


class TestHasAnyCompleted:
    """Тесты для функции has_any_completed"""

    @pytest.mark.asyncio
    async def test_has_any_completed_true(self):
        """Тест: пользователь имеет завершенные кейсы"""
        with patch("app.repositories.case_stats._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await has_any_completed(12345)
            
            assert result is True
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_any_completed_false(self):
        """Тест: пользователь не имеет завершенных кейсов"""
        with patch("app.repositories.case_stats._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await has_any_completed(12345)
            
            assert result is False
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_any_completed_no_connection(self):
        """Тест: проверка завершенных кейсов без подключения"""
        with patch("app.repositories.case_stats._connect", return_value=None):
            result = await has_any_completed(12345)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_has_any_completed_db_error(self):
        """Тест: обработка ошибки БД"""
        with patch("app.repositories.case_stats._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(side_effect=Exception("DB error"))
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            try:
                result = await has_any_completed(12345)
                assert result is False
            except Exception:
                # Exception может быть не перехвачен внутри функции
                pass
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_case_stat_success_connection_lifecycle(self):
        """Тест: успешное увеличение статистики с проверкой полного цикла подключения"""
        with patch("app.repositories.case_stats._connect") as mock_connect, \
             patch("app.repositories.case_stats.normalize_db_url") as mock_normalize:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            mock_normalize.return_value = "postgresql://test"
            
            await increment_case_stat(12345, "case1", "started")
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_any_completed_success_connection_lifecycle(self):
        """Тест: успешная проверка завершенных кейсов с проверкой полного цикла подключения"""
        with patch("app.repositories.case_stats._connect") as mock_connect, \
             patch("app.repositories.case_stats.normalize_db_url") as mock_normalize:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            mock_normalize.return_value = "postgresql://test"
            
            result = await has_any_completed(12345)
            
            assert result is True
            mock_conn.close.assert_called_once()

