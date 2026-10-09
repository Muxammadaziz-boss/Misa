# -*- coding: utf-8 -*-
"""
Misa AI — Microsoft Edge-TTS Provider
O'zbek tilidagi rasmiy milliy ovozlar: Madina (uz-UZ-MadinaNeural) va Sardor (uz-UZ-SardorNeural).
"""

import os
import uuid
import asyncio
import tempfile
import logging
from typing import Optional
from .base_provider import BaseVoiceProvider
from ..cancellation import CancellationToken

logger = logging.getLogger("EdgeTTSProvider")


class EdgeTTSVoiceProvider(BaseVoiceProvider):
    """Microsoft Edge-TTS ovoz provayderi"""

    def __init__(self):
        self._available = False
        try:
            import edge_tts
            self._available = True
        except ImportError:
            logger.warning("edge-tts kutubxonasi topilmadi")

    def get_provider_name(self) -> str:
        return "edge_tts"

    def is_available(self) -> bool:
        return self._available

    def synthesize(
        self,
        text: str,
        voice_id: str = "uz-UZ-MadinaNeural",
        pitch: str = "+0Hz",
        rate: str = "+0%",
        cancel_token: Optional[CancellationToken] = None
    ) -> Optional[str]:
        if not self._available or not text:
            return None

        if cancel_token and cancel_token.is_cancelled:
            return None

        import edge_tts
        fn = os.path.join(tempfile.gettempdir(), f"misa_edge_{uuid.uuid4().hex}.mp3")

        async def _run():
            com = edge_tts.Communicate(text, voice_id, pitch=pitch, rate=rate)
            await com.save(fn)

        try:
            try:
                asyncio.run(_run())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_run())
                finally:
                    loop.close()

            if cancel_token and cancel_token.is_cancelled:
                if os.path.exists(fn):
                    try:
                        os.remove(fn)
                    except Exception:
                        pass
                return None

            if os.path.exists(fn) and os.path.getsize(fn) > 500:
                return fn
        except Exception as e:
            logger.warning(f"Edge-TTS sintezida xato: {e}")
            if os.path.exists(fn):
                try:
                    os.remove(fn)
                except Exception:
                    pass
        return None
