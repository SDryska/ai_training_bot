# Деплой на Amvera

Пошаговая инструкция для развёртывания бота на Amvera с webhook режимом.

## Шаг 1: Подготовка репозитория

Убедитесь, что в репозитории есть:
- `bot.py` - точка входа
- `amvera.yml` - конфигурация для Amvera (Python 3.10)
- `requirements.txt` - зависимости
- `.env.example` - шаблон переменных окружения

Всё это уже в проекте.

## Шаг 2: Создание проекта на Amvera

1. Перейти на https://amvera.ru
2. Создать новый проект
3. Подключить GitHub репозиторий
4. Выбрать ветку (обычно `main`)
5. Amvera автоматически обнаружит `amvera.yml`

## Шаг 3: Переменные окружения

В панели Amvera добавить все переменные из `.env`:

### Обязательные

```
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
AUTH_PASSWORD_USER=your_user_password
AUTH_PASSWORD_ADMIN=your_admin_password
```

### AI Провайдеры

```
OPENAI_API_KEY=sk-your-key
GEMINI_API_KEY=your-gemini-key
```

### Webhook (обязательно для Amvera)

```
WEBHOOK_ENABLED=true
WEBHOOK_HOST=https://your-app-name.amvera.ru
WEBHOOK_PATH=/webhook
WEBHOOK_PORT=80
```

Заменить `your-app-name` на реальное имя приложения в Amvera.

### Google Sheets (опционально)

**Вариант 1: Путь к файлу**
```
GSPREAD_SERVICE_ACCOUNT_FILE=gsa.json
```
Файл `gsa.json` должен быть в корне проекта.

**Вариант 2: Base64 кодирование (рекомендуется)**

Закодировать `gsa.json` в base64:
```bash
# Linux/macOS
base64 gsa.json > gsa.b64
cat gsa.b64

# Windows PowerShell
$content = Get-Content gsa.json -Raw
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($content))
```

Добавить в Amvera:
```
GSPREAD_SERVICE_ACCOUNT_JSON_B64=your_base64_encoded_json
```

Дополнительно:
```
GSHEETS_SPREADSHEET_ID=your_spreadsheet_id
GSHEETS_SPREADSHEET_NAME=EMCO Stats
GSHEETS_SHARE_WITH=email1@example.com,email2@example.com
SHEETS_EXPORT_ENABLED=true
```

### Мониторинг (опционально)

```
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENV=production
METRICS_PORT=8000
```

## Шаг 4: Первый деплой

После добавления всех переменных:

1. Нажать "Deploy" в панели Amvera
2. Подождать сборки и запуска (1-3 минуты)
3. Проверить логи на наличие ошибок

## Шаг 5: Проверка

```bash
# Проверить health check
curl https://your-app-name.amvera.ru/health
# Должен вернуть: OK

# Проверить webhook у Telegram
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

В логах должны быть сообщения:
```
Запуск в режиме webhook
Webhook установлен: https://your-app-name.amvera.ru/webhook
Webhook сервер запущен на порту 80
```

## Шаг 6: Обновление после изменений

```bash
git add .
git commit -m "Описание изменений"
git push origin main
```

Amvera автоматически:
1. Соберёт новую версию
2. Запустит новый контейнер
3. Отправит SIGTERM старому контейнеру
4. Дождётся graceful shutdown (до 30 сек)
5. Переключит трафик

**Время простоя:** < 5 секунд
**Потеря сообщений:** 0 (Telegram хранит в очереди)

## Локальная разработка

Для локального тестирования используйте polling:

```bash
# .env
WEBHOOK_ENABLED=false
DATABASE_URL=  (пусто для MemoryStorage)
```

```bash
python bot.py
```

## Отладка

**Webhook не работает:**
1. Проверить `WEBHOOK_HOST` (полная HTTPS ссылка)
2. Проверить логи Amvera
3. Проверить firewall/DNS

**Потеря сообщений:**
- Убедиться что `drop_pending_updates=False` (уже установлено)
- Проверить логи при shutdown

**Долгое завершение:**
- Нормально! Бот завершает текущие задачи перед остановкой

**Ошибка PostgreSQL SSL: "tlsv1 alert no application protocol"**

Проблема возникает при использовании `psycopg2` с `libpq` версии 17+. Amvera требует версию 16.

**Решение (уже применено в проекте):**
1. В `requirements.txt` зафиксирована версия `psycopg2-binary==2.9.9` (libpq v16)
2. В `alembic/env.py` добавлены параметры:
   ```python
   'sslmode': 'prefer',
   'gssencmode': 'disable',  # Отключает GSS шифрование
   'connect_timeout': 30
   ```
3. В storage классах (`PostgresFSMStorage`, `PostgresStorage`) настроены SSL параметры для `asyncpg`

**Если проблема всё равно возникает:**
- Проверить, что в логах используется `psycopg2-binary==2.9.9`
- Убедиться, что переменная `DATABASE_URL` корректна
- Добавить в переменные окружения: `DATABASE_SSL_MODE=prefer`