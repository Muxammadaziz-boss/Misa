# -*- coding: utf-8 -*-
"""
Misa AI — Full-Duplex Barge-in & Interruption Detector
Misa gapirayotgan vaqtda mikrofonni ochiq saqlab, foydalanuvchining "To'xta" yoki "Stop"
buyruqlarini darhol aniqlab, audio ijroni bir zumda (<100ms) to'xtatuvchi modul.
"""

import re
import time
import logging
from typing import Optional, Callable, Set
import numpy as np

logger = logging.getLogger("BargeInDetector")

DEFAULT_STOP_KEYWORDS: Set[str] = {
    "to'xta", "toxta", "toxtat", "to'xtat", "to'xtang", "toxtang", "to'xtagin", "toxtagin",
    "stop", "jim", "bas", "yetar",
    "bo'ldi", "boldi", "qisqartir", "kut", "og'zingni yop", "jim bo'l", "jim bol"
}


class BargeInDetector:
    """
    Ijro davomida ovozli to'xtatish komandalarini kuzatuvchi detektor.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        stop_keywords: Optional[Set[str]] = None,
        on_interrupted: Optional[Callable[[], None]] = None
    ):
        self.sample_rate = sample_rate
        self.stop_keywords = stop_keywords or DEFAULT_STOP_KEYWORDS
        self.on_interrupted = on_interrupted

        self._recent_frames = []
        self._speech_in_progress = False
        self._start_time = 0.0

    def reset(self) -> None:
        self._recent_frames.clear()
        self._speech_in_progress = False

    def is_stop_command(self, text: str) -> bool:
        """Matn to'xtatish komandasi ekanligini tekshirish"""
        if not text:
            return False
        clean = re.sub(r"[^\w\s']", " ", text.lower()).strip()
        words = clean.split()
        if any(w in self.stop_keywords for w in words):
            return True
        for kw in self.stop_keywords:
            if kw in clean:
                return True
        return False

    def check_audio_interruption(self, chunk: np.ndarray, threshold: float = 0.045) -> bool:
        """
        Ijro paytida kuchli ovoz bosimi (foydalanuvchi baqirishi yoki gapirishi) paydo bo'lganini tekshirish.
        Karnay aks-sadosidan balandroq bo'lgan inson nutqi chegarasi (0.045 RMS).
        """
        if chunk is None or len(chunk) == 0:
            return False

        rms = float(np.sqrt(np.mean(chunk.astype(np.float32)**2)))
        return rms >= threshold

    def trigger_interruption(self) -> None:
        """To'xtatish hodisasini ishga tushirish"""
        logger.info("BargeIn: 'To'xta' komandasi qabul qilindi, ijro uzilmoqda")
        if self.on_interrupted:
            try:
                self.on_interrupted()
            except Exception as e:
                logger.debug(f"Interruption callback xatosi: {e}")
