import requests
import base64
import os
import time
import logging
from pathlib import Path

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
        
        # ИСПРАВЛЕНО: используем правильные параметры для v3 API
        payload = {
            "images": [image_base64],
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
            
            # Логируем полный ответ для отладки
            logger.debug(f"Полный ответ API: {result}")
            
            # Правильная обработка ответа v3 API
            if result.get("result"):
                # Проверяем, является ли объект растением
                if result["result"].get("is_plant", {}).get("binary", False):
                    classification = result["result"].get("classification", {})
                    suggestions = classification.get("suggestions", [])
                    
                    if suggestions:
                        best_match = suggestions[0]
                        plant_name = best_match.get("name", "Неизвестное растение")
                        probability = best_match.get("probability", 0)
                        
                        plant_details = best_match.get("plant_details", {})
                        common_names = plant_details.get("common_names", [])
                        
                        # Получаем URL изображения если есть
                        image_url = None
                        if result.get("images") and len(result["images"]) > 0:
                            image_url = result["images"][0].get("url")
                        
                        logger.info(f"Распознано: {plant_name} с вероятностью {probability:.2f}")
                        
                        return {
                            "name": plant_name,
                            "probability": probability,
                            "common_names": common_names[:5] if common_names else [],
                            "all_suggestions": [s.get("name", "") for s in suggestions[:3] if s.get("name")],
                            "image_url": image_url
                        }
                else:
                    logger.warning("На изображении не обнаружено растение")
                    return {"name": "Не является растением", "probability": 0}
            else:
                logger.warning("Неожиданная структура ответа API")
                return {"name": "Неизвестное растение", "probability": 0}
                
            logger.warning("Растение не распознано или результат пустой")
            return {"name": "Неизвестное растение", "probability": 0}
            
        elif response.status_code == 400:
            error_text = response.text
            logger.error(f"Ошибка запроса 400: {error_text}")
            
            # Проверяем специфичную ошибку с plant_language
            if "plant_language" in error_text and "Available modifiers" in error_text:
                logger.info("Обнаружена проблема с plant_language, пробуем без языковых параметров")
                return try_without_language(image_path)
            else:
                # Пробуем упрощенный запрос без лишних параметров
                return try_simple_request(image_path)
                
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

def try_without_language(image_path):
    """Пробует запрос без параметра plant_language"""
    try:
        logger.info("Пробуем запрос без языковых параметров...")
        
        with open(image_path, "rb") as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # Запрос без plant_language
        payload = {
            "images": [image_base64],
            "plant_details": ["common_names", "url", "name_authority", "wiki_description", "taxonomy"]
        }
        
        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            PLANT_ID_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            request_count += 1
            return parse_v3_response(result)
        else:
            logger.error(f"Ошибка в запросе без языка: {response.status_code}")
            return try_simple_request(image_path)
            
    except Exception as e:
        logger.error(f"Ошибка в запросе без языка: {e}")
        return try_simple_request(image_path)

def try_simple_request(image_path):
    """Пробует отправить максимально упрощенный запрос"""
    try:
        logger.info("Пробуем упрощенный запрос...")
        
        with open(image_path, "rb") as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # Минимальный запрос
        payload = {
            "images": [image_base64]
        }
        
        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            PLANT_ID_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            request_count += 1
            return parse_v3_response(result)
        else:
            logger.error(f"Упрощенный запрос тоже не сработал: {response.status_code}")
            return {"name": "Не удалось распознать", "probability": 0}
        
    except Exception as e:
        logger.error(f"Ошибка в упрощенном запросе: {e}")
        return {"name": "Ошибка распознавания", "probability": 0}

def parse_v3_response(result):
    """Парсит ответ v3 API в единый формат"""
    try:
        if result.get("result"):
            if result["result"].get("is_plant", {}).get("binary", False):
                classification = result["result"].get("classification", {})
                suggestions = classification.get("suggestions", [])
                
                if suggestions:
                    best_match = suggestions[0]
                    plant_name = best_match.get("name", "Неизвестное растение")
                    probability = best_match.get("probability", 0)
                    
                    plant_details = best_match.get("plant_details", {})
                    common_names = plant_details.get("common_names", [])
                    
                    return {
                        "name": plant_name,
                        "probability": probability,
                        "common_names": common_names[:5] if common_names else [],
                        "all_suggestions": [s.get("name", "") for s in suggestions[:3] if s.get("name")]
                    }
            else:
                return {"name": "Не является растением", "probability": 0}
        
        return {"name": "Неизвестное растение", "probability": 0}
        
    except Exception as e:
        logger.error(f"Ошибка парсинга ответа: {e}")
        return {"name": "Ошибка обработки", "probability": 0}

def check_remaining_requests():
    global request_count, last_reset_day
    
    current_day = time.strftime("%Y-%m-%d")
    if current_day != last_reset_day:
        request_count = 0
        last_reset_day = current_day
    
    remaining = max(0, 100 - request_count)
    logger.info(f"Использовано запросов сегодня: {request_count}, осталось: {remaining}")
    
    return {
        "used": request_count,
        "remaining": remaining,
        "reset_day": current_day
    }