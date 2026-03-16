import requests
import json
import time
import logging

logger = logging.getLogger(__name__)

# ПРОВЕРЬТЕ: API ключ должен быть в правильном формате
# Для OpenRouter API ключи обычно начинаются с "sk-or-v1-"
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemma-3n-e2b-it:free"

def get_plant_advice(plant_name):
    """
    Получает советы по уходу за растением через OpenRouter API
    """
    if not OPENROUTER_API_KEY:
        return "❌ API ключ OpenRouter не настроен"
    
    # Проверяем, не содержит ли имя растения сообщение об ошибке
    if plant_name.startswith("Ошибка") or plant_name.startswith("Не удалось"):
        return f"❌ Не могу дать советы: {plant_name}. Попробуйте отправить другое фото или название."
    
    # Создаем промпт для AI
    prompt = f"""Дай краткие советы по уходу за растением: {plant_name}

    Формат ответа:
    
    🌱 **{plant_name}**
    
    💧 **Полив:** [частота и количество воды]
    ☀️ **Освещение:** [требования к свету]
    🌡 **Температура:** [комфортный диапазон]
    ⚠️ **Предупреждения:** [частые проблемы]
    🌟 **Интересный факт:** [один факт]
    
    Ответ должен быть на русском языке, информативным и дружелюбным.
    """
    
    # ИСПРАВЛЕНО: Правильные заголовки для OpenRouter
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Эти заголовки обязательны для OpenRouter
        "HTTP-Referer": "https://github.com/felicitb/plant-bot",  # Замените на ваш актуальный URL
        "X-Title": "Plant Nanny Bot"
    }
    
    # ИСПРАВЛЕНО: Убедимся, что модель указана правильно
    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты - опытный ботаник, помогающий с уходом за растениями. Давай краткие, полезные советы."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    # Пробуем разные форматы ключа, если первый не сработает
    api_keys_to_try = [
        OPENROUTER_API_KEY,
        # Если ключ начинается с "sk-or-v1-", пробуем без префикса
        OPENROUTER_API_KEY.replace("sk-or-v1-", "") if OPENROUTER_API_KEY.startswith("sk-or-v1-") else None,
    ]
    
    # Удаляем None значения
    api_keys_to_try = [key for key in api_keys_to_try if key]
    
    for idx, api_key in enumerate(api_keys_to_try):
        try:
            headers["Authorization"] = f"Bearer {api_key}"
            
            logger.info(f"Отправка запроса к OpenRouter для растения: {plant_name} (попытка {idx+1}/{len(api_keys_to_try)})")
            start_time = time.time()
            
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=data,
                timeout=30
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Ответ получен за {elapsed_time:.2f} секунд, статус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                advice = result['choices'][0]['message']['content']
                return advice
            elif response.status_code == 401:
                logger.warning(f"Попытка {idx+1} не удалась: 401 - {response.text}")
                continue  # Пробуем следующий ключ
            else:
                logger.error(f"Ошибка OpenRouter API: {response.status_code} - {response.text}")
                return f"❌ Не удалось получить советы для {plant_name}. Попробуйте позже."
                
        except requests.exceptions.Timeout:
            logger.error(f"Таймаут при запросе к OpenRouter (попытка {idx+1})")
            if idx == len(api_keys_to_try) - 1:
                return f"⏱ Превышено время ожидания ответа для {plant_name}. Попробуйте еще раз."
        except requests.exceptions.ConnectionError:
            logger.error(f"Ошибка соединения с OpenRouter (попытка {idx+1})")
            if idx == len(api_keys_to_try) - 1:
                return f"🔌 Проблемы с соединением. Проверьте интернет."
        except Exception as e:
            logger.error(f"Неожиданная ошибка в попытке {idx+1}: {e}")
            if idx == len(api_keys_to_try) - 1:
                return f"❌ Ошибка при получении советов: {str(e)[:100]}"
    
    # Если все попытки не удались
    return f"❌ Не удалось подключиться к OpenRouter API для {plant_name}. Проверьте API ключ."

def test_openrouter_connection():
    """
    Тестовая функция для проверки подключения к OpenRouter
    """
    test_result = {
        "success": False,
        "message": "",
        "details": {}
    }
    
    if not OPENROUTER_API_KEY:
        test_result["message"] = "API ключ не настроен"
        return test_result
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Пробуем получить список доступных моделей
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            models = response.json()
            test_result["success"] = True
            test_result["message"] = "Подключение успешно"
            test_result["details"]["models_available"] = len(models.get("data", []))
            
            # Проверяем, доступна ли наша модель
            model_available = False
            for model in models.get("data", []):
                if model.get("id") == OPENROUTER_MODEL:
                    model_available = True
                    break
            
            test_result["details"]["model_available"] = model_available
            
        elif response.status_code == 401:
            test_result["message"] = "Ошибка авторизации: неверный API ключ"
            test_result["details"]["response"] = response.text
        else:
            test_result["message"] = f"Ошибка {response.status_code}"
            test_result["details"]["response"] = response.text
            
    except Exception as e:
        test_result["message"] = f"Ошибка подключения: {str(e)}"
    
    return test_result