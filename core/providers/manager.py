# ========== core/providers/manager.py ==========
# Misa AI 9.0.0 — Unified Provider System Manager & Facade

import logging
from typing import Dict, Any, Optional, List, Iterator

from core.intelligence.types import AIRequest, AIResponse
from core.providers.base import LLMProvider, StreamChunk, ModelMetadata, ProviderHealth
from core.providers.registry import ModelRegistry, get_model_registry
from core.providers.health import HealthMonitor, get_health_monitor
from core.providers.config import ProviderConfigManager, get_provider_config_manager
from core.providers.openai_compatible import OpenAICompatibleProvider
from core.providers.gemini import GeminiProvider
from core.providers.router import ModelRouter

logger = logging.getLogger(__name__)


class ProviderSystem:
    """
    Misa AI Ko'p Provayderli Tizimi.
    Barcha provayderlar (Groq, Cerebras, Gemini, OpenRouter, NVIDIA NIM),
    registry, health monitor va router ni yagona nuqtadan boshqaradi.
    """

    def __init__(self):
        self.registry = get_model_registry()
        self.health_monitor = get_health_monitor()
        self.config_manager = get_provider_config_manager()

        # Provayder instansiyalarini yaratish
        self._providers: Dict[str, LLMProvider] = {}
        self._init_default_providers()

        # Intellektual routerni o'rnatish
        self.router = ModelRouter(
            providers=self._providers,
            registry=self.registry,
            health_monitor=self.health_monitor,
            config_manager=self.config_manager,
            max_retries=4
        )

    def _init_default_providers(self):
        """Asosiy saralangan provayderlarni ishga tushirish."""
        # 1. Groq (Tier 1 Primary: ultra-tez, 30 RPM, 14.4k RPD)
        self._providers["groq"] = OpenAICompatibleProvider(
            name="groq",
            base_url="https://api.groq.com/openai/v1",
            default_model="qwen/qwen3.8-27b",
            timeout=15.0
        )

        # 2. Cerebras (Tier 1 Fallback/Primary: Wafer-scale tezlik, 30 RPM, 1M daily tokens)
        self._providers["cerebras"] = OpenAICompatibleProvider(
            name="cerebras",
            base_url="https://api.cerebras.ai/v1",
            default_model="qwen-3.8-27b",
            timeout=15.0
        )

        # 3. Google Gemini (Tier 1 Multimodal/Vision: 1M kontekst, Grounding, 15 RPM)
        self._providers["gemini"] = GeminiProvider(
            default_model="gemini-flash-lite-latest",
            timeout=18.0
        )

        # 4. OpenRouter (Tier 1 Fallback Aggregator: 30+ bepul modellar)
        self._providers["openrouter"] = OpenAICompatibleProvider(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            default_model="nvidia/nemotron-3.5-lightning:free",
            timeout=20.0
        )

        # 5. NVIDIA NIM (Tier 1 ixtisoslashgan: Nemotron / DeepSeek R1)
        self._providers["nvidia"] = OpenAICompatibleProvider(
            name="nvidia",
            base_url="https://integrate.api.nvidia.com/v1",
            default_model="meta/llama-3.3-70b-instruct",
            timeout=20.0
        )

    def register_provider(self, provider: LLMProvider):
        """Maxsus (custom) yoki yangi provayderni qo'shish."""
        self._providers[provider.name.lower()] = provider
        self.router.register_provider(provider)

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name.lower())

    def get_available_providers(self) -> List[str]:
        """Kaliti mavjud va ayni paytda tayyor bo'lgan provayderlar ro'yxati."""
        return [p.name for p in self._providers.values() if p.is_available()]

    def is_any_available(self) -> bool:
        """Kamida bitta provayder ishga tayyormi?"""
        return any(p.is_available() for p in self._providers.values())

    def generate(self, request: AIRequest) -> AIResponse:
        """Intellektual router orqali eng yaxshi modelga so'rov yuborish va fallback qilish."""
        return self.router.route_and_generate(request)

    def stream(self, request: AIRequest) -> Iterator[StreamChunk]:
        """Tokenlarni oqimli (stream) ravishda chiqarish."""
        return self.router.route_and_stream(request)

    def get_status_summary(self) -> Dict[str, Any]:
        """UI va API uchun xavfsiz holat hisoboti (API kalitlarni oshkor qilmaydi)."""
        providers_status = {}
        for p_name, p in self._providers.items():
            health = self.health_monitor.get_health(p_name)
            cfg_enabled = self.config_manager.is_provider_enabled(p_name)
            cfg_prio = self.config_manager.get_provider_priority(p_name)
            available = p.is_available()
            key = getattr(p, "api_key", "")
            has_key = bool(key and str(key).strip())

            masked_key = ""
            if has_key and len(key) > 8:
                masked_key = key[:4] + "..." + key[-4:]

            models = [m.model for m in self.registry.get_models_for_provider(p_name, only_enabled=True)]

            providers_status[p_name] = {
                "name": p_name,
                "configured": has_key,
                "enabled": cfg_enabled,
                "available": available,
                "priority": cfg_prio,
                "status": health.status,
                "latency_ms": round(health.latency_ms, 1),
                "last_success": health.last_success,
                "last_failure": health.last_failure,
                "consecutive_failures": health.consecutive_failures,
                "cooldown_until": health.cooldown_until,
                "masked_key": masked_key,
                "models": models,
            }

        return {
            "total_providers": len(self._providers),
            "available_providers_count": len(self.get_available_providers()),
            "any_available": self.is_any_available(),
            "providers": providers_status,
        }

    def discover_all_models(self) -> Dict[str, List[str]]:
        """Barcha faol provayderlardan dinamik model ro'yxatini so'rab yangilash."""
        results = {}
        for p_name, p in self._providers.items():
            if p.is_available():
                found = p.discover_models()
                results[p_name] = found
        return results


_global_provider_system: Optional[ProviderSystem] = None


def get_provider_system() -> ProviderSystem:
    global _global_provider_system
    if _global_provider_system is None:
        _global_provider_system = ProviderSystem()
    return _global_provider_system
