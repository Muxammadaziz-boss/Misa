import os
import requests
import json
from pathlib import Path

# Load .env
env_file = Path(__file__).resolve().parent.parent / ".env"
keys = {}
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()

print("Loaded keys from .env:")
for k in ["MISA_GROQ_API_KEY", "MISA_GEMINI_API_KEY", "MISA_CEREBRAS_API_KEY", "MISA_OPENROUTER_API_KEY", "MISA_NVIDIA_API_KEY"]:
    val = keys.get(k, "")
    masked = val[:6] + "..." + val[-4:] if len(val) > 10 else val
    print(f"  {k}: {masked}")

print("\n--- 1. Testing GROQ ---")
groq_key = keys.get("MISA_GROQ_API_KEY", "")
if groq_key:
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": "Salom! 1+1 nechchi? Qisqa javob ber."}],
                "max_tokens": 20
            },
            timeout=10
        )
        print(f"GROQ status: {r.status_code}")
        if r.status_code == 200:
            print("GROQ reply:", r.json()["choices"][0]["message"]["content"])
        else:
            print("GROQ error:", r.text[:200])
    except Exception as e:
        print("GROQ exception:", e)

print("\n--- 2. Testing CEREBRAS ---")
cerebras_key = keys.get("MISA_CEREBRAS_API_KEY", "")
if cerebras_key:
    try:
        r = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {cerebras_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b",
                "messages": [{"role": "user", "content": "Salom! 1+1 nechchi? Qisqa javob ber."}],
                "max_tokens": 20
            },
            timeout=10
        )
        print(f"CEREBRAS status: {r.status_code}")
        if r.status_code == 200:
            print("CEREBRAS reply:", r.json()["choices"][0]["message"]["content"])
        else:
            print("CEREBRAS error:", r.text[:200])
    except Exception as e:
        print("CEREBRAS exception:", e)

print("\n--- 3. Testing OPENROUTER ---")
openrouter_key = keys.get("MISA_OPENROUTER_API_KEY", "")
if openrouter_key:
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://misa-ai.uz",
                "X-Title": "Misa AI Assistant"
            },
            json={
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{"role": "user", "content": "Salom! 1+1 nechchi? Qisqa javob ber."}],
                "max_tokens": 20
            },
            timeout=15
        )
        print(f"OPENROUTER status: {r.status_code}")
        if r.status_code == 200:
            print("OPENROUTER reply:", r.json()["choices"][0]["message"]["content"])
        else:
            print("OPENROUTER error:", r.text[:200])
    except Exception as e:
        print("OPENROUTER exception:", e)

print("\n--- 4. Testing GEMINI ---")
gemini_key = keys.get("MISA_GEMINI_API_KEY", "")
if gemini_key:
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "Salom! 1+1 nechchi? Qisqa javob ber."}]}],
                "generationConfig": {"maxOutputTokens": 20}
            },
            timeout=10
        )
        print(f"GEMINI status: {r.status_code}")
        if r.status_code == 200:
            print("GEMINI reply:", r.json()["candidates"][0]["content"]["parts"][0]["text"])
        else:
            print("GEMINI error:", r.text[:200])
    except Exception as e:
        print("GEMINI exception:", e)

print("\n--- 5. Testing NVIDIA NIM ---")
nvidia_key = keys.get("MISA_NVIDIA_API_KEY", "")
if nvidia_key and not nvidia_key.startswith("nvapi-..."):
    try:
        r = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {nvidia_key}", "Content-Type": "application/json"},
            json={
                "model": "meta/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": "Salom! 1+1 nechchi?"}],
                "max_tokens": 20
            },
            timeout=10
        )
        print(f"NVIDIA status: {r.status_code}")
        if r.status_code == 200:
            print("NVIDIA reply:", r.json()["choices"][0]["message"]["content"])
        else:
            print("NVIDIA error:", r.text[:200])
    except Exception as e:
        print("NVIDIA exception:", e)
else:
    print("NVIDIA key is placeholder (nvapi-...)")
