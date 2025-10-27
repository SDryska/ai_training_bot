from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Принудительно загружаем .env в начале модуля настроек
load_dotenv(override=True)


class Settings(BaseSettings):
    # Обязательно для запуска
    BOT_TOKEN: str = Field(..., description="Токен Telegram-бота")

    # Бэкенд (используем позже в сервисах)
    BACKEND_BASE_URL: str | None = Field(default=None, description="Базовый URL бэкенда")
    BACKEND_TIMEOUT: float = Field(default=10.0, description="Таймаут запросов к бэкенду (сек)")
    BACKEND_MAX_RETRIES: int = Field(default=3, description="Макс. число ретраев к бэкенду")

    # База данных
    DATABASE_URL: str | None = Field(default=None, description="postgresql+asyncpg://...")
    DATABASE_SSL_MODE: str = Field(default="prefer", description="SSL режим для PostgreSQL (disable/prefer/require)")

    # Авторизация (пароли ролей)
    AUTH_PASSWORD_USER: str | None = Field(default=None, description="Пароль для роли user")
    AUTH_PASSWORD_ADMIN: str | None = Field(default=None, description="Пароль для роли admin")

    # Метрики и наблюдаемость
    METRICS_PORT: int = Field(default=8000, description="Порт HTTP-сервера метрик Prometheus")
    SENTRY_DSN: str | None = Field(default=None, description="DSN для Sentry (опционально)")
    SENTRY_ENV: str = Field(default="dev", description="Окружение для Sentry")

    # Планировщик
    APSCHEDULER_TIMEZONE: str = Field(default="UTC", description="Часовой пояс планировщика")
    
    # Экспорт статистики в Google Sheets (фон)
    SHEETS_EXPORT_ENABLED: bool = Field(default=False, description="Включить фоновой экспорт в Google Sheets")
    
    # Webhook настройки
    WEBHOOK_ENABLED: bool = Field(default=False, description="Использовать webhook вместо polling")
    WEBHOOK_HOST: str | None = Field(default=None, description="Хост для webhook (например, https://your-app.amvera.ru)")
    WEBHOOK_PATH: str = Field(default="/webhook", description="Путь для webhook")
    WEBHOOK_PORT: int = Field(default=80, description="Порт для aiohttp сервера")
    
    # OpenAI API
    OPENAI_API_KEY: str | None = Field(default=None, description="API ключ для OpenAI")
    
    # Google Gemini API
    GEMINI_API_KEY: str | None = Field(default=None, description="API ключ для Google Gemini")
    
    # Валидация входных данных
    # Текстовые сообщения
    TEXT_MAX_LENGTH: int = Field(default=12000, description="Максимальная длина текстового сообщения (символов)")
    TEXT_MAX_LINES: int = Field(default=50, description="Максимальное количество строк в сообщении")
    TEXT_MIN_LENGTH: int = Field(default=1, description="Минимальная длина текстового сообщения (символов)")
    
    # Голосовые сообщения
    VOICE_MAX_SIZE_MB: float = Field(default=25.0, description="Максимальный размер голосового файла (МБ)")
    VOICE_MAX_DURATION_SEC: int = Field(default=300, description="Максимальная длительность голосового сообщения (сек)")
    VOICE_MIN_DURATION_SEC: float = Field(default=0.5, description="Минимальная длительность голосового сообщения (сек)")
    
    # Rate limiting (опционально)
    MAX_REQUESTS_PER_MINUTE: int = Field(default=20, description="Максимум запросов к AI на пользователя в минуту")
    MAX_REQUESTS_PER_HOUR: int = Field(default=100, description="Максимум запросов к AI на пользователя в час")

    # Таймауты и ретраи AI-провайдера
    AI_REQUEST_TIMEOUT_SEC: float = Field(default=30.0, description="Таймаут запроса к AI провайдеру (сек)")
    AI_REQUEST_MAX_RETRIES: int = Field(default=3, description="Максимум попыток запроса к AI провайдеру")
    AI_REQUEST_RETRY_BACKOFF_SEC: float = Field(default=1.5, description="Бэкофф между ретраями (сек)")

    # Таймауты и ретраи транскрибации
    TRANSCRIBE_TIMEOUT_SEC: float = Field(default=25.0, description="Таймаут транскрибации (сек)")
    TRANSCRIBE_MAX_RETRIES: int = Field(default=2, description="Максимум попыток транскрибации")
    TRANSCRIBE_RETRY_BACKOFF_SEC: float = Field(default=1.0, description="Бэкофф между ретраями транскрибации (сек)")

    # Загрузка из .env по умолчанию
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra='ignore')
