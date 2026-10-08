# -*- coding: utf-8 -*-
"""
Misa AI — Local Acoustic Wake-Word Engine ("Misa")
100% lokal, maxfiy va tezkor (<200ms) kalit so'zni aniqlash vositasi.
Tashqi serverlarga audio yubormaydi (Zero Cloud Leaks).
Faqat "Misa" eshitilgandagina uyg'onadi va mikrofonni STT ga ulaydi.
"""

import time
import logging
import threading
from typing import Optional, Callable, Dict, Any
import numpy as np

logger = logging.getLogger("WakeWordEngine")


class WakeWordDetector:
    """
    Mahalliy "Misa" (yoki "Hey Misa") kalit so'zini aniqlash mexanizmi.
    16kHz mono audio signali ustida spektral va fonetik bosqichli tahlil o'tkazadi.
    """

    def __init__(self, sample_rate: int = 16000, sensitivity: float = 0.65):
        self.sample_rate = sample_rate
        self.sensitivity = max(0.2, min(0.95, sensitivity))
        self.buffer_duration = 1.2  # soniya
        self.buffer_size = int(self.sample_rate * self.buffer_duration)
        self._audio_buffer = np.zeros(self.buffer_size, dtype=np.float32)

        self._lock = threading.Lock()
        self._last_wake_time = 0.0
        self._cooldown_seconds = 1.8  # Qayta uyg'onishdan saqlanish
        self._ambient_noise_level = 0.008

    def reset(self) -> None:
        """Buferni tozalash"""
        with self._lock:
            self._audio_buffer.fill(0.0)

    def update_ambient_noise(self, rms: float) -> None:
        """Atrofdagi fon shovqin darajasini moslashtirish"""
        self._ambient_noise_level = 0.95 * self._ambient_noise_level + 0.05 * max(0.002, rms)

    def process_frame(self, chunk: np.ndarray) -> bool:
        """
        Audio bo'lagini (odatda 50-100ms) buferga qo'shish va "Misa" kalit so'zini qidirish.
        Qaytaradi: True agar "Misa" aniqlansa, False aks holda.
        """
        if chunk is None or len(chunk) == 0:
            return False

        chunk_flat = chunk.flatten().astype(np.float32)

        with self._lock:
            # Siklik buferni siljitish
            shift = len(chunk_flat)
            if shift >= self.buffer_size:
                self._audio_buffer = chunk_flat[-self.buffer_size:]
            else:
                self._audio_buffer[:-shift] = self._audio_buffer[shift:]
                self._audio_buffer[-shift:] = chunk_flat

            now = time.time()
            if now - self._last_wake_time < self._cooldown_seconds:
                return False

            buf_copy = self._audio_buffer.copy()

        # Kalit so'z akustik tahlili
        is_detected, confidence = self._analyze_misa_acoustics(buf_copy)

        if is_detected and confidence >= (1.0 - self.sensitivity * 0.5):
            self._last_wake_time = now
            logger.info(f"WakeWord: 'Misa' lokal aniqlandi! (Ishonchlilik: {confidence:.2f})")
            return True

        return False

    def _analyze_misa_acoustics(self, audio: np.ndarray) -> (bool, float):
        """
        'Misa' fonetik belgilarini tahlil qilish:
        1. /m/ (Burun undoshi, 200-400Hz energiya)
        2. /i/ (Yuqori unli, F1 ~300Hz, F2 ~2200-2600Hz)
        3. /s/ (Jarohatlovchi shivirlash, frikativ, 4000-7500Hz va yuqori ZCR)
        4. /a/ (Ochiq unli, F1 ~700-850Hz, F2 ~1300Hz)
        """
        rms_total = float(np.sqrt(np.mean(audio**2)))
        if rms_total < self._ambient_noise_level * 1.5:
            return False, 0.0

        # Bo'laklarga ajratish (har biri 80ms)
        frame_len = int(self.sample_rate * 0.08)
        num_frames = len(audio) // frame_len
        if num_frames < 4:
            return False, 0.0

        frames = [audio[i * frame_len:(i + 1) * frame_len] for i in range(num_frames)]
        zcrs = []
        high_freq_energies = []
        mid_freq_energies = []
        low_freq_energies = []

        fft_size = 512
        freqs = np.fft.rfftfreq(fft_size, 1.0 / self.sample_rate)

        low_mask = (freqs >= 200) & (freqs <= 700)
        mid_mask = (freqs >= 1500) & (freqs <= 2800)
        high_mask = (freqs >= 4000) & (freqs <= 7500)

        for f in frames:
            # Zero-crossing rate
            zcr = float(np.mean(np.abs(np.diff(np.sign(f)))) / 2.0)
            zcrs.append(zcr)

            # FFT spektr quvvati
            spec = np.abs(np.fft.rfft(f, n=fft_size))
            total_power = np.sum(spec) + 1e-9

            low_e = np.sum(spec[low_mask]) / total_power
            mid_e = np.sum(spec[mid_mask]) / total_power
            high_e = np.sum(spec[high_mask]) / total_power

            low_freq_energies.append(low_e)
            mid_freq_energies.append(mid_e)
            high_freq_energies.append(high_e)

        # /s/ tovushining cho'qqisini qidirish (yuqori ZCR va yuqori chastota)
        s_candidates = [i for i, z in enumerate(zcrs) if z > 0.22 and high_freq_energies[i] > 0.20]
        if not s_candidates:
            return False, 0.0

        best_s_idx = max(s_candidates, key=lambda idx: zcrs[idx] * high_freq_energies[idx])

        # /s/ dan oldin /mi/ bo'lishi kerak (kamida 1-2 freym oldin)
        if best_s_idx < 1:
            return False, 0.0

        pre_s_frames = range(max(0, best_s_idx - 4), best_s_idx)
        has_mi_vowel = any(
            (mid_freq_energies[idx] > 0.18 or low_freq_energies[idx] > 0.25)
            for idx in pre_s_frames
        )

        # /s/ dan keyin /a/ unlisi bo'lishi kerak (1-3 freym keyin)
        if best_s_idx >= num_frames - 1:
            return False, 0.0

        post_s_frames = range(best_s_idx + 1, min(num_frames, best_s_idx + 4))
        has_a_vowel = any(
            (low_freq_energies[idx] > 0.28 and zcrs[idx] < 0.16)
            for idx in post_s_frames
        )

        # Ishonchlilik hisobi
        if has_mi_vowel and has_a_vowel:
            confidence = min(0.98, 0.50 + zcrs[best_s_idx] * 0.8 + high_freq_energies[best_s_idx] * 0.5)
            return True, confidence

        return False, 0.0
