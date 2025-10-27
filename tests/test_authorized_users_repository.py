"""
Тесты для репозитория авторизованных пользователей.

Модуль: app/repositories/authorized_users.py

Используем моки для asyncpg, так как не хотим зависеть от реальной БД в тестах.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from app.repositories.authorized_users import (
    get_role_by_user_id,
    upsert_authorized_user,
    get_authorized_user,
    _connect
)


class TestConnect:
    """Тесты функции подключения к БД
    
    Примечание: asyncpg импортируется локально внутри _connect(),
    поэтому тестируем через моки _connect() в других тестах.
    """

    @pytest.mark.asyncio
    async def test_connect_without_database_url(self):
        """Тест: подключение без DATABASE_URL возвращает None"""
        with patch('app.repositories.authorized_users.Settings') as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            
            result = await _connect()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_connect_with_empty_database_url(self):
        """Тест: подключение с пустым DATABASE_URL"""
        with patch('app.repositories.authorized_users.Settings') as mock_settings:
            mock_settings.return_value.DATABASE_URL = ""
            
            result = await _connect()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_connect_calls_normalize_db_url(self):
        """Тест: подключение вызывает normalize_db_url"""
        with patch('app.repositories.authorized_users.Settings') as mock_settings, \
             patch('app.repositories.authorized_users.normalize_db_url') as mock_normalize:
            
            mock_settings.return_value.DATABASE_URL = "postgres://test"
            mock_normalize.return_value = "postgresql://test"
            
            # Мокируем динамический импорт asyncpg
            mock_asyncpg = MagicMock()
            mock_asyncpg.connect = AsyncMock(side_effect=Exception("Connection error"))
            
            with patch('builtins.__import__', return_value=mock_asyncpg):
                try:
                    result = await _connect()
                except:
                    pass
            
            # Проверяем, что normalize_db_url был вызван с правильным URL
            mock_normalize.assert_called_once_with("postgres://test")


class TestGetRoleByUserId:
    """Тесты получения роли пользователя"""

    @pytest.mark.asyncio
    async def test_get_role_user_exists(self):
        """Тест: получение роли существующего пользователя"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            # Создаем мок соединения
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value="admin")
            mock_connect.return_value = mock_conn
            
            result = await get_role_by_user_id(123)
            
            assert result == "admin"
            mock_conn.fetchval.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_role_user_not_exists(self):
        """Тест: получение роли несуществующего пользователя"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=None)
            mock_connect.return_value = mock_conn
            
            result = await get_role_by_user_id(999)
            
            assert result is None
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_role_no_database(self):
        """Тест: получение роли когда БД недоступна"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_connect.return_value = None
            
            result = await get_role_by_user_id(123)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_role_connection_closes_on_error(self):
        """Тест: соединение закрывается даже при ошибке"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(side_effect=Exception("DB error"))
            mock_connect.return_value = mock_conn
            
            with pytest.raises(Exception):
                await get_role_by_user_id(123)
            
            # Соединение должно закрыться даже при ошибке (finally block)
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_role_different_user_ids(self):
        """Тест: разные user_id передаются в запрос"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value="user")
            mock_connect.return_value = mock_conn
            
            await get_role_by_user_id(12345)
            
            # Проверяем что правильный user_id передан в запрос
            call_args = mock_conn.fetchval.call_args
            assert 12345 in call_args[0]  # user_id в позиционных аргументах


class TestUpsertAuthorizedUser:
    """Тесты добавления/обновления пользователя"""

    @pytest.mark.asyncio
    async def test_upsert_new_user(self):
        """Тест: добавление нового пользователя"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await upsert_authorized_user(123, "admin")
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_existing_user(self):
        """Тест: обновление существующего пользователя"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_connect.return_value = mock_conn
            
            # Обновляем роль с user на admin
            await upsert_authorized_user(123, "admin")
            
            mock_conn.execute.assert_called_once()
            # Проверяем что в запросе есть ON CONFLICT
            call_args = mock_conn.execute.call_args
            query = call_args[0][0]
            assert "on conflict" in query.lower()

    @pytest.mark.asyncio
    async def test_upsert_no_database(self):
        """Тест: upsert когда БД недоступна"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_connect.return_value = None
            
            result = await upsert_authorized_user(123, "user")
            
            # Должен вернуть None без ошибки
            assert result is None

    @pytest.mark.asyncio
    async def test_upsert_connection_closes_on_error(self):
        """Тест: соединение закрывается при ошибке"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("DB error"))
            mock_connect.return_value = mock_conn
            
            with pytest.raises(Exception):
                await upsert_authorized_user(123, "admin")
            
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_with_different_roles(self):
        """Тест: upsert с разными ролями"""
        roles = ["user", "admin", "moderator"]
        
        for role in roles:
            with patch('app.repositories.authorized_users._connect') as mock_connect:
                mock_conn = AsyncMock()
                mock_conn.execute = AsyncMock()
                mock_connect.return_value = mock_conn
                
                await upsert_authorized_user(123, role)
                
                # Проверяем что роль передана в запрос
                call_args = mock_conn.execute.call_args
                assert role in call_args[0]  # роль в позиционных аргументах


class TestGetAuthorizedUser:
    """Тесты получения полной информации о пользователе"""

    @pytest.mark.asyncio
    async def test_get_user_exists(self):
        """Тест: получение существующего пользователя"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            
            # Создаем мок строки из БД
            mock_row = {
                "user_id": 123,
                "role": "admin",
                "created_at": datetime(2024, 1, 15, 10, 30, 0)
            }
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_connect.return_value = mock_conn
            
            result = await get_authorized_user(123)
            
            assert result is not None
            assert result["user_id"] == 123
            assert result["role"] == "admin"
            assert result["created_at"] == datetime(2024, 1, 15, 10, 30, 0)
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_not_exists(self):
        """Тест: получение несуществующего пользователя"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_connect.return_value = mock_conn
            
            result = await get_authorized_user(999)
            
            assert result is None
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_no_database(self):
        """Тест: получение пользователя когда БД недоступна"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_connect.return_value = None
            
            result = await get_authorized_user(123)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_user_connection_closes_on_error(self):
        """Тест: соединение закрывается при ошибке"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(side_effect=Exception("DB error"))
            mock_connect.return_value = mock_conn
            
            with pytest.raises(Exception):
                await get_authorized_user(123)
            
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_returns_all_fields(self):
        """Тест: возвращает все поля пользователя"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            
            mock_row = {
                "user_id": 456,
                "role": "user",
                "created_at": datetime(2024, 3, 20, 15, 45, 30)
            }
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_connect.return_value = mock_conn
            
            result = await get_authorized_user(456)
            
            # Проверяем что все поля присутствуют
            assert "user_id" in result
            assert "role" in result
            assert "created_at" in result
            assert len(result) == 3


class TestRealWorldScenarios:
    """Тесты реальных сценариев использования"""

    @pytest.mark.asyncio
    async def test_scenario_new_user_registration(self):
        """Сценарий: регистрация нового пользователя"""
        user_id = 123
        
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            
            # Сначала пользователь не существует
            mock_conn.fetchval = AsyncMock(return_value=None)
            mock_connect.return_value = mock_conn
            
            role = await get_role_by_user_id(user_id)
            assert role is None
            
            # Добавляем пользователя
            mock_conn.execute = AsyncMock()
            await upsert_authorized_user(user_id, "user")
            
            # Теперь пользователь существует
            mock_conn.fetchval = AsyncMock(return_value="user")
            role = await get_role_by_user_id(user_id)
            assert role == "user"

    @pytest.mark.asyncio
    async def test_scenario_user_role_upgrade(self):
        """Сценарий: повышение роли пользователя"""
        user_id = 456
        
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            # Пользователь изначально user
            mock_conn.fetchval = AsyncMock(return_value="user")
            role = await get_role_by_user_id(user_id)
            assert role == "user"
            
            # Повышаем до admin
            mock_conn.execute = AsyncMock()
            await upsert_authorized_user(user_id, "admin")
            
            # Проверяем новую роль
            mock_conn.fetchval = AsyncMock(return_value="admin")
            role = await get_role_by_user_id(user_id)
            assert role == "admin"

    @pytest.mark.asyncio
    async def test_scenario_check_user_details(self):
        """Сценарий: проверка полной информации о пользователе"""
        user_id = 789
        
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            
            mock_row = {
                "user_id": user_id,
                "role": "admin",
                "created_at": datetime(2024, 1, 1, 0, 0, 0)
            }
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_connect.return_value = mock_conn
            
            user = await get_authorized_user(user_id)
            
            assert user is not None
            assert user["user_id"] == user_id
            assert user["role"] == "admin"
            assert isinstance(user["created_at"], datetime)

    @pytest.mark.asyncio
    async def test_scenario_database_unavailable_graceful_degradation(self):
        """Сценарий: graceful degradation при недоступной БД"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_connect.return_value = None
            
            # Все функции должны работать без ошибок
            role = await get_role_by_user_id(123)
            assert role is None
            
            result = await upsert_authorized_user(123, "user")
            assert result is None
            
            user = await get_authorized_user(123)
            assert user is None

    @pytest.mark.asyncio
    async def test_scenario_multiple_users(self):
        """Сценарий: работа с несколькими пользователями"""
        users = [
            (100, "user"),
            (200, "admin"),
            (300, "user"),
        ]
        
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            # Добавляем всех пользователей
            for user_id, role in users:
                mock_conn.execute = AsyncMock()
                await upsert_authorized_user(user_id, role)
            
            # Проверяем роли
            for user_id, expected_role in users:
                mock_conn.fetchval = AsyncMock(return_value=expected_role)
                role = await get_role_by_user_id(user_id)
                assert role == expected_role


class TestErrorHandling:
    """Тесты обработки ошибок"""

    @pytest.mark.asyncio
    async def test_connection_timeout_error(self):
        """Тест: таймаут подключения"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_connect.side_effect = TimeoutError("Connection timeout")
            
            with pytest.raises(TimeoutError):
                await get_role_by_user_id(123)

    @pytest.mark.asyncio
    async def test_database_query_error(self):
        """Тест: ошибка выполнения запроса"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(side_effect=Exception("Query error"))
            mock_connect.return_value = mock_conn
            
            with pytest.raises(Exception):
                await get_role_by_user_id(123)

    @pytest.mark.asyncio
    async def test_connection_closes_even_on_error(self):
        """Тест: соединение всегда закрывается (finally block)"""
        with patch('app.repositories.authorized_users._connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(side_effect=Exception("Error"))
            mock_connect.return_value = mock_conn
            
            try:
                await get_role_by_user_id(123)
            except Exception:
                pass
            
            # Соединение должно закрыться
            mock_conn.close.assert_called_once()

