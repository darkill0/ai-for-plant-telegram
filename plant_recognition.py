# plant_recognition.py
import requests
import json
import os
import time

import logging
from pathlib import Path
PLANT_ID_URL = "https://api.plant.id/v2/identify"
PLANT_ID_API_KEY =  "kQyHiDnUA8TbpdXrkY1OWk7Kx2HqZmrCffYyMT4V6PSh24Lyp2"

logger = logging.getLogger(__name__)

# Счетчик запросов (для отслеживания лимитов)
request_count = 0
last_reset_day = time.strftime("%Y-%m-%d")

def recognize_plant(image_path):
    """
    Распознает растение по фото через Plant.id API
    """
    global request_count, last_reset_day
    
    # Сбрасываем счетчик в новый день
    current_day = time.strftime("%Y-%m-%d")
    if current_day != last_reset_day:
        request_count = 0
        last_reset_day = current_day
        logger.info(f"Новый день, счетчик сброшен")
    
    # Проверяем существование файла
    if not os.path.exists(image_path):
        logger.error(f"Файл не найден: {image_path}")
        return {"name": "Файл не найден", "probability": 0}
    
    if not PLANT_ID_API_KEY:
        logger.error("API ключ Plant.id не настроен")
        return {"name": "Ошибка API", "probability": 0}
    
    try:
        # Подготавливаем изображение
        with open(image_path, 'rb') as f:
            images = [f.read()]
        
        logger.info(f"Отправка запроса к Plant.id API, файл: {image_path}, размер: {os.path.getsize(image_path)} байт")
        start_time = time.time()
        
        # Параметры запроса
        params = {
            'api_key': PLANT_ID_API_KEY,
            'images': images,
            'modifiers': ['crops_fast', 'similar_images'],
            'plant_language': 'ru',
            'plant_details': ['common_names', 'url', 'name_authority', 'wiki_description', 'taxonomy']
        }
        
        response = requests.post(
            PLANT_ID_URL,
            files=[('images', ('image.jpg', img, 'image/jpeg')) for img in images],
            data={'organs': ['auto']},
            params={'api_key': PLANT_ID_API_KEY},
            timeout=30
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Ответ получен за {elapsed_time:.2f} секунд, статус: {response.status_code}")
        
        if response.status_code == 200:
            request_count += 1
            result = response.json()
            
            if result.get('suggestions') and len(result['suggestions']) > 0:
                best_match = result['suggestions'][0]
                plant_name = best_match.get('plant_name', 'Неизвестное растение')
                probability = best_match.get('probability', 0)
                
                # Получаем дополнительные детали
                common_names = []
                if best_match.get('plant_details') and best_match['plant_details'].get('common_names'):
                    common_names = best_match['plant_details']['common_names']
                
                logger.info(f"Распознано: {plant_name} с вероятностью {probability:.2f}")
                
                return {
                    "name": plant_name,
                    "probability": probability,
                    "common_names": common_names[:5],  # Первые 5 названий
                    "all_suggestions": [s['plant_name'] for s in result['suggestions'][:3]]
                }
            else:
                logger.warning("Растение не распознано")
                return {"name": "Неизвестное растение", "probability": 0}
                
        elif response.status_code == 429:
            logger.error("Превышен лимит запросов к Plant.id API")
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

def check_remaining_requests():
    """
    Проверяет оставшееся количество запросов (для информирования)
    """
    global request_count, last_reset_day
    
    current_day = time.strftime("%Y-%m-%d")
    if current_day != last_reset_day:
        request_count = 0
        last_reset_day = current_day
    
    remaining = max(0, 100 - request_count)  # Предполагаем лимит 100 запросов в день
    logger.info(f"Использовано запросов сегодня: {request_count}, осталось: {remaining}")
    
    return {
        "used": request_count,
        "remaining": remaining,
        "reset_day": current_day
    }