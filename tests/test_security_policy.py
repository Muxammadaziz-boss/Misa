# ========== tests/test_security_policy.py ==========
import os
import sys
import time
import unittest
from unittest.mock import MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.intelligence.types import RiskLevel
from core.tools.contract import ToolContract2, ToolErrorCode, ToolResult
from core.tools.runner import SafeToolRunner
from core.tools.security_policy import (
    AuthoritativeSecurityPolicy,
    ConfirmationTokenManager,
    PolicyActionClass,
    get_security_policy,
    get_internal_api_session_token,
    verify_internal_api_request,
)


class TestSecurityPolicy(unittest.TestCase):
    def setUp(self):
        self.policy = AuthoritativeSecurityPolicy()
        self.token_mgr = ConfirmationTokenManager(default_ttl_seconds=2.0)

    def test_01_read_only_tools_auto_allowed(self):
        read_only_tools = [
            "system_info",
            "battery_status",
            "cpu_metrics",
            "list_processes",
            "list_files",
            "read_file",
            "get_weather",
            "get_time",
            "clipboard_get",
            "window_list",
            "screen_analyze",
            "screenshot",
        ]
        for t in read_only_tools:
            decision = self.policy.evaluate(t)
            self.assertTrue(decision.allowed, f"Tool {t} should be allowed")
            self.assertFalse(decision.requires_confirmation, f"Tool {t} should not require confirmation")
            self.assertEqual(decision.reason, "READ_ONLY_AUTO_ALLOWED")

    def test_02_mandatory_confirmation_categories(self):
        # 1. Keyboard
        d1 = self.policy.evaluate("keyboard_type", params={"text": "hello"})
        self.assertFalse(d1.allowed)
        self.assertTrue(d1.requires_confirmation)
        self.assertIsNotNone(d1.challenge_token)

        # 2. Mouse click
        d2 = self.policy.evaluate("screen_click", params={"x": 100, "y": 200})
        self.assertFalse(d2.allowed)
        self.assertTrue(d2.requires_confirmation)

        # 3. Clipboard write
        d3 = self.policy.evaluate("clipboard_set", params={"text": "secret"})
        self.assertFalse(d3.allowed)
        self.assertTrue(d3.requires_confirmation)

        # 4. File write / delete
        d4a = self.policy.evaluate("file_write", params={"path": "test.txt", "content": "data"})
        self.assertFalse(d4a.allowed)
        self.assertTrue(d4a.requires_confirmation)

        d4b = self.policy.evaluate("file_delete", params={"path": "test.txt"})
        self.assertFalse(d4b.allowed)
        self.assertTrue(d4b.requires_confirmation)

        # 5. Process close
        d5 = self.policy.evaluate("process_kill", params={"pid": 1234})
        self.assertFalse(d5.allowed)
        self.assertTrue(d5.requires_confirmation)

        # 6. Browser navigation
        d6 = self.policy.evaluate("open_url", params={"url": "https://example.com"})
        self.assertFalse(d6.allowed)
        self.assertTrue(d6.requires_confirmation)

        # 7. Network requests
        d7 = self.policy.evaluate("http_request", params={"url": "https://api.com"})
        self.assertFalse(d7.allowed)
        self.assertTrue(d7.requires_confirmation)

        # 8. Power actions
        d8 = self.policy.evaluate("system_shutdown")
        self.assertFalse(d8.allowed)
        self.assertTrue(d8.requires_confirmation)
        self.assertEqual(d8.risk_level, RiskLevel.HIGH)

    def test_03_confirmation_token_validation_and_replay_protection(self):
        tool = "file_delete"
        params = {"path": "C:\\temp\\file.txt"}

        # Token yaratish
        token = self.token_mgr.create_token(tool, params, ttl=2.0)
        self.assertTrue(len(token) > 20)

        # Noto'g'ri tool uchun rad etish
        ok_wrong_tool, err = self.token_mgr.verify_and_consume(token, "system_shutdown", params)
        self.assertFalse(ok_wrong_tool)
        self.assertEqual(err, "TOOL_NAME_MISMATCH")

        # Noto'g'ri parametrlar uchun rad etish
        ok_wrong_params, err = self.token_mgr.verify_and_consume(token, tool, {"path": "other.txt"})
        self.assertFalse(ok_wrong_params)
        self.assertEqual(err, "PARAMS_MISMATCH")

        # To'g'ri tasdiqlash
        ok, err = self.token_mgr.verify_and_consume(token, tool, params)
        self.assertTrue(ok)
        self.assertEqual(err, "OK")

        # REPLAY ATTACK tekshiruvi: Ikkinchi marta o'sha token bilan murojaat qilinganda rad etilishi shart
        ok_replay, err_replay = self.token_mgr.verify_and_consume(token, tool, params)
        self.assertFalse(ok_replay)
        self.assertEqual(err_replay, "TOKEN_ALREADY_USED")

    def test_04_confirmation_token_expiry(self):
        token = self.token_mgr.create_token("screen_click", {"x": 10, "y": 20}, ttl=0.1)
        time.sleep(0.2)
        ok, err = self.token_mgr.verify_and_consume(token, "screen_click", {"x": 10, "y": 20})
        self.assertFalse(ok)
        self.assertEqual(err, "TOKEN_EXPIRED")

    def test_05_safe_tool_runner_with_security_policy(self):
        called = {"count": 0}

        def mock_action(text: str = ""):
            called["count"] += 1
            return {"status": "ok", "typed": text}

        tool = ToolContract2(
            name="keyboard_type",
            description="Type keys into target window",
            function=mock_action,
            parameters={"text": {"type": "string"}},
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
        )

        runner = SafeToolRunner(security_policy=self.policy)

        # 1. Chaqiruv tokensiz bo'lsa rad etiladi
        res1 = runner.execute_tool(tool, {"text": "hello"})
        self.assertFalse(res1.success)
        self.assertEqual(res1.code, ToolErrorCode.PERMISSION_DENIED)
        self.assertEqual(res1.error, "CONFIRMATION_REQUIRED")
        self.assertEqual(called["count"], 0)

        challenge = res1.metadata.get("challenge_token")
        self.assertIsNotNone(challenge)

        # 2. To'g'ri challenge token bilan chaqirilganda muvaffaqiyatli bajariladi
        res2 = runner.execute_tool(tool, {"text": "hello"}, confirmation_token=challenge)
        self.assertTrue(res2.success)
        self.assertEqual(called["count"], 1)

        # 3. O'sha tokenni qayta ishlatishga urinish rad etiladi (Replay protection)
        res3 = runner.execute_tool(tool, {"text": "hello"}, confirmation_token=challenge)
        self.assertFalse(res3.success)
        self.assertEqual(res3.error, "CONFIRMATION_REQUIRED")
        self.assertEqual(called["count"], 1)

    def test_06_internal_api_request_verification(self):
        token = get_internal_api_session_token()

        # 1. To'g'ri X-Misa-Session-Token sarlavhasi
        self.assertTrue(verify_internal_api_request({"X-Misa-Session-Token": token}))
        self.assertTrue(verify_internal_api_request({"x-misa-session-token": token}))

        # 2. To'g'ri Bearer token
        self.assertTrue(verify_internal_api_request({"Authorization": f"Bearer {token}"}))

        # 3. Body token
        self.assertTrue(verify_internal_api_request({}, {"session_token": token}))

        # 4. Noto'g'ri yoki yo'q token
        self.assertFalse(verify_internal_api_request({"X-Misa-Session-Token": "attacker-token"}))
        self.assertFalse(verify_internal_api_request({}))


if __name__ == "__main__":
    unittest.main()
