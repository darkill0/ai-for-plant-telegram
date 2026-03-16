import requests

url = "https://openrouter.ai/api/v1/chat/completions"

headers = {
 "Authorization": "Bearer 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",
 "Content-Type": "application/json"
}

data = {
 "model": "google/gemma-3n-e2b-it:free",
 "messages": [{"role":"user","content":"Hello"}]
}

print(requests.post(url, headers=headers, json=data).text)