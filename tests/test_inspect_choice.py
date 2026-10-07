import requests
import json
from pathlib import Path

env_file = Path(__file__).resolve().parent.parent / ".env"
keys = {}
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()

# 1. Groq
groq_key = keys.get("MISA_GROQ_API_KEY", "")
for m in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "allam-2-7b"]:
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": m,
                "messages": [{"role": "user", "content": "Salom! Bu Misa AI sinovi. 'Salom Ustoz!' deb javob ber."}],
                "max_tokens": 50
            },
            timeout=10
        )
        print(f"Groq ({m}): {r.status_code}")
        if r.status_code == 200:
            print("  Choice keys:", r.json()["choices"][0])
            break
        else:
            print("  Error:", r.text[:120])
    except Exception as e:
        print(f"Groq ({m}) error: {e}")

# 2. Cerebras
cerebras_key = keys.get("MISA_CEREBRAS_API_KEY", "")
for m in ["gpt-oss-120b", "qwen-3.8-27b"]:
    try:
        r = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {cerebras_key}", "Content-Type": "application/json"},
            json={
                "model": m,
                "messages": [{"role": "user", "content": "Salom! 'Salom Ustoz!' deb javob ber."}],
                "max_tokens": 50
            },
            timeout=10
        )
        print(f"Cerebras ({m}): {r.status_code}")
        if r.status_code == 200:
            print("  Choice:", r.json()["choices"][0])
            break
        else:
            print("  Error:", r.text[:120])
    except Exception as e:
        print(f"Cerebras ({m}) error: {e}")

# 3. Gemini models
gemini_key = keys.get("MISA_GEMINI_API_KEY", "")
for m in ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-pro-latest"]:
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "Salom! 'Salom Ustoz!' deb javob ber."}]}],
                "generationConfig": {"maxOutputTokens": 30}
            },
            timeout=10
        )
        print(f"Gemini ({m}): {r.status_code}")
        if r.status_code == 200:
            print("  Gemini text:", r.json()["candidates"][0]["content"]["parts"][0]["text"].strip())
            break
        else:
            print("  Error:", r.text[:120])
    except Exception as e:
        print(f"Gemini ({m}) error: {e}")
