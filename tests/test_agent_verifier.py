# ========== test_agent_verifier.py ==========
# Phase 31 — Agentic Step Verification Engine Unit Tests
# Deterministic Checks, Expected Outcome Matching & Continue Decisions

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.intelligence.types import (
    PlanStep,
    StepResult,
    VerificationResult,
    VerificationStatus,
    RiskLevel,
    StepStatus,
)
from core.intelligence.verifier import AgentVerifier


class TestAgentVerifier(unittest.TestCase):
    """AgentVerifier qadam verifikatsiyasi va xavfsiz davom etish testlari"""

    def setUp(self):
        self.verifier = AgentVerifier()

    def _make_step(self, tool: str, params: dict = None, expected: str = "") -> PlanStep:
        return PlanStep(
            step_id="step-test-1",
            order=1,
            intent=tool,
            tool=tool,
            parameters=params or {},
            expected_result=expected,
            risk_level=RiskLevel.LOW,
            status=StepStatus.RUNNING,
        )

    def _make_result(self, tool: str, raw: any, success: bool = True, err: str = None) -> StepResult:
        return StepResult(
            step_id="step-test-1",
            tool=tool,
            parameters={},
            success=success,
            raw_result=raw,
            error=err,
            duration_ms=10.0,
            timestamp="2026-09-14T22:00:00",
        )

    # 1. Calculator verification
    def test_verifier_calculator_success(self):
        """Kalkulyator to'g'ri hisoblaganda SUCCESS qaytarishi kerak"""
        step = self._make_step("calculator", {"expression": "25 * 4"})
        res = self._make_result("calculator", "100")
        ver = self.verifier.verify_step(step, res)
        self.assertTrue(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.SUCCESS)
        self.assertIn("100", ver.reason)

    def test_verifier_calculator_failure(self):
        """Kalkulyatorda xatolik bo'lsa FAILURE qaytarishi kerak"""
        step = self._make_step("calculator", {"expression": "10 / 0"})
        res = self._make_result("calculator", "Xatolik: Nolga bo'lish mumkin emas", success=False)
        ver = self.verifier.verify_step(step, res)
        self.assertFalse(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.FAILURE)

    # 2. Weather verification
    def test_verifier_weather_success(self):
        """Ob-havo ma'lumoti muvaffaqiyatli olinganda SUCCESS qaytarishi kerak"""
        step = self._make_step("weather", {"city": "Toshkent"})
        res = self._make_result("weather", "Toshkentda havo ochiq, harorat +24°C, namlik 40%")
        ver = self.verifier.verify_step(step, res)
        self.assertTrue(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.SUCCESS)

    def test_verifier_weather_failure(self):
        """Ob-havo topilmasa FAILURE qaytarishi kerak"""
        step = self._make_step("weather", {"city": "UnknownCity123"})
        res = self._make_result("weather", "Shahar ob-havosi topilmadi", success=False)
        ver = self.verifier.verify_step(step, res)
        self.assertFalse(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.FAILURE)

    # 3. System info verification
    def test_verifier_system_info_success(self):
        """Tizim ma'lumotlari mavjud bo'lsa SUCCESS qaytaradi"""
        step = self._make_step("system_info", {"category": "cpu"})
        res = self._make_result("system_info", {"cpu_percent": 12.5, "cores": 8})
        ver = self.verifier.verify_step(step, res)
        self.assertTrue(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.SUCCESS)

    def test_verifier_system_info_empty_failure(self):
        """Tizim ma'lumotlari bo'sh kelsa FAILURE qaytaradi"""
        step = self._make_step("system_info", {"category": "cpu"})
        res = self._make_result("system_info", "")
        ver = self.verifier.verify_step(step, res)
        self.assertFalse(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.FAILURE)

    # 4. Currency verification
    def test_verifier_currency_success(self):
        """Valyuta kursi ma'lumotlari to'g'ri kelsa SUCCESS qaytaradi"""
        step = self._make_step("currency", {"from_currency": "USD", "to_currency": "UZS"})
        res = self._make_result("currency", "1 USD = 12,850 UZS (Markaziy Bank kursi)")
        ver = self.verifier.verify_step(step, res)
        self.assertTrue(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.SUCCESS)

    # 5. App check verification
    def test_verifier_app_check_success(self):
        """Ilova aniqlanganda SUCCESS qaytaradi"""
        step = self._make_step("app_check", {"app_name": "chrome"})
        res = self._make_result("app_check", "Google Chrome kompyuterda o'rnatilgan")
        ver = self.verifier.verify_step(step, res)
        self.assertTrue(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.SUCCESS)

    def test_verifier_app_check_failure(self):
        """Ilova topilmaganda yoki mavjud bo'lmaganda FAILURE qaytaradi"""
        step = self._make_step("app_check", {"app_name": "fake_app_xyz"})
        res = self._make_result("app_check", "Ilova kompyuterda topilmadi")
        ver = self.verifier.verify_step(step, res)
        self.assertFalse(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.FAILURE)

    # 6. Browser & YouTube verification
    def test_verifier_open_browser_success(self):
        """Brauzer ochilganda SUCCESS qaytaradi"""
        step = self._make_step("open_chrome")
        res = self._make_result("open_chrome", "Chrome brauzeri ochildi")
        ver = self.verifier.verify_step(step, res)
        self.assertTrue(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.SUCCESS)

    # 7. Lexical Expected Outcome Matching
    def test_verifier_lexical_expected_outcome_match(self):
        """Kutilgan natija kalit so'zlari mavjud bo'lsa SUCCESS qaytaradi"""
        step = self._make_step("custom_tool", expected="muvaffaqiyatli bajarildi")
        res = self._make_result("custom_tool", "Operatsiya muvaffaqiyatli bajarildi va saqlandi")
        ver = self.verifier.verify_step(step, res)
        self.assertTrue(ver.verified)
        self.assertEqual(ver.status, VerificationStatus.SUCCESS)
        self.assertIn("mos keldi", ver.reason)

    def test_verifier_unknown_status_fallback(self):
        """Noma'lum vosita kelsa va xatolik bo'lmasa UNKNOWN qaytaradi"""
        step = self._make_step("unrecognized_tool_xyz")
        res = self._make_result("unrecognized_tool_xyz", "Bajarildi")
        ver = self.verifier.verify_step(step, res)
        self.assertEqual(ver.status, VerificationStatus.UNKNOWN)

    # 8. should_continue decision tests
    def test_should_continue_on_success(self):
        """SUCCESS holatida davom etishga ruxsat beriladi"""
        ver = VerificationResult(verified=True, status=VerificationStatus.SUCCESS, reason="OK")
        step = self._make_step("calculator")
        can_cont, reason = self.verifier.should_continue(ver, step)
        self.assertTrue(can_cont)
        self.assertEqual(reason, "STEP_VERIFIED_SUCCESS")

    def test_should_continue_on_unknown(self):
        """UNKNOWN holatida retry qolgan bo'lsa re-observe/retry, tugagan bo'lsa clarification so'raydi"""
        ver = VerificationResult(verified=True, status=VerificationStatus.UNKNOWN, reason="Unknown")
        step = self._make_step("notification")
        can_cont, reason = self.verifier.should_continue(ver, step)
        self.assertFalse(can_cont)
        self.assertEqual(reason, "UNKNOWN_STATUS_RETRY_OBSERVATION")

        step.retry_count = step.max_retries
        can_cont_done, reason_done = self.verifier.should_continue(ver, step)
        self.assertFalse(can_cont_done)
        self.assertEqual(reason_done, "UNKNOWN_STATUS_REQUIRES_CLARIFICATION")

    def test_should_continue_on_failure(self):
        """FAILURE holatida davom etish to'xtatiladi"""
        ver = VerificationResult(verified=False, status=VerificationStatus.FAILURE, reason="Failed calc")
        step = self._make_step("calculator")
        can_cont, reason = self.verifier.should_continue(ver, step)
        self.assertFalse(can_cont)
        self.assertTrue(reason.startswith("STEP_VERIFICATION_FAILED"))


if __name__ == "__main__":
    unittest.main()
