# -*- coding: utf-8 -*-
"""
Tests for Misa AI v9.0.1 Raw JSON Leak Prevention and Truncated Response Sanitization.
Verifies that responses like `{"type": "answer", "response": "..."}` are always unwrapped cleanly.
"""

import pytest
from core.intelligence.text_cleaner import extract_clean_response_text
from core.intelligence.types import IntelligenceResponse
from core.intelligence.adapter import CompatibilityAdapter
from core.intelligence.orchestrator import IntelligenceOrchestrator
from core.ai_engine import _javob_tahlil


def test_truncated_json_user_case_unwrapped():
    """Screenshotdagi aniq holat: Uzilib qolgan JSON dan toza o'zbekcha javob ajratib olinishi kerak."""
    raw_user_sample = (
        '{"type": "answer", "response": "Bu nomdagi eng mashhur qo\'shiqlar bir nechta, asosiylari:\\n\\n'
        '1. Alec Benjamin - «Let Me Down Slowly» (odatda ko\'pchilik aynan shuni nazarda tutadi): '
        'Qo\'shiqni Alec Benjamin, Michael Pollack'
    )
    clean = extract_clean_response_text(raw_user_sample)
    assert not clean.startswith("{")
    assert '"type"' not in clean
    assert '"response"' not in clean
    assert "Bu nomdagi eng mashhur qo'shiqlar" in clean
    assert "Alec Benjamin" in clean


def test_literal_newline_in_json_parsed():
    """Unescaped yangi qatorli JSON to'g'ri o'qilib toza matn qaytarishi kerak."""
    raw = (
        '{\n'
        '  "type": "answer",\n'
        '  "response": "Birinchi qator\nIkkinchi qator\nUchinchi qator"\n'
        '}'
    )
    clean = extract_clean_response_text(raw)
    assert "Birinchi qator" in clean
    assert "Ikkinchi qator" in clean
    assert "{" not in clean


def test_markdown_and_nested_json_unwrapped():
    """Markdown bloklari yoki ikki qavatli JSON qobig'i tozalanishi kerak."""
    markdown_json = '```json\n{"type": "answer", "response": "Markdown ichidagi javob"}\n```'
    clean_md = extract_clean_response_text(markdown_json)
    assert clean_md == "Markdown ichidagi javob"

    nested = '{"type": "answer", "response": "{\\"type\\": \\"answer\\", \\"response\\": \\"Ichki toza matn\\"}"}'
    clean_nested = extract_clean_response_text(nested)
    assert clean_nested == "Ichki toza matn"


def test_orchestrator_finalize_sanitizes_raw_json():
    """IntelligenceOrchestrator._finalize_response xom JSON ni tozalashi kerak."""
    orch = IntelligenceOrchestrator()
    resp = IntelligenceResponse(
        type="answer",
        content='{"type": "answer", "response": "Toza yakuniy javob"}',
        verified=True
    )
    final = orch._finalize_response(resp, trace=None)
    assert final.content == "Toza yakuniy javob"
    assert "{" not in final.content


def test_compatibility_adapter_unwraps_raw_json():
    """CompatibilityAdapter frontend va legacy formatga o'tkazganda xom JSON qoldirmasligi kerak."""
    resp = IntelligenceResponse(
        type="answer",
        content='{"type": "answer", "response": "Adapter orqali o\'tgan javob"}',
        verified=True
    )
    fe = CompatibilityAdapter.to_frontend_response(resp)
    assert fe["response"] == "Adapter orqali o'tgan javob"
    assert "{" not in fe["response"]

    leg = CompatibilityAdapter.to_legacy_ai_engine_dict(resp)
    assert leg["response"] == "Adapter orqali o'tgan javob"
    assert "{" not in leg["response"]


def test_ai_engine_javob_tahlil_sanitizes():
    """_javob_tahlil uzilib qolgan yoki xom JSON ni xavfsiz tozalashi kerak."""
    raw = '{"type": "answer", "response": "AI Engine javobi'
    parsed = _javob_tahlil(raw)
    assert parsed.get("type") == "answer"
    assert parsed.get("response") == "AI Engine javobi"
    assert "{" not in parsed.get("response")
