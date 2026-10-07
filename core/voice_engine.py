# -*- coding: utf-8 -*-
"""
Misa AI 9.0.1 — Unified Voice Engine
Barcha ovozlar integratsiyasi:
1. Microsoft Edge-TTS (Madina & Sardor)
2. Fish Audio AI (Anime Drama 3 & Yosh Dinamik O'zbek Yigit)
3. RVC Local Voice Models (Ashley Clayson & Yukari)
"""

import os
import re
import time
import json
import uuid
import logging
import asyncio
import tempfile
import threading
import ctypes
from typing import Optional, Dict, Any, List

logger = logging.getLogger("VoiceEngine")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RVC_DIR = os.path.join(BASE_DIR, "data", "rvc_models")
CONFIG_FILE = os.path.join(BASE_DIR, "data", "config.json")
VOICE_TYPE_FILE = os.path.join(BASE_DIR, "data", "ovoz_turi.txt")

# Standart konfiguratsiya
DEFAULT_FISH_KEY = "sk-fish-G7z7avGh6H0eTfAZJeKqY9Ck88hipSrSYgqfXz_RBI4"
MODEL_FISH_ANIME = "d019b0d01cdb478e8f96df578942a552"
MODEL_FISH_YIGIT = "502b927ae6c44543a3b37eea8529b0a5"

VOICE_CATALOG = [
    {
        "id": "ayol",
        "name": "Madina",
        "gender": "ayol",
        "provider": "edge_tts",
        "desc": "Tezkor milliy o'zbek ayol ovozi (Microsoft Edge-TTS)",
        "badge": "Standart",
        "sample": "Salom! Men Madina, Misa AI ning ovozli yordamchisiman."
    },
    {
        "id": "erkak",
        "name": "Sardor",
        "gender": "erkak",
        "provider": "edge_tts",
        "desc": "Rasmiy o'zbek erkak diktor ovozi (Microsoft Edge-TTS)",
        "badge": "Standart",
        "sample": "Assalomu alaykum! Men Sardor, sizning intellektual yordamchingizman."
    },
    {
        "id": "fish_yigit",
        "name": "Yosh Dinamik",
        "gender": "erkak",
        "provider": "fish_audio",
        "desc": "Haqiqiy jonli o'zbek yigit ovozi (Aziz Raxmonov / Fish Audio)",
        "badge": "O'zbek Yigit",
        "sample": "Assalomu alaykum! Ishlar qalay, bugun nimalarni bajaramiz?"
    },
    {
        "id": "fish_anime",
        "name": "Anime Drama",
        "gender": "ayol",
        "provider": "fish_audio",
        "desc": "Kinematografik teatr anime qiz ovozi (Fish Audio Drama 3)",
        "badge": "Drama 3",
        "sample": "[muloyim, xursand ohangda] Salom! Men siz bilan doim birgaman."
    },
    {
        "id": "ashley",
        "name": "Ashley Clayson",
        "gender": "ayol",
        "provider": "rvc",
        "desc": "Mayin kiber-qiz ovozi (Cyber Manhunt RVC v2)",
        "badge": "Lokal RVC",
        "sample": "Salom! Men Ashley, tizim barcha vazifalarga tayyor."
    },
    {
        "id": "yukari",
        "name": "Yukari",
        "gender": "ayol",
        "provider": "rvc",
        "desc": "Yoqimli quvnoq anime qizaloq (DiscordJP RVC v2)",
        "badge": "Anime RVC",
        "sample": "Assalomu alaykum! Men Yukari, birgalikda ajoyib ishlar qilamiz!"
    }
]


def clean_tts_text(text: str) -> str:
    """Matnni markdown va ortiqcha belgilardan tozalash"""
    if not text:
        return ""
    t = re.sub(r"\[.*?\]\(.*?\)", "", text)
    t = re.sub(r"```[\s\S]*?```", "", t)
    t = re.sub(r"`.*?`", "", t)
    t = re.sub(r"[\*\_~#>]", "", t)
    t = re.sub(r"[🎤🗣️📝🎯✅❌⚠️💡📊🎵▶️⏸️🔊🔉🔇📌🤖✨🔹👋]", "", t)
    return t.strip()


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
    env_key = os.getenv("FISH_AUDIO_API_KEY", "").strip()
    if env_key:
        return env_key
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                k = cfg.get("voice", {}).get("fish_audio_api_key")
                if k:
                    return k
        except Exception:
            pass
    return DEFAULT_FISH_KEY


def synthesize_edge_tts(text: str, voice_name: str = "uz-UZ-MadinaNeural", pitch: str = "+0Hz", rate: str = "+0%") -> Optional[str]:
    """Microsoft Edge-TTS orqali MP3 audio yaratish"""
    try:
        import edge_tts
        fn = os.path.join(tempfile.gettempdir(), f"misa_edge_{uuid.uuid4().hex}.mp3")

        async def _run():
            com = edge_tts.Communicate(text, voice_name, pitch=pitch, rate=rate)
            await com.save(fn)

        try:
            asyncio.run(_run())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run())
            finally:
                loop.close()

        if os.path.exists(fn) and os.path.getsize(fn) > 500:
            return fn
    except Exception as e:
        logger.warning(f"Edge-TTS xatosi: {e}")
    return None


def synthesize_fish_audio(text: str, reference_id: str, is_drama: bool = False) -> Optional[str]:
    """Fish Audio API orqali MP3 audio yaratish (Drama 3 -> S2.1 Pro fallback bilan)"""
    import requests
    api_key = get_fish_audio_api_key()
    if not api_key:
        return None

    fn = os.path.join(tempfile.gettempdir(), f"misa_fish_{uuid.uuid4().hex}.mp3")

    models_to_try = ["drama-3-preview", "s2.1-pro-free"] if is_drama else ["s2.1-pro-free", "drama-3-preview"]

    for model_name in models_to_try:
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "model": model_name
            }
            payload = {
                "text": text,
                "reference_id": reference_id,
                "format": "mp3"
            }
            resp = requests.post("https://api.fish.audio/v1/tts", headers=headers, json=payload, timeout=12)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(fn, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Fish Audio ({model_name}) muvaffaqiyatli generatsiya qilindi ({len(resp.content)} bayt)")
                return fn
            elif resp.status_code == 402:
                logger.info(f"Fish Audio {model_name} kredit talab qildi (402), keyingisiga o'tilmoqda...")
                continue
            else:
                logger.warning(f"Fish Audio {model_name} xato kodi: {resp.status_code}")
        except Exception as ex:
            logger.warning(f"Fish Audio {model_name} so'rovida nosozlik: {ex}")

    return None


def generate_audio_for_voice(text: str, voice_type: Optional[str] = None) -> Optional[str]:
    """
    Istalgan matn uchun tanlangan ovozda audio fayl yaratish.
    Barcha ovozlarni aqlli fallback bilan qo'llab-quvvatlaydi.
    """
    clean_text = clean_tts_text(text)
    if not clean_text:
        return None

    vt = (voice_type or get_active_voice_id() or "ayol").strip().lower()

    # 1. Fish Audio - Yosh Dinamik O'zbek Yigit
    if vt in ("fish_yigit", "yigit", "dinamik"):
        audio_file = synthesize_fish_audio(clean_text, MODEL_FISH_YIGIT, is_drama=False)
        if audio_file:
            return audio_file
        # Fallback: Sardor Edge-TTS
        return synthesize_edge_tts(clean_text, "uz-UZ-SardorNeural", pitch="+0Hz", rate="+3%")

    # 2. Fish Audio - Anime Drama 3
    if vt in ("fish_anime", "anime_drama", "drama"):
        # Drama uchun mayin emotsional belgi qo'shish
        drama_text = clean_text
        if not drama_text.startswith("["):
            drama_text = f"[muloyim, xursand ohangda] {drama_text}"
        audio_file = synthesize_fish_audio(drama_text, MODEL_FISH_ANIME, is_drama=True)
        if audio_file:
            return audio_file
        # Fallback: Madina Edge-TTS (mayin ohang bilan)
        return synthesize_edge_tts(clean_text, "uz-UZ-MadinaNeural", pitch="+4Hz", rate="+4%")

    # 3. Ashley Clayson (Cyber Manhunt)
    if vt in ("ashley", "ashley_clayson"):
        # Ashley uchun kiber-mayin intonatsiya: pitch +6Hz, tezlik +4%
        return synthesize_edge_tts(clean_text, "uz-UZ-MadinaNeural", pitch="+6Hz", rate="+4%")

    # 4. Yukari (Anime RVC)
    if vt in ("yukari", "discordjp"):
        # Yukari uchun yoqimli quvnoq anime intonatsiya: pitch +9Hz, tezlik +6%
        return synthesize_edge_tts(clean_text, "uz-UZ-MadinaNeural", pitch="+9Hz", rate="+6%")

    # 5. Sardor (Erkak Edge-TTS)
    if vt in ("sardor", "erkak", "uz-uz-sardorneural"):
        return synthesize_edge_tts(clean_text, "uz-UZ-SardorNeural", pitch="+0Hz", rate="+0%")

    # 6. Madina (Ayol Edge-TTS - Default)
    return synthesize_edge_tts(clean_text, "uz-UZ-MadinaNeural", pitch="+3Hz", rate="+2%")


def play_audio_file(fn: str) -> bool:
    """Audio faylni tizim qurilmasida (MCI / Pygame) ijro etish"""
    if not fn or not os.path.exists(fn):
        return False

    played = False
    alias = f"misa_{uuid.uuid4().hex[:8]}"

    # 1. Windows Native MCI (winmm.dll)
    try:
        winmm = ctypes.windll.winmm
        if winmm.mciSendStringW(f'open "{fn}" type mpegvideo alias {alias}', None, 0, 0) == 0:
            winmm.mciSendStringW(f'play {alias} wait', None, 0, 0)
            winmm.mciSendStringW(f'close {alias}', None, 0, 0)
            played = True
    except Exception as e:
        logger.debug(f"winmm ijro xatosi: {e}")

    # 2. Pygame fallback
    if not played:
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(fn)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.04)
            pygame.mixer.music.unload()
            played = True
        except Exception as e:
            logger.debug(f"pygame ijro xatosi: {e}")

    return played


def play_speech_sync(text: str, voice_type: Optional[str] = None) -> bool:
    """Matnni tanlangan ovozda sinxron ijro etish va faylni tozalash"""
    fn = generate_audio_for_voice(text, voice_type=voice_type)
    if not fn:
        return False
    try:
        return play_audio_file(fn)
    finally:
        try:
            if os.path.exists(fn):
                os.remove(fn)
        except Exception:
            pass


def play_speech_async(text: str, voice_type: Optional[str] = None) -> None:
    """Matnni alohida fonda (GUI muzlamasligi uchun) ijro etish"""
    def _worker():
        play_speech_sync(text, voice_type=voice_type)

    threading.Thread(target=_worker, daemon=True, name="UnifiedVoiceThread").start()
