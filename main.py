from fastapi import FastAPI, Request, Response
import os
import httpx
import random

app = FastAPI()

# === Lấy danh sách key từ ENV ===
GEMINI_KEYS = {}
for i in range(1, 48):
    key_name = f"GEMINI_API_KEY_{i}"
    key_value = os.getenv(key_name)
    if key_value:
        GEMINI_KEYS[key_name] = key_value

# === Proxy endpoint động cho bất kỳ model nào ===
@app.post("/v1beta/models/{model_name}:{action}")
async def proxy_dynamic_model(model_name: str, action: str, request: Request):
    body = await request.body()

    for name, key in random.sample(GEMINI_KEYS.items(), len(GEMINI_KEYS)):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:{action}?key={key}"
            async with httpx.AsyncClient(timeout=60) as client:
                res = await client.post(url, content=body, headers={
                    "Content-Type": "application/json"
                })
                if res.status_code == 200:
                    return Response(content=res.content, media_type="application/json")
                else:
                    print(f"[{name}] Failed: {res.status_code}")
        except Exception as e:
            print(f"[{name}] Error: {e}")
            continue

    return Response(status_code=500, content=b"All keys failed")
