# ========== test_account_api.py ==========
# Phase 15 — Account API Unit Tests (Profile, Voice, AI, Appearance, Notifications, Privacy, About)

import os
import sys
import json
import asyncio
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.api_server import (
    handle_account_get,
    handle_account_update,
    CONFIG_FILE,
    _read_config,
    _write_config,
)


class MockRequest:
    def __init__(self, json_data=None, query_data=None, headers=None):
        self._json_data = json_data or {}
        self.query = query_data or {}
        self.headers = headers or {}

    async def json(self):
        return self._json_data


class TestAccountAPI(unittest.TestCase):
    """Account & Settings API testlari"""

    def setUp(self):
        # Asl config nusxasini saqlab turish
        self.original_config = _read_config()

    def tearDown(self):
        # Asl config ni qayta tiklash
        _write_config(self.original_config)

    def test_account_get_structure(self):
        """GET /api/account to'liq Phase 15 arxitekturasi bo'yicha ma'lumot qaytaradi"""
        async def _run():
            resp = await handle_account_get(MockRequest())
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.text)

            self.assertTrue(data.get("ok"))
            self.assertIn("name", data)
            self.assertIn("avatar", data)
            self.assertIn("role", data)
            self.assertIn("bio", data)
            self.assertIn("language", data)
            self.assertIn("voice_type", data)
            self.assertIn("tts_speed", data)
            self.assertIn("theme", data)
            self.assertIn("ai_model", data)
            self.assertIn("ai_mode", data)
            self.assertIn("thinking_enabled", data)
            self.assertIn("has_gemini_key", data)
            self.assertIn("version", data)
            self.assertIn("app_info", data)
            self.assertIn("notifications", data)
            self.assertIn("privacy", data)
            self.assertIn("voices_available", data)
            self.assertIn("ai_models_available", data)

            # Ovozlar soni va nomlari
            voices = data["voices_available"]
            self.assertGreaterEqual(len(voices), 2)
            voice_ids = [v["id"] for v in voices]
            self.assertIn("ayol", voice_ids)
            self.assertIn("erkak", voice_ids)

            # AI modellari
            ai_models = data["ai_models_available"]
            self.assertGreaterEqual(len(ai_models), 3)
            model_ids = [m["id"] for m in ai_models]
            self.assertIn("gemini", model_ids)
            self.assertIn("openrouter", model_ids)
            self.assertIn("local", model_ids)

            # App info
            self.assertEqual(data["app_info"]["name"], "Misa AI")
            self.assertTrue(data["app_info"]["version"].startswith("9.0"))

        asyncio.run(_run())

    def test_account_update_profile(self):
        """POST /api/account orqali foydalanuvchi profili ma'lumotlarini yangilash"""
        async def _run():
            update_payload = {
                "name": "Muhammadaziz",
                "avatar": "purple",
                "role": "Bosh Muhandis",
                "bio": "Misa AI yaratuvchisi",
                "language": "uz",
            }
            resp = await handle_account_update(MockRequest(json_data=update_payload))
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.text)
            self.assertTrue(res_data.get("ok"))
            self.assertEqual(res_data.get("name"), "Muhammadaziz")
            self.assertEqual(res_data.get("avatar"), "purple")

            # GET orqali tekshirish
            get_resp = await handle_account_get(MockRequest())
            get_data = json.loads(get_resp.text)
            self.assertEqual(get_data.get("name"), "Muhammadaziz")
            self.assertEqual(get_data.get("avatar"), "purple")
            self.assertEqual(get_data.get("role"), "Bosh Muhandis")
            self.assertEqual(get_data.get("bio"), "Misa AI yaratuvchisi")

        asyncio.run(_run())

    def test_account_update_voice_and_ai_settings(self):
        """POST /api/account orqali ovoz, AI va tashqi ko'rinish parametrlarini sozlash"""
        async def _run():
            settings_payload = {
                "voice_type": "erkak",
                "tts_speed": 1.8,
                "auto_speak": True,
                "vad_enabled": True,
                "theme": "oled",
                "ai_model": "openrouter",
                "ai_mode": "creative",
                "thinking_enabled": True,
                "notifications": {
                    "scheduler": True,
                    "voice": True,
                    "sound_effects": False,
                },
                "privacy": {
                    "local_storage_only": True,
                    "telemetry_disabled": True,
                },
            }
            resp = await handle_account_update(MockRequest(json_data=settings_payload))
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.text)
            self.assertTrue(res_data.get("ok"))
            self.assertEqual(res_data.get("voice_type"), "erkak")
            self.assertEqual(res_data.get("tts_speed"), 1.8)
            self.assertEqual(res_data.get("theme"), "oled")

            # GET orqali tekshirish
            get_resp = await handle_account_get(MockRequest())
            get_data = json.loads(get_resp.text)
            self.assertEqual(get_data.get("voice_type"), "erkak")
            self.assertEqual(get_data.get("tts_speed"), 1.8)
            self.assertEqual(get_data.get("theme"), "oled")
            self.assertEqual(get_data.get("ai_model"), "openrouter")
            self.assertEqual(get_data.get("ai_mode"), "creative")
            self.assertEqual(get_data.get("thinking_enabled"), True)
            self.assertFalse(get_data.get("notifications", {}).get("sound_effects"))

        asyncio.run(_run())

    def test_account_get_masked_key_safety(self):
        """API keylar hech qachon ochiq ko'rinmasligi va masked_key xavfsiz shakllanishi"""
        async def _run():
            from unittest.mock import patch, MagicMock

            # 1. Kalitsiz holat: barcha kalitlar bo'sh bo'lganda masked_key bo'sh bo'lishi va crash bo'lmasligi
            mock_mgr = MagicMock()
            mock_mgr.get_status_summary.return_value = {"active_keys": {}}
            mock_mgr.get_active_gemini_key.return_value = None

            with patch("core.v8.ai_key_manager.get_ai_key_manager", return_value=mock_mgr):
                old_env = os.environ.pop("GEMINI_API_KEY", None)
                try:
                    resp = await handle_account_get(MockRequest())
                    self.assertEqual(resp.status, 200)
                    data = json.loads(resp.text)
                    self.assertIn("api_key_masked", data)
                    self.assertIn("ai_keys", data)
                    self.assertIsInstance(data["api_key_masked"], str)
                    self.assertEqual(data["api_key_masked"], "")
                    self.assertFalse(data["has_gemini_key"])
                    self.assertEqual(data["ai_status"], "missing_key")

                    # 2. Kalit o'rnatilgan holat: maxfiy kalit xom holda chiqmasligi va xavfsiz maskalanishi
                    test_secret = "AIzaSySecretTestKey123456789"
                    mock_mgr.get_active_gemini_key.return_value = test_secret
                    resp_with_key = await handle_account_get(MockRequest())
                    self.assertEqual(resp_with_key.status, 200)
                    data_with_key = json.loads(resp_with_key.text)
                    masked = data_with_key.get("api_key_masked", "")

                    self.assertNotIn(test_secret, resp_with_key.text)
                    self.assertTrue(masked.startswith("AIzaSy...") or masked == "●●●●●●")
                    self.assertTrue(data_with_key["has_gemini_key"])
                    self.assertEqual(data_with_key["ai_status"], "ready")
                finally:
                    if old_env:
                        os.environ["GEMINI_API_KEY"] = old_env

    def test_account_get_404_for_unknown_user(self):
        """Mavjud bo'lmagan foydalanuvchi so'ralganda 404 qaytariladi"""
        async def _run():
            import uuid
            unknown_id = f"unknown_user_{uuid.uuid4().hex}"
            req = MockRequest(query_data={"user_id": unknown_id})
            resp = await handle_account_get(req)
            self.assertEqual(resp.status, 404)
            data = json.loads(resp.text)
            self.assertFalse(data.get("ok"))
            self.assertIn("topilmadi", data.get("error", "").lower())

        asyncio.run(_run())

    def test_account_get_401_for_invalid_token(self):
        """Yaroqsiz Bearer token yuborilganda 401 Unauthorized qaytariladi"""
        async def _run():
            req = MockRequest(headers={"Authorization": "Bearer invalid.fake.token.12345"})
            resp = await handle_account_get(req)
            self.assertEqual(resp.status, 401)
            data = json.loads(resp.text)
            self.assertFalse(data.get("ok"))

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()

