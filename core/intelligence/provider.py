# ========== provider.py ==========
# Misa AI 7.x — AI Provider Base Interface & Provider Manager
# Provider Abstraction & Deterministic Fallback Mechanism

import abc
import re
import logging
from typing import List, Optional, Dict, Any
from core.intelligence.types import AIRequest, AIResponse

logger = logging.getLogger(__name__)


class AIProvider(abc.ABC):
    """Barcha AI provayderlari (Gemini, OpenRouter, va h.k.) uchun yagona baza interfeys"""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provayder nomi (masalan: 'gemini', 'openrouter')"""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Provayder konfiguratsiya qilingan va tayyor ekanligini tekshirish"""
        pass

    @abc.abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Sinxron so'rov yuborish va normalizatsiya qilingan AIResponse qaytarish"""
        pass


class ProviderManager:
    """AI provayderlarini boshqarish va deterministik fallback mexanizmi"""

    def __init__(self, providers: Optional[List[AIProvider]] = None):
        self._providers: List[AIProvider] = providers or []

    def register_provider(self, provider: AIProvider):
        """Yangi provayder ro'yxatdan o'tkazish"""
        self._providers.append(provider)

    def get_available_providers(self) -> List[str]:
        """Faol va kalitlari sozlangan provayderlar ro'yxati"""
        return [p.name for p in self._providers if p.is_available()]

    def is_any_available(self) -> bool:
        """Kamida bitta provayder mavjudligini tekshirish"""
        return any(p.is_available() for p in self._providers)

    def generate_with_fallback(self, request: AIRequest) -> AIResponse:
        """
        Deterministik zanjir orqali javob olish:
        Provayder 1 (Gemini) -> xatolik? -> Provayder 2 (OpenRouter) -> xatolik? -> AI_PROVIDER_UNAVAILABLE
        """
        available_providers = [p for p in self._providers if p.is_available()]
        
        if not available_providers:
            logger.warning("Hech qanday AI provayder sozlanmagan (API kalitlar mavjud emas). Mahalliy offline rejim ishga tushadi.")
            query_str = getattr(request, "message", None) or getattr(request, "query", "") or ""
            query_lower = str(query_str).lower().strip()
            query_words = set(re.findall(r"\b\w+\b", query_lower))
            req_user = getattr(request, "user_name", None) or getattr(request, "user", None) or (request.metadata.get("user_name") if hasattr(request, "metadata") and isinstance(request.metadata, dict) else None) or "Foydalanuvchi"

            # 1. Foydalanuvchi o'zi haqida so'raganda
            if any(p in query_lower for p in ["men kimman", "men kimmam", "men kim", "ismim nima", "mening ismim", "otim nima", "men haqimda"]):
                resp_text = f"Siz — **{req_user}**siz. Misa AI tizimida shaxsiy profilingiz faol holatda."
            elif any(p in query_lower for p in ["sen kimsan", "misa kimsan", "o'zing haqingda", "nimalar qila olasan", "imkoniyating"]) or any(w in query_words for w in ["salom", "assalom", "assalomu"]):
                resp_text = (
                    "Assalomu alaykum! Men Misa — sizning shaxsiy sun'iy intellekt yordamchingizman.\n\n"
                    "Men quyidagi asosiy vazifalarni mustaqil bajara olaman:\n"
                    "• 💻 Kompyuterni boshqarish (dasturlarni ochish, oynalar va skrinshot)\n"
                    "• 📊 Tizim holati (CPU, RAM va real vaqtdagi parametrlar)\n"
                    "• ⏰ Vazifalar va eslatmalarni rejalashtirish\n"
                    "• 🎵 Musiqa va videolarni boshqarish\n\n"
                    "💡 Kengaytirilgan chuqur muloqot va erkin suhbat uchun Sozlamalar bo'limidan Google Gemini API kalitini kiritishingiz mumkin."
                )
            else:
                resp_text = (
                    "Misa mahalliy yordamchi rejimida ishlamoqda. Buyruqlaringizni bajarishga tayyorman!\n\n"
                    "Erkin tahlil va suhbatlar uchun Hisob sozlamalaridan Gemini API kalitini sozlashingiz mumkin."
                )

            return AIResponse(
                provider="local",
                model="misa-offline-core",
                type="answer",
                content=resp_text,
                success=True,
                error_code=None,
                metadata={"offline_mode": True}
            )

        last_error = ""
        for provider in available_providers:
            try:
                logger.info(f"AI so'rovi yuborilmoqda: provayder='{provider.name}'")
                response = provider.generate(request)
                if response and response.success:
                    logger.info(f"AI muvaffaqiyatli javob berdi: provayder='{provider.name}', model='{response.model}', type='{response.type}'")
                    return response
                
                # Agar muvaffaqiyatsiz bo'lsa, keyingi provayderga o'tish
                last_error = response.content if response else "Bo'sh javob"
                logger.warning(f"Provayder '{provider.name}' muvaffaqiyatsiz bo'ldi ({last_error}), keyingi provayderga o'tilmoqda...")
            except Exception as e:
                last_error = str(e)
                logger.error(f"Provayder '{provider.name}' ijrosida istisno: {e}", exc_info=True)

        # Barcha provayderlar ishlamadi yoki kvota/tarmoq limiti
        logger.warning(f"Barcha tashqi AI provayderlar zanjiri muvaffaqiyatsiz tugadi. Oxirgi xatolik: {last_error}")
        
        query_str = getattr(request, "message", None) or getattr(request, "query", "") or ""
        query_lower = str(query_str).lower().strip()
        query_words = set(re.findall(r"\b\w+\b", query_lower))
        req_user = getattr(request, "user_name", None) or getattr(request, "user", None) or "Foydalanuvchi"

        is_quota = "429" in str(last_error) or "quota" in str(last_error).lower() or "resource_exhausted" in str(last_error).lower()
        is_auth_error = any(k in str(last_error).lower() for k in ["403", "permission_denied", "leaked", "unregistered_callers", "api_key_invalid"])

        # 1. Foydalanuvchi o'zi haqida so'raganda
        if any(p in query_lower for p in ["men kimman", "men kimmam", "men kim", "ismim nima", "mening ismim", "otim nima", "men haqimda"]):
            fallback_text = f"Siz — **{req_user}**siz. Misa AI tizimida shaxsiy profilingiz faol holatda."
        elif is_auth_error:
            fallback_text = (
                "⚠️ **Google Gemini API kaliti xatoligi (403 Permission Denied / Leaked Key)**\n\n"
                "Tizimga ulangan API kaliti Google xavfsizlik filtri tomonidan bekor qilingan (ochiq tarmoqqa sizib chiqqan deb topilgan).\n\n"
                "**Yechim:**\n"
                "1. [Google AI Studio](https://aistudio.google.com/app/apikey) sahifasidan bepul yangi shaxsiy API kalit oling.\n"
                "2. Yuqori o'ng burchakdagi **Profil / Hisob sozlamalari** bo'limiga kirib, yangi kalitni kiriting.\n\n"
                "💻 Hozirda barcha mahalliy kompyuter buyruqlari, dasturlarni ochish va tizim ma'lumotlari to'liq ishlamoqda!"
            )
        elif is_quota:
            fallback_text = (
                "⚠️ Sun'iy intellekt (Gemini) so'rovlar limiti vaqtincha to'ldi (429 Quota Exceeded).\n\n"
                "Tizim avtomatik zaxira kalitlarga o'tmoqda yoki administrator yangi kalit yuklashini kutishingiz mumkin. "
                "Shuningdek, o'zingizning shaxsiy Google Gemini API kalitingizni Hisob bo'limiga kiritishingiz mumkin.\n\n"
                "Men kompyuteringizdagi barcha mahalliy buyruqlarni bajarishga tayyorman!"
            )
        elif any(p in query_lower for p in ["sen kimsan", "misa kimsan", "o'zing haqingda", "nimalar qila olasan", "imkoniyat"]) or any(w in query_words for w in ["salom", "assalom", "assalomu"]):
            fallback_text = (
                "Assalomu alaykum! Men Misa — sizning shaxsiy sun'iy intellekt yordamchingizman.\n\n"
                "Men quyidagi vazifalarni mustaqil bajara olaman:\n"
                "• 💻 Dasturlarni boshqarish (Telegram, Chrome, fayllar va oyna amallari)\n"
                "• 📊 Tizim holati (CPU, RAM, batareya, vaqt va sana)\n"
                "• 🎵 Ovoz va media boshqaruvi\n"
                "• 📱 Telegram bot orqali masofaviy boshqaruv\n\n"
                "💡 Kengaytirilgan tahlil va suhbatlar uchun Hisob sozlamalaridan Gemini API kalitini kiritishingiz mumkin."
            )
        else:
            fallback_text = (
                "Tashqi AI serveri bilan vaqtinchalik aloqa uzildi. "
                "Biroq barcha kompyuter boshqaruvi va mahalliy buyruqlar faol holatda. Qanday amal bajaramiz?"
            )

        return AIResponse(
            provider="local",
            model="misa-offline-core",
            type="answer",
            content=fallback_text,
            success=True,
            metadata={"last_error": last_error, "offline_fallback": True}
        )

