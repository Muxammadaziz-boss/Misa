# -*- coding: utf-8 -*-
"""
Misa AI — Unified Voice Engine Facade
Orqaga moslik (Backward Compatibility) va yuqori darajadagi API interfeysi.
Ichki arxitekturada core.voice.VoiceManager va AudioQueue orqali boshqariladi.
"""

import os
import re
import json
import logging
from typing import Optional, Dict, Any, List

from core.voice import get_voice_manager, get_voice_registry, CancellationToken

logger = logging.getLogger("VoiceEngine")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RVC_DIR = os.path.join(BASE_DIR, "data", "rvc_models")
CONFIG_FILE = os.path.join(BASE_DIR, "data", "config.json")
VOICE_TYPE_FILE = os.path.join(BASE_DIR, "data", "ovoz_turi.txt")

# Standart modellar konstantalari
MODEL_FISH_ANIME = "d019b0d01cdb478e8f96df578942a552"
MODEL_FISH_YIGIT = "502b927ae6c44543a3b37eea8529b0a5"
MODEL_FISH_ASHLEY = "5c071b5e0fde43beb4204509b08b96ca"
MODEL_FISH_YUKARI = "aaa4089bda2f41b8ad69086712f99882"


def get_voice_catalog() -> List[Dict[str, Any]]:
    """Ovozlar katalogini VoiceRegistry orqali olish"""
    return get_voice_registry().get_catalog()


# Orqaga moslik uchun katalog obyekti
VOICE_CATALOG = get_voice_catalog()


def clean_tts_text(text: str) -> str:
    """Matnni tozalash"""
    return get_voice_manager().clean_text(text)


def get_active_voice_id() -> str:
    """Joriy tanlangan ovoz identifikatorini olish"""
    if os.path.exists(VOICE_TYPE_FILE):
        try:
            with open(VOICE_TYPE_FILE, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    return v
        except Exception:
            pass

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                v = cfg.get("user", {}).get("voice_type")
                if v:
                    return v
        except Exception:
            pass

    return "ayol"


def get_fish_audio_api_key() -> str:
    """Fish Audio API kalitini olish"""
    return get_voice_registry().fish_provider._get_api_key()


def synthesize_edge_tts(
    text: str,
    voice_name: str = "uz-UZ-MadinaNeural",
    pitch: str = "+0Hz",
    rate: str = "+0%"
) -> Optional[str]:
    """Edge-TTS sintezi"""
    return get_voice_registry().edge_provider.synthesize(text, voice_name, pitch=pitch, rate=rate)


def synthesize_fish_audio(
    text: str,
    reference_id: str,
    is_drama: bool = False
) -> Optional[str]:
    """Fish Audio sintezi"""
    return get_voice_registry().fish_provider.synthesize(text, reference_id)


def generate_audio_for_voice(text: str, voice_type: Optional[str] = None) -> Optional[str]:
    """Tanlangan ovozda audio fayl generatsiya qilish"""
    vt = voice_type or get_active_voice_id() or "ayol"
    return get_voice_manager().synthesize_text(text, voice_id=vt)


def play_audio_file(fn: str, cancel_token: Optional[CancellationToken] = None) -> bool:
    """Audio faylni to'xtatiluvchi drayver orqali ijro etish"""
    return get_voice_manager().player.play_file(fn, cancel_token=cancel_token, delete_on_finish=False)


def play_speech_sync(text: str, voice_type: Optional[str] = None) -> bool:
    """Sinxron tarzda audio ijro etish"""
    vt = voice_type or get_active_voice_id() or "ayol"
    fn = generate_audio_for_voice(text, voice_type=vt)
    if not fn:
        return False
    return get_voice_manager().player.play_file(fn, delete_on_finish=True)


def play_speech_async(text: str, voice_type: Optional[str] = None) -> None:
    """
    Ovozni markaziy AudioQueue orqali ijro etish.
    Bir vaqtda bir nechta ovoz baravar yangrab ketishining oldini oladi.
    """
    vt = voice_type or get_active_voice_id() or "ayol"
    get_voice_manager().speak(text, voice_id=vt)


def interrupt_speech() -> int:
    """Barcha ovoz ijrosini darhol to'xtatish ("To'xta" komandasi)"""
    return get_voice_manager().interrupt()
