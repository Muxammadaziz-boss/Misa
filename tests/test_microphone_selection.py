# -*- coding: utf-8 -*-
"""
Misa AI — Universal Microphone Device Selection, Dynamic Enumeration, Hot-Plug & Pipeline Integration Tests
Barcha apparat turlari (USB mikrofonlar, veb-kameralar, tashqi audio interfeyslar, o'rnatilgan mikrofonlar)
uchun dinamik topish, karnaylarni qat'iy chiqarish, hot-plug refresh va tanlangan qurilmadan audio olish sinovlari.
"""

import unittest
from unittest.mock import patch, MagicMock
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from core.voice.devices import (
    MicrophoneManager,
    _save_persisted_microphone,
    _read_persisted_microphone,
    _normalize_device_name,
)
from core.api_server import create_app
from core.voice.service import get_conversational_voice_service


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

    def test_output_devices_are_strictly_excluded_from_enumeration(self):
        """Karnaylar (speakers) va chiqish qurilmalari ro'yxatga kirmasligini tekshirish."""
        mock_raw_devices = [
            {"name": "Speakers (Realtek Audio)", "max_input_channels": 0, "max_output_channels": 2, "hostapi": 1},
            {"name": "Headphones (Bluetooth Stereo)", "max_input_channels": 0, "max_output_channels": 2, "hostapi": 1},
            {"name": "USB Audio Microphone", "max_input_channels": 1, "max_output_channels": 0, "hostapi": 1, "default_samplerate": 48000},
            {"name": "Laptop Built-in Microphone", "max_input_channels": 2, "max_output_channels": 0, "hostapi": 0, "default_samplerate": 44100},
        ]
        with patch("sounddevice.query_devices", return_value=mock_raw_devices):
            with patch("sounddevice.default", MagicMock(device=[2, 0])):
                devs = self.mgr.get_input_devices()
                names = [d["name"] for d in devs]
                # Chiqish karnaylari ro'yxatda yo'qligini tekshirish
                self.assertNotIn("Speakers (Realtek Audio)", names)
                self.assertNotIn("Headphones (Bluetooth Stereo)", names)
                # Kirish qurilmalari ro'yxatda borligini tekshirish
                self.assertTrue(any("USB Audio Microphone" in n for n in names))
                self.assertTrue(any("Laptop Built-in Microphone" in n for n in names))

    def test_hot_plug_re_enumeration_discovers_new_device(self):
        """Microphone yangi ulanganda (hot-plug) refresh orqali darhol paydo bo'lishi."""
        initial_devices = [
            {"name": "Internal Mic", "max_input_channels": 2, "max_output_channels": 0, "hostapi": 1, "default_samplerate": 44100},
        ]
        hot_plugged_devices = [
            {"name": "Internal Mic", "max_input_channels": 2, "max_output_channels": 0, "hostapi": 1, "default_samplerate": 44100},
            {"name": "External Studio USB Mic", "max_input_channels": 1, "max_output_channels": 0, "hostapi": 1, "default_samplerate": 48000},
        ]

        with patch("sounddevice.default", MagicMock(device=[0, 0])):
            with patch("sounddevice._terminate") as mock_term, patch("sounddevice._initialize") as mock_init:
                with patch("sounddevice.query_devices", side_effect=[initial_devices, hot_plugged_devices]):
                    # Dastlabki holat
                    devs_1 = self.mgr.get_input_devices()
                    names_1 = [d["name"] for d in devs_1]
                    self.assertFalse(any("External Studio USB Mic" in n for n in names_1))

                    # Refresh chaqirilganda
                    devs_2 = self.mgr.refresh_devices()
                    mock_term.assert_called_once()
                    mock_init.assert_called_once()
                    names_2 = [d["name"] for d in devs_2]
                    self.assertTrue(any("External Studio USB Mic" in n for n in names_2))

    def test_persistence_save_and_read(self):
        test_id = "input_test_generic_mic"
        test_name = "Universal Condenser Mic"
        _save_persisted_microphone(test_id, test_name)
        saved_id, saved_name = _read_persisted_microphone()
        self.assertEqual(saved_id, test_id)
        self.assertEqual(saved_name, test_name)

    def test_fallback_when_device_disconnected(self):
        """Ulanmagan yoki soxta qurilma tanlanganda yashirincha emas, aniq ogohlantirish bilan fallback qilish."""
        self.mgr.set_selected_device("input_non_existent_999", "Mavjud bo'lmagan mikrofon")
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

    def test_conversational_voice_service_microphone_integration(self):
        """Voice Service tanlangan mikrofonga ulanishi va qayta ulanish signalini berishi."""
        service = get_conversational_voice_service()
        res = service.set_microphone("default", "Tizim standarti")
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("selected_device_id"), "default")
        # _reconnect_stream_event o'rnatilgan bo'lishi kerak
        self.assertTrue(service._reconnect_stream_event.is_set())


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
    async def test_refresh_voice_devices_endpoint(self):
        resp = await self.client.request("POST", "/api/voice/devices/refresh")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("devices", data)

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
