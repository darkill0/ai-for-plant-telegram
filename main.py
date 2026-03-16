import os
import logging
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, Update

from config import TELEGRAM_TOKEN
from plant_recognition import recognize_plant, check_remaining_requests
from ai_advice import get_plant_advice


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


BASE_WEBHOOK_PATH = f"/webhook/{TELEGRAM_TOKEN}"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-secret")


bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


TEMP_DIR = Path("/tmp/plant_bot")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.message(CommandStart())
async def start_handler(message: Message):

    text = (
        "🌿 Бот для распознавания растений\n\n"
        "Отправьте:\n"
        "• фото растения\n"
        "или\n"
        "• название растения"
    )

    await message.answer(text)


@router.message()
async def message_handler(message: Message):

    # Обработка текстового запроса
    if message.text:

        plant = message.text.strip()

        await message.answer(f"🔎 Ищу информацию о: {plant}")

        advice = get_plant_advice(plant)

        await message.answer(advice)

        return


    # Обработка фото
    if message.photo:

        msg = await message.answer("📷 Анализирую фото растения...")
        temp_path = None

        try:

            photo = message.photo[-1]

            with tempfile.NamedTemporaryFile(
                dir=TEMP_DIR,
                suffix=".jpg",
                delete=False
            ) as tmp:

                temp_path = tmp.name


            file = await bot.get_file(photo.file_id)

            await bot.download_file(
                file.file_path,
                destination=temp_path
            )


            result = recognize_plant(temp_path)

            plant = result.get("name", "Неизвестно")
            probability = result.get("probability", 0)

            text = (
                f"🌱 Растение: {plant}\n"
                f"🎯 Точность: {round(probability * 100)}%"
            )

            await msg.edit_text(text)

            advice = get_plant_advice(plant)

            await message.answer(advice)

        except Exception as e:

            logger.error(f"Ошибка обработки фото: {e}")

            await msg.edit_text("❌ Ошибка анализа фотографии")

        finally:

            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)


@asynccontextmanager
async def lifespan(app: FastAPI):

    webhook_url = (
        f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
        f"{BASE_WEBHOOK_PATH}"
    )

    await bot.set_webhook(
        url=webhook_url,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )

    logger.info(f"Webhook установлен: {webhook_url}")

    yield

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Webhook удалён")


app = FastAPI(lifespan=lifespan)


@app.post(BASE_WEBHOOK_PATH)
async def telegram_webhook(request: Request):

    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        raise HTTPException(status_code=403)

    data = await request.json()

    update = Update.model_validate(data)

    await dp.feed_update(bot, update)

    return {"ok": True}


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