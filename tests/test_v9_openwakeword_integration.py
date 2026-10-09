# -*- coding: utf-8 -*-
"""
Misa AI — Secure Local openWakeWord & Fallback Integration Tests (v9.0.0)
Tekshiruvlar:
1. Maxfiylik va Offline tekshiruvi: Runtime vaqtida internetga so'rov yuborilmasligi.
2. Model mavjud bo'lmaganda 'model_missing' holati va avtomatik lokal akustik fallback.
3. Mock ONNX modeli bilan 'ready' holati, to'g'ri inferens va uyg'onish callback hodisasi.
4. Cooldown va Misa gapirayotganda o'z ovozidan qayta uyg'onmaslik (AEC / Cooldown).
5. REST API (/api/voice/wakeword/status, /api/voice/wakeword/configure) va telemetriya.
6. Xavfsiz xatoliklarni qayta ishlash (bo'sh freymlar, noto'g'ri parametrlar).
"""

import os
import sys
import time
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

# Ishchi yo'llarni ulash
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)

from core.voice.wake_word import (
    WakeWordDetector,
    OpenWakeWordEngine,
    AcousticWakeWordDetector,
    DEFAULT_PRIMARY_PHRASE,
    DEFAULT_MODEL_FILENAME
)
from core.voice.service import ConversationalVoiceService, VoiceServiceState


class TestOpenWakeWordEnginePrivacyAndFallback:
    """openWakeWord dvigatelining lokal va maxfiy ishlashini tekshirish"""

    def test_openwakeword_engine_model_missing_without_network_call(self):
        """Model fayli diskda yo'q bo'lganda internetga so'rov yubormasdan model_missing qaytarishi"""
        non_existent_path = os.path.join(_base_dir, "models", "wake_word", "non_existent_salom_misa.onnx")

        # Tarmoq so'rovlarini to'liq bloklash uchun requests va socket patch qilinadi
        with patch("urllib.request.urlopen") as mock_url, patch("requests.get") as mock_req:
            engine = OpenWakeWordEngine(model_path=non_existent_path, phrase="Salom Misa")

            assert engine.status == "model_missing"
            assert not engine.is_ready()
            assert "topilmadi" in engine.status_message or "not found" in engine.status_message.lower()

            # Tarmoqqa hech qanday so'rov ketmagan bo'lishi shart!
            mock_url.assert_not_called()
            mock_req.assert_not_called()

    def test_openwakeword_predict_safe_when_uninitialized(self):
        """Dvigatel tayyor bo'lmaganda predict xavfsiz (False, 0.0, thresh) qaytaradi"""
        engine = OpenWakeWordEngine(model_path="invalid.onnx")
        audio_chunk = np.zeros(1600, dtype=np.float32)

        is_detected, score, thresh = engine.predict(audio_chunk)
        assert is_detected is False
        assert score == 0.0
        assert thresh > 0.0


class TestMockNeuralWakeWordInference:
    """Mock qilingan ONNX neyrotarmoq modeli bilan to'liq inferens tekshiruvi"""

    def test_mock_oww_model_detection(self):
        """Mock openWakeWord modeli yuqori ball berganida aniqlash muvaffaqiyatli bo'lishi"""
        engine = OpenWakeWordEngine(model_path="dummy.onnx", sensitivity=0.7)

        # Mock model yaratamiz
        mock_model = MagicMock()
        mock_model.predict.return_value = {"salom_misa": 0.88}

        engine._model = mock_model
        engine.status = "ready"
        engine.threshold = 0.50

        assert engine.is_ready()

        audio_chunk = np.random.uniform(-0.5, 0.5, 1600).astype(np.float32)
        detected, score, thresh = engine.predict(audio_chunk)

        assert detected is True
        assert score == 0.88
        assert thresh == 0.50

    def test_mock_oww_model_below_threshold_no_false_positive(self):
        """Past ehtimollikda (shovqin / begona suhbat) uyg'onmasligi"""
        engine = OpenWakeWordEngine(model_path="dummy.onnx", sensitivity=0.5)

        mock_model = MagicMock()
        mock_model.predict.return_value = {"salom_misa": 0.15}

        engine._model = mock_model
        engine.status = "ready"
        engine.threshold = 0.60

        audio_chunk = np.random.uniform(-0.1, 0.1, 1600).astype(np.float32)
        detected, score, thresh = engine.predict(audio_chunk)

        assert detected is False
        assert score == 0.15


class TestUnifiedWakeWordOrchestrator:
    """Yagona WakeWordDetector orkestratori va akustik fallback tekshiruvi"""

    def test_orchestrator_initializes_with_status(self):
        """Orkestrator to'liq telemetriya va holat ma'lumotlarini taqdim etishi"""
        detector = WakeWordDetector(sensitivity=0.65)
        status = detector.get_status()

        assert status["phrase"] == "Salom Misa"
        assert "openwakeword" in status
        assert "acoustic_fallback" in status
        assert "security" in status
        assert status["security"]["offline_guarantee"] is True
        assert status["security"]["zero_network_leaks"] is True

    def test_orchestrator_cooldown_prevents_duplicate_wake(self):
        """Cooldown vaqti oralig'ida takroriy uyg'onish sodir bo'lmasligi"""
        detector = WakeWordDetector(sensitivity=0.65)
        detector._cooldown_seconds = 2.0
        detector._last_wake_time = time.time()  # hozirgina uyg'ongan

        # Freym berilganda cooldown tufayli False qaytarishi shart
        audio_chunk = np.ones(1600, dtype=np.float32) * 0.1
        res = detector.process_frame(audio_chunk)
        assert res is False

    def test_orchestrator_configure_updates_sensitivity_and_cooldown(self):
        """configure() metodi sezuvchanlik va cooldownni dinamik yangilashi"""
        detector = WakeWordDetector(sensitivity=0.5)
        updated = detector.configure(sensitivity=0.85, cooldown=1.2)

        assert detector.sensitivity == 0.85
        assert detector._cooldown_seconds == 1.2
        assert updated["sensitivity"] == 0.85
        assert updated["cooldown_seconds"] == 1.2

    def test_orchestrator_wake_callback_dispatch(self):
        """Uyg'onish sodir bo'lganda callback chaqirilishi va ma'lumot uzatilishi"""
        callback_mock = MagicMock()
        detector = WakeWordDetector(on_wake_detected=callback_mock)

        # Mock openwakeword tayyor holatga keltiriladi
        detector.oww_engine.is_ready = MagicMock(return_value=True)
        detector.oww_engine.predict = MagicMock(return_value=(True, 0.92, 0.50))
        detector._last_wake_time = 0.0

        audio_chunk = np.zeros(1600, dtype=np.float32)
        res = detector.process_frame(audio_chunk)

        assert res is True
        callback_mock.assert_called_once()
        call_arg = callback_mock.call_args[0][0]
        assert call_arg["phrase"] == "Salom Misa"
        assert call_arg["engine"] == "openwakeword"
        assert call_arg["score"] == 0.92


class TestConversationalVoiceServiceIntegration:
    """ConversationalVoiceService bilan uyg'onish sikli va hodisalar integratsiyasi"""

    def test_service_registers_wake_callback_and_transitions_state(self):
        """Service uyg'onish hodisasini qabul qilib WAKE_DETECTED va ACKNOWLEDGING ga o'tishi"""
        service = ConversationalVoiceService()
        state_log = []
        wake_log = []

        service.add_state_callback(lambda st: state_log.append(st))
        service.add_wake_callback(lambda data: wake_log.append(data))

        # Ovozli ijroni mock qilamiz (karnay kutmasligi uchun)
        service.voice_manager.speak = MagicMock()

        # Uyg'onish hodisasini simulyatsiya qilamiz
        service._on_wake_detected({"phrase": "Salom Misa", "engine": "openwakeword", "score": 0.89})

        assert len(wake_log) == 1
        assert wake_log[0]["phrase"] == "Salom Misa"
        assert wake_log[0]["score"] == 0.89
        assert VoiceServiceState.WAKE_DETECTED in state_log
        assert VoiceServiceState.ACKNOWLEDGING in state_log

    def test_service_echo_suppression_resets_detector(self):
        """Karnay gapirayotganda yoki tugagach, detektor tozalanishi va cooldown o'rnatilishi"""
        service = ConversationalVoiceService()
        service.wake_detector.reset = MagicMock()

        service._on_wake_detected({"phrase": "Salom Misa"})
        service.wake_detector.reset.assert_called()
