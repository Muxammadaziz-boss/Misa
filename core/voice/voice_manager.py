# -*- coding: utf-8 -*-
"""
Misa AI — Unified Voice Manager
Yagona markazlashtirilgan ovoz menejeri:
- Provayderlarni (Edge-TTS, Fish Audio, RVC) boshqarish
- Audio navbat (AudioQueue) va zudlik bilan to'xtatish (Barge-in / Interrupt)
- Oqimli TTS (Streaming sentence-by-sentence TTS)
- Frontend MisaAperture bilan real-vaqt sinxronizatsiya
"""

import os
import re
import time
import logging
import threading
from typing import Optional, Callable, Dict, Any, Iterable, List
from .cancellation import CancellationToken
from .audio_player import AudioPlayer
from .audio_queue import AudioQueue
from .voice_registry import get_voice_registry, VoiceRegistry
from .providers.base_provider import BaseVoiceProvider

logger = logging.getLogger("VoiceManager")


class VoiceManager:
    """
    Misa AI ning barcha ovoz tizimlarini birlashtiruvchi markaziy menejeri.
    """

    def __init__(self):
        self.registry: VoiceRegistry = get_voice_registry()
        self.player: AudioPlayer = AudioPlayer()
        self.queue: AudioQueue = AudioQueue(player=self.player)
        self._state_callbacks: List[Callable[[str], None]] = []
        self._lock = threading.Lock()
        self._current_cancel_token: Optional[CancellationToken] = None

        # AudioQueue holat o'zgarishlarini tinglash
        self.queue.set_state_callback(self._on_queue_state_change)

    def register_state_callback(self, cb: Callable[[str], None]) -> None:
        """Holat o'zgarishi tinglovchisini ro'yxatdan o'tkazish (masalan, WebSocket broadcast)"""
        with self._lock:
            if cb not in self._state_callbacks:
                self._state_callbacks.append(cb)

    def _on_queue_state_change(self, state: str) -> None:
        with self._lock:
            cbs = list(self._state_callbacks)
        for cb in cbs:
            try:
                cb(state)
            except Exception as e:
                logger.debug(f"Voice state callback xatosi: {e}")

    @staticmethod
    def clean_text(text: str) -> str:
        """Matnni TTS uchun tozalash"""
        if not text:
            return ""
        t = re.sub(r"\[.*?\]\(.*?\)", "", text)
        t = re.sub(r"```[\s\S]*?```", "", t)
        t = re.sub(r"`.*?`", "", t)
        t = re.sub(r"[\*\_~#>]", "", t)
        t = re.sub(r"[🎤🗣️📝🎯✅❌⚠️💡📊🎵▶️⏸️🔊🔉🔇📌🤖✨🔹👋]", "", t)
        return t.strip()

    def is_speaking(self) -> bool:
        """Hozir ovoz yangrayaptimi yoki navbatda audio bormi?"""
        return self.queue.is_busy()

    def interrupt(self) -> int:
        """
        Barcha audio ijroni bir zumda to'xtatish ("To'xta" / Barge-in).
        Navbatni tozalaydi va audio drayverni o'chiradi.
        """
        with self._lock:
            if self._current_cancel_token:
                self._current_cancel_token.cancel()
        count = self.queue.flush()
        logger.info(f"VoiceManager: Ijro darhol to'xtatildi (Barge-in faollashdi, {count} audio bekor qilindi)")
        return count

    def synthesize_text(
        self,
        text: str,
        voice_id: Optional[str] = None,
        cancel_token: Optional[CancellationToken] = None
    ) -> Optional[str]:
        """Matndan tanlangan ovoz bo'yicha audio fayl yaratish"""
        clean = self.clean_text(text)
        if not clean:
            return None

        vid = (voice_id or "ayol").strip().lower()
        info = self.registry.get_voice_info(vid)
        provider_name = info.get("provider", "edge_tts") if info else "edge_tts"

        # 1. Edge-TTS provayderi
        if provider_name == "edge_tts":
            target_voice = info.get("voice_id", "uz-UZ-MadinaNeural") if info else "uz-UZ-MadinaNeural"
            return self.registry.edge_provider.synthesize(
                clean, target_voice, cancel_token=cancel_token
            )

        # 2. Fish Audio provayderi
        if provider_name == "fish_audio":
            model_target = info.get("voice_id", "d019b0d01cdb478e8f96df578942a552") if info else "d019b0d01cdb478e8f96df578942a552"
            return self.registry.fish_provider.synthesize(
                clean, model_target, cancel_token=cancel_token
            )

        # 3. RVC provayderi
        if provider_name == "rvc":
            rvc_status = self.registry.rvc_provider.get_voice_status(vid)
            if rvc_status.get("runtime_ready"):
                return self.registry.rvc_provider.synthesize(clean, vid, cancel_token=cancel_token)
            else:
                logger.warning(
                    f"RVC modeli '{vid}' nofaol ({rvc_status.get('reason')}). "
                    f"Standart Madina ovoziga o'tilmoqda."
                )
                return self.registry.edge_provider.synthesize(
                    clean, "uz-UZ-MadinaNeural", cancel_token=cancel_token
                )

        # Standart fallback
        return self.registry.edge_provider.synthesize(
            clean, "uz-UZ-MadinaNeural", cancel_token=cancel_token
        )

    # Alias for synthesize_text
    synthesize = synthesize_text

    def speak(
        self,
        text: str,
        voice_id: Optional[str] = None,
        cancel_token: Optional[CancellationToken] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_complete: Optional[Callable[[bool], None]] = None,
    ) -> bool:
        """
        Matnni navbatga qo'yib, tartib bilan ijro etish.
        Parallel bir-birining ustiga tushib ketish holati (overlapping) yuz bermaydi.
        """
        token = cancel_token or CancellationToken()
        with self._lock:
            self._current_cancel_token = token

        audio_file = self.synthesize_text(text, voice_id=voice_id, cancel_token=token)
        if not audio_file:
            return False

        self.queue.enqueue(
            audio_file,
            text=text,
            cancel_token=token,
            on_start=on_start,
            on_complete=on_complete,
            delete_on_finish=True
        )
        return True

    def speak_stream(
        self,
        text_chunks: Iterable[str],
        voice_id: Optional[str] = None,
        cancel_token: Optional[CancellationToken] = None
    ) -> None:
        """
        Oqimli (Streaming) TTS ijrosi:
        LLM dan matn bo'laklari kelishi bilan jumlalarga ajratib,
        birinchi jumla tayyor bo'lishi bilanoq darhol sintezlab navbatga uzatadi.
        Natijada javob eshitilish kechikishi (TTFA) 1 soniyadan pastga tushadi.
        """
        token = cancel_token or CancellationToken()
        with self._lock:
            self._current_cancel_token = token

        buffer = ""
        sentence_delimiters = re.compile(r"([.!?\n]+)")

        def _synthesize_and_queue(sentence: str):
            clean_s = self.clean_text(sentence)
            if len(clean_s) < 2 or token.is_cancelled:
                return
            fn = self.synthesize_text(clean_s, voice_id=voice_id, cancel_token=token)
            if fn and not token.is_cancelled:
                self.queue.enqueue(fn, text=clean_s, cancel_token=token, delete_on_finish=True)

        for chunk in text_chunks:
            if token.is_cancelled:
                break
            buffer += chunk
            parts = sentence_delimiters.split(buffer)
            # Agar kamida bitta to'liq jumla bo'lsa
            while len(parts) >= 3:
                complete_sentence = parts[0] + parts[1]
                buffer = "".join(parts[2:])
                _synthesize_and_queue(complete_sentence)
                parts = sentence_delimiters.split(buffer)

        # Oxirgi qolgan jumla bo'lagini ijro etish
        if buffer.strip() and not token.is_cancelled:
            _synthesize_and_queue(buffer)


# Global VoiceManager nusxasi
_voice_manager_instance: Optional[VoiceManager] = None


def get_voice_manager() -> VoiceManager:
    global _voice_manager_instance
    if _voice_manager_instance is None:
        _voice_manager_instance = VoiceManager()
    return _voice_manager_instance
