# -*- coding: utf-8 -*-
"""
Misa AI — Base Voice Provider Interface
Barcha TTS provayderlari (Edge-TTS, Fish Audio, RVC va boshqalar) uchun umumiy abstrakt interfeys.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..cancellation import CancellationToken


class BaseVoiceProvider(ABC):
    """Barcha TTS ovoz provayderlari uchun baza sinfi"""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Provayder nomi"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Provayder hozirda ishlashga tayyormi?"""
        pass

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        pitch: str = "+0Hz",
        rate: str = "+0%",
        cancel_token: Optional[CancellationToken] = None
    ) -> Optional[str]:
        """
        Matndan MP3/WAV fayl hosil qilish.
        Muvaffaqiyatli bo'lsa audio fayl yo'lini (str) qaytaradi, aks holda None.
        """
        pass
