import requests
import json
from pathlib import Path


def main():
    env_file = Path(__file__).resolve().parent.parent / ".env"
    keys = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    keys[k.strip()] = v.strip()

    # Gemini with gemini-3.8-flash and gemini-flash-latest
    gemini_key = keys.get("MISA_GEMINI_API_KEY", "")
    if gemini_key:
        for m in ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash-lite", "gemini-flash-lite-latest"]:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": "Salom! Bu Misa AI sinovi. O'zbekcha 'Salom Ustoz!' deb javob ber."}]}],
                        "generationConfig": {"maxOutputTokens": 40}
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
                print(f"Gemini {m} exception: {e}")

    # Cerebras structure inspection
    cerebras_key = keys.get("MISA_CEREBRAS_API_KEY", "")
    if cerebras_key:
        try:
            r_cer = requests.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {cerebras_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-oss-120b",
                    "messages": [{"role": "user", "content": "Salom! O'zbekcha 'Salom Ustoz!' deb javob ber."}],
                    "max_tokens": 40
                },
                timeout=10
            )
            print(f"Cerebras response keys: {r_cer.status_code}")
            if r_cer.status_code == 200:
                print("Cerebras json:", json.dumps(r_cer.json(), indent=2)[:300])
        except Exception as e:
            print("Cerebras exception:", e)

    # Groq structure inspection
    groq_key = keys.get("MISA_GROQ_API_KEY", "")
    if groq_key:
        try:
            r_groq = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [{"role": "user", "content": "Salom! O'zbekcha 'Salom Ustoz!' deb javob ber."}],
                    "max_tokens": 40
                },
                timeout=10
            )
            print(f"Groq response: {r_groq.status_code}")
            if r_groq.status_code == 200:
                print("Groq json:", json.dumps(r_groq.json(), indent=2)[:300])
        except Exception as e:
            print("Groq exception:", e)


if __name__ == "__main__":
    main()
