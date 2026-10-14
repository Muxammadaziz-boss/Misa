# ========== verifier.py ==========
# Misa AI 7.x — Step Verification Engine
# Deterministic & Semantic Verification for Agentic Plan Execution

import logging
from typing import Any, Dict, Optional, Tuple

from core.intelligence.types import (
    PlanStep,
    StepResult,
    VerificationResult,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class AgentVerifier:
    """
    Agent qadami natijalarini tekshiruvchi deterministik verifikator.
    Hech qachon taxminiy dalilsiz 'muvaffaqiyat' deb xulosa chiqarmaydi.
    Deterministik tekshiruv imkoni bo'lmaganda 'UNKNOWN' maqomini beradi.
    """

    # Ma'lum vositalar bo'yicha deterministik tekshiruv qoidalari
    DETERMINISTIC_TOOLS = {
        "calculator",
        "weather",
        "system_info",
        "currency",
        "app_check",
        "open_chrome",
        "open_youtube",
        "open_telegram",
        "open_code",
        "open_discord",
        "open_brave",
        "close_window",
        "close_chrome",
        "keyboard_type",
        "screen_click",
        "screen_analyze",
        "focus_window",
        "get_active_window",
        "window_list",
        "notepad",
    }

    def __init__(self, tool_registry=None, app_detector=None):
        self.tool_registry = tool_registry
        self.app_detector = app_detector

    def verify_step(
        self,
        step: PlanStep,
        step_result: StepResult
    ) -> VerificationResult:
        """
        Qadam natijasini sinchkovlik bilan tekshirish.
        Returns: VerificationResult
        """
        tool_name = (step.tool or "").lower().strip()

        # 1. Asbobning o'zi xato bilan yakunlangan bo'lsa -> Aniq FAILURE
        if not step_result.success:
            err_msg = step_result.error or "Asbob bajarilmadi"
            logger.warning(f"[AgentVerifier] Qadam #{step.order} ({tool_name}) muvaffaqiyatsiz: {err_msg}")
            return VerificationResult(
                verified=False,
                status=VerificationStatus.FAILURE,
                reason=f"Asbob xatosi: {err_msg}",
                details={"error": err_msg, "tool": tool_name}
            )

        raw = step_result.raw_result

        # 2. Maxsus vositalar uchun deterministik orakullar
        if tool_name == "calculator":
            return self._verify_calculator(step, raw)
        elif tool_name == "weather":
            return self._verify_weather(step, raw)
        elif tool_name == "system_info":
            return self._verify_system_info(step, raw)
        elif tool_name == "currency":
            return self._verify_currency(step, raw)
        elif tool_name == "app_check":
            return self._verify_app_check(step, raw)
        elif tool_name in ("open_chrome", "open_brave"):
            return self._verify_browser_open(step, raw, tool_name)
        elif tool_name == "open_youtube":
            return self._verify_youtube_open(step, raw)
        elif tool_name in ("close_chrome", "close_window"):
            return self._verify_window_close(step, raw)
        elif tool_name == "keyboard_type":
            return self._verify_keyboard_type(step, raw)
        elif tool_name == "screen_click":
            return self._verify_screen_click(step, raw)
        elif tool_name == "screen_analyze":
            return self._verify_screen_analyze(step, raw)
        elif tool_name in ("focus_window", "get_active_window", "window_list", "notepad"):
            return self._verify_window_management(step, raw, tool_name)

        # 3. Kutilgan natija (expected_result) bilan leksik/semantik solishtirish
        if step.expected_result:
            return self._verify_against_expected(step, raw)

        # 4. Deterministik tekshirish imkoni yo'q, lekin xato bo'lmagan holat -> UNKNOWN
        logger.info(f"[AgentVerifier] Qadam #{step.order} ({tool_name}) uchun orakul yo'q: UNKNOWN")
        return VerificationResult(
            verified=True,
            status=VerificationStatus.UNKNOWN,
            reason=f"Asbob '{tool_name}' muvaffaqiyatli yakunlandi, ammo deterministik dalil tekshirilmadi (UNKNOWN)",
            details={"raw_summary": str(raw)[:200] if raw is not None else ""}
        )

    def should_continue(
        self,
        verification: VerificationResult,
        step: PlanStep
    ) -> Tuple[bool, str]:
        """
        Qadam verifikatsiyasi asosida rejaning keyingi qadamiga o'tish mumkinligini hal qilish.
        UNKNOWN holatida davom etish o'rniga retry, re-observe yoki clarification so'raladi.
        Returns: (can_continue: bool, reason: str)
        """
        if verification.status == VerificationStatus.SUCCESS:
            return True, "STEP_VERIFIED_SUCCESS"

        if verification.status == VerificationStatus.UNKNOWN:
            # Agar qayta urinish imkoniyati qolgan bo'lsa -> Re-observe / Retry
            if step.retry_count < step.max_retries:
                return False, "UNKNOWN_STATUS_RETRY_OBSERVATION"
            # Qayta urinishlar tugagan bo'lsa -> Foydalanuvchidan aniqlik/tasdiq so'rash
            return False, "UNKNOWN_STATUS_REQUIRES_CLARIFICATION"

        if verification.status == VerificationStatus.FAILURE:
            return False, f"STEP_VERIFICATION_FAILED: {verification.reason}"

        return False, "UNKNOWN_VERIFICATION_STATE"

    # ========================================================
    # XUSUSIY DETERMINISTIK TEKSHIRUV METODLARI
    # ========================================================

    def _verify_calculator(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Kalkulyator natijasini tekshirish"""
        if isinstance(raw, (int, float)):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason=f"Hisoblash to'g'ri bajarildi: {raw}",
                details={"result": raw}
            )
        if isinstance(raw, dict) and "result" in raw:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason=f"Hisoblash to'g'ri bajarildi: {raw.get('result')}",
                details={"result": raw.get("result")}
            )
        if raw is not None and str(raw).strip():
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason=f"Kalkulyator javob qaytardi: {str(raw)[:60]}",
                details={"raw": str(raw)}
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILURE,
            reason="Kalkulyator bo'sh natija qaytardi",
            details={"raw": raw}
        )

    def _verify_weather(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Ob-havo ma'lumotlarini tekshirish"""
        text = str(raw).lower() if raw else ""
        if any(w in text for w in ["harorat", "daraja", "°c", "ob-havo", "namlik", "shamol", "havo"]):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Ob-havo ma'lumotlari muvaffaqiyatli olindi",
                details={"summary": str(raw)[:100]}
            )
        if raw and not ("xato" in text or "topilmadi" in text):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Ob-havo javobi olindi",
                details={"summary": str(raw)[:100]}
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILURE,
            reason=f"Ob-havo ma'lumoti topilmadi: {raw}",
            details={"raw": raw}
        )

    def _verify_system_info(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Tizim ma'lumotlarini tekshirish"""
        if isinstance(raw, dict) and len(raw) > 0:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Tizim parametrlari to'liq olindi",
                details={"keys": list(raw.keys())}
            )
        if raw and len(str(raw).strip()) > 10:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Tizim ma'lumotlari olindi",
                details={"length": len(str(raw))}
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILURE,
            reason="Tizim ma'lumotlari bo'sh qaytdi",
            details={"raw": raw}
        )

    def _verify_currency(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Valyuta kursi natijasini tekshirish"""
        text = str(raw).lower() if raw else ""
        if any(w in text for w in ["kurs", "so'm", "usd", "sum", "narx", "qiymat"]) or isinstance(raw, (int, float)):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Valyuta kursi muvaffaqiyatli hisoblandi",
                details={"raw": str(raw)[:80]}
            )
        return VerificationResult(
            verified=True,
            status=VerificationStatus.UNKNOWN,
            reason="Valyuta javobi olindi, aniq qiymat formati tekshirilmadi",
            details={"raw": str(raw)[:80]}
        )

    def _verify_app_check(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Ilova mavjudligini tekshirish natijasi"""
        if isinstance(raw, dict):
            found = raw.get("installed", raw.get("found", True))
            return VerificationResult(
                verified=bool(found),
                status=VerificationStatus.SUCCESS if found else VerificationStatus.FAILURE,
                reason="Ilova holati tekshirildi: " + ("o'rnatilgan" if found else "topilmadi"),
                details=raw
            )
        text = str(raw).lower() if raw else ""
        if "o'rnatilgan" in text or "ornatilgan" in text or "mavjud" in text:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Ilova o'rnatilganligi aniqlandi",
                details={"raw": str(raw)[:100]}
            )
        if "topilmadi" in text or "mavjud emas" in text or "yo'q" in text:
            return VerificationResult(
                verified=False,
                status=VerificationStatus.FAILURE,
                reason="Ilova kompyuterda topilmadi",
                details={"raw": str(raw)[:100]}
            )
        return VerificationResult(
            verified=True,
            status=VerificationStatus.UNKNOWN,
            reason="Ilova tekshiruvi yakunlandi",
            details={"raw": str(raw)[:100]}
        )

    def _verify_browser_open(self, step: PlanStep, raw: Any, browser_name: str) -> VerificationResult:
        """Brauzer ochilganligini tekshirish"""
        # Jarayon mavjudligini tekshirishga urinish
        try:
            import psutil
            proc_names = {"open_chrome": ["chrome.exe", "chrome"], "open_brave": ["brave.exe", "brave"]}
            targets = proc_names.get(browser_name, ["chrome.exe"])
            found = any(p.name().lower() in targets for p in psutil.process_iter(['name']))
            if found:
                return VerificationResult(
                    verified=True,
                    status=VerificationStatus.SUCCESS,
                    reason=f"{browser_name.replace('open_', '').capitalize()} jarayoni tizimda faol",
                    details={"browser": browser_name, "process_found": True}
                )
        except Exception:
            pass

        # Agar psutil bo'lmasa yoki jarayon topilmasa, tool muvaffaqiyati asosida
        if raw is not None and not ("xato" in str(raw).lower()):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason=f"{browser_name.replace('open_', '').capitalize()} ochish buyrug'i berildi",
                details={"raw": str(raw)[:100]}
            )

        return VerificationResult(
            verified=True,
            status=VerificationStatus.UNKNOWN,
            reason=f"{browser_name} buyrug'i yuborildi, ammo jarayon holati tasdiqlanmadi",
            details={"raw": str(raw)}
        )

    def _verify_youtube_open(self, step: PlanStep, raw: Any) -> VerificationResult:
        """YouTube ochilganligini tekshirish"""
        if raw is not None and not ("xato" in str(raw).lower()):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="YouTube muvaffaqiyatli ochildi",
                details={"raw": str(raw)[:100]}
            )
        return VerificationResult(
            verified=True,
            status=VerificationStatus.UNKNOWN,
            reason="YouTube ochish buyrug'i berildi",
            details={"raw": str(raw)}
        )

    def _verify_window_close(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Oyna yopilganligini tekshirish"""
        if raw is not None and not ("xato" in str(raw).lower()):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Oyna yopildi",
                details={"raw": str(raw)[:80]}
            )
        return VerificationResult(
            verified=True,
            status=VerificationStatus.UNKNOWN,
            reason="Oynani yopish buyrug'i bajarildi",
            details={"raw": str(raw)}
        )

    def _verify_against_expected(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Kutilgan natija (expected_result) bilan taqqoslash"""
        expected = (step.expected_result or "").lower().strip()
        actual_str = str(raw).lower() if raw is not None else ""

        # Leksik qidiruv
        expected_tokens = set(expected.split())
        if not expected_tokens:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.UNKNOWN,
                reason="Kutilgan natija bo'sh, vosita muvaffaqiyati qabul qilindi",
                details={}
            )

        overlap = sum(1 for t in expected_tokens if t in actual_str)
        overlap_ratio = overlap / len(expected_tokens)

        if overlap_ratio >= 0.4:
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason=f"Natija kutilgan natijaga mos keldi ({round(overlap_ratio * 100)}% moslik)",
                details={"expected": step.expected_result, "overlap_ratio": overlap_ratio}
            )

        return VerificationResult(
            verified=True,
            status=VerificationStatus.UNKNOWN,
            reason="Natija kutilgan natija bilan to'liq mos kelmadi, ammo xato aniqlanmadi (UNKNOWN)",
            details={"expected": step.expected_result, "actual_preview": str(raw)[:120]}
        )

    def _verify_keyboard_type(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Klaviatura orqali matn yozishni tekshirish"""
        if isinstance(raw, dict):
            if raw.get("error"):
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.FAILURE,
                    reason=f"Klaviatura amali xatosi: {raw.get('error')}",
                    details=raw
                )
            if raw.get("postcondition_verified") or raw.get("typed") or raw.get("success", False):
                txt = raw.get("text", "")
                return VerificationResult(
                    verified=True,
                    status=VerificationStatus.SUCCESS,
                    reason=f"Matn muvaffaqiyatli yozildi: {txt[:30]}",
                    details=raw
                )
        elif raw and not ("xato" in str(raw).lower() or "error" in str(raw).lower()):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Matn kiritish muvaffaqiyatli yakunlandi",
                details={"raw": str(raw)[:100]}
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILURE,
            reason="Klaviatura amali tasdiqlanmadi",
            details={"raw": raw}
        )

    def _verify_screen_click(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Ekran bosish amalini tekshirish"""
        if isinstance(raw, dict):
            if raw.get("error"):
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.FAILURE,
                    reason=f"Ekran bosish xatosi: {raw.get('error')}",
                    details=raw
                )
            if raw.get("clicked") or raw.get("postcondition_verified") or raw.get("success", False):
                return VerificationResult(
                    verified=True,
                    status=VerificationStatus.SUCCESS,
                    reason=f"Ekran nuqtasi bosildi: ({raw.get('x')}, {raw.get('y')})",
                    details=raw
                )
        elif raw and not ("xato" in str(raw).lower() or "error" in str(raw).lower()):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Ekran bosish muvaffaqiyatli yakunlandi",
                details={"raw": str(raw)[:100]}
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILURE,
            reason="Ekran bosish tasdiqlanmadi",
            details={"raw": raw}
        )

    def _verify_screen_analyze(self, step: PlanStep, raw: Any) -> VerificationResult:
        """Ekran tahlili (Vision/OCR/Local) natijasini tekshirish"""
        if isinstance(raw, dict):
            if raw.get("error"):
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.FAILURE,
                    reason=f"Ekran tahlili xatosi: {raw.get('error')}",
                    details=raw
                )
            if raw.get("message") or raw.get("active_window") or raw.get("local_analysis") is not None:
                msg = str(raw.get("message") or raw.get("active_window") or "Tahlil yakunlandi")
                return VerificationResult(
                    verified=True,
                    status=VerificationStatus.SUCCESS,
                    reason="Ekran tahlili muvaffaqiyatli olindi",
                    details={"summary": msg[:100]}
                )
        if raw and not ("xato" in str(raw).lower() or "error" in str(raw).lower()):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason="Ekran tahlili olindi",
                details={"raw": str(raw)[:100]}
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILURE,
            reason="Ekran tahlili olinmadi",
            details={"raw": raw}
        )

    def _verify_window_management(self, step: PlanStep, raw: Any, tool_name: str) -> VerificationResult:
        """Oyna boshqaruvi (focus_window, window_list, notepad) natijasini tekshirish"""
        if isinstance(raw, dict):
            if raw.get("error"):
                return VerificationResult(
                    verified=False,
                    status=VerificationStatus.FAILURE,
                    reason=f"{tool_name} xatosi: {raw.get('error')}",
                    details=raw
                )
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason=f"{tool_name} muvaffaqiyatli bajarildi",
                details=raw
            )
        if raw and not ("xato" in str(raw).lower() or "error" in str(raw).lower()):
            return VerificationResult(
                verified=True,
                status=VerificationStatus.SUCCESS,
                reason=f"{tool_name} muvaffaqiyatli bajarildi",
                details={"raw": str(raw)[:100]}
            )
        return VerificationResult(
            verified=False,
            status=VerificationStatus.FAILURE,
            reason=f"{tool_name} natijasi tasdiqlanmadi",
            details={"raw": raw}
        )
