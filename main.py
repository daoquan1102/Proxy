from fastapi import FastAPI, Request, Response
import os
import httpx
import random

app = FastAPI()

# === Lấy tất cả các biến GEMINI_API_KEY_1 đến GEMINI_API_KEY_36 ===
GEMINI_KEYS = {}
for i in range(1, 37):
    env_key = f"GEMINI_API_KEY_{i}"
    api_key = os.getenv(env_key)
    if api_key:
        GEMINI_KEYS[env_key] = api_key

MODEL = "gemini-2.5-pro"
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"

# === Proxy chat thường ===
@app.post("/v1/gemini/chat")
async def proxy_chat(request: Request):
    body = await request.body()
    for name, key in random.sample(GEMINI_KEYS.items(), len(GEMINI_KEYS)):
        try:
            url = f"{BASE_URL}:generateContent?key={key}"
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

# === Proxy streaming ===
@app.post("/v1/gemini/stream")
async def proxy_stream(request: Request):
    body = await request.body()
    for name, key in random.sample(GEMINI_KEYS.items(), len(GEMINI_KEYS)):
        try:
            url = f"{BASE_URL}:streamGenerateContent?key={key}"
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", url, content=body, headers={
                    "Content-Type": "application/json"
                }) as res:
                    return Response(content=await res.aread(), media_type="text/event-stream")
        except Exception as e:
            print(f"[{name}] Streaming error: {e}")
            continue
    return Response(status_code=500, content=b"All streaming keys failed")

@app.get("/models")
def list_models():
    return {
        "models": [
            {
                "id": "gemini-2.5-pro",
                "object": "model",
                "owned_by": "google",
                "capabilities": ["chat", "vision", "streaming", "json"]
            }
        ]
    }
