import requests
import base64
import json
import os

API_KEY = "kQyHiDnUA8TbpdXrkY1OWk7Kx2HqZmrCffYyMT4V6PSh24Lyp2"
API_URL = "https://api.plant.id/v3/identification"

IMAGE_PATH = "plant.jpg"


def test_plant_api():

    if not os.path.exists(IMAGE_PATH):
        print("Файл изображения не найден:", IMAGE_PATH)
        return

    with open(IMAGE_PATH, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "images": [image_base64],
        "modifiers": [
            "classification_level=species",
            "similar_images=true"
        ]
    }

    headers = {
        "Api-Key": API_KEY,
        "Content-Type": "application/json"
    }

    print("Отправка запроса к Plant.id...")

    response = requests.post(
        API_URL,
        json=payload,
        headers=headers,
        timeout=30
    )

    print("Статус ответа:", response.status_code)

    if response.status_code not in [200, 201]:
        print("Ошибка API:")
        print(response.text)
        return

    data = response.json()

    print("\nПолный ответ API:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    result = data.get("result", {})
    classification = result.get("classification", {})
    suggestions = classification.get("suggestions", [])

    if not suggestions:
        print("\nРастение не определено")
        return

    best = suggestions[0]

    name = best.get("name")
    probability = best.get("probability")

    print("\nЛучшее совпадение:")
    print("Название:", name)
    print("Вероятность:", probability)


if __name__ == "__main__":
    test_plant_api()