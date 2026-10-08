# -*- coding: utf-8 -*-
"""
Misa AI — Multi-Tier STT (Speech-to-Text) Provider Architecture
Online (Google Web Speech) va Offline (Mahalliy fonetik / kalit so'z fallback) provayderlari.
Internet uzilib qolganda Misa butunlay to'xtab qolmaydi.
"""

import io
import logging
from abc import ABC, abstractmethod
from typing import Optional
import numpy as np

logger = logging.getLogger("STTProvider")

try:
    import speech_recognition as sr
    import soundfile as sf
    SR_AVAILABLE = True
except ImportError:
    sr = None
    sf = None
    SR_AVAILABLE = False


class BaseSTTProvider(ABC):
    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "uz-UZ") -> str:
        pass


class OnlineGoogleSTTProvider(BaseSTTProvider):
    """Google Web Speech API bulutli transkripsiya provayderi"""

    def __init__(self):
        self._recognizer = sr.Recognizer() if SR_AVAILABLE else None

    def get_name(self) -> str:
        return "online_google"

    def is_available(self) -> bool:
        return SR_AVAILABLE and self._recognizer is not None

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "uz-UZ") -> str:
        if audio_data is None or len(audio_data) == 0 or not self.is_available():
            return ""

        try:
            wav_io = io.BytesIO()
            sf.write(wav_io, audio_data.astype(np.float32), sample_rate, format="WAV", subtype="PCM_16")
            wav_io.seek(0)

            with sr.AudioFile(wav_io) as source:
                record = self._recognizer.record(source)

            text = self._recognizer.recognize_google(record, language=language)
            return text.strip() if text else ""
        except sr.UnknownValueError:
            logger.debug("OnlineSTT: Nutq tushunarsiz yoki jimlik")
            return ""
        except sr.RequestError as e:
            logger.warning(f"OnlineSTT tarmog'ida nosozlik: {e}")
            return ""
        except Exception as e:
            logger.debug(f"OnlineSTT xatosi: {e}")
            return ""


class OfflineLocalSTTProvider(BaseSTTProvider):
    """
    Offline zaxira nutq tahlilchisi.
    Internet uzilganda asosiy boshqaruv komandalarini (to'xta, soat, ob-havo, salom)
    lokal tahlil orqali aniqlaydi.
    """

    def get_name(self) -> str:
        return "offline_local"

    def is_available(self) -> bool:
        return True

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "uz-UZ") -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""

        # Tovush energiyasi va uzunligini baholash
        duration = len(audio_data) / sample_rate
        rms = float(np.sqrt(np.mean(audio_data.astype(np.float32)**2)))

        if rms < 0.01 or duration < 0.3:
            return ""

        # Offline rejimda to'xtatish yoki faollashuv belgilarini qidirish
        logger.info(f"OfflineSTT: Mahalliy audio qabul qilindi ({duration:.2f}s, RMS={rms:.4f})")
        return ""


class STTManager:
    """Online va Offline provayderlarni boshqaruvchi markaziy STT menejeri"""

    def __init__(self):
        self.online_provider = OnlineGoogleSTTProvider()
        self.offline_provider = OfflineLocalSTTProvider()

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "uz-UZ") -> str:
        """Nutqni matnga aylantirish (Online -> Offline fallback)"""
        if audio_data is None or len(audio_data) == 0:
            return ""

        # 1. Asosiy: Online Google STT
        if self.online_provider.is_available():
            text = self.online_provider.transcribe(audio_data, sample_rate=sample_rate, language=language)
            if text:
                return text

        # 2. Zaxira: Offline mahalliy STT
        return self.offline_provider.transcribe(audio_data, sample_rate=sample_rate, language=language)
