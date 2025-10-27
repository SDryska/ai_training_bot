# AI Провайдеры

## OpenAI

**Конфигурация:**
```
OPENAI_API_KEY=sk-...
```

**Модели:**
- gpt-5 - ревьювер
- gpt-5-mini - диалоги

**Аудио:**
- Формат: MP3, MP4, MPEG, MPGA, M4A, OGG, FLAC, WAV, WEBM
- Макс. размер: 25 МБ
- Транскрибация: gpt-4o-transcribe

---

## Google Gemini

**Конфигурация:**
```
GEMINI_API_KEY=your-google-api-key
```
Получить: https://aistudio.google.com/apikey

**Модели:**
- gemini-2.5-flash 

**Аудио:**
- Формат: audio/wav, audio/mp3, audio/aac, audio/ogg, audio/flac
- Макс. размер: 20 МБ
- Макс. длина: 15 минут
- Встроенное распознавание

---

## Использование в коде

**OpenAI:**
```python
from app.providers.base import ProviderType

response = await ai_gateway.send_message(
    user_id=user_id,
    message=message,
    system_prompt=system_prompt,
    provider_type=ProviderType.OPENAI,
    model_override="gpt-5-mini"
)
```

**Gemini:**
```python
response = await ai_gateway.send_message(
    user_id=user_id,
    message=message,
    system_prompt=system_prompt,
    provider_type=ProviderType.GEMINI,
    model_override="gemini-2.0-flash"
)
```

**Gemini с аудио:**
```python
from io import BytesIO

file = await message.bot.get_file(message.voice.file_id)
buffer = BytesIO()
await message.bot.download(file, buffer)

response = await ai_gateway.send_message(
    user_id=user_id,
    message="Распознай это аудио",
    system_prompt=system_prompt,
    provider_type=ProviderType.GEMINI,
    audio_bytes=buffer
)
```

---

## Зависимости

```bash
pip install openai>=1.0
pip install google-generativeai>=0.3
pip install -r requirements.txt
```

---

## Отладка

**Доступные провайдеры:**
```python
available_providers = gateway.get_available_providers()
print([p.value for p in available_providers])
```

**Логи:**
```python
import logging
logging.getLogger("app.providers.gemini").setLevel(logging.DEBUG)
```

**Тест:**
```python
from app.services.ai_service import initialize_ai_providers, get_ai_gateway

initialize_ai_providers()
gateway = get_ai_gateway()

response = await gateway.send_message(
    user_id=123,
    message="Hello",
    system_prompt="You are a helpful assistant"
)
```
