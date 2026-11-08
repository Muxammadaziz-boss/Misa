# -*- coding: utf-8 -*-
"""
Tests for Misa AI Wake-Word Production Fix and Reconciliation.
Verifies:
1. Single-owner idempotent wake callback dispatch (no double execution).
2. Rapid repeated wake cooldown guard.
3. Honest engine status reporting (heuristic fallback vs missing ONNX models).
4. Google STT failure / empty transcription polite retry recovery.
5. Invocation phrase detection & clean command extraction without requiring 'Salom'.
6. Follow-up window command acceptance.
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from core.voice.wake_word import WakeWordDetector, DEFAULT_PRIMARY_PHRASE, DEFAULT_ALTERNATIVE_PHRASES
from core.voice.service import ConversationalVoiceService, VoiceServiceState


class TestWakeWordProductionFix:
    def test_default_invocation_phrases(self):
        """Verifies primary phrase is 'Misa' and does not strictly require 'Salom'."""
        assert DEFAULT_PRIMARY_PHRASE == "Misa"
        assert "Misa" in DEFAULT_ALTERNATIVE_PHRASES
        assert "Salom Misa" in DEFAULT_ALTERNATIVE_PHRASES
        assert "Hey Misa" in DEFAULT_ALTERNATIVE_PHRASES

    def test_engine_status_honesty(self):
        """Detector must honestly report fallback when trained models are missing."""
        detector = WakeWordDetector(sample_rate=16000)
        status = detector.get_status()

        # In current repo, openwakeword/onnx models are dummy/missing
        assert status["is_trained_model"] is False
        assert status["active_engine"] == "heuristic_spectral_fallback"
        assert "models_required" in status
        assert len(status["models_required"]) == 3
        assert status["primary_phrase"] == "Misa"

    def test_clean_command_extraction(self):
        """Verifies clean extraction of user command after various wake words."""
        service = ConversationalVoiceService()

        # Standalone "Misa" prefix
        assert service.extract_clean_command("Misa bugun ob-havo qanday") == "bugun ob-havo qanday"
        assert service.extract_clean_command("misa, yordam ber") == "yordam ber"

        # Alternative prefixes
        assert service.extract_clean_command("Salom Misa nima yangiliklar") == "nima yangiliklar"
        assert service.extract_clean_command("Hey Misa konspekt yarat") == "konspekt yarat"
        assert service.extract_clean_command("Mikasa faylni ko'rsat") == "faylni ko'rsat"

    def test_is_misa_invocation(self):
        """Matches 'Misa' standalone or inside text."""
        service = ConversationalVoiceService()
        assert service.is_misa_invocation("Misa") is True
        assert service.is_misa_invocation("Salom Misa!") is True
        assert service.is_misa_invocation("Hey Mikasa") is True
        assert service.is_misa_invocation("Bugun ob-havo qanday") is False

    def test_single_owner_idempotent_wake(self):
        """
        One acoustic detection must trigger on_wake_detected exactly once,
        queue exactly 1 acknowledgment speech, and invoke registered callbacks once.
        """
        service = ConversationalVoiceService()
        service.state = VoiceServiceState.IDLE

        wake_callback = MagicMock()
        service.add_wake_callback(wake_callback)

        with patch.object(service.voice_manager, "speak") as mock_speak:
            event = {
                "detected": True,
                "phrase": "Misa",
                "score": 0.88,
                "engine": "heuristic_spectral_fallback",
                "timestamp": time.time()
            }

            # Direct single wake invocation
            service._on_wake_detected(event)

            # Assert state transitioned to acknowledging
            assert service.state == VoiceServiceState.ACKNOWLEDGING

            # Assert registered wake callback called exactly once
            assert wake_callback.call_count == 1

            # Assert speak called exactly once for acknowledgment
            assert mock_speak.call_count == 1
            args, kwargs = mock_speak.call_args
            assert "Ha, eshitaman." in args[0]

    def test_concurrent_or_repeated_wake_cooldown(self):
        """
        A second wake event fired within the 1.5s cooldown or while already acknowledging
        must be dropped by the idempotency guard.
        """
        service = ConversationalVoiceService()
        service.state = VoiceServiceState.IDLE

        wake_callback = MagicMock()
        service.add_wake_callback(wake_callback)

        with patch.object(service.voice_manager, "speak") as mock_speak:
            event = {"detected": True, "phrase": "Misa", "score": 0.9}

            # First wake
            service._on_wake_detected(event)
            assert wake_callback.call_count == 1
            assert mock_speak.call_count == 1

            # Immediate second wake (within cooldown)
            service._on_wake_detected(event)

            # Must still be 1 (second was dropped)
            assert wake_callback.call_count == 1
            assert mock_speak.call_count == 1

    def test_empty_stt_failure_recovery(self):
        """
        When STT returns empty or unintelligible speech, the service should not crash or silently drop.
        It must speak a polite retry prompt and reopen the listening window.
        """
        service = ConversationalVoiceService()
        service.state = VoiceServiceState.THINKING

        with patch.object(service, "_speak_and_listen_follow_up") as mock_retry:
            service._process_user_utterance("")

            assert mock_retry.call_count == 1
            retry_text = mock_retry.call_args[0][0]
            assert "Kechirasiz, qayta ayta olasizmi?" in retry_text

    def test_follow_up_window_command_gate(self):
        """
        In active follow-up window, commands without wake word must be accepted.
        """
        service = ConversationalVoiceService()
        service.state = VoiceServiceState.THINKING

        # Mock session to simulate active follow-up
        service.session.is_in_follow_up_window = MagicMock(return_value=True)

        with patch.object(service.stt_manager, "transcribe", return_value="ertaga ob-havo qanday bo'ladi"):
            with patch.object(service, "_dispatch_to_misa_intelligence") as mock_dispatch:
                service._process_user_utterance(MagicMock())
                assert mock_dispatch.call_count == 1
                assert mock_dispatch.call_args[0][0] == "ertaga ob-havo qanday bo'ladi"
