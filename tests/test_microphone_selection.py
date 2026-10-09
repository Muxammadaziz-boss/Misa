# -*- coding: utf-8 -*-
"""
Misa AI — Microphone Device Selection, Enumeration, Persistence & Fallback Tests
"""

import unittest
from unittest.mock import patch, MagicMock
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from core.voice.devices import MicrophoneManager, _save_persisted_microphone, _read_persisted_microphone
from core.api_server import create_app


class TestMicrophoneManagerUnit(unittest.TestCase):
    def setUp(self):
        self.mgr = MicrophoneManager.get_instance()

    def test_get_input_devices_contains_default_and_capture_only(self):
        devices = self.mgr.get_input_devices()
        self.assertGreater(len(devices), 0)
        # 1-element Tizim standarti bo'lishi kerak
        self.assertEqual(devices[0]["id"], "default")
        self.assertTrue(devices[0]["available"])
        self.assertEqual(devices[0]["type"], "input")

        # Barcha qurilmalar faqat "input" turida bo'lishi shart (hech qanday speaker/output yo'q)
        for d in devices:
            self.assertEqual(d["type"], "input")
            self.assertIn("name", d)
            self.assertIn("id", d)

    def test_persistence_save_and_read(self):
        test_id = "dev_test_bm800"
        test_name = "BM 800 Condenser Mic"
        _save_persisted_microphone(test_id, test_name)
        saved_id, saved_name = _read_persisted_microphone()
        self.assertEqual(saved_id, test_id)
        self.assertEqual(saved_name, test_name)

    def test_fallback_when_device_disconnected(self):
        """Ulanmagan yoki soxta qurilma tanlanganda yashirincha emas, aniq ogohlantirish bilan fallback qilish."""
        self.mgr.set_selected_device("dev_non_existent_999", "BM 800 (Yo'q)")
        idx, dev_info, fallback_used, msg = self.mgr.resolve_selected_device()
        
        # Fallback ishlatilgan bo'lishi kerak
        self.assertTrue(fallback_used)
        self.assertIn("ulanmagan", msg.lower())
        self.assertIn("default", msg.lower())

    def test_select_default_policy(self):
        """Default tanlanganda fallback ishlatilmasligi kerak."""
        self.mgr.set_selected_device("default", "Tizim standarti (Windows Default)")
        idx, dev_info, fallback_used, msg = self.mgr.resolve_selected_device()
        self.assertFalse(fallback_used)
        self.assertEqual(dev_info.get("id"), "default")

    def test_real_microphone_test_execution(self):
        """Haqiqiy apparatda yoki mavjud mikrofonda test o'tkazish."""
        res = self.mgr.test_microphone(duration_s=0.3)
        self.assertIn("ok", res)
        self.assertIn("working", res)
        self.assertIn("level", res)
        self.assertIn("status", res)
        self.assertIn("message", res)


class TestMicrophoneApiEndpoints(AioHTTPTestCase):
    async def get_application(self):
        return create_app()

    @unittest_run_loop
    async def test_get_voice_devices_endpoint(self):
        resp = await self.client.request("GET", "/api/voice/devices")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("devices", data)
        self.assertIn("selected_device_id", data)
        self.assertGreater(len(data["devices"]), 0)

    @unittest_run_loop
    async def test_select_voice_device_endpoint(self):
        resp = await self.client.request(
            "POST",
            "/api/voice/devices/select",
            json={"device_id": "default", "device_name": "Tizim standarti"}
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("selected_device_id"), "default")

    @unittest_run_loop
    async def test_test_voice_device_endpoint(self):
        resp = await self.client.request(
            "POST",
            "/api/voice/devices/test",
            json={"device_id": "default"}
        )
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertIn("ok", data)
        self.assertIn("level", data)
        self.assertIn("status", data)

    @unittest_run_loop
    async def test_voice_diagnostic_includes_microphone_info(self):
        resp = await self.client.request("GET", "/api/voice/diagnostic")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("Microphone", data)
        self.assertIn("selected_device_id", data)
        self.assertIn("fallback_used", data)
        self.assertIn("microphone_status", data)


if __name__ == "__main__":
    unittest.main()
