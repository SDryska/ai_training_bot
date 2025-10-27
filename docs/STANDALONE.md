# Standalone Скрипты

Утилиты для тестирования, анализа и обслуживания без интерфейса бота.

## Database

- **db_analyzer.py** - анализ БД, статистика, JSON-дамп
- **db_to_sheets.py** - периодический экспорт статистики в Google Sheets
- **reset_user_stats.py** - сброс статистики пользователя
- **cleanup_case_stats.py** - удаление статистики по case_id

## Testing

- **test_dialogue_models.py** - тестирование диалоговых AI моделей
- **test_transcription.py** - тестирование транскрибации аудио
- **demo_validation.py** - демо системы валидации
- **standalone_validation_test.py** - автономные тесты валидации (без API)
- **interactive_validation_test.py** - интерактивное тестирование валидации
- **test_validation.py** - тесты валидации с моками
- **test_helper.py** - просмотр/сброс данных в БД

## Запуск

```bash
cd standalone
python script_name.py
```

## Требования

Большинство скриптов требуют:
- `DATABASE_URL` - подключение к PostgreSQL
- `OPENAI_API_KEY` или `GEMINI_API_KEY` - для тестирования моделей
- `GSPREAD_SERVICE_ACCOUNT_FILE`, `GSHEETS_*` - для экспорта в Sheets

Все зависимости в `requirements.txt`
