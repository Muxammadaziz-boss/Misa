# ========== text_cleaner.py ==========
# Misa AI 9.0.1 — Robust AI Response & JSON Sanitizer
# Eliminates raw JSON leaks, handles truncated outputs, and unescapes text.

import json
import re
from typing import Optional, Dict, Any


def clean_unwrapped_text(val: str) -> str:
    """Unescape common JSON escape sequences and strip whitespace"""
    if not val:
        return ""
    return val.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '').strip()


def extract_clean_response_text(text: Any) -> str:
    """
    Har qanday AI javobidan (to'liq JSON, qisman/uzilib qolgan JSON,
    yoki markdown bilan o'ralgan JSON) toza inson o'qiydigan matnni ajratib olish.
    Foydalanuvchi interfeysiga HECH QACHON xom JSON {'type': 'answer', ...} chiqmaydi.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        if isinstance(text, dict):
            val = text.get("response") or text.get("content") or text.get("javob") or text.get("question") or text.get("message")
            if val is not None:
                return extract_clean_response_text(str(val))
            return str(text)
        return str(text)

    cleaned = text.strip()
    if not cleaned:
        return ""

    # 1. Agar matnda JSON belgilari umuman bo'lmasa -> to'g'ridan-to'g'ri qaytarish
    if not (cleaned.startswith("{") or "```" in cleaned or '"type"' in cleaned or '"response"' in cleaned):
        return cleaned

    # Markdown bloklarini tozalash
    candidate = cleaned
    if "```json" in candidate:
        parts = candidate.split("```json", 1)[1].split("```", 1)
        candidate = parts[0].strip()
    elif "```" in candidate:
        parts = candidate.split("```", 1)[1].split("```", 1)
        candidate = parts[0].strip()

    # 2. To'liq JSON ni parse qilish (strict=False bilan - literal yangi qatorlarga ruxsat beradi)
    try:
        parsed = json.loads(candidate, strict=False)
        if isinstance(parsed, dict):
            extracted = (
                parsed.get("response")
                or parsed.get("content")
                or parsed.get("javob")
                or parsed.get("question")
                or parsed.get("message")
                or parsed.get("error")
            )
            if extracted is not None and isinstance(extracted, str):
                # Agar ichma-ich yana JSON bo'lsa (double-wrapping)
                return extract_clean_response_text(extracted)
            elif extracted is not None:
                return str(extracted)
    except Exception:
        pass

    # 3. Ichma-ich balanslangan {} qidirish (strict=False bilan)
    start = candidate.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(candidate)):
            if candidate[i] == "{":
                depth += 1
            elif candidate[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        sub = candidate[start:i+1]
                        parsed = json.loads(sub, strict=False)
                        if isinstance(parsed, dict):
                            extracted = (
                                parsed.get("response")
                                or parsed.get("content")
                                or parsed.get("javob")
                                or parsed.get("question")
                                or parsed.get("message")
                            )
                            if extracted is not None and isinstance(extracted, str):
                                return extract_clean_response_text(extracted)
                            elif extracted is not None:
                                return str(extracted)
                    except Exception:
                        pass
                    break

    # 4. Uzilib qolgan yoki qisman buzilgan JSON (Truncated JSON recovery)
    # Masalan: {"type": "answer", "response": "Bu nomdagi eng mashhur qo'shiqlar...
    # (oxirida qo'shtirnoq yoki qavs yopilmagan bo'lsa)
    resp_match = re.search(
        r'"(?:response|content|javob|question|message)"\s*:\s*"(.*)',
        candidate,
        flags=re.DOTALL
    )
    if resp_match:
        raw_val = resp_match.group(1)
        # Agar oxirida "} yoki " bo'lsa olib tashlaymiz
        raw_val = re.sub(r'"\s*\}?\s*$', '', raw_val)
        clean = clean_unwrapped_text(raw_val)
        if clean:
            return extract_clean_response_text(clean)

    # 5. Regex orqali {"type": ...} qobig'ini kesib tashlash
    clean_stripped = re.sub(
        r'^\s*\{\s*["\']type["\']\s*:\s*["\'][^"\']+["\']\s*,\s*["\'](?:response|content|javob|question|message)["\']\s*:\s*["\']?',
        '',
        candidate,
        flags=re.DOTALL
    )
    clean_stripped = re.sub(r'["\']?\s*\}?\s*$', '', clean_stripped)
    clean_stripped = clean_unwrapped_text(clean_stripped)
    if clean_stripped and not clean_stripped.startswith("{"):
        return clean_stripped

    # 6. Agar baribir {"type": "answer", ...} qolgan bo'lsa, xom belgilarni tozalash
    if candidate.startswith("{") and ('"type"' in candidate or '"response"' in candidate):
        raw_sub = re.sub(r'^\s*\{.*?"(?:response|content|javob)":\s*"?', '', candidate, flags=re.DOTALL)
        raw_sub = re.sub(r'"?\s*\}?\s*$', '', raw_sub)
        raw_clean = clean_unwrapped_text(raw_sub)
        if raw_clean:
            return raw_clean

    return cleaned
