#!/usr/bin/env python3
"""
Диагностический скрипт для тестирования транскрибации аудио.

Использование:
    python test_transcription.py
    
Примеры с параметрами:
    python test_transcription.py --file "путь/к/файлу.ogg"
    python test_transcription.py --model "gpt-4o-transcribe"
    python test_transcription.py --language "en" --temperature 0.2
    python test_transcription.py --prompt "Разговор о работе, техника, экскаватор"
    
Доступные параметры:
    --file/-f       Путь к аудиофайлу
    --model/-m      Модель (whisper-1, gpt-4o-transcribe)
    --language/-l   Язык (ru, en, и др. в формате ISO-639-1)
    --prompt/-p     Контекстная подсказка (до 224 токенов)
    --temperature/-t Температура 0.0-1.0 (0.0=детерминированно, 1.0=креативно)
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from io import BytesIO

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from app.config.settings import Settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Путь к аудиофайлу по умолчанию
DEFAULT_AUDIO_FILE = r"C:\Users\Александр\Downloads\audio_2025-10-27_12-57-31.ogg"

# Модель по умолчанию (как в боте)
DEFAULT_MODEL = "gpt-4o-transcribe"


async def transcribe_audio_file(
    file_path: str, 
    model: str = DEFAULT_MODEL,
    language: str = "ru",
    prompt: str = None,
    temperature: float = 0.9
) -> str:
    """
    Транскрибирует аудиофайл через OpenAI API.
    
    Args:
        file_path: Путь к аудиофайлу
        model: Модель для транскрибации
        language: Язык аудио (ISO-639-1, например "ru")
        prompt: Контекстная подсказка для модели (до 224 токенов)
        temperature: Температура выборки (0.0-1.0, влияет на детерминированность)
        
    Returns:
        Транскрибированный текст
    """
    try:
        # Проверяем существование файла
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
            
        # Читаем файл в память
        with open(file_path, "rb") as f:
            audio_data = f.read()
            
        logger.info(f"Файл загружен: {file_path} ({len(audio_data)} байт)")
        
        # Создаем BytesIO объект
        bytes_io = BytesIO(audio_data)
        
        # Получаем настройки
        settings = Settings()
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY не настроен в .env файле")
            
        # Создаем клиент OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        logger.info(f"Отправляем на транскрибацию (модель: {model})...")
        
        # Синхронная функция для выполнения в executor
        def _sync_transcribe():
            bytes_io.seek(0)
            # Определяем расширение файла для MIME-type
            file_ext = Path(file_path).suffix.lower()
            mime_types = {
                '.ogg': 'audio/ogg',
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.m4a': 'audio/m4a',
                '.mp4': 'audio/mp4',
                '.webm': 'audio/webm'
            }
            mime_type = mime_types.get(file_ext, 'audio/ogg')
            
            # Формируем tuple для передачи файла
            file_tuple = (f"audio{file_ext}", bytes_io, mime_type)
            
            # Формируем параметры запроса
            params = {
                "model": model,
                "file": file_tuple,
                "response_format": "text",
                "language": language,
                "temperature": temperature
            }
            
            # Добавляем prompt если указан
            if prompt:
                params["prompt"] = prompt
                
            result = client.audio.transcriptions.create(**params)
            
            # Обрабатываем результат
            if isinstance(result, str):
                return result
            else:
                # Если результат объект, извлекаем текст
                text = getattr(result, "text", None)
                if not text and isinstance(result, dict):
                    text = result.get("text")
                return text or ""
        
        # Выполняем в executor для асинхронности
        loop = asyncio.get_event_loop()
        transcribed_text = await loop.run_in_executor(None, _sync_transcribe)
        
        logger.info("Транскрибация завершена успешно!")
        return transcribed_text.strip()
        
    except Exception as e:
        logger.error(f"Ошибка транскрибации: {e} ({type(e).__name__})")
        return ""


async def main():
    """Главная функция скрипта."""
    parser = argparse.ArgumentParser(
        description="Диагностический скрипт для тестирования транскрибации аудио"
    )
    parser.add_argument(
        "--file", "-f",
        default=DEFAULT_AUDIO_FILE,
        help=f"Путь к аудиофайлу (по умолчанию: {DEFAULT_AUDIO_FILE})"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Модель для транскрибации (по умолчанию: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--language", "-l",
        default="ru",
        help="Язык аудио в формате ISO-639-1 (по умолчанию: ru)"
    )
    parser.add_argument(
        "--prompt", "-p",
        default=None,
        help="Контекстная подсказка для модели (до 224 токенов)"
    )
    parser.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.0,
        help="Температура выборки 0.0-1.0 (по умолчанию: 0.0)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎤 ДИАГНОСТИКА ТРАНСКРИБАЦИИ АУДИО")
    print("=" * 60)
    print(f"Файл: {args.file}")
    print(f"Модель: {args.model}")
    print(f"Язык: {args.language}")
    print(f"Температура: {args.temperature}")
    if args.prompt:
        print(f"Подсказка: {args.prompt}")
    print("-" * 60)
    
    # Выполняем транскрибацию
    result = await transcribe_audio_file(
        args.file, 
        args.model, 
        args.language, 
        args.prompt, 
        args.temperature
    )
    
    print("\n📝 РЕЗУЛЬТАТ ТРАНСКРИБАЦИИ:")
    print("-" * 60)
    if result:
        print(f'"{result}"')
        print(f"\nДлина текста: {len(result)} символов")
    else:
        print("❌ Транскрибация не удалась или вернула пустой результат")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)
