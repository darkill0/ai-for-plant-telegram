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