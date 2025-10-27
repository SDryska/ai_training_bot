"""
Тесты для репозитория рейтингов.

Тестируемый модуль:
- app/repositories/ratings.py

Тестируемые компоненты:
- upsert_rating функция
- get_user_ratings функция
- get_user_rating_for_question функция
- insert_rating_comment функция
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories.ratings import (
    upsert_rating,
    get_user_ratings,
    get_user_rating_for_question,
    insert_rating_comment,
    RATING_QUESTIONS,
    _connect
)


class TestUpsertRating:
    """Тесты для функции upsert_rating"""

    @pytest.mark.asyncio
    async def test_upsert_rating_success(self):
        """Тест: успешное обновление рейтинга"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await upsert_rating(12345, "overall_impression", 5)
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_rating_invalid_question(self):
        """Тест: неверный вопрос рейтинга"""
        with pytest.raises(ValueError, match="Unknown rating question"):
            await upsert_rating(12345, "invalid_question", 5)

    @pytest.mark.asyncio
    async def test_upsert_rating_no_connection(self):
        """Тест: обновление рейтинга без подключения"""
        with patch("app.repositories.ratings._connect", return_value=None):
            result = await upsert_rating(12345, "overall_impression", 5)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_upsert_rating_all_questions(self):
        """Тест: обновление всех типов вопросов"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            for question in RATING_QUESTIONS:
                await upsert_rating(12345, question, 5)
            
            assert mock_conn.execute.call_count == len(RATING_QUESTIONS)


class TestGetUserRatings:
    """Тесты для функции get_user_ratings"""

    @pytest.mark.asyncio
    async def test_get_user_ratings_success(self):
        """Тест: успешное получение рейтингов пользователя"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_row1 = MagicMock()
            mock_row1.__getitem__ = MagicMock(side_effect=lambda key: {
                "question": "overall_impression",
                "rating": 5
            }[key])
            mock_row2 = MagicMock()
            mock_row2.__getitem__ = MagicMock(side_effect=lambda key: {
                "question": "recommend_to_colleagues",
                "rating": 4
            }[key])
            mock_conn.fetch = AsyncMock(return_value=[mock_row1, mock_row2])
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await get_user_ratings(12345)
            
            assert len(result) == 2
            assert result["overall_impression"] == 5
            assert result["recommend_to_colleagues"] == 4
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_ratings_empty(self):
        """Тест: получение пустых рейтингов"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await get_user_ratings(12345)
            
            assert result == {}
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_ratings_no_connection(self):
        """Тест: получение рейтингов без подключения"""
        with patch("app.repositories.ratings._connect", return_value=None):
            result = await get_user_ratings(12345)
            
            assert result == {}


class TestGetUserRatingForQuestion:
    """Тесты для функции get_user_rating_for_question"""

    @pytest.mark.asyncio
    async def test_get_user_rating_for_question_success(self):
        """Тест: успешное получение рейтинга для вопроса"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = MagicMock(return_value=5)
            mock_conn.fetchrow = AsyncMock(return_value=mock_row)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await get_user_rating_for_question(12345, "overall_impression")
            
            assert result == 5
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_rating_for_question_not_found(self):
        """Тест: рейтинг не найден"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value=None)
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            result = await get_user_rating_for_question(12345, "overall_impression")
            
            assert result is None
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_rating_for_question_no_connection(self):
        """Тест: получение рейтинга без подключения"""
        with patch("app.repositories.ratings._connect", return_value=None):
            result = await get_user_rating_for_question(12345, "overall_impression")
            
            assert result is None


class TestInsertRatingComment:
    """Тесты для функции insert_rating_comment"""

    @pytest.mark.asyncio
    async def test_insert_rating_comment_success(self):
        """Тест: успешное добавление комментария"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await insert_rating_comment(12345, "Great bot!")
            
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_rating_comment_no_connection(self):
        """Тест: добавление комментария без подключения"""
        with patch("app.repositories.ratings._connect", return_value=None):
            result = await insert_rating_comment(12345, "Great bot!")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_insert_rating_comment_empty_comment(self):
        """Тест: добавление пустого комментария"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await insert_rating_comment(12345, "")
            
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_rating_comment_multiple_comments(self):
        """Тест: добавление нескольких комментариев"""
        with patch("app.repositories.ratings._connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_connect.return_value = mock_conn
            
            await insert_rating_comment(12345, "First comment")
            await insert_rating_comment(12345, "Second comment")
            
            assert mock_conn.execute.call_count == 2


class TestConnectRatings:
    """Тесты функции подключения к БД для ratings"""

    @pytest.mark.asyncio
    async def test_connect_without_database_url(self):
        """Тест: подключение без DATABASE_URL возвращает None"""
        with patch('app.repositories.ratings.Settings') as mock_settings:
            mock_settings.return_value.DATABASE_URL = None
            
            result = await _connect()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_connect_calls_normalize_db_url(self):
        """Тест: подключение вызывает normalize_db_url"""
        with patch('app.repositories.ratings.Settings') as mock_settings, \
             patch('app.repositories.ratings.normalize_db_url') as mock_normalize:
            
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

