# ========== openrouter_provider.py ==========
# Misa AI 7.x — OpenRouter AI Provider Implementation
# Universal OpenAI-compatible Fallback Provider with Response Normalization

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
    """Matn ichidan JSON obyektini xavfsiz ajratib olish (nested qavslar va strict=False bilan)"""
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


class OpenRouterProvider(AIProvider):
    """OpenRouter universal AI provayderi (fallback uchun)"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self._model = model or os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

    @property
    def name(self) -> str:
        return "openrouter"

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def generate(self, request: AIRequest) -> AIResponse:
        """OpenRouter API orqali so'rov yuborish va normalizatsiya qilingan AIResponse qaytarish"""
        if not self.is_available():
            return AIResponse(
                provider=self.name,
                model="none",
                type="error",
                content="OpenRouter API kaliti topilmadi.",
                success=False,
                error_code="API_KEY_MISSING"
            )

        # 1. System Prompt
        system_text = ""
        if request.system_context:
            system_text = request.system_context.get("prompt", "")
        if not system_text and "system_prompt" in request.metadata:
            system_text = request.metadata["system_prompt"]

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
        messages.append({"role": "user", "content": request.message})

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://misa-ai.uz",
            "X-Title": "Misa AI Desktop",
        }
        body = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.3,
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=15)
            if response.status_code != 200:
                err_msg = f"HTTP {response.status_code}: {response.text[:150]}"
                logger.warning(f"OpenRouter xatosi: {err_msg}")
                return AIResponse(
                    provider=self.name,
                    model=self._model,
                    type="error",
                    content=f"OpenRouter xatosi: {err_msg}",
                    success=False,
                    error_code="OPENROUTER_HTTP_ERROR"
                )

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return AIResponse(
                    provider=self.name,
                    model=self._model,
                    type="error",
                    content="OpenRouter javobida 'choices' topilmadi.",
                    success=False,
                    error_code="OPENROUTER_EMPTY_RESPONSE"
                )

            ai_text = choices[0].get("message", {}).get("content", "").strip()
            usage = data.get("usage", {})

            return self._normalize_response(ai_text, self._model, usage)

        except Exception as e:
            logger.error(f"OpenRouter so'rovida istisno: {e}")
            return AIResponse(
                provider=self.name,
                model=self._model,
                type="error",
                content=f"OpenRouter bog'lanish xatosi: {e}",
                success=False,
                error_code="OPENROUTER_EXCEPTION"
            )

    def _normalize_response(self, text: str, model: str, usage: dict) -> AIResponse:
        """OpenRouter javobini normalizatsiya qilingan AIResponse ga aylantirish"""
        from core.intelligence.text_cleaner import extract_clean_response_text
        parsed = _extract_json_from_text(text)

        if parsed and isinstance(parsed, dict):
            resp_type = parsed.get("type", "answer").lower()
            intent = parsed.get("intent")
            params = parsed.get("params", {})
            raw_content = parsed.get("response") or parsed.get("content") or parsed.get("javob") or ""
            content = extract_clean_response_text(raw_content)

            if resp_type in ("command", "action"):
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="command",
                    content=content or f"Buyruq bajarilmoqda: {intent}",
                    intent=intent,
                    params=params,
                    usage=usage,
                    raw_text=text,
                    success=True
                )
            elif resp_type == "clarification":
                question = extract_clean_response_text(parsed.get("question") or content)
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="clarification",
                    content=question,
                    intent=intent,
                    params=params,
                    usage=usage,
                    raw_text=text,
                    success=True
                )
            elif resp_type == "confirmation":
                question = extract_clean_response_text(parsed.get("question") or content)
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="confirmation",
                    content=question,
                    intent=intent,
                    params=params,
                    usage=usage,
                    raw_text=text,
                    success=True
                )
            else:
                return AIResponse(
                    provider=self.name,
                    model=model,
                    type="answer",
                    content=content or extract_clean_response_text(text),
                    intent=intent,
                    params=params,
                    usage=usage,
                    raw_text=text,
                    success=True
                )

        # Matnli javob yoki uzilib qolgan JSON
        clean_text_ans = extract_clean_response_text(text)
        return AIResponse(
            provider=self.name,
            model=model,
            type="answer",
            content=clean_text_ans,
            usage=usage,
            raw_text=text,
            success=True
        )
