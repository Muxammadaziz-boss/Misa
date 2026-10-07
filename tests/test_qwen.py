import requests, json
from pathlib import Path

env_file = Path('.env')
keys = {}
for l in env_file.read_text(encoding='utf-8').splitlines():
    if '=' in l and not l.startswith('#'):
        k, v = l.strip().split('=', 1)
        keys[k] = v

# Groq qwen
r = requests.post(
    'https://api.groq.com/openai/v1/chat/completions',
    headers={'Authorization': f"Bearer {keys['MISA_GROQ_API_KEY']}"},
    json={'model': 'qwen/qwen3.8-27b', 'messages': [{'role': 'user', 'content': "Salom! O'zbekcha bir jumla ayt."}], 'max_tokens': 100}
)
print('Groq Qwen:', r.status_code, r.json().get('choices', [{}])[0].get('message'))

# Cerebras qwen
r2 = requests.post(
    'https://api.cerebras.ai/v1/chat/completions',
    headers={'Authorization': f"Bearer {keys['MISA_CEREBRAS_API_KEY']}"},
    json={'model': 'qwen-3.8-27b', 'messages': [{'role': 'user', 'content': "Salom! O'zbekcha bir jumla ayt."}], 'max_tokens': 100, 'reasoning_effort': 'none'}
)
print('Cerebras Qwen:', r2.status_code, r2.json().get('choices', [{}])[0].get('message'))
