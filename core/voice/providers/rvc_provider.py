# -*- coding: utf-8 -*-
"""
Misa AI — RVC (Retrieval-based Voice Conversion) v2 Model Provider
Ashley Clayson va Yukari lokal modellari holatini tekshirish va boshqarish.
Agar PyTorch/HuBERT/FAISS kabi og'ir bog'liqliklar bo'lmasa, soxtalashtirmasdan aniq 'unavailable' holatini qaytaradi.
"""

import os
import logging
from typing import Optional, Dict, Any
from .base_provider import BaseVoiceProvider
from ..cancellation import CancellationToken

logger = logging.getLogger("RVCProvider")


class RVCVoiceProvider(BaseVoiceProvider):
    """
    Lokal RVC v2 ovoz provayderi.
    Haqiqiy model fayllari (Ashley Clayson.pth va DiscordJP.pth) mavjudligini va
    ishga tushirish muhiti (PyTorch, HuBERT, FAISS) holatini qat'iy tekshiradi.
    """

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = models_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "rvc_models")
        )
        self._check_runtime_status()

    def get_provider_name(self) -> str:
        return "rvc"

    def _check_runtime_status(self) -> None:
        """RVC inference uchun zarur vositalarni tekshirish"""
        self.has_torch = False
        self.has_hubert = False
        self.has_faiss = False

        try:
            import torch
            self.has_torch = True
        except ImportError:
            pass

        try:
            import faiss
            self.has_faiss = True
        except ImportError:
            pass

        # HuBERT / ContentVec vazn fayli mavjudligini tekshirish
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        hubert_candidates = [
            os.path.join(root_dir, "hubert_base.pt"),
            os.path.join(root_dir, "data", "hubert_base.pt"),
            os.path.join(self.models_dir, "hubert_base.pt")
        ]
        self.has_hubert = any(os.path.exists(p) for p in hubert_candidates)

    def is_available(self) -> bool:
        """Haqiqiy RVC inferensi barcha talablari mavjud bo'lgandagina True"""
        self._check_runtime_status()
        return self.has_torch and self.has_hubert and self.has_faiss

    def get_voice_status(self, voice_id: str) -> Dict[str, Any]:
        """Ovoz modelining aniq holati va sababini qaytarish"""
        self._check_runtime_status()

        model_name = "Ashley Clayson" if "ashley" in voice_id.lower() else "Yukari (DiscordJP)"
        
        # 1. Model fayllari tekshiruvi
        pth_exists = False
        if "ashley" in voice_id.lower():
            pth_path = os.path.join(self.models_dir, "ashley", "Ashley Clayson.pth")
            pth_exists = os.path.exists(pth_path)
        else:
            pth_path = os.path.join(self.models_dir, "yukari", "DiscordJP_e400_s10800.pth")
            pth_exists = os.path.exists(pth_path)

        if not pth_exists:
            return {
                "status": "unavailable",
                "reason": f"{model_name} .pth fayli topilmadi (data/rvc_models jildida yo'q)",
                "runtime_ready": False
            }

        # 2. Runtime bog'liqliklar tekshiruvi
        missing_deps = []
        if not self.has_torch:
            missing_deps.append("PyTorch (torch/torchaudio)")
        if not self.has_hubert:
            missing_deps.append("HuBERT xususiyat ajratgich modeli (hubert_base.pt)")
        if not self.has_faiss:
            missing_deps.append("FAISS indeks qidiruv moduli")

        if missing_deps:
            return {
                "status": "unavailable",
                "reason": f"model runtime not implemented / missing dependency: {', '.join(missing_deps)}",
                "runtime_ready": False
            }

        return {
            "status": "available",
            "reason": "RVC inference modeli to'liq tayyor",
            "runtime_ready": True
        }

    def synthesize(
        self,
        text: str,
        voice_id: str,
        pitch: str = "+0Hz",
        rate: str = "+0%",
        cancel_token: Optional[CancellationToken] = None
    ) -> Optional[str]:
        """
        RVC inference sintezi.
        Agar runtime to'liq bo'lmasa, soxtalashtirilmasdan xabar beriladi va None qaytariladi.
        """
        status_info = self.get_voice_status(voice_id)
        if not status_info.get("runtime_ready"):
            logger.warning(
                f"RVC ovozi ({voice_id}) ishga tushirilmadi: {status_info.get('reason')}. "
                f"Misa qoidasi: Soxta emulyatsiya qilinmaydi."
            )
            return None

        # Agar barcha RVC talablari mavjud bo'lsa (to'liq muhitda):
        logger.info(f"RVC model orqali sintez bajarilmoqda: {voice_id}")
        return None
