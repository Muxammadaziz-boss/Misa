# ========== command_dispatcher.py ==========
# Misa AI v6.0.0 — Mahalliy va AI Buyruqlarni Taqsimlash Xizmati (Command Dispatcher)
# Tezkor mahalliy buyruqlar va murakkab AI topshiriqlarini boshqarish

import os
import re
import logging
import datetime
import webbrowser
import platform
import psutil
import socket
import shutil
try:
    import winreg  # type: ignore
    WINREG_AVAILABLE = True
except ImportError:
    winreg = None  # type: ignore
    WINREG_AVAILABLE = False
from typing import Tuple, Optional, Dict, Any, Callable
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

try:
    from core.smart_algorithms import aqlli_buyruq_aniqla, xavfli_buyruqmi
    SMART_ALGO_AVAILABLE = True
except ImportError:
    SMART_ALGO_AVAILABLE = False


# =========================================================================
# 1. APPARAT VA TIZIM MA'LUMOTLARI (QISQA VA TO'LIQ DETALLI)
# =========================================================================

def get_system_gpus() -> list:
    """Tizimdagi barcha faol videokartalarni VRAM va drayver versiyalari bilan aniq olish"""
    gpus = []
    if not WINREG_AVAILABLE or winreg is None:
        return gpus
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}') as root_gpu:
            count_gpu = winreg.QueryInfoKey(root_gpu)[0]
            for i in range(count_gpu):
                sub = winreg.EnumKey(root_gpu, i)
                if sub.isdigit():
                    try:
                        with winreg.OpenKey(root_gpu, sub) as k:
                            desc, _ = winreg.QueryValueEx(k, 'DriverDesc')
                            if not desc:
                                continue
                            drv_ver = ""
                            try:
                                drv_ver, _ = winreg.QueryValueEx(k, 'DriverVersion')
                            except Exception:
                                pass
                            vram_gb = 0.0
                            for mem_key in ['HardwareInformation.qwMemorySize', 'HardwareInformation.MemorySize']:
                                try:
                                    raw_bytes, _ = winreg.QueryValueEx(k, mem_key)
                                    if raw_bytes and raw_bytes > 0:
                                        vram_gb = round(raw_bytes / (1024**3), 1)
                                        break
                                except Exception:
                                    pass
                            gpus.append({
                                "name": str(desc).strip(),
                                "driver": str(drv_ver).strip(),
                                "vram_gb": vram_gb
                            })
                    except Exception:
                        pass
    except Exception:
        pass
    return gpus


def get_system_specs_summary() -> str:
    """Kompyuterning asosiy apparat parametrlarini qisqa olish"""
    try:
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
        node_name = platform.node()
        cpu_name = platform.processor() or "Standart protsessor"
        if WINREG_AVAILABLE and winreg is not None:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
                    reg_name, _ = winreg.QueryValueEx(k, 'ProcessorNameString')
                    if reg_name:
                        cpu_name = str(reg_name).strip()
            except Exception:
                pass

        gpu_items = get_system_gpus()
        gpus = [g["name"] + (f" ({g['vram_gb']} GB)" if g.get("vram_gb") else "") for g in gpu_items]

        cores_p = psutil.cpu_count(logical=False) or 1
        cores_l = psutil.cpu_count(logical=True) or 1
        cpu_usage = psutil.cpu_percent(interval=0.1)

        mem = psutil.virtual_memory()
        total_ram = round(mem.total / (1024**3), 1)
        used_ram = round(mem.used / (1024**3), 1)
        free_ram = round(mem.available / (1024**3), 1)

        disks = []
        for part in psutil.disk_partitions(all=False):
            if "cdrom" in part.opts or part.fstype == "":
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                free_gb = round(usage.free / (1024**3), 1)
                total_gb = round(usage.total / (1024**3), 1)
                drive = part.mountpoint.rstrip("\\")
                disks.append(f"{drive} ({free_gb} GB bo'sh / {total_gb} GB)")
            except Exception:
                pass
        disks_str = ", ".join(disks) if disks else "Aniqlanmadi"

        lines = [
            "🖥️ Kompyuteringiz parametrlari:",
            f"• Operatsion tizim: {os_info}",
            f"• Kompyuter nomi: {node_name}",
            f"• Protsessor (CPU): {cpu_name} ({cores_p} fiz / {cores_l} mantiqiy yadro, {cpu_usage}% band)",
        ]
        if gpus:
            lines.append(f"• Videokarta (GPU): {', '.join(gpus)}")
        lines.extend([
            f"• Tezkor xotira (RAM): {total_ram} GB (Ishlatilmoqda: {used_ram} GB, Bo'sh: {free_ram} GB, {mem.percent}%)",
            f"• Disk xotirasi: {disks_str}"
        ])

        bat = psutil.sensors_battery()
        if bat:
            plug = "tarmoqqa ulangan" if bat.power_plugged else "batareyada"
            lines.append(f"• Batareya quvvati: {bat.percent}% ({plug})")

        return "\n".join(lines)
    except Exception as e:
        return f"Tizim parametrlarini aniqlashda xatolik: {e}"


def get_system_specs_detailed() -> str:
    """Kompyuterning barcha to'liq texnik ma'lumotlarini olish (CPU, GPU, RAM, Swap, Disks, IP, Uptime)"""
    try:
        lines = []
        lines.append("🖥️ Kompyuteringizning to'liq texnik ma'lumotlari:")

        # 1. Operatsion tizim va Kompyuter
        os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"
        win_version = platform.version()
        lines.append(f"• Operatsion tizim: {os_name} (Build {win_version})")
        lines.append(f"• Kompyuter nomi: {platform.node()}")
        try:
            lines.append(f"• Joriy tizim foydalanuvchisi: {os.getlogin()}")
        except Exception:
            pass

        # Uptime
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            d = uptime.days
            h = int((uptime.total_seconds() % 86400) // 3600)
            m = int((uptime.total_seconds() % 3600) // 60)
            uptime_str = f"{d} kun, {h} soat, {m} daqiqa" if d > 0 else f"{h} soat, {m} daqiqa"
            lines.append(f"• Ish vaqti (Uptime): {uptime_str} (Yoqilgan vaqt: {boot_time.strftime('%H:%M, %d-%m-%Y')})")
        except Exception:
            pass

        # 2. Protsessor (CPU)
        cpu_name = platform.processor() or "Standart protsessor"
        if WINREG_AVAILABLE and winreg is not None:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
                    reg_name, _ = winreg.QueryValueEx(k, 'ProcessorNameString')
                    if reg_name:
                        cpu_name = reg_name.strip()
            except Exception:
                pass
        cores_p = psutil.cpu_count(logical=False) or 1
        cores_l = psutil.cpu_count(logical=True) or 1
        cpu_usage = psutil.cpu_percent(interval=0.1)

        freq_str = ""
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current:
                freq_str = f" @ {round(freq.current / 1000, 2)} GHz"
        except Exception:
            pass
        lines.append(f"• Protsessor (CPU): {cpu_name}{freq_str} ({cores_p} fiz / {cores_l} mantiqiy yadro, {cpu_usage}% band)")

        # 3. Videokarta (GPU)
        if WINREG_AVAILABLE and winreg is not None:
            try:
                gpus = []
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}') as root_gpu:
                    num_subkeys = winreg.QueryInfoKey(root_gpu)[0]
                    for i in range(num_subkeys):
                        sub = winreg.EnumKey(root_gpu, i)
                        if sub.isdigit():
                            try:
                                with winreg.OpenKey(root_gpu, sub) as k:
                                    desc, _ = winreg.QueryValueEx(k, 'DriverDesc')
                                    if desc and desc not in gpus:
                                        gpus.append(desc)
                            except Exception:
                                pass
                if gpus:
                    lines.append(f"• Videokarta (GPU): {', '.join(gpus)}")
            except Exception:
                pass

        # 4. Tezkor xotira (RAM)
        mem = psutil.virtual_memory()
        total_ram = round(mem.total / (1024**3), 1)
        used_ram = round(mem.used / (1024**3), 1)
        free_ram = round(mem.available / (1024**3), 1)
        lines.append(f"• Tezkor xotira (RAM): {total_ram} GB (Ishlatilmoqda: {used_ram} GB, Bo'sh: {free_ram} GB, {mem.percent}%)")

        # Virtual xotira (Pagefile/Swap)
        try:
            swap = psutil.swap_memory()
            swap_total = round(swap.total / (1024**3), 1)
            swap_used = round(swap.used / (1024**3), 1)
            if swap_total > 0:
                lines.append(f"• Virtual xotira (Pagefile): {swap_total} GB (Ishlatilmoqda: {swap_used} GB, {swap.percent}%)")
        except Exception:
            pass

        # 5. Disklar
        disks = []
        for part in psutil.disk_partitions(all=False):
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                free_gb = round(usage.free / (1024**3), 1)
                total_gb = round(usage.total / (1024**3), 1)
                drive = part.mountpoint.rstrip('\\')
                fstype = f" [{part.fstype}]" if part.fstype else ""
                disks.append(f"{drive}{fstype} ({free_gb} GB bo'sh / {total_gb} GB, {usage.percent}% band)")
            except Exception:
                pass
        if disks:
            lines.append(f"• Disk xotiralari:\n  " + "\n  ".join(f"- {d}" for d in disks))

        # 6. Tarmoq (Network)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip_addr = s.getsockname()[0]
            s.close()
            lines.append(f"• Mahalliy tarmoq (IP): {ip_addr}")
        except Exception:
            pass

        # 7. Quvvat manbai
        bat = psutil.sensors_battery()
        if bat:
            plug = "tarmoqqa ulangan" if bat.power_plugged else "batareyada"
            lines.append(f"• Batareya holati: {bat.percent}% ({plug})")
        else:
            lines.append("• Quvvat manbai: Statsionar kompyuter (Doimiy elektr tarmog'ida)")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"To'liq tizim parametrlarini olishda xatolik: {e}")
        return get_system_specs_summary()


# =========================================================================
# 2. ILOVALARNI TEKSHIRISH VA ANIQ ISHGA TUSHIRISH (APP INTELLIGENCE)
# =========================================================================

KNOWN_APPS: Dict[str, Dict[str, Any]] = {
    "telegram": {
        "title": "Telegram Desktop",
        "protocol": "tg:",
        "exe_names": ["telegram.exe", "ayugram.exe", "kotatogram.exe", "64gram.exe"],
        "paths": [
            r"D:\Telegram akklar\AyuGram\AyuGram.exe",
            r"%APPDATA%\Telegram Desktop\Telegram.exe",
            r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe",
            r"%PROGRAMFILES%\Telegram Desktop\Telegram.exe",
            r"%PROGRAMFILES(X86)%\Telegram Desktop\Telegram.exe",
        ],
        "web_url": "https://web.telegram.org"
    },
    "ayugram": {
        "title": "AyuGram Desktop (Telegram)",
        "protocol": "tg:",
        "exe_names": ["ayugram.exe"],
        "paths": [
            r"D:\Telegram akklar\AyuGram\AyuGram.exe",
            r"%APPDATA%\AyuGram Desktop\AyuGram.exe",
            r"%LOCALAPPDATA%\Programs\AyuGram Desktop\AyuGram.exe",
        ],
        "web_url": "https://web.telegram.org"
    },
    "chrome": {
        "title": "Google Chrome",
        "protocol": "",
        "exe_names": ["chrome.exe"],
        "paths": [
            r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe",
            r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe",
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        ],
        "web_url": "https://www.google.com"
    },
    "code": {
        "title": "Visual Studio Code",
        "protocol": "vscode:",
        "exe_names": ["code.exe", "code.cmd"],
        "paths": [
            r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
            r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
        ],
        "web_url": "https://code.visualstudio.com"
    },
    "discord": {
        "title": "Discord",
        "protocol": "discord:",
        "exe_names": ["discord.exe", "update.exe"],
        "paths": [
            r"%LOCALAPPDATA%\Discord\Update.exe",
        ],
        "web_url": "https://discord.com"
    },
    "brave": {
        "title": "Brave Browser",
        "protocol": "",
        "exe_names": ["brave.exe"],
        "paths": [
            r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
        ],
        "web_url": "https://brave.com"
    }
}


def find_installed_app(app_key: str) -> Tuple[bool, bool, str, str]:
    """
    Ilovaning kompyuterda mavjudligini aniqlash (chuqur jarayonlar, registri va disk qidiruvi).
    Qaytaradi: (o'rnatilganmi, ishlab_turibdimi, joylashgan_yo'li, rasmiy_nomi)
    """
    try:
        from core.app_detector import get_app_detector
        info = get_app_detector().detect_app(app_key)
        return info.found, info.running, info.exe_path, info.name
    except Exception as e:
        logger.warning(f"App detector xatolik ({app_key}): {e}")
        return False, False, "", app_key.capitalize()


def is_question_phrase(text: str) -> bool:
    """Matn savol yoki mantiqiy so'rov ekanligini aniqlash"""
    clean = text.lower().strip()
    if "?" in clean:
        return True

    question_keywords = [
        "bormi", "bormikan", "bormikin", "mavjudmi", "o'rnatilganmi", "ornatilganmi",
        "nima", "qanday", "qanaqa", "necha", "qachon", "kim", "kimniki", "nega",
        "sababi", "haqida", "bilasanmi", "bilasan", "tushuntir", "aytib ber", "maslahat"
    ]
    return any(re.search(rf"\b{re.escape(kw)}\b", clean) for kw in question_keywords)


# =========================================================================
# 3. ASOSIY COMMAND DISPATCHER KLASSI
# =========================================================================

class CommandDispatcher:
    """
    Buyruqlarni tezkor mahalliy bajarish va AI agentiga yo'naltirish xizmati.
    Mantiqiy savollar va apparat so'rovlarini to'g'ri taqsimlaydi.
    """

    def __init__(self, tts_speak_func: Optional[Callable[[str], None]] = None):
        self.speak_func = tts_speak_func
        self._custom_handlers: Dict[str, Callable] = {}

    def register_handler(self, intent: str, handler: Callable):
        """Maxsus buyruq handlerini ro'yxatdan o'tkazish"""
        self._custom_handlers[intent] = handler

    def dispatch_local(self, text: str, user_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Matn mahalliy tizim buyrug'i ekanligini tekshirish va bajarish.
        Agar mahalliy buyruq yoki tizim so'rovi bo'lsa: (True, "natija xabari")
        Agar AI tahlili/suhbat talab qilinsa: (False, "")
        """
        clean_text = text.lower().strip()
        if not clean_text:
            return True, "Bo'sh so'rov kiritildi."

        has_question = is_question_phrase(clean_text)

        # -------------------------------------------------------------
        # 0. Foydalanuvchi va Misa identifikatsiyasi (Identity queries)
        # -------------------------------------------------------------
        clean_no_punct = re.sub(r"[?!.,;:_`*~#]+", "", clean_text).strip()
        user_display = (user_name or "").strip()
        if not user_display or user_display.lower() in ["user", "foydalanuvchi", "none"]:
            try:
                from config import get_config
                cfg_user = get_config("user_name")
                if cfg_user:
                    user_display = str(cfg_user).strip()
            except Exception:
                pass
        if not user_display or user_display.lower() in ["user", "foydalanuvchi", "none"]:
            user_display = "Ustoz"

        # -------------------------------------------------------------
        # 0.1. Misa chaqiruv so'zi (Wake-word / Call prefix: "Misa ...")
        # -------------------------------------------------------------
        misa_call_match = re.match(r"^(?:(?:salom|assalomu\s+alaykum|hey|ey|o['']?y|hoy|qani|iltimos)\s+)?(?:misa|mikasa|micasa|миса|микаса|мекаса|mekasa)(?:[,\s:!.]*|$)", clean_text, re.IGNORECASE)
        if misa_call_match:
            sub_command = clean_text[misa_call_match.end():].strip()
            if not sub_command or len(sub_command) < 2:
                return True, f"Labbay, {user_display}! Sizni tinglayapman, marhamat buyuring."
            # Misa so'zini olib tashlab, qolgan buyruqni tahlil qilish
            clean_text = sub_command
            clean_no_punct = re.sub(r"[?!.,;:_`*~#]+", "", clean_text).strip()
            has_question = is_question_phrase(clean_text)

        if clean_no_punct in [
            "men kimman", "men kimmam", "men kim", "men haqimda ayt", "men haqimda",
            "ismim nima", "mening ismim nima", "otim nima", "mening otim nima", "ismimni ayt"
        ] or re.match(r"^(?:men\s+kimman|mening\s+ismim\s+nima|ismim\s+nima)\??$", clean_text):
            return True, f"Siz — **{user_display}**siz. Misa AI tizimida shaxsiy profilingiz faol holatda."

        if clean_no_punct in [
            "sen kimsan", "sen kim", "kimsan", "o'zing haqingda ayt", "ozing haqingda ayt",
            "misa kimsan", "misa nima", "sen nimasan", "o'zingni tanishtir", "ozingni tanishtir"
        ] or re.match(r"^(?:sen\s+kimsan|misa\s+kimsan|kimsan)\??$", clean_text):
            return True, (
                "Men **Misa AI** — sizning shaxsiy sun'iy intellekt va avtonom kompyuter yordamchingizman.\n\n"
                "Men quyidagi asosiy vazifalarni bajara olaman:\n"
                "• 💻 Dasturlarni ochish va boshqarish (Telegram, Chrome, VS Code, Discord va b.)\n"
                "• 📊 Tizim parametrlarini tahlil qilish (CPU, GPU, RAM, Disk, batareya, vaqt va sana)\n"
                "• 🎵 Ovoz va musiqa boshqaruvi\n"
                "• ⏰ Vazifalar va eslatmalarni rejalashtirish\n"
                "• 📱 Telegram orqali masofaviy boshqaruv"
            )

        # -------------------------------------------------------------
        # 1. Vaqt va sana so'rovlari
        # -------------------------------------------------------------
        if clean_no_punct in [
            "vaqt", "soat", "vaqt necha", "soat necha", "vaqt nechi", "soat nechi",
            "soat nechchi", "vaqt nechchi", "vaqtni ayt", "soatni ayt", "hozir soat necha",
            "hozir soat nechi", "hozirgi vaqt", "hozir vaqt nechi", "hozir soat nechchi"
        ] or re.search(r"^(?:hozir\s+)?(?:soat|vaqt)\s*(?:necha|nechi|nechchi|qancha)?\??$", clean_no_punct):
            now = datetime.datetime.now()
            return True, f"Hozirgi vaqt: {now.strftime('%H:%M')}"

        if clean_no_punct in [
            "sana", "bugungi sana", "bugun qaysi kun", "qaysi sana", "bugun sana necha",
            "bugun sana nechi", "bugungi kun"
        ] or re.search(r"^(?:bugun(?:gi)?\s+)?(?:sana|kun)\s*(?:necha|nechi|qaysi)?\??$", clean_no_punct):
            now = datetime.datetime.now()
            oylar = [
                "yanvar", "fevral", "mart", "aprel", "may", "iyun",
                "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"
            ]
            return True, f"Bugun {now.day}-{oylar[now.month-1]}, {now.year}-yil."

        # -------------------------------------------------------------
        # 2. Protsessor, Videokarta va Tizim Parametrlari (Hardware Specs)
        # -------------------------------------------------------------
        # Protsessor (CPU) so'ralganda ("protsessor", "prosseser", "cpu", "processor")
        is_cpu_query = any(w in clean_text for w in [
            "protsessor", "protsessr", "prossesor", "prosseser", "processor", "cpu",
            "protsessorchi", "protsessrchi", "prossesorchi", "prosseserchi", "cpuchi"
        ]) and (
            any(p in clean_text for p in [
                "model", "qanaqa", "qanday", "nechi", "qancha", "haqida", "haqidagi",
                "ma'lumot", "malumot", "parametr", "kerak", "ayt", "ko'rsat", "korsat",
                "nomi", "qaysi", "bormi", "chi", "?"
            ]) or clean_text in [
                "protsessor", "protsessor?", "prosseser", "prosseser?", "cpu", "cpu?",
                "protsessorim", "protsessorim?", "protsessorchi", "protsessorchi?",
                "prosseserchi", "prosseserchi?", "cpuchi", "cpuchi?"
            ] or clean_text.endswith("chi") or clean_text.endswith("chi?")
        )
        if is_cpu_query:
            cpu_name = platform.processor() or "Standart protsessor"
            if WINREG_AVAILABLE and winreg is not None:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
                        reg_name, _ = winreg.QueryValueEx(k, 'ProcessorNameString')
                        if reg_name:
                            cpu_name = str(reg_name).strip()
                except Exception:
                    pass
            cores_p = psutil.cpu_count(logical=False) or 1
            cores_l = psutil.cpu_count(logical=True) or 1
            cpu_usage = psutil.cpu_percent(interval=0.1)
            return True, (
                f"🧠 **Protsessoringiz modeli va ma'lumotlari:**\n\n"
                f"• **Model:** {cpu_name}\n"
                f"• **Yadrolar:** {cores_p} ta fizik / {cores_l} ta mantiqiy yadro\n"
                f"• **Hozirgi yuklama:** {cpu_usage}% band"
            )

        # Videokarta (GPU) so'ralganda ("videokarta", "gpu", "grafika", "videokartam", "videokartachi?")
        is_gpu_query = any(w in clean_text for w in [
            "videokarta", "videokartam", "videokartachi", "videokartamchi",
            "gpu", "gpuchi", "grafika", "grafikachi"
        ]) and (
            any(p in clean_text for p in [
                "model", "qanaqa", "qanday", "nechi", "qancha", "haqida", "ma'lumot",
                "kerak", "ayt", "nomi", "bormi", "ko'rsat", "korsat", "parametr", "chi", "?"
            ]) or clean_text in [
                "videokarta", "videokarta?", "videokartam", "videokartam?",
                "videokartachi", "videokartachi?", "gpu", "gpu?", "gpuchi", "gpuchi?",
                "grafika", "grafika?", "grafikachi", "grafikachi?"
            ] or clean_text.endswith("chi") or clean_text.endswith("chi?")
        )
        if is_gpu_query:
            gpu_items = get_system_gpus()
            if gpu_items:
                gpu_lines = []
                for g in gpu_items:
                    details = [f"• **Model:** {g['name']}"]
                    if g.get("vram_gb"):
                        details.append(f"• **Video xotira (VRAM):** {g['vram_gb']} GB")
                    if g.get("driver"):
                        details.append(f"• **Drayver versiyasi:** {g['driver']}")
                    details.append("• **Holati:** Faol (DirectX 12)")
                    gpu_lines.append("\n".join(details))
                gpu_body = "\n\n".join(gpu_lines)
                return True, f"🎮 **Videokartangiz (GPU) ma'lumotlari:**\n\n{gpu_body}"
            else:
                return True, "🎮 **Videokartangiz (GPU):**\n• Standart video adapter"

        # RAM (Tezkor xotira) so'ralganda ("ram", "ramchi?", "operativka", "operativkachi?")
        is_ram_query = bool(
            re.search(
                r"\b(ram|ramchi|operativka|operativkachi|tezkor xotira|xotirachi)\b",
                clean_text,
            )
        ) and (
            any(p in clean_text for p in [
                "qancha", "qanaqa", "nechi", "haqida", "ma'lumot", "kerak", "ayt",
                "band", "bo'sh", "hajm", "chi", "?"
            ]) or clean_text in [
                "ram", "ram?", "ramchi", "ramchi?", "operativka", "operativka?",
                "operativkachi", "operativkachi?", "tezkor xotira", "tezkor xotira?",
                "xotirachi", "xotirachi?"
            ] or clean_text.endswith("chi") or clean_text.endswith("chi?")
        )
        if is_ram_query:
            mem = psutil.virtual_memory()
            total_gb = round(mem.total / (1024**3), 1)
            used_gb = round(mem.used / (1024**3), 1)
            free_gb = round(mem.available / (1024**3), 1)
            approx_total = round(total_gb)
            return True, (
                f"💾 **Tezkor xotira (RAM) ma'lumotlari:**\n\n"
                f"• **Jami hajm:** {total_gb} GB (~{approx_total} GB)\n"
                f"• **Ishlatilmoqda:** {used_gb} GB ({mem.percent}%)\n"
                f"• **Bo'sh joy:** {free_gb} GB"
            )

        # Disk (Qattiq disk / SSD) so'ralganda ("disk", "diskchi?", "joy qancha?")
        is_disk_query = any(w in clean_text for w in [
            "disk", "diskchi", "qattiq disk", "ssd", "hdd", "xotira joyi", "qancha joy bor", "joy qancha"
        ]) and (
            any(p in clean_text for p in [
                "qancha", "qanaqa", "nechi", "bo'sh", "haqida", "ma'lumot", "kerak", "ayt", "bor", "joy", "chi", "?"
            ]) or clean_text in [
                "disk", "disk?", "diskchi", "diskchi?", "joy qancha?", "qancha joy bor?", "disklar"
            ] or clean_text.endswith("chi") or clean_text.endswith("chi?")
        )
        if is_disk_query:
            disks = []
            for part in psutil.disk_partitions(all=False):
                if "cdrom" in part.opts or part.fstype == "":
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    free_gb = round(usage.free / (1024**3), 1)
                    total_gb = round(usage.total / (1024**3), 1)
                    drive = part.mountpoint.rstrip("\\")
                    disks.append(f"• **{drive}\\**: {free_gb} GB bo'sh / {total_gb} GB ({usage.percent}% band)")
                except Exception:
                    pass
            disks_str = "\n".join(disks) if disks else "Disklar aniqlanmadi"
            return True, f"💽 **Disk xotirasi (Storage) holati:**\n\n{disks_str}"

        is_pc_query = (
            any(w in clean_text for w in ["kompyuter", "pc", "tizim", "sistema"]) and
            any(p in clean_text for p in ["parametr", "xususiyat", "ma'lumot", "malumot", "xarakteristika", "info", "spesifikatsiya", "haqida"])
        ) or any(clean_text == kw for kw in [
            "kompyuterim parametrlarini aytib ber", "pc parametrlarini aytib ber",
            "kompyuterim parametrlari", "pc parametrlari", "tizim parametrlari",
            "tizim ma'lumotlari", "diskda qancha joy bor"
        ])

        if is_pc_query:
            # Agar "barcha", "to'liq", "batafsil", "hamma" deb so'ralgan bo'lsa -> To'liq texnik ma'lumot
            is_detailed = any(w in clean_text for w in ["barcha", "to'liq", "toliq", "hamma", "batafsil", "detailed", "all", "full"])
            if is_detailed:
                return True, get_system_specs_detailed()
            else:
                return True, get_system_specs_summary()

        # -------------------------------------------------------------
        # 3. Ilova Mavjudligini Tekshirish (Mantiqiy Savol: "menda X bormi?")
        # -------------------------------------------------------------
        # Agar so'rov qiyosiy, maslahat, tahliliy yoki avvalgi mavzuga bog'liq bo'lsa -> AI agentga o'tkazish!
        is_comparative = any(w in clean_text for w in [
            "shunga o'xshash", "shunga oxshash", "o'xshash", "oxshash", "boshqa",
            "muqobil", "alternativ", "variant", "tavsiya", "maslahat", "qaysi",
            "farqi", "nima uchun", "qanday qilib", "solishtir", "taqqosla"
        ])

        if not is_comparative:
            # Jami nechta ilova bor / qanday dasturlar bor so'rovi
            total_apps_match = re.search(
                r"(?:menda|kompyuterimda|kompyuterda|bu\s+qurilmada|pcda|tizimda)?\s*(?:jami\s+)?(?:nechta|qanday|qanaqa|qaysi)\s*(?:ilova|dastur|programmala?r?)\s*(?:bor|mavjud|o['']rnatilgan)\??$",
                clean_text
            )
            if total_apps_match:
                try:
                    from core.app_detector import get_app_detector
                    detector = get_app_detector()
                    inv = detector.get_realtime_inventory_summary()
                    items = [line for line in inv.split("\n") if line.strip().startswith("•")]
                    count = len(items)
                    return True, f"📊 Kompyuteringizda aniqlangan asosiy dasturlar (jami {count} ta):\n\n{inv}"
                except Exception as e:
                    logger.warning(f"Ilovalar sonini aniqlashda xatolik: {e}")

            app_inquiry_match = re.search(
                r"(?:kel\s+undan\s+oldin|avval)?\s*(?:menda|kompyuterimda|kompyuterda|bu\s+qurilmada|pcda)?\s*(telegram|tg|ayugram|kotatogram|chrome|google chrome|vs code|vscode|code|discord|brave|python|spotify|steam|cursor|pycharm|opencode|webstorm|sublime|notepad\+\+|notepad)\s*(?:ilovasi|dasturi)?\s*(?:bormi|brmi|bormikan|o['']rnatilganmi|ornatilganmi|mavjudmi)\s*(?:tekshir|ayt|ko['']rsat)?\??$",
                clean_text
            )
            if app_inquiry_match:
                target_app = app_inquiry_match.group(1).strip()
                if target_app == "tg":
                    target_app = "telegram"
                elif target_app in ["vs code", "vscode"]:
                    target_app = "code"
                elif target_app == "google chrome":
                    target_app = "chrome"

                try:
                    from core.app_detector import get_app_detector
                    info = get_app_detector().detect_app(target_app)
                    return True, info.format_uzbek_response(target_app)
                except Exception:
                    installed, running, path, title = find_installed_app(target_app)
                    if running:
                        return True, f"✅ Ha, kompyuteringizda {title} o'rnatilgan va ayni paytda ishlab turibdi."
                    elif installed:
                        loc_info = f" ({path})" if path else ""
                        return True, f"✅ Ha, kompyuteringizda {title} ilovasi o'rnatilgan{loc_info}. Uni ochishni xohlaysizmi?"
                    else:
                        return True, f"❌ Yo'q, kompyuteringizda {title} ilovasi topilmadi (o'rnatilmagan)."

        # -------------------------------------------------------------
        # 4. Ilovalarni Ochish Buyruqlari (Faqatgina BUYRUQ bo'lganda, savol EMAS!)
        # -------------------------------------------------------------
        if not has_question:
            # Telegram / AyuGram
            if re.match(r"^(telegramni\s+och|telegram\s+och|ayugramni\s+och|ayugram\s+och|telegram\s+dasturini\s+och|telegramni\s+ishga\s+tushir|ayugram|telegram)$", clean_text):
                installed, _, path, title = find_installed_app("telegram")
                if installed:
                    try:
                        if path and os.path.exists(path) and hasattr(os, "startfile"):
                            os.startfile(path)
                        elif hasattr(os, "startfile"):
                            os.startfile("tg:")
                        else:
                            import subprocess
                            subprocess.Popen(["cmd", "/c", "start", "tg:"], shell=False)
                        return True, f"✅ {title} ochilmoqda."
                    except Exception as e:
                        return True, f"Telegramni ochishda xatolik: {e}"
                else:
                    return True, "❌ Kompyuteringizda Telegram topilmadi (o'rnatilmagan). Uni web.telegram.org manzilidan yoki rasmiy saytidan yuklab olishingiz mumkin."

            # Chrome
            if re.match(r"^(chromeni\s+och|chrome\s+och|brauzerni\s+och|google\s+chromeni\s+och|chrome)$", clean_text):
                installed, _, path, title = find_installed_app("chrome")
                if installed and path and os.path.exists(path) and hasattr(os, "startfile"):
                    try:
                        os.startfile(path)
                        return True, "✅ Google Chrome ochilmoqda."
                    except Exception:
                        pass
                webbrowser.open("https://www.google.com")
                return True, "✅ Brauzer ochilmoqda."

            # VS Code
            if re.match(r"^(code|vscode|vs\s*code|kodni\s+och|visual\s+studioni\s+och|vs\s*codeni\s+och)$", clean_text):
                installed, _, path, title = find_installed_app("code")
                if installed and path and os.path.exists(path) and hasattr(os, "startfile"):
                    try:
                        os.startfile(path)
                        return True, "✅ VS Code ochilmoqda."
                    except Exception:
                        pass
                try:
                    import subprocess
                    subprocess.Popen(["code"], shell=False)
                    return True, "✅ VS Code ochilmoqda."
                except Exception:
                    return True, "❌ Kompyuteringizda VS Code topilmadi."

            # Discord
            if re.match(r"^(discord|discordni\s+och|diskordni\s+och)$", clean_text):
                installed, _, path, title = find_installed_app("discord")
                if installed and path and os.path.exists(path) and hasattr(os, "startfile"):
                    try:
                        os.startfile(path)
                        return True, "✅ Discord ochilmoqda."
                    except Exception:
                        pass
                try:
                    if hasattr(os, "startfile"):
                        os.startfile("discord:")
                    else:
                        import subprocess
                        subprocess.Popen(["cmd", "/c", "start", "discord:"], shell=False)
                    return True, "✅ Discord ochilmoqda."
                except Exception:
                    return True, "❌ Kompyuteringizda Discord topilmadi."

        # -------------------------------------------------------------
        # 5. YouTube va Musiqa
        # -------------------------------------------------------------
        if any(w in clean_text for w in ["qo'shiq", "qoshiq", "musiqa", "trek", "ashula", "ijro", "eshit"]):
            return False, ""

        if not has_question and re.match(r"^(youtube|yutub|yutubni\s+och|youtubeni\s+och)$", clean_text):
            webbrowser.open("https://www.youtube.com")
            return True, "✅ YouTube ochilmoqda."

        yt_search = re.match(r"(?:youtube|yutub)(?:da|dan)?\s+(?:qidir|och|top)\s+(.+)", clean_text)
        if yt_search:
            query = yt_search.group(1).strip()
            webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
            return True, f"🔍 YouTube'dan '{query}' qidirilmoqda."

        # -------------------------------------------------------------
        # 6. Google qidiruv
        # -------------------------------------------------------------
        google_search = re.match(r"(?:google|gugl)(?:da|dan)?\s+(?:qidir|top)\s+(.+)", clean_text)
        if google_search:
            query = google_search.group(1).strip()
            webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
            return True, f"🔍 Google'dan '{query}' qidirilmoqda."

        # -------------------------------------------------------------
        # 7. Ovoz darajasi (Volume)
        # -------------------------------------------------------------
        volume_match = re.search(r"ovoz(?:ni)?\s*(\d+)(?:\s*(?:foiz|qil|ga\s*qo['']y))?", clean_text)
        if volume_match:
            try:
                vol_level = int(volume_match.group(1))
                vol_level = max(0, min(100, vol_level))
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL

                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(vol_level / 100.0, None)
                return True, f"🔊 Ovoz balandligi {vol_level}% ga sozlandi."
            except Exception as e:
                logger.error(f"Ovozni sozlashda xatolik: {e}")

        # -------------------------------------------------------------
        # 8. Maxsus ro'yxatdan o'tgan handlerlar
        # -------------------------------------------------------------
        for intent, handler in self._custom_handlers.items():
            try:
                handled, result = handler(clean_text)
                if handled:
                    return True, result
            except Exception as e:
                logger.error(f"Custom handler '{intent}' xatolik: {e}")

        # Mahalliy buyruq emas — savol yoki suhbat sifatida AI agentga yo'naltiriladi!
        return False, ""

