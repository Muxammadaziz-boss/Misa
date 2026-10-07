# ========== core/providers/openai_compatible.py ==========
# Misa AI 9.0.0 — Unified OpenAI-Compatible Provider Adapter
# Powers Groq, Cerebras, OpenRouter, NVIDIA NIM & Custom Endpoints

import os
import re
import time
import json
import logging
from typing import List, Dict, Any, Optional, Iterator, Tuple
import requests

from core.intelligence.types import AIRequest, AIResponse
from core.providers.base import LLMProvider, StreamChunk, ProviderHealth, ModelMetadata
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
    """Matn ichidan JSON obyektini xavfsiz ajratib olish (nested qavslar bilan)."""
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


def _strip_reasoning(text: str) -> str:
    """<think>...</think> va boshqa ichki fikrlash teglarini tozalash."""
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
    return text.strip()


def _is_leaked_reasoning(text: str) -> bool:
    """Matn foydalanuvchiga qaratilgan javob emas, modelning ichki inglizcha monologi ekanligini aniqlash."""
    if not text:
        return False
    t_lower = text.lower().strip()
    reasoning_prefixes = [
        "the user is asking",
        "the user asks",
        "the user wants",
        "the user is inquiring",
        "i should use the",
        "i should check",
        "i need to check",
        "let me check",
        "looking at the system",
        "looking at the provided",
        "so, 5 applications are listed",
        "let me think",
        "we need to answer",
        "we should respond",
        "according to the rules",
        "according to the system",
        "actually, the system information",
    ]
    return any(t_lower.startswith(p) for p in reasoning_prefixes)


def _format_tool_schema(t: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI / Groq / Cerebras API uchun qat'iy standartdagi JSON Schema formatlash."""
    name = t.get("name", "unknown")
    desc = t.get("description", "")
    raw_params = t.get("parameters", {})

    if isinstance(raw_params, dict) and raw_params.get("type") == "object" and "properties" in raw_params:
        params_schema = raw_params
    else:
        properties = {}
        required = []
        if isinstance(raw_params, dict):
            for p_name, p_def in raw_params.items():
                if isinstance(p_def, dict):
                    p_type = p_def.get("type", "string")
                    if p_type in ("int", "integer"):
                        p_type = "integer"
                    elif p_type in ("float", "number"):
                        p_type = "number"
                    elif p_type in ("bool", "boolean"):
                        p_type = "boolean"
                    else:
                        p_type = "string"
                    prop_item: Dict[str, Any] = {"type": p_type}
                    if p_def.get("description"):
                        prop_item["description"] = p_def["description"]
                    properties[p_name] = prop_item
                    if p_def.get("required") is True:
                        required.append(p_name)
                else:
                    properties[p_name] = {"type": "string"}
        params_schema = {
            "type": "object",
            "properties": properties,
        }
        if required:
            params_schema["required"] = required

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": params_schema,
        }
    }


class OpenAICompatibleProvider(LLMProvider):
    """
    OpenAI API spetsifikatsiyasiga (Chat Completions) mos keluvchi barcha
    provayderlar uchun umumiy, yuqori darajada moslashuvchan adapter.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 15.0,
        extra_headers: Optional[Dict[str, str]] = None,
        health_monitor: Optional[Any] = None,
        registry: Optional[Any] = None,
    ):
        self._name = name.lower()
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or ""
        self._default_model = default_model or ""
        self._timeout = timeout
        self._extra_headers = extra_headers or {}
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
        """Dinamik ravishda API kalitni qidirish."""
        if self._api_key and self._api_key.strip():
            return self._api_key.strip()

        # 1. MISA_<NAME>_API_KEY
        misa_env = os.getenv(f"MISA_{self._name.upper()}_API_KEY", "").strip()
        if misa_env:
            return misa_env

        # 2. <NAME>_API_KEY
        std_env = os.getenv(f"{self._name.upper()}_API_KEY", "").strip()
        if std_env:
            return std_env

        # 3. AIKeyManager
        try:
            from core.v8.ai_key_manager import get_ai_key_manager
            mgr = get_ai_key_manager()
            if hasattr(mgr, "get_active_key"):
                k = mgr.get_active_key(self._name)
                if k:
                    return k
            elif self._name == "openrouter":
                k = mgr.get_active_openrouter_key()
                if k:
                    return k
        except Exception:
            pass

        return ""

    def is_available(self) -> bool:
        """API kaliti mavjud va provayder sovutish (cooldown) holatida emasligini tekshirish."""
        key = self.api_key
        if not key:
            return False
        return not self._health_monitor.is_cooling_down(self._name)

    def _get_active_model(self, request: Optional[AIRequest] = None) -> str:
        """So'rov yoki registrdan mos modelni aniqlash."""
        if request and request.metadata and request.metadata.get("model"):
            return str(request.metadata["model"]).strip()
        if self._default_model:
            return self._default_model
        # Registrdan eng yuqori ustuvorlikdagi faol modelni olish
        prov_models = self._registry.get_models_for_provider(self._name)
        if prov_models:
            return prov_models[0].model
        return "default"

    def _build_payload(self, request: AIRequest, model: str, stream: bool = False) -> Dict[str, Any]:
        """OpenAI chat completion so'rov formatsini qurish."""
        # 1. System Prompt
        system_text = ""
        if request.system_context and isinstance(request.system_context, dict):
            system_text = request.system_context.get("prompt", "")
        if not system_text and request.metadata and isinstance(request.metadata, dict):
            system_text = request.metadata.get("system_prompt", "")

        messages = []
        if system_text:
            messages.append({"role": "system", "content": system_text})

        # 2. Conversation History
        if request.conversation:
            for item in request.conversation:
                role = "assistant" if item.get("role") in ("model", "assistant") else "user"
                content = item.get("content") or item.get("text") or ""
                if content:
                    messages.append({"role": role, "content": content})

        # 3. User Message
        user_message = request.message or ""
        messages.append({"role": "user", "content": user_message})

        temperature = request.metadata.get("temperature", 0.3) if request.metadata else 0.3
        max_tokens = request.metadata.get("max_tokens", 2048) if request.metadata else 2048

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        # Qwen modellarida ichki fikrlash (reasoning monologi) tokenlarni yeb qo'ymasligi va tezkor javob uchun:
        if "qwen" in model.lower() and not (request.metadata and request.metadata.get("reasoning")):
            payload["reasoning_effort"] = "none"

        # 4. Tool / Function Calling (agar talab qilinsa)
        if request.tools:
            formatted_tools = []
            for t in request.tools:
                if isinstance(t, dict) and "function" in t:
                    formatted_tools.append(t)
                elif isinstance(t, dict) and "name" in t:
                    formatted_tools.append(_format_tool_schema(t))
            if formatted_tools:
                payload["tools"] = formatted_tools
                payload["tool_choice"] = "auto"

        return payload

    def _build_headers(self) -> Dict[str, str]:
        key = self.api_key
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "MisaAI/9.0.0",
        }
        if self._name == "openrouter":
            headers["HTTP-Referer"] = "https://misa-ai.uz"
            headers["X-Title"] = "Misa AI Agent"
        headers.update(self._extra_headers)
        return headers

    def _normalize_response(self, raw_data: Dict[str, Any], model: str) -> AIResponse:
        """OpenAI javobini Misa AIResponse ga aylantirish."""
        choices = raw_data.get("choices") or []
        if not choices:
            raise MalformedResponseError("OpenAI javobida 'choices' maydoni bo'sh", provider=self._name, model=model)

        choice0 = choices[0]
        message = choice0.get("message") or {}
        raw_text = (message.get("content") or "").strip()
        reasoning_text = (message.get("reasoning") or message.get("reasoning_content") or "").strip()
        raw_text = _strip_reasoning(raw_text)

        # DIQQAT: Inglizcha ichki fikrlash (reasoning) HECH QACHON foydalanuvchiga matn qilib ko'rsatilmaydi!
        # Faqat agar unda structured JSON bo'lsa, JSON ni qidirib olamiz.
        if not raw_text and reasoning_text:
            extracted_from_reasoning = _extract_json_from_text(reasoning_text)
            if extracted_from_reasoning and isinstance(extracted_from_reasoning, dict):
                raw_text = json.dumps(extracted_from_reasoning)

        usage = raw_data.get("usage") or {}

        # 1. Function / Tool Calling tekshirish
        tool_calls = message.get("tool_calls")
        if tool_calls and isinstance(tool_calls, list) and len(tool_calls) > 0:
            tc = tool_calls[0]
            func_data = tc.get("function", {})
            func_name = func_data.get("name", "unknown")
            args_str = func_data.get("arguments", "{}")
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
            except Exception:
                args = {}

            clean_content = raw_text if (raw_text and not _is_leaked_reasoning(raw_text)) else f"'{func_name}' vositasi bajarilmoqda..."

            return AIResponse(
                provider=self._name,
                model=model,
                type="command",
                intent=func_name,
                params=args,
                content=clean_content,
                usage=usage,
                metadata={
                    "tool_call_id": tc.get("id"),
                    "raw_tool_call": tc,
                    "reasoning": reasoning_text if reasoning_text else None,
                },
                raw_text=raw_text,
                success=True,
            )

        # 2. JSON ichki tuzilmani tahlil qilish (Misa Legacy & Prompted format)
        extracted = _extract_json_from_text(raw_text)
        if extracted and isinstance(extracted, dict):
            resp_type = extracted.get("type", "answer")
            intent = extracted.get("intent")
            params = extracted.get("params") or {}
            content = extracted.get("response") or extracted.get("question")
            if not content:
                if resp_type == "command" and intent:
                    content = f"'{intent}' buyrug'i bajarilmoqda..."
                else:
                    content = "Buyruq qabul qilindi."

            return AIResponse(
                provider=self._name,
                model=model,
                type=resp_type,
                intent=intent,
                params=params,
                content=str(content),
                usage=usage,
                metadata={
                    "parsed_json": extracted,
                    "reasoning": reasoning_text if reasoning_text else None,
                },
                raw_text=raw_text,
                success=True,
            )

        # 3. Oddiy matnli javob
        if _is_leaked_reasoning(raw_text):
            logger.warning(f"[{self._name}] Model ({model}) ichki inglizcha fikrlashni chiqardi. Filtrlanyapti.")
            raw_text = "So'rovingiz tushunildi. Natijani aniqlashtiryapman..."

        # Agar javob bo'sh bo'lsa (masalan model barcha tokenlarni reasoning da sarflagan yoki uzilib qolgan)
        if not raw_text.strip():
            raise MalformedResponseError(
                f"Provayder '{self._name}' ({model}) dan bo'sh javob olindi",
                provider=self._name,
                model=model,
            )

        return AIResponse(
            provider=self._name,
            model=model,
            type="answer",
            content=raw_text,
            usage=usage,
            metadata={"reasoning": reasoning_text if reasoning_text else None},
            raw_text=raw_text,
            success=True,
        )

    def generate(self, request: AIRequest) -> AIResponse:
        """Sinxron so'rov yuborish."""
        if not self.api_key:
            raise AuthenticationError(
                f"Provayder '{self._name}' uchun API kaliti topilmadi.",
                provider=self._name,
            )
        if self._health_monitor.is_cooling_down(self._name):
            raise RateLimitError(
                f"Provayder '{self._name}' hozirda sovutish (cooldown) holatida.",
                provider=self._name,
            )

        model = self._get_active_model(request)
        url = f"{self._base_url}/chat/completions"
        payload = self._build_payload(request, model=model, stream=False)
        headers = self._build_headers()

        start_time = time.time()
        try:
            logger.info(f"[{self._name.upper()}] So'rov yuborilmoqda: model='{model}'")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._timeout
            )

            # Agar model reasoning_effort parametrini qabul qilmasa (400), uni olib tashlab qayta yuborish
            if response.status_code == 400 and "reasoning_effort" in payload and "reasoning_effort" in response.text:
                payload.pop("reasoning_effort", None)
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self._timeout
                )

            latency_ms = (time.time() - start_time) * 1000.0

            # Xatoliklarni tekshirish va tasniflash
            if response.status_code == 429:
                retry_after = 60.0
                try:
                    if "retry-after" in response.headers:
                        retry_after = float(response.headers["retry-after"])
                except Exception:
                    pass
                err = RateLimitError(
                    f"{self._name.upper()} (429): Quota/Rate limit oshib ketdi.",
                    provider=self._name,
                    model=model,
                    retry_after_seconds=retry_after
                )
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            if response.status_code in (401, 403):
                err = AuthenticationError(
                    f"{self._name.upper()} ({response.status_code}): API kaliti yaroqsiz yoki ruxsat yo'q.",
                    provider=self._name,
                    model=model,
                    status_code=response.status_code
                )
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            if response.status_code == 404:
                err = ModelUnavailableError(
                    f"{self._name.upper()} (404): Model '{model}' topilmadi yoki mavjud emas.",
                    provider=self._name,
                    model=model
                )
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            if response.status_code >= 500:
                err = ServerNetworkError(
                    f"{self._name.upper()} ({response.status_code}): Server xatosi.",
                    provider=self._name,
                    model=model,
                    status_code=response.status_code
                )
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            if response.status_code != 200:
                err = ProviderError(
                    f"{self._name.upper()} kutilmagan status: {response.status_code} - {response.text[:150]}",
                    provider=self._name,
                    model=model,
                    status_code=response.status_code
                )
                self._health_monitor.record_failure(self._name, err, latency_ms)
                raise err

            raw_data = response.json()
            norm_resp = self._normalize_response(raw_data, model=model)
            norm_resp.metadata["latency_ms"] = latency_ms

            # Salomatlikni muvaffaqiyatli deb belgilash
            self._health_monitor.record_success(self._name, latency_ms)
            return norm_resp

        except requests.exceptions.Timeout as e:
            latency_ms = (time.time() - start_time) * 1000.0
            err = TimeoutError(
                f"{self._name.upper()} timeout ({self._timeout}s): {e}",
                provider=self._name,
                model=model,
                timeout_seconds=self._timeout
            )
            self._health_monitor.record_failure(self._name, err, latency_ms)
            raise err

        except requests.exceptions.RequestException as e:
            latency_ms = (time.time() - start_time) * 1000.0
            err = ServerNetworkError(
                f"{self._name.upper()} tarmoq ulanish xatosi: {e}",
                provider=self._name,
                model=model
            )
            self._health_monitor.record_failure(self._name, err, latency_ms)
            raise err

    def stream(self, request: AIRequest) -> Iterator[StreamChunk]:
        """Oqimli (streaming) tokenlar oqimini generatsiya qilish."""
        if not self.api_key:
            raise AuthenticationError(f"Provayder '{self._name}' uchun API kaliti topilmadi.", provider=self._name)
        if self._health_monitor.is_cooling_down(self._name):
            raise RateLimitError(f"Provayder '{self._name}' hozirda sovutish (cooldown) holatida.", provider=self._name)

        model = self._get_active_model(request)
        url = f"{self._base_url}/chat/completions"
        payload = self._build_payload(request, model=model, stream=True)
        headers = self._build_headers()

        start_time = time.time()
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=self._timeout
            )

            if response.status_code != 200:
                # Agar oqimli so'rov rad etilsa, oddiy rejimga o'tishga urinish
                logger.warning(f"[{self._name.upper()}] Streaming rad etildi ({response.status_code}), generate fallback...")
                full_resp = self.generate(request)
                yield StreamChunk(text=full_resp.content, is_final=True)
                return

            accumulated_text = ""
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices") or []
                        if choices:
                            delta = choices[0].get("delta") or {}
                            delta_text = delta.get("content") or ""
                            if delta_text:
                                accumulated_text += delta_text
                                yield StreamChunk(
                                    text=delta_text,
                                    is_final=False,
                                    finish_reason=choices[0].get("finish_reason")
                                )
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
        """Provayderning salomatlik holati."""
        return self._health_monitor.get_health(self._name)

    def supports(self, capability: str) -> bool:
        """Mavjud modellardan biri ushbu imkoniyatni qo'llab-quvvatlaydimi?"""
        models = self._registry.get_models_for_provider(self._name)
        return any(m.supports(capability) for m in models)

    def discover_models(self) -> List[str]:
        """API dan mavjud modellarni kashf etish."""
        return self._registry.discover_models_from_api(
            provider=self._name,
            api_key=self.api_key,
            base_url=self._base_url
        )
