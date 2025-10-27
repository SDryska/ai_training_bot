# EMCO Assessment Bot (aiogram v3, Python 3.10)

Проект Telegram-бота на aiogram v3. Цели: модульная архитектура, асинхронность, простая масштабируемость, быстрое время до первого релиза (80/20), дальнейшее развитие итерациями.

## Стек (80/20)
- Язык: Python 3.10
- Telegram: aiogram v3.x (Routers, Middlewares, FSM)
- БД: PostgreSQL
- Драйвер БД: asyncpg (асинхронный)
- Планировщик рассылок: APScheduler AsyncIOScheduler
  - Job store: PostgreSQL
  - Один активный инстанс планировщика
- Конфигурация: pydantic-settings + .env (для dev)
- Логирование: stdlib logging
- Метрики: prometheus-client (отдельный http endpoint)
- Ошибки: sentry-sdk (опционально, через DSN)
- Пакетный менеджер: pip
- AI Провайдеры: OpenAI, Google Gemini
- Google Sheets экспорт: gspread + google-auth
- Голос: распознавание и работа с аудио

## Структура проекта
```
.
├─ bot.py                # Точка входа (polling в dev; webhook в prod)
├─ app/
│  ├─ cases/             # Сценарии взаимодействия (fb_employee, fb_peer, career_dialog)
│  │  ├─ fb_employee/    # Сценарий обратной связи от сотрудника
│  │  ├─ fb_peer/        # Сценарий обратной связи от коллеги
│  │  └─ career_dialog/  # Сценарий карьерного диалога
│  ├─ config/            # Конфиги, загрузка переменных окружения (pydantic-settings)
│  ├─ handlers/          # Основные обработчики (/start, /help, auth, nav, rating)
│  ├─ keyboards/         # Инлайн/реплай клавиатуры и колбэки
│  ├─ middlewares/       # Промежуточные слои (логирование, обработка ошибок, роли)
│  ├─ metrics.py         # Метрики Prometheus
│  ├─ providers/         # AI провайдеры (OpenAI, Gemini)
│  ├─ repositories/      # Работа с БД (пользователи, рейтинги, статистика)
│  ├─ services/          # Бизнес-логика (auth, AI, валидация, транскрипция)
│  ├─ storage/           # FSM/кеш/хранилища (MemoryStorage, PostgresFSMStorage)
│  ├─ texts.py           # Текстовые сообщения
│  └─ utils/             # Утилиты/хелперы
├─ standalone/           # Скрипты для тестирования и экспорта данных
├─ static/               # Статические файлы (PDF гайды)
├─ tests/                # Тесты (pytest/pytest-asyncio)
├─ docs/                 # Документация проекта
├─ .env.example          # Образец переменных окружения
├─ requirements.txt      # Зависимости (pip)
└─ amvera.yml           # Конфигурация для развёртывания на Amvera
```

## Основные модули

### Сценарии (Cases)
Каждый сценарий представляет собой отдельный кейс взаимодействия с пользователем:
- **fb_employee**: Обратная связь от сотрудника
- **fb_peer**: Обратная связь от коллеги
- **career_dialog**: Диалог о карьере

Каждый сценарий имеет:
- `config.py` - конфигурация сценария
- `handler.py` - основная логика с router'ом

### Компоненты приложения
- **Handlers**: Основные обработчики команд и взаимодействий
- **Services**: Бизнес-логика (аутентификация, AI, валидация)
- **Providers**: Интеграции с внешними AI API (OpenAI, Gemini)
- **Repositories**: Работа с базой данных
- **Middlewares**: Обработка ошибок и проверка ролей
- **Storage**: Хранение состояний FSM

## Конфигурация (.env)
Пример ключей (минимум):
```
BOT_TOKEN=        # токен бота (обязательно)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# Авторизация (ролевой доступ)
AUTH_PASSWORD_USER=your_user_password
AUTH_PASSWORD_ADMIN=your_admin_password

# AI Провайдеры
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# Webhook Configuration (для production на Amvera)
WEBHOOK_ENABLED=false  # true для webhook режима
WEBHOOK_HOST=https://your-app.amvera.ru
WEBHOOK_PATH=/webhook
WEBHOOK_PORT=80

# Метрики Prometheus
METRICS_PORT=8000

# Sentry (опционально)
SENTRY_DSN=
SENTRY_ENV=dev

# Планировщик
APSCHEDULER_TIMEZONE=UTC

# Валидация входных данных
TEXT_MAX_LENGTH=12000
TEXT_MAX_LINES=50
TEXT_MIN_LENGTH=1
VOICE_MAX_SIZE_MB=25.0
VOICE_MAX_DURATION_SEC=300
VOICE_MIN_DURATION_SEC=0.5
MAX_REQUESTS_PER_MINUTE=20
MAX_REQUESTS_PER_HOUR=100

# Google Sheets экспорт (опционально)
SHEETS_EXPORT_ENABLED=false
```

Загрузка конфигурации: через `pydantic-settings` в `app/config/settings.py`.

## Запуск локально (dev, polling)
1. Python 3.10+
2. Создать виртуальное окружение и установить зависимости:
   - Windows PowerShell:
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```
   - Linux/macOS:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
3. Скопировать `.env.example` → `.env` и заполнить `BOT_TOKEN`, `DATABASE_URL`, `AUTH_PASSWORD_USER`, `AUTH_PASSWORD_ADMIN` и API ключи.
4. Запустить бота:
   ```
   python bot.py
   ```
5. Метрики Prometheus будут доступны на `http://localhost:${METRICS_PORT}/` (по умолчанию 8000).

## Деплой на Amvera (Production, Webhook)

### Первичная настройка

1. **Создайте проект на Amvera:**
   - Подключите ваш GitHub репозиторий
   - Amvera автоматически определит Python окружение из `amvera.yml` (Python 3.10)

2. **Настройте переменные окружения в Amvera:**
   ```
   BOT_TOKEN=your_bot_token
   DATABASE_URL=postgresql+asyncpg://...
   AUTH_PASSWORD_USER=your_user_pass
   AUTH_PASSWORD_ADMIN=your_admin_pass
   OPENAI_API_KEY=your_key
   GEMINI_API_KEY=your_key
   
   # Webhook настройки (обязательно!)
   WEBHOOK_ENABLED=true
   WEBHOOK_HOST=https://your-app.amvera.ru
   WEBHOOK_PATH=/webhook
   WEBHOOK_PORT=80
   
   # Опционально
   SENTRY_DSN=your_sentry_dsn
   SENTRY_ENV=production
   SHEETS_EXPORT_ENABLED=false
   ```

3. **Задеплойте приложение:**
   - Amvera автоматически запустит бота с webhook режимом
   - Health check доступен на `https://your-app.amvera.ru/health`

### Zero-Downtime Обновления

Бот настроен для **graceful shutdown**, что обеспечивает обновления без потери сообщений:

1. **Как это работает:**
   - При получении сигнала SIGTERM (от Amvera при деплое), бот:
     - Прекращает принимать новые запросы
     - Завершает обработку текущих сообщений (до 30 секунд)
     - Корректно закрывает все соединения
     - Telegram буферизирует входящие сообщения во время переключения

2. **Деплой обновлений:**
   - Просто сделайте `git push` в ваш репозиторий
   - Amvera автоматически:
     - Соберёт новую версию
     - Отправит SIGTERM старому контейнеру
     - Запустит новый контейнер
     - Переключит трафик (rolling update)
   - **Время простоя: < 5 секунд**
   - **Потеря сообщений: 0** (Telegram хранит их в очереди)

3. **Мониторинг деплоя:**
   - Проверьте health check: `curl https://your-app.amvera.ru/health`
   - Логи доступны в панели Amvera
   - Метрики Prometheus на порту 8000 (настройте в Amvera если нужен доступ)

### Переключение между polling и webhook

**Development (локально):**
```env
WEBHOOK_ENABLED=false
```

**Production (Amvera):**
```env
WEBHOOK_ENABLED=true
WEBHOOK_HOST=https://your-app.amvera.ru
```

Бот автоматически определит режим работы при запуске.

## База данных и миграции
- Используется PostgreSQL с asyncpg драйвером
- Инициализация/обновление схемы выполняется через Alembic: `run_migrations()` в `app/services/auth.py`

## Хранилище состояний (FSM)
- **Development**: MemoryStorage (память приложения)
- **Production**: PostgresFSMStorage (база данных)
- Автоматический выбор при запуске в зависимости от наличия `DATABASE_URL`

## Планировщик рассылок (APScheduler)
- Используем `AsyncIOScheduler`.
- Job store — PostgreSQL (через SQLAlchemy). Это даёт надежность и совместимость при рестартах.
- Запускается внутри процесса бота с одним активным инстансом планировщика.

## Метрики и наблюдаемость
- Prometheus: счётчики/гистограммы по ключевым путям (запросы к бэкенду, обработка апдейтов, отправка сообщений, джобы).
- Sentry: подключаем при наличии `SENTRY_DSN`. Если пусто — не активируем.

## Логирование
- Стандартный `logging` с уровнем из env (например, INFO)

## Архитектурные принципы
- Модульность: один сценарий = один кейс с config + handler
- Чистые границы: `handlers` (взаимодействие с Telegram) ↔ `services` (бизнес/интеграции) ↔ `repositories` (БД)
- Асинхронность end-to-end (aiogram/asyncpg/SQLAlchemy async)
- Ролевой доступ через middlewares

## Текущие возможности
- ✅ Три полноценных сценария взаимодействия (fb_employee, fb_peer, career_dialog)
- ✅ Система рейтингов
- ✅ Интеграция с OpenAI и Google Gemini
- ✅ Валидация входных данных
- ✅ Распознавание речи (транскрипция)
- ✅ Экспорт статистики в Google Sheets
- ✅ Ролевой доступ (user, admin)
- ✅ Graceful shutdown и zero-downtime деплой
- ✅ Prometheus метрики
- ✅ Обработка ошибок и логирование
- ✅ FSM хранилище (MemoryStorage в dev, PostgresFSMStorage в prod)

## Безопасность
- Не коммитим `.env` и секреты
- Принудительные таймауты на внешних вызовах
- Базовые лимиты отправки сообщений и логирование ошибок
- Ролевой доступ и аутентификация через пароли
- Валидация всех входных данных

---

Проект находится в активной разработке и полностью функционален для использования в production с webhook режимом на Amvera.