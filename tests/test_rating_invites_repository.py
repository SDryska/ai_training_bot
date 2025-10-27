"""
Тесты для репозитория приглашений на рейтинг.

Тестируемый модуль:
- app/repositories/rating_invites.py

Тестируемые компоненты:
- acquire_rating_invite_lock функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories.rating_invites import acquire_rating_invite_lock


class TestAcquireRatingInviteLock:
    """Тесты для функции acquire_rating_invite_lock"""

    @pytest.mark.asyncio
    async def test_acquire_rating_invite_lock_success(self):
        """Тест: успешное получение блокировки (первый раз)"""
        with patch("app.repositories.rating_invites._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await acquire_rating_invite_lock(12345)
            
            assert result is True
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_rating_invite_lock_duplicate(self):
        """Тест: попытка получить блокировку второй раз (duplicate key)"""
        with patch("app.repositories.rating_invites._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("Duplicate key"))
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await acquire_rating_invite_lock(12345)
            
            assert result is False
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_rating_invite_lock_no_connection(self):
        """Тест: получение блокировки без подключения"""
        with patch("app.repositories.rating_invites._connect", return_value=None):
            result = await acquire_rating_invite_lock(12345)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_acquire_rating_invite_lock_different_users(self):
        """Тест: получение блокировок для разных пользователей"""
        with patch("app.repositories.rating_invites._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result1 = await acquire_rating_invite_lock(12345)
            result2 = await acquire_rating_invite_lock(67890)
            
            assert result1 is True
            assert result2 is True
            assert mock_conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_acquire_rating_invite_lock_execution_error(self):
        """Тест: обработка ошибки выполнения SQL"""
        with patch("app.repositories.rating_invites._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("SQL error"))
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await acquire_rating_invite_lock(12345)
            
            assert result is False
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_rating_invite_lock_success_connection_lifecycle(self):
        """Тест: успешное получение блокировки с проверкой полного цикла подключения"""
        with patch("app.repositories.rating_invites._connect") as mock_connect, \
             patch("app.repositories.rating_invites.normalize_db_url") as mock_normalize:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            mock_normalize.return_value = "postgresql://test"
            
            result = await acquire_rating_invite_lock(12345)
            
            assert result is True
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

