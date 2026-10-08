# -*- coding: utf-8 -*-
"""
Misa AI — Streaming Adaptive VAD (Voice Activity Detection)
Dinamik shovqin moslashuvi va pre-roll xotirasi bilan jihozlangan nutq faolligi detektori.
Nutqning birinchi bo'g'inini qirqib tashlamaslik uchun 250ms pre-roll buferidan foydalanadi.
"""

import time
import logging
from typing import Optional, Tuple, List
import numpy as np

logger = logging.getLogger("StreamingVAD")


class StreamingVAD:
    """
    Uzluksiz audio oqimida nutq boshlanishi va yakunlanishini aniqlash.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_timeout: float = 1.1,
        min_speech_duration: float = 0.35,
        max_duration: float = 12.0
    ):
        self.sample_rate = sample_rate
        self.silence_timeout = silence_timeout
        self.min_speech_duration = min_speech_duration
        self.max_duration = max_duration

        # Pre-roll buferi (250ms = 4000 namunalar)
        self.preroll_samples = int(self.sample_rate * 0.25)
        self._preroll_buffer = np.zeros(self.preroll_samples, dtype=np.float32)

        # Holat o'zgaruvchilari
        self._is_speaking = False
        self._speech_frames: List[np.ndarray] = []
        self._speech_start_time = 0.0
        self._silence_start_time = None
        self._ambient_rms = 0.006

    def reset(self) -> None:
        """Detektorni dastlabki holatga qaytarish"""
        self._is_speaking = False
        self._speech_frames.clear()
        self._speech_start_time = 0.0
        self._silence_start_time = None
        self._preroll_buffer.fill(0.0)

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def get_speech_threshold(self) -> float:
        """Dinamik sezuvchanlik chegarasi"""
        return max(0.012, self._ambient_rms * 2.3 + 0.003)

    def process_chunk(self, chunk: np.ndarray) -> Tuple[str, Optional[np.ndarray]]:
        """
        Audio bo'lagini (odatda 50-100ms) tahlil qilish.
        Qaytaradi: (hodisa_turi, to'liq_audio_agar_tugagan_bo'lsa)
        Hodisa turlari: 'silence', 'speech_start', 'speaking', 'speech_end'
        """
        if chunk is None or len(chunk) == 0:
            return "silence", None

        flat_chunk = chunk.flatten().astype(np.float32)
        rms = float(np.sqrt(np.mean(flat_chunk**2)))
        now = time.time()
        threshold = self.get_speech_threshold()

        # 1. Agar nutq hali boshlanmagan bo'lsa
        if not self._is_speaking:
            # Pre-roll buferini yangilash
            chunk_len = len(flat_chunk)
            if chunk_len >= self.preroll_samples:
                self._preroll_buffer = flat_chunk[-self.preroll_samples:]
            else:
                self._preroll_buffer[:-chunk_len] = self._preroll_buffer[chunk_len:]
                self._preroll_buffer[-chunk_len:] = flat_chunk

            # Jimlik davom etayotganda fon shovqinini asta yangilash
            if rms < threshold:
                self._ambient_rms = 0.96 * self._ambient_rms + 0.04 * max(0.002, rms)
                return "silence", None

            # Nutq boshlandi!
            if rms >= threshold:
                self._is_speaking = True
                self._speech_start_time = now
                self._silence_start_time = None
                # Pre-roll buferini birinchi bo'lak sifatida qo'shish
                self._speech_frames = [self._preroll_buffer.copy(), flat_chunk]
                logger.debug(f"VAD: Nutq boshlandi (RMS: {rms:.4f} >= {threshold:.4f})")
                return "speech_start", None

        # 2. Nutq davom etayotgan bo'lsa
        self._speech_frames.append(flat_chunk)
        total_duration = now - self._speech_start_time

        # Maksimal vaqt chegarasi tekshiruvi
        if total_duration >= self.max_duration:
            logger.info(f"VAD: Maksimal vaqt yetib keldi ({total_duration:.1f}s)")
            audio_out = np.concatenate(self._speech_frames, axis=0)
            self.reset()
            return "speech_end", audio_out

        # Ovoz kuchi tahlili
        if rms >= threshold * 0.7:  # Hali ham gapiryapti
            self._silence_start_time = None
            return "speaking", None
        else:
            # Ovoz pasaydi (jimlik boshlandi)
            if self._silence_start_time is None:
                self._silence_start_time = now
                return "speaking", None
            elif now - self._silence_start_time >= self.silence_timeout:
                # Nutq yakunlandi!
                speech_len = now - self._speech_start_time
                if speech_len >= self.min_speech_duration:
                    logger.info(f"VAD: Nutq yakunlandi ({speech_len:.2f} soniya)")
                    audio_out = np.concatenate(self._speech_frames, axis=0)
                    self.reset()
                    return "speech_end", audio_out
                else:
                    # Shovqin deb baholandi
                    logger.debug("VAD: Juda qisqa tovush, bekor qilindi")
                    self.reset()
                    return "silence", None

        return "speaking", None
