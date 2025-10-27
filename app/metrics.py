from prometheus_client import Counter, Histogram, start_http_server
import time
from functools import wraps
from typing import Any, Callable, Awaitable

try:
    # Опциональный импорт для определения типов; если недоступен, используем утиную типизацию
    from aiogram.types import Message, CallbackQuery  # type: ignore
except Exception:  # pragma: no cover - безопасный фолбэк если aiogram не импортирован
    Message = None  # type: ignore
    CallbackQuery = None  # type: ignore

# Публичные объекты метрик
METRIC_UPDATES_TOTAL = Counter(
    "bot_updates_total",
    "Количество обработанных апдейтов Telegram",
)

METRIC_HANDLER_LATENCY = Histogram(
    "bot_handler_latency_seconds",
    "Время обработки хэндлеров",
    buckets=(0.01, 0.05, 0.1, 0.3, 1, 3, 10),
)

# Метрики с указаниями для наблюдаемости по кейсам/шагам/типам
HANDLER_UPDATES = Counter(
    "bot_handler_updates_total",
    "Количество обработанных апдейтов по кейсам/шагам",
    ["case", "step", "type"],
)

HANDLER_LATENCY_LABELED = Histogram(
    "bot_handler_latency_seconds_labeled",
    "Время обработки хэндлеров по кейсам/шагам",
    ["case", "step", "type"],
    buckets=(0.01, 0.05, 0.1, 0.3, 1, 3, 10),
)

# Метрики валидации входных данных
VALIDATION_ERRORS_TOTAL = Counter(
    "bot_validation_errors_total",
    "Общее количество ошибок валидации входных данных",
    ["error_type", "input_type"],
)

INPUT_SIZE_HISTOGRAM = Histogram(
    "bot_input_size_bytes",
    "Распределение размеров входных данных",
    ["input_type"],
    buckets=(100, 500, 1000, 2000, 5000, 10000, 25000, 50000, 100000),
)

RATE_LIMIT_BLOCKS_TOTAL = Counter(
    "bot_rate_limit_blocks_total", 
    "Количество заблокированных запросов по rate limit",
    ["limit_type"],
)


def start_metrics(port: int) -> None:
    """Запускает HTTP-сервер Prometheus на указанном порту."""
    start_http_server(port)


def _detect_event_type(*args: Any, **kwargs: Any) -> str:
    """Попытка определить тип события для подписей метрик."""
    # Сначала проверяем kwargs
    for key in ("message", "callback_query", "event"):
        obj = kwargs.get(key)
        if obj is not None:
            return _map_obj_to_type(obj)

    # Фолбэк: сканируем позиционные аргументы
    for obj in args:
        t = _map_obj_to_type(obj)
        if t != "other":
            return t
    return "other"


def _map_obj_to_type(obj: Any) -> str:
    try:
        if Message is not None and isinstance(obj, Message):
            return "message"
        if CallbackQuery is not None and isinstance(obj, CallbackQuery):
            return "callback_query"
    except Exception:
        pass
    # Утиная типизация как фолбэк
    if hasattr(obj, "text"):
        return "message"
    if hasattr(obj, "data") and hasattr(obj, "message"):
        return "callback_query"
    return "other"


def measure(case: str, step: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """Декоратор для сбора метрик по хэндлерам.

    - Увеличивает глобальный счётчик METRIC_UPDATES_TOTAL
    - Увеличивает метрику HANDLER_UPDATES с указаниями case/step/type
    - Наблюдает за задержкой в HANDLER_LATENCY_LABELED
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            ev_type = _detect_event_type(*args, **kwargs)
            METRIC_UPDATES_TOTAL.inc()
            labels = {"case": case, "step": step, "type": ev_type}
            HANDLER_UPDATES.labels(**labels).inc()
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                HANDLER_LATENCY_LABELED.labels(**labels).observe(elapsed)

        return wrapper

    return decorator
