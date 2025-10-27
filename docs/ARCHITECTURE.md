# EMCO Assessment Bot — Архитектура

## Структура проекта

```
app/
├── cases/                    # Сценарии взаимодействия
│   ├── fb_employee/         # Обратная связь от сотрудника
│   ├── fb_peer/             # Обратная связь от коллеги
│   └── career_dialog/       # Диалог о карьере
├── config/
│   ├── settings.py          # Конфигурация (pydantic-settings)
│   └── provider_config.py   # Конфигурация AI провайдеров
├── handlers/                # Основные обработчики
│   ├── auth.py             # Аутентификация (/start, пароли)
│   ├── help.py             # Справка (/help)
│   ├── nav.py              # Навигация (главное меню)
│   ├── rating.py           # Рейтинги
│   └── fallback.py         # Обработка неизвестных команд
├── keyboards/              # Клавиатуры и кнопки
│   ├── menu.py             # Главное меню
│   ├── callbacks.py        # Упаковка/распаковка callback-data
│   └── ratings.py          # Клавиатуры для рейтингов
├── middlewares/            # Промежуточные слои
│   ├── errors.py           # Обработка ошибок
│   └── roles.py            # Проверка ролей пользователей
├── metrics.py              # Prometheus метрики
├── providers/              # AI провайдеры
│   ├── base.py             # Базовый интерфейс
│   ├── gateway.py          # Роутер провайдеров
│   ├── openai.py           # Интеграция с OpenAI
│   └── gemini.py           # Интеграция с Google Gemini
├── repositories/           # Работа с БД
│   ├── authorized_users.py # Управление ролями пользователей
│   ├── ratings.py          # Рейтинги
│   ├── rating_invites.py   # Приглашения на рейтинг
│   └── case_stats.py       # Статистика кейсов
├── services/               # Бизнес-логика
│   ├── auth.py            # Аутентификация, инициализация БД
│   ├── ai_service.py      # Управление AI провайдерами
│   ├── validation_service.py # Валидация входных данных
│   └── transcription_service.py # Транскрибация аудио
├── storage/               # Хранилища FSM
│   ├── base.py            # Базовый интерфейс
│   ├── memory_storage.py  # In-memory (dev)
│   ├── postgres_fsm_storage.py # PostgreSQL (prod)
│   └── postgres_storage.py
├── texts.py              # Все текстовые сообщения
└── utils/                # Утилиты
    ├── case_stats.py
    ├── rating_flow.py
    └── typing_indicator.py
```

## Основные компоненты

### Bot Entry Point (`bot.py`)

1. Загрузка конфигурации из `.env` (pydantic-settings)
2. Инициализация логирования
3. Инициализация Sentry (опционально)
4. Применение миграций БД (`run_migrations()`)
5. Инициализация AI провайдеров
6. Выбор FSM storage (PostgreSQL или Memory)
7. Запуск метрик Prometheus
8. Запуск APScheduler
9. Регистрация middlewares
10. Подключение роутеров
11. Запуск polling (dev) или webhook (prod)
12. Graceful shutdown при SIGTERM/SIGINT

### Authentication (`app/handlers/auth.py`)

- `/start` - вход, проверка роли пользователя
- Ввод пароля - определение роли (user/admin)
- `/whoami` - информация о текущем пользователе
- Сохранение в `authorized_users` таблице

### Cases (Сценарии)

Каждый кейс — самостоятельный модуль с:
- `config.py` - конфигурация (промпты, параметры)
- `handler.py` - роутер и логика обработки диалога

**fb_employee** - обратная связь от сотрудника:
- Диалог по структурированному формату
- Финальный рецензия от модели
- Сохранение результатов

**fb_peer** - обратная связь от коллеги:
- Аналогичная структура
- Ориентирована на peer feedback

**career_dialog** - диалог о карьере:
- Консультация по развитию карьеры
- Структурированный вывод с рекомендациями

### AI Providers (Провайдеры)

**Gateway** (`app/providers/gateway.py`):
- Единая точка доступа к AI моделям
- Выбор провайдера (OpenAI/Gemini)
- Кэширование провайдеров

**OpenAI** (`app/providers/openai.py`):
- Модели: gpt-5, gpt-5-mini
- Транскрибация: gpt-4o-transcribe
- Отправка текста в модель

**Gemini** (`app/providers/gemini.py`):
- Модели: gemini-2.5-flash
- Встроенная обработка аудио
- Мультимодальная обработка

### Repositories (Доступ к БД)

- **authorized_users** - роли пользователей (user/admin)
- **ratings** - оценки и отзывы пользователей
- **rating_invites** - приглашения на рейтинг
- **case_stats** - статистика по кейсам

### Services (Бизнес-логика)

**auth.py**:
- `run_migrations()` - применение Alembic миграций
- `get_role_by_user_id()` - получение роли

**ai_service.py**:
- `initialize_ai_providers()` - инициализация при старте
- `get_ai_gateway()` - получение gateway
- Управление конфигурацией провайдеров

**validation_service.py**:
- Валидация текстовых сообщений (длина, количество строк)
- Валидация голосовых сообщений (размер, длительность)
- Rate limiting по пользователям
- Проверка черного списка слов

**transcription_service.py**:
- Загрузка аудиофайлов
- Транскрибация через OpenAI API
- Кэширование результатов

### Middlewares (Промежуточные слои)

**ErrorsMiddleware**:
- Перехват всех необработанных исключений
- Логирование ошибок
- Отправка friendly сообщения пользователю
- Graceful fallback при ошибках БД

**RolesMiddleware**:
- Определение роли пользователя
- Добавление информации о роли в контекст
- Fallback при ошибке БД (role=None)

### Storage (Хранилище состояний FSM)

**MemoryStorage** (dev):
- Состояния хранятся в памяти приложения
- Теряются при перезагрузке
- Подходит для локальной разработки

**PostgresFSMStorage** (prod):
- Состояния хранятся в PostgreSQL
- Сохраняются между перезагрузками
- Поддерживает масштабирование

## Flow обработки сообщения

1. **Telegram** отправляет обновление
2. **Bot** получает и передаёт в Dispatcher
3. **ErrorsMiddleware** оборачивает обработку в try/except
4. **RolesMiddleware** добавляет информацию о роли
5. **Router** определяет подходящий handler на основе состояния и типа обновления
6. **Handler** обрабатывает запрос:
   - Для кейсов: отправляет в AI модель
   - Для меню: отправляет инлайн-клавиатуру
   - Для команд: выполняет логику
7. **Service** выполняет бизнес-логику:
   - Валидация входных данных
   - Запрос к AI через Gateway
   - Работа с БД через Repositories
8. **Response** отправляется пользователю
9. **Metrics** записываются в Prometheus

## Ключевые решения

- **Webhook для production** - без потери сообщений при обновлении
- **Graceful shutdown** - корректное завершение при SIGTERM
- **FSM состояния в БД** - совместимость при масштабировании
- **Gateway pattern** - единая точка доступа к AI провайдерам
- **Repository pattern** - инкапсуляция доступа к БД
- **Middleware pattern** - централизованная обработка ошибок и ролей
- **Async/await end-to-end** - асинхронность на всех уровнях

## Конфигурация

Все параметры загружаются из `.env` через `app/config/settings.py`:
- `BOT_TOKEN` - токен бота (обязательно)
- `DATABASE_URL` - подключение к PostgreSQL (опционально)
- `AUTH_PASSWORD_USER`, `AUTH_PASSWORD_ADMIN` - пароли ролей
- `OPENAI_API_KEY`, `GEMINI_API_KEY` - ключи AI провайдеров
- `WEBHOOK_ENABLED`, `WEBHOOK_HOST`, `WEBHOOK_PORT` - настройки webhook
- `METRICS_PORT` - порт для Prometheus метрик
- Параметры валидации (TEXT_MAX_LENGTH, VOICE_MAX_SIZE_MB и т.д.)

## Масштабирование

Архитектура поддерживает:
- **Горизонтальное масштабирование** - несколько инстансов за балансировщиком
- **PostgreSQL FSM storage** - состояния в БД, общие для всех инстансов
- **Webhook** - входящие события распределяются между инстансами
- **Планировщик** - один активный инстанс (через блокировки в БД)
- **Метрики** - централизованный Prometheus для всех инстансов
