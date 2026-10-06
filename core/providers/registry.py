# ========== core/providers/registry.py ==========
# Misa AI 9.0.0 — Curated LLM Model Registry & Dynamic Model Discovery

import json
import logging
from typing import Dict, List, Optional, Any
import requests

from core.providers.base import ModelMetadata, Capability

logger = logging.getLogger(__name__)


# Rasmiy provayder hujjatlari va awesome-freellm-apis ma'lumotlariga asoslangan saralangan modellar registri
CURATED_MODELS: List[Dict[str, Any]] = [
    # ---------- 1. GROQ (Tier 1: Ultra-tez, 30 RPM, 14.4k RPD, Bepul) ----------
    {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
            Capability.FAST_RESPONSE.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 95,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "tpm": 6000,
        "pricing": "free",
        "description": "Meta Llama 3.3 70B Groq LPU tezlatkichida — Misa uchun asosiy agent va dasturlash modeli.",
    },
    {
        "provider": "groq",
        "model": "llama-3.1-8b-instant",
        "base_url": "https://api.groq.com/openai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.FAST_RESPONSE.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 88,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "tpm": 20000,
        "pricing": "free",
        "description": "Ultra-tezkor 8B model — qisqa buyruqlar va tezkor ovozli muloqot uchun ideal.",
    },
    {
        "provider": "groq",
        "model": "mixtral-8x7b-32768",
        "base_url": "https://api.groq.com/openai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.FAST_RESPONSE.value,
        ],
        "context_window": 32768,
        "streaming": True,
        "priority": 75,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "pricing": "free",
        "description": "Mixtral 8x7B MoE modeli — barqaror tezkor suhbat.",
    },

    # ---------- 2. CEREBRAS (Tier 1: Wafer-Scale rekord tezlik, 30 RPM, 1M daily tokens) ----------
    {
        "provider": "cerebras",
        "model": "llama-3.3-70b",
        "base_url": "https://api.cerebras.ai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
            Capability.FAST_RESPONSE.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 93,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "pricing": "free",
        "description": "Cerebras CS-3 mikrosxemasida Llama 3.3 70B (~2000 token/soniya) — Groq bilan birgalikda 1-darajali zaxira.",
    },
    {
        "provider": "cerebras",
        "model": "llama3.1-70b",
        "base_url": "https://api.cerebras.ai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
            Capability.FAST_RESPONSE.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 90,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "pricing": "free",
        "description": "Cerebras Llama 3.1 70B — yuqori aniqlikdagi tezkor tahlil.",
    },
    {
        "provider": "cerebras",
        "model": "llama3.1-8b",
        "base_url": "https://api.cerebras.ai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.FAST_RESPONSE.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 84,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "pricing": "free",
        "description": "Cerebras 8B — 1800+ tok/s tezlikdagi yengil model.",
    },

    # ---------- 3. GOOGLE GEMINI (Tier 1: Multimodal, Vision, Search Grounding, 1M Context) ----------
    {
        "provider": "gemini",
        "model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
            Capability.VISION.value,
            Capability.LONG_CONTEXT.value,
            Capability.FAST_RESPONSE.value,
        ],
        "context_window": 1048576,
        "streaming": True,
        "priority": 94,
        "enabled": True,
        "rpm": 15,
        "rpd": 1500,
        "tpm": 1000000,
        "pricing": "free",
        "description": "Google Gemini 2.0 Flash — ekran tahlili (vision), qidiruv va 1M kontekst uchun eng kuchli model.",
    },
    {
        "provider": "gemini",
        "model": "gemini-2.0-flash-lite",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "capabilities": [
            Capability.CHAT.value,
            Capability.FAST_RESPONSE.value,
            Capability.LONG_CONTEXT.value,
            Capability.VISION.value,
        ],
        "context_window": 1048576,
        "streaming": True,
        "priority": 87,
        "enabled": True,
        "rpm": 30,
        "rpd": 1500,
        "pricing": "free",
        "description": "Gemini 2.0 Flash Lite — tejamkor va tezkor multimodal model.",
    },
    {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
            Capability.VISION.value,
            Capability.LONG_CONTEXT.value,
        ],
        "context_window": 1048576,
        "streaming": True,
        "priority": 89,
        "enabled": True,
        "rpm": 10,
        "pricing": "free",
        "description": "Gemini 2.5 Flash — chuqur mantiq va ekran tasvirlarini tahlil qilish uchun.",
    },
    {
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "capabilities": [
            Capability.CHAT.value,
            Capability.VISION.value,
            Capability.TOOL_CALLING.value,
            Capability.LONG_CONTEXT.value,
        ],
        "context_window": 1048576,
        "streaming": True,
        "priority": 78,
        "enabled": True,
        "rpm": 15,
        "rpd": 1500,
        "pricing": "free",
        "description": "Gemini 1.5 Flash — barqaror zaxira multimodal model.",
    },

    # ---------- 4. OPENROUTER (Tier 1 Fallback: 30+ Bepul modellar agregatori) ----------
    {
        "provider": "openrouter",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "base_url": "https://openrouter.ai/api/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 80,
        "enabled": True,
        "rpm": 20,
        "pricing": "free",
        "description": "OpenRouter bepul Llama 3.3 70B — universal zaxira.",
    },
    {
        "provider": "openrouter",
        "model": "google/gemini-2.0-flash-exp:free",
        "base_url": "https://openrouter.ai/api/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
            Capability.VISION.value,
            Capability.LONG_CONTEXT.value,
        ],
        "context_window": 1048576,
        "streaming": True,
        "priority": 79,
        "enabled": True,
        "rpm": 20,
        "pricing": "free",
        "description": "OpenRouter bepul Gemini 2.0 Flash — tashqi multimodal fallback.",
    },
    {
        "provider": "openrouter",
        "model": "deepseek/deepseek-r1:free",
        "base_url": "https://openrouter.ai/api/v1",
        "capabilities": [
            Capability.REASONING.value,
            Capability.CODING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 77,
        "enabled": True,
        "rpm": 20,
        "pricing": "free",
        "description": "DeepSeek R1 fikrlash (Reasoning) modeli — murakkab mantiqiy va algoritmli savollar uchun.",
    },
    {
        "provider": "openrouter",
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "base_url": "https://openrouter.ai/api/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
        ],
        "context_window": 262144,
        "streaming": True,
        "priority": 73,
        "enabled": True,
        "pricing": "free",
        "description": "OpenRouter orqali NVIDIA Nemotron 120B — keng kontekstli tahlil.",
    },

    # ---------- 5. NVIDIA NIM (Tier 1 ixtisoslashgan: 1000 bepul kredit, Nemotron) ----------
    {
        "provider": "nvidia",
        "model": "meta/llama-3.3-70b-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 74,
        "enabled": True,
        "rpm": 40,
        "pricing": "free_credits",
        "description": "NVIDIA NIM orqali Llama 3.3 70B — yuqori unumdorlikdagi enterprise infratuzilma.",
    },
    {
        "provider": "nvidia",
        "model": "deepseek-ai/deepseek-r1",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "capabilities": [
            Capability.REASONING.value,
            Capability.CODING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 72,
        "enabled": True,
        "rpm": 40,
        "pricing": "free_credits",
        "description": "NVIDIA NIM orqali DeepSeek R1 — professional darajadagi reasoning modeli.",
    },
    {
        "provider": "nvidia",
        "model": "nvidia/llama-3.1-nemotron-70b-instruct",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 70,
        "enabled": True,
        "rpm": 40,
        "pricing": "free_credits",
        "description": "NVIDIA Nemotron 70B — alignment va dialogga moslashtirilgan kuchli model.",
    },
]


class ModelRegistry:
    """
    Misa AI Ko'p Provayderli Modellar Registri.
    Modellarni saqlaydi, qidiradi, saralaydi va provayder API lari orqali
    dinamik kashfiyot (dynamic discovery) o'tkazadi.
    """

    def __init__(self, models: Optional[List[ModelMetadata]] = None):
        self._models: Dict[str, ModelMetadata] = {}
        if models:
            for m in models:
                self.register(m)
        else:
            self._load_curated_models()

    def _key(self, provider: str, model: str) -> str:
        return f"{provider.lower()}::{model.strip()}"

    def _load_curated_models(self):
        """Dastlabki saralangan modellarni registratsiya qilish."""
        for item in CURATED_MODELS:
            meta = ModelMetadata(
                provider=item["provider"].lower(),
                model=item["model"],
                base_url=item["base_url"],
                capabilities=item.get("capabilities", []),
                context_window=item.get("context_window", 8192),
                streaming=item.get("streaming", True),
                priority=item.get("priority", 50),
                enabled=item.get("enabled", True),
                rpm=item.get("rpm"),
                rpd=item.get("rpd"),
                tpm=item.get("tpm"),
                pricing=item.get("pricing", "free"),
                description=item.get("description", ""),
            )
            self.register(meta)

    def register(self, metadata: ModelMetadata):
        """Modelni registrga qo'shish yoki yangilash."""
        key = self._key(metadata.provider, metadata.model)
        self._models[key] = metadata

    def get_model(self, provider: str, model: str) -> Optional[ModelMetadata]:
        """Provayder va model nomi bo'yicha qidirish."""
        return self._models.get(self._key(provider, model))

    def get_models_for_provider(self, provider: str, only_enabled: bool = True) -> List[ModelMetadata]:
        """Bitta provayderga tegishli barcha modellar."""
        prov = provider.lower()
        res = [m for m in self._models.values() if m.provider == prov]
        if only_enabled:
            res = [m for m in res if m.enabled]
        return sorted(res, key=lambda x: x.priority, reverse=True)

    def get_models_by_capability(self, capability: str, only_enabled: bool = True) -> List[ModelMetadata]:
        """Ma'lum bir qobiliyatga (masalan: 'tool_calling', 'vision') ega modellar."""
        res = [m for m in self._models.values() if m.supports(capability)]
        if only_enabled:
            res = [m for m in res if m.enabled]
        return sorted(res, key=lambda x: x.priority, reverse=True)

    def get_all_models(self, only_enabled: bool = False) -> List[ModelMetadata]:
        """Barcha modellar ro'yxati."""
        models = list(self._models.values())
        if only_enabled:
            models = [m for m in models if m.enabled]
        return sorted(models, key=lambda x: x.priority, reverse=True)

    def set_enabled(self, provider: str, model: str, enabled: bool) -> bool:
        """Modelni faollashtirish yoki o'chirish."""
        meta = self.get_model(provider, model)
        if meta:
            meta.enabled = enabled
            return True
        return False

    def discover_models_from_api(self, provider: str, api_key: str, base_url: str) -> List[str]:
        """
        Provayderning `/models` endpointi orqali mavjud modellarni dinamik o'qib olish.
        OpenAI-compatible provayderlar (Groq, Cerebras, OpenRouter, NVIDIA NIM) uchun to'liq ishlaydi.
        """
        if not api_key or not base_url:
            return []

        clean_base = base_url.rstrip("/")
        models_url = f"{clean_base}/models"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MisaAI/9.0.0",
        }

        try:
            resp = requests.get(models_url, headers=headers, timeout=8)
            if resp.status_code != 200:
                logger.debug(f"[Discovery] {provider} /models so'rovi muvaffaqiyatsiz ({resp.status_code})")
                return []

            data = resp.json()
            items = data.get("data") or []
            discovered_ids = []

            for item in items:
                mid = item.get("id") if isinstance(item, dict) else str(item)
                if not mid:
                    continue
                discovered_ids.append(mid)

                # Agar model bizning registrda bo'lsa, mavjudligini tasdiqlaymiz
                existing = self.get_model(provider, mid)
                if not existing:
                    # Yangi topilgan modelni xavfsiz default bilan ro'yxatdan o'tkazamiz
                    new_meta = ModelMetadata(
                        provider=provider.lower(),
                        model=mid,
                        base_url=clean_base,
                        capabilities=[Capability.CHAT.value],
                        context_window=item.get("context_window", 8192) if isinstance(item, dict) else 8192,
                        priority=30,  # Yangi noma'lum modellar pastroq ustuvorlikda
                        enabled=True,
                        description=f"{provider.upper()} API dan dinamik kashf etilgan model.",
                    )
                    self.register(new_meta)

            logger.info(f"[Discovery] {provider} dan {len(discovered_ids)} ta model topildi.")
            return discovered_ids

        except Exception as e:
            logger.debug(f"[Discovery] {provider} modellarini aniqlashda xatolik: {e}")
            return []


_global_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ModelRegistry()
    return _global_registry
