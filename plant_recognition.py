import requests
import base64
import os
import time
import logging

logger = logging.getLogger(__name__)

PLANT_ID_URL = "https://api.plant.id/v3/identification"
PLANT_ID_API_KEY = "kQyHiDnUA8TbpdXrkY1OWk7Kx2HqZmrCffYyMT4V6PSh24Lyp2"

request_count = 0
last_reset_day = time.strftime("%Y-%m-%d")


def recognize_plant(image_path):
    global request_count, last_reset_day

    current_day = time.strftime("%Y-%m-%d")
    if current_day != last_reset_day:
        request_count = 0
        last_reset_day = current_day
        logger.info("Счетчик запросов сброшен — новый день")

    if not os.path.exists(image_path):
        logger.error(f"Файл отсутствует: {image_path}")
        return {"name": "Файл не найден", "probability": 0}

    if not PLANT_ID_API_KEY:
        logger.error("Отсутствует API-ключ Plant.id")
        return {"name": "Ошибка конфигурации API", "probability": 0}

    try:
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "images": [image_base64],
            "similar_images": True
        }

        params = {
            "details": "common_names,url,name_authority,wiki_description,taxonomy,synonyms"
        }

        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }

        logger.info(f"Запрос к Plant.id API v3 → {image_path}")
        start = time.time()

        response = requests.post(
            PLANT_ID_URL,
            json=payload,
            params=params,
            headers=headers,
            timeout=30
        )

        elapsed = time.time() - start
        logger.info(f"Ответ получен за {elapsed:.2f} с, код: {response.status_code}")

        if response.status_code != 200:
            if response.status_code == 400:
                logger.error(f"Ошибка 400: {response.text.strip()}")
                return try_minimal_request(image_path)
            if response.status_code == 401:
                logger.error("Ошибка аутентификации")
                return {"name": "Неверный API-ключ", "probability": 0}
            if response.status_code == 429:
                logger.error("Превышен лимит запросов")
                return {"name": "Лимит запросов исчерпан", "probability": 0}
            logger.error(f"Необработанная ошибка {response.status_code}: {response.text[:180]}")
            return {"name": f"Ошибка API {response.status_code}", "probability": 0}

        request_count += 1
        data = response.json()

        result = data.get("result", {})
        is_plant_prob = result.get("is_plant", {}).get("probability", 0)

        if is_plant_prob <= 0.5:
            logger.warning(f"Объект не является растением (вероятность {is_plant_prob:.2f})")
            return {
                "name": "Не является растением",
                "probability": 0,
                "is_plant_probability": is_plant_prob
            }

        suggestions = result.get("classification", {}).get("suggestions", [])
        if not suggestions:
            logger.warning("Отсутствуют предположения по виду")
            return {"name": "Вид не определён", "probability": 0}

        best = suggestions[0]
        name = best.get("name", "Неизвестное растение")
        prob = best.get("probability", 0)

        details = best.get("details", {})
        common_names = details.get("common_names", [])[:5]

        image_url = None
        similar = result.get("similar_images", [])
        if similar:
            image_url = similar[0].get("url")

        top_suggestions = [
            {"name": s.get("name", ""), "probability": s.get("probability", 0)}
            for s in suggestions[:3] if s.get("name")
        ]

        logger.info(f"Опознано: {name} ({prob:.2f})")

        return {
            "name": name,
            "probability": prob,
            "common_names": common_names,
            "all_suggestions": [s["name"] for s in top_suggestions],
            "suggestions_with_prob": top_suggestions,
            "image_url": image_url,
            "is_plant_probability": is_plant_prob
        }

    except requests.exceptions.Timeout:
        logger.error("Таймаут запроса к Plant.id")
        return {"name": "Таймаут запроса", "probability": 0}
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка соединения с Plant.id")
        return {"name": "Ошибка сети", "probability": 0}
    except Exception as e:
        logger.exception("Неожиданное исключение в recognize_plant")
        return {"name": "Системная ошибка распознавания", "probability": 0}


def try_minimal_request(image_path):
    try:
        logger.info("Повторная попытка — минимальный запрос")

        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {"images": [image_base64]}
        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }

        response = requests.post(
            PLANT_ID_URL,
            json=payload,
            headers=headers,
            timeout=25
        )

        if response.status_code != 200:
            logger.error(f"Минимальный запрос завершился с кодом {response.status_code}")
            return {"name": "Не удалось распознать", "probability": 0}

        data = response.json()
        request_count += 1  # глобальная переменная

        result = data.get("result", {})
        is_plant_prob = result.get("is_plant", {}).get("probability", 0)

        if is_plant_prob <= 0.5:
            return {
                "name": "Не является растением",
                "probability": 0,
                "is_plant_probability": is_plant_prob
            }

        suggestions = result.get("classification", {}).get("suggestions", [])
        if not suggestions:
            return {"name": "Вид не определён", "probability": 0}

        best = suggestions[0]
        return {
            "name": best.get("name", "Неизвестное растение"),
            "probability": best.get("probability", 0),
            "common_names": [],
            "all_suggestions": [
                s.get("name", "") for s in suggestions[:3] if s.get("name")
            ],
            "is_plant_probability": is_plant_prob
        }

    except Exception as e:
        logger.error(f"Ошибка минимального запроса: {e}")
        return {"name": "Ошибка распознавания", "probability": 0}


def check_remaining_requests():
    current_day = time.strftime("%Y-%m-%d")
    if current_day != last_reset_day:
        request_count = 0
        last_reset_day = current_day

    remaining = max(0, 100 - request_count)
    logger.info(f"Запросов сегодня: {request_count} / 100")

    return {
        "used": request_count,
        "remaining": remaining,
        "reset_day": current_day,
        "limit": 100
    }


def test_api_connection():
    try:
        payload = {"images": ["invalid_test_string"]}
        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }

        r = requests.post(
            PLANT_ID_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        if r.status_code in (400, 401):
            logger.info(f"API доступен (ожидаемый код {r.status_code})")
            return r.status_code == 400

        logger.info(f"Неожиданный код при тесте: {r.status_code}")
        return r.status_code < 500

    except Exception as e:
        logger.error(f"Тест соединения завершился ошибкой: {e}")
        return False