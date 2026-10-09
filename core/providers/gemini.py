# ========== core/providers/gemini.py ==========
# Misa AI 9.0.0 — Dedicated Google Gemini Provider Adapter
# Native Google AI Studio REST Integration with Grounding, Vision & Streaming

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional, Iterator
import requests

from core.intelligence.types import AIRequest, AIResponse
from core.providers.base import LLMProvider, StreamChunk, ProviderHealth, Capability
from core.providers.health import get_health_monitor
from core.providers.registry import get_model_registry
from core.providers.errors import (
    ProviderError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    ServerNetworkError,
    ModelUnavailableError,
    MalformedResponseError,
)

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Matn ichidan JSON obyektini xavfsiz ajratib olish."""
    if not text:
        return None
    cleaned = text.strip()

    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            return json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            pass

    if "```json" in cleaned:
        try:
            return json.loads(cleaned.split("```json")[1].split("```")[0].strip(), strict=False)
        except (IndexError, json.JSONDecodeError):
            pass

    if "```" in cleaned:
        try:
            return json.loads(cleaned.split("```")[1].split("```")[0].strip(), strict=False)
        except (IndexError, json.JSONDecodeError):
            pass

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
                        return json.loads(cleaned[start:i+1], strict=False)
                    except json.JSONDecodeError:
                        break
    return None


class GeminiProvider(LLMProvider):
    """
    Google Gemini rasmiy REST API provayderi.
    Google Search Grounding, multimodal vision va token oqimini qo'llab-quvvatlaydi.
    """

    DEFAULT_MODELS = [
        "gemini-3.8-flash",
        "gemini-2.5-flash",
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout: float = 15.0,
        health_monitor: Optional[Any] = None,
        registry: Optional[Any] = None,
    ):
        self._name = "gemini"
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or ""
        self._default_model = default_model or "gemini-3.8-flash"
        self._timeout = timeout
        self._health_monitor = health_monitor or get_health_monitor()
        self._registry = registry or get_model_registry()

    @property
    def name(self) -> str:
        return self._name

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_key(self) -> str:
        """Dinamik Gemini API kalitini olish."""
        if self._api_key and self._api_key.strip():
            return self._api_key.strip()

        # 1. MISA_GEMINI_API_KEY
        misa_k = os.getenv("MISA_GEMINI_API_KEY", "").strip()
        if misa_k:
            return misa_k

        # 2. GEMINI_API_KEY yoki GOOGLE_API_KEY
        env_k = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        if env_k:
            return env_k

        # 3. AIKeyManager
        try:
            from core.v8.ai_key_manager import get_ai_key_manager
            mgr_key = get_ai_key_manager().get_active_gemini_key()
            if mgr_key:
                return mgr_key
        except Exception:
            pass

        # 4. config.json
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    ck = cfg.get("gemini_api_key") or cfg.get("google_api_key") or cfg.get("ai", {}).get("gemini_api_key")
                    if ck and str(ck).strip():
                        return str(ck).strip()
        except Exception:
            pass

        return ""

    def is_available(self) -> bool:
        """API kaliti borligi va cooldown da emasligini tekshirish."""
        key = self.api_key
        if not key:
            return False
        return not self._health_monitor.is_cooling_down(self._name)

    def _get_active_model(self, request: Optional[AIRequest] = None) -> str:
        if request and request.metadata and request.metadata.get("model"):
            return str(request.metadata["model"]).strip()
        if self._default_model:
            return self._default_model
        return "gemini-2.0-flash"

    def _build_contents(self, request: AIRequest) -> List[Dict[str, Any]]:
        """Gemini formati bo'yicha contents qatorini qurish."""
        contents = []

        # Suhbat tarixi
        if request.conversation:
            for item in request.conversation:
                role = "user" if item.get("role") == "user" else "model"
                text = item.get("content") or item.get("text") or ""
                if text:
                    contents.append({"role": role, "parts": [{"text": text}]})

        # Hozirgi xabar
        user_parts = [{"text": request.message or ""}]

        # Multimodal Vision qo'llab-quvvatlash
        if request.metadata and "image_base64" in request.metadata:
            img_b64 = request.metadata["image_base64"]
            mime = request.metadata.get("mime_type", "image/jpeg")
            user_parts.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": img_b64
                }
            })

        contents.append({"role": "user", "parts": user_parts})
        return contents

    def _build_request_body(self, request: AIRequest, model: str) -> Dict[str, Any]:
        """Gemini REST so'rov tanasini tayyorlash."""
        system_text = ""
        if request.system_context and isinstance(request.system_context, dict):
            system_text = request.system_context.get("prompt", "")
        if not system_text and request.metadata and isinstance(request.metadata, dict):
            system_text = request.metadata.get("system_prompt", "")

        temperature = request.metadata.get("temperature", 0.4) if request.metadata else 0.4
        max_tokens = request.metadata.get("max_tokens", 2048) if request.metadata else 2048

        body: Dict[str, Any] = {
            "contents": self._build_contents(request),
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        if system_text:
            body["system_instruction"] = {"parts": [{"text": system_text}]}

        # Google Search Grounding — real-time faktlar uchun (agar talab qilinsa)
        enable_grounding = request.metadata.get("grounding", False) if request.metadata else False
        if enable_grounding and "vision" not in request.metadata:
            body["tools"] = [{"google_search": {}}]

        return body

    def _normalize_response(self, raw_data: Dict[str, Any], model: str) -> AIResponse:
        """Gemini javobini AIResponse obyektiga aylantirish."""
        candidates = raw_data.get("candidates") or []
        if not candidates:
            raise MalformedResponseError("Gemini javobida 'candidates' bo'sh", provider=self._name, model=model)

        cand0 = candidates[0]
        content_obj = cand0.get("content") or {}
        parts = content_obj.get("parts") or []

        ai_text = ""
        for p in parts:
            if p.get("thought", False):
                continue
            if "text" in p:
                ai_text += p["text"]
        ai_text = ai_text.strip()

        usage = raw_data.get("usageMetadata") or {}

        # Function Calling
        for p in parts:
            if "functionCall" in p:
                fc = p["functionCall"]
                fname = fc.get("name", "unknown")
                fargs = fc.get("args") or {}
                return AIResponse(
                    provider=self._name,
                    model=model,
                    type="command",
                    intent=fname,
                    params=fargs,
                    content=ai_text or f"Tool '{fname}' chaqirilmoqda.",
                    usage=usage,
                    metadata={"function_call": fc},
                    raw_text=ai_text,
                    success=True,
                )

        # JSON Parse
        from core.intelligence.text_cleaner import extract_clean_response_text
        extracted = _extract_json_from_text(ai_text)
        if extracted and isinstance(extracted, dict):
            resp_type = extracted.get("type", "answer")
            intent = extracted.get("intent")
            params = extracted.get("params") or {}
            raw_content = extracted.get("response") or extracted.get("question") or ai_text
            content = extract_clean_response_text(raw_content)
            return AIResponse(
                provider=self._name,
                model=model,
                type=resp_type,
                intent=intent,
                params=params,
                content=str(content),
                usage=usage,
                metadata={"parsed_json": extracted},
                raw_text=ai_text,
                success=True,
            )

        clean_content = extract_clean_response_text(ai_text)
        return AIResponse(
            provider=self._name,
            model=model,
            type="answer",
            content=clean_content,
            usage=usage,
            raw_text=ai_text,
            success=True,
        )

    def generate(self, request: AIRequest) -> AIResponse:
        """Sinxron so'rov yuborish."""
        if not self.api_key:
            raise AuthenticationError("Gemini API kaliti topilmadi.", provider=self._name)
        if self._health_monitor.is_cooling_down(self._name):
            raise RateLimitError("Gemini provayderi hozirda sovutish (cooldown) holatida.", provider=self._name)

        model = self._get_active_model(request)
        url = f"{self._base_url}/models/{model}:generateContent?key={self.api_key}"
        body = self._build_request_body(request, model)

        start_time = time.time()
        try:
            logger.info(f"[GEMINI] So'rov yuborilmoqda: model='{model}'")
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=self._timeout
            )
            latency_ms = (time.time() - start_time) * 1000.0

            if resp.status_code == 429:
                err = RateLimitError("Gemini (429): Kvota yoki so'rovlar limiti to'ldi.", provider=self._name, model=model)
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            if resp.status_code in (401, 403):
                err = AuthenticationError(f"Gemini ({resp.status_code}): Kalit yaroqsiz (Permission Denied).", provider=self._name, model=model, status_code=resp.status_code)
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            if resp.status_code == 404:
                err = ModelUnavailableError(f"Gemini (404): Model '{model}' topilmadi.", provider=self._name, model=model)
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            if resp.status_code == 400 and "tools" in body:
                # Agar Google Search Grounding xato bersa, unisiz qayta urinish
                del body["tools"]
                resp = requests.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=self._timeout)

            if resp.status_code != 200:
                err = ProviderError(f"Gemini kutilmagan status: {resp.status_code} - {resp.text[:150]}", provider=self._name, model=model, status_code=resp.status_code)
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            raw_data = resp.json()
            norm = self._normalize_response(raw_data, model=model)
            norm.metadata["latency_ms"] = latency_ms

            self._health_monitor.record_success(self._name, latency_ms)
            return norm

        except requests.exceptions.Timeout as e:
            latency_ms = (time.time() - start_time) * 1000.0
            err = TimeoutError(f"Gemini timeout ({self._timeout}s): {e}", provider=self._name, model=model, timeout_seconds=self._timeout)
            self._health_monitor.record_failure(self._name, err, latency_ms)
            raise err

        except requests.exceptions.RequestException as e:
            latency_ms = (time.time() - start_time) * 1000.0
            err = ServerNetworkError(f"Gemini ulanish xatosi: {e}", provider=self._name, model=model)
            self._health_monitor.record_failure(self._name, err, latency_ms)
            raise err

    def stream(self, request: AIRequest) -> Iterator[StreamChunk]:
        """Oqimli javob qaytarish (SSE streamGenerateContent)."""
        if not self.api_key:
            raise AuthenticationError("Gemini API kaliti topilmadi.", provider=self._name)
        if self._health_monitor.is_cooling_down(self._name):
            raise RateLimitError("Gemini provayderi hozirda sovutish (cooldown) holatida.", provider=self._name)

        model = self._get_active_model(request)
        url = f"{self._base_url}/models/{model}:streamGenerateContent?alt=sse&key={self.api_key}"
        body = self._build_request_body(request, model)

        start_time = time.time()
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
                stream=True,
                timeout=self._timeout
            )

            if resp.status_code != 200:
                logger.warning(f"[GEMINI] Streaming rad etildi ({resp.status_code}), generate fallback...")
                full = self.generate(request)
                yield StreamChunk(text=full.content, is_final=True)
                return

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    chunk_str = line[6:].strip()
                    try:
                        chunk_json = json.loads(chunk_str)
                        candidates = chunk_json.get("candidates") or []
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            chunk_text = "".join(p.get("text", "") for p in parts)
                            if chunk_text:
                                yield StreamChunk(text=chunk_text, is_final=False)
                    except Exception:
                        continue

            latency_ms = (time.time() - start_time) * 1000.0
            self._health_monitor.record_success(self._name, latency_ms)
            yield StreamChunk(text="", is_final=True)

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000.0
            self._health_monitor.record_failure(self._name, e, latency_ms)
            raise e

    def health_check(self) -> ProviderHealth:
        return self._health_monitor.get_health(self._name)

    def supports(self, capability: str) -> bool:
        cap = capability.lower()
        # Gemini rasman barcha ushbu imkoniyatlarga ega
        return cap in (
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
            Capability.VISION.value,
            Capability.LONG_CONTEXT.value,
            Capability.FAST_RESPONSE.value,
        )
