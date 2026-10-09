# -*- coding: utf-8 -*-
"""
Misa AI — Multi-Tier STT (Speech-to-Text) Provider Architecture
Online (Google Web Speech) va Offline (Mahalliy fonetik / kalit so'z fallback) provayderlari.
Internet uzilib qolganda Misa butunlay to'xtab qolmaydi.
"""

import io
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
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
    Agar diskda haqiqiy lokal Vosk yoki Whisper modeli bo'lmasa,
    o'zini 'ishlayapti' deb soxtalashtirmaydi va buni aniq bildiradi.
    """

    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models", "stt")
        self._vosk_model = None
        self.status = "not_installed"
        self.status_message = (
            "Haqiqiy lokal offline STT modeli (masalan, Vosk yoki Whisper-ONNX) o'rnatilmagan. "
            "To'liq offline ovoz transkripsiyasi uchun 'models/stt/' papkasiga model joylashtirilishi zarur."
        )
        self._check_local_model()

    def _check_local_model(self) -> None:
        """Diskda lokal STT modeli mavjudligini tekshirish"""
        if os.path.isdir(self.model_dir) and any(os.scandir(self.model_dir)):
            try:
                import vosk
                self._vosk_model = vosk.Model(self.model_dir)
                self.status = "ready"
                self.status_message = f"Lokal Vosk STT modeli faol: {self.model_dir}"
                logger.info(self.status_message)
            except Exception as e:
                self.status = "error"
                self.status_message = f"Lokal STT modelini yuklashda xatolik: {e}"
        else:
            self.status = "not_installed"

    def get_name(self) -> str:
        return "offline_local"

    def is_available(self) -> bool:
        return self.status == "ready" and self._vosk_model is not None

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "uz-UZ") -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""

        if not self.is_available():
            logger.info("OfflineSTT: Mahalliy model yo'qligi sababli offline transkripsiya bajarilmadi.")
            return ""

        # Agar Vosk o'rnatilgan bo'lsa
        try:
            import json
            import vosk
            pcm16 = (np.clip(audio_data, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
            rec = vosk.KaldiRecognizer(self._vosk_model, sample_rate)
            rec.AcceptWaveform(pcm16)
            res = json.loads(rec.FinalResult())
            return res.get("text", "").strip()
        except Exception as e:
            logger.error(f"OfflineSTT transkripsiyasida xato: {e}")
            return ""


class OnlineGoogleSTTProvider(BaseSTTProvider):
    """Google Web Speech API bulutli transkripsiya provayderi (Foydalanuvchi roziligi bilan)"""

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
            logger.info("Online Google STT: Foydalanuvchi sozlamasi asosida audio Google Speech serveriga uzatilmoqda...")
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


class STTManager:
    """Online va Offline provayderlarni boshqaruvchi markaziy STT menejeri"""

    def __init__(self, allow_cloud_stt: Optional[bool] = None):
        if allow_cloud_stt is not None:
            self.allow_cloud_stt = bool(allow_cloud_stt)
        else:
            # Standart: MISA_ALLOW_CLOUD_STT muhit o'zgaruvchisidan olinadi (sukut bo'yicha True, lekin o'chirish mumkin)
            self.allow_cloud_stt = os.environ.get("MISA_ALLOW_CLOUD_STT", "1").strip().lower() in ("1", "true", "yes")

        self.online_provider = OnlineGoogleSTTProvider()
        self.offline_provider = OfflineLocalSTTProvider()

    def set_allow_cloud_stt(self, allowed: bool) -> None:
        """Foydalanuvchi sozlamasi orqali bulutli STT ruxsatini boshqarish"""
        self.allow_cloud_stt = bool(allowed)
        logger.info(f"STTManager: Bulutli STT ruxsati o'zgartirildi: {self.allow_cloud_stt}")

    def get_status(self) -> Dict[str, Any]:
        """STT holati va maxfiylik sozlamalarini ko'rsatish"""
        return {
            "cloud_stt": {
                "provider": "google_web_speech",
                "enabled": self.allow_cloud_stt,
                "is_available": self.online_provider.is_available(),
                "requires_internet": True,
                "privacy_notice": "Google Web Speech API ga audio yuboriladi (agar yoqilgan bo'lsa)."
            },
            "local_offline_stt": {
                "provider": "offline_local",
                "is_available": self.offline_provider.is_available(),
                "status": self.offline_provider.status,
                "message": self.offline_provider.status_message
            }
        }

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "uz-UZ") -> str:
        """Nutqni matnga aylantirish (Nazorat qilinadigan Cloud -> Offline fallback)"""
        if audio_data is None or len(audio_data) == 0:
            return ""

        # 1. Agar foydalanuvchi bulutli STT ga ruxsat bergan bo'lsa
        if self.allow_cloud_stt and self.online_provider.is_available():
            text = self.online_provider.transcribe(audio_data, sample_rate=sample_rate, language=language)
            if text:
                return text
        elif not self.allow_cloud_stt:
            logger.info("STTManager: Bulutli STT o'chirilgan (Privacy Mode). Faqat mahalliy zaxira tekshiriladi.")

        # 2. Zaxira: Offline mahalliy STT (haqiqiy model mavjud bo'lsa)
        if self.offline_provider.is_available():
            return self.offline_provider.transcribe(audio_data, sample_rate=sample_rate, language=language)

        logger.info("STTManager: Nutq transkripsiyasi amalga oshmadi (Lokal model yo'q, bulutli STT ishlatilmadi yoki javobsiz).")
        return ""
