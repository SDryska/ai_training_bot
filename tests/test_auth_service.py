"""
Тесты для сервиса аутентификации.

Тестируемый модуль:
- app/services/auth.py

Тестируемые компоненты:
- normalize_db_url функция
- run_migrations функция
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestNormalizeDbUrl:
    """Тесты для функции normalize_db_url"""

    def test_normalize_db_url_with_asyncpg(self):
        """Тест: конвертация sqlalchemy-style URL в asyncpg URL"""
        from app.services.auth import normalize_db_url
        
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        result = normalize_db_url(url)
        assert result == "postgresql://user:pass@host:5432/db"

    def test_normalize_db_url_without_asyncpg(self):
        """Тест: URL без +asyncpg остается без изменений"""
        from app.services.auth import normalize_db_url
        
        url = "postgresql://user:pass@host:5432/db"
        result = normalize_db_url(url)
        assert result == url

    def test_normalize_db_url_none(self):
        """Тест: None возвращается как есть"""
        from app.services.auth import normalize_db_url
        
        result = normalize_db_url(None)
        assert result is None

    def test_normalize_db_url_empty_string(self):
        """Тест: пустая строка возвращается как есть"""
        from app.services.auth import normalize_db_url
        
        result = normalize_db_url("")
        assert result == ""


class TestRunMigrations:
    """Тесты для функции run_migrations"""

    def test_run_migrations_success(self):
        """Тест: успешное выполнение миграций"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("importlib.import_module"), \
             patch("subprocess.run") as mock_run:
            
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            mock_run.return_value.stdout = ""
            
            run_migrations(mock_logger, "postgresql://test/db")
            
            mock_run.assert_called_once()
            mock_logger.info.assert_called()

    def test_run_migrations_no_database_url(self):
        """Тест: выполнение миграций без DATABASE_URL"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        run_migrations(mock_logger, None)
        
        mock_logger.info.assert_called_with("DATABASE_URL не задан, миграции пропущены")

    def test_run_migrations_no_alembic_ini(self):
        """Тест: выполнение миграций без alembic.ini"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=False):
            run_migrations(mock_logger, "postgresql://test/db")
            
            mock_logger.warning.assert_called_with("Файл alembic.ini не найден, миграции пропущены")

    def test_run_migrations_alembic_not_installed(self):
        """Тест: выполнение миграций без установленного Alembic"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("importlib.import_module", side_effect=ModuleNotFoundError("No module named 'alembic'")):
            
            run_migrations(mock_logger, "postgresql://test/db")
            
            mock_logger.error.assert_called()

    def test_run_migrations_alembic_import_error(self):
        """Тест: ошибка импорта Alembic"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("importlib.import_module", side_effect=Exception("Import error")):
            
            run_migrations(mock_logger, "postgresql://test/db")
            
            mock_logger.warning.assert_called()

    def test_run_migrations_subprocess_error(self):
        """Тест: ошибка при выполнении subprocess"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("importlib.import_module"), \
             patch("subprocess.run") as mock_run:
            
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Migration error"
            mock_run.return_value.stdout = ""
            
            run_migrations(mock_logger, "postgresql://test/db")
            
            mock_logger.error.assert_called()

    def test_run_migrations_timeout(self):
        """Тест: таймаут при выполнении миграций"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("importlib.import_module"), \
             patch("subprocess.run") as mock_run:
            
            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired("alembic", 300)
            
            run_migrations(mock_logger, "postgresql://test/db")
            
            mock_logger.warning.assert_called()

    def test_run_migrations_exception(self):
        """Тест: общее исключение при выполнении миграций"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("importlib.import_module"), \
             patch("subprocess.run", side_effect=Exception("General error")):
            
            run_migrations(mock_logger, "postgresql://test/db")
            
            mock_logger.warning.assert_called()

    def test_run_migrations_with_pythonpath(self):
        """Тест: выполнение миграций с установленным PYTHONPATH"""
        from app.services.auth import run_migrations
        
        mock_logger = MagicMock()
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("importlib.import_module"), \
             patch("subprocess.run") as mock_run, \
             patch("os.environ", {"PYTHONPATH": "/existing/path"}):
            
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            mock_run.return_value.stdout = ""
            
            run_migrations(mock_logger, "postgresql://test/db")
            
            # Проверяем, что PYTHONPATH был объединен
            call_kwargs = mock_run.call_args[1]
            env = call_kwargs["env"]
            assert "PYTHONPATH" in env

