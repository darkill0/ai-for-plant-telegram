import requests
import base64
import os
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PLANT_ID_URL = "https://api.kindwise.com/v1/identification"  # актуальный эндпоинт v3 по состоянию на 2026
PLANT_ID_API_KEY = "kQyHiDnUA8TbpdXrkY1OWk7Kx2HqZmrCffYyMT4V6PSh24Lyp2"

request_count = 0
last_reset_day = time.strftime("%Y-%m-%d")

def recognize_plant(image_path):
    global request_count, last_reset_day
    
    current_day = time.strftime("%Y-%m-%d")
    if current_day != last_reset_day:
        request_count = 0
        last_reset_day = current_day
        logger.info("Новый день, счетчик сброшен")
    
    if not os.path.exists(image_path):
        logger.error(f"Файл не найден: {image_path}")
        return {"name": "Файл не найден", "probability": 0}
    
    if not PLANT_ID_API_KEY:
        logger.error("API ключ Plant.id не настроен")
        return {"name": "Ошибка API", "probability": 0}
    
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        payload = {
            "images": [image_base64],
            "modifiers": ["crops_fast", "similar_images"],
            "plant_language": "ru",
            "plant_details": ["common_names", "url", "name_authority", "wiki_description", "taxonomy"]
        }
        
        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Отправка запроса к Plant.id API v3, файл: {image_path}, размер: {os.path.getsize(image_path)} байт")
        start_time = time.time()
        
        response = requests.post(
            PLANT_ID_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Ответ получен за {elapsed_time:.2f} секунд, статус: {response.status_code}")
        
        if response.status_code == 200:
            request_count += 1
            result = response.json()
            
            if result.get("result") and result["result"].get("is_plant") and result["result"].get("classification"):
                suggestions = result["result"]["classification"]
                if suggestions:
                    best_match = suggestions[0]
                    plant_name = best_match.get("name", "Неизвестное растение")
                    probability = best_match.get("score", 0)
                    
                    common_names = best_match.get("details", {}).get("common_names", [])
                    
                    logger.info(f"Распознано: {plant_name} с вероятностью {probability:.2f}")
                    
                    return {
                        "name": plant_name,
                        "probability": probability,
                        "common_names": common_names[:5],
                        "all_suggestions": [s["name"] for s in suggestions[:3]]
                    }
            logger.warning("Растение не распознано или результат пустой")
            return {"name": "Неизвестное растение", "probability": 0}
            
        elif response.status_code == 401:
            logger.error(f"Ошибка аутентификации: {response.text}")
            return {"name": "Ошибка аутентификации API", "probability": 0}
        elif response.status_code == 429:
            logger.error("Превышен лимит запросов")
            return {"name": "Превышен лимит запросов", "probability": 0}
        else:
            logger.error(f"Ошибка API: {response.status_code} - {response.text[:200]}")
            return {"name": f"Ошибка API {response.status_code}", "probability": 0}
            
    except requests.exceptions.Timeout:
        logger.error("Таймаут при запросе к Plant.id API")
        return {"name": "Таймаут запроса", "probability": 0}
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка соединения с Plant.id API")
        return {"name": "Ошибка сети", "probability": 0}
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return {"name": f"Ошибка: {str(e)[:50]}", "probability": 0}