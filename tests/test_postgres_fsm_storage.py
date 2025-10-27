"""
Тесты для PostgreSQL FSM Storage.

Тестируемый модуль:
- app/storage/postgres_fsm_storage.py

Тестируемые компоненты:
- PostgresFSMStorage класс
- _normalize_db_url функция
- Методы: __init__, _connect, _make_key, set_state, get_state, set_data, get_data, close
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.fsm.storage.base import StorageKey

from app.storage.postgres_fsm_storage import (
    PostgresFSMStorage,
    _normalize_db_url,
)


def create_storage_key(bot_id: int = 123, chat_id: int = 456, user_id: int = 789) -> StorageKey:
    """Создает StorageKey для тестов"""
    return StorageKey(
        bot_id=bot_id,
        chat_id=chat_id,
        user_id=user_id,
    )


class TestNormalizeDbUrl:
    """Тесты для функции _normalize_db_url"""

    def test_normalize_db_url_with_asyncpg(self):
        """Тест: конвертация sqlalchemy-style URL в asyncpg URL"""
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = _normalize_db_url(url)
        assert result == "postgresql://user:pass@host:5432/db"

    def test_normalize_db_url_without_asyncpg(self):
        """Тест: URL без +asyncpg остается без изменений"""
        url = "postgresql://user:pass@host:5432/db"
        result = _normalize_db_url(url)
        assert result == url

    def test_normalize_db_url_none(self):
        """Тест: None возвращается как есть"""
        result = _normalize_db_url(None)
        assert result is None

    def test_normalize_db_url_empty_string(self):
        """Тест: пустая строка возвращается как есть"""
        result = _normalize_db_url("")
        assert result == ""


class TestPostgresFSMStorageInit:
    """Тесты для __init__ метода"""

    def test_init_with_url(self):
        """Тест: инициализация с явным URL"""
        storage = PostgresFSMStorage("postgresql://user:pass@host:5432/db")
        assert storage.database_url == "postgresql://user:pass@host:5432/db"

    def test_init_with_none(self):
        """Тест: инициализация без URL (берется из Settings)"""
        with patch("app.storage.postgres_fsm_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = "postgresql://localhost/test"
            storage = PostgresFSMStorage()
            assert storage.database_url == "postgresql://localhost/test"

    def test_init_normalizes_url(self):
        """Тест: URL нормализуется при инициализации"""
        storage = PostgresFSMStorage("postgresql+asyncpg://user:pass@host:5432/db")
        assert storage.database_url == "postgresql://user:pass@host:5432/db"


class TestPostgresFSMStorageConnect:
    """Тесты для метода _connect"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Тест: успешное подключение к БД"""
        storage = PostgresFSMStorage("postgresql://user:pass@host:5432/db")
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await storage._connect()
            
            assert result == mock_conn
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_no_database_url(self):
        """Тест: подключение без DATABASE_URL"""
        with patch("app.storage.postgres_fsm_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            storage = PostgresFSMStorage(None)
            
            result = await storage._connect()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Тест: обработка исключения при подключении"""
        storage = PostgresFSMStorage("postgresql://user:pass@host:5432/db")
        
        with patch("asyncpg.connect", side_effect=Exception("Connection error")):
            result = await storage._connect()
            
            assert result is None


class TestPostgresFSMStorageMakeKey:
    """Тесты для метода _make_key"""

    def test_make_key_all_parts(self):
        """Тест: создание ключа со всеми частями"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key(bot_id=123, chat_id=456, user_id=789)
        
        result = storage._make_key(key)
        
        assert result == "123:456:789"

    def test_make_key_without_bot_id(self):
        """Тест: создание ключа без bot_id"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key(bot_id=None, chat_id=456, user_id=789)
        
        result = storage._make_key(key)
        
        assert result == "456:789"

    def test_make_key_only_user_id(self):
        """Тест: создание ключа только с user_id"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key(bot_id=None, chat_id=None, user_id=789)
        
        result = storage._make_key(key)
        
        assert result == "789"


class TestPostgresFSMStorageSetState:
    """Тесты для метода set_state"""

    @pytest.mark.asyncio
    async def test_set_state_success(self):
        """Тест: успешное сохранение состояния"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        state = MagicMock()
        state.state = "TestState"
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await storage.set_state(key, state)
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_state_clear(self):
        """Тест: очистка состояния (state=None)"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await storage.set_state(key, None)
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_state_no_connection(self):
        """Тест: сохранение состояния без подключения"""
        storage = PostgresFSMStorage(None)
        key = create_storage_key()
        state = MagicMock()
        state.state = "TestState"
        
        await storage.set_state(key, state)
        
        # Не должно быть исключений

    @pytest.mark.asyncio
    async def test_set_state_exception(self):
        """Тест: обработка исключения при сохранении"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        state = MagicMock()
        state.state = "TestState"
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("DB error"))
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await storage.set_state(key, state)
            
            mock_conn.close.assert_called_once()


class TestPostgresFSMStorageGetState:
    """Тесты для метода get_state"""

    @pytest.mark.asyncio
    async def test_get_state_success(self):
        """Тест: успешное получение состояния"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = MagicMock(return_value="TestState")
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await storage.get_state(key)
            
            assert result == "TestState"
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_not_found(self):
        """Тест: состояние не найдено"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await storage.get_state(key)
            
            assert result is None
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state_no_connection(self):
        """Тест: получение состояния без подключения"""
        with patch("app.storage.postgres_fsm_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            storage = PostgresFSMStorage(None)
            key = create_storage_key()
            
            result = await storage.get_state(key)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_state_exception(self):
        """Тест: обработка исключения при получении"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(side_effect=Exception("DB error"))
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await storage.get_state(key)
            
            assert result is None
            mock_conn.close.assert_called_once()


class TestPostgresFSMStorageSetData:
    """Тесты для метода set_data"""

    @pytest.mark.asyncio
    async def test_set_data_success(self):
        """Тест: успешное сохранение данных"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        data = {"turn_count": 5, "test": "value"}
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await storage.set_data(key, data)
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_data_with_set(self):
        """Тест: сохранение данных со set (конвертация в list)"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        data = {"total_provd_achieved": {"Behavior", "Result"}}
        
        with patch("asyncpg.connect") as mock_connect, \
             patch("json.dumps") as mock_dumps:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await storage.set_data(key, data)
            
            # Проверяем, что set был конвертирован в list
            call_args = mock_dumps.call_args[0][0]
            assert isinstance(call_args["total_provd_achieved"], list)
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_data_no_connection(self):
        """Тест: сохранение данных без подключения"""
        storage = PostgresFSMStorage(None)
        key = create_storage_key()
        data = {"test": "value"}
        
        await storage.set_data(key, data)
        
        # Не должно быть исключений

    @pytest.mark.asyncio
    async def test_set_data_exception(self):
        """Тест: обработка исключения при сохранении"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        data = {"test": "value"}
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("DB error"))
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await storage.set_data(key, data)
            
            mock_conn.close.assert_called_once()


class TestPostgresFSMStorageGetData:
    """Тесты для метода get_data"""

    @pytest.mark.asyncio
    async def test_get_data_success(self):
        """Тест: успешное получение данных"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect, \
             patch("json.loads") as mock_loads:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = MagicMock(return_value='{"test": "value"}')
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            mock_loads.return_value = {"test": "value"}
            
            result = await storage.get_data(key)
            
            assert result == {"test": "value"}
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_not_found(self):
        """Тест: данные не найдены"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await storage.get_data(key)
            
            assert result == {}
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_with_provd_list(self):
        """Тест: восстановление set из list для total_provd_achieved"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect, \
             patch("json.loads") as mock_loads:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = MagicMock(return_value='{"total_provd_achieved": ["Behavior"]}')
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            mock_loads.return_value = {"total_provd_achieved": ["Behavior"]}
            
            result = await storage.get_data(key)
            
            assert isinstance(result["total_provd_achieved"], set)
            assert "Behavior" in result["total_provd_achieved"]
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_no_connection(self):
        """Тест: получение данных без подключения"""
        with patch("app.storage.postgres_fsm_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            storage = PostgresFSMStorage(None)
            key = create_storage_key()
            
            result = await storage.get_data(key)
            
            assert result == {}

    @pytest.mark.asyncio
    async def test_get_data_exception(self):
        """Тест: обработка исключения при получении"""
        storage = PostgresFSMStorage("postgresql://test")
        key = create_storage_key()
        
        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(side_effect=Exception("DB error"))
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await storage.get_data(key)
            
            assert result == {}
            mock_conn.close.assert_called_once()


class TestPostgresFSMStorageClose:
    """Тесты для метода close"""

    @pytest.mark.asyncio
    async def test_close(self):
        """Тест: метод close ничего не делает"""
        storage = PostgresFSMStorage("postgresql://test")
        
        # Не должно быть исключений
        await storage.close()

