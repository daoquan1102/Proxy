from fastapi import FastAPI, Request, Response
import os
import httpx
import random

app = FastAPI()

# === Load tất cả các key từ ENV: GEMINI_API_KEY_1 đến GEMINI_API_KEY_36 ===
GEMINI_KEYS = {}
for i in range(1, 37):
    env_key = f"GEMINI_API_KEY_{i}"
    api_key = os.getenv(env_key)
    if api_key:
        GEMINI_KEYS[env_key] = api_key

MODEL = "gemini-2.5-pro"
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"

@app.post("/v1/gemini/chat")
async def proxy_chat(request: Request):
    body = await request.body()
    
    # Duyệt ngẫu nhiên qua các key
    for name, key in random.sample(GEMINI_KEYS.items(), len(GEMINI_KEYS)):
        try:
            url = f"{BASE_URL}:generateContent"
            async with httpx.AsyncClient(timeout=60) as client:
                res = await client.post(
                    url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": key
                    }
                )
                if res.status_code == 200:
                    return Response(content=res.content, media_type="application/json")
                else:
                    print(f"[{name}] Status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[{name}] Error: {e}")
            continue

    return Response(status_code=500, content=b"All API keys failed.")

@app.post("/v1/gemini/stream")
async def proxy_stream(request: Request):
    body = await request.body()

    for name, key in random.sample(GEMINI_KEYS.items(), len(GEMINI_KEYS)):
        try:
            url = f"{BASE_URL}:streamGenerateContent"
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": key
                    }
                ) as res:
                    return Response(content=await res.aread(), media_type="text/event-stream")
        except Exception as e:
            print(f"[{name}] Streaming error: {e}")
            continue

    return Response(status_code=500, content=b"All streaming keys failed")

# Tuỳ chọn: Trả về mô hình giả (cho tool test thấy model)
@app.get("/v1/models")
def list_models_openai_style():
    return {
        "data": [
            {
                "id": "gemini-2.5-pro",
                "object": "model",
                "created": 1720000000,
                "owned_by": "google",
                "permission": [],
            }
        ],
        "object": "list"
    }
@app.get("/models")
def compat_models():
    return list_models_openai_style()
@app.post("/v1/chat/completions")
async def openai_compatible_chat(request: Request):
    body = await request.json()

    # Chuyển đổi OpenAI-style sang Gemini-style
    messages = body.get("messages", [])
    contents = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts = [{"text": content}] if isinstance(content, str) else content
        contents.append({"role": role, "parts": parts})

    gemini_body = { "contents": contents }

    # Gửi sang Gemini như cũ
    for name, key in random.sample(GEMINI_KEYS.items(), len(GEMINI_KEYS)):
        try:
            url = f"{BASE_URL}:generateContent"
            async with httpx.AsyncClient(timeout=60) as client:
                res = await client.post(
                    url,
                    json=gemini_body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": key
                    }
                )
                if res.status_code == 200:
                    gemini_res = res.json()
                    text = gemini_res.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    return {
                        "id": "chatcmpl-fakeid",
                        "object": "chat.completion",
                        "choices": [{
                            "index": 0,
                            "message": {"role": "assistant", "content": text},
                            "finish_reason": "stop"
                        }],
                        "created": 1720000000,
                        "model": MODEL,
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0
                        }
                    }
                else:
                    print(f"[{name}] Status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[{name}] Error: {e}")
            continue

    return Response(status_code=500, content=b"All API keys failed.")
