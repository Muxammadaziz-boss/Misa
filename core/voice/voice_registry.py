# -*- coding: utf-8 -*-
"""
Misa AI — Unified Voice Registry
Barcha ovozlar katalogi, provayderlari va real mavjudlik statuslari reestri.
Soxtalashtirilgan emulyatsiyalarga yo'l qo'ymaydi.
"""

from typing import Dict, Any, List, Optional
from .providers.rvc_provider import RVCVoiceProvider
from .providers.fish_audio_provider import FishAudioVoiceProvider
from .providers.edge_tts_provider import EdgeTTSVoiceProvider


class VoiceRegistry:
    """Misa AI barcha ovoz modellarini boshqarish reestri"""

    def __init__(self):
        self.edge_provider = EdgeTTSVoiceProvider()
        self.fish_provider = FishAudioVoiceProvider(fallback_provider=self.edge_provider)
        self.rvc_provider = RVCVoiceProvider()

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Hozirgi barcha ovozlarning dinamik tekshirilgan katalogini olish"""
        fish_ok = self.fish_provider.is_available()
        ashley_status = self.rvc_provider.get_voice_status("ashley")
        yukari_status = self.rvc_provider.get_voice_status("yukari")

        return [
            {
                "id": "ayol",
                "name": "Madina",
                "gender": "ayol",
                "provider": "edge_tts",
                "voice_id": "uz-UZ-MadinaNeural",
                "status": "available",
                "desc": "Tezkor milliy o'zbek ayol ovozi (Microsoft Edge-TTS)",
                "badge": "Standart",
                "sample": "Salom! Men Madina, Misa AI ning ovozli yordamchisiman."
            },
            {
                "id": "erkak",
                "name": "Sardor",
                "gender": "erkak",
                "provider": "edge_tts",
                "voice_id": "uz-UZ-SardorNeural",
                "status": "available",
                "desc": "Rasmiy o'zbek erkak diktor ovozi (Microsoft Edge-TTS)",
                "badge": "Standart",
                "sample": "Assalomu alaykum! Men Sardor, sizning intellektual yordamchingizman."
            },
            {
                "id": "fish_yigit",
                "name": "Yosh Dinamik",
                "gender": "erkak",
                "provider": "fish_audio",
                "voice_id": "502b927ae6c44543a3b37eea8529b0a5",
                "status": "available" if fish_ok else "fallback",
                "desc": "Haqiqiy jonli o'zbek yigit ovozi (Aziz Raxmonov / Fish Audio)",
                "badge": "O'zbek Yigit",
                "sample": "Assalomu alaykum! Ishlar qalay, bugun nimalarni bajaramiz?"
            },
            {
                "id": "fish_anime",
                "name": "Anime Drama",
                "gender": "ayol",
                "provider": "fish_audio",
                "voice_id": "d019b0d01cdb478e8f96df578942a552",
                "status": "available" if fish_ok else "fallback",
                "desc": "Kinematografik teatr anime qiz ovozi (Fish Audio Drama 3)",
                "badge": "Drama 3",
                "sample": "[muloyim, xursand ohangda] Salom! Men siz bilan doim birgaman."
            },
            {
                "id": "ashley",
                "name": "Ashley Clayson",
                "gender": "ayol",
                "provider": "rvc",
                "voice_id": "ashley_clayson",
                "status": ashley_status.get("status", "unavailable"),
                "reason": ashley_status.get("reason", "model runtime not implemented / missing dependency"),
                "desc": "Cyber Manhunt kiber-detektiv qahramonining xarizmatik ovoz modeli",
                "badge": "Lokal RVC",
                "sample": "Salom! Men Ashley, tizim sizning barcha buyruqlaringizga tayyor."
            },
            {
                "id": "yukari",
                "name": "Yukari",
                "gender": "ayol",
                "provider": "rvc",
                "voice_id": "discordjp_yukari",
                "status": yukari_status.get("status", "unavailable"),
                "reason": yukari_status.get("reason", "model runtime not implemented / missing dependency"),
                "desc": "DiscordJP yapon anime stilidagi quvnoq va yoqimli qizaloq ovoz modeli",
                "badge": "Anime RVC",
                "sample": "Assalomu alaykum! Men Yukari, birgalikda ajoyib ishlar qilamiz!"
            }
        ]

    def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Aynan bitta ovoz ma'lumotlarini olish"""
        cat = self.get_catalog()
        for v in cat:
            if v["id"] == voice_id.lower():
                return v
        return None


# Global nusxa
_registry_instance: Optional[VoiceRegistry] = None


def get_voice_registry() -> VoiceRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = VoiceRegistry()
    return _registry_instance
