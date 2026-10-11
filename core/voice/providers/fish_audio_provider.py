# -*- coding: utf-8 -*-
"""
Misa AI — Fish Audio Cloud Neural Provider
Neyron ovozlar: Yosh Dinamik O'zbek Yigit (s2.1-pro-free) va Anime Drama 3 (drama-3-preview).
Avtomatik Edge-TTS fallback bilan: HTTP 402, timeout yoki API kalit mavjud bo'lmaganda uzluksiz ishlaydi.
"""

import os
import uuid
import tempfile
import logging
from typing import Optional
from .base_provider import BaseVoiceProvider
from .edge_tts_provider import EdgeTTSVoiceProvider
from ..cancellation import CancellationToken

logger = logging.getLogger("FishAudioProvider")


class FishAudioVoiceProvider(BaseVoiceProvider):
    """Fish Audio neyron TTS provayderi va aqlli fallback mexanizmi"""

    def __init__(self, fallback_provider: Optional[BaseVoiceProvider] = None):
        self._fallback = fallback_provider or EdgeTTSVoiceProvider()

    def get_provider_name(self) -> str:
        return "fish_audio"

    def _get_api_key(self) -> str:
        """API kalitni .env yoki muhitdan xavfsiz olish"""
        # 1. Environment variable
        k = os.getenv("FISH_AUDIO_API_KEY", "").strip()
        if k:
            return k
        # 2. .env fayli (loyiha ildizidan)
        try:
            from core.common_paths import PROJECT_ROOT
            env_file = os.path.join(PROJECT_ROOT, ".env")
        except Exception:
            env_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line_s = line.strip()
                        if line_s.startswith("FISH_AUDIO_API_KEY="):
                            val = line_s.split("FISH_AUDIO_API_KEY=", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass
        return ""

    def is_available(self) -> bool:
        """API kalit mavjudmi?"""
        return bool(self._get_api_key())

    def synthesize(
        self,
        text: str,
        voice_id: str,
        pitch: str = "+0Hz",
        rate: str = "+0%",
        cancel_token: Optional[CancellationToken] = None
    ) -> Optional[str]:
        if not text:
            return None

        if cancel_token and cancel_token.is_cancelled:
            return None

        api_key = self._get_api_key()
        if not api_key:
            logger.info("Fish Audio API kaliti yo'q, Edge-TTS fallback ishlatilmoqda")
            return self._fallback.synthesize(text, "uz-UZ-MadinaNeural", pitch=pitch, rate=rate, cancel_token=cancel_token)

        import requests

        fn = os.path.join(tempfile.gettempdir(), f"misa_fish_{uuid.uuid4().hex}.mp3")
        is_drama = "drama" in voice_id.lower() or "anime" in voice_id.lower()
        models_to_try = ["drama-3-preview", "s2.1-pro-free"] if is_drama else ["s2.1-pro-free", "drama-3-preview"]

        for model_name in models_to_try:
            if cancel_token and cancel_token.is_cancelled:
                return None

            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "model": model_name
                }
                payload = {
                    "text": text,
                    "reference_id": voice_id,
                    "format": "mp3"
                }
                resp = requests.post("https://api.fish.audio/v1/tts", headers=headers, json=payload, timeout=12)

                if cancel_token and cancel_token.is_cancelled:
                    return None

                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(fn, "wb") as f:
                        f.write(resp.content)
                    return fn
                elif resp.status_code == 402:
                    logger.warning(f"Fish Audio ({model_name}) kredit tugadi (402). Keyingi model yoki fallbackga o'tilmoqda")
                    continue
                else:
                    logger.warning(f"Fish Audio ({model_name}) xato kodi: {resp.status_code}")
            except Exception as ex:
                logger.warning(f"Fish Audio ({model_name}) ulanish xatosi: {ex}")

        # Agar barcha Fish Audio urinishlari muvaffaqiyatsiz bo'lsa -> Edge-TTS fallback
        logger.info("Fish Audio ulanishida nosozlik, Edge-TTS ga avtomatik o'tilmoqda")
        return self._fallback.synthesize(text, "uz-UZ-MadinaNeural", pitch=pitch, rate=rate, cancel_token=cancel_token)
