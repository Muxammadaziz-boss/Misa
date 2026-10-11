# -*- coding: utf-8 -*-
"""
Misa AI — RVC Model & Runtime Dependency Installer
Ashley Clayson va Yukari lokal ovoz modellari uchun zarur AI paketlarini
(HuBERT model og'irliklari, PyTorch, FAISS) foydalanuvchi talabi bilan
(On-Demand) yuklab olish va o'rnatish menejeri.
"""

import os
import sys
import time
import shutil
import logging
import threading
import urllib.request
import subprocess
from typing import Dict, Any, Optional, List

logger = logging.getLogger("RVCInstaller")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RVC_MODELS_DIR = os.path.join(BASE_DIR, "data", "rvc_models")
HUBERT_FILE = os.path.join(RVC_MODELS_DIR, "hubert_base.pt")

# Rasmiy HuBERT / ContentVec vazn fayli
HUBERT_URL = "https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt"
HUBERT_EXPECTED_SIZE = 189507909  # ~180.7 MB


class RVCInstaller:
    """RVC lokal AI modellarini va kutubxonalarini nazorat qiluvchi va yuklovchi servis"""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._cancel_requested = False

        self._task_info: Dict[str, Any] = {
            "state": "idle",  # "idle" | "downloading_hubert" | "installing_packages" | "completed" | "error"
            "step": "",
            "progress": 0,
            "message": "",
            "downloaded_bytes": 0,
            "total_bytes": 0,
            "error": None,
            "updated_at": time.time(),
        }

    def check_components(self) -> Dict[str, bool]:
        """Barcha komponentlar holatini tekshirish"""
        has_torch = False
        has_torchaudio = False
        has_faiss = False

        try:
            import torch
            has_torch = True
        except ImportError:
            pass

        try:
            import torchaudio
            has_torchaudio = True
        except ImportError:
            pass

        try:
            import faiss
            has_faiss = True
        except ImportError:
            pass

        has_hubert = os.path.exists(HUBERT_FILE) and os.path.getsize(HUBERT_FILE) > 50_000_000

        # Model og'irliklari
        ashley_pth = os.path.join(RVC_MODELS_DIR, "ashley", "Ashley Clayson.pth")
        yukari_pth = os.path.join(RVC_MODELS_DIR, "yukari", "DiscordJP_e400_s10800.pth")

        return {
            "torch": has_torch,
            "torchaudio": has_torchaudio,
            "faiss": has_faiss,
            "hubert": has_hubert,
            "ashley_pth": os.path.exists(ashley_pth),
            "yukari_pth": os.path.exists(yukari_pth),
        }

    def get_status(self) -> Dict[str, Any]:
        """UI va API uchun to'liq status hisoboti"""
        comp = self.check_components()
        all_runtime_ready = comp["torch"] and comp["hubert"] and comp["faiss"]
        needs_download = not all_runtime_ready

        missing = []
        if not comp["hubert"]:
            missing.append("HuBERT xususiyat ajratgich modeli (hubert_base.pt, ~180MB)")
        if not comp["torch"] or not comp["torchaudio"]:
            missing.append("PyTorch CPU neyrotarmoq hisoblash moduli")
        if not comp["faiss"]:
            missing.append("FAISS vektor indeks moduli")

        installed = []
        if comp["hubert"]:
            installed.append("HuBERT modeli")
        if comp["torch"]:
            installed.append("PyTorch")
        if comp["faiss"]:
            installed.append("FAISS")
        if comp["ashley_pth"]:
            installed.append("Ashley Clayson ovoz vaznlari (.pth/.index)")
        if comp["yukari_pth"]:
            installed.append("Yukari ovoz vaznlari (.pth/.index)")

        with self._lock:
            task_copy = dict(self._task_info)

        return {
            "installed": all_runtime_ready,
            "needs_download": needs_download,
            "status_label": "Yuklab olish zarur" if needs_download else "O'rnatilgan (Faol)",
            "badge": "Yuklab olish zarur" if needs_download else "Lokal RVC",
            "missing_components": missing,
            "installed_components": installed,
            "hubert_exists": comp["hubert"],
            "torch_exists": comp["torch"],
            "faiss_exists": comp["faiss"],
            "task": task_copy,
        }

    def start_install(self) -> Dict[str, Any]:
        """Yuklab olish va o'rnatish jarayonini fonda boshlash"""
        with self._lock:
            if self._task_info["state"] in ["downloading_hubert", "installing_packages"]:
                return {
                    "ok": False,
                    "message": "Yuklab olish jarayoni allaqachon bajarilmoqda",
                    "task": dict(self._task_info),
                }

            self._cancel_requested = False
            self._task_info = {
                "state": "downloading_hubert",
                "step": "hubert",
                "progress": 0,
                "message": "HuBERT modelini yuklab olish boshlandi...",
                "downloaded_bytes": 0,
                "total_bytes": HUBERT_EXPECTED_SIZE,
                "error": None,
                "updated_at": time.time(),
            }

            self._thread = threading.Thread(target=self._run_install_worker, daemon=True)
            self._thread.start()

            return {
                "ok": True,
                "message": "AI paketlarini yuklab olish boshlandi",
                "task": dict(self._task_info),
            }

    def cancel_install(self) -> Dict[str, Any]:
        """Jarayonni to'xtatish"""
        with self._lock:
            self._cancel_requested = True
            self._task_info["state"] = "cancelled"
            self._task_info["message"] = "Yuklab olish foydalanuvchi tomonidan bekor qilindi"
            self._task_info["updated_at"] = time.time()
            return {"ok": True, "message": "Yuklab olish bekor qilindi"}

    def _update_task(self, **kwargs):
        with self._lock:
            self._task_info.update(kwargs)
            self._task_info["updated_at"] = time.time()

    def _run_install_worker(self):
        """Fon jarayoni: 1) HuBERT yuklab olish, 2) Kutubxonalarni o'rnatish"""
        logger.info("RVC Installer fon ishchi boshlandi")
        try:
            # 1-BOSQICH: HuBERT model faylini yuklab olish
            os.makedirs(RVC_MODELS_DIR, exist_ok=True)
            comp = self.check_components()

            if not comp["hubert"]:
                self._update_task(
                    state="downloading_hubert",
                    step="hubert",
                    progress=5,
                    message="HuBERT model fayli (hubert_base.pt) yuklanmoqda...",
                )

                part_file = HUBERT_FILE + ".downloading"
                req = urllib.request.Request(HUBERT_URL, headers={"User-Agent": "MisaAI/9.0"})

                with urllib.request.urlopen(req, timeout=30) as response, open(part_file, "wb") as out_file:
                    total_size = int(response.headers.get("Content-Length") or HUBERT_EXPECTED_SIZE)
                    self._update_task(total_bytes=total_size)
                    downloaded = 0
                    chunk_size = 512 * 1024  # 512 KB

                    while True:
                        if self._cancel_requested:
                            out_file.close()
                            if os.path.exists(part_file):
                                os.remove(part_file)
                            logger.info("HuBERT yuklab olish bekor qilindi")
                            return

                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        pct = int((downloaded / total_size) * 75)  # 0% dan 75% gacha
                        self._update_task(
                            progress=max(5, pct),
                            downloaded_bytes=downloaded,
                            message=f"HuBERT modeli yuklanmoqda: {downloaded // (1024 * 1024)} MB / {total_size // (1024 * 1024)} MB ({int((downloaded/total_size)*100)}%)",
                        )

                # Yuklab bo'lingach, haqiqiy fayl nomiga almashtirish
                if os.path.exists(HUBERT_FILE):
                    try:
                        os.remove(HUBERT_FILE)
                    except Exception:
                        pass
                shutil.move(part_file, HUBERT_FILE)
                logger.info(f"HuBERT modeli saqlandi: {HUBERT_FILE}")

            self._update_task(
                progress=80,
                step="packages",
                state="installing_packages",
                message="FAISS va AI inferens modullari o'rnatilmoqda...",
            )

            # 2-BOSQICH: FAISS kutubxonasini o'rnatish
            comp_now = self.check_components()
            if not comp_now["faiss"]:
                self._update_task(
                    progress=85,
                    message="FAISS qidiruv moduli o'rnatilmoqda (pip install faiss-cpu)...",
                )
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "faiss-cpu", "--quiet"],
                        capture_output=True,
                        text=True,
                        timeout=180,
                    )
                except Exception as e:
                    logger.warning(f"FAISS o'rnatishda xatolik: {e}")

            # 3-BOSQICH: PyTorch CPU tekshirish / o'rnatish
            comp_now = self.check_components()
            if not comp_now["torch"]:
                self._update_task(
                    progress=90,
                    message="PyTorch moduli tekshirilmoqda...",
                )
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "torch", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cpu", "--quiet"],
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                except Exception as e:
                    logger.warning(f"PyTorch o'rnatishda xatolik: {e}")

            # Yakuniy tekshiruv
            final_comp = self.check_components()
            if final_comp["hubert"]:
                self._update_task(
                    state="completed",
                    step="done",
                    progress=100,
                    message="Lokal RVC AI to'plami muvaffaqiyatli tayyorlandi! Ashley Clayson va Yukari ovozlari faol.",
                )
            else:
                self._update_task(
                    state="error",
                    error="HuBERT fayli to'liq saqlanmadi",
                    message="O'rnatish to'liq tugallanmadi",
                )

        except Exception as e:
            logger.error(f"RVC Installer xatosi: {e}")
            self._update_task(
                state="error",
                error=str(e),
                message=f"Xatolik yuz berdi: {str(e)}",
            )


# Global yagona nusxa
_installer_instance: Optional[RVCInstaller] = None


def get_rvc_installer() -> RVCInstaller:
    global _installer_instance
    if _installer_instance is None:
        _installer_instance = RVCInstaller()
    return _installer_instance
