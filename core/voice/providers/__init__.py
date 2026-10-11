# -*- coding: utf-8 -*-
from .base_provider import BaseVoiceProvider
from .edge_tts_provider import EdgeTTSVoiceProvider
from .fish_audio_provider import FishAudioVoiceProvider
from .rvc_provider import RVCVoiceProvider

__all__ = [
    "BaseVoiceProvider",
    "EdgeTTSVoiceProvider",
    "FishAudioVoiceProvider",
    "RVCVoiceProvider",
]
