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
        "model": "qwen/qwen3.8-27b",
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
        "priority": 96,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "tpm": 20000,
        "pricing": "free",
        "description": "Qwen 3.8 27B Groq LPU da — Misa uchun o'zbek tilini mukammal tushunuvchi ultra-tezkor asosiy model.",
    },
    {
        "provider": "groq",
        "model": "openai/gpt-oss-120b",
        "base_url": "https://api.groq.com/openai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 95,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "tpm": 6000,
        "pricing": "free",
        "description": "OpenAI GPT-OSS 120B Groq da — chuqur mantiqiy fikrlash (reasoning) va dasturlash modeli.",
    },
    {
        "provider": "groq",
        "model": "openai/gpt-oss-20b",
        "base_url": "https://api.groq.com/openai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.FAST_RESPONSE.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 90,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "tpm": 20000,
        "pricing": "free",
        "description": "Ultra-tezkor GPT-OSS 20B — tezkor qisqa javoblar uchun.",
    },

    # ---------- 2. CEREBRAS (Tier 1: Wafer-Scale rekord tezlik, 30 RPM, 1M daily tokens) ----------
    {
        "provider": "cerebras",
        "model": "qwen-3.8-27b",
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
        "priority": 94,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "pricing": "free",
        "description": "Cerebras CS-3 da Qwen 3.8 27B — 2000+ token/s rekord tezlikdagi o'zbek tili va agent modeli.",
    },
    {
        "provider": "cerebras",
        "model": "gpt-oss-120b",
        "base_url": "https://api.cerebras.ai/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 93,
        "enabled": True,
        "rpm": 30,
        "rpd": 14400,
        "pricing": "free",
        "description": "Cerebras CS-3 mikrosxemasida GPT-OSS 120B — kuchli mantiq va kod generatsiyasi.",
    },

    # ---------- 3. GOOGLE GEMINI (Tier 1: Multimodal, Vision, Search Grounding, 1M Context) ----------
    {
        "provider": "gemini",
        "model": "gemini-flash-lite-latest",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "capabilities": [
            Capability.CHAT.value,
            Capability.FAST_RESPONSE.value,
            Capability.LONG_CONTEXT.value,
            Capability.VISION.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 1048576,
        "streaming": True,
        "priority": 95,
        "enabled": True,
        "rpm": 30,
        "rpd": 1500,
        "pricing": "free",
        "description": "Google Gemini Flash Lite Latest — o'ta barqaror, chaqmoq tezligidagi multimodal model.",
    },
    {
        "provider": "gemini",
        "model": "gemini-flash-latest",
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
        "priority": 94,
        "enabled": True,
        "rpm": 15,
        "rpd": 1500,
        "pricing": "free",
        "description": "Google Gemini Flash Latest — universal multimodal va agent vazifalar uchun.",
    },
    {
        "provider": "gemini",
        "model": "gemini-3.8-flash",
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
        "priority": 96,
        "enabled": True,
        "rpm": 15,
        "rpd": 1500,
        "pricing": "free",
        "description": "Google Gemini 3.8 Flash — eng so'nggi avlod yuqori intellektli model.",
    },

    # ---------- 4. OPENROUTER (Tier 1 Fallback: 30+ Bepul modellar agregatori) ----------
    {
        "provider": "openrouter",
        "model": "nvidia/nemotron-3.5-lightning:free",
        "base_url": "https://openrouter.ai/api/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.REASONING.value,
            Capability.CODING.value,
            Capability.TOOL_CALLING.value,
        ],
        "context_window": 131072,
        "streaming": True,
        "priority": 82,
        "enabled": True,
        "rpm": 20,
        "pricing": "free",
        "description": "NVIDIA Nemotron 3.5 Lightning (Free) — OpenRouter da barqaror tezkor model.",
    },
    {
        "provider": "openrouter",
        "model": "liquid/lfm-2.5-2.6b:free",
        "base_url": "https://openrouter.ai/api/v1",
        "capabilities": [
            Capability.CHAT.value,
            Capability.FAST_RESPONSE.value,
        ],
        "context_window": 32768,
        "streaming": True,
        "priority": 81,
        "enabled": True,
        "rpm": 20,
        "pricing": "free",
        "description": "Liquid LFM 2.5 (Free) — yengil va tezkor zaxira model.",
    },
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
