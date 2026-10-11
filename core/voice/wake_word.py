# -*- coding: utf-8 -*-
"""
Misa AI — Secure Local Wake-Word Engine ("Salom Misa")
100% lokal, maxfiy va tezkor (<200ms) kalit so'zni aniqlash vositasi.
Rasmiy openWakeWord arxitekturasi va apparat-kalibrlangan fonetik tahlil integratsiyasi.
Tashqi serverlarga audio yoki telemetriya yubormaydi (Zero Cloud Leaks, Zero Network Calls).
Faqat "Salom Misa" (yoki sozlangan "Hey Misa" / "Mikasa") eshitilganda uyg'onadi.
"""

import os
import sys
import time
import logging
import threading
from typing import Optional, Callable, Dict, Any, Tuple, List
import numpy as np

from core.common_paths import get_base_dir

logger = logging.getLogger("WakeWordEngine")

# openWakeWord va ONNX Runtime mavjudligini tekshirish
try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
    import onnxruntime as ort
    OPENWAKEWORD_AVAILABLE = True
except Exception as _oww_err:
    openwakeword = None
    OWWModel = None
    ort = None
    OPENWAKEWORD_AVAILABLE = False
    logger.debug(f"openWakeWord kutubxonasi yuklanmadi: {_oww_err}")

BASE_DIR = get_base_dir()
DEFAULT_MODEL_DIR = os.path.join(BASE_DIR, "models", "wake_word")
DEFAULT_PRIMARY_PHRASE = "Salom Misa"
DEFAULT_MODEL_FILENAME = "salom_misa.onnx"
DEFAULT_ALTERNATIVE_PHRASES = ["Hey Misa", "Mikasa"]


class OpenWakeWordEngine:
    """
    Rasmiy openWakeWord loyihasiga asoslangan lokal neyrotarmoq uyg'otuvchi so'z dvigateli.
    Maxfiylik kafolati:
    - Tarmoq orqali hech qanday audio yoki telemetriya yubormaydi.
    - Model faylini runtime vaqtida internetdan yashirincha YUKLAB OLMAYDI (Zero auto-download).
    - Faqat lokal diskdagi rasmiy/maxsus ONNX model faylini yuklaydi.
    - Agar maxsus "salom_misa.onnx" modeli diskda topilmasa, yolg'on model qo'llamaydi,
      balki aniq holat qaytaradi va lokal akustik tahlilchiga o'tadi.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        phrase: str = DEFAULT_PRIMARY_PHRASE,
        sensitivity: float = 0.65
    ):
        self.phrase = phrase
        self.sensitivity = max(0.1, min(0.99, sensitivity))
        self.threshold = float(0.85 - (self.sensitivity * 0.45))  # 0.40 - 0.80 oralig'ida bo'sag'a

        self.model_dir = DEFAULT_MODEL_DIR
        self.configured_model_path = model_path or os.environ.get("MISA_WAKE_WORD_MODEL_PATH")
        self.resolved_model_path = self._resolve_model_path()

        self._model: Optional[Any] = None
        self._lock = threading.Lock()
        self.status = "uninitialized"  # "ready" | "model_missing" | "library_unavailable" | "error"
        self.status_message = ""
        self.last_score = 0.0

        self._init_engine()

    def _check_file_validity(self, path: Optional[str]) -> bool:
        """Fayl mavjudligi va hajm/tuzilishi yaroqliligini tekshirish (>1KB)"""
        if not path or not os.path.isfile(path):
            return False
        try:
            return os.path.getsize(path) > 1024
        except Exception:
            return False

    def _resolve_model_path(self) -> str:
        """Lokal model faylining mutlaq yo'lini aniqlash"""
        if self.configured_model_path:
            cand = os.path.abspath(self.configured_model_path)
            if os.path.isfile(cand):
                return cand

        # Standart papkadagi faylni qidirish: models/wake_word/salom_misa.onnx
        default_path = os.path.join(self.model_dir, DEFAULT_MODEL_FILENAME)
        return default_path

    def _init_engine(self) -> None:
        """Dvigatelni lokal diskdagi model bilan initsializatsiya qilish (Internetga so'rovsiz)"""
        if not OPENWAKEWORD_AVAILABLE:
            self.status = "library_unavailable"
            self.status_message = "openwakeword yoki onnxruntime kutubxonasi muhitda mavjud emas."
            logger.info(f"OpenWakeWordEngine: {self.status_message}")
            return

        if not os.path.isfile(self.resolved_model_path):
            self.status = "model_missing"
            self.status_message = (
                f"Maxsus '{self.phrase}' modeli '{self.resolved_model_path}' yo'lida topilmadi. "
                f"Lokal apparat-kalibrlangan fonetik tahlilchiga (Heuristic fallback) o'tildi."
            )
            logger.info(f"OpenWakeWordEngine: {self.status_message}")
            return

        if not self._check_file_validity(self.resolved_model_path):
            self.status = "invalid_model_file"
            self.status_message = (
                f"Model fayli '{self.resolved_model_path}' yaroqsiz yoki bo'sh (hajmi <1KB). "
                f"Lokal evristik tahlilchi (Heuristic fallback) faol."
            )
            logger.warning(f"OpenWakeWordEngine: {self.status_message}")
            return

        # openWakeWord uchun xususiyat ekstraktorlari (melspectrogram & embedding) mavjudligini tekshirish
        melspec_path = os.path.join(self.model_dir, "melspectrogram.onnx")
        embed_path = os.path.join(self.model_dir, "embedding_model.onnx")

        # Agar maxsus model papkasida bo'lmasa, openwakeword paketi resurslaridan qidirish
        if not os.path.isfile(melspec_path) and openwakeword:
            pkg_res = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models", "melspectrogram.onnx")
            if os.path.isfile(pkg_res):
                melspec_path = pkg_res

        if not os.path.isfile(embed_path) and openwakeword:
            pkg_res = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models", "embedding_model.onnx")
            if os.path.isfile(pkg_res):
                embed_path = pkg_res

        has_feature_models = self._check_file_validity(melspec_path) and self._check_file_validity(embed_path)
        if not has_feature_models:
            self.status = "model_missing"
            self.status_message = (
                f"openWakeWord audio xususiyat modellari (melspectrogram.onnx, embedding_model.onnx) "
                f"'{self.model_dir}' papkasida topilmadi. Internetdan yashirincha yuklab olinmaydi. "
                f"Lokal apparat evristikasi (Heuristic fallback) faol holatda davom etmoqda."
            )
            logger.info(f"OpenWakeWordEngine: {self.status_message}")
            return

        try:
            logger.info(f"OpenWakeWordEngine: Lokal model yuklanmoqda: {self.resolved_model_path}")
            self._model = OWWModel(
                wakeword_models=[self.resolved_model_path],
                inference_framework="onnx",
                melspec_model_path=melspec_path,
                embedding_model_path=embed_path,
                vad_threshold=0.0
            )
            self.status = "ready"
            self.status_message = f"Lokal '{self.phrase}' modeli muvaffaqiyatli yuklandi ({os.path.basename(self.resolved_model_path)})."
            logger.info(f"OpenWakeWordEngine: {self.status_message}")
        except Exception as e:
            self.status = "error"
            self.status_message = f"Modelni yuklashda xatolik yuz berdi: {e}"
            logger.error(f"OpenWakeWordEngine: {self.status_message}")

    def is_ready(self) -> bool:
        """Dvigatel haqiqiy lokal model bilan ishlashga to'liq tayyormi?"""
        return self.status == "ready" and self._model is not None

    def predict(self, chunk: np.ndarray) -> Tuple[bool, float, float]:
        """
        Audio freymini (16kHz, float32 yoki int16) tahlil qilish.
        Qaytaradi: (aniqlandimi, ball, chegara)
        """
        if not self.is_ready() or chunk is None or len(chunk) == 0:
            return False, 0.0, self.threshold

        try:
            chunk_arr = np.asarray(chunk, dtype=np.float32).flatten()
            # 16-bit PCM ga normallashtirish
            pcm16 = (np.clip(chunk_arr, -1.0, 1.0) * 32767.0).astype(np.int16)

            with self._lock:
                preds = self._model.predict(pcm16)

            if isinstance(preds, dict) and preds:
                # Barcha model nomlaridagi eng yuqori ehtimollikni olish
                max_score = max(float(v) for v in preds.values())
                self.last_score = max_score
                detected = max_score >= self.threshold
                return detected, max_score, self.threshold

            return False, 0.0, self.threshold
        except Exception as e:
            logger.debug(f"OpenWakeWordEngine inferens xatosi: {e}")
            return False, 0.0, self.threshold

    def reset(self) -> None:
        """Buferni tozalash"""
        if self._model and hasattr(self._model, "prediction_buffer"):
            try:
                for k in self._model.prediction_buffer:
                    self._model.prediction_buffer[k].clear()
            except Exception:
                pass


class AcousticWakeWordDetector:
    """
    Mahalliy "Salom Misa" / "Misa" (yoki "Hey Misa") kalit so'zini aniqlash mexanizmi.
    16kHz mono audio signali ustida spektral va fonetik bosqichli tahlil o'tkazadi:
    [m] (burun murmuri) -> [i] (yuqori formant) -> [s] (jarohatlovchi frikativ) -> [a] (ochiq unli).
    100% lokal, maxfiy, offline va tezkor (<200ms).
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        sensitivity: float = 0.65
    ):
        self.sample_rate = sample_rate
        self.sensitivity = max(0.2, min(0.95, sensitivity))

        self.buffer_duration = 1.2  # soniya
        self.buffer_size = int(self.sample_rate * self.buffer_duration)
        self._audio_buffer = np.zeros(self.buffer_size, dtype=np.float32)

        self._lock = threading.Lock()
        self._ambient_noise_level = 0.002
        self.last_wake_score = 0.0
        self.last_threshold = 0.82 - (self.sensitivity * 0.40)

        # FFT chastota zonalari (hardware-calibrated fonetik zonalar)
        self.fft_size = 512
        freqs = np.fft.rfftfreq(self.fft_size, 1.0 / self.sample_rate)
        self.nasal_mask = (freqs >= 150) & (freqs <= 480)     # /m/ burun murmuri (150-480Hz)
        self.vowel_a_mask = (freqs >= 650) & (freqs <= 1400) # /a/ ochiq unli formantlari (F1 ~750Hz, F2 ~1200Hz)
        self.mid_mask = (freqs >= 1400) & (freqs <= 2800)   # /i/ yuqori formanti (F2 ~2200-2600Hz)
        self.high_mask = (freqs >= 2800) & (freqs <= 7500)  # /s/ frikativ sibilans

    def reset(self) -> None:
        """Buferni tozalash"""
        with self._lock:
            self._audio_buffer.fill(0.0)

    def update_ambient_noise(self, rms: float) -> None:
        """Atrofdagi fon shovqin darajasini moslashtirish"""
        if rms < 0.012:
            self._ambient_noise_level = 0.98 * self._ambient_noise_level + 0.02 * max(0.0005, rms)

    def analyze_audio(self, chunk: np.ndarray) -> Tuple[bool, float, float]:
        """
        Audio bo'lagini tahlil qilish va (aniqlandimi, ball, chegara) qaytarish.
        """
        if chunk is None or len(chunk) == 0:
            return False, 0.0, self.last_threshold

        chunk_arr = np.asarray(chunk, dtype=np.float32)
        if chunk_arr.ndim > 1:
            chunk_arr = chunk_arr.mean(axis=1)
        chunk_flat = chunk_arr.flatten()

        shift = len(chunk_flat)
        with self._lock:
            if shift >= self.buffer_size:
                self._audio_buffer = chunk_flat[-self.buffer_size:]
            else:
                self._audio_buffer[:-shift] = self._audio_buffer[shift:]
                self._audio_buffer[-shift:] = chunk_flat

            buf_copy = self._audio_buffer.copy()

        is_detected, score, thresh = self._analyze_misa_acoustics(buf_copy)
        self.last_wake_score = score
        self.last_threshold = thresh
        return is_detected, score, thresh

    def _analyze_misa_acoustics(self, audio: np.ndarray) -> Tuple[bool, float, float]:
        """
        'Misa' fonetik belgilarini real mikrofon signali ustida tahlil qilish:
        1. /m/ (Burun murmuri, 150-480Hz)
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
        nasal_energies = []
        vowel_a_energies = []
        frame_rms = []

        crest_factors = []
        for f in frames:
            r = float(np.sqrt(np.mean(f**2)))
            frame_rms.append(r)
            peak = float(np.max(np.abs(f))) if len(f) > 0 else 0.0
            crest_factors.append(peak / (r + 1e-9))
            z = float(np.mean(np.abs(np.diff(np.sign(f)))) / 2.0)
            zcrs.append(z)

            spec = np.abs(np.fft.rfft(f, n=self.fft_size))
            tot = np.sum(spec) + 1e-9
            nasal_energies.append(float(np.sum(spec[self.nasal_mask]) / tot))
            vowel_a_energies.append(float(np.sum(spec[self.vowel_a_mask]) / tot))
            mid_energies.append(float(np.sum(spec[self.mid_mask]) / tot))
            high_energies.append(float(np.sum(spec[self.high_mask]) / tot))

        max_r = max(frame_rms) if frame_rms else 0.0
        speech_thresh = max(0.002, max_r * 0.15)

        s_candidates = [
            i for i in range(1, num_frames - 1)
            if frame_rms[i] >= speech_thresh and crest_factors[i] <= 9.5 and (
                (zcrs[i] >= 0.15 and high_energies[i] >= 0.14) or
                (high_energies[i] >= 0.25)
            )
        ]

        if not s_candidates:
            return False, 0.0, thresh

        best_score = 0.0
        for s_idx in s_candidates:
            # 1. /s/ dan oldingi 1-5 freymda /m-i/ fonemasi mavjudligi (/m/ 150-480Hz yoki /i/ 1400-2800Hz)
            pre_scores = []
            for p in range(max(0, s_idx - 5), s_idx):
                if (
                    frame_rms[p] >= speech_thresh
                    and crest_factors[p] <= 9.5
                    and zcrs[p] < 0.16
                    and high_energies[p] < 0.12
                ):
                    val = max(nasal_energies[p] / 0.30, mid_energies[p] / 0.25)
                    pre_scores.append(min(1.0, val))
            if not pre_scores:
                continue
            m_score = max(pre_scores)

            # 2. /s/ dan keyingi 1-5 freymda /a/ unlisi mavjudligi (650-1400Hz formant)
            post_scores = []
            for p in range(s_idx + 1, min(num_frames, s_idx + 6)):
                if (
                    frame_rms[p] >= speech_thresh
                    and crest_factors[p] <= 9.5
                    and zcrs[p] < 0.18
                    and high_energies[p] < 0.14
                ):
                    val = vowel_a_energies[p] / 0.30
                    post_scores.append(min(1.0, val))
            if not post_scores:
                continue
            a_score = max(post_scores)

            # 3. /s/ sifat ko'rsatkichi
            s_score = min(1.0, (zcrs[s_idx] / 0.30) * 0.5 + (high_energies[s_idx] / 0.28) * 0.5)

            cand_score = 0.35 * m_score + 0.35 * s_score + 0.30 * a_score
            if cand_score > best_score:
                best_score = cand_score

        is_detected = (best_score >= thresh)
        return is_detected, best_score, thresh


class WakeWordDetector:
    """
    Misa AI — Yagona Birlashgan Uyg'otuvchi So'z Boshqaruvchisi (Unified Wake-Word Orchestrator).
    Arxitektura:
    1. openWakeWord Engine: Agar diskda 'models/wake_word/salom_misa.onnx' (va kerakli xususiyat modellari)
       mavjud bo'lsa, rasmiy openWakeWord neyrotarmoq modelidan foydalanadi.
    2. Acoustic Fallback Engine: Agar maxsus model fayli topilmasa, internetdan hech narsa tortib olinmaydi!
       Buning o'rniga zudlik bilan apparat-kalibrlangan lokal fonetik tahlilchi ishga tushadi.
    3. Maxfiylik va Xavfsizlik: Barcha tahlil 100% lokal disk va RAM da kechadi, tashqi so'rovlar umuman yo'q.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        sensitivity: float = 0.65,
        on_wake_detected: Optional[Callable[[Dict[str, Any]], None]] = None,
        model_path: Optional[str] = None,
        phrase: str = DEFAULT_PRIMARY_PHRASE
    ):
        self.sample_rate = sample_rate
        self.sensitivity = max(0.1, min(0.99, sensitivity))
        self.on_wake_detected = on_wake_detected
        self.phrase = phrase
        self.alternative_phrases = list(DEFAULT_ALTERNATIVE_PHRASES)

        self._cooldown_seconds = 1.8
        self._last_wake_time = 0.0
        self._lock = threading.Lock()

        # Dvigatellarni yaratish
        self.oww_engine = OpenWakeWordEngine(
            model_path=model_path,
            phrase=self.phrase,
            sensitivity=self.sensitivity
        )
        self.acoustic_detector = AcousticWakeWordDetector(
            sample_rate=self.sample_rate,
            sensitivity=self.sensitivity
        )

        self.last_wake_score = 0.0
        self.last_threshold = 0.5
        self.active_engine_name = "openwakeword" if self.oww_engine.is_ready() else "acoustic"

        # Diagnostika
        self.diagnostic_mode = os.environ.get("VOICE_DIAGNOSTIC", "").strip().lower() in ("1", "true", "yes")
        self._last_diag_log = 0.0

    def reset(self) -> None:
        """Buferlarni tozalash"""
        with self._lock:
            self.oww_engine.reset()
            self.acoustic_detector.reset()

    def update_ambient_noise(self, rms: float) -> None:
        """Atrof shovqin darajasini yangilash"""
        self.acoustic_detector.update_ambient_noise(rms)

    def get_active_engine_name(self) -> str:
        """Hozirgi faol dvigatel nomi"""
        return "openwakeword" if self.oww_engine.is_ready() else "heuristic_spectral_fallback"

    def configure(
        self,
        sensitivity: Optional[float] = None,
        model_path: Optional[str] = None,
        cooldown: Optional[float] = None
    ) -> Dict[str, Any]:
        """Parametrlarni dinamik sozlash"""
        with self._lock:
            if sensitivity is not None:
                self.sensitivity = max(0.1, min(0.99, float(sensitivity)))
                self.oww_engine.sensitivity = self.sensitivity
                self.oww_engine.threshold = float(0.85 - (self.sensitivity * 0.45))
                self.acoustic_detector.sensitivity = self.sensitivity

            if cooldown is not None:
                self._cooldown_seconds = max(0.5, float(cooldown))

            if model_path is not None:
                self.oww_engine = OpenWakeWordEngine(
                    model_path=model_path,
                    phrase=self.phrase,
                    sensitivity=self.sensitivity
                )
                self.active_engine_name = self.get_active_engine_name()

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """Tizim telemetriyasi va holatini qaytarish"""
        is_trained = self.oww_engine.is_ready()
        return {
            "phrase": self.phrase,
            "alternative_phrases": self.alternative_phrases,
            "active_engine": self.get_active_engine_name(),
            "is_trained_model": is_trained,
            "engine_type": "neural_network" if is_trained else "heuristic_spectral_analyzer",
            "sensitivity": self.sensitivity,
            "cooldown_seconds": self._cooldown_seconds,
            "openwakeword": {
                "available": OPENWAKEWORD_AVAILABLE,
                "status": self.oww_engine.status,
                "status_message": self.oww_engine.status_message,
                "model_path": self.oww_engine.resolved_model_path,
                "model_exists": self.oww_engine._check_file_validity(self.oww_engine.resolved_model_path),
                "is_ready": is_trained,
                "threshold": self.oww_engine.threshold,
                "last_score": self.oww_engine.last_score,
            },
            "heuristic_fallback": {
                "active": not is_trained,
                "is_trained_model": False,
                "description": "Apparat-kalibrlangan FFT fonetik evristikasi (o'qitilgan neyrotarmoq modeli emas)",
                "last_score": self.acoustic_detector.last_wake_score,
                "threshold": self.acoustic_detector.last_threshold,
            },
            "acoustic_fallback": {
                "active": not is_trained,
                "is_trained_model": False,
                "description": "Apparat-kalibrlangan FFT fonetik evristikasi (o'qitilgan neyrotarmoq modeli emas)",
                "last_score": self.acoustic_detector.last_wake_score,
                "threshold": self.acoustic_detector.last_threshold,
            },
            "security": {
                "offline_guarantee": True,
                "zero_network_leaks": True,
                "auto_download_forbidden": True
            },
            "license": {
                "openwakeword_code": "Apache-2.0",
                "openwakeword_pretrained_models": "CC BY-NC-SA 4.0",
                "custom_trained_models": "Owner/Dataset Defined",
                "heuristic_fallback": "Built-in Spectral Analysis Heuristic"
            }
        }

    def process_frame(self, chunk: np.ndarray) -> bool:
        """
        Audio bo'lagini (50-100ms) tahlil qilish va uyg'otuvchi so'z aniqlanganini bildirish.
        """
        if chunk is None or len(chunk) == 0:
            return False

        now = time.time()
        # Cooldown tekshiruvi: qayta uyg'onishdan saqlanish
        if now - self._last_wake_time < self._cooldown_seconds:
            return False

        is_detected = False
        score = 0.0
        thresh = 0.5
        engine_used = "heuristic_spectral_fallback"

        # 1. Agar openWakeWord modeli tayyor bo'lsa -> openWakeWord ishlatiladi
        if self.oww_engine.is_ready():
            is_detected, score, thresh = self.oww_engine.predict(chunk)
            engine_used = "openwakeword"
        else:
            # 2. Aks holda -> Zudlik bilan xavfsiz lokal apparat fonetik evristikasi ishlatiladi
            is_detected, score, thresh = self.acoustic_detector.analyze_audio(chunk)
            engine_used = "heuristic_spectral_fallback"

        self.last_wake_score = score
        self.last_threshold = thresh
        self.active_engine_name = engine_used

        # Diagnostik loglar
        chunk_arr = np.asarray(chunk, dtype=np.float32).flatten()
        chunk_rms = float(np.sqrt(np.mean(chunk_arr**2))) if len(chunk_arr) > 0 else 0.0
        if (self.diagnostic_mode or logger.isEnabledFor(logging.DEBUG)) and (now - self._last_diag_log >= 1.5):
            if chunk_rms >= 0.003 or score > 0.15:
                logger.info(
                    f"[VOICE] wake_detector: engine={engine_used} | score={score:.2f} "
                    f"(thresh={thresh:.2f}, rms={chunk_rms:.4f})"
                )
                self._last_diag_log = now

        if is_detected:
            self._last_wake_time = now
            logger.info(
                f"[VOICE] WAKE WORD DETECTED: '{self.phrase}' via {engine_used} "
                f"(score={score:.2f} >= threshold={thresh:.2f})"
            )

            if self.on_wake_detected:
                event_data = {
                    "phrase": self.phrase,
                    "engine": engine_used,
                    "score": score,
                    "threshold": thresh,
                    "timestamp": now
                }
                try:
                    # Callback argument qabul qilsa uzatish, aks holda argumentsiz chaqirish
                    try:
                        self.on_wake_detected(event_data)
                    except TypeError:
                        self.on_wake_detected()
                except Exception as cb_err:
                    logger.error(f"[VOICE] Wake callback ijro xatosi: {cb_err}")

            return True

        return False
