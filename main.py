import os
import logging
from pathlib import Path
import tempfile
from fastapi import FastAPI, Request, HTTPException
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from contextlib import asynccontextmanager
from config import TELEGRAM_TOKEN
from plant_recognition import recognize_plant, check_remaining_requests
from ai_advice import get_plant_advice

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BASE_WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-very-long-random-secret-string")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

TEMP_DIR = Path("/tmp/plant_bot")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

@router.message(CommandStart())
async def start_handler(message: Message):
    text = "🌿 Бот для растений\nОтправьте фото растения\nили название растения"
    await message.answer(text)

@router.message()
async def message_handler(message: Message):
    if message.text:
        plant = message.text.strip()
        await message.answer(f"Ищу информацию о {plant}")
        advice = get_plant_advice(plant)
        await message.answer(advice)
        return

    if message.photo:
        msg = await message.answer("Анализирую фото...")
        temp_path = None
        try:
            photo = message.photo[-1]
            with tempfile.NamedTemporaryFile(dir=TEMP_DIR, suffix=".jpg", delete=False) as tmp:
                temp_path = tmp.name
            await photo.download(destination=temp_path)

            result = recognize_plant(temp_path)
            plant = result.get("name", "Неизвестно")
            probability = result.get("probability", 0)
            text = f"Растение: {plant}\nТочность: {round(probability * 100)}%"
            await msg.edit_text(text)

            advice = get_plant_advice(plant)
            await message.answer(advice)
        except Exception as e:
            logger.error(f"Ошибка обработки фото: {e}")
            await msg.edit_text("Ошибка анализа фото")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

app = FastAPI(lifespan=lifespan)

@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{BASE_WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )
    yield
    await bot.delete_webhook(drop_pending_updates=True)

app.mount(BASE_WEBHOOK_PATH, handler)

handler = SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
    secret_token=WEBHOOK_SECRET
)

setup_application(app, dp, bot=bot)

@app.get("/")
async def root():
    stats = check_remaining_requests()
    used = stats.get("used", 0)
    remaining = stats.get("remaining", 0)
    return {
        "status": "active",
        "used_today": used,
        "remaining": remaining
    }