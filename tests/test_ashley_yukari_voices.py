import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.voice_engine import generate_audio_for_voice, VOICE_CATALOG


def test_voice_catalog_contains_ashley_and_yukari():
    catalog_ids = [v["id"] for v in VOICE_CATALOG]
    assert "ashley" in catalog_ids
    assert "yukari" in catalog_ids


def test_ashley_voice_generation():
    audio_path = generate_audio_for_voice("Salom! Men Ashley, tizim tayyor.", voice_type="ashley")
    assert audio_path is not None
    assert os.path.exists(audio_path)
    size = os.path.getsize(audio_path)
    assert size > 2000
    try:
        os.remove(audio_path)
    except Exception:
        pass


def test_yukari_voice_generation():
    audio_path = generate_audio_for_voice("Salom! Men Yukari, birgalikda ishlaymiz!", voice_type="yukari")
    assert audio_path is not None
    assert os.path.exists(audio_path)
    size = os.path.getsize(audio_path)
    assert size > 2000
    try:
        os.remove(audio_path)
    except Exception:
        pass
