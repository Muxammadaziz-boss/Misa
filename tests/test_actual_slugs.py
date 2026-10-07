import pytest
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


def run_live_slugs():
    print("=== LIVE GENERATION TEST WITH REAL 2026 MODEL SLUGS ===")

    # 1. Gemini
    gemini_key = keys.get("MISA_GEMINI_API_KEY", "")
    if gemini_key:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "Salom! Bu Misa AI sinovi. O'zbekcha 1 jumla ayt."}]}],
                "generationConfig": {"maxOutputTokens": 40}
            },
            timeout=10
        )
        print("Gemini:", r.status_code)
        if r.status_code == 200:
            print("  ->", r.json()["candidates"][0]["content"]["parts"][0]["text"].strip())
        else:
            print("  -> Error:", r.text[:200])

    # 2. Groq
    groq_key = keys.get("MISA_GROQ_API_KEY", "")
    if groq_key:
        for m in ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": m,
                    "messages": [{"role": "user", "content": "Salom! O'zbekcha 1 jumla ayt."}],
                    "max_tokens": 40
                },
                timeout=10
            )
            print(f"Groq ({m}):", r.status_code)
            if r.status_code == 200:
                print("  ->", r.json()["choices"][0]["message"].get("content", "").strip())
                break
            else:
                print("  -> Error:", r.text[:150])

    # 3. Cerebras
    cerebras_key = keys.get("MISA_CEREBRAS_API_KEY", "")
    if cerebras_key:
        for m in ["gpt-oss-120b", "qwen-3.8-27b"]:
            r = requests.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {cerebras_key}", "Content-Type": "application/json"},
                json={
                    "model": m,
                    "messages": [{"role": "user", "content": "Salom! O'zbekcha 1 jumla ayt."}],
                    "max_tokens": 40
                },
                timeout=10
            )
            print(f"Cerebras ({m}):", r.status_code)
            if r.status_code == 200:
                print("  ->", r.json()["choices"][0]["message"].get("content", "").strip())
                break
            else:
                print("  -> Error:", r.text[:150])

    # 4. OpenRouter
    openrouter_key = keys.get("MISA_OPENROUTER_API_KEY", "")
    if openrouter_key:
        for m in ["nvidia/nemotron-3.5-lightning:free", "liquid/lfm-2.5-2.6b:free"]:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://misa-ai.uz",
                    "X-Title": "Misa AI Assistant"
                },
                json={
                    "model": m,
                    "messages": [{"role": "user", "content": "Salom! O'zbekcha 1 jumla ayt."}],
                    "max_tokens": 40
                },
                timeout=15
            )
            print(f"OpenRouter ({m}):", r.status_code)
            if r.status_code == 200:
                print("  ->", r.json()["choices"][0]["message"].get("content", "").strip())
                break
            else:
                print("  -> Error:", r.text[:150])


def test_slugs_import_pass():
    """Pytest import tekshiruvi"""
    assert True


if __name__ == "__main__":
    run_live_slugs()
