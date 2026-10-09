# -*- coding: utf-8 -*-
"""
Misa AI — Local Acoustic Wake-Word Engine ("Misa")
100% lokal, maxfiy va tezkor (<200ms) kalit so'zni aniqlash vositasi.
Tashqi serverlarga audio yubormaydi (Zero Cloud Leaks).
Faqat "Misa" eshitilgandagina uyg'onadi va mikrofonni STT ga ulaydi.
"""

import os
import time
import logging
import threading
from typing import Optional, Callable, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger("WakeWordEngine")


class WakeWordDetector:
    """
    Mahalliy "Misa" (yoki "Hey Misa") kalit so'zini aniqlash mexanizmi.
    16kHz mono audio signali ustida spektral va fonetik bosqichli tahlil o'tkazadi:
    [m] (burun murmuri) -> [i] (yuqori formant) -> [s] (jarohatlovchi frikativ) -> [a] (ochiq unli).
    100% lokal, maxfiy va tezkor (<200ms).
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        sensitivity: float = 0.65,
        on_wake_detected: Optional[Callable[[], None]] = None
    ):
        self.sample_rate = sample_rate
        self.sensitivity = max(0.2, min(0.95, sensitivity))
        self.on_wake_detected = on_wake_detected

        self.buffer_duration = 1.2  # soniya
        self.buffer_size = int(self.sample_rate * self.buffer_duration)
        self._audio_buffer = np.zeros(self.buffer_size, dtype=np.float32)

        self._lock = threading.Lock()
        self._last_wake_time = 0.0
        self._cooldown_seconds = 1.8  # Qayta uyg'onishdan saqlanish
        self._ambient_noise_level = 0.002
        self.last_wake_score = 0.0
        self.last_threshold = 0.82 - (self.sensitivity * 0.40)

        # FFT chastota zonalari (hardware-calibrated for real mics and webcams)
        self.fft_size = 512
        freqs = np.fft.rfftfreq(self.fft_size, 1.0 / self.sample_rate)
        self.low_mask = (freqs >= 150) & (freqs <= 800)     # /m/ va /a/ pastki formantlar
        self.mid_mask = (freqs >= 1400) & (freqs <= 2800)   # /i/ va /a/ o'rta formantlar
        self.high_mask = (freqs >= 2800) & (freqs <= 7500)  # /s/ frikativ sibilans

        # Diagnostika rejimi
        self.diagnostic_mode = os.environ.get("VOICE_DIAGNOSTIC", "").strip().lower() in ("1", "true", "yes")
        self._last_diag_log = 0.0

    def reset(self) -> None:
        """Buferni tozalash"""
        with self._lock:
            self._audio_buffer.fill(0.0)

    def update_ambient_noise(self, rms: float) -> None:
        """
        Atrofdagi fon shovqin darajasini moslashtirish.
        Muhim: Nutq paytida yoki yuqori tovushlarda fon shovqini darajasini
        sun'iy oshirib yubormaslik uchun faqat past rms (<0.012) da yangilanadi.
        """
        if rms < 0.012:
            self._ambient_noise_level = 0.98 * self._ambient_noise_level + 0.02 * max(0.0005, rms)

    def process_frame(self, chunk: np.ndarray) -> bool:
        """
        Audio bo'lagini (50-100ms) buferga qo'shish va 'Misa' kalit so'zini qidirish.
        Qaytaradi: True agar 'Misa' aniqlansa, False aks holda.
        """
        if chunk is None or len(chunk) == 0:
            return False

        chunk_arr = np.asarray(chunk, dtype=np.float32)
        if chunk_arr.ndim > 1:
            chunk_arr = chunk_arr.mean(axis=1)
        chunk_flat = chunk_arr.flatten()

        shift = len(chunk_flat)
        now = time.time()

        with self._lock:
            # Siklik buferni siljitish
            if shift >= self.buffer_size:
                self._audio_buffer = chunk_flat[-self.buffer_size:]
            else:
                self._audio_buffer[:-shift] = self._audio_buffer[shift:]
                self._audio_buffer[-shift:] = chunk_flat

            buf_copy = self._audio_buffer.copy()

        # Kalit so'z akustik tahlili
        is_detected, score, thresh = self._analyze_misa_acoustics(buf_copy)
        self.last_wake_score = score
        self.last_threshold = thresh

        # Diagnostik loglar (throttled: sekundiga 1 marta yoki nutq mavjud bo'lganda)
        chunk_rms = float(np.sqrt(np.mean(chunk_flat**2)))
        chunk_max = float(np.max(np.abs(chunk_flat))) if len(chunk_flat) > 0 else 0.0

        if (self.diagnostic_mode or logger.isEnabledFor(logging.DEBUG)) and (now - self._last_diag_log >= 1.2):
            if chunk_rms >= 0.003 or score > 0.15:
                logger.info(
                    f"[VOICE] microphone frame received (rms={chunk_rms:.4f}, max={chunk_max:.4f}) | "
                    f"wake detector processing frame | wake score = {score:.2f} (threshold: {thresh:.2f})"
                )
                self._last_diag_log = now

        # Cooldown tekshiruvi
        if now - self._last_wake_time < self._cooldown_seconds:
            return False

        if is_detected:
            self._last_wake_time = now
            logger.info(f"[VOICE] MISA DETECTED (score = {score:.2f} >= threshold = {thresh:.2f})")
            if self.on_wake_detected:
                logger.info("[VOICE] wake callback fired")
                try:
                    self.on_wake_detected()
                except Exception as cb_err:
                    logger.error(f"[VOICE] Wake callback ijro xatosi: {cb_err}")
            return True

        return False

    def _analyze_misa_acoustics(self, audio: np.ndarray) -> Tuple[bool, float, float]:
        """
        'Misa' fonetik belgilarini real mikrofon signali ustida tahlil qilish:
        1. /m/ (Burun murmuri, 150-500Hz)
        2. /i/ (Yuqori unli, F1 ~300Hz, F2 ~2200-2600Hz)
        3. /s/ (Frikativ sibilans, 2800-7500Hz va yuqori ZCR)
        4. /a/ (Ochiq unli, F1 ~650-850Hz, F2 ~1200Hz)
        """
        thresh = 0.82 - (self.sensitivity * 0.40)
        rms_total = float(np.sqrt(np.mean(audio**2)))
        if rms_total < self._ambient_noise_level * 1.1 or rms_total < 0.002:
            return False, 0.0, thresh

        # 60ms li tahlil darchalari
        frame_len = int(self.sample_rate * 0.06)
        num_frames = len(audio) // frame_len
        if num_frames < 4:
            return False, 0.0, thresh

        frames = [audio[i * frame_len : (i + 1) * frame_len] for i in range(num_frames)]
        zcrs = []
        high_energies = []
        mid_energies = []
        low_energies = []
        frame_rms = []

        for f in frames:
            r = float(np.sqrt(np.mean(f**2)))
            frame_rms.append(r)
            z = float(np.mean(np.abs(np.diff(np.sign(f)))) / 2.0)
            zcrs.append(z)

            spec = np.abs(np.fft.rfft(f, n=self.fft_size))
            tot = np.sum(spec) + 1e-9
            low_energies.append(float(np.sum(spec[self.low_mask]) / tot))
            mid_energies.append(float(np.sum(spec[self.mid_mask]) / tot))
            high_energies.append(float(np.sum(spec[self.high_mask]) / tot))

        max_r = max(frame_rms) if frame_rms else 0.0
        speech_thresh = max(0.002, max_r * 0.15)

        # /s/ frikativ nomzodlarini aniqlash (jarohatlovchi shivirlash)
        s_candidates = [
            i for i in range(1, num_frames - 1)
            if frame_rms[i] >= speech_thresh and (
                (zcrs[i] >= 0.15 and high_energies[i] >= 0.14) or
                (high_energies[i] >= 0.25)
            )
        ]

        if not s_candidates:
            return False, 0.0, thresh

        best_score = 0.0
        for s_idx in s_candidates:
            # 1. /s/ dan oldingi 1-5 freymda /m-i/ fonemasi mavjudligi
            pre_scores = []
            for p in range(max(0, s_idx - 5), s_idx):
                if frame_rms[p] >= speech_thresh and zcrs[p] < 0.16:
                    val = max(low_energies[p] / 0.35, mid_energies[p] / 0.25)
                    pre_scores.append(min(1.0, val))
            if not pre_scores:
                continue
            m_score = max(pre_scores)

            # 2. /s/ dan keyingi 1-5 freymda /a/ unlisi mavjudligi
            post_scores = []
            for p in range(s_idx + 1, min(num_frames, s_idx + 6)):
                if frame_rms[p] >= speech_thresh and zcrs[p] < 0.18:
                    val = (low_energies[p] + mid_energies[p]) / 0.45
                    post_scores.append(min(1.0, val))
            if not post_scores:
                continue
            a_score = max(post_scores)

            # 3. /s/ sifat ko'rsatkichi
            s_score = min(1.0, (zcrs[s_idx] / 0.30) * 0.5 + (high_energies[s_idx] / 0.28) * 0.5)

            # Umumiy fonetik ketma-ketlik bali
            cand_score = 0.35 * m_score + 0.35 * s_score + 0.30 * a_score
            if cand_score > best_score:
                best_score = cand_score

        is_detected = (best_score >= thresh)
        return is_detected, best_score, thresh
