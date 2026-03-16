# config.py
import os
from pathlib import Path

# Определяем, где мы работаем
IS_PYTHONANYWHERE = 'PYTHONANYWHERE_DOMAIN' in os.environ

if not IS_PYTHONANYWHERE:
    # Локальная разработка - загружаем из .env файла
    from dotenv import load_dotenv
    # Ищем .env файл в текущей директории и выше
    env_path = Path('.') / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"✅ Загружен .env файл из {env_path.absolute()}")
    else:
        # Проверяем родительскую директорию
        env_path = Path('..') / '.env'
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"✅ Загружен .env файл из {env_path.absolute()}")
        else:
            print("⚠️ .env файл не найден, используем переменные окружения")

# === Токены и ключи ===

# Токен Telegram бота (обязательно замените на свой в PythonAnywhere)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8613600069:AAE9_YkVvMlJgRA9dcjw1B-07Ms5xWM10dw")

# OpenRouter API ключ (ваш существующий ключ)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")

# Plant.id API ключ (ваш существующий ключ)
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY", "kQyHiDnUA8TbpdXrkY1OWk7Kx2HqZmrCffYyMT4V6PSh24Lyp2")

# === URL и настройки API ===

# URL для OpenRouter API
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")

# Модель для OpenRouter (бесплатная)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3n-e2b-it:free")

# URL для Plant.id API
PLANT_ID_URL = "https://api.plant.id/v2/identify"

# === Настройки бота ===

# Имя бота (для логов)
BOT_NAME = "PlantNannyBot"

# Версия
VERSION = "1.0.0"

# === Настройки для PythonAnywhere ===

# Путь для временных файлов
if IS_PYTHONANYWHERE:
    # На PythonAnywhere используем /tmp
    TEMP_DIR = "/tmp/plant_bot_temp"
    print("🏠 Запуск на PythonAnywhere")
else:
    # Локально используем папку temp_images
    TEMP_DIR = "temp_images"
    print("💻 Запуск локально")

# Создаем папку для временных файлов, если её нет
os.makedirs(TEMP_DIR, exist_ok=True)

# === Лимиты API ===

# Максимальное количество запросов в день (для отслеживания)
MAX_REQUESTS_PER_DAY = 100  # Ограничение бесплатного Plant.id

# === Проверка конфигурации ===

def check_config():
    """Проверяет наличие всех необходимых ключей"""
    missing_keys = []
    
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        missing_keys.append("TELEGRAM_TOKEN")
    
    if not OPENROUTER_API_KEY:
        missing_keys.append("OPENROUTER_API_KEY")
    
    if not PLANT_ID_API_KEY:
        missing_keys.append("PLANT_ID_API_KEY")
    
    if missing_keys:
        print(f"⚠️ Отсутствуют ключи: {', '.join(missing_keys)}")
        return False
    
    print("✅ Конфигурация загружена успешно")
    print(f"📊 Модель OpenRouter: {OPENROUTER_MODEL}")
    print(f"📁 Временная папка: {TEMP_DIR}")
    return True

# Автоматическая проверка при импорте
if __name__ != "__main__":
    check_config()

# Для ручного запуска проверки
if __name__ == "__main__":
    print("=" * 50)
    print("🔧 Проверка конфигурации PlantNannyBot")
    print("=" * 50)
    
    print(f"📱 Telegram Token: {'✅ Установлен' if TELEGRAM_TOKEN != 'YOUR_TELEGRAM_BOT_TOKEN' else '❌ Не установлен'}")
    print(f"🤖 OpenRouter Key: {'✅ Установлен' if OPENROUTER_API_KEY else '❌ Не установлен'}")
    print(f"🌿 Plant.id Key: {'✅ Установлен' if PLANT_ID_API_KEY else '❌ Не установлен'}")
    print(f"🔗 OpenRouter URL: {OPENROUTER_URL}")
    print(f"📊 Модель: {OPENROUTER_MODEL}")
    print(f"📁 Temp dir: {TEMP_DIR}")
    print(f"🏠 PythonAnywhere: {'Да' if IS_PYTHONANYWHERE else 'Нет'}")
    print("=" * 50)