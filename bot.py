"""
Точка входа бота с поддержкой polling и webhook.

Что делает:
- Загружает конфиг из .env (pydantic-settings).
- Настраивает логирование.
- Поднимает метрики Prometheus на отдельном порту.
- Инициализирует планировщик APScheduler (позже добавим задания/рассылки).
- Создаёт Bot/Dispatcher/Router (aiogram v3) и обрабатывает /start.
- Запускает polling (dev) или webhook (production).
- Graceful shutdown для zero-downtime deploys.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.metrics import start_metrics
from app.config.settings import Settings
from app.storage import PostgresFSMStorage
from app.handlers.auth import router as auth_router
from app.cases.fb_employee.handler import router as case_fb_employee_router
from app.cases.fb_peer.handler import router as case_fb_peer_router
from app.cases.career_dialog.handler import router as case_career_dialog_router
from app.handlers.nav import router as nav_router
from app.handlers.rating import router as rating_router
from app.handlers.help import router as help_router
from app.handlers.fallback import router as fallback_router
from app.services.auth import run_migrations, normalize_db_url
from app.services.ai_service import initialize_ai_providers
from app.middlewares.errors import ErrorsMiddleware
from app.middlewares.roles import RolesMiddleware

# Импортируем экспортёр (используем его _export_once и настройки)
try:
    from standalone.db_to_sheets import ExportSettings, _export_once as export_once
except Exception:
    ExportSettings = None  # type: ignore
    export_once = None  # type: ignore

# -----------------------------
# Конфигурация приложения загружается из app/config/settings.py
# -----------------------------


# -----------------------------
# Метрики Prometheus импортируются из app/metrics.py
# -----------------------------


# -----------------------------
# Роутеры: все хэндлеры вынесены в app/handlers/auth.py
# -----------------------------


# -----------------------------
# Глобальные переменные для graceful shutdown
# -----------------------------
shutdown_event = asyncio.Event()


# -----------------------------
# Health check endpoint
# -----------------------------
async def health_check(request: web.Request) -> web.Response:
    """Проверка здоровья приложения для Amvera."""
    return web.Response(text="OK", status=200)


# -----------------------------
# Инициализация и запуск приложения
# -----------------------------
async def main() -> None:
    settings = Settings()

    # 1) Логирование (просто и понятно; позже можно перейти на JSON-логирование)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger("bot")

    # 2) Sentry (если указан DSN)
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.SENTRY_ENV,
                # Трейсинг можно включить позже; держим выключенным для 80/20
                traces_sample_rate=0.0,
            )
            logger.info("Sentry инициализирован")
        except Exception as e:
            logger.warning("Не удалось инициализировать Sentry: %s", e)

    # Применение миграций БД (если DATABASE_URL задан)
    if settings.DATABASE_URL:
        logger.info("📊 БД конфигурация:")
        logger.info("  DATABASE_URL: %s", settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL)
        run_migrations(logger, normalize_db_url(settings.DATABASE_URL))
    else:
        logger.warning("⚠️  DATABASE_URL не задан → используется in-memory хранилище (данные теряются при перезапуске)")
    
    # Инициализация AI провайдеров
    initialize_ai_providers()
    
    # Выбор FSM storage: PostgreSQL если есть DATABASE_URL, иначе Memory
    if settings.DATABASE_URL:
        fsm_storage = PostgresFSMStorage(settings.DATABASE_URL)
        logger.info("✅ PostgresFSMStorage: состояния FSM сохраняются в БД")
    else:
        fsm_storage = MemoryStorage()
        logger.info("⚠️  MemoryStorage: состояния FSM в памяти (потеряются при перезапуске)")

    # 3) Метрики Prometheus (поднимаем легкий HTTP-сервер на отдельном порту)
    try:
        start_metrics(settings.METRICS_PORT)
        logger.info("Метрики Prometheus доступны на http://localhost:%d/", settings.METRICS_PORT)
    except Exception as e:
        logger.warning("Не удалось запустить сервер метрик: %s", e)

    # 4) Планировщик задач (рассылки и периодические задания)
    scheduler = AsyncIOScheduler(timezone=settings.APSCHEDULER_TIMEZONE)
    # Фоновый экспорт в Google Sheets
    if settings.SHEETS_EXPORT_ENABLED and ExportSettings and export_once:
        try:
            export_settings = ExportSettings()
            interval = max(30, int(export_settings.EXPORT_INTERVAL_SECONDS))
            async def export_job():
                try:
                    await export_once(export_settings)
                except Exception as e:
                    logger = logging.getLogger("sheets_export")
                    logger.warning(f"Ошибка фонового экспорта: {e}")
            # Первый запуск сразу после старта
            asyncio.create_task(export_job())
            # Периодический запуск через APScheduler
            scheduler.add_job(export_job, "interval", seconds=interval, id="sheets_export")
        except Exception as e:
            logger = logging.getLogger("sheets_export")
            logger.warning(f"Экспортёр Google Sheets не инициализирован: {e}")
    scheduler.start()
    logger.info("Планировщик APScheduler запущен")

    # 5) Инициализация aiogram (Bot, Dispatcher, Routers)
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=fsm_storage)
    # Global middlewares: errors and roles context
    dp.update.outer_middleware(ErrorsMiddleware())
    dp.update.outer_middleware(RolesMiddleware())
    # Ensure per-pipeline coverage
    dp.message.outer_middleware(ErrorsMiddleware())
    dp.message.outer_middleware(RolesMiddleware())
    dp.callback_query.outer_middleware(ErrorsMiddleware())
    dp.callback_query.outer_middleware(RolesMiddleware())

    # Подключаем роутеры
    dp.include_router(auth_router)
    dp.include_router(help_router)
    dp.include_router(case_fb_employee_router)
    dp.include_router(case_fb_peer_router)
    dp.include_router(case_career_dialog_router)
    dp.include_router(nav_router)
    dp.include_router(rating_router)
    # Должен идти последним: catch-all хэндлеры
    dp.include_router(fallback_router)

    # Обработчик сигналов для graceful shutdown
    def handle_signal(signum, frame):
        logger.info(f"Получен сигнал {signum}, запуск graceful shutdown...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        if settings.WEBHOOK_ENABLED and settings.WEBHOOK_HOST:
            # WEBHOOK MODE (Production)
            logger.info("Запуск в режиме webhook")
            
            # Устанавливаем webhook
            webhook_url = f"{settings.WEBHOOK_HOST.rstrip('/')}{settings.WEBHOOK_PATH}"
            await bot.set_webhook(
                url=webhook_url,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=False,  # Не теряем сообщения при деплое
            )
            logger.info(f"Webhook установлен: {webhook_url}")

            # Создаём aiohttp приложение
            app = web.Application()
            
            # Добавляем health check endpoint
            app.router.add_get("/health", health_check)
            app.router.add_get("/", health_check)  # Для проверки доступности
            
            # Настраиваем webhook handler
            webhook_handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
            )
            webhook_handler.register(app, path=settings.WEBHOOK_PATH)
            
            # Запускаем сервер
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", settings.WEBHOOK_PORT)
            await site.start()
            
            logger.info(f"Webhook сервер запущен на порту {settings.WEBHOOK_PORT}")
            logger.info(f"Health check доступен на http://0.0.0.0:{settings.WEBHOOK_PORT}/health")
            
            # Ждём сигнала остановки
            await shutdown_event.wait()
            
            logger.info("Начинаем graceful shutdown...")
            await runner.cleanup()
            await bot.delete_webhook(drop_pending_updates=False)
            
        else:
            # POLLING MODE (Development)
            logger.info("Запуск в режиме polling (dev)")
            
            # Удаляем webhook если был установлен
            await bot.delete_webhook(drop_pending_updates=False)
            
            # Запускаем polling с graceful shutdown
            polling_task = asyncio.create_task(
                dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                )
            )
            
            # Ждём сигнала остановки
            shutdown_task = asyncio.create_task(shutdown_event.wait())
            done, pending = await asyncio.wait(
                [polling_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем оставшиеся задачи
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
            logger.info("Polling остановлен")
            
    finally:
        # Корректное завершение при остановке
        logger.info("Завершение работы компонентов...")
        scheduler.shutdown(wait=False)
        try:
            await dp.storage.close()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии storage: {e}")
        try:
            await bot.session.close()
        except Exception as e:
            logger.warning(f"Ошибка при закрытии bot session: {e}")
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # Нормальное завершение по Ctrl+C / сигналы ОС
        pass