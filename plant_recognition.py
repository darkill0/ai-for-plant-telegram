import requests
import base64
import os
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Исправленный URL для v3 API
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
        
        # ИСПРАВЛЕНО: правильные параметры для v3 API
        payload = {
            "images": [image_base64],
            "latitude": None,  # Можно добавить координаты если есть
            "longitude": None,
            "similar_images": True
        }
        
        # Добавляем параметры для детальной информации (опционально)
        # Эти параметры должны быть в правильном формате для v3 API
        details_payload = {
            "common_names": True,
            "url": True,
            "name_authority": True,
            "wiki_description": True,
            "taxonomy": True,
            "synonyms": True
        }
        
        # Объединяем параметры
        payload.update(details_payload)
        
        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Отправка запроса к Plant.id API v3, файл: {image_path}")
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
            
            # Логируем структуру ответа для отладки
            logger.debug(f"Структура ответа: {list(result.keys())}")
            
            # Обработка ответа v3 API
            if result.get("result"):
                result_data = result["result"]
                
                # Проверяем, является ли объект растением
                is_plant = result_data.get("is_plant", {})
                if is_plant.get("probability", 0) > 0.5:
                    
                    # Получаем классификацию
                    classification = result_data.get("classification", {})
                    suggestions = classification.get("suggestions", [])
                    
                    if suggestions:
                        best_match = suggestions[0]
                        plant_name = best_match.get("name", "Неизвестное растение")
                        probability = best_match.get("probability", 0)
                        
                        # Получаем детальную информацию о растении
                        plant_details = best_match.get("details", {})
                        
                        # Собираем русские названия если есть
                        common_names = []
                        if plant_details.get("common_names"):
                            # Фильтруем русские названия
                            all_names = plant_details.get("common_names", [])
                            # Ищем названия на русском или берем первые 3
                            common_names = all_names[:5] if all_names else []
                        
                        # Получаем URL похожего изображения
                        image_url = None
                        if result_data.get("similar_images"):
                            similar_images = result_data.get("similar_images", [])
                            if similar_images and len(similar_images) > 0:
                                image_url = similar_images[0].get("url")
                        
                        logger.info(f"Распознано: {plant_name} с вероятностью {probability:.2f}")
                        
                        # Собираем все предложения для контекста
                        all_suggestions = []
                        for s in suggestions[:3]:
                            if s.get("name"):
                                all_suggestions.append({
                                    "name": s.get("name"),
                                    "probability": s.get("probability", 0)
                                })
                        
                        return {
                            "name": plant_name,
                            "probability": probability,
                            "common_names": common_names,
                            "all_suggestions": [s["name"] for s in all_suggestions],
                            "suggestions_with_prob": all_suggestions,
                            "image_url": image_url,
                            "is_plant_probability": is_plant.get("probability", 0)
                        }
                    else:
                        logger.warning("Нет предположений о виде растения")
                        return {
                            "name": "Не удалось определить вид",
                            "probability": is_plant.get("probability", 0),
                            "is_plant": True
                        }
                else:
                    logger.warning(f"На изображении не растение (вероятность: {is_plant.get('probability', 0):.2f})")
                    return {
                        "name": "Не является растением",
                        "probability": 0,
                        "is_plant_probability": is_plant.get("probability", 0)
                    }
            else:
                logger.warning("Неожиданная структура ответа API")
                return {"name": "Ошибка формата ответа", "probability": 0}
                
        elif response.status_code == 400:
            error_text = response.text
            logger.error(f"Ошибка запроса 400: {error_text}")
            
            # Пробуем упрощенный запрос без дополнительных параметров
            return try_minimal_request(image_path)
            
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

def try_minimal_request(image_path):
    """Пробует минимальный запрос без дополнительных параметров"""
    try:
        logger.info("Пробуем минимальный запрос...")
        
        with open(image_path, "rb") as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode("utf-8")
        
        # Минимальный запрос только с изображением
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
            request_count += 1
            result = response.json()
            
            # Базовая обработка минимального ответа
            return parse_minimal_response(result)
        else:
            logger.error(f"Минимальный запрос тоже не сработал: {response.status_code}")
            return {"name": "Не удалось распознать", "probability": 0}
        
    except Exception as e:
        logger.error(f"Ошибка в минимальном запросе: {e}")
        return {"name": "Ошибка распознавания", "probability": 0}

def parse_minimal_response(result):
    """Парсит минимальный ответ API"""
    try:
        if result.get("result"):
            result_data = result["result"]
            
            # Проверяем, растение ли это
            is_plant = result_data.get("is_plant", {})
            if is_plant.get("probability", 0) > 0.5:
                
                # Получаем классификацию
                classification = result_data.get("classification", {})
                suggestions = classification.get("suggestions", [])
                
                if suggestions:
                    best_match = suggestions[0]
                    plant_name = best_match.get("name", "Неизвестное растение")
                    probability = best_match.get("probability", 0)
                    
                    return {
                        "name": plant_name,
                        "probability": probability,
                        "common_names": [],
                        "all_suggestions": [s.get("name", "") for s in suggestions[:3] if s.get("name")],
                        "is_plant_probability": is_plant.get("probability", 0)
                    }
            
            return {
                "name": "Не является растением",
                "probability": 0,
                "is_plant_probability": is_plant.get("probability", 0)
            }
        
        return {"name": "Неизвестное растение", "probability": 0}
        
    except Exception as e:
        logger.error(f"Ошибка парсинга минимального ответа: {e}")
        return {"name": "Ошибка обработки", "probability": 0}

def check_remaining_requests():
    global request_count, last_reset_day
    
    current_day = time.strftime("%Y-%m-%d")
    if current_day != last_reset_day:
        request_count = 0
        last_reset_day = current_day
    
    # Бесплатный тариф обычно 100 запросов в день
    remaining = max(0, 100 - request_count)
    logger.info(f"Использовано запросов сегодня: {request_count}, осталось: {remaining}")
    
    return {
        "used": request_count,
        "remaining": remaining,
        "reset_day": current_day,
        "limit": 100
    }

# Функция для проверки соединения с API
def test_api_connection():
    """Тестирует соединение с API"""
    try:
        test_payload = {
            "images": ["test"],  # Невалидное изображение для теста
        }
        
        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            PLANT_ID_URL,
            json=test_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 400:
            # Ожидаемая ошибка - значит API доступен
            logger.info("API доступен (получена ожидаемая ошибка 400)")
            return True
        elif response.status_code == 401:
            logger.error("Неверный API ключ")
            return False
        else:
            logger.info(f"API ответил статусом: {response.status_code}")
            return response.status_code < 500
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании API: {e}")
        return False