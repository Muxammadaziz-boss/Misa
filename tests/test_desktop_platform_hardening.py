"""
tests/test_desktop_platform_hardening.py
Unit and integration tests for desktop platform hardening:
- Screenshot false-positive fix (captured: False on error)
- Sensitive data redaction in telemetry/audit logs
- Browser automation adapter (tab list, page title, explicit navigation, DOM actions)
- Backend handshake provenance and version validation
"""

import unittest
from unittest.mock import patch, MagicMock

from agent.tools import handle_system_screenshot
from core.intelligence.observability import redact_sensitive_data
from core.browser.adapter import BrowserAutomationAdapter, BrowserTab
from core.gui.controller import WindowTarget


class TestDesktopPlatformHardening(unittest.TestCase):

    def test_screenshot_error_returns_captured_false(self):
        """Screenshot xatolik berganida captured: False qaytishi shart (noto'g'ri true bo'lmasligi kerak)"""
        with patch("PIL.ImageGrab.grab", side_effect=RuntimeError("Screen capture permission denied")):
            res = handle_system_screenshot({})
            self.assertFalse(res.get("captured"), "Xatolik holatida captured False bo'lishi kerak")
            self.assertFalse(res.get("mock"), "Mock False bo'lishi kerak")
            self.assertIn("error", res)
            self.assertIn("Screen capture permission denied", res["error"])

    def test_telemetry_sensitive_data_redaction(self):
        """Telemetriya va audit loglarda JWT, API key, Supabase va parollar yashirilishi shart"""
        raw_payload = {
            "username": "admin",
            "password": "supersecretpassword123",
            "api_key": "sk-1234567890abcdef1234567890",
            "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature",
            "supabase_key": "sbp_abcdef12345678901234567890",
            "nested": {
                "secret_token": "misa_token_secret_value_999",
                "normal_field": "public_data"
            }
        }

        redacted = redact_sensitive_data(raw_payload)

        self.assertEqual(redacted["password"], "[REDACTED]")
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["authorization"], "[REDACTED]")
        self.assertEqual(redacted["supabase_key"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["secret_token"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["normal_field"], "public_data")

    def test_browser_adapter_tab_listing_and_title_cleaning(self):
        """Brauzer adapteri oynalarni topib, sarlavhadan brauzer nomini tozalashi kerak"""
        mock_gui = MagicMock()
        mock_gui.list_windows.return_value = [
            WindowTarget(hwnd=101, title="YouTube - Google Chrome", class_name="Chrome_WidgetWin_1", pid=5001, rect=(0, 0, 1000, 800), process_name="chrome.exe"),
            WindowTarget(hwnd=102, title="GitHub: Where the world builds software - Brave", class_name="Chrome_WidgetWin_1", pid=5002, rect=(0, 0, 1000, 800), process_name="brave.exe"),
            WindowTarget(hwnd=103, title="Notepad", class_name="Notepad", pid=5003, rect=(0, 0, 600, 400), process_name="notepad.exe"),
        ]
        mock_gui.get_foreground_window.return_value = mock_gui.list_windows.return_value[0]

        adapter = BrowserAutomationAdapter(gui_controller=mock_gui)
        tabs = adapter.list_tabs()

        self.assertEqual(len(tabs), 2)
        # Chrome tab
        self.assertEqual(tabs[0].title, "YouTube")
        self.assertEqual(tabs[0].browser_type, "chrome")
        self.assertTrue(tabs[0].is_active)

        # Brave tab
        self.assertEqual(tabs[1].title, "GitHub: Where the world builds software")
        self.assertEqual(tabs[1].browser_type, "brave")
        self.assertFalse(tabs[1].is_active)

    def test_browser_adapter_navigation_and_validation(self):
        """Brauzer adapteri URL sxemasini xavfsiz to'ldirishi va navigatsiya qilishi kerak"""
        mock_gui = MagicMock()
        adapter = BrowserAutomationAdapter(gui_controller=mock_gui)

        with patch("webbrowser.open", return_value=True) as mock_open:
            # 1. Sxemasiz URL
            res1 = adapter.navigate("google.com")
            self.assertTrue(res1["success"])
            self.assertEqual(res1["url"], "https://google.com")
            mock_open.assert_called_with("https://google.com", new=2)

            # 2. Bo'sh URL
            res2 = adapter.navigate("")
            self.assertFalse(res2["success"])
            self.assertIn("bo'sh", res2["error"])

    def test_browser_adapter_dom_action_interface(self):
        """DOM action interfeysi CDP ga tayyor strukturalangan javob qaytarishi kerak"""
        adapter = BrowserAutomationAdapter(gui_controller=MagicMock())
        res = adapter.execute_dom_action(action="click", selector="#submit-button")

        self.assertTrue(res["success"])
        self.assertEqual(res["action"], "click")
        self.assertEqual(res["selector"], "#submit-button")
        self.assertFalse(res["cdp_attached"])

    def test_backend_version_handshake_simulation(self):
        """Supervisor handshake 9.0.2 backend bilan muvaffaqiyatli, 8.0.0 bilan mos kelmaslikni qaytarishi kerak"""
        # Handshake regex & logic simulation
        def parse_handshake(http_response: str, expected_version: str):
            is_healthy = "200 OK" in http_response and ("\"status\"" in http_response or "Misa AI" in http_response)
            version = ""
            if "\"version\"" in http_response:
                rest = http_response.split("\"version\"")[1]
                if ":" in rest:
                    parts = rest.split(":")[1].strip().lstrip("\"'")
                    version = parts.split("\"")[0]

            is_compatible = False
            if expected_version and version:
                exp_prefix = expected_version[:3]
                if version == expected_version or version.startswith(exp_prefix):
                    is_compatible = True
            return is_healthy, is_compatible, version

        resp_902 = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"status":"ok","app":"Misa AI","version":"9.0.2"}'
        h1, c1, v1 = parse_handshake(resp_902, "9.0.2")
        self.assertTrue(h1)
        self.assertTrue(c1)
        self.assertEqual(v1, "9.0.2")

        resp_old = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"status":"ok","app":"Misa AI","version":"8.0.0"}'
        h2, c2, v2 = parse_handshake(resp_old, "9.0.2")
        self.assertTrue(h2)
        self.assertFalse(c2, "Eski 8.0.0 versiyasi 9.0.2 ga mos kelmasligi kerak")
        self.assertEqual(v2, "8.0.0")


if __name__ == "__main__":
    unittest.main()
