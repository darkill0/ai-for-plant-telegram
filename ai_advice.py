# ai_advice.py
import requests
import json
import time
from config import OPENROUTER_API_KEY, OPENROUTER_URL, OPENROUTER_MODEL
import logging

logger = logging.getLogger(__name__)

def get_plant_advice(plant_name):
    """
    Получает советы по уходу за растением через OpenRouter API
    """
    if not OPENROUTER_API_KEY:
        return "❌ API ключ OpenRouter не настроен"
    
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
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yourusername/plant-bot",  # Замените на ваш репозиторий
        "X-Title": "Plant Nanny Bot"
    }
    
    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ты - опытный ботаник, помогающий с уходом за растениями. Давай краткие, полезные советы."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        logger.info(f"Отправка запроса к OpenRouter для растения: {plant_name}")
        start_time = time.time()
        
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=data,
            timeout=30  # Таймаут 30 секунд
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Ответ получен за {elapsed_time:.2f} секунд, статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            advice = result['choices'][0]['message']['content']
            return advice
        else:
            logger.error(f"Ошибка OpenRouter API: {response.status_code} - {response.text}")
            return f"❌ Не удалось получить советы для {plant_name}. Попробуйте позже."
            
    except requests.exceptions.Timeout:
        logger.error("Таймаут при запросе к OpenRouter")
        return f"⏱ Превышено время ожидания ответа для {plant_name}. Попробуйте еще раз."
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка соединения с OpenRouter")
        return f"🔌 Проблемы с соединением. Проверьте интернет."
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return f"❌ Ошибка при получении советов: {str(e)[:100]}"