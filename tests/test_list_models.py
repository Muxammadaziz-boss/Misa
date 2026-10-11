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

# 1. Groq models
groq_key = keys.get("MISA_GROQ_API_KEY", "")
if groq_key:
    r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {groq_key}"})
    if r.status_code == 200:
        models = [m["id"] for m in r.json().get("data", [])]
        print(f"Groq models ({len(models)}):", models)
    else:
        print("Groq models error:", r.text[:200])

# 2. Cerebras models
cerebras_key = keys.get("MISA_CEREBRAS_API_KEY", "")
if cerebras_key:
    r = requests.get("https://api.cerebras.ai/v1/models", headers={"Authorization": f"Bearer {cerebras_key}"})
    if r.status_code == 200:
        models = [m["id"] for m in r.json().get("data", [])]
        print(f"Cerebras models ({len(models)}):", models)
    else:
        print("Cerebras models error:", r.text[:200])

# 3. Gemini models
gemini_key = keys.get("MISA_GEMINI_API_KEY", "")
if gemini_key:
    r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}")
    if r.status_code == 200:
        models = [m["name"].replace("models/", "") for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        print(f"Gemini models ({len(models)}):", models[:10])
    else:
        print("Gemini models error:", r.text[:200])

# 4. OpenRouter free models
openrouter_key = keys.get("MISA_OPENROUTER_API_KEY", "")
if openrouter_key:
    r = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {openrouter_key}"})
    if r.status_code == 200:
        free_models = [m["id"] for m in r.json().get("data", []) if ":free" in m.get("id", "")]
        print(f"OpenRouter free models ({len(free_models)}):", free_models[:10])
    else:
        print("OpenRouter models error:", r.text[:200])
