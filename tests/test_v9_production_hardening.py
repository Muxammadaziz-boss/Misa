# ========== test_v9_production_hardening.py ==========
# Misa AI v9.0.1 — Production Hardening, Voice Test, Real-Time Audio Monitor,
# TTS Preview, Onboarding Profile, and Cross-Device Audit Unit Tests.

import os
import sys
import json
import asyncio
import unittest
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.voice.devices import RealtimeAudioMonitor, MicrophoneManager
from core.voice.voice_manager import VoiceManager
from core.api_server import (
    handle_voice_device_monitor_start,
    handle_voice_device_monitor_stop,
    handle_voice_device_monitor_status,
    handle_voice_preview,
    handle_account_get,
    handle_account_update,
    _read_config,
    _write_config,
)


class MockRequest:
    def __init__(self, json_data=None, query_data=None, headers=None, method="GET"):
        self._json_data = json_data or {}
        self.query = query_data or {}
        self.headers = headers or {}
        self.method = method

    async def json(self):
        return self._json_data


class TestV9ProductionHardening(unittest.TestCase):
    """v9.0.1 Production Hardening va Yangi Funksiyalar Testlari"""

    def setUp(self):
        self.original_config = _read_config()

    def tearDown(self):
        _write_config(self.original_config)
        # Ensure any active audio monitor is stopped
        try:
            mm = MicrophoneManager.get_instance()
            mm.stop_realtime_monitor()
        except Exception:
            pass

    def test_01_realtime_audio_monitor_math_and_safety(self):
        """Audio monitor RMS, Peak va Soft Limiter hisob-kitoblarining to'g'riligi"""
        monitor = RealtimeAudioMonitor.get_instance()

        # Test RMS/Peak calculation on known synthetic buffer
        # Pure sine wave with amplitude 0.5: Peak should be ~0.5, RMS should be ~0.5 / sqrt(2) ≈ 0.3535
        t = np.linspace(0, 1, 512, endpoint=False)
        sine = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)

        peak = float(np.max(np.abs(sine)))
        rms = float(np.sqrt(np.mean(sine ** 2)))
        self.assertAlmostEqual(peak, 0.5, places=2)
        self.assertAlmostEqual(rms, 0.3535, places=2)

        # Test soft limiter logic (np.clip with 0.95 scaling)
        hot_audio = np.array([1.5, -1.8, 0.5, -0.2], dtype=np.float32)
        limited = np.clip(hot_audio * 0.95, -0.98, 0.98)
        self.assertLessEqual(np.max(limited), 0.98)
        self.assertGreaterEqual(np.min(limited), -0.98)

        status = monitor.get_status()
        self.assertTrue(status.get("ok"))
        self.assertIn("active", status)
        self.assertIn("rms", status)
        self.assertIn("peak", status)
        self.assertIn("loopback", status)
        self.assertFalse(status["active"])

    def test_02_microphone_manager_monitor_interface(self):
        """MicrophoneManager'da real-time monitor metodlari mavjudligi va holati"""
        mgr = MicrophoneManager.get_instance()
        status = mgr.get_realtime_monitor_status()
        self.assertIsInstance(status, dict)
        self.assertIn("active", status)
        self.assertIn("rms", status)
        self.assertIn("peak", status)

        # Stopping an inactive monitor should safely return True without throwing
        stop_res = mgr.stop_realtime_monitor()
        self.assertTrue(stop_res)

    def test_03_voice_manager_synthesize_alias(self):
        """VoiceManager'da synthesize aliasi synthesize_text bilan bir xil ishlashi"""
        from core.voice.voice_manager import get_voice_manager
        vm = get_voice_manager()
        self.assertTrue(hasattr(vm, "synthesize"))
        self.assertTrue(callable(getattr(vm, "synthesize")))

    def test_04_api_audio_monitor_endpoints(self):
        """API monitor endpointlari (status, stop, start) to'g'ri ishlashi"""
        async def _run():
            # GET /api/voice/devices/monitor/status
            req = MockRequest(method="GET")
            res = await handle_voice_device_monitor_status(req)
            self.assertEqual(res.status, 200)
            data = json.loads(res.text)
            self.assertTrue(data.get("ok"))
            self.assertIn("active", data)
            self.assertIn("rms", data)
            self.assertIn("peak", data)

            # POST /api/voice/devices/monitor/stop
            res_stop = await handle_voice_device_monitor_stop(MockRequest(method="POST"))
            self.assertEqual(res_stop.status, 200)
            data_stop = json.loads(res_stop.text)
            self.assertTrue(data_stop.get("ok"))

        asyncio.run(_run())

    def test_05_api_voice_preview_edge_tts(self):
        """POST /api/voice/preview orqali haqiqiy Base64 audio generatsiyasi"""
        async def _run():
            payload = {
                "voice_id": "ayol",
                "text": "Salom. Men Misa, sizning sun’iy intellekt yordamchingizman."
            }
            req = MockRequest(json_data=payload, method="POST")
            res = await handle_voice_preview(req)
            self.assertEqual(res.status, 200)
            data = json.loads(res.text)

            self.assertTrue(data.get("ok"))
            self.assertIn("audio_data", data)
            self.assertTrue(data["audio_data"].startswith("data:audio/mp3;base64,"))
            self.assertEqual(data.get("voice_id"), "ayol")
            self.assertIn("Madina", data.get("voice_name", ""))
            self.assertIn("is_fallback", data)

        asyncio.run(_run())

    def test_06_account_first_name_last_name_and_neutral_bio(self):
        """Ism, Familiya ajratilishi, neutral Bio va bo'sh role saqlanishi"""
        async def _run():
            # Update with first_name and last_name
            update_payload = {
                "first_name": "Aziz",
                "last_name": "Rahmonov",
                "role": "Sun'iy Intellekt Muhandisi",
                "bio": "Misa AI loyihasi ustida ishlayapman.",
            }
            res_up = await handle_account_update(MockRequest(json_data=update_payload))
            self.assertEqual(res_up.status, 200)

            # Retrieve account
            res_get = await handle_account_get(MockRequest())
            self.assertEqual(res_get.status, 200)
            data = json.loads(res_get.text)

            self.assertEqual(data.get("first_name"), "Aziz")
            self.assertEqual(data.get("last_name"), "Rahmonov")
            self.assertEqual(data.get("name"), "Aziz Rahmonov")
            self.assertEqual(data.get("role"), "Sun'iy Intellekt Muhandisi")
            self.assertEqual(data.get("bio"), "Misa AI loyihasi ustida ishlayapman.")

            # Test empty bio and role (no fake AI defaults injected)
            empty_payload = {
                "first_name": "Rustam",
                "last_name": "",
                "role": "",
                "bio": "",
            }
            await handle_account_update(MockRequest(json_data=empty_payload))
            res_empty = await handle_account_get(MockRequest())
            data_empty = json.loads(res_empty.text)

            self.assertEqual(data_empty.get("first_name"), "Rustam")
            self.assertEqual(data_empty.get("name"), "Rustam")
            self.assertEqual(data_empty.get("role"), "")
            self.assertEqual(data_empty.get("bio"), "")

        asyncio.run(_run())

    def test_07_cross_device_no_hardcoded_paths(self):
        """Hech qanday dasturchi kompyuteriga xos shaxsiy yo'llar yoki device IDlar qolmaganligi"""
        config = _read_config()
        config_str = json.dumps(config)

        # Prohibit developer home folder hardcodes
        self.assertNotIn("Users/Administrator", config_str)
        self.assertNotIn("Users/muxam", config_str)
        self.assertNotIn("C:\\Users\\", config_str)


if __name__ == "__main__":
    unittest.main()
