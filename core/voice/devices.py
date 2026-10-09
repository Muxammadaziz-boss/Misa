# -*- coding: utf-8 -*-
"""
Misa AI — Universal Audio Capture & Microphone Device Manager
Windows audio kirish qurilmalarini dinamik aniqlash (dynamic enumeration),
har qanday apparat (USB mikrofonlar, tashqi audio interfeyslar, o'rnatilgan mikrofonlar,
veb-kameralar, bluetooth/headsetlar) uchun barqaror identifikatsiya, hot-plug refresh,
tanlovni xotirada saqlash (persistence), xavfsiz fallback va real apparatda test qilish.
"""

import os
import json
import logging
import threading
import hashlib
import re
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("MicrophoneManager")

# Config fayli
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

# Virtual Windows drayver dublikatlari (bular "Tizim standarti" opsiya orqali qamrab olinadi)
VIRTUAL_MAPPER_NAMES = {
    "microsoft sound mapper - input",
    "primary sound capture driver",
}


def _normalize_device_name(raw_name: str) -> str:
    """Windows MME 31-belgilik chegarasi tufayli kesilib qolgan qavslarni tuzatish"""
    name = raw_name.strip()
    if name.endswith("(") or (name.count("(") > name.count(")")):
        name = name.rstrip("(")
        name = name + ")"
    return name


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
    Windows tizimidagi audio input qurilmalarini universal boshqarish:
    - Barcha haqiqiy capture qurilmalarni dinamik topish (output/speaker qurilmalar qat'iy kiritilmaydi)
    - Hot-plug qo'llab-quvvatlash (yangi ulangan mikrofonlarni aniqlash va uzilganlarini ko'rsatish)
    - Barqaror (stable) identifikatorlar orqali tanlovni saqlash
    - Fallback siyosati: tanlangan qurilma uzilgan bo'lsa, foydalanuvchiga halol status bilan Defaultga o'tish
    - Universal apparat moslashuvi (turli sample rate va kanallarni avtomatik 16kHz monoga moslashtirish)
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

    def refresh_devices(self) -> List[Dict[str, Any]]:
        """
        Hot-plug qo'llab-quvvatlashi:
        PortAudio quyi tizimini qayta initsializatsiya qilib, yangi ulangan yoki
        uzilgan Windows audio qurilmalarini to'liq yangidan skanerlash.
        """
        try:
            import sounddevice as sd
            sd._terminate()
            sd._initialize()
            logger.info("[MicrophoneManager] PortAudio muvaffaqiyatli qayta initsializatsiya qilindi (hot-plug refresh)")
        except Exception as e:
            logger.warning(f"[MicrophoneManager] PortAudio qayta initsializatsiyasida xatolik: {e}")
        return self.get_input_devices(force_refresh=False)

    def get_input_devices(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Windows'dagi barcha haqiqiy AUDIO INPUT (capture) qurilmalarini dinamik aniqlash.
        Output/speaker qurilmalari qat'iy chiqarib tashlanadi.
        Virtual drayver dublikatlari tozalanadi va har bir jismoniy qurilma uchun
        barqaror (stable) identifikator hosil qilinadi.
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice o'rnatilmagan")
            return []

        if force_refresh:
            try:
                sd._terminate()
                sd._initialize()
            except Exception:
                pass

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

        # Jismoniy kirish qurilmalarini saralash
        # Host API ustuvorligi: DirectSound (1) > MME (0) > WASAPI (3). WDM-KS (4) chiqariladi.
        seen_groups: Dict[str, Dict[str, Any]] = {}

        for idx, d in enumerate(raw_devices):
            max_in = d.get("max_input_channels", 0)
            if max_in <= 0:
                continue  # Faqat input qurilmalar! Chiqish karnaylari qat'iy chiqariladi.

            raw_name = str(d.get("name", "")).strip()
            if not raw_name:
                continue

            low_name = raw_name.lower()
            if low_name in VIRTUAL_MAPPER_NAMES:
                continue  # Virtual sound mapperlar "default" parametri orqali qamralgan

            host_api = d.get("hostapi", 0)
            if host_api == 4:
                continue  # WDM-KS exclusive rejim talab qiladi, umumiy oqimlar uchun tavsiya etilmaydi

            norm_name = _normalize_device_name(raw_name)
            group_key = re.sub(r'\s+', ' ', norm_name.lower()).rstrip(')')
            stable_id = f"input_{hashlib.sha256(group_key.encode('utf-8')).hexdigest()[:10]}"

            # DirectSound (1) > MME (0) > WASAPI (3)
            priority = 3 if host_api == 1 else (2 if host_api == 0 else 1)

            if group_key not in seen_groups or priority > seen_groups[group_key]["priority"]:
                seen_groups[group_key] = {
                    "priority": priority,
                    "data": {
                        "id": stable_id,
                        "name": norm_name,
                        "type": "input",
                        "available": True,
                        "is_default": (idx == default_input_idx),
                        "index": idx,
                        "host_api": host_api,
                        "channels": max_in,
                        "sample_rate": int(d.get("default_samplerate", 16000)),
                    }
                }

        for g in seen_groups.values():
            devices_list.append(g["data"])

        # Agar oldin saqlangan tanlangan qurilma hozirgi ulangan qurilmalar orasida bo'lmasa,
        # ro'yxatga "available: False" sifatida qo'shamiz (Foydalanuvchi uzilganini aniq ko'rishi uchun)
        if self._selected_device_id and self._selected_device_id != "default":
            exists = any(d["id"] == self._selected_device_id for d in devices_list)
            if not exists:
                devices_list.append({
                    "id": self._selected_device_id,
                    "name": self._selected_device_name or "Tanlangan mikrofon",
                    "type": "input",
                    "available": False,
                    "is_default": False,
                    "index": None,
                    "description": "Ushbu mikrofon hozirda kompyuterga ulanmagan",
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
        default_index = sd.default.device[0] if (sd.default.device and sd.default.device[0] is not None and sd.default.device[0] >= 0) else None

        # 1. Agar user aniq qurilma tanlagan bo'lsa:
        if self._selected_device_id and self._selected_device_id != "default":
            # Id bo'yicha qidirish
            target = next((d for d in devices if d.get("id") == self._selected_device_id), None)
            
            # Agar id bo'yicha topilmasa, nom bo'yicha qidirish (USB port o'zgarganda yoki hot-plugdan so'ng)
            if not target and self._selected_device_name:
                target = next((
                    d for d in devices
                    if d.get("id") != "default" and d.get("available") and (
                        self._selected_device_name.lower() in d.get("name", "").lower()
                        or d.get("name", "").lower() in self._selected_device_name.lower()
                    )
                ), None)

            if target and target.get("available") and target.get("index") is not None:
                return target["index"], target, False, "Ulangan / Ishlamoqda"

            # Tanlangan qurilma ulanmagan:
            # Aniq halol ogohlantirish bilan Default ga o'tish (Requirement 9)
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
            "message": status_msg,
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

        target_index: Optional[int] = None
        dev_name = "Noma'lum"

        if device_id and device_id != "default":
            devs = self.get_input_devices()
            found = next((d for d in devs if d.get("id") == device_id), None)
            if found and found.get("available") and found.get("index") is not None:
                target_index = found["index"]
                dev_name = found.get("name", "Mikrofon")
            elif found and not found.get("available"):
                return {
                    "ok": False,
                    "working": False,
                    "level": 0.0,
                    "status": "disconnected",
                    "device_name": found.get("name", "Mikrofon"),
                    "message": f"Tanlangan mikrofon ({found.get('name')}) audio portga ulanmagan.",
                }
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
                "device_name": dev_name,
                "message": f"Tanlangan mikrofon ({dev_name}) topilmadi yoki ulanmagan.",
            }

        # Apparatdan real audio o'qish
        target_sr = 16000
        native_sr = int(sd.query_devices(target_index).get("default_samplerate", 44100))
        captured_frames = []

        try:
            # 1-urinish: To'g'ridan-to'g'ri 16000 Hz
            chunk_size = int(target_sr * 0.1)  # 100ms
            total_chunks = max(1, int(duration_s / 0.1))
            used_sr = target_sr

            try:
                with sd.InputStream(
                    device=target_index,
                    samplerate=target_sr,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_size,
                ) as stream:
                    for _ in range(total_chunks):
                        data, overflow = stream.read(chunk_size)
                        if len(data) > 0:
                            captured_frames.append(data.copy())
            except Exception as e_16k:
                logger.info(f"16000Hz to'g'ridan-to'g'ri ochilmadi ({e_16k}), native {native_sr}Hz ga o'tilmoqda")
                # 2-urinish: Native samplerate bilan ochib resample qilish
                used_sr = native_sr
                chunk_native = int(native_sr * 0.1)
                with sd.InputStream(
                    device=target_index,
                    samplerate=native_sr,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_native,
                ) as stream:
                    for _ in range(total_chunks):
                        data, overflow = stream.read(chunk_native)
                        if len(data) > 0:
                            captured_frames.append(data.copy())

            if not captured_frames:
                return {
                    "ok": False,
                    "working": False,
                    "level": 0.0,
                    "status": "warning",
                    "device_name": dev_name,
                    "message": "Mikrofondan audio signali qabul qilinmadi.",
                }

            all_audio = np.concatenate(captured_frames, axis=0).flatten()
            rms = float(np.sqrt(np.mean(np.square(all_audio))))
            peak = float(np.max(np.abs(all_audio)))

            # Signal darajasi (0.0 - 1.0)
            level = min(1.0, max(0.0, peak if peak > 0 else rms * 3.0))

            return {
                "ok": True,
                "working": True,
                "level": round(level, 3),
                "rms": round(rms, 4),
                "peak": round(peak, 4),
                "status": "connected",
                "device_name": dev_name,
                "device_id": device_id or self._selected_device_id or "default",
                "sample_rate": used_sr,
                "message": f"Mikrofon muvaffaqiyatli sinovdan o'tdi (RMS: {round(rms, 3)})",
            }

        except Exception as e:
            err_str = str(e)
            logger.error(f"Mikrofonni sinashda apparat xatoligi: {e}")
            if "busy" in err_str.lower() or "in use" in err_str.lower():
                msg = "Mikrofon boshqa dastur tomonidan band qilingan."
            elif "permission" in err_str.lower() or "denied" in err_str.lower():
                msg = "Mikrofon ruxsati berilmagan."
            else:
                msg = f"Mikrofonni ochib bo'lmadi: {err_str}"
            return {
                "ok": False,
                "working": False,
                "level": 0.0,
                "status": "error",
                "device_name": dev_name,
                "message": msg,
                "error": err_str,
            }
