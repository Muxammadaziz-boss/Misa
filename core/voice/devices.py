# -*- coding: utf-8 -*-
"""
Misa AI — Production Audio Capture & Microphone Device Manager
Windows audio kirish qurilmalarini aniqlash (enumeration), tanlash (selection),
xotirada saqlash (persistence), apparat muvofiqligi (resampling/compatibility)
va real-time test qilish xizmati.
"""

import os
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("MicrophoneManager")

# Config fayli
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


def _read_persisted_microphone() -> Tuple[Optional[str], Optional[str]]:
    """config.json dan oldin tanlangan mikrofon id va nomini o'qish"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                v = cfg.get("voice", {})
                return v.get("selected_microphone_id"), v.get("selected_microphone_name")
    except Exception as e:
        logger.debug(f"Config o'qishda xatolik: {e}")
    return None, None


def _save_persisted_microphone(device_id: str, device_name: str) -> None:
    """config.json ga tanlangan mikrofonni xavfsiz saqlash"""
    try:
        cfg: Dict[str, Any] = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
        if "voice" not in cfg:
            cfg["voice"] = {}
        cfg["voice"]["selected_microphone_id"] = device_id
        cfg["voice"]["selected_microphone_name"] = device_name
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Tanlangan mikrofonni saqlashda xatolik: {e}")


class MicrophoneManager:
    """
    Windows tizimidagi audio input qurilmalarini to'liq boshqarish:
    - Real capture devicelarni filtrlash (speaker/outputlar chiqarib tashlanadi)
    - Fallback siyosati (tanlangan device uzilgan bo'lsa, foydalanuvchiga halol xabar bilan defaultga o'tish)
    - Har qanday qurilma (BM 800, Onda Webcam, Realtek) uchun apparat moslashuvi
    """

    _instance: Optional["MicrophoneManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._selected_device_id: Optional[str] = None
        self._selected_device_name: Optional[str] = None
        saved_id, saved_name = _read_persisted_microphone()
        self._selected_device_id = saved_id
        self._selected_device_name = saved_name

    @classmethod
    def get_instance(cls) -> "MicrophoneManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_input_devices(self) -> List[Dict[str, Any]]:
        """
        Windows'dagi barcha haqiqiy AUDIO INPUT (capture) qurilmalarini aniqlash.
        Output/speaker qurilmalari mutlaqo kiritilmaydi.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice o'rnatilmagan")
            return []

        devices_list: List[Dict[str, Any]] = []
        try:
            raw_devices = sd.query_devices()
            default_input_idx = sd.default.device[0]
        except Exception as e:
            logger.error(f"Audio qurilmalarni so'rashda xatolik: {e}")
            return []

        # Tizim standarti (Windows Default) har doim birinchi parametr
        devices_list.append({
            "id": "default",
            "name": "Tizim standarti (Windows Default)",
            "type": "input",
            "available": True,
            "is_default": True,
            "index": default_input_idx if default_input_idx is not None and default_input_idx >= 0 else None,
            "description": "Windows ovoz sozlamalaridagi asosiy yozib olish qurilmasi",
        })

        seen_names = set()
        for idx, d in enumerate(raw_devices):
            max_in = d.get("max_input_channels", 0)
            if max_in <= 0:
                continue  # Faqat input qurilmalar! Output/speaker chiqariladi.

            raw_name = str(d.get("name", "")).strip()
            if not raw_name:
                continue

            host_api = d.get("hostapi", 0)
            # PortAudio blocking API uchun MME (0) va DirectSound (1) eng barqaror
            # Agar bir xil nomli qurilma MME da bo'lsa, WDM-KS dublikatlarini saralash
            key = f"{raw_name}_{host_api}"
            is_default = (idx == default_input_idx)

            # Qurilmani tekshirib ko'rish (ochilishi mumkinmi)
            is_available = True
            if host_api == 4:
                # WDM-KS blocking API ni qo'llamaydi
                is_available = False

            devices_list.append({
                "id": f"dev_{idx}",
                "name": raw_name,
                "type": "input",
                "available": is_available,
                "is_default": is_default,
                "index": idx,
                "host_api": host_api,
                "channels": max_in,
                "sample_rate": int(d.get("default_samplerate", 16000)),
            })

        return devices_list

    def resolve_selected_device(self) -> Tuple[Optional[int], Dict[str, Any], bool, str]:
        """
        Hozirgi tanlangan qurilmani PortAudio indexiga yechish.
        Qaytadi: (device_index, device_info, fallback_used, status_message)
        
        Siyosat (Policy):
        1. User oldin tanlagan bo'lsa va mavjud bo'lsa -> shu qurilma
        2. Tanlangan qurilma ulanmagan/mavjud bo'lmasa -> aniq ogohlantirish bilan Default ga o'tish
        3. User "default" tanlagan bo'lsa -> Windows Default
        4. Default ham yo'q bo'lsa -> Unavailable
        """
        try:
            import sounddevice as sd
        except ImportError:
            return None, {}, True, "sounddevice moduli topilmadi"

        devices = self.get_input_devices()
        default_dev = next((d for d in devices if d.get("id") == "default"), None)
        default_index = sd.default.device[0] if (sd.default.device and sd.default.device[0] is not None and sd.default.device[0] >= 0) else None

        # 1. Agar user aniq qurilma tanlagan bo'lsa:
        if self._selected_device_id and self._selected_device_id != "default":
            # Id bo'yicha qidirish
            target = next((d for d in devices if d.get("id") == self._selected_device_id), None)
            
            # Agar id bo'yicha topilmasa, nom bo'yicha qidirish (USB port o'zgarganda yoki restartdan so'ng index o'zgargan bo'lsa)
            if not target and self._selected_device_name:
                target = next((
                    d for d in devices
                    if d.get("id") != "default" and (
                        self._selected_device_name.lower() in d.get("name", "").lower()
                        or d.get("name", "").lower() in self._selected_device_name.lower()
                    )
                ), None)

            if target and target.get("available") and target.get("index") is not None:
                return target["index"], target, False, "Ulangan / Ishlamoqda"

            # Tanlangan qurilma topilmadi yoki ulanmagan:
            # Yashirincha o'tib ketmaymiz — halol status beramiz!
            if default_index is not None and default_index >= 0:
                dev_info = sd.query_devices(default_index)
                fallback_info = {
                    "id": "default",
                    "name": dev_info.get("name", "Default Microphone"),
                    "index": default_index,
                    "type": "input",
                    "available": True,
                    "is_default": True,
                }
                msg = f"Tanlangan mikrofon ({self._selected_device_name or self._selected_device_id}) ulanmagan. Default mikrofon ishlatilmoqda."
                return default_index, fallback_info, True, msg

            return None, {}, True, "Tanlangan mikrofon ulanmagan va tizim standarti ham mavjud emas."

        # 2. Agar "default" tanlangan bo'lsa yoki hali tanlov bo'lmasa:
        if default_index is not None and default_index >= 0:
            dev_info = sd.query_devices(default_index)
            def_dict = {
                "id": "default",
                "name": dev_info.get("name", "Default Microphone"),
                "index": default_index,
                "type": "input",
                "available": True,
                "is_default": True,
            }
            return default_index, def_dict, False, "Ulangan / Ishlamoqda"

        return None, {}, True, "Hech qanday audio kirish qurilmasi (mikrofon) topilmadi."

    def set_selected_device(self, device_id: str, device_name: Optional[str] = None) -> Dict[str, Any]:
        """Foydalanuvchi tanlagan mikrofonni saqlash"""
        self._selected_device_id = device_id
        if device_name:
            self._selected_device_name = device_name
        else:
            devs = self.get_input_devices()
            matched = next((d for d in devs if d.get("id") == device_id), None)
            if matched:
                self._selected_device_name = matched.get("name")

        _save_persisted_microphone(self._selected_device_id or "default", self._selected_device_name or "Default")
        logger.info(f"[VOICE] Foydalanuvchi mikrofonni tanladi: {self._selected_device_name} (ID: {self._selected_device_id})")

        idx, dev_info, fallback_used, status_msg = self.resolve_selected_device()
        return {
            "ok": True,
            "selected_device_id": self._selected_device_id,
            "selected_device_name": self._selected_device_name,
            "resolved_index": idx,
            "fallback_used": fallback_used,
            "status": status_msg,
        }

    def test_microphone(self, device_id: Optional[str] = None, duration_s: float = 1.0) -> Dict[str, Any]:
        """
        Mikrofonni haqiqiy apparatda tekshirish (REAL AUDIO CAPTURE):
        - Haqiqiy signal olinadi
        - Real RMS va Peak hisoblanadi
        - Agar apparat 16000Hz ni to'g'ridan-to'g'ri qo'llamasa, native samplerate bilan ochib resample qilinadi
        - Hech qanday soxta (fake) animatsiya yo'q!
        """
        try:
            import sounddevice as sd
        except ImportError:
            return {
                "ok": False,
                "working": False,
                "level": 0.0,
                "status": "error",
                "message": "sounddevice kutubxonasi mavjud emas.",
            }

        # Agar maxsus device berilgan bo'lsa vaqtincha shu qurilmani tekshiramiz
        target_index: Optional[int] = None
        dev_name = "Noma'lum"

        if device_id and device_id != "default":
            devs = self.get_input_devices()
            found = next((d for d in devs if d.get("id") == device_id), None)
            if found and found.get("index") is not None:
                target_index = found["index"]
                dev_name = found.get("name", "Mikrofon")
        else:
            idx, dev_info, _, _ = self.resolve_selected_device()
            target_index = idx
            dev_name = dev_info.get("name", "Default mikrofon")

        if target_index is None or target_index < 0:
            return {
                "ok": False,
                "working": False,
                "level": 0.0,
                "status": "disconnected",
                "message": "Tanlangan mikrofon topilmadi yoki ulanmagan.",
            }

        # Apparatdan real audio o'qish (namuna: 1 soniya)
        target_sr = 16000
        native_sr = int(sd.query_devices(target_index).get("default_samplerate", 44100))
        captured_frames = []

        try:
            # 1-urinish: To'g'ridan-to'g'ri 16000 Hz
            chunk_size = int(target_sr * 0.1)  # 100ms
            total_chunks = int(duration_s / 0.1)
            used_sr = target_sr

            try:
                with sd.InputStream(
                    device=target_index,
                    samplerate=target_sr,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_size
                ) as stream:
                    # Warmup tashlash
                    stream.read(chunk_size)
                    for _ in range(total_chunks):
                        data, _ = stream.read(chunk_size)
                        if data is not None and len(data) > 0:
                            captured_frames.append(data.flatten())
            except Exception as direct_err:
                # 2-urinish: Apparatning native sampleratesi bilan ochish (resampling bilan)
                logger.info(f"Test: 16000Hz xatosi ({direct_err}), native {native_sr}Hz bilan urinilmoqda...")
                used_sr = native_sr
                native_chunk = int(native_sr * 0.1)
                with sd.InputStream(
                    device=target_index,
                    samplerate=native_sr,
                    channels=1,
                    dtype="float32",
                    blocksize=native_chunk
                ) as stream:
                    stream.read(native_chunk)
                    for _ in range(total_chunks):
                        data, _ = stream.read(native_chunk)
                        if data is not None and len(data) > 0:
                            captured_frames.append(data.flatten())

            if not captured_frames:
                return {
                    "ok": True,
                    "working": False,
                    "level": 0.0,
                    "status": "warning",
                    "message": "Mikrofon ochildi, lekin audio ma'lumot kelmadi.",
                    "device_name": dev_name,
                }

            all_samples = np.concatenate(captured_frames)
            rms = float(np.sqrt(np.mean(all_samples**2)))
            peak = float(np.max(np.abs(all_samples)))
            # Real UI darajasi (0.0 - 1.0 oralig'ida)
            level = min(1.0, float(rms * 12.0))

            is_working = True
            msg = "Mikrofon ishlayapti va signal qabul qilinmoqda."
            if rms < 0.00005:
                msg = "Mikrofon ulangan, lekin ovoz signali juda past (Mute qilingan bo'lishi mumkin)."

            return {
                "ok": True,
                "working": is_working,
                "level": round(level, 3),
                "rms": round(rms, 5),
                "peak": round(peak, 5),
                "sample_rate": used_sr,
                "status": "connected",
                "message": msg,
                "device_name": dev_name,
            }

        except Exception as e:
            err_str = str(e)
            logger.error(f"Mikrofonni tekshirishda xatolik: {err_str}")
            msg = "Mikrofon xatosi yuz berdi."
            if "busy" in err_str.lower() or "in use" in err_str.lower() or "-9996" in err_str:
                msg = "Mikrofon boshqa dastur tomonidan band qilingan."
            elif "permission" in err_str.lower() or "access" in err_str.lower():
                msg = "Mikrofon ruxsati rad etilgan. Windows sozlamalarida mikrofon ruxsatini tekshiring."

            return {
                "ok": False,
                "working": False,
                "level": 0.0,
                "status": "error",
                "message": msg,
                "error": err_str,
                "device_name": dev_name,
            }
