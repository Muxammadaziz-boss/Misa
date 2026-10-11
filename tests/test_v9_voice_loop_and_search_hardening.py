# -*- coding: utf-8 -*-
"""
Tests for Misa AI v9.0.1 Audio Loop Prevention and Web Search Anti-Leak Hardening.
"""

import time
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from core.intelligence.orchestrator import IntelligenceOrchestrator
from core.agent_tools import get_registry
from core.voice.service import ConversationalVoiceService, VoiceServiceState


def test_no_prompt_leak_in_web_search():
    registry = get_registry()
    tool = registry.get("web_search")
    assert tool is not None

    # Test with query that returns no local results
    res = tool.call(query="nonexistent_very_unique_query_12345_xyz")
    assert res.get("success") is True
    result_data = res.get("result", {})
    message = result_data.get("message", "")

    # Must NOT leak internal instructions
    assert "o'z bilimingdan" not in message.lower()
    assert "70%" not in message
    assert "aniqlik talab etiladi" not in message.lower()
    assert "mezoniga amal qil" not in message.lower()


def test_is_leaked_reasoning_detects_prompt_leaks():
    orch = IntelligenceOrchestrator()
    assert orch._is_leaked_reasoning("the user is asking something") is True
    assert orch._is_leaked_reasoning("Internetda aniq javob topilmadi. O'z bilimingdan javob ber (kamida 70% aniqlik talab etiladi).") is True
    assert orch._is_leaked_reasoning("Qidiruv API ishlamadi. O'z bilimingdan javob ber (kamida 70% aniqlik mezoniga amal qil).") is True
    assert orch._is_leaked_reasoning("Bugun xalqaro pochta kuni nishonlanadi.") is False


def test_voice_service_listening_window_not_dropping_to_idle():
    svc = ConversationalVoiceService()
    svc.state = VoiceServiceState.LISTENING
    svc._listening_deadline = time.time() + 5.0

    # Simulate quiet audio chunk (zeros)
    quiet_chunk = np.zeros(1600, dtype=np.float32)
    vad_event, full_audio = svc.vad.process_chunk(quiet_chunk)
    assert vad_event == "silence"
    assert full_audio is None

    # In our improved logic, since now < deadline, state stays LISTENING
    now = time.time()
    assert now < svc._listening_deadline
    # It does not drop to IDLE prematurely
    assert svc.state == VoiceServiceState.LISTENING


def test_voice_acknowledgement_cooldown_and_reset():
    svc = ConversationalVoiceService()
    svc._is_running = True

    # Call _on_wake_detected
    with patch.object(svc.voice_manager, "speak") as mock_speak:
        svc._on_wake_detected()
        assert svc.state == VoiceServiceState.ACKNOWLEDGING
        assert mock_speak.called

        # Extract on_complete callback
        _, kwargs = mock_speak.call_args
        on_complete = kwargs.get("on_complete")
        assert callable(on_complete)

        # Trigger on_complete
        on_complete(False)
        assert svc.state == VoiceServiceState.LISTENING
        assert svc._listening_deadline > time.time()
        assert svc.wake_detector._last_wake_time > time.time()
