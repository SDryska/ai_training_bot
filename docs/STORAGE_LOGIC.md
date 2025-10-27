# Логика хранения диалогов и FSM состояний

## Архитектура

Бот использует два типа хранилищ:

1. **ConversationStorage** — для истории диалогов с AI
2. **FSM Storage** — для состояний aiogram (FSM states, user data)

Оба хранилища поддерживают PostgreSQL (продакшн) и in-memory fallback (dev/тесты).

### Таблица `conversations`

```sql
CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    provider_type VARCHAR(50) NOT NULL,  -- 'openai', 'gemini'
    role VARCHAR(50) NOT NULL,           -- 'system', 'user', 'assistant'
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ              -- NULL = активная сессия
);

CREATE INDEX idx_conversations_user_provider 
ON conversations (user_id, provider_type, finished_at, created_at);
```

### Таблица `fsm_storage`

```sql
CREATE TABLE fsm_storage (
    storage_key VARCHAR(255) PRIMARY KEY,  -- "bot_id:chat_id:user_id"
    bot_id BIGINT,
    chat_id BIGINT,
    user_id BIGINT,
    state VARCHAR(255),                    -- FSM состояние (например, "AIChat:waiting_user")
    data JSONB NOT NULL DEFAULT '{}',      -- Данные пользователя (turn_count, dialogue_entries и т.д.)
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fsm_storage_user 
ON fsm_storage (user_id, updated_at);
```

**Что хранится в `data`:**
- `turn_count` — количество ходов в диалоге
- `dialogue_entries` — история диалога для анализа
- `total_provd_achieved` — достигнутые компоненты ПРОВД
- Другие данные состояния из `FSMContext`

## Жизненный цикл сессии

### 1. Активная сессия
- `finished_at IS NULL` — сессия активна
- Все сообщения с `finished_at IS NULL` загружаются при старте диалога
- При перезапуске бота история восстанавливается из БД

### 2. Завершение сессии
Сессия помечается как завершённая (`finished_at = NOW()`) в следующих случаях:

#### a) Старт нового кейса
- Команды: `/career`, `/fbpeer`, `/fbemployee`
- Кнопка: "Начать диалог"
- Функция: `clear_case_conversations(case_id, user_id)`

#### b) Перезапуск текущего кейса
- Кнопка: "Начать заново" (restart)
- Функция: `clear_case_conversations(case_id, user_id)`

#### c) Возврат в главное меню
- Команда: `/start`
- Кнопка: "Главное меню" (из диалога)
- Кнопка: "Главное меню" (из навигации)
- Функция: `clear_all_conversations(user_id)` — очищает ВСЕ провайдеры

#### d) После получения анализа
- Reviewer сессия очищается сразу после генерации анализа
- Основная сессия пользователя остаётся активной (пользователь может продолжить)

## Функции очистки

### `clear_case_conversations(case_id: str, user_id: int)`
Очищает историю для всех провайдеров, связанных с конкретным кейсом:
- dialogue.primary / dialogue.fallback
- reviewer.primary / reviewer.fallback

### `clear_all_conversations(user_id: int)`
Очищает историю для ВСЕХ доступных провайдеров (OpenAI, Gemini, и т.д.).
Используется при полном выходе из диалогов (возврат в главное меню, `/start`).

## Восстановление после перезапуска

### История диалогов (ConversationStorage)

1. Бот перезапускается (деплой, рестарт)
2. Пользователь отправляет сообщение
3. Провайдер загружает историю из БД:
   ```sql
   SELECT role, content, metadata
   FROM conversations
   WHERE user_id = $1 AND provider_type = $2 AND finished_at IS NULL
   ORDER BY created_at ASC
   ```
4. Диалог продолжается с того же места

### FSM состояния (PostgresFSMStorage)

1. Бот перезапускается
2. Пользователь отправляет сообщение
3. aiogram автоматически загружает состояние из БД:
   ```sql
   SELECT state, data
   FROM fsm_storage
   WHERE storage_key = $1
   ```
4. FSM состояние и данные (`turn_count`, `dialogue_entries` и т.д.) восстанавливаются
5. Пользователь может продолжить диалог с того же места

**Важно:** Оба хранилища работают независимо:
- `conversations` — для контекста AI (история сообщений)
- `fsm_storage` — для состояния бота (FSM state, счётчики, временные данные)

## Конфигурация

### PostgreSQL (продакшн)
```python
# .env
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Автоматически используется:
# - PostgresStorage для истории диалогов
# - PostgresFSMStorage для FSM состояний
```

### In-Memory (dev/тесты)
```python
# .env без DATABASE_URL

# Автоматически используется:
# - InMemoryStorage для истории диалогов
# - MemoryStorage для FSM состояний
# ⚠️ Всё теряется при перезапуске
```

### Режим работы на проде (webhook)

При работе через webhook состояния сохраняются в PostgreSQL:
- Бот может перезапускаться без потери активных диалогов
- Пользователи могут продолжить диалог после деплоя
- Graceful shutdown сохраняет все состояния перед остановкой

### Режим работы локально (polling)

При работе через polling:
- С `DATABASE_URL`: состояния сохраняются в PostgreSQL
- Без `DATABASE_URL`: состояния в памяти (теряются при Ctrl+C)

## Retention Policy

Старые завершённые сессии можно удалять через cron:
```sql
-- Удаление старых диалогов
DELETE FROM conversations
WHERE finished_at < NOW() - INTERVAL '30 days';

-- Удаление старых FSM состояний (неактивные более 7 дней)
DELETE FROM fsm_storage
WHERE updated_at < NOW() - INTERVAL '7 days';
```

## Миграция

Обе таблицы создаются автоматически при старте бота через Alembic:
1. При запуске бота вызывается `run_migrations()` из `app/services/auth.py`
2. Alembic выполняет `alembic upgrade head`
3. Миграция `b66012ceafd1_initial_schema.py` создаёт таблицы `conversations` и `fsm_storage`

**Требования:** убедитесь, что установлены:
```bash
pip install alembic sqlalchemy
# или
pip install -r requirements.txt
```

## Тестирование восстановления сессий

### Сценарий 1: Перезапуск бота во время диалога

1. Запустите бота с `DATABASE_URL`
2. Начните диалог (например, `/fbpeer` → "Начать диалог")
3. Отправьте несколько сообщений
4. Остановите бота (Ctrl+C)
5. Запустите бота снова
6. Отправьте сообщение — диалог должен продолжиться

### Сценарий 2: Проверка состояния в БД

```sql
-- Посмотреть активные FSM состояния
SELECT user_id, state, data, updated_at
FROM fsm_storage
ORDER BY updated_at DESC;

-- Посмотреть активные диалоги
SELECT user_id, provider_type, COUNT(*) as msg_count
FROM conversations
WHERE finished_at IS NULL
GROUP BY user_id, provider_type;
```

### Что должно восстановиться:

✅ FSM состояние (например, `AIChat:waiting_user`)  
✅ Данные диалога (`turn_count`, `dialogue_entries`)  
✅ История сообщений AI (контекст диалога)  
✅ Достигнутые компоненты ПРОВД (`total_provd_achieved`)  

### Что НЕ восстанавливается:

❌ Временные сообщения с индикатором печати  
❌ Inline-кнопки (их ID не сохраняются)  
❌ Состояние клавиатуры (reply keyboard)
