# ========== core/providers/base.py ==========
# Misa AI 9.0.0 — Unified LLM Provider Base Interface & Metadata Types

import abc
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator

from core.intelligence.types import AIRequest, AIResponse
from core.intelligence.provider import AIProvider


class TaskCategory(str, Enum):
    """Misa topshiriq toifalari."""
    GENERAL_CHAT = "general_chat"
    REASONING = "reasoning"
    CODING = "coding"
    LONG_CONTEXT = "long_context"
    VISION = "vision"
    TOOL_CALLING = "tool_calling"
    FAST_RESPONSE = "fast_response"


class Capability(str, Enum):
    """Model imkoniyatlari."""
    CHAT = "chat"
    REASONING = "reasoning"
    CODING = "coding"
    TOOL_CALLING = "tool_calling"
    VISION = "vision"
    FAST_RESPONSE = "fast_response"
    LONG_CONTEXT = "long_context"


@dataclass
class StreamChunk:
    """Oqimli tokenlar (streaming chunk) modeli."""
    text: str
    is_final: bool = False
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    raw_chunk: Optional[Dict[str, Any]] = None


@dataclass
class ModelMetadata:
    """Model registri ma'lumotlari."""
    provider: str
    model: str
    base_url: str
    capabilities: List[str] = field(default_factory=list)
    context_window: int = 8192
    streaming: bool = True
    priority: int = 50  # 1-100 (yuqori son = yuqoriroq ustuvorlik)
    enabled: bool = True
    rpm: Optional[int] = None      # Requests Per Minute (bepul limit)
    rpd: Optional[int] = None      # Requests Per Day (bepul limit)
    tpm: Optional[int] = None      # Tokens Per Minute
    pricing: str = "free"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "capabilities": self.capabilities,
            "context_window": self.context_window,
            "streaming": self.streaming,
            "priority": self.priority,
            "enabled": self.enabled,
            "rpm": self.rpm if self.rpm is not None else "unknown",
            "rpd": self.rpd if self.rpd is not None else "unknown",
            "tpm": self.tpm if self.tpm is not None else "unknown",
            "pricing": self.pricing,
            "description": self.description,
        }

    def supports(self, capability: str) -> bool:
        cap_val = capability.value if isinstance(capability, Enum) else str(capability).lower()
        return cap_val in [c.lower() for c in self.capabilities]


@dataclass
class ProviderHealth:
    """Provayderning salomatlik holati (Health State)."""
    provider: str
    status: str = "healthy"  # healthy | degraded | cooling_down | unavailable
    latency_ms: float = 0.0
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    consecutive_failures: int = 0
    cooldown_until: Optional[float] = None
    success_count: int = 0
    failure_count: int = 0
    rate_limit_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "consecutive_failures": self.consecutive_failures,
            "cooldown_until": self.cooldown_until,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "rate_limit_count": self.rate_limit_count,
        }


class LLMProvider(AIProvider):
    """
    Barcha LLM provayderlari (Gemini, Groq, Cerebras, OpenRouter, NVIDIA NIM, va h.k.)
    uchun umumiy kuchli interfeys.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provayder identifikatori (masalan: 'groq', 'gemini', 'cerebras')."""
        pass

    @property
    def base_url(self) -> str:
        """API asosiy manzili."""
        return ""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """API kaliti sozlangan va provayder faol ekanligini bildiradi."""
        pass

    @abc.abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Sinxron so'rov yuborish va normalizatsiya qilingan AIResponse qaytarish."""
        pass

    @abc.abstractmethod
    def stream(self, request: AIRequest) -> Iterator[StreamChunk]:
        """Oqimli (streaming) tokenlar oqimini qaytarish."""
        pass

    @abc.abstractmethod
    def health_check(self) -> ProviderHealth:
        """Provayderning hozirgi holati va salomatligini tekshirish."""
        pass

    def supports(self, capability: str) -> bool:
        """Ushbu provayder ma'lum bir imkoniyatni (masalan: 'vision', 'tool_calling') qo'llab-quvvatlaydimi?"""
        return False

    def metadata(self) -> Dict[str, Any]:
        """Provayder haqida metama'lumotlar."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "available": self.is_available(),
        }

    def discover_models(self) -> List[str]:
        """Provayder API sidan mavjud modellarni dinamik o'qib olish (agar qo'llab-quvvatlasa)."""
        return []
