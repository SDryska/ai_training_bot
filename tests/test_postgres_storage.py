"""
Тесты для PostgreSQL хранилища истории диалогов.

Тестируемый модуль:
- app/storage/postgres_storage.py

Тестируемые компоненты:
- PostgresStorage класс
- _normalize_db_url функция
- Методы: __init__, _get_pool, _connect, save_message, get_history, clear_history, get_conversation_length
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

from app.storage.postgres_storage import PostgresStorage, _normalize_db_url
from app.providers.base import AIMessage


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


class TestPostgresStorageInit:
    """Тесты для __init__ метода"""

    def test_init_with_url(self):
        """Тест: инициализация с явным URL"""
        storage = PostgresStorage("postgresql://user:pass@host:5432/db")
        assert storage.database_url == "postgresql://user:pass@host:5432/db"
        assert storage._pool is None

    def test_init_with_none(self):
        """Тест: инициализация без URL (берется из Settings)"""
        with patch("app.storage.postgres_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = "postgresql://localhost/test"
            storage = PostgresStorage()
            assert storage.database_url == "postgresql://localhost/test"

    def test_init_normalizes_url(self):
        """Тест: URL нормализуется при инициализации"""
        storage = PostgresStorage("postgresql+asyncpg://user:pass@host:5432/db")
        assert storage.database_url == "postgresql://user:pass@host:5432/db"


class TestPostgresStorageGetPool:
    """Тесты для метода _get_pool"""

    @pytest.mark.asyncio
    async def test_get_pool_success(self):
        """Тест: успешное создание connection pool"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            result = await storage._get_pool()
            
            assert result == mock_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pool_no_database_url(self):
        """Тест: создание pool без DATABASE_URL"""
        with patch("app.storage.postgres_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            storage = PostgresStorage(None)
            
            result = await storage._get_pool()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_pool_exception(self):
        """Тест: обработка исключения при создании pool"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock, side_effect=Exception("Pool error")):
            result = await storage._get_pool()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_pool_returns_existing_pool(self):
        """Тест: возврат существующего pool"""
        storage = PostgresStorage("postgresql://test")
        mock_pool = AsyncMock()
        storage._pool = mock_pool
        
        result = await storage._get_pool()
        
        assert result == mock_pool

    @pytest.mark.asyncio
    async def test_get_pool_race_condition(self):
        """Тест: защита от race condition при создании pool"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            
            # Имитируем ситуацию, когда pool создаётся между проверками
            async def set_pool_on_lock(*args, **kwargs):
                if storage._pool is None:
                    storage._pool = mock_pool
                return mock_pool
            
            mock_create_pool.side_effect = set_pool_on_lock
            
            # Первый вызов создаст pool
            result1 = await storage._get_pool()
            # Второй вызов должен вернуть существующий pool
            result2 = await storage._get_pool()
            
            assert result1 == mock_pool
            assert result2 == mock_pool
            # create_pool должен быть вызван только один раз
            assert mock_create_pool.call_count == 1

    @pytest.mark.asyncio
    async def test_get_pool_double_check_return_existing(self):
        """Тест: double-check возвращает существующий pool"""
        storage = PostgresStorage("postgresql://test")
        mock_pool = AsyncMock()
        storage._pool = mock_pool
        
        result = await storage._get_pool()
        
        assert result == mock_pool


class TestPostgresStorageConnect:
    """Тесты для метода _connect"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Тест: успешное получение соединения из pool"""
        storage = PostgresStorage("postgresql://test")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value = mock_conn
        storage._pool = mock_pool
        
        result = await storage._connect()
        
        assert result == mock_conn
        mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_no_pool(self):
        """Тест: получение соединения без pool"""
        with patch("app.storage.postgres_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            storage = PostgresStorage(None)
            storage._pool = None
            
            result = await storage._connect()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Тест: обработка исключения при получении соединения"""
        storage = PostgresStorage("postgresql://test")
        mock_pool = AsyncMock()
        mock_pool.acquire.side_effect = Exception("Acquire error")
        storage._pool = mock_pool
        
        result = await storage._connect()
        
        assert result is None


class TestPostgresStorageSaveMessage:
    """Тесты для метода save_message"""

    @pytest.mark.asyncio
    async def test_save_message_success(self):
        """Тест: успешное сохранение сообщения"""
        storage = PostgresStorage("postgresql://test")
        message = AIMessage("user", "Hello", {"test": "metadata"})
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            # Настраиваем pool.acquire() как асинхронный контекстный менеджер
            mock_acquire_cm = AsyncMock()
            mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)
            mock_create_pool.return_value = mock_pool
            
            await storage.save_message(12345, "openai", message)
            
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_message_no_pool(self):
        """Тест: сохранение сообщения без pool"""
        storage = PostgresStorage(None)
        message = AIMessage("user", "Hello")
        
        await storage.save_message(12345, "openai", message)
        
        # Не должно быть исключений

    @pytest.mark.asyncio
    async def test_save_message_pool_creation_fails(self):
        """Тест: сохранение сообщения когда _get_pool возвращает None"""
        storage = PostgresStorage("postgresql://test")
        message = AIMessage("user", "Hello")
        
        # Мокируем _get_pool чтобы он вернул None
        with patch.object(storage, '_get_pool', new_callable=AsyncMock, return_value=None):
            await storage.save_message(12345, "openai", message)
            
            # Не должно быть исключений

    @pytest.mark.asyncio
    async def test_get_pool_double_check_pattern(self):
        """Тест: double-check паттерн для создания pool"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            # Первый вызов создает pool
            pool1 = await storage._get_pool()
            assert pool1 == mock_pool
            
            # Второй вызов использует существующий pool (double-check срабатывает)
            pool2 = await storage._get_pool()
            assert pool2 == mock_pool
            
            # create_pool вызван только один раз
            assert mock_create_pool.call_count == 1

    @pytest.mark.asyncio
    async def test_save_message_with_metadata(self):
        """Тест: сохранение сообщения с metadata"""
        storage = PostgresStorage("postgresql://test")
        message = AIMessage("user", "Hello", {"key": "value", "number": 123})
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_acquire_cm = AsyncMock()
            mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)
            mock_create_pool.return_value = mock_pool
            
            await storage.save_message(12345, "openai", message)
            
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args[0]
            # Проверяем, что metadata передаётся
            assert len(call_args) == 6
            assert call_args[4] is not None  # metadata_json

    @pytest.mark.asyncio
    async def test_save_message_with_none_metadata(self):
        """Тест: сохранение сообщения без metadata"""
        storage = PostgresStorage("postgresql://test")
        message = AIMessage("user", "Hello", None)
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_acquire_cm = AsyncMock()
            mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)
            mock_create_pool.return_value = mock_pool
            
            await storage.save_message(12345, "openai", message)
            
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_message_exception(self):
        """Тест: обработка исключения при сохранении"""
        storage = PostgresStorage("postgresql://test")
        message = AIMessage("user", "Hello")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("DB error"))
            # Настраиваем pool.acquire() как асинхронный контекстный менеджер
            mock_acquire_cm = AsyncMock()
            mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)
            mock_create_pool.return_value = mock_pool
            
            await storage.save_message(12345, "openai", message)
            
            # Не должно быть исключений


class TestPostgresStorageGetHistory:
    """Тесты для метода get_history"""

    @pytest.mark.asyncio
    async def test_get_history_success(self):
        """Тест: успешное получение истории"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = MagicMock(side_effect=lambda key: {
                "role": "user",
                "content": "Hello",
                "metadata": '{"test": "data"}'
            }[key])
            mock_conn.fetch = AsyncMock(return_value=[mock_row])
            # Настраиваем pool.acquire() как асинхронный контекстный менеджер
            mock_acquire_cm = AsyncMock()
            mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)
            mock_create_pool.return_value = mock_pool
            
            result = await storage.get_history(12345, "openai")
            
            assert len(result) == 1
            assert result[0].role == "user"
            assert result[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        """Тест: получение пустой истории"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            # Настраиваем pool.acquire() как асинхронный контекстный менеджер
            mock_acquire_cm = AsyncMock()
            mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)
            mock_create_pool.return_value = mock_pool
            
            result = await storage.get_history(12345, "openai")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_history_no_pool(self):
        """Тест: получение истории без pool"""
        with patch("app.storage.postgres_storage.Settings") as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            storage = PostgresStorage(None)
            
            result = await storage.get_history(12345, "openai")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_get_history_exception(self):
        """Тест: обработка исключения при получении истории"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(side_effect=Exception("DB error"))
            # Настраиваем pool.acquire() как асинхронный контекстный менеджер
            mock_acquire_cm = AsyncMock()
            mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire_cm.__aexit__ = AsyncMock(return_value=None)
            mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)
            mock_create_pool.return_value = mock_pool
            
            result = await storage.get_history(12345, "openai")
            
            assert result == []


class TestPostgresStorageClearHistory:
    """Тесты для метода clear_history"""

    @pytest.mark.asyncio
    async def test_clear_history_success(self):
        """Тест: успешная очистка истории"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_pool.acquire.return_value = mock_conn
            mock_create_pool.return_value = mock_pool
            
            await storage.clear_history(12345, "openai")
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_history_no_connection(self):
        """Тест: очистка истории без подключения"""
        storage = PostgresStorage(None)
        
        await storage.clear_history(12345, "openai")
        
        # Не должно быть исключений

    @pytest.mark.asyncio
    async def test_clear_history_connect_fails(self):
        """Тест: очистка истории когда _connect возвращает None"""
        storage = PostgresStorage("postgresql://test")
        
        # Мокируем _connect чтобы он вернул None
        with patch.object(storage, '_connect', new_callable=AsyncMock, return_value=None):
            await storage.clear_history(12345, "openai")
            
            # Не должно быть исключений

    @pytest.mark.asyncio
    async def test_clear_history_exception(self):
        """Тест: обработка исключения при очистке"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(side_effect=Exception("DB error"))
            mock_conn.close = AsyncMock()
            mock_pool.acquire.return_value = mock_conn
            mock_create_pool.return_value = mock_pool
            
            await storage.clear_history(12345, "openai")
            
            mock_conn.close.assert_called_once()


class TestPostgresStorageGetConversationLength:
    """Тесты для метода get_conversation_length"""

    @pytest.mark.asyncio
    async def test_get_conversation_length_success(self):
        """Тест: успешное получение длины истории"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=5)
            mock_conn.close = AsyncMock()
            mock_pool.acquire.return_value = mock_conn
            mock_create_pool.return_value = mock_pool
            
            result = await storage.get_conversation_length(12345, "openai")
            
            assert result == 5
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_length_zero(self):
        """Тест: длина истории равна нулю"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(return_value=0)
            mock_conn.close = AsyncMock()
            mock_pool.acquire.return_value = mock_conn
            mock_create_pool.return_value = mock_pool
            
            result = await storage.get_conversation_length(12345, "openai")
            
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_conversation_length_no_connection(self):
        """Тест: получение длины без подключения"""
        storage = PostgresStorage(None)
        
        result = await storage.get_conversation_length(12345, "openai")
        
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_conversation_length_connect_fails(self):
        """Тест: получение длины когда _connect возвращает None"""
        storage = PostgresStorage("postgresql://test")
        
        # Мокируем _connect чтобы он вернул None
        with patch.object(storage, '_connect', new_callable=AsyncMock, return_value=None):
            result = await storage.get_conversation_length(12345, "openai")
            
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_conversation_length_exception(self):
        """Тест: обработка исключения при получении длины"""
        storage = PostgresStorage("postgresql://test")
        
        with patch("asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.fetchval = AsyncMock(side_effect=Exception("DB error"))
            mock_conn.close = AsyncMock()
            mock_pool.acquire.return_value = mock_conn
            mock_create_pool.return_value = mock_pool
            
            result = await storage.get_conversation_length(12345, "openai")
            
            assert result == 0
            mock_conn.close.assert_called_once()

