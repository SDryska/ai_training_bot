# Unit Tests

Тесты компонентов проекта (pytest/pytest-asyncio).

## Repositories

- **test_authorized_users_repository.py** - тесты репозитория авторизованных пользователей
  - Подключение к БД
  - Получение роли пользователя
  - Создание/обновление пользователя
  - Обработка ошибок БД

## Keyboards & Callbacks

- **test_callbacks.py** - тесты упаковки/распаковки callback данных
  - Упаковка с префиксом и данными
  - Распаковка и парсинг
  - Обработка edge cases

## Middlewares

- **test_errors_middleware.py** - тесты middleware обработки ошибок
  - Перехват исключений
  - Логирование ошибок
  - Отправка friendly сообщений пользователю
  - Graceful fallback при ошибках БД

## Services

- **test_validation_service.py** - тесты сервиса валидации входных данных
  - Валидация текстовых сообщений (длина, строки)
  - Валидация голосовых сообщений (размер, длительность)
  - Rate limiting
  - Custom правила валидации

## AI Response Parsing

- **test_parse_ai_response.py** - тесты парсинга ответов от AI моделей
  - Парсинг JSON ответов
  - Обработка ошибок парсинга
  - Fallback значения для всех трёх кейсов (fb_peer, fb_employee, career_dialog)

## Запуск тестов

```bash
# Все тесты
pytest

# Конкретный тест
pytest tests/test_validation_service.py

# С логированием
pytest -v

# С покрытием
pytest --cov=app
```

## Требования

- pytest >= 8.0
- pytest-asyncio >= 0.23
- Зависит от requirements.txt
