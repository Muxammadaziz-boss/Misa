# -*- coding: utf-8 -*-
"""
tests/test_v9_wake_word_acoustic_evaluation.py
Misa AI v9.0 — Haqiqiy akustik va fonetik baholash sinov to'plami.

Ushbu testlar oddiy mock bilan cheklanmaydi:
1. Sintetik 16kHz PCM audio orqali "Misa" fonetik ketma-ketligi (/m-i/ -> /s/ -> /a/) tekshiriladi.
2. O'xshash chalg'ituvchi so'zlar ("maysa", "salom mirza", "kassa", "barchaga") ning noto'g'ri faollashmasligi (False Positive Rejection) baholanadi.
3. Atrof-muhit shovqinlari (Gaussian white noise, 50Hz tarmoq g'uvillashi, toza sinusoidlar) sinovdan o'tkaziladi.
4. Tasodifiy shovqin-suron, click/pop impulslari va jimlikda faollashmaslik kafolatlanadi.
5. Maxfiylik auditi: Wake-word aniqlash siklida bitta ham tarmoq so'rovi (socket connect) amalga oshirilmasligi tekshiriladi.
6. Model haqiqiyligi: O'qitilgan ONNX modeli yo'qligida "heuristic_spectral_analyzer" deb to'g'ri ko'rsatilishi tasdiqlanadi.
"""

import math
import socket
import pytest
import numpy as np
from unittest.mock import patch

from core.voice.wake_word import (
    AcousticWakeWordDetector,
    WakeWordDetector,
    OpenWakeWordEngine,
)


def generate_tone(freq: float, duration_sec: float, sample_rate: int = 16000, amplitude: float = 0.3) -> np.ndarray:
    """Berilgan chastota va davomiylikdagi garmonik sinusoid signal yaratish"""
    n_samples = int(sample_rate * duration_sec)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def generate_fricative_noise(duration_sec: float, sample_rate: int = 16000, amplitude: float = 0.3, seed: int = 42) -> np.ndarray:
    """Yuqori chastotali frikativ sibilans (/s/ tovushi) signali: 3500Hz - 7000Hz shovqin"""
    n_samples = int(sample_rate * duration_sec)
    rng = np.random.RandomState(seed)
    noise = rng.uniform(-1.0, 1.0, n_samples).astype(np.float32)
    t = np.linspace(0, duration_sec, n_samples, endpoint=False)
    carrier = np.sin(2 * np.pi * 5000 * t).astype(np.float32)
    s_signal = noise * carrier * amplitude
    return s_signal


def generate_synthetic_misa_utterance(sample_rate: int = 16000) -> np.ndarray:
    """
    'Misa' so'zining tabiiy fonetik tuzilishiga mos sintetik 16kHz PCM audio:
    - 0.0 - 0.2s: Jimlik/fon
    - 0.2 - 0.45s: /m-i/ (pastki/o'rta formantlar: ~300Hz va ~2200Hz)
    - 0.45 - 0.65s: /s/ (yuqori chastotali frikativ: 4000-6500Hz)
    - 0.65 - 0.90s: /a/ (ochiq unli: ~750Hz va ~1200Hz)
    - 0.90 - 1.20s: Jimlik
    Jami davomiylik: 1.2 soniya (AcousticWakeWordDetector bufer hajmiga teng)
    """
    total_samples = int(sample_rate * 1.2)
    audio = np.zeros(total_samples, dtype=np.float32)

    # 1. /m-i/ qismi (0.2s - 0.45s, 0.25s davomiylik)
    start_mi = int(sample_rate * 0.20)
    dur_mi = 0.25
    t_mi = np.linspace(0, dur_mi, int(sample_rate * dur_mi), endpoint=False)
    mi_sig = (0.25 * np.sin(2 * np.pi * 300 * t_mi) + 0.20 * np.sin(2 * np.pi * 2200 * t_mi)).astype(np.float32)
    audio[start_mi : start_mi + len(mi_sig)] = mi_sig

    # 2. /s/ qismi (0.45s - 0.65s, 0.20s davomiylik)
    start_s = start_mi + len(mi_sig)
    dur_s = 0.20
    s_sig = generate_fricative_noise(dur_s, sample_rate, amplitude=0.35)
    audio[start_s : start_s + len(s_sig)] = s_sig

    # 3. /a/ qismi (0.65s - 0.90s, 0.25s davomiylik)
    start_a = start_s + len(s_sig)
    dur_a = 0.25
    t_a = np.linspace(0, dur_a, int(sample_rate * dur_a), endpoint=False)
    a_sig = (0.28 * np.sin(2 * np.pi * 750 * t_a) + 0.18 * np.sin(2 * np.pi * 1250 * t_a)).astype(np.float32)
    audio[start_a : start_a + len(a_sig)] = a_sig

    return audio


class TestWakeWordAcousticPhonetics:
    """Haqiqiy PCM audio bilan fonetik va spektral tahlil sinovlari"""

    def test_positive_misa_phonetic_progression(self):
        """To'g'ri 'Misa' fonetik ketma-ketligi (/m-i/ -> /s/ -> /a/) tahlildan ijobiy o'tishi"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.80)
        audio = generate_synthetic_misa_utterance(sample_rate=16000)

        # 100ms li bo'laklar bilan yuboramiz (real sounddevice oqimi kabi)
        chunk_size = 1600
        detected = False
        max_score = 0.0

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]
            det, score, thresh = detector.analyze_audio(chunk)
            if det:
                detected = True
            if score > max_score:
                max_score = score

        assert max_score >= 0.50, f"Misa akustik balli juda past bo'ldi: {max_score}"
        assert detected is True or max_score >= detector.last_threshold

    def test_rejection_of_reversed_confusable_salom_mirza(self):
        """'Salom Mirza': /s/ boshida keladi, /m/ esa keyin keladi -> Misa ketma-ketligi mos kelmaydi"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.65)
        total_samples = int(16000 * 1.2)
        audio = np.zeros(total_samples, dtype=np.float32)

        # /s/ dastlab keladi (Salom)
        start_s = int(16000 * 0.2)
        s_sig = generate_fricative_noise(0.20, 16000, amplitude=0.35)
        audio[start_s : start_s + len(s_sig)] = s_sig

        # Keyin /m-i-r/ keladi
        start_m = start_s + len(s_sig) + 800
        t_m = np.linspace(0, 0.3, int(16000 * 0.3), endpoint=False)
        m_sig = (0.3 * np.sin(2 * np.pi * 350 * t_m)).astype(np.float32)
        audio[start_m : start_m + len(m_sig)] = m_sig

        chunk_size = 1600
        detected = False
        for i in range(0, len(audio), chunk_size):
            det, _, _ = detector.analyze_audio(audio[i : i + chunk_size])
            if det:
                detected = True

        assert detected is False, "'Salom Mirza' teskari fonetikasi xatolik bilan uyg'onmasligi kerak!"

    def test_rejection_of_confusable_kassa(self):
        """'Kassa': Faqat /s/ va /a/ bor, lekin oldinda /m-i/ burun murmuri yo'q"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.65)
        total_samples = int(16000 * 1.2)
        audio = np.zeros(total_samples, dtype=np.float32)

        # /s/ tovushi
        start_s = int(16000 * 0.4)
        s_sig = generate_fricative_noise(0.25, 16000, amplitude=0.40)
        audio[start_s : start_s + len(s_sig)] = s_sig

        # /a/ unlisi
        start_a = start_s + len(s_sig)
        t_a = np.linspace(0, 0.25, int(16000 * 0.25), endpoint=False)
        a_sig = (0.35 * np.sin(2 * np.pi * 750 * t_a)).astype(np.float32)
        audio[start_a : start_a + len(a_sig)] = a_sig

        chunk_size = 1600
        detected = False
        for i in range(0, len(audio), chunk_size):
            det, _, _ = detector.analyze_audio(audio[i : i + chunk_size])
            if det:
                detected = True

        assert detected is False, "'Kassa' so'zi burun murmurisiz uyg'onmasligi shart!"

    def test_rejection_of_pure_vowel_barchaga(self):
        """'Barchaga': Faqat pastki va o'rta chastotalar, /s/ frikativ sibilansi yo'q"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.70)
        t = np.linspace(0, 1.2, int(16000 * 1.2), endpoint=False)
        audio = (0.3 * np.sin(2 * np.pi * 400 * t) + 0.2 * np.sin(2 * np.pi * 800 * t)).astype(np.float32)

        chunk_size = 1600
        detected = False
        for i in range(0, len(audio), chunk_size):
            det, score, _ = detector.analyze_audio(audio[i : i + chunk_size])
            if det:
                detected = True

        assert detected is False, "'Barchaga' (frikativsiz) uyg'onmasligi shart!"


class TestEnvironmentalNoiseAndArtifacts:
    """Turli xil shovqin va anomal signallarni rad etish sinovlari"""

    def test_rejection_of_gaussian_white_noise(self):
        """Oq shovqin (Gaussian White Noise) fonida tasodifiy uyg'onmaslik"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.65)
        np.random.seed(42)
        noise = np.random.normal(0, 0.08, int(16000 * 1.5)).astype(np.float32)

        chunk_size = 1600
        detected = False
        for i in range(0, len(noise), chunk_size):
            det, _, _ = detector.analyze_audio(noise[i : i + chunk_size])
            if det:
                detected = True

        assert detected is False, "Oq shovqin wake-wordni faollashtirmasligi kerak!"

    def test_rejection_of_ac_electrical_hum_50hz(self):
        """50Hz elektr tarmog'i g'uvillashi va garmonikalari (50Hz, 100Hz, 150Hz)"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.70)
        t = np.linspace(0, 1.5, int(16000 * 1.5), endpoint=False)
        hum = (0.25 * np.sin(2 * np.pi * 50 * t) + 0.15 * np.sin(2 * np.pi * 100 * t)).astype(np.float32)

        chunk_size = 1600
        detected = False
        for i in range(0, len(hum), chunk_size):
            det, _, _ = detector.analyze_audio(hum[i : i + chunk_size])
            if det:
                detected = True

        assert detected is False, "50Hz g'uvillash faollashuv keltirib chiqarmasligi shart!"

    def test_rejection_of_isolated_click_pop_spikes(self):
        """Mikrofon ulanishidagi qisqa impulsli chertilishlar (Clicks & Pops)"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.65)
        audio = np.zeros(int(16000 * 1.2), dtype=np.float32)
        # 3 ta yakka impuls
        audio[1000] = 0.95
        audio[5000] = -0.90
        audio[9000] = 0.85

        chunk_size = 1600
        detected = False
        for i in range(0, len(audio), chunk_size):
            det, _, _ = detector.analyze_audio(audio[i : i + chunk_size])
            if det:
                detected = True

        assert detected is False, "Yakka klik impulslari fonetik uyg'onish bermasligi kerak!"

    def test_silence_handling(self):
        """To'liq jimlik (0 amplituda)"""
        detector = AcousticWakeWordDetector(sample_rate=16000, sensitivity=0.65)
        silence = np.zeros(1600, dtype=np.float32)
        det, score, thresh = detector.analyze_audio(silence)

        assert det is False
        assert score == 0.0


class TestPrivacyAndNetworkZeroLeakAudit:
    """Maxfiylik auditi: Wake-word aniqlash paytida mutlaqo tarmoq faoliyati yo'qligi"""

    def test_zero_network_connections_during_detection(self):
        """WakeWordDetector.process_frame chaqirilganda birorta ham tarmoq ulanishi bo'lmasligi"""
        detector = WakeWordDetector(sensitivity=0.65)
        chunk = np.random.uniform(-0.1, 0.1, 1600).astype(np.float32)

        network_call_attempted = False

        original_connect = socket.socket.connect

        def guarded_connect(self, *args, **kwargs):
            nonlocal network_call_attempted
            network_call_attempted = True
            raise AssertionError("XATOLIK: Wake-word jarayonida tarmoqqa ulanish taqiqlangan!")

        with patch.object(socket.socket, "connect", guarded_connect):
            # 20 ta ketma-ket audio freymni tahlil qilamiz
            for _ in range(20):
                detector.process_frame(chunk)

        assert network_call_attempted is False, "Wake-word jarayonida noqonuniy tarmoq so'rovi amalga oshirildi!"


class TestModelHonestyAndIntegrity:
    """Tizim o'z holati haqida yolg'on ma'lumot bermasligini tekshirish"""

    def test_detector_honestly_reports_heuristic_when_model_missing(self):
        """ONNX fayl yo'q bo'lganda is_trained_model=False va heuristic_spectral_analyzer qaytarilishi"""
        detector = WakeWordDetector(model_path="nonexistent_salom_misa.onnx")
        status = detector.get_status()

        assert status["is_trained_model"] is False
        assert status["engine_type"] == "heuristic_spectral_analyzer"
        assert status["active_engine"] == "heuristic_spectral_fallback"
        assert status["heuristic_fallback"]["active"] is True
        assert status["heuristic_fallback"]["is_trained_model"] is False

    def test_corrupted_onnx_file_does_not_crash_and_falls_back(self, tmp_path):
        """Yaroqsiz/buzilgan kichik ONNX fayli xavfsiz rad etilishi va zaxira mexanizmga o'tilishi"""
        fake_onnx = tmp_path / "corrupt_salom_misa.onnx"
        fake_onnx.write_text("invalid onnx binary header")

        engine = OpenWakeWordEngine(model_path=str(fake_onnx))
        assert engine.is_ready() is False
        assert engine.status in ("invalid_model_file", "load_failed", "model_missing")

        detector = WakeWordDetector(model_path=str(fake_onnx))
        assert detector.get_status()["is_trained_model"] is False
        # Freym berilganda tizim qulamasligi kerak
        dummy = np.zeros(1600, dtype=np.float32)
        assert detector.process_frame(dummy) is False
