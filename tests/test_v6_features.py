# ========== test_v6_features.py ==========
# Misa AI v6.0.0 yangi funksiyalari uchun Unit-testlar to'plami

import unittest

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from core.audio_service import AudioService, get_audio_service
from core.command_dispatcher import CommandDispatcher
from core.agents.system_agent import SystemAgent
from config import get_config


class TestV6AudioService(unittest.TestCase):
    """AudioService va VAD testlari"""

    def setUp(self):
        self.audio = AudioService(sample_rate=16000)

    def test_audio_service_initialization(self):
        self.assertEqual(self.audio.sample_rate, 16000)
        self.assertEqual(self.audio.channels, 1)
        self.assertGreater(self.audio.vad_threshold, 0)
        self.assertGreater(self.audio.silence_timeout, 0)

    @unittest.skipUnless(NUMPY_AVAILABLE, "numpy moduli o'rnatilmagan")
    def test_calculate_rms(self):
        # Jimlik uchun RMS 0 bo'lishi kerak
        silence = np.zeros(1600, dtype="float32")
        rms_silence = self.audio.calculate_rms(silence)
        self.assertEqual(rms_silence, 0.0)

        # Ovozli signal uchun RMS noldan katta bo'lishi kerak
        signal = np.ones(1600, dtype="float32") * 0.5
        rms_signal = self.audio.calculate_rms(signal)
        self.assertAlmostEqual(rms_signal, 0.5, places=3)

    def test_calculate_rms_none(self):
        self.assertEqual(self.audio.calculate_rms(None), 0.0)

    def test_singleton_instance(self):
        s1 = get_audio_service()
        s2 = get_audio_service()
        self.assertIs(s1, s2)


class TestV6CommandDispatcher(unittest.TestCase):
    """CommandDispatcher tezkor mahalliy buyruqlar testi"""

    def setUp(self):
        self.dispatcher = CommandDispatcher()

    def test_time_command(self):
        handled, msg = self.dispatcher.dispatch_local("soat necha")
        self.assertTrue(handled)
        self.assertIn("Hozirgi vaqt", msg)

    def test_date_command(self):
        handled, msg = self.dispatcher.dispatch_local("bugun qaysi kun")
        self.assertTrue(handled)
        self.assertIn("Bugun", msg)

    def test_unknown_command_returns_false(self):
        handled, msg = self.dispatcher.dispatch_local("dasturlash bo'yicha maslahat ber")
        self.assertFalse(handled)
        self.assertEqual(msg, "")

    def test_custom_handler_registration(self):
        def my_custom(text):
            if "maxsus" in text:
                return True, "Maxsus bajarildi"
            return False, ""

        self.dispatcher.register_handler("custom", my_custom)
        handled, msg = self.dispatcher.dispatch_local("bu maxsus sinov")
        self.assertTrue(handled)
        self.assertEqual(msg, "Maxsus bajarildi")


class TestV6SystemAgent(unittest.TestCase):
    """SystemAgent monitoring va resurslar testi"""

    def setUp(self):
        def dummy_ai_call(prompt, system_prompt):
            return "Tizim holati barqaror."

        self.agent = SystemAgent(dummy_ai_call)

    def test_can_handle(self):
        self.assertTrue(self.agent.can_handle("tizimni monitoring qil"))
        self.assertTrue(self.agent.can_handle("RAM xotirani ko'rsat"))
        self.assertTrue(self.agent.can_handle("temp keshni tozala"))
        self.assertFalse(self.agent.can_handle("musiqa qo'y"))

    @unittest.skipUnless(PSUTIL_AVAILABLE, "psutil moduli o'rnatilmagan")
    def test_system_health_stats(self):
        stats = self.agent.get_system_health()
        self.assertIn("cpu_percent", stats)
        self.assertIn("ram_percent", stats)
        self.assertIn("disk_percent", stats)
        self.assertIsInstance(stats["cpu_percent"], (int, float))

    def test_execute(self):
        result = self.agent.run("tizim xotirasini tahlil qil")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["agent"], "SystemAgent")
        self.assertIn("response", result)


class TestV6VersionAndConfig(unittest.TestCase):
    """Versiya 9.0.0 ekanligini tasdiqlash testi"""

    def test_version_number(self):
        from main import VERSION
        self.assertTrue(str(VERSION).startswith("9.0"))

    def test_config_version(self):
        version = get_config("app.version")
        self.assertTrue(str(version).startswith("9.0"))


if __name__ == "__main__":
    unittest.main()
