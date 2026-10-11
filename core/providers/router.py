# ========== core/providers/router.py ==========
# Misa AI 9.0.0 — Intelligent Model Router & Deterministic Fallback Engine

import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Iterator

from core.intelligence.types import AIRequest, AIResponse
from core.providers.base import (
    LLMProvider,
    StreamChunk,
    ModelMetadata,
    TaskCategory,
    Capability,
    ProviderHealth,
)
from core.providers.registry import ModelRegistry, get_model_registry
from core.providers.health import HealthMonitor, get_health_monitor
from core.providers.config import ProviderConfigManager, get_provider_config_manager
from core.providers.errors import (
    ProviderError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    ServerNetworkError,
    ModelUnavailableError,
)

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Misa AI Intellektual Routeri.
    1. Vazifani tahlil qiladi (Task Classification)
    2. Kerakli imkoniyatlarni aniqlaydi (Required Capabilities)
    3. Eng mos model va provayderlarni ballaydi (Model Scoring)
    4. Salomatlik (Health Check) va cooldown holatini hisobga oladi
    5. Fallback zanjiri orqali so'rovni uzatadi
    """

    def __init__(
        self,
        providers: Optional[Dict[str, LLMProvider]] = None,
        registry: Optional[ModelRegistry] = None,
        health_monitor: Optional[HealthMonitor] = None,
        config_manager: Optional[ProviderConfigManager] = None,
        max_retries: int = 3,
    ):
        self._providers: Dict[str, LLMProvider] = providers or {}
        self._registry = registry or get_model_registry()
        self._health_monitor = health_monitor or get_health_monitor()
        self._config_manager = config_manager or get_provider_config_manager()
        self._max_retries = max_retries

    def register_provider(self, provider: LLMProvider):
        """Provayder obyektini qo'shish."""
        self._providers[provider.name.lower()] = provider

    def get_provider(self, name: str) -> Optional[LLMProvider]:
        return self._providers.get(name.lower())

    def get_registered_providers(self) -> List[str]:
        return list(self._providers.keys())

    # ========================================================
    # 1. TASK CLASSIFICATION (Vazifani tasniflash)
    # ========================================================
    def classify_task(self, request: AIRequest) -> TaskCategory:
        """Foydalanuvchi so'rovi va kontekstini topshiriq toifasiga ajratish."""
        meta = request.metadata or {}
        message = (request.message or "").lower().strip()

        # A) Vision
        if "image_base64" in meta or meta.get("vision") or any(k in message for k in ["ekran", "screenshot", "ko'rinmoqda", "rasm", "tasvir"]):
            return TaskCategory.VISION

        # B) Tool Calling (Agentlik vositalari)
        if request.tools or meta.get("requires_tool"):
            return TaskCategory.TOOL_CALLING

        # C) Coding (Dasturlash, kod va xatolar)
        code_keywords = [
            "python", "javascript", "typescript", "c++", "rust", "sql", "html", "css",
            "kod", "funksiya", "class", "algoritm", "bug", "xatolik", "traceback",
            "script", "def ", "import ", "regex", "api", "backend", "frontend"
        ]
        if any(ck in message for ck in code_keywords):
            return TaskCategory.CODING

        # D) Long Context (Katta hujjatlar va kontekst)
        total_len = len(request.message or "")
        if request.conversation:
            total_len += sum(len(c.get("content", "")) for c in request.conversation)
        if total_len > 12000 or meta.get("long_context"):
            return TaskCategory.LONG_CONTEXT

        # E) Reasoning (Chuqur mantiq, fikrlash va tahlil)
        reasoning_keywords = [
            "tahlil qil", "mantiqan", "isbotla", "reja tuz", "taqqosla", "chuqur o'yla",
            "farqini tushuntir", "qanday ishlaydi", "sababi nima", "step-by-step", "bosqichma-bosqich"
        ]
        if any(rk in message for rk in reasoning_keywords) or meta.get("reasoning"):
            return TaskCategory.REASONING

        # F) Fast Response (Qisqa buyruqlar, salomlashish, tezkor ovoz)
        if len(message) < 40 or meta.get("fast_response") or any(w in message for w in ["salom", "assalom", "vaqt", "soat", "ovoz", "ob-havo"]):
            return TaskCategory.FAST_RESPONSE

        # G) Standart suhbat
        return TaskCategory.GENERAL_CHAT

    # ========================================================
    # 2. REQUIRED CAPABILITIES (Kerakli qobiliyatlar)
    # ========================================================
    def get_required_capabilities(self, task: TaskCategory) -> List[str]:
        """Vazifaga ko'ra modeldan talab qilinadigan imkoniyatlar ro'yxati."""
        mapping = {
            TaskCategory.VISION: [Capability.VISION.value, Capability.CHAT.value],
            TaskCategory.TOOL_CALLING: [Capability.TOOL_CALLING.value, Capability.CHAT.value],
            TaskCategory.CODING: [Capability.CODING.value, Capability.CHAT.value],
            TaskCategory.REASONING: [Capability.REASONING.value, Capability.CHAT.value],
            TaskCategory.LONG_CONTEXT: [Capability.LONG_CONTEXT.value, Capability.CHAT.value],
            TaskCategory.FAST_RESPONSE: [Capability.FAST_RESPONSE.value, Capability.CHAT.value],
            TaskCategory.GENERAL_CHAT: [Capability.CHAT.value],
        }
        return mapping.get(task, [Capability.CHAT.value])

    # ========================================================
    # 3. MODEL SCORING & SELECTION (Model va provayderlarni baholash)
    # ========================================================
    def select_candidate_models(
        self,
        request: AIRequest,
        task: Optional[TaskCategory] = None
    ) -> List[Tuple[LLMProvider, ModelMetadata, float]]:
        """
        Mavjud barcha modellarni vazifa, salomatlik va ustuvorlik bo'yicha baholaydi.
        Qaytaradi: [(provayder, model_metadata, ball), ...] — eng yuqori balldan boshlab.
        """
        actual_task = task or self.classify_task(request)
        required_caps = self.get_required_capabilities(actual_task)
        candidates = []

        all_models = self._registry.get_all_models(only_enabled=True)

        for model_meta in all_models:
            p_name = model_meta.provider
            provider = self._providers.get(p_name)
            if not provider:
                continue

            # Konfiguratsiya orqali o'chirilgan bo'lsa o'tkazib yuborish
            if not self._config_manager.is_provider_enabled(p_name):
                continue

            # API kaliti mavjud bo'lmasa o'tkazib yuborish
            if not provider.is_available():
                continue

            score = 0.0

            # 1. Imkoniyatlar mosligi (Capabilities Match)
            # Agar majburiy talab (masalan: vision) modelda bo'lmasa, uni tanlamaymiz!
            if actual_task == TaskCategory.VISION and not model_meta.supports(Capability.VISION.value):
                continue
            if actual_task == TaskCategory.TOOL_CALLING and not model_meta.supports(Capability.TOOL_CALLING.value):
                # Tool calling uchun faqat tool calling ni aniq biladigan modellar
                continue

            for cap in required_caps:
                if model_meta.supports(cap):
                    score += 35.0

            # 2. Modelning o'z ustuvorligi (1-100)
            score += (model_meta.priority * 0.4)

            # 3. Provayderning konfiguratsiyadagi ustuvorligi (1-100)
            cfg_prio = self._config_manager.get_provider_priority(p_name)
            score += (cfg_prio * 0.4)

            # 4. Provayder salomatlik holati (Health State)
            health = self._health_monitor.get_health(p_name)
            if health.status == "healthy":
                score += 25.0
            elif health.status == "degraded":
                score -= 15.0
            elif health.status == "cooling_down":
                score -= 100.0  # Sovutishdagi provayder pastga tushadi

            # 5. Kechikish (Latency penalty)
            if health.latency_ms > 0:
                score -= min(30.0, health.latency_ms / 150.0)

            # 6. Tezkorlik talab etilsa Groq va Cerebras ga bonus
            if actual_task == TaskCategory.FAST_RESPONSE and p_name in ("groq", "cerebras"):
                score += 20.0

            candidates.append((provider, model_meta, score))

        # Ballar bo'yicha kamayish tartibida saralash
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates

    # ========================================================
    # 4. EXECUTION WITH AUTOMATIC FALLBACK
    # ========================================================
    def route_and_generate(self, request: AIRequest) -> AIResponse:
        """
        Avtomatik intellektual marshrutlash va nosozlikda zaxira (fallback) provayderga o'tish:
        1. Vazifani aniqlash
        2. Eng yaxshi provayder va modelni tanlash
        3. 429, timeout, network error bo'lsa, keyingi provayderga avtomatik o'tish
        """
        task = self.classify_task(request)
        logger.info(f"[ModelRouter] Topshiriq toifasi aniqlandi: '{task.value}'")

        candidates = self.select_candidate_models(request, task=task)

        if not candidates:
            # Hech qaysi provayder API kaliti bilan sozlanmagan
            logger.warning("[ModelRouter] Hech qanday faol AI provayder topilmadi. Mahalliy zaxiraga yo'naltirilmoqda.")
            return AIResponse(
                provider="local",
                model="offline-assistant",
                type="answer",
                content=(
                    "Misa AI: Tashqi AI provayderlari sozlanmagan yoki API kalitlar topilmadi. "
                    "Iltimos, .env faylida MISA_GROQ_API_KEY yoki MISA_GEMINI_API_KEY ni sozlang."
                ),
                success=False,
                error_code="NO_ACTIVE_PROVIDERS",
                metadata={"offline_fallback": True}
            )

        last_error = ""
        attempt_count = 0
        max_attempts = min(len(candidates), self._max_retries)

        for provider, model_meta, score in candidates[:max_attempts]:
            attempt_count += 1
            prov_name = provider.name
            mod_name = model_meta.model
            logger.info(
                f"[ModelRouter] Urinish {attempt_count}/{max_attempts}: "
                f"provayder='{prov_name}', model='{mod_name}' (ball={round(score, 1)})"
            )

            # So'rov metama'lumotiga tanlangan modelni biriktiramiz
            if not request.metadata:
                request.metadata = {}
            request.metadata["model"] = mod_name

            try:
                response = provider.generate(request)
                if response and response.success:
                    logger.info(
                        f"[ModelRouter] Muvaffaqiyat! Provayder='{prov_name}', "
                        f"model='{response.model}', tur='{response.type}'"
                    )
                    return response

                last_error = response.content if response else "Bo'sh javob"
                logger.warning(f"[ModelRouter] '{prov_name}' muvaffaqiyatsiz bo'ldi: {last_error}")

            except (RateLimitError, TimeoutError, ServerNetworkError, ModelUnavailableError, AuthenticationError) as e:
                last_error = f"{e.__class__.__name__}: {str(e)}"
                logger.warning(f"[ModelRouter] Provayder '{prov_name}' xato qaytardi: {last_error}. Keyingi provayderga o'tilmoqda...")
                # Qisqa tanaffus (exponential backoff)
                time.sleep(0.15 * attempt_count)

            except Exception as e:
                last_error = f"Kutilmagan xatolik ({prov_name}): {str(e)}"
                logger.error(f"[ModelRouter] {last_error}", exc_info=True)

        logger.error(f"[ModelRouter] Barcha {max_attempts} ta provayder urinishlari muvaffaqiyatsiz tugadi. Oxirgi xato: {last_error}")
        return AIResponse(
            provider="none",
            model="none",
            type="error",
            content=f"Barcha AI provayderlari bilan aloqa vaqtincha uzildi. Oxirgi xato: {last_error}",
            success=False,
            error_code="ALL_PROVIDERS_FAILED",
            metadata={"last_error": last_error, "attempts": attempt_count}
        )

    def route_and_stream(self, request: AIRequest) -> Iterator[StreamChunk]:
        """Oqimli so'rovlar uchun avtomatik marshrutlash."""
        task = self.classify_task(request)
        candidates = self.select_candidate_models(request, task=task)

        if not candidates:
            yield StreamChunk(text="AI provayder sozlanmagan.", is_final=True)
            return

        for provider, model_meta, _ in candidates[:self._max_retries]:
            if not request.metadata:
                request.metadata = {}
            request.metadata["model"] = model_meta.model
            try:
                for chunk in provider.stream(request):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"[ModelRouter-Stream] '{provider.name}' streaming xatosi: {e}, keyingi provayderga...")
                continue

        yield StreamChunk(text="Barcha oqimli AI provayderlari muvaffaqiyatsiz bo'ldi.", is_final=True)
