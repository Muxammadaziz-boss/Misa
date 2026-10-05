# ========== gemini_provider.py ==========
# Misa AI 7.x — Google Gemini AI Provider Implementation
# Native REST Integration with Model Fallbacks, Search Grounding and Response Normalization

import os
import re
import json
import logging
import requests
from typing import List, Optional, Dict, Any

from core.intelligence.types import AIRequest, AIResponse
from core.intelligence.provider import AIProvider

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Matn ichidan JSON obyektini xavfsiz ajratib olish (nested qavslar bilan)"""
    if not text:
        return None
    cleaned = text.strip()

    # 1. To'g'ridan-to'g'ri JSON
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # 2. Markdown ```json ... ``` bloklari
    if "```json" in cleaned:
        try:
            return json.loads(cleaned.split("```json")[1].split("```")[0].strip())
        except (IndexError, json.JSONDecodeError):
            pass

    if "```" in cleaned:
        try:
            return json.loads(cleaned.split("```")[1].split("```")[0].strip())
        except (IndexError, json.JSONDecodeError):
            pass

    # 3. Ichma-ich {} qidiruvi
    start = cleaned.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start:i+1])
                    except json.JSONDecodeError:
                        break

    return None


class GeminiProvider(AIProvider):
    """Google Gemini rasmiy REST API provayderi"""

    DEFAULT_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-pro",
        "gemini-pro-latest",
    ]

    def __init__(self, api_key: Optional[str] = None, models: Optional[List[str]] = None):
        self._api_key = api_key or ""
        self._models = models or list(self.DEFAULT_MODELS)

    @property
    def api_key(self) -> str:
        """Dinamik ravishda API kalitni olish (explicit key, AIKeyManager, GEMINI_API_KEY, GOOGLE_API_KEY yoki config.json)"""
        if self._api_key and self._api_key.strip():
            return self._api_key.strip()
        try:
            from core.v8.ai_key_manager import get_ai_key_manager
            manager_key = get_ai_key_manager().get_active_gemini_key()
            if manager_key:
                return manager_key
        except Exception:
            pass
        env_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        if env_key:
            return env_key
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    k = (
                        cfg.get("gemini_api_key")
                        or cfg.get("google_api_key")
                        or cfg.get("ai", {}).get("gemini_api_key")
                        or cfg.get("ai", {}).get("api_key")
                    )
                    if k and str(k).strip():
                        return str(k).strip()
        except Exception:
            pass
        return ""

    def set_api_key(self, key: str):
        """API kalitni xotirada darhol yangilash"""
        self._api_key = (key or "").strip()

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, request: AIRequest) -> AIResponse:
        """Gemini API orqali so'rov yuborish va normalizatsiya qilingan AIResponse qaytarish"""
        user_id = request.metadata.get("user_id") if request and hasattr(request, "metadata") and isinstance(request.metadata, dict) else None
        active_key = ""
        try:
            from core.v8.ai_key_manager import get_ai_key_manager
            active_key = get_ai_key_manager().get_active_gemini_key(user_id=user_id)
        except Exception:
            pass
        if not active_key:
            active_key = self.api_key

        if not active_key:
            return AIResponse(
                provider=self.name,
                model="none",
                type="error",
                content="Gemini API kaliti topilmadi.",
                success=False,
                error_code="API_KEY_MISSING"
            )


        # 1. Contents va Suhbat tarixi tuzish
        contents = []
        if request.conversation:
            for item in request.conversation:
                role = "user" if item.get("role") in ("user", "human") else "model"
                text = item.get("content") or item.get("text") or ""
                if text:
                    contents.append({"role": role, "parts": [{"text": text}]})

        # Joriy xabarni qo'shish
        contents.append({"role": "user", "parts": [{"text": request.message}]})

        # 2. Tizim ko'rsatmasi (System Instruction)
        system_text = ""
        if request.system_context:
            system_text = request.system_context.get("prompt", "")
        if not system_text and "system_prompt" in request.metadata:
            system_text = request.metadata["system_prompt"]

        gen_config = {"maxOutputTokens": 2048, "temperature": 0.4}

        last_error = ""
        for model in self._models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            request_body: Dict[str, Any] = {
                "contents": contents,
                "generationConfig": gen_config,
                "tools": [{"google_search": {}}]
            }
            if system_text:
                request_body["system_instruction"] = {"parts": [{"text": system_text}]}

            try:
                response = requests.post(
                    f"{url}?key={active_key}",
                    headers={"Content-Type": "application/json"},
                    json=request_body,
                    timeout=15
                )

                if response.status_code == 403:
                    last_error = f"HTTP 403 Permission Denied: {response.text[:200]}"
                    logger.warning(f"Gemini API kaliti bloklangan yoki yaroqsiz (403): {last_error}")
                    break

                if response.status_code == 429:
                    logger.warning(f"Gemini {model} kvotasi tugadi (429), keyingi modelga o'tilmoqda...")
                    continue

                if response.status_code == 400:
                    # Search Grounding qo'llab-quvvatlanmagan bo'lsa, tools siz qayta urinish
                    if "tools" in request_body:
                        del request_body["tools"]
                        response = requests.post(
                            f"{url}?key={active_key}",
                            headers={"Content-Type": "application/json"},
                            json=request_body,
                            timeout=15
                        )

                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}: {response.text[:150]}"
                    logger.warning(f"Gemini {model} xatolik berdi: {last_error}")
                    continue

                data = response.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                ai_text = ""
                for part in parts:
                    if part.get("thought", False):
                        continue
                    if "text" in part:
                        ai_text += part["text"]
                ai_text = ai_text.strip()

                grounding = candidates[0].get("groundingMetadata", {})
                usage = data.get("usageMetadata", {})

                # Normalizatsiya
                return self._normalize_response(ai_text, model, usage, grounding)

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Gemini {model} istisno: {e}")
                continue

        try:
            from core.v8.ai_key_manager import get_ai_key_manager
            get_ai_key_manager().mark_key_failed(active_key, cooldown_seconds=60.0)
        except Exception:
            pass

        return AIResponse(
            provider=self.name,
            model="none",
            type="error",
            content=f"Gemini so'rovi muvaffaqiyatsiz bo'ldi: {last_error}",
            success=False,
            error_code="GEMINI_CALL_FAILED"
        )

    def _normalize_response(self, text: str, model: str, usage: dict, grounding: dict) -> AIResponse:
        """Gemini matnini normalizatsiya qilingan AIResponse ga aylantirish"""
        parsed = _extract_json_from_text(text)

        metadata = {
            "grounding_active": bool(grounding),
            "raw_length": len(text),
        }

        if parsed and isinstance(parsed, dict):
            resp_type = parsed.get("type", "answer").lower()
            intent = parsed.get("intent")
            params = parsed.get("params", {})
            content = parsed.get("response") or parsed.get("content") or parsed.get("javob") or ""

            if resp_type in ("command", "action"):
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="command",
                    content=content or f"Buyruq bajarilmoqda: {intent}",
                    intent=intent,
                    params=params,
                    usage=usage,
                    metadata=metadata,
                    raw_text=text,
                    success=True
                )
            elif resp_type == "clarification":
                question = parsed.get("question") or content
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="clarification",
                    content=question,
                    intent=intent,
                    params=params,
                    usage=usage,
                    metadata=metadata,
                    raw_text=text,
                    success=True
                )
            elif resp_type == "confirmation":
                question = parsed.get("question") or content
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="confirmation",
                    content=question,
                    intent=intent,
                    params=params,
                    usage=usage,
                    metadata=metadata,
                    raw_text=text,
                    success=True
                )
            else:
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="answer",
                    content=content or str(parsed),
                    intent=intent,
                    params=params,
                    usage=usage,
                    metadata=metadata,
                    raw_text=text,
                    success=True
                )

        # JSON topilmasa: toza matn javob
        # Qisman buzilgan JSON dan response ni tiklashga urinish
        resp_match = re.search(r'"response"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)', text)
        if resp_match:
            clean_resp = resp_match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
            if clean_resp:
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="answer",
                    content=clean_resp,
                    usage=usage,
                    metadata=metadata,
                    raw_text=text,
                    success=True
                )

        return AIResponse(
            provider=self.name,
            model=model,
            type="answer",
            content=text,
            usage=usage,
            metadata=metadata,
            raw_text=text,
            success=True
        )
