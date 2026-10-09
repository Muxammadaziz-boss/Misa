# ========== main.py ===============================
# Misa AI — Shaxsiy sun'iy intellekt yordamchi
# Versiya: 8.0.0
# ========== Ogohlantirishlarni yashirish ==========

VERSION = "9.0.1"
APP_NAME = "Misa AI"
import os
import sys
import logging

if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import webbrowser
import urllib.request
from urllib.parse import quote_plus
from config import get_config, get_logger

# Logging sozlash
logger = get_logger(__name__)

# Logging — config.py da boshqariladi, dublikat qo'shmaymiz
# (config.py allaqachon absl, google.auth, urllib3 ni o'chirgan)

# ========== Asosiy importlar ==========
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np

    SPEECH_AVAILABLE = True
except ImportError:
    sd = None
    sf = None
    np = None
    SPEECH_AVAILABLE = False
    print(
        "WARNING: sounddevice/soundfile modullari topilmadi. Ovozli mikrofon ishlamaydi."
    )

try:
    import speech_recognition as sr

    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None
    SPEECH_RECOGNITION_AVAILABLE = False
    print("WARNING: speech_recognition moduli topilmadi. Ovozli mikrofon ishlamaydi.")

_pyaudio_checked = False
_pyaudio_missing_warned = False

import asyncio  # Standart kutubxona — har doim mavjud

try:
    import edge_tts

    TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    TTS_AVAILABLE = False
    print("WARNING: edge-tts moduli topilmadi. Ovozli javob ishlamaydi.")

import threading
import time
import subprocess
import requests
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog, ttk
import datetime
try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import psutil
except ImportError:
    psutil = None

try:
    import keyboard
except ImportError:
    keyboard = None

import uuid
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from core.ai_engine import (
        ai_savol_yuborish,
        ai_mavjudmi,
        suhbat_tarixini_tozalash,
        ekran_tahlil,
        ekran_element_top,
        buyruq_tekshir,
    )

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("WARNING: ai_engine.py topilmadi. AI integratsiya ishlamaydi.")
# import google.generativeai as genai  # AI integratsiya uchun kerak emas
import re

try:
    from core.smart_algorithms import (
        algoritmlarni_tayyorla,
        aqlli_buyruq_aniqla,
        keyingi_bashorat,
        get_cache,
        get_bashorat,
        get_gemini_limiter,
        get_openrouter_limiter,
        statistika as algo_statistika,
        xavfli_buyruqmi,
        buyruq_prioriteti,
        XAVFLI_BUYRUQLAR,
    )

    SMART_ALGO_AVAILABLE = True
except ImportError:
    SMART_ALGO_AVAILABLE = False
    print("WARNING: smart_algorithms.py topilmadi. Oddiy regex ishlaydi.")

# ========== Agent modullari ==========
try:
    from core.agent_tools import get_registry
    from core.agent_planner import ReActAgent
    from core.agent_memory import AgentMemory
    from core.agent_plugins import get_plugin_manager, get_proactive_agent
    from core.proactive_watcher import start_proactive_watcher, stop_proactive_watcher

    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False
    print("WARNING: Agent modullari topilmadi. Oddiy AI ishlaydi.")

# ========== v6.0.0 Audio Service va Command Dispatcher ==========
try:
    from core.audio_service import get_audio_service, AudioService
    AUDIO_SERVICE_AVAILABLE = True
except ImportError:
    AUDIO_SERVICE_AVAILABLE = False

try:
    from core.command_dispatcher import CommandDispatcher
    COMMAND_DISPATCHER_AVAILABLE = True
    command_dispatcher = CommandDispatcher()
except ImportError:
    COMMAND_DISPATCHER_AVAILABLE = False
    command_dispatcher = None
import tempfile
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    PYCAW_AVAILABLE = True
except ImportError:
    AudioUtilities = None
    IAudioEndpointVolume = None
    cast = None
    POINTER = None
    CLSCTX_ALL = None
    PYCAW_AVAILABLE = False
# logging allaqachon 9-qatorda import qilingan

# Logging config.py da boshqariladi (Config.setup_logging())
# Qo'shimcha handler qo'shish shart emas

# ========== Versiya ==========
# VERSION allaqachon 6-qatorda belgilangan ("3.1.0")

# ========== Asosiy papka yo'li (xavfsiz) ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ========== NirCmd yo'li ==========
NIRCMD_PATH = os.path.join(BASE_DIR, "nircmd.exe")

# ========== Global o'zgaruvchilar va thread-safety ==========
from threading import RLock


class GlobalState:
    """Thread-safe global holat klassi"""

    def __init__(self):
        self._lock = RLock()
        self._buyruq_bajarilmoqda = False
        self._so_ngi_natija = ""
        self._ovoz_turi_global = "erkak"
        self._gui_callback = None
        self._youtube_ochiq = False
        self._tinglash_faol = False
        self._tts_engine = None
        self._tts_failed = False
        self._gapirmoqda = False
        self._oxirgi_gapirish_vaqti = 0

    @property
    def buyruq_bajarilmoqda_lock(self):
        return self._lock

    @property
    def buyruq_bajarilmoqda(self):
        with self._lock:
            return self._buyruq_bajarilmoqda

    @buyruq_bajarilmoqda.setter
    def buyruq_bajarilmoqda(self, value):
        with self._lock:
            self._buyruq_bajarilmoqda = value

    @property
    def so_ngi_natija(self):
        with self._lock:
            return self._so_ngi_natija

    @so_ngi_natija.setter
    def so_ngi_natija(self, value):
        with self._lock:
            self._so_ngi_natija = value

    @property
    def ovoz_turi_global(self):
        with self._lock:
            return self._ovoz_turi_global

    @ovoz_turi_global.setter
    def ovoz_turi_global(self, value):
        with self._lock:
            self._ovoz_turi_global = value

    @property
    def gui_callback(self):
        with self._lock:
            return self._gui_callback

    @gui_callback.setter
    def gui_callback(self, value):
        with self._lock:
            self._gui_callback = value

    @property
    def youtube_ochiq(self):
        with self._lock:
            return self._youtube_ochiq

    @youtube_ochiq.setter
    def youtube_ochiq(self, value):
        with self._lock:
            self._youtube_ochiq = value

    @property
    def tinglash_faol(self):
        with self._lock:
            return self._tinglash_faol

    @tinglash_faol.setter
    def tinglash_faol(self, value):
        with self._lock:
            self._tinglash_faol = value

    @property
    def tts_engine(self):
        with self._lock:
            return self._tts_engine

    @tts_engine.setter
    def tts_engine(self, value):
        with self._lock:
            self._tts_engine = value

    @property
    def tts_failed(self):
        with self._lock:
            return self._tts_failed

    @tts_failed.setter
    def tts_failed(self, value):
        with self._lock:
            self._tts_failed = value

    @property
    def gapirmoqda(self):
        with self._lock:
            return self._gapirmoqda

    @gapirmoqda.setter
    def gapirmoqda(self, value):
        with self._lock:
            self._gapirmoqda = value

    @property
    def oxirgi_gapirish_vaqti(self):
        with self._lock:
            return self._oxirgi_gapirish_vaqti

    @oxirgi_gapirish_vaqti.setter
    def oxirgi_gapirish_vaqti(self, value):
        with self._lock:
            self._oxirgi_gapirish_vaqti = value


# Global holat obyekti
global_state = GlobalState()


# ========== GUI bilan integratsiya ==========
def gui_bilan_integratsiya(callback_func):
    global_state.gui_callback = callback_func


def gui_ga_xabar_yuborish(xabar, ovoz=False):
    """GUI ga xabar yuborish. ovoz=True bo'lsa ovozli aytadi"""
    callback = global_state.gui_callback
    if callback:
        try:
            callback(xabar)
        except Exception as e:
            print(f"GUI callback xatolik: {e}")
            print(xabar)
    else:
        print(xabar)

    # Agar ovoz kerak bo'lsa
    if ovoz:
        ovoz_xabar = xabar
        # Emoji va vaqt belgisini olib tashlash
        ovoz_xabar = re.sub(r"\[.*?\]", "", ovoz_xabar)  # [12:30:45]
        ovoz_xabar = re.sub(
            r"[🎤🗣️📝🎯✅❌⚠️💡📊🎵▶️⏸️🔊🔉🔇📌🤖]", "", ovoz_xabar
        )  # Emojlar
        ovoz_xabar = ovoz_xabar.strip()
        if ovoz_xabar:
            ovoz_chiqar_tez(ovoz_xabar)


# ========== TTS Engine (tts_manager.py boshqaradi) ==========
# get_tts_engine(), _tts_engine, _tts_failed — olib tashlandi (dead code edi)


# ========== Ovozli javob berish ==========
def kayfiyat_aniqla(matn):
    """Matn kayfiyatini aniqlash va SSML prosody parametrlari qaytarish"""
    matn_kichik = matn.lower()

    # Kayfiyat so'zlari
    XURSAND = [
        "ajoyib",
        "zo'r",
        "yaxshi",
        "barakalla",
        "tabriklayman",
        "salom",
        "rahmat",
        "marhamat",
        "qoyil",
        "chiroyli",
        "sevaman",
        "ishga tushdi",
        "tayyor",
        "ochildi",
        "muvaffaqiyat",
        "ishladi",
        "to'g'ri",
        "ha!",
        "super",
        "shunday",
    ]
    GAMGIN = [
        "kechirasiz",
        "uzr",
        "afsuski",
        "xato",
        "muammo",
        "topilmadi",
        "ishlamadi",
        "buzildi",
        "yo'q",
        "olmadi",
        "xatolik",
        "muvaffaqiyatsiz",
        "qiyin",
    ]
    HAYAJON = [
        "voy",
        "qara",
        "tezroq",
        "shoshiling",
        "muhim",
        "diqqat",
        "ehtiyot",
        "tez",
        "iltimos",
        "shart",
        "darrov",
        "keling",
    ]
    JIDDIY = [
        "eslatma",
        "ogohlantirish",
        "xavfsizlik",
        "parol",
        "o'chirish",
        "qulflash",
        "o'chirildi",
        "yopildi",
        "to'xtatildi",
        "bloklandi",
    ]
    ILIQ = [
        "yoqimli",
        "salqin",
        "sayir",
        "dam ol",
        "choy",
        "kurtka",
        "issiq",
        "havo",
        "daraja",
        "ob-havo",
        "bulutli",
        "quyosh",
        "yomg'ir",
    ]
    XAVOTIR = [
        "sovuq",
        "momaqaldiroq",
        "kuchli",
        "bo'ron",
        "ehtiyot bo'ling",
        "soyabon",
        "iliq kiyining",
        "juda issiq",
        "juda sovuq",
    ]

    # Kayfiyatni aniqlash
    ball = {
        "xursand": 0,
        "gamgin": 0,
        "hayajon": 0,
        "jiddiy": 0,
        "iliq": 0,
        "xavotir": 0,
    }

    for soz in XURSAND:
        # So'z chegarasini tekshirish — "ha" "shahar" ichida topilmasin
        if re.search(r"\b" + re.escape(soz) + r"\b", matn_kichik):
            ball["xursand"] += 1
    for soz in GAMGIN:
        if re.search(r"\b" + re.escape(soz) + r"\b", matn_kichik):
            ball["gamgin"] += 1
    for soz in HAYAJON:
        if re.search(r"\b" + re.escape(soz) + r"\b", matn_kichik):
            ball["hayajon"] += 1
    for soz in JIDDIY:
        if re.search(r"\b" + re.escape(soz) + r"\b", matn_kichik):
            ball["jiddiy"] += 1
    for soz in ILIQ:
        if re.search(r"\b" + re.escape(soz) + r"\b", matn_kichik):
            ball["iliq"] += 1
    for soz in XAVOTIR:
        if re.search(r"\b" + re.escape(soz) + r"\b", matn_kichik):
            ball["xavotir"] += 1

    # Undov va so'roq belgilari — mavjud kayfiyatni kuchaytiradi
    if "!" in matn:
        # Eng kuchli kayfiyatni kuchaytirish (hayajon emas har doim)
        dominant = max(ball, key=ball.get)
        if ball[dominant] > 0:
            ball[dominant] += 1  # Mavjud kayfiyatni kuchaytirish
        else:
            ball["xursand"] += 1  # Standart — xursand
    if "?" in matn:
        ball["iliq"] += 1

    # Eng yuqori kayfiyat
    kayfiyat = max(ball, key=ball.get)
    if ball[kayfiyat] == 0:
        kayfiyat = "oddiy"

    # Prosody parametrlari: rate, pitch, volume
    PROSODY = {
        "xursand": ("+12%", "+8Hz", "+5%"),  # Tez va baland — xursand ohang
        "gamgin": ("-15%", "-6Hz", "-5%"),  # Sekin va past — g'amgin, muloyim
        "hayajon": ("+18%", "+12Hz", "+8%"),  # Juda tez va baland — hayajonli
        "jiddiy": ("-5%", "-3Hz", "+0%"),  # Biroz sekin — jiddiy, rasmiy
        "iliq": ("-8%", "+3Hz", "+0%"),  # Sekinroq, biroz baland — iliq, do'stona
        "xavotir": ("+5%", "-2Hz", "+3%"),  # Biroz tez — xavotirli
        "oddiy": ("+0%", "+0Hz", "+0%"),  # Oddiy
    }

    rate, pitch, volume = PROSODY.get(kayfiyat, PROSODY["oddiy"])
    logging.debug(f"Kayfiyat: {kayfiyat} (ball: {ball}) → rate={rate}, pitch={pitch}")
    return rate, pitch, volume


def ovoz_chiqar_tez(text, ovoz_turi=None):
    """
    Misa AI 9.0.0 — Yuqori sifatli va barqaror TTS audio ijrosi.
    Edge TTS (uz-UZ-MadinaNeural / uz-UZ-SardorNeural) orqali ovoz yaratadi
    va Windows Native MCI (winmm.dll), pygame yoki sounddevice orqali
    foydalanuvchining asosiy audio qurilmasida (karnay/naushnik/monitor) ijro etadi.
    """
    if not text:
        return

    def _ijro_et():
        import ctypes
        try:
            global_state.gapirmoqda = True
            logging.info(f"Ovoz chiqarish boshlandi: {text[:80]}")

            # 1. Matnni keraksiz belgilardan tozalash (Markdown, URL, emojilar)
            clean_text = re.sub(r"\[.*?\]\(.*?\)", "", text)  # Markdown linklar
            clean_text = re.sub(r"```[\s\S]*?```", "", clean_text)  # Code blocklar
            clean_text = re.sub(r"`.*?`", "", clean_text)  # Inline code
            clean_text = re.sub(r"[\*\_~#>]", "", clean_text)  # Markdown format
            clean_text = re.sub(r"[🎤🗣️📝🎯✅❌⚠️💡📊🎵▶️⏸️🔊🔉🔇📌🤖✨🔹👋]", "", clean_text)
            clean_text = clean_text.strip()

            if not clean_text:
                return

            sentences = [s.strip() for s in re.split(r"[.!?\n।]+", clean_text) if s.strip()]
            if not sentences:
                sentences = [clean_text]

            # 2. Ovoz turini aniqlash (barcha modellar: Edge-TTS, Fish Audio, RVC)
            target_ovoz = ovoz_turi or getattr(global_state, "ovoz_turi_global", None)
            if not target_ovoz:
                fayl = os.path.join(BASE_DIR, "data", "ovoz_turi.txt")
                if os.path.exists(fayl):
                    try:
                        with open(fayl, "r", encoding="utf-8") as f:
                            v = f.read().strip()
                            if v:
                                target_ovoz = v
                    except Exception:
                        pass

            if not target_ovoz:
                target_ovoz = "ayol"

            # 3. Unified VoiceEngine orqali ijro etish
            try:
                from core.voice_engine import play_speech_sync
                if play_speech_sync(clean_text, voice_type=target_ovoz):
                    return
            except Exception as e:
                logging.debug(f"VoiceEngine ijro xatosi, mahalliy fallbackga o'tilmoqda: {e}")

            voice = "uz-UZ-MadinaNeural" if target_ovoz in ["ayol", "madina", "fish_anime", "ashley", "yukari"] else "uz-UZ-SardorNeural"

            # 3. Tezlik (speed) ni config.json dan olish
            speed_mult = 1.0
            try:
                from config import get_config
                cfg_speed = get_config("audio.tts_speed")
                if cfg_speed is not None:
                    speed_mult = float(cfg_speed)
            except Exception:
                speed_mult = 1.0

            speed_pct = int((speed_mult - 1.0) * 100)
            sign = "+" if speed_pct >= 0 else ""
            rate_str = f"{sign}{speed_pct}%"

            async def _speak():
                import edge_tts

                for sentence in sentences:
                    if not global_state.gapirmoqda:
                        break

                    filename = os.path.join(
                        tempfile.gettempdir(), f"misa_tts_{uuid.uuid4().hex}.mp3"
                    )
                    try:
                        communicate = edge_tts.Communicate(
                            sentence, voice, rate=rate_str, volume="+0%"
                        )
                        await communicate.save(filename)

                        played = False

                        # 1-variant: Windows Native MCI (winmm.dll) — Eng barqaror va tizim default qurilmasiga to'g'ridan-to'g'ri uzatuvchi
                        try:
                            alias = f"misa_{uuid.uuid4().hex[:8]}"
                            winmm = ctypes.windll.winmm
                            r_open = winmm.mciSendStringW(f'open "{filename}" type mpegvideo alias {alias}', None, 0, 0)
                            if r_open == 0:
                                winmm.mciSendStringW(f'play {alias}', None, 0, 0)
                                status_buf = ctypes.create_unicode_buffer(64)
                                while global_state.gapirmoqda:
                                    winmm.mciSendStringW(f'status {alias} mode', status_buf, 64, 0)
                                    if status_buf.value != "playing":
                                        break
                                    await asyncio.sleep(0.04)
                                winmm.mciSendStringW(f'stop {alias}', None, 0, 0)
                                winmm.mciSendStringW(f'close {alias}', None, 0, 0)
                                played = True
                        except Exception as e:
                            logging.debug(f"winmm ijro xatosi: {e}")

                        # 2-variant: Pygame fallback
                        if not played and global_state.gapirmoqda:
                            try:
                                import pygame
                                if not pygame.mixer.get_init():
                                    pygame.mixer.init(frequency=24000)
                                pygame.mixer.music.load(filename)
                                pygame.mixer.music.play()
                                while pygame.mixer.music.get_busy() and global_state.gapirmoqda:
                                    await asyncio.sleep(0.04)
                                pygame.mixer.music.stop()
                                pygame.mixer.music.unload()
                                played = True
                            except Exception as e:
                                logging.warning(f"Pygame ijro xatosi: {e}")

                        # 3-variant: sounddevice fallback
                        if not played and global_state.gapirmoqda:
                            try:
                                import soundfile as sf
                                import sounddevice as sd
                                data, fs = sf.read(filename)
                                sd.play(data, fs)
                                sd.wait()
                                played = True
                            except Exception as e:
                                logging.debug(f"sounddevice ijro xatosi: {e}")

                    except Exception as e:
                        logging.error(f"TTS generatsiya yoki ijro xatosi: {e}")
                    finally:
                        try:
                            if os.path.exists(filename):
                                os.remove(filename)
                        except Exception:
                            pass

            try:
                asyncio.run(_speak())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_speak())
                finally:
                    loop.close()

        except Exception as e:
            logging.error(f"Audio execution error: {e}")
            print(f"Ovoz xatolik: {e}")
        finally:
            global_state.oxirgi_gapirish_vaqti = time.time()
            global_state.gapirmoqda = False
            logging.info("Ovoz ijrosi yakunlandi")

    threading.Thread(target=_ijro_et, daemon=True, name="TTSPlaybackThread").start()


# ========== Foydalanuvchi ma'lumotlarini olish ==========
def foydalanuvchi_ismi_ol():
    """Foydalanuvchi ismini config.json dan olish (eski txt fayldan migratsiya)"""
    from config import get_config, set_config

    # Avval config.json dan tekshirish
    ism = get_config("user.name")
    if ism:
        return ism

    # Eski txt fayldan migratsiya (bir martalik)
    fayl = os.path.join(BASE_DIR, "data", "foydalanuvchi_ismi.txt")
    if os.path.exists(fayl):
        try:
            with open(fayl, "r", encoding="utf-8") as f:
                ism = f.read().strip()
            if ism:
                set_config("user.name", ism)
                logging.info(
                    f"Foydalanuvchi ismi txt dan config.json ga ko'chirildi: {ism}"
                )
                return ism
        except Exception:
            pass

    # Hech qayerda yo'q — so'rash
    root = tk.Tk()
    root.withdraw()
    ism = simpledialog.askstring("Ism", "Iltimos, ismingizni kiriting:")
    root.destroy()
    if ism:
        ism = re.sub(r"[^\w\s]", "", ism).strip()
        set_config("user.name", ism)
        return ism
    return "Foydalanuvchi"


def ovoz_turi_ol():
    """Ovoz turini config.json dan olish (eski txt fayldan migratsiya)"""
    from config import get_config, set_config

    # Avval config.json dan tekshirish
    ovoz = get_config("user.voice_type")
    if ovoz:
        return ovoz

    # Eski txt fayldan migratsiya
    fayl = os.path.join(BASE_DIR, "data", "ovoz_turi.txt")
    if os.path.exists(fayl):
        try:
            with open(fayl, "r", encoding="utf-8") as f:
                ovoz = f.read().strip()
            if ovoz and ovoz.lower() in ["erkak", "ayol"]:
                set_config("user.voice_type", ovoz.lower())
                logging.info(f"Ovoz turi txt dan config.json ga ko'chirildi: {ovoz}")
                return ovoz.lower()
        except Exception:
            pass

    # Hech qayerda yo'q — default
    set_config("user.voice_type", "erkak")
    return "erkak"


# ========== Buyruqlarni yuklash ==========
def buyruqlar_json_ol():
    default_commands = {
        "yutub": "open_youtube",
        "yutuq": "open_youtube",
        "youtube": "open_youtube",
        "birinchi video": "youtube_first_video",
        "musiqa": "music_search",
        "qo'shiq": "music_search",
        "telegram": "open_telegram",
        "vs code": "open_code",
        "chrome": "open_chrome",
        "brave": "open_brave",
        "discord": "open_discord",
        "havo": "weather",
        "ob-havo": "weather",
        "qidir": "search",
        "qidiruv": "search",
        "izla": "search",
        "vaqt": "time",
        "soat": "time",
        "soat necha": "time",
        "sana": "date",
        "bugun": "date",
        "eslatma": "reminder",
        "eslatmalar": "reminders",
        "eslatmani o'chir": "delete_reminder",
        "video qo'y": "play_video",
        "videoni davom et": "play_video",
        "videoni to'xtat": "pause_video",
        "video pauza": "pause_video",
        "musiqani to'xtat": "music_pause",
        "musiqa to'xtat": "music_pause",
        "to'xtat": "music_pause",
        "pauza": "music_pause",
        "musiqani qo'y": "music_play",
        "davom et": "music_play",
        "davom ettir": "music_play",
        "ijro et": "music_play",
        "boshidan boshla": "music_restart",
        "qayta boshla": "music_restart",
        "salom": "greet",
        "assalomu alaykum": "greet",
        "ai": "chat_mode",
        "suhbat qil": "chat_mode",
        "kompyuterni o'chir": "shutdown",
        "kompyuter o'chir": "shutdown",
        "kompyuterni yoq": "restart",
        "qayta yukla": "restart",
        "ekranni yop": "lock",
        "ekranni qulfa": "lock",
        "qulfa": "lock",
    }

    fayl = os.path.join(BASE_DIR, "data", "commands.json")
    if os.path.exists(fayl):
        try:
            with open(fayl, "r", encoding="utf-8") as f:
                existing = json.load(f)
                for k, v in default_commands.items():
                    if k not in existing:
                        existing[k] = v
                return existing
        except Exception as e:
            logging.error(f"commands.json yuklash xatolik: {e}")
            return default_commands
    else:
        with open(fayl, "w", encoding="utf-8") as f:
            json.dump(default_commands, f, ensure_ascii=False, indent=2)
        return default_commands


buyruqlar_json = buyruqlar_json_ol()

# Smart algoritmlarni tayyorlash
if SMART_ALGO_AVAILABLE:
    algoritmlarni_tayyorla(buyruqlar_json)

# ========== Ovozni aniqlash ==========
# Gapirish tugagandan keyin kutish vaqti (soniyada)
GAPIRISH_COOLDOWN = 2.5  # 1.5 dan oshirildi — TTS feedback loop oldini olish


def tingla():
    if not global_state.tinglash_faol:
        return None

    # Agar yordamchi hozir gapirayotgan bo'lsa — kutish
    if global_state.gapirmoqda:
        time.sleep(0.3)
        return None

    # Cooldown — gapirish tugaganidan keyin biroz kutish
    # (karnaydan chiqayotgan ovozning aks-sadosi so'nishi uchun)
    vaqt_farqi = time.time() - global_state.oxirgi_gapirish_vaqti
    if vaqt_farqi < GAPIRISH_COOLDOWN:
        time.sleep(GAPIRISH_COOLDOWN - vaqt_farqi)
        return None

    if not SPEECH_AVAILABLE or not SPEECH_RECOGNITION_AVAILABLE:
        time.sleep(1)
        return None

    # v6.0.0 Tezkor VAD Audio Xizmati (unit testlarda sd/sr mock qilingan bo'lsa fallback yo'liga o'tiladi)
    if (
        AUDIO_SERVICE_AVAILABLE
        and not hasattr(sd, "_mock_name")
        and not hasattr(sr, "_mock_name")
    ):
        try:
            audio_svc = get_audio_service()
            text = audio_svc.listen_and_transcribe(language="uz-UZ", timeout=4.0)
            if text:
                gui_ga_xabar_yuborish(f"🗣️ Siz: {text}")
                return text.lower()
            return None
        except Exception as e:
            logging.debug(f"AudioService fallback ga o'tish: {e}")

    try:
        # Fallback: Record audio
        samplerate = 16000
        duration = 5
        audio_data = sd.rec(
            int(samplerate * duration),
            samplerate=samplerate,
            channels=1,
            dtype="float32",
        )

        # sd.wait() — GPU/CPU ga yuklangan audio yozuvni kutish
        sd.wait()

        # Convert to speech_recognition format
        audio_data = (audio_data * 32767).astype("int16")

        # Use speech_recognition for Google API
        r = sr.Recognizer()
        audio = sr.AudioData(audio_data.tobytes(), samplerate, 2)

        try:
            text = r.recognize_google(audio, language="uz-UZ")
            gui_ga_xabar_yuborish(f"🗣️ Siz: {text}")
            return text.lower()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            gui_ga_xabar_yuborish(f"❌ Google API xatosi: {e}", ovoz=True)
            return None
    except Exception as e:
        print(f"DEBUG: Microphone Error: {e}")
        gui_ga_xabar_yuborish(f"❌ Mikrofon xatosi: {e}", ovoz=True)
        return None


# ========== Windows Audio API orqali ovoz boshqaruvi ==========
def get_audio_session():
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume
    except Exception as e:
        print(f"Audio session error: {e}")
        return None


def ovoz_sozlash(level):
    volume = get_audio_session()
    if not volume:
        gui_ga_xabar_yuborish("❌ Ovoz boshqarib bo'lmadi", ovoz=True)
        return False

    try:
        level = max(0.0, min(1.0, level / 100.0))
        volume.SetMute(0, None)  # Avval unmute qilish
        volume.SetMasterVolumeLevelScalar(level, None)
        gui_ga_xabar_yuborish(f"🔊 Ovoz {int(level * 100)}% ga o'rnatildi")
        ovoz_chiqar_tez(f"Ovoz {int(level * 100)} foizga o'rnatildi")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Ovoz o'rnatilmadi: {e}", ovoz=True)
        return False


def ovoz_oshir(miqdor=5):
    volume = get_audio_session()
    if not volume:
        gui_ga_xabar_yuborish("❌ Ovoz boshqarib bo'lmadi", ovoz=True)
        return False

    try:
        current_level = volume.GetMasterVolumeLevelScalar()
        new_level = min(1.0, current_level + (miqdor / 100.0))
        volume.SetMute(0, None)  # Avval unmute qilish
        volume.SetMasterVolumeLevelScalar(new_level, None)
        change = int((new_level - current_level) * 100)
        gui_ga_xabar_yuborish(f"🔊 Ovoz {change}% oshirildi")
        ovoz_chiqar_tez(f"Ovoz {change} foizga oshirildi")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Ovoz oshirilmadi: {e}", ovoz=True)
        return False


def ovoz_pasaytir(miqdor=5):
    volume = get_audio_session()
    if not volume:
        gui_ga_xabar_yuborish("❌ Ovoz boshqarib bo'lmadi", ovoz=True)
        return False

    try:
        current_level = volume.GetMasterVolumeLevelScalar()
        new_level = max(0.0, current_level - (miqdor / 100.0))
        volume.SetMute(0, None)  # Avval unmute qilish
        volume.SetMasterVolumeLevelScalar(new_level, None)
        change = int((current_level - new_level) * 100)
        gui_ga_xabar_yuborish(f"🔉 Ovoz {change}% pasaytirildi")
        ovoz_chiqar_tez(f"Ovoz {change} foizga pasaytirildi")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Ovoz pasaytirilmadi: {e}", ovoz=True)
        return False


def ovoz_ochir():
    volume = get_audio_session()
    if not volume:
        gui_ga_xabar_yuborish("❌ Ovoz boshqarib bo'lmadi", ovoz=True)
        return False

    try:
        # AVVAL gapir, KEYIN mute qil (aks holda o'chirilgan ovozda gapirmaydi)
        ovoz_chiqar_tez("Ovoz o'chirildi")
        import time as _t

        _t.sleep(1.5)  # TTS gapirib bo'lishini kutish
        volume.SetMute(1, None)
        gui_ga_xabar_yuborish("🔇 Ovoz o'chirildi")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Ovoz o'chirilmadi: {e}", ovoz=True)
        return False


def ovoz_och():
    volume = get_audio_session()
    if not volume:
        gui_ga_xabar_yuborish("❌ Ovoz boshqarib bo'lmadi", ovoz=True)
        return False

    try:
        volume.SetMute(0, None)
        gui_ga_xabar_yuborish("🔊 Ovoz ochildi")
        ovoz_chiqar_tez("Ovoz ochildi")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Ovoz ochilmadi: {e}", ovoz=True)
        return False


# ========== YouTube video boshqaruvi ==========
def youtube_video_play():
    try:
        pyautogui.press("k")
        gui_ga_xabar_yuborish("▶️ Video qo'yilmoqda")
        ovoz_chiqar_tez("Video qo'yildi")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish("❌ Video qo'yilmadi", ovoz=True)
        return False


def youtube_video_pause():
    try:
        pyautogui.press("k")
        gui_ga_xabar_yuborish("⏸️ Video to'xtatildi")
        ovoz_chiqar_tez("Video to'xtatildi")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish("❌ Video to'xtatilmadi", ovoz=True)
        return False


def youtube_keyingi_video():
    """YouTube'da keyingi videoga o'tish (Shift+N)"""
    try:
        pyautogui.hotkey("shift", "n")
        gui_ga_xabar_yuborish("⏭️ Keyingi video")
        ovoz_chiqar_tez("Keyingi video")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish("❌ Keyingi videoga o'tilmadi", ovoz=True)
        return False


def youtube_oldingi_video():
    """YouTube'da oldingi videoga qaytish (Shift+P)"""
    try:
        pyautogui.hotkey("shift", "p")
        gui_ga_xabar_yuborish("⏮️ Oldingi video")
        ovoz_chiqar_tez("Oldingi video")
        return True
    except Exception as e:
        gui_ga_xabar_yuborish("❌ Oldingi videoga o'tilmadi", ovoz=True)
        return False


def youtube_video_boshla_koordinata(video_raqam=1):
    try:
        if not global_state.youtube_ochiq:
            gui_ga_xabar_yuborish("⚠️ Avval YouTube ochilishi kerak", ovoz=True)
            return False

        time.sleep(1.5)

        screen_width, screen_height = pyautogui.size()

        positions = {
            1: (screen_width // 4, screen_height // 3),
            2: (screen_width // 2, screen_height // 3),
            3: (3 * screen_width // 4, screen_height // 3),
            4: (screen_width // 4, screen_height // 2),
            5: (screen_width // 2, screen_height // 2),
            6: (3 * screen_width // 4, screen_height // 2),
        }

        x, y = positions.get(video_raqam, positions[1])

        pyautogui.click(x, y)
        gui_ga_xabar_yuborish(f"✅ {video_raqam}-video ochilmoqda")
        ovoz_chiqar_tez(f"{video_raqam} chi video ochildi")
        return True

    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Video ochilmadi", ovoz=True)
        return False


# ========== Chrome oynasini aqlli yopish ==========
import ctypes
from ctypes import wintypes


def _oldingi_oyna_nomi():
    """Hozirgi faol oyna nomini olish"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value, hwnd
    except Exception:
        return "", 0


def _chrome_oynasini_top():
    """Barcha Chrome oynalarini topish"""
    chrome_oynalar = []

    def enum_callback(hwnd, _):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                if "Google Chrome" in buf.value or "- Chrome" in buf.value:
                    chrome_oynalar.append((hwnd, buf.value))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    return chrome_oynalar


def chrome_oyna_yop_aqlli():
    """Chrome oynasini aqlli yopish — foreground tekshirish bilan"""
    try:
        oyna_nomi, hwnd = _oldingi_oyna_nomi()

        # Chrome ochiq oynalarni topish
        chrome_oynalar = _chrome_oynasini_top()
        if not chrome_oynalar:
            ovoz_chiqar_tez("Chrome ochiq emas")
            return False

        # Agar Chrome hozir faol oyna bo'lsa — to'g'ridan-to'g'ri yopish
        if "Chrome" in oyna_nomi or "chrome" in oyna_nomi.lower():
            pyautogui.hotkey("ctrl", "w")
            gui_ga_xabar_yuborish("🗑️ Chrome oynasi yopildi")
            ovoz_chiqar_tez("Chrome oynasi yopildi")
            return True

        # Chrome faol emas — foydalanuvchidan so'rash
        tab_nomi = chrome_oynalar[0][1].replace(" - Google Chrome", "")
        ovoz_chiqar_tez(
            f"Oxirgi Chrome oynasini yopaveraymi? U yerda '{tab_nomi[:30]}' ochiq. Ko'rishni xohlamaysizmi?"
        )

        javob = tingla()
        if not javob:
            ovoz_chiqar_tez("Eshitmadim, Chrome oyna yopilmadi")
            return False

        javob_toza = matnni_tozalash(javob.lower())

        # "Yo'q" / "yopaver" / "keraksiz" — to'g'ridan-to'g'ri yopish
        yoklar = ["yoq", "yopaver", "yop", "keraksiz", "kerakmas", "ber", "yopavoray"]
        if any(s in javob_toza for s in yoklar):
            # Chrome oynasiga o'tib yopish
            chrome_hwnd = chrome_oynalar[0][0]
            ctypes.windll.user32.SetForegroundWindow(chrome_hwnd)
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "w")
            gui_ga_xabar_yuborish("🗑️ Chrome oynasi yopildi")
            ovoz_chiqar_tez("Chrome oynasi yopildi")
            return True

        # "Ha" / "ko'rsatib" — Chrome ni oldingi oynaga chiqarish
        halar = ["ha", "korat", "korsat", "korsa", "ochiq", "korsatib"]
        if any(s in javob_toza for s in halar):
            chrome_hwnd = chrome_oynalar[0][0]
            ctypes.windll.user32.SetForegroundWindow(chrome_hwnd)
            gui_ga_xabar_yuborish("🔄 Chrome ko'rsatildi. Yopish uchun 'yop' deng")
            ovoz_chiqar_tez("Mana Chrome oynasi. Yopish uchun yop deng")

            # Foydalanuvchi javobini kutish
            javob2 = tingla()
            if javob2 and ("yop" in matnni_tozalash(javob2.lower())):
                pyautogui.hotkey("ctrl", "w")
                gui_ga_xabar_yuborish("🗑️ Chrome oynasi yopildi")
                ovoz_chiqar_tez("Chrome oynasi yopildi")
                return True
            else:
                ovoz_chiqar_tez("Chrome oynasi qoldirildi")
                return False

        ovoz_chiqar_tez("Tushunmadim. Chrome oynasi qoldirildi")
        return False

    except Exception as e:
        logging.error(f"Chrome yopish xatolik: {e}")
        gui_ga_xabar_yuborish(f"❌ Chrome yopishda xatolik", ovoz=True)
        return False


# ========== Ob-havo ==========
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# O'zbek shahar nomlari → OpenWeatherMap nomi
SHAHAR_NOMLARI = {
    "toshkent": "Tashkent",
    "samarqand": "Samarkand",
    "buxoro": "Bukhara",
    "andijon": "Andijan",
    "namangan": "Namangan",
    "fargona": "Fergana",
    "farg'ona": "Fergana",
    "parvona": "Fergana",
    "farg'onada": "Fergana",
    "navoiy": "Navoi",
    "nukus": "Nukus",
    "qarshi": "Karshi",
    "jizzax": "Jizzakh",
    "termiz": "Termez",
    "urganch": "Urgench",
    "xorazm": "Khiva",
    "qo'qon": "Kokand",
    "marg'ilon": "Margilan",
    "chirchiq": "Chirchik",
    "olmaliq": "Almalyk",
    "guliston": "Gulistan",
    "denov": "Denau",
    "shahrisabz": "Shahrisabz",
    "zarafshon": "Zarafshan",
    "tashkent": "Tashkent",
    "fergana": "Fergana",
    "samarkand": "Samarkand",
    # Boshqa mamlakatlar
    "moskva": "Moscow",
    "istanbul": "Istanbul",
    "dubai": "Dubai",
    "seul": "Seoul",
    "tokio": "Tokyo",
    "london": "London",
}

# Ob-havo holati emoji mapping
HAVO_EMOJI = {
    "clear": "☀️",
    "clouds": "☁️",
    "rain": "🌧️",
    "drizzle": "🌦️",
    "thunderstorm": "⛈️",
    "snow": "❄️",
    "mist": "🌫️",
    "fog": "🌫️",
    "haze": "🌫️",
    "smoke": "🌫️",
}


def ob_havo_olish(shahar="Tashkent"):
    """OpenWeatherMap API orqali ob-havo — do'stona, iliq javob"""
    if not OPENWEATHER_API_KEY:
        return None, "Kechirasiz, ob-havo xizmatiga ulanib bo'lmadi"

    # Ingliz ob-havo → O'zbek tarjima
    HAVO_TARJIMA = {
        "clear sky": "toza osmon",
        "few clouds": "oz-moz bulutli",
        "scattered clouds": "bulutli",
        "broken clouds": "bulutli",
        "overcast clouds": "to'liq bulutli",
        "light rain": "yengil yomg'ir",
        "moderate rain": "o'rtacha yomg'ir",
        "heavy intensity rain": "kuchli yomg'ir",
        "light snow": "yengil qor",
        "snow": "qor yog'moqda",
        "mist": "tumanli",
        "fog": "tumanli",
        "haze": "tumanli",
        "thunderstorm": "momaqaldiroq",
        "drizzle": "mayda yomg'ir",
    }

    # O'zbek shahar nomlarini qaytarish (API dan kelgan nomni o'zbekchaga)
    SHAHAR_UZB = {
        "Fergana": "Farg'ona",
        "Tashkent": "Toshkent",
        "Samarkand": "Samarqand",
        "Bukhara": "Buxoro",
        "Andijan": "Andijon",
        "Namangan": "Namangan",
        "Navoi": "Navoiy",
        "Nukus": "Nukus",
        "Karshi": "Qarshi",
        "Jizzakh": "Jizzax",
        "Termez": "Termiz",
        "Urgench": "Urganch",
        "Kokand": "Qo'qon",
        "Margilan": "Marg'ilon",
        "Chirchik": "Chirchiq",
        "Gulistan": "Guliston",
        "Denau": "Denov",
    }

    # O'zbek nomini inglizchaga aylantirish (API uchun)
    # MUHIM: rstrip("da") emas — regex bilan qo'shimchani olish
    shahar_toza = re.sub(r"(dagi|da|ga)$", "", shahar.lower().strip())
    for uzb, eng in SHAHAR_NOMLARI.items():
        if uzb in shahar_toza or shahar_toza in uzb:
            shahar = eng
            break

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": shahar,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "en",  # Inglizcha — tarjima o'zimiz qilamiz
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            logging.warning(f"Ob-havo xato: {response.status_code} — {shahar}")
            return None, f"Kechirasiz, {shahar} ob-havosini tekshirib bo'lmadi"

        data = response.json()

        harorat = round(data["main"]["temp"])
        his_qilish = round(data["main"]["feels_like"])
        namlik = data["main"]["humidity"]
        shamol = round(data["wind"]["speed"], 1)
        holat_en = data["weather"][0]["description"].lower()
        holat_main = data["weather"][0]["main"].lower()
        shahar_nomi_en = data["name"]

        # Shahar nomini o'zbekchaga
        shahar_nomi = SHAHAR_UZB.get(shahar_nomi_en, shahar_nomi_en)

        # Ob-havo holatini o'zbekchaga
        holat_uz = HAVO_TARJIMA.get(holat_en, holat_en)

        # Emoji
        emoji = HAVO_EMOJI.get(holat_main, "🌡️")

        # Do'stona izoh — harorat va holatga qarab
        if harorat >= 35:
            izoh = "Juda issiq ekan! Soyada yuring va suv ichishni unutmang 💧"
        elif harorat >= 28:
            izoh = "Issiq havo, yengil kiyimda chiqsangiz bo'ladi ☀️"
        elif harorat >= 20:
            izoh = "Ajoyib havo! Sayir qilish uchun zo'r kun 🌿"
        elif harorat >= 13:
            izoh = "Yoqimli salqin havo. Yengil kurtka olsangiz yaxshi bo'ladi"
        elif harorat >= 5:
            izoh = "Salqin ekan, iliq kiyining! Issiq choy ichib oling ☕"
        elif harorat >= -5:
            izoh = "Sovuq ekan, ehtiyot bo'ling! Iliq kiyinib chiqing 🧥"
        else:
            izoh = "Juda sovuq! Uyda iliq o'tirsangiz yaxshi bo'lardi ❄️"

        # Yomg'ir/qor bo'lsa — alohida maslahat
        if "rain" in holat_main or "drizzle" in holat_main:
            izoh = "Yomg'ir yog'yapti, soyabon olishni unutmang! ☔"
        elif "snow" in holat_main:
            izoh = "Qor yog'yapti! Iliq kiyinib chiqing, yo'llarda ehtiyot bo'ling ❄️"
        elif "thunder" in holat_main:
            izoh = "Momaqaldiroq bor, iloji bo'lsa uyda qoling ⛈️"

        # GUI uchun — to'liq ma'lumot
        gui_matn = (
            f"{emoji} {shahar_nomi}: {harorat}°C, {holat_uz}. "
            f"His qilinadi: {his_qilish}°C. "
            f"Namlik: {namlik}%. Shamol: {shamol} m/s"
        )

        # Ovozli javob — do'stona, qisqa
        ovoz_matn = f"{shahar_nomi}da hozir {harorat} daraja, {holat_uz}. {izoh}"

        return gui_matn, ovoz_matn

    except requests.exceptions.Timeout:
        return (
            None,
            "Kechirasiz, ob-havo serveri javob bermadi. Birozdan keyin qaytadan urinib ko'ring",
        )
    except Exception as e:
        logging.error(f"Ob-havo xatolik: {e}")
        return None, "Ob-havo ma'lumotini olishda muammo chiqdi, kechirasiz"


# ========== Musiqa platformalari ==========
def musiqa_platform_tanlash():
    ovoz_chiqar_tez(
        "Qaysi platformadan musiqa qidiraylik? YouTube, Yandex Music yoki Spotify?"
    )

    for _ in range(2):
        javob = tingla()

        if not javob:
            continue

        if "yandex" in javob or "яндекс" in javob:
            return "yandex"
        elif "spotify" in javob:
            return "spotify"
        elif "youtube" in javob or "yutub" in javob:
            return "youtube"

    return "youtube"


def musiqa_qidir(query, platform="youtube"):
    try:
        # ===== 1-QADAM: Desktop ilova tekshirish =====
        if platform in ["yandex", "spotify"]:
            desktop_result = _musiqa_desktop_app(query, platform)
            if desktop_result:
                return True

        # ===== 2-QADAM: Browser fallback & To'g'ridan-to'g'ri ijro =====
        if platform == "youtube":
            watch_url = None
            try:
                # YouTube qidiruv natijalaridan to'g'ridan-to'g'ri birinchi video URL-ini olish
                search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                req = urllib.request.Request(
                    search_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )
                with urllib.request.urlopen(req, timeout=3.5) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                    vids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                    if vids:
                        watch_url = f"https://www.youtube.com/watch?v={vids[0]}"
            except Exception as e:
                logging.debug(f"Direct YouTube video topishda xatolik: {e}")

            url = watch_url or f"https://www.youtube.com/results?search_query={quote_plus(query)}+music"
            gui_ga_xabar_yuborish(f"🎵 '{query}' YouTube'da ijro etilmoqda...")
            webbrowser.open(url)
            ovoz_chiqar_tez(f"{query} qo'yilmoqda")
            return True

        elif platform == "yandex":
            url = f"https://music.yandex.ru/search?text={quote_plus(query)}"
            gui_ga_xabar_yuborish(f"🎵 Yandex Music'da qidirilmoqda (web)")
            webbrowser.open(url)
            ovoz_chiqar_tez(f"{query} qidirildi")

            def _auto_play_yandex():
                time.sleep(8)
                try:
                    for i in range(3):
                        pyautogui.press("space")
                        logging.debug(f"Auto-play: Yandex Music Space bosildi ({i + 1})")
                        time.sleep(3)
                except Exception as e:
                    logging.warning(f"Auto-play xatolik: {e}")

            threading.Thread(target=_auto_play_yandex, daemon=True).start()
            return True

        elif platform == "spotify":
            url = f"https://open.spotify.com/search/{quote_plus(query)}"
            gui_ga_xabar_yuborish(f"🎵 Spotify'da qidirilmoqda (web)")
            webbrowser.open(url)
            ovoz_chiqar_tez(f"{query} qidirildi")

            def _auto_play_spotify():
                time.sleep(4)
                try:
                    pyautogui.press("enter")
                    logging.debug("Auto-play: Spotify Enter bosildi")
                except Exception as e:
                    logging.warning(f"Auto-play xatolik: {e}")

            threading.Thread(target=_auto_play_spotify, daemon=True).start()
            return True

        else:
            url = f"https://www.youtube.com/results?search_query={quote_plus(query)}+music"
            gui_ga_xabar_yuborish(f"🎵 '{query}' qidirilmoqda...")
            webbrowser.open(url)
            ovoz_chiqar_tez(f"{query} qidirildi")
            return True

    except Exception as e:
        logging.error(f"Musiqa qidirish xatolik: {e}")
        return False


def _musiqa_desktop_app(query, platform):
    """Desktop ilovada musiqa qidirish — agar ilova o'rnatilgan bo'lsa"""
    try:
        # Ilova jarayonlarini tekshirish
        APPS = {
            "yandex": {
                "processes": [
                    "Yandex Music.exe",
                    "YandexMusic.exe",
                    "yandex-music.exe",
                ],
                "paths": [
                    os.path.expandvars(
                        r"%LOCALAPPDATA%\Programs\YandexMusic\Yandex Music.exe"
                    ),
                    os.path.expandvars(
                        r"%LOCALAPPDATA%\Yandex\YandexMusic\Yandex Music.exe"
                    ),
                ],
                "title_part": "Yandex Music",
            },
            "spotify": {
                "processes": ["Spotify.exe"],
                "paths": [
                    os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
                ],
                "title_part": "Spotify",
            },
        }

        app_info = APPS.get(platform)
        if not app_info:
            return False

        # 1. Jarayon allaqachon ishlamoqdami?
        app_running = False
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] in app_info["processes"]:
                    app_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if app_running:
            # Ilova ochiq — oynani oldingi planga olib kelish
            gui_ga_xabar_yuborish(f"🎵 {app_info['title_part']} ilovasida qidirilmoqda")
            ovoz_chiqar_tez(f"{query} ni {app_info['title_part']} ilovasida qidiraman")
            try:
                import ctypes

                # Birinchi — oynani topish va aktivlashtirish
                user32 = ctypes.windll.user32

                def _activate_and_search():
                    time.sleep(0.5)
                    # Alt+Tab yoki tasklist orqali oynani topish
                    keyboard.send("alt+tab")
                    time.sleep(1)
                    # Search hotkey — Ctrl+F yoki / yoki Ctrl+L
                    if platform == "yandex":
                        keyboard.send("ctrl+f")
                    elif platform == "spotify":
                        keyboard.send("ctrl+l")
                    time.sleep(0.5)
                    # Matnni yozish
                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.2)
                    pyautogui.typewrite(
                        query, interval=0.03
                    ) if query.isascii() else pyautogui.write(query)
                    time.sleep(0.3)
                    pyautogui.press("enter")

                threading.Thread(target=_activate_and_search, daemon=True).start()
                return True
            except Exception as e:
                logging.warning(f"Desktop app search xatolik: {e}")
                return False

        # 2. Ilova o'rnatilgan ammo ishlamayapti — uni ochish
        for path in app_info["paths"]:
            if os.path.exists(path):
                gui_ga_xabar_yuborish(
                    f"🎵 {app_info['title_part']} ilovasi ochilmoqda..."
                )
                ovoz_chiqar_tez(f"{app_info['title_part']} ilovasini ochyapman")
                subprocess.Popen([path], shell=False)
                return True

        # 3. Ilova yo'q — browser fallback ga qaytish
        return False

    except Exception as e:
        logging.warning(f"Desktop app tekshirish xatolik: {e}")
        return False


# ========== O'zbekcha raqamlar lug'ati ==========
UZBEK_RAQAMLAR = {
    "nol": 0,
    "bir": 1,
    "ikki": 2,
    "uch": 3,
    "tort": 4,
    "to'rt": 4,
    "besh": 5,
    "olti": 6,
    "yetti": 7,
    "sakkiz": 8,
    "toqqiz": 9,
    "to'qqiz": 9,
    "on": 10,
    "o'n": 10,
    "yigirma": 20,
    "ottiz": 30,
    "o'ttiz": 30,
    "qirq": 40,
    "ellik": 50,
    "oltmish": 60,
    "yetmish": 70,
    "sakson": 80,
    "tukson": 90,
    "to'qson": 90,
    "yuz": 100,
}


def matnni_tozalash(matn):
    """Apostrof va maxsus belgilarni normalizatsiya qilish.
    Google Speech 'ko\\'tar' ni 'kotar' yoki 'qoʻy' deb yozishi mumkin."""
    # Barcha turdagi apostroflarni olib tashlash
    matn = matn.replace("'", "").replace("'", "").replace("ʻ", "").replace("`", "")
    matn = matn.replace("'", "").replace("%", " ").replace("-", " ")
    return matn.lower().strip()


def suzdan_raqam(matn):
    """Matndagi o'zbekcha raqam so'zlarini topib, sonni qaytarish.
    Masalan: 'ellik' -> 50, 'yigirma besh' -> 25"""
    matn_toza = matnni_tozalash(matn)
    sozlar = matn_toza.split()

    # Avval oddiy raqamlarni tekshirish (50, 100 kabi)
    for soz in sozlar:
        if soz.isdigit():
            return int(soz)

    # So'z bilan yozilgan raqamlarni tekshirish
    jami = 0
    topildi = False
    for soz in sozlar:
        if soz in UZBEK_RAQAMLAR:
            jami += UZBEK_RAQAMLAR[soz]
            topildi = True

    return jami if topildi else None


# ========== Qoidalarga asoslangan aniqlash ==========
def buyruqni_aniqla(matn):
    matn_lower = matn.lower().strip()
    matn_toza = matnni_tozalash(matn)  # Apostrofsiz versiya

    # Agar bu savol yoki mantiqiy so'rov bo'lsa, buyruq sifatida noto'g'ri bajarmay AI ga o'tkazish
    if "?" in matn_lower or any(w in matn_toza for w in [
        "bormi", "bormikan", "ornatilganmi", "mavjudmi",
        "oxshash", "shunga", "nima", "qanday", "qanaqa", "kim", "nega",
        "haqida", "tavsiya", "maslahat", "fikr"
    ]):
        if "soat necha" not in matn_toza and "vaqt necha" not in matn_toza:
            return "unknown"

    # ===== Ovoz boshqaruvi =====
    ovoz_bor = "ovoz" in matn_toza or "oboz" in matn_toza

    if ovoz_bor:
        raqam = suzdan_raqam(matn)

        # "ovoz 50", "ovozni ellik qil", "ovozni 50% qil"
        if raqam is not None and raqam > 0:
            # Oshirish/pasaytirish yo'q — to'g'ridan-to'g'ri o'rnatish
            oshir_bor = any(
                s in matn_toza for s in ["oshir", "kotar", "kottar", "baland"]
            )
            pasayt_bor = any(
                s in matn_toza for s in ["pasayt", "kamayt", "past", "tushir"]
            )

            if oshir_bor:
                return ("volume_up", raqam)
            elif pasayt_bor:
                return ("volume_down", raqam)
            else:
                return ("volume_set", raqam)

        # "ovozni oshir", "ovozni ko'tar", "ovoz baland"
        if any(
            s in matn_toza for s in ["oshir", "kotar", "kottar", "baland", "kuchli"]
        ):
            return ("volume_up", 10)

        # "ovozni pasayt", "ovozni kamaytir", "ovoz past"
        if any(
            s in matn_toza
            for s in ["pasayt", "kamayt", "past", "tushir", "kichik", "sekin"]
        ):
            return ("volume_down", 10)

        # "ovozni o'chir"
        if any(s in matn_toza for s in ["ochir", "uchir"]):
            return "volume_mute"

        # "ovozni och", "ovozni yoq"
        if any(s in matn_toza for s in ["och", "yoq"]):
            return "volume_unmute"

    # ===== Video raqami =====
    match = re.search(r"(\d+)\s*(?:-?\s*)?(?:chi|chi\s)?video", matn_toza)
    if match:
        num = int(match.group(1))
        return ("video_number", num)

    # So'z bilan: "birinchi video", "ikkinchi video"
    tartib_raqamlar = {
        "birinchi": 1,
        "ikkinchi": 2,
        "uchinchi": 3,
        "tortinchi": 4,
        "beshinchi": 5,
    }
    for soz, raqam in tartib_raqamlar.items():
        if soz in matn_toza and "video" in matn_toza:
            return ("video_number", raqam)

    # ===== Media va Musiqa boshqaruvi / qidiruvi (Yuqori ustunlik) =====
    # 1. Pauza / To'xtatish
    if any(s in matn_toza for s in ["musiqani toxtat", "musiqa toxtat", "videoni toxtat", "video toxtat", "pauza"]):
        if any(s in matn_toza for s in ["video", "videoni"]):
            return "pause_video"
        return "music_pause"
    if matn_toza in ["toxtat", "stop"]:
        return "music_pause"

    # 2. Davom ettirish (faqat aniq resume buyruqlari)
    pure_resume = [
        "davom ettir",
        "davom et",
        "musiqani qoy",
        "musiqani davom ettir",
        "musiqani davom et",
        "videoni davom et",
        "videoni davom ettir",
        "ijro et",
    ]
    if matn_toza in pure_resume:
        if "video" in matn_toza:
            return "play_video"
        return "music_play"

    # 3. Qayta boshlash
    if any(s in matn_toza for s in ["boshidan boshla", "qayta boshla"]):
        return "music_restart"

    # 4. Musiqa / Qo'shiq qidirish va ijro etish
    musiqa_kalitlar = ["qoshiq", "qoshig", "musiqa", "ashula", "trek", "klip"]
    ijro_feillar = [
        "qoy",
        "eshit",
        "tingla",
        "ijro",
        "play",
        "qoyib ber",
        "eshitaylik",
        "tinglaylik",
        "eshitmoqchiman",
        "tinglamoqchiman",
    ]
    platformalar = ["youtube", "yutub", "yutuq", "spotify", "yandex", "yandeks"]

    musiqa_bor = any(k in matn_toza for k in musiqa_kalitlar)
    ijro_bor = any(k in matn_toza for k in ijro_feillar)
    platforma_bor = any(k in matn_toza for k in platformalar)

    # Agar musiqa kalit so'zlari bor bo'lsa yoki platforma + ijro so'zi bo'lsa -> music_search
    if musiqa_bor or (platforma_bor and ijro_bor):
        return "music_search"

    # 5. YouTube / Yandex / Spotify faqat dastur/sayt ochish
    if platforma_bor and any(s in matn_toza for s in ["youtube", "yutub", "yutuq"]):
        ochish_sozlari = ["och", "kir", "sayt", "ilova", "dastur", "bosh sahifa", "sahifa"]
        words = matn_toza.split()
        if len(words) <= 3 and (any(s in matn_toza for s in ochish_sozlari) or matn_toza in ["youtube", "yutub", "yutuq"]):
            return "open_youtube"

    # ===== Oddiy buyruqlar — tozalangan matn bilan ham tekshirish =====
    sorted_commands = sorted(
        buyruqlar_json.items(), key=lambda x: len(x[0]), reverse=True
    )

    # Kontekst-aware: ba'zi so'zlar boshqa intent bilan aralashmasligini tekshirish
    # Masalan: "bugungi dollar kursi" → "bugun" topilsa ham, "dollar/kurs" konteksti bor
    AGENT_GA_YUBORISH_KALITLAR = {
        "date": [
            "dollar",
            "kurs",
            "valyuta",
            "narx",
            "pul",
            "som",
            "rubl",
            "yevro",
            "euro",
            "bitcoin",
        ],
        "time": ["dollar", "kurs", "valyuta", "narx"],
    }

    for soz, buyruq in sorted_commands:
        soz_toza = matnni_tozalash(soz)
        # Original va tozalangan versiyalarni ham tekshirish
        if soz in matn_lower or soz_toza in matn_toza:
            # Kontekst tekshirish — noto'g'ri match oldini olish
            kalitlar = AGENT_GA_YUBORISH_KALITLAR.get(buyruq, [])
            if kalitlar and any(k in matn_lower for k in kalitlar):
                continue  # Bu match noto'g'ri — keyingisini tekshir
            if buyruq == "open_youtube" and (musiqa_bor or ijro_bor):
                return "music_search"
            return buyruq

    # ===== O'zak solishtirish (stem matching) =====
    # "qo'shig'ini" → "qoshigini" vs "qo'shiq" → "qoshiq" → o'zak "qoshi" mos
    for soz, buyruq in sorted_commands:
        soz_toza = matnni_tozalash(soz)
        if len(soz_toza) >= 4:
            ozak = soz_toza[: len(soz_toza) - 1]  # oxirgi harfni olib tashlash
            if ozak in matn_toza:
                if buyruq == "open_youtube" and (musiqa_bor or ijro_bor):
                    return "music_search"
                return buyruq

    return "unknown"


# ========== Agent Pipeline ==========
_agent = None
_agent_memory = None
_agent_init_lock = threading.Lock()


def _agent_init():
    """Agent ni bir marta ishga tushirish (thread-safe)"""
    global _agent, _agent_memory
    if _agent is not None:
        return True

    with _agent_init_lock:  # Double-check locking
        if _agent is not None:
            return True

        if not AGENT_AVAILABLE or not AI_AVAILABLE:
            return False

        try:
            from core.ai_engine import agent_ai_call
            from core.agent_memory import get_memory

            _agent_memory = get_memory()  # Singleton — duplikat yaratmaslik!
            registry = get_registry()

            # ask_user tool uchun callback — ovoz bilan so'rab, javobni tinglash
            from core.agent_tools import set_ask_user_callback

            def _ask_user_via_voice(question):
                """Agent foydalanuvchidan savol so'raganda — ovoz + GUI"""
                gui_ga_xabar_yuborish(f"❓ Agent so'ramoqda: {question}")
                ovoz_chiqar_tez(question)

                while global_state.gapirmoqda:
                    time.sleep(0.3)

                time.sleep(1.0)

                javob = None
                for k in range(3):
                    javob = tingla()
                    if javob:
                        gui_ga_xabar_yuborish(f"💬 Javob: {javob}")
                        return javob
                    time.sleep(0.5)

                gui_ga_xabar_yuborish("⚠️ Foydalanuvchi javob bermadi.")
                return None

            set_ask_user_callback(_ask_user_via_voice)

            _agent = ReActAgent(registry, agent_ai_call, _agent_memory)

            # GUI ga har bir qadam haqida xabar berish
            def agent_step_callback(step_num, step_type, data):
                if step_type == "thought":
                    gui_ga_xabar_yuborish(
                        f"🧠 Qadam {step_num}: {data.get('thought', '')}"
                    )
                elif step_type == "tool_result":
                    tool = data.get("tool", "")
                    result = data.get("result", {})
                    msg = (
                        result.get("result", {}).get("message", "")
                        if isinstance(result.get("result"), dict)
                        else str(result)[:100]
                    )
                    gui_ga_xabar_yuborish(f"🔧 Tool '{tool}': {msg}")
                elif step_type == "final_answer":
                    pass  # Yakuniy javob alohida ko'rsatiladi
                elif step_type == "error":
                    gui_ga_xabar_yuborish(f"⚠️ Agent xatolik: {data.get('error', '')}")

            _agent.on_step(agent_step_callback)

            # Scheduler ni ishga tushirish
            try:
                from core.agent_scheduler import get_scheduler

                scheduler = get_scheduler()

                def scheduler_callback(task):
                    """Vaqti kelgan vazifani bajarish"""
                    if task.task_type == "reminder":
                        text = task.data.get("text", "Eslatma!")
                        gui_ga_xabar_yuborish(f"⏰ Eslatma: {text}")
                        ovoz_chiqar_tez(f"Eslatma: {text}")
                    elif task.task_type == "tool_call":
                        tool_name = task.data.get("tool", "")
                        params = task.data.get("params", {})
                        registry.call(tool_name, **params)

                scheduler.set_callback(scheduler_callback)
                scheduler.start()
                logging.info("Scheduler ishga tushdi")
            except Exception as e:
                logging.warning(f"Scheduler ishga tushmadi: {e}")

            # Plugin'larni yuklash
            try:
                pm = get_plugin_manager()
                loaded = pm.load_all(registry)
                if loaded > 0:
                    logging.info(f"Plugin'lar yuklandi: {loaded} ta")
            except Exception as e:
                logging.warning(f"Plugin'lar yuklanmadi: {e}")

            # Silero TTS modelini oldindan yuklash (background)
            try:
                from core.tts_manager import get_tts_manager

                tts = get_tts_manager(getattr(global_state, "ovoz_turi_global", "ayol"))
                tts.preload()
            except Exception as e:
                logging.warning(f"TTS preload xatolik: {e}")

            # Proaktiv Agent
            try:
                proactive = get_proactive_agent(_agent_memory)
                suggestions = proactive.get_greeting_suggestions()
                for s in suggestions:
                    gui_ga_xabar_yuborish(f"💡 {s}")
            except Exception as e:
                logging.warning(f"Proaktiv agent xatolik: {e}")

            logging.info(f"Agent tayyor: {registry.count} ta tool")
            return True
        except Exception as e:
            logging.error(f"Agent init xatolik: {e}")
            return False


def agent_pipeline_run(matn):
    """Agent pipeline orqali buyruqni bajarish"""
    if not _agent_init():
        # Agent ishlamasa — eskicha AI ga yuborish
        openrouter_ai_suhbat(matn)
        return

    gui_ga_xabar_yuborish("🤖 Agent o'ylamoqda...")

    # Suhbat tarixini olish
    history = _agent_memory.get_history_for_ai(last_n=6) if _agent_memory else []

    # Agent ni ishga tushirish
    result = _agent.run(matn, conversation_history=history)

    if result.get("success"):
        response = result.get("response", "Bajarildi!")
        tools_used = result.get("tools_used", [])
        steps = result.get("steps", [])

        # Natijani ko'rsatish
        if tools_used:
            gui_ga_xabar_yuborish(
                f"✅ Agent: {response} (tool'lar: {', '.join(tools_used)})"
            )
        else:
            gui_ga_xabar_yuborish(f"🤖 Agent: {response}")

        ovoz_chiqar_tez(response)
        logging.info(f"Agent natija: {len(steps)} qadam, tools: {tools_used}")
    else:
        response = result.get("response", "Kechirasiz, buni bajarolmadim.")
        gui_ga_xabar_yuborish(f"⚠️ Agent: {response}")
        ovoz_chiqar_tez(response)

    try:
        from core.voice.session_manager import get_session_manager
        get_session_manager().record_turn(matn, response)
    except Exception:
        pass


# ========== OpenRouter AI ==========
def openrouter_ai_suhbat(matn):
    """AI orqali savolga javob berish"""
    if not AI_AVAILABLE:
        gui_ga_xabar_yuborish("❌ AI moduli topilmadi", ovoz=True)
        return

    # Rate Limiting tekshirish
    if SMART_ALGO_AVAILABLE:
        limiter = get_gemini_limiter()
        ruxsat, qoldiq = limiter.is_allowed()
        if not ruxsat:
            gui_ga_xabar_yuborish(
                f"⚠️ AI so'rovlar limiti tugadi. {qoldiq}s kuting.", ovoz=True
            )
            return

    gui_ga_xabar_yuborish("🤖 AI o'ylamoqda...")
    javob = ai_savol_yuborish(matn)

    if javob is None:
        gui_ga_xabar_yuborish(
            "❌ AI javob bermadi. Internet aloqasini tekshiring.", ovoz=True
        )
        return

    if javob.get("type") == "command":
        # AI buyruq aniqladimi?
        intent = javob.get("intent", "")
        params = javob.get("params", {})
        response_text = javob.get("response", "Bajarildi")

        # Xavfli buyruqlarni tasdiqlash (2 marta urinish bilan)
        if SMART_ALGO_AVAILABLE and xavfli_buyruqmi(intent):
            gui_ga_xabar_yuborish(f"⚠️ AI xavfli buyruq: {intent}. Tasdiqlaysizmi?")
            ovoz_chiqar_tez(
                f"Diqqat! {response_text}. Rostdan bajaraymi? 'Ha' yoki 'Yo'q' deng."
            )

            tasdiqlandi = False
            for _urinish in range(2):  # 2 marta so'rash
                javob_tasdiqlash = tingla()
                if javob_tasdiqlash:
                    javob_kichik = javob_tasdiqlash.lower()
                    # Aniq rad etish
                    if any(
                        s in javob_kichik
                        for s in ["yo'q", "bekor", "to'xta", "kerak emas"]
                    ):
                        break
                    # Tasdiqlash
                    if any(
                        s in javob_kichik
                        for s in [
                            "ha",
                            "tasdiql",
                            "bajar",
                            "qil",
                            "bo'pti",
                            "ok",
                            "davom",
                        ]
                    ):
                        tasdiqlandi = True
                        break
                # Javob tushunarsiz yoki bo'sh — qayta so'rash
                if _urinish == 0:
                    ovoz_chiqar_tez(
                        "Tushunmadim. 'Ha' bajaraman, 'Yo'q' bekor qilaman. Nima deysiz?"
                    )

            if not tasdiqlandi:
                gui_ga_xabar_yuborish("🚫 Buyruq bekor qilindi")
                ovoz_chiqar_tez("Buyruq bekor qilindi")
                return

        gui_ga_xabar_yuborish(f"🤖 AI: {response_text}")
        ovoz_chiqar_tez(response_text)

        # AI aniqlagan buyruqni bajarish
        _intent_bajar(intent, params)
    else:
        # Oddiy javob
        response_text = javob.get("response", "Tushunmadim")
        gui_ga_xabar_yuborish(f"🤖 AI: {response_text}")
        ovoz_chiqar_tez(response_text)


def _intent_bajar(intent, params=None, matn="", foydalanuvchi_ismi=""):
    """Yagona intent bajarish funksiyasi — AI va regex ikkisi ham shu yerga keladi.

    Args:
        intent: Buyruq nomi (masalan: "open_youtube", "volume_set")
        params: AI dan kelgan parametrlar (dict). Regex pipeline None beradi.
        matn: Original foydalanuvchi matni (musiqa, ob-havo kabi kontekstli buyruqlar uchun).
        foydalanuvchi_ismi: Foydalanuvchi ismi (salomlashish uchun).

    Returns:
        True agar buyruq topildi va bajarildi, False agar topilmadi (Agent ga yuborish kerak).
    """
    if params is None:
        params = {}

    try:
        # ========== Ovoz boshqaruvi ==========
        if intent == "volume_set":
            ovoz_sozlash(params.get("level", 50))
        elif intent == "volume_up":
            ovoz_oshir(params.get("amount", 10))
        elif intent == "volume_down":
            ovoz_pasaytir(params.get("amount", 10))
        elif intent in ["volume_mute", "volume_mute_nircmd"]:
            ovoz_ochir()
        elif intent in ["volume_unmute", "volume_unmute_nircmd"]:
            ovoz_och()

        # ========== Ilova ochish ==========
        elif intent == "open_youtube":
            webbrowser.open("https://www.youtube.com")
            global_state.youtube_ochiq = True
            gui_ga_xabar_yuborish("✅ YouTube ochildi")
            ovoz_chiqar_tez("YouTube ochildi")
        elif intent == "open_telegram":
            try:
                webbrowser.open("telegram:")
                gui_ga_xabar_yuborish("✅ Telegram ochildi")
                ovoz_chiqar_tez("Telegram ochildi")
            except Exception as e:
                logging.error(f"Telegram ochish xatolik: {e}")
                gui_ga_xabar_yuborish("❌ Telegram ochilmadi", ovoz=True)
        elif intent == "open_chrome":
            try:
                webbrowser.open("https://google.com")
                gui_ga_xabar_yuborish("✅ Chrome ochildi")
                ovoz_chiqar_tez("Chrome ochildi")
            except Exception as e:
                logging.error(f"Chrome ochish xatolik: {e}")
                gui_ga_xabar_yuborish("❌ Chrome ochilmadi", ovoz=True)
        elif intent == "open_brave":
            try:
                # Avval Brave brauzerini to'g'ridan-to'g'ri ochishga urinish
                brave_paths = [
                    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                ]
                brave_found = False
                for bp in brave_paths:
                    if os.path.exists(bp):
                        subprocess.Popen([bp])
                        brave_found = True
                        break
                if not brave_found:
                    webbrowser.open("https://google.com")  # Fallback
                gui_ga_xabar_yuborish("✅ Brave ochildi")
                ovoz_chiqar_tez("Brave ochildi")
            except Exception as e:
                logging.error(f"Brave ochish xatolik: {e}")
                gui_ga_xabar_yuborish("❌ Brave ochilmadi", ovoz=True)
        elif intent == "open_discord":
            try:
                webbrowser.open("discord:")
                gui_ga_xabar_yuborish("✅ Discord ochildi")
                ovoz_chiqar_tez("Discord ochildi")
            except Exception as e:
                logging.error(f"Discord ochish xatolik: {e}")
                gui_ga_xabar_yuborish("❌ Discord ochilmadi", ovoz=True)
        elif intent == "open_code":
            try:
                subprocess.Popen(["code"], shell=False)
                gui_ga_xabar_yuborish("✅ VS Code ochildi")
                ovoz_chiqar_tez("VS Code ochildi")
            except FileNotFoundError:
                # code PATH da yo'q — to'liq yo'l bilan ochish
                code_paths = [
                    os.path.expandvars(
                        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
                    ),
                    r"C:\Program Files\Microsoft VS Code\Code.exe",
                ]
                opened = False
                for cp in code_paths:
                    if os.path.exists(cp):
                        subprocess.Popen([cp], shell=False)
                        opened = True
                        break
                if not opened:
                    gui_ga_xabar_yuborish("❌ VS Code topilmadi", ovoz=True)
                    return True
                gui_ga_xabar_yuborish("✅ VS Code ochildi")
                ovoz_chiqar_tez("VS Code ochildi")
            except Exception as e:
                logging.error(f"VS Code ochish xatolik: {e}")
                gui_ga_xabar_yuborish("❌ VS Code ochilmadi", ovoz=True)

        # ========== Salomlashish / identifikatsiya ==========
        elif intent == "greet":
            ism = foydalanuvchi_ismi or "Do'stim"
            gui_ga_xabar_yuborish(f"👋 Salom, {ism}! Xush kelibsiz!")
            ovoz_chiqar_tez(f"Salom, {ism}. Ishlaringiz yaxshimi?")
        elif intent == "identity":
            ism = foydalanuvchi_ismi or "Do'stim"
            gui_ga_xabar_yuborish(
                f"🤖 Men Misa AI yordamchiman! {ism} uchun yaratilganman."
            )
            ovoz_chiqar_tez(
                f"Men Misa, sun'iy intellektga ega shaxsiy yordamchiman. "
                f"{ism}, siz uchun har doim xizmatdaman!"
            )

        # ========== Video boshqaruvi ==========
        elif intent == "youtube_first_video":
            webbrowser.open("https://www.youtube.com")
            global_state.youtube_ochiq = True
            time.sleep(3)
            youtube_video_boshla_koordinata(1)
        elif intent == "play_video":
            youtube_video_play()
        elif intent == "pause_video":
            youtube_video_pause()
        elif intent == "next_video":
            youtube_keyingi_video()
        elif intent == "prev_video":
            youtube_oldingi_video()
        elif intent == "close_chrome":
            chrome_oyna_yop_aqlli()

        # ========== Musiqa boshqaruvi ==========
        elif intent in ("music_pause", "music_play"):
            # Media Play/Pause tugma — tizim darajasida ishlaydi
            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
            if intent == "music_pause":
                gui_ga_xabar_yuborish("⏸️ Musiqa to'xtatildi")
                ovoz_chiqar_tez("Musiqa to'xtatildi")
            else:
                gui_ga_xabar_yuborish("▶️ Musiqa davom etmoqda")
                ovoz_chiqar_tez("Musiqa davom etmoqda")
        elif intent == "music_restart":
            ctypes.windll.user32.keybd_event(0xB2, 0, 0, 0)  # STOP
            ctypes.windll.user32.keybd_event(0xB2, 0, 2, 0)
            time.sleep(0.3)
            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)  # PLAY
            ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
            ovoz_chiqar_tez("Musiqa boshidan boshlandi")
        elif intent == "music_search":
            # AI dan query kelgan bo'lsa, to'g'ridan-to'g'ri qidirish
            query = params.get("query", "")
            if query:
                musiqa_qidir(query)
            else:
                # Regex pipeline — matndan qo'shiq nomini ajratish
                _musiqa_search_matn(matn)

        # ========== Vaqt / Sana ==========
        elif intent == "time":
            current_time = time.strftime("%H:%M")
            gui_ga_xabar_yuborish(f"⏰ Hozir soat {current_time}")
            ovoz_chiqar_tez(f"Hozir soat {current_time}")
        elif intent == "date":
            current_date = time.strftime("%d %B %Y")
            gui_ga_xabar_yuborish(f"📅 Bugun {current_date}")
            ovoz_chiqar_tez(f"Bugun {current_date}")

        # ========== Ob-havo ==========
        elif intent == "weather":
            shahar = params.get("city", "") or params.get("query", "")
            if not shahar and matn:
                # Regex pipeline — matndan shahar olish
                shahar = matn if isinstance(matn, str) else ""
                for soz in [
                    "havo",
                    "ob-havo",
                    "harorat",
                    "qanaqa",
                    "qanday",
                    "hozir",
                    "bugun",
                    "necha",
                    "daraja",
                    "gradus",
                ]:
                    shahar = shahar.replace(soz, "")
                shahar = shahar.strip().strip("da").strip("ga").strip()
            if not shahar:
                shahar = "Tashkent"
            gui_ga_xabar_yuborish("🌤️ Ob-havo tekshirilmoqda...")
            gui_matn, ovoz_matn = ob_havo_olish(shahar)
            if gui_matn:
                gui_ga_xabar_yuborish(gui_matn)
                ovoz_chiqar_tez(ovoz_matn)
            else:
                gui_ga_xabar_yuborish(f"❌ {ovoz_matn}")
                ovoz_chiqar_tez(ovoz_matn)

        # ========== Qidirish ==========
        elif intent == "search":
            query = params.get("query", "")
            if not query:
                ovoz_chiqar_tez("Niman qidiraylik?")
                query = tingla()
            if query:
                url = f"https://www.google.com/search?q={quote_plus(query)}"
                webbrowser.open(url)
                gui_ga_xabar_yuborish(f"🔍 '{query}' qidirilmoqda")
                ovoz_chiqar_tez(f"{query} qidirilmoqda")

        # ========== Eslatmalar ==========
        elif intent == "reminder":
            eslatma_matni = (
                params.get("text", "")
                or params.get("query", "")
                or params.get("reminder", "")
            )
            if not eslatma_matni:
                ovoz_chiqar_tez("Nima eslataylik?")
                eslatma_matni = tingla()
            if eslatma_matni:
                eslatma_qoshish(eslatma_matni)
        elif intent == "reminders":
            eslatmalarni_o_qish()
        elif intent == "delete_reminder":
            eslatma_o_chirish()

        # ========== Tizim buyruqlari ==========
        elif intent == "shutdown":
            gui_ga_xabar_yuborish("⚠️ Kompyuter 60 soniyada o'chiriladi...")
            ovoz_chiqar_tez("Kompyuter bir daqiqada o'chiriladi")
            subprocess.run(["shutdown", "/s", "/t", "60"], shell=False)
        elif intent == "restart":
            gui_ga_xabar_yuborish("🔄 Kompyuter 60 soniyada qayta yuklanadi...")
            ovoz_chiqar_tez("Kompyuter bir daqiqada qayta yuklanadi")
            subprocess.run(["shutdown", "/r", "/t", "60"], shell=False)
        elif intent == "lock":
            gui_ga_xabar_yuborish("🔒 Ekran qulflanmoqda...")
            ovoz_chiqar_tez("Ekran qulflanmoqda")
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], shell=False)

        # ========== AI suhbat rejimi ==========
        elif intent == "chat_mode":
            if not AI_AVAILABLE:
                gui_ga_xabar_yuborish("❌ AI moduli topilmadi", ovoz=True)
            else:
                ovoz_chiqar_tez("AI rejimidaman. Nima haqida gaplashamiz?")
                while global_state.tinglash_faol:
                    savol = tingla()
                    if savol:
                        if any(
                            s in savol.lower()
                            for s in ["chiq", "to'xta", "yetadi", "bo'ldi", "rahmat"]
                        ):
                            ovoz_chiqar_tez(
                                "AI rejimdan chiqdim. Buyruqlaringizni kutaman."
                            )
                            break
                        openrouter_ai_suhbat(savol)

        # ========== Windows shortcutlar ==========
        elif intent == "show_desktop":
            keyboard.send("win+d")
            gui_ga_xabar_yuborish("🖥️ Ish stoli ko'rsatildi")
            ovoz_chiqar_tez("Ish stoli ko'rsatildi")
        elif intent == "switch_window":
            keyboard.send("alt+tab")
            ovoz_chiqar_tez("Oyna almashtirildi")
        elif intent == "open_explorer":
            keyboard.send("win+e")
            gui_ga_xabar_yuborish("📁 Fayl menejeri ochildi")
            ovoz_chiqar_tez("Fayl menejeri ochildi")
        elif intent == "open_cmd":
            subprocess.Popen(["cmd"], creationflags=subprocess.CREATE_NEW_CONSOLE)
            gui_ga_xabar_yuborish("💻 Terminal ochildi")
            ovoz_chiqar_tez("Terminal ochildi")
        elif intent == "open_taskmanager":
            keyboard.send("ctrl+shift+esc")
            gui_ga_xabar_yuborish("📊 Vazifa menejeri ochildi")
            ovoz_chiqar_tez("Vazifa menejeri ochildi")
        elif intent == "close_window":
            keyboard.send("alt+F4")
            ovoz_chiqar_tez("Oyna yopildi")
        elif intent == "task_view":
            keyboard.send("win+tab")
            ovoz_chiqar_tez("Barcha oynalar ko'rsatildi")
        elif intent == "open_settings":
            keyboard.send("win+i")
            gui_ga_xabar_yuborish("⚙️ Sozlamalar ochildi")
            ovoz_chiqar_tez("Sozlamalar ochildi")
        elif intent == "take_screenshot":
            keyboard.send("win+shift+s")
            ovoz_chiqar_tez("Ekran rasmi olish tanlandi")
        elif intent == "open_run":
            keyboard.send("win+r")
            ovoz_chiqar_tez("Ishga tushirish oynasi ochildi")
        elif intent == "minimize_all":
            keyboard.send("win+m")
            gui_ga_xabar_yuborish("⬇️ Barcha oynalar kichraytirildi")
            ovoz_chiqar_tez("Barcha oynalar kichraytirildi")

        else:
            # Buyruq topilmadi — False qaytarish (Agent ga yuborish kerak)
            return False

        return True
    except Exception as e:
        logging.error(f"Intent bajarishda xato ({intent}): {e}")
        return True  # Xato bo'lsa ham, buyruq tanildi — Agent ga yuborish shart emas


def toza_musiqa_nomi(matn):
    """Buyruq matnidan toza qo'shiq/trek nomini ajratib olish"""
    text = matn.strip()

    # Boshidagi undov va platforma prefikslarini tozalash:
    patterns_head = [
        r"^(?:(?:hey|salom|iltimos|menga|bitta|biror|bir|misajon|misa|misajon|misa)\s+)+",
        r"^(?:youtube|youtub|yutub|yutuq|yandex|yandeks|яндекс|spotify)(?:\s*music)?(?:\s*(?:dan|da|dagi|ga))?\s*",
        r"^(?:menga|iltimos|bitta|biror|bir)\s+",
    ]
    changed = True
    while changed:
        changed = False
        for p in patterns_head:
            new_text = re.sub(p, "", text, flags=re.IGNORECASE).strip()
            if new_text != text:
                text = new_text
                changed = True

    # Oxiridagi fe'l va media so'zlarni tozalash:
    patterns_tail = [
        r"\s*(?:qo['‘`ʼʻ]?shig['‘`ʼʻ]?(?:ini|i|ni)?|qoshig(?:ini|i|ni)?|qo['‘`ʼʻ]?shiq(?:ni)?|qoshiq(?:ni)?)\s*$",
        r"\s*(?:musiqa(?:si|sini|ni)?|trek(?:i|ini|ni)?|ashula(?:si|sini|ni)?|klip(?:i|ini|ni)?|video(?:si|sini|ni)?)\s*$",
        r"\s*(?:qo['‘`ʼʻ]?yib\s*ber(?:ing)?|qoyib\s*ber(?:ing)?|qo['‘`ʼʻ]?y(?:ing)?|qoy(?:ing)?|ijro\s*et(?:ing)?)\s*$",
        r"\s*(?:eshitaylik|eshitay|tinglaylik|tinglay|eshitamiz|tinglaymiz|eshitmoqchiman|tinglamoqchiman)\s*$",
        r"\s*(?:ochib\s*ber|och|ber|play|ijro)\s*$",
        r"\s*(?:qo['‘`ʼʻ]?shig['‘`ʼʻ]?(?:ini|i|ni)?|qoshig(?:ini|i|ni)?|qo['‘`ʼʻ]?shiq|qoshiq)\s*$",
        r"\s*(?:musiqasi|musiqasini|musiqa|treki|trek|ashulasi|ashula)\s*$",
        r"\s*(?:qo['‘`ʼʻ]?yib|qoyib|qo['‘`ʼʻ]?y|qoy)\s*$",
    ]
    changed = True
    while changed:
        changed = False
        for p in patterns_tail:
            new_text = re.sub(p, "", text, flags=re.IGNORECASE).strip()
            if new_text != text:
                text = new_text
                changed = True

    return text.strip(' .,!?"\'')


def _musiqa_search_matn(matn):
    """Regex pipeline uchun musiqa qidirish — matndan qo'shiq nomini ajratish"""
    matn_l = matn.lower()
    matn_toza = matnni_tozalash(matn_l)

    # "Mening to'lqinim" (My Wave) — AVVAL tekshirish (har doim Yandex)
    if "tolqin" in matn_toza or "волна" in matn_l:
        webbrowser.open("https://music.yandex.uz")
        gui_ga_xabar_yuborish("🎵 Yandex Music — Mening to'lqinim")
        ovoz_chiqar_tez("Yandex Music'da mening to'lqinim qo'yilmoqda")

        def _auto_play():
            try:
                time.sleep(12)

                # Brauzerni fokusga olish (Alt trick)
                try:
                    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
                    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
                    time.sleep(0.3)
                    hwnd_list = []

                    def enum_cb(hwnd, _):
                        if ctypes.windll.user32.IsWindowVisible(hwnd):
                            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                            if length > 0:
                                buf = ctypes.create_unicode_buffer(length + 1)
                                ctypes.windll.user32.GetWindowTextW(
                                    hwnd, buf, length + 1
                                )
                                title = buf.value.lower()
                                if "chrome" in title or "yandex" in title:
                                    hwnd_list.append(hwnd)
                            return True

                    WNDENUMPROC = ctypes.WINFUNCTYPE(
                        ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
                    )
                    ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
                    if hwnd_list:
                        ctypes.windll.user32.SetForegroundWindow(hwnd_list[0])
                        logging.debug(f"My Wave: brauzer fokusga olindi")
                    time.sleep(1)
                except Exception as e:
                    logging.debug(f"My Wave fokus: {e}")

                screen_w, screen_h = pyautogui.size()

                # Play — bir necha joyni bosib ko'rish
                for i, y_ratio in enumerate([0.33, 0.37, 0.30, 0.42]):
                    px, py = screen_w // 2, int(screen_h * y_ratio)
                    pyautogui.click(px, py)
                    logging.debug(f"My Wave: click ({px},{py}) urinish {i + 1}")
                    time.sleep(2)

                    if AI_AVAILABLE and i < 2:
                        tekshiruv = buyruq_tekshir(
                            "Yandex Music'da 'Mening to'lqinim' play bosdim",
                            "YANGI trek boshlanishi kerak — progress bar 00:01 yoki 00:02 ko'rsatmoqda, "
                            "YOKI sahifa radio rejimiga o'tgan. "
                            "DIQQAT: pastdagi mini-player'da ESKI trek turishi mumkin — bu play boshlangani emas!",
                        )
                        if tekshiruv.get("muvaffaqiyat"):
                            logging.debug("My Wave: MUVAFFAQIYAT!")
                            return
                        logging.debug(f"My Wave: {tekshiruv.get('tavsif', '')[:60]}")

                pyautogui.press("space")
                logging.debug("My Wave: fallback Space")

            except Exception as e:
                logging.warning(f"My Wave xatolik: {e}")

        threading.Thread(target=_auto_play, daemon=True).start()
        return

    # Platformani aniqlash
    if "yandex" in matn_toza or "yandeks" in matn_toza or "яндекс" in matn_l:
        platform = "yandex"
    elif "spotify" in matn_toza:
        platform = "spotify"
    else:
        platform = "youtube"

    # Qo'shiq nomini buyruqdan ajratib olish
    query = toza_musiqa_nomi(matn)

    if not query or len(query) < 2:
        ovoz_chiqar_tez("Qaysi qo'shiqni qo'yay?")
        query = tingla()
        if query:
            query = toza_musiqa_nomi(query) or query.strip()

    if query:
        platform_nomi = {
            "youtube": "YouTube",
            "yandex": "Yandex Music",
            "spotify": "Spotify",
        }
        gui_ga_xabar_yuborish(f"🎵 '{query}' {platform_nomi.get(platform, 'YouTube')}da qo'yilmoqda...")
        musiqa_qidir(query, platform)
    else:
        ovoz_chiqar_tez("Qo'shiq nomini eshitmadim. Qaytadan aytib ko'ring.")


# ========== Tarix saqlash ==========
def buyruqni_saqla(matn):
    try:
        fayl = os.path.join(BASE_DIR, "buyruqlar_tarixi.txt")
        with open(fayl, "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {matn}\n"
            )

        # Rotatsiya — 500 ta qatordan oshsa, eski qatorlarni kesish
        try:
            with open(fayl, "r", encoding="utf-8") as f:
                qatorlar = f.readlines()
            if len(qatorlar) > 500:
                with open(fayl, "w", encoding="utf-8") as f:
                    f.writelines(qatorlar[-300:])  # Oxirgi 300 tasini saqlash
                logging.debug(f"Buyruq tarixi rotatsiya: {len(qatorlar)} → 300")
        except Exception:
            pass
    except Exception as e:
        logging.error(f"Buyruq saqlash xatolik: {e}")


# ========== Eslatmalar ==========
def eslatma_qoshish(eslatma_matni):
    try:
        sana = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fayl = os.path.join(BASE_DIR, "eslatmalar.txt")
        with open(fayl, "a", encoding="utf-8") as f:
            f.write(f"[{sana}] {eslatma_matni}\n")
        gui_ga_xabar_yuborish(f"✅ Eslatma saqlandi")
        ovoz_chiqar_tez("Eslatma saqlandi")
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Eslatma saqlanmadi", ovoz=True)


def eslatma_o_chirish(raqam=None):
    """Eslatmani o'chirish. raqam=None bo'lsa oxirgi eslatmani o'chiradi."""
    try:
        fayl = os.path.join(BASE_DIR, "eslatmalar.txt")
        if not os.path.exists(fayl):
            gui_ga_xabar_yuborish("📌 Eslatmalar yo'q", ovoz=True)
            return

        with open(fayl, "r", encoding="utf-8") as f:
            eslatmalar = f.readlines()

        if not eslatmalar:
            gui_ga_xabar_yuborish("📌 Eslatmalar yo'q", ovoz=True)
            return

        if raqam is not None and 1 <= raqam <= len(eslatmalar):
            o_chirilgan = eslatmalar.pop(raqam - 1).strip()
        else:
            o_chirilgan = eslatmalar.pop().strip()

        with open(fayl, "w", encoding="utf-8") as f:
            f.writelines(eslatmalar)

        gui_ga_xabar_yuborish(f"✅ Eslatma o'chirildi: {o_chirilgan}")
        ovoz_chiqar_tez("Eslatma o'chirildi")
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Eslatma o'chirilmadi: {e}", ovoz=True)


def eslatmalarni_o_qish():
    try:
        fayl = os.path.join(BASE_DIR, "eslatmalar.txt")
        if not os.path.exists(fayl):
            gui_ga_xabar_yuborish("📌 Eslatmalar yo'q", ovoz=True)
            return

        with open(fayl, "r", encoding="utf-8") as f:
            eslatmalar = f.readlines()

        if not eslatmalar:
            gui_ga_xabar_yuborish("📌 Eslatmalar yo'q", ovoz=True)
            return

        gui_ga_xabar_yuborish(f"📌 {len(eslatmalar)} ta eslatma bor")
        ovoz_chiqar_tez(f"Sizda {len(eslatmalar)} ta eslatma bor")

        for idx, eslatma in enumerate(eslatmalar[-5:], 1):
            if eslatma.strip():
                gui_ga_xabar_yuborish(f"{idx}. {eslatma.strip()}")
    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Eslatmalar o'qilmadi", ovoz=True)


# ========== Buyruqni bajarish ==========
def buyruqni_tushun(matn, foydalanuvchi_ismi, ovoz_turi):
    """Unified Pipeline: Tezkor buyruqlar → Agent"""
    try:
        with global_state.buyruq_bajarilmoqda_lock:
            global_state.ovoz_turi_global = ovoz_turi
            buyruqni_saqla(matn)

        # v6.0.0: Tezkor Mahalliy Buyruqlar (Command Dispatcher)
        if COMMAND_DISPATCHER_AVAILABLE and command_dispatcher:
            try:
                handled, result_msg = command_dispatcher.dispatch_local(matn)
                if handled and result_msg:
                    try:
                        from core.voice.session_manager import get_session_manager
                        get_session_manager().record_turn(matn, result_msg)
                    except Exception:
                        pass
                    gui_ga_xabar_yuborish(f"✨ {result_msg}", ovoz=True)
                    return
            except Exception as e:
                logging.debug(f"Dispatcher xatosi: {e}")

        # 1-QADAM: TEZKOR BUYRUQLAR (regex faqat aniq patternlar uchun)
        intent = buyruqni_aniqla(matn)

        # Tuple (buyruq, qiymat) — ovoz/video kabi
        if isinstance(intent, tuple):
            buyruq, qiymat = intent[0], intent[1]
            if buyruq == "volume_set":
                ovoz_sozlash(qiymat)
            elif buyruq == "volume_up":
                ovoz_oshir(qiymat)
            elif buyruq == "volume_down":
                ovoz_pasaytir(qiymat)
            elif buyruq == "video_number":
                youtube_video_boshla_koordinata(qiymat)
            return

        # Oddiy buyruq — to'g'ridan-to'g'ri bajarish
        if intent != "unknown":
            _intent_bajar(
                intent, params=None, matn=matn, foydalanuvchi_ismi=foydalanuvchi_ismi
            )
            return

        # 2-QADAM: QOLGAN HAMMASI → Agent Pipeline
        agent_pipeline_run(matn)

    except Exception as e:
        gui_ga_xabar_yuborish(f"❌ Xatolik buyruqni bajarishda: {e}", ovoz=True)


# ========== Orqa fon ==========
def fon_xizmat(foydalanuvchi_ismi, ovoz_turi, gui_callback_func=None):
    global_state.tinglash_faol = True
    global_state.ovoz_turi_global = ovoz_turi

    gui_bilan_integratsiya(gui_callback_func)
    gui_ga_xabar_yuborish(f"👋 Salom, {foydalanuvchi_ismi}!", ovoz=True)
    gui_ga_xabar_yuborish("🎙️ Tinglash boshlandi...")

    while global_state.tinglash_faol:
        try:
            buyruq = tingla()
            if buyruq and global_state.tinglash_faol:
                gui_ga_xabar_yuborish(f"📝 Buyruq: {buyruq}")
                buyruqni_tushun(buyruq, foydalanuvchi_ismi, ovoz_turi)
                time.sleep(0.5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            gui_ga_xabar_yuborish(f"❌ Xatolik: {e}", ovoz=True)
            time.sleep(1)

    gui_ga_xabar_yuborish("🛑 Tinglash to'xtatildi", ovoz=True)


def fon_xizmat_toxtat():
    global_state.tinglash_faol = False


# ========== GUI ==========
def gui_ishga_tushir():
    foydalanuvchi_ismi = foydalanuvchi_ismi_ol()
    ovoz_turi = ovoz_turi_ol()

    # Windows Audio API tekshiruvi - endi pycaw ishlatiladi
    print("✅ Windows Audio API orqali ovoz boshqaruvi tayyor")

    # Yangi GUI ni ishlatish
    try:
        from customtkinter.windows.widgets.core_rendering import DrawEngine
        DrawEngine.preferred_drawing_method = "circle_shapes"

        from gui.app import MisaApp

        print("🔷 MISA AI — Yangi GUI ishga tushmoqda...")
        app = MisaApp(connect_backend=True)
        app.mainloop()
    except ImportError:
        # Yangi GUI topilmasa — eski GUI
        try:
            from gui_old import gui_ishga_tushir as eski_gui

            eski_gui(foydalanuvchi_ismi, ovoz_turi, fon_xizmat, gui_bilan_integratsiya)
        except ImportError as e:
            messagebox.showerror("Xatolik", f"GUI topilmadi!\n{e}")
    except Exception as e:
        logging.critical(f"GUI xatolik: {e}", exc_info=True)
        messagebox.showerror("Xatolik", f"Dastur ishga tushmadi:\n{e}")


def main():
    import sys
    import traceback

    # Global exception handler — thread lardagi xatolarni ham ushlash
    def global_exception_handler(exc_type, exc_value, exc_tb):
        if exc_type == KeyboardInterrupt:
            print("\n👋 Dastur to'xtatildi")
            return
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.critical(f"Kutilmagan xatolik:\n{error_msg}")
        print(f"\n❌ Kutilmagan xatolik:\n{error_msg}")

    sys.excepthook = global_exception_handler

    # Thread exception handler (Python 3.8+)
    def threading_exception_handler(args):
        logging.error(
            f"Thread '{args.thread.name}' xatolik: {args.exc_value}",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = threading_exception_handler

    try:
        gui_ishga_tushir()
    except KeyboardInterrupt:
        print("\n👋 Dastur to'xtatildi")
    except Exception as e:
        logging.critical(f"Dastur crash: {e}", exc_info=True)
        print(f"\n❌ Dastur kutilmagan xatolik bilan yopildi:\n{e}")
        print("Log faylini tekshiring: debug.log")


if __name__ == "__main__":
    main()
