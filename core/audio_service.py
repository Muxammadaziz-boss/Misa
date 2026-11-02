# ========== audio_service.py ==========
# Misa AI v6.0.0 — Modulli Audio va Tezkor VAD (Voice Activity Detection) Xizmati
# Past kechikish (Low-latency) va real-vaqt to'lqin monitoringi

import os
import io
import time
import math
import logging
import threading
from typing import Optional, Callable, Tuple

logger = logging.getLogger(__name__)

# Sounddevice / Soundfile mavjudligini tekshirish
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    AUDIO_HW_AVAILABLE = True
except ImportError:
    sd = None
    sf = None
    np = None
    AUDIO_HW_AVAILABLE = False
    logger.warning("sounddevice yoki numpy topilmadi. Audio apparat xizmati cheklangan.")

# SpeechRecognition mavjudligini tekshirish
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    sr = None
    SR_AVAILABLE = False
    logger.warning("speech_recognition topilmadi.")


class AudioService:
    """
    Misa AI uchun professional audio yozish va VAD xizmati.
    Statik 5 soniya kutish o'rniga dinamik ovoz faolligini aniqlaydi.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._is_recording = False
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._tts_playing = False
        self._recognizer = sr.Recognizer() if SR_AVAILABLE else None

        # VAD sozlamalari
        self.vad_threshold = 0.015       # Ovoz sezuvchanligi chegarasi (RMS)
        self.silence_timeout = 1.2       # Gap tugagach kutiladigan jimlik vaqti (soniya)
        self.max_recording_time = 10.0   # Maksimal yozish vaqti
        self.min_speech_duration = 0.4   # Shunchaki shovqin deb hisoblamaslik uchun minimal vaqt

    def is_available(self) -> bool:
        """Audio tizimi to'liq ishlashga tayyormi?"""
        return AUDIO_HW_AVAILABLE and SR_AVAILABLE

    def set_tts_playing(self, is_playing: bool):
        """
        Misa karnaydan gapirayotganda akustik aks-sado (AEC) va
        o'z ovozidan o'zi to'xtab qolishini oldini olish (MISA-ROOT-014).
        """
        with self._lock:
            self._tts_playing = bool(is_playing)

    def stop_recording(self):
        """Audio yozish jarayonini xavfsiz to'xtatish"""
        with self._lock:
            self._is_recording = False
            self._stop_event.set()

    def calculate_rms(self, chunk: "np.ndarray") -> float:
        """Audio bo'lagining RMS (Root Mean Square) quvvatini hisoblash"""
        if chunk is None or len(chunk) == 0 or np is None:
            return 0.0
        try:
            return float(np.sqrt(np.mean(chunk**2)))
        except Exception:
            return 0.0

    def record_with_vad(
        self,
        on_volume_change: Optional[Callable[[float], None]] = None,
        timeout: float = 6.0,
    ) -> Optional["np.ndarray"]:
        """
        Dinamik Voice Activity Detection (VAD) bilan ovoz yozib olish.
        Deadlock xavfsizligi va AEC Ducking bilan ta'minlangan.
        """
        if not AUDIO_HW_AVAILABLE:
            logger.error("Audio apparat vositalari o'rnatilmagan.")
            return None

        with self._lock:
            if self._is_recording:
                logger.warning("Allaqachon yozib olinmoqda")
                return None
            self._is_recording = True
            self._stop_event.clear()

        frames = []
        chunk_size = int(self.sample_rate * 0.1)  # 100ms chunks
        has_spoken = False
        speech_start_time = 0.0
        silence_start_time = None
        start_time = time.time()

        logger.info("VAD: Tinglash boshlandi...")

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype="float32") as stream:
                while self._is_recording and not self._stop_event.is_set():
                    chunk, overflowed = stream.read(chunk_size)
                    frames.append(chunk)

                    current_time = time.time()
                    elapsed_total = current_time - start_time
                    rms = self.calculate_rms(chunk)

                    # Dynamic AEC threshold: Karnay ishlayotgan bo'lsa sezuvchanlik chegarasini oshirish
                    active_threshold = self.vad_threshold * 4.0 if self._tts_playing else self.vad_threshold

                    # GUI dagi to'lqin vizualizatsiyasini yangilash
                    if on_volume_change:
                        try:
                            # 0.0 dan 1.0 gacha normallashtirish
                            normalized_vol = min(1.0, rms * 15.0)
                            on_volume_change(normalized_vol)
                        except Exception:
                            pass

                    # 1. Nutq boshlanganini aniqlash
                    if rms > active_threshold:
                        if not has_spoken:
                            has_spoken = True
                            speech_start_time = current_time
                            logger.debug("VAD: Nutq boshlandi")
                        silence_start_time = None  # Jimlik hisobini yangilash
                    else:
                        # 2. Agar foydalanuvchi gapirgan bo'lsa va endi jim bo'lsa
                        if has_spoken:
                            if silence_start_time is None:
                                silence_start_time = current_time
                            elif current_time - silence_start_time >= self.silence_timeout:
                                # Gap tugadi!
                                duration = current_time - speech_start_time
                                if duration >= self.min_speech_duration:
                                    logger.info(f"VAD: Nutq yakunlandi ({duration:.1f} soniya). To'xtatildi.")
                                    break
                                else:
                                    # Juda qisqa shovqin — yana kutamiz
                                    has_spoken = False
                                    silence_start_time = None

                    # 3. Vaqt chegaralari (Timeout)
                    if not has_spoken and elapsed_total > timeout:
                        logger.info("VAD: Hech narsa aytilmadi (kutish vaqti tugadi)")
                        break

                    if elapsed_total > self.max_recording_time:
                        logger.info("VAD: Maksimal yozish vaqti yetib keldi")
                        break

        except Exception as e:
            logger.error(f"VAD yozishda xatolik: {e}")
            return None
        finally:
            with self._lock:
                self._is_recording = False
                self._stop_event.clear()
            if on_volume_change:
                try:
                    on_volume_change(0.0)
                except Exception:
                    pass

        if not frames:
            return None

        # Bo'laklarni bitta massivga birlashtirish
        try:
            recording = np.concatenate(frames, axis=0)
            return recording
        except Exception as e:
            logger.error(f"Audio ma'lumotlarni birlashtirishda xatolik: {e}")
            return None

    def recognize_speech(self, audio_data: "np.ndarray", language: str = "uz-UZ") -> str:
        """
        Yozib olingan numpy audio ma'lumotini SpeechRecognition orqali matnga aylantirish.
        """
        if audio_data is None or not SR_AVAILABLE or not AUDIO_HW_AVAILABLE:
            return ""

        try:
            # Numpy massivni xotiradagi WAV formatiga o'tkazish
            wav_io = io.BytesIO()
            sf.write(wav_io, audio_data, self.sample_rate, format="WAV", subtype="PCM_16")
            wav_io.seek(0)

            with sr.AudioFile(wav_io) as source:
                audio_record = self._recognizer.record(source)

            # Google Web Speech API orqali matnga o'girish
            text = self._recognizer.recognize_google(audio_record, language=language)
            logger.info(f"Ovoz tanildi: '{text}'")
            return text.strip()

        except sr.UnknownValueError:
            logger.info("Nutq tushunarsiz yoki hech narsa deyilmadi")
            return ""
        except sr.RequestError as e:
            logger.error(f"Google Speech API so'rovida xatolik: {e}")
            return ""
        except Exception as e:
            logger.error(f"Ovozni aniqlashda xatolik: {e}")
            return ""

    def listen_and_transcribe(
        self,
        on_volume_change: Optional[Callable[[float], None]] = None,
        language: str = "uz-UZ",
        timeout: float = 5.0,
    ) -> str:
        """Tinglash va to'g'ridan-to'g'ri matn qaytarish (One-Stop Metod)"""
        audio = self.record_with_vad(on_volume_change=on_volume_change, timeout=timeout)
        if audio is None:
            return ""
        return self.recognize_speech(audio, language=language)


# Global singleton nusxa
_audio_service_instance: Optional[AudioService] = None


def get_audio_service() -> AudioService:
    global _audio_service_instance
    if _audio_service_instance is None:
        _audio_service_instance = AudioService()
    return _audio_service_instance
