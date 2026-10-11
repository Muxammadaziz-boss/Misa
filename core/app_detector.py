# ========== app_detector.py ==========
# Misa AI 7.x — Deep Windows Application & Process Inventory Engine
# [Phase 6] Haqiqiy vaqt rejimida Windows ilovalari, jarayonlar, registri va portativ dasturlarni aniqlash

import os
import sys
import time
import shutil
import logging
import platform
import psutil
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("MisaAppDetector")

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    winreg = None
    WINREG_AVAILABLE = False


class AppInfo:
    """Ilova haqida to'liq ma'lumot obyekti"""

    def __init__(
        self,
        found: bool = False,
        running: bool = False,
        name: str = "",
        canonical_name: str = "",
        family: str = "",
        exe_path: str = "",
        pid: Optional[int] = None,
        notes: str = ""
    ):
        self.found = found
        self.running = running
        self.name = name
        self.canonical_name = canonical_name
        self.family = family
        self.exe_path = exe_path
        self.pid = pid
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "running": self.running,
            "name": self.name,
            "canonical_name": self.canonical_name,
            "family": self.family,
            "exe_path": self.exe_path,
            "pid": self.pid,
            "notes": self.notes
        }

    def format_uzbek_response(self, requested_name: str = "") -> str:
        """Foydalanuvchiga tabiiy o'zbek tilida aniq va rostgo'y javob shakllantirish"""
        req_clean = (requested_name or self.canonical_name).lower().strip()

        # Agar telegram so'ralib, ayugram topilgan bo'lsa
        if "telegram" in req_clean and "ayugram" in self.name.lower():
            if self.running:
                return f"✅ Kompyuteringizda Telegram mijozi sifatida **AyuGram Desktop** o'rnatilgan va ayni paytda ishlab turibdi."
            else:
                return f"✅ Kompyuteringizda Telegram mijozi sifatida **AyuGram Desktop** o'rnatilgan ({self.exe_path}). Uni ochishni xohlaysizmi?"

        if self.running:
            return f"✅ Ha, kompyuteringizda **{self.name}** o'rnatilgan va ayni paytda ishlab turibdi."
        elif self.found:
            loc = f" ({self.exe_path})" if self.exe_path else ""
            return f"✅ Ha, kompyuteringizda **{self.name}** ilovasi o'rnatilgan{loc}. Uni ochishni xohlaysizmi?"
        else:
            display_name = requested_name.capitalize() if requested_name else "Ushbu ilova"
            return f"❌ Yo'q, kompyuteringizda **{display_name}** ilovasi topilmadi (o'rnatilmagan)."


class WindowsAppDetector:
    """
    Windows tizimida ilovalarni chuqur skanerlash va monitoring qilish tizimi:
    1. Ishlab turgan jarayonlar (psutil)
    2. Windows Registri (HKCU & HKLM Uninstall + App Paths)
    3. Start Menu va Desktop yorliqlari (.lnk)
    4. Portativ dasturlar va disklar bo'yicha dinamik qidiruv
    5. TTL kesh bilan yuqori tezlikdagi ishlash
    """

    # Ilovalar oilalari va ularning ekvivalentlari
    APP_FAMILIES = {
        "telegram": {
            "title": "Telegram Desktop",
            "aliases": ["telegram", "tg", "ayugram", "kotatogram", "64gram", "ayu"],
            "exe_names": ["telegram.exe", "ayugram.exe", "kotatogram.exe", "64gram.exe"],
            "protocol": "tg:",
            "web_url": "https://web.telegram.org"
        },
        "ayugram": {
            "title": "AyuGram Desktop",
            "aliases": ["ayugram", "ayu"],
            "exe_names": ["ayugram.exe"],
            "protocol": "tg:",
            "web_url": "https://web.telegram.org"
        },
        "chrome": {
            "title": "Google Chrome",
            "aliases": ["chrome", "google chrome", "googlechrome"],
            "exe_names": ["chrome.exe"],
            "protocol": "",
            "web_url": "https://www.google.com"
        },
        "code": {
            "title": "Visual Studio Code",
            "aliases": ["code", "vscode", "vs code", "visual studio code"],
            "exe_names": ["code.exe", "code.cmd"],
            "protocol": "vscode:",
            "web_url": "https://code.visualstudio.com"
        },
        "discord": {
            "title": "Discord",
            "aliases": ["discord"],
            "exe_names": ["discord.exe", "update.exe"],
            "protocol": "discord:",
            "web_url": "https://discord.com"
        },
        "brave": {
            "title": "Brave Browser",
            "aliases": ["brave", "brave browser"],
            "exe_names": ["brave.exe"],
            "protocol": "",
            "web_url": "https://brave.com"
        },
        "edge": {
            "title": "Microsoft Edge",
            "aliases": ["edge", "msedge", "microsoft edge"],
            "exe_names": ["msedge.exe"],
            "protocol": "",
            "web_url": "https://www.microsoft.com/edge"
        },
        "spotify": {
            "title": "Spotify",
            "aliases": ["spotify"],
            "exe_names": ["spotify.exe"],
            "protocol": "spotify:",
            "web_url": "https://open.spotify.com"
        },
        "steam": {
            "title": "Steam",
            "aliases": ["steam"],
            "exe_names": ["steam.exe"],
            "protocol": "steam:",
            "web_url": "https://store.steampowered.com"
        },
        "git": {
            "title": "Git SCM",
            "aliases": ["git", "git bash"],
            "exe_names": ["git.exe", "git-bash.exe"],
            "protocol": "",
            "web_url": "https://git-scm.com"
        },
        "cursor": {
            "title": "Cursor AI Code Editor",
            "aliases": ["cursor", "cursor ai"],
            "exe_names": ["cursor.exe"],
            "protocol": "cursor:",
            "web_url": "https://cursor.com"
        },
        "pycharm": {
            "title": "PyCharm",
            "aliases": ["pycharm", "pycharm ide", "jetbrains pycharm"],
            "exe_names": ["pycharm64.exe", "pycharm.exe", "pycharm.bat"],
            "protocol": "",
            "web_url": "https://www.jetbrains.com/pycharm"
        },
        "opencode": {
            "title": "OpenCode",
            "aliases": ["opencode"],
            "exe_names": ["opencode.exe"],
            "protocol": "",
            "web_url": ""
        }
    }

    def __init__(self, cache_ttl: float = 30.0):
        self.cache_ttl = cache_ttl
        self._last_process_scan_time = 0.0
        self._cached_running_processes: List[Dict[str, Any]] = []
        self._cached_installed_apps: Dict[str, AppInfo] = {}
        self._last_full_scan_time = 0.0

    def _get_running_processes(self) -> List[Dict[str, Any]]:
        """Ishlab turgan jarayonlarni tezkor olish (TTL kesh bilan)"""
        now = time.time()
        if now - self._last_process_scan_time < 5.0 and self._cached_running_processes:
            return self._cached_running_processes

        procs = []
        for p in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                name = p.info.get('name') or ''
                exe = p.info.get('exe') or ''
                pid = p.info.get('pid')
                if name:
                    procs.append({
                        "pid": pid,
                        "name": name.lower(),
                        "exe": exe,
                        "raw_name": name
                    })
            except Exception:
                pass

        self._cached_running_processes = procs
        self._last_process_scan_time = now
        return procs

    def detect_app(self, query: str) -> AppInfo:
        """
        Istalgan dasturni har tomonlama qidirish.
        query: masalan "telegram", "ayugram", "chrome", "vscode"
        """
        q = query.lower().strip()
        if not q:
            return AppInfo()

        running_procs = self._get_running_processes()

        # 1. Family va Aliases tekshiruvi
        matched_family_key = None
        for fam_k, fam_cfg in self.APP_FAMILIES.items():
            if fam_k in q or q in fam_k or any(al in q or q in al for al in fam_cfg["aliases"]):
                matched_family_key = fam_k
                break

        family_cfg = self.APP_FAMILIES.get(matched_family_key) if matched_family_key else None
        target_exe_names = [e.lower() for e in family_cfg["exe_names"]] if family_cfg else [f"{q}.exe", q]

        # 2. Jarayonlar orasida tekshirish (Ayni paytda ishlab turgan)
        for p in running_procs:
            pname = p["name"]
            pexe = p["exe"] or ""
            pexe_lower = pexe.lower()
            pexe_basename = os.path.basename(pexe_lower)

            # Maxsus: AyuGram tekshiruvi
            if "ayugram" in pname or "ayugram" in pexe_lower:
                if "ayugram" in q or "telegram" in q or matched_family_key == "telegram":
                    return AppInfo(
                        found=True,
                        running=True,
                        name="AyuGram Desktop (Telegram mijozi)",
                        canonical_name="ayugram",
                        family="telegram",
                        exe_path=pexe or pname,
                        pid=p["pid"]
                    )

            # Maxsus: Telegram Desktop
            if "telegram" in pname or "telegram.exe" in pexe_basename:
                if "telegram" in q or matched_family_key == "telegram":
                    return AppInfo(
                        found=True,
                        running=True,
                        name="Telegram Desktop",
                        canonical_name="telegram",
                        family="telegram",
                        exe_path=pexe or pname,
                        pid=p["pid"]
                    )

            # Boshqa maqsadli nomlar
            if any(target_exe in pname or target_exe == pexe_basename for target_exe in target_exe_names):
                title = family_cfg["title"] if family_cfg else os.path.splitext(p["raw_name"])[0]
                return AppInfo(
                    found=True,
                    running=True,
                    name=title,
                    canonical_name=matched_family_key or q,
                    family=matched_family_key or q,
                    exe_path=pexe or pname,
                    pid=p["pid"]
                )

        # 3. Disklar va standart kataloglar bo'yicha tekshirish
        standard_paths = self._get_standard_paths_for_app(matched_family_key, q)
        for sp in standard_paths:
            if os.path.exists(sp):
                title = self._get_title_for_path(sp, family_cfg, q)
                fam = "telegram" if ("ayugram" in sp.lower() or "telegram" in sp.lower()) else (matched_family_key or q)
                return AppInfo(
                    found=True,
                    running=False,
                    name=title,
                    canonical_name=matched_family_key or q,
                    family=fam,
                    exe_path=sp
                )

        # 4. PATH orqali tekshirish
        which_exe = shutil.which(q) or (shutil.which(target_exe_names[0]) if target_exe_names else None)
        if which_exe:
            title = family_cfg["title"] if family_cfg else q.capitalize()
            return AppInfo(
                found=True,
                running=False,
                name=title,
                canonical_name=matched_family_key or q,
                family=matched_family_key or q,
                exe_path=which_exe
            )

        # 5. Windows Start Menu va Desktop yorliqlari (.lnk)
        shortcut_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            r"C:\Users\Public\Desktop",
        ]
        for sdir in shortcut_dirs:
            if not os.path.exists(sdir):
                continue
            try:
                for root, _, files in os.walk(sdir):
                    for f in files:
                        fl = f.lower()
                        # Agar telegram so'ralsa va ayugram yorlig'i bo'lsa
                        if ("telegram" in q and "ayugram" in fl) or ("ayugram" in q and "ayugram" in fl):
                            return AppInfo(
                                found=True,
                                running=False,
                                name="AyuGram Desktop (Telegram)",
                                canonical_name="ayugram",
                                family="telegram",
                                exe_path=os.path.join(root, f)
                            )
                        if any(k in fl for k in [q] + (family_cfg["aliases"] if family_cfg else [])):
                            full_path = os.path.join(root, f)
                            title = os.path.splitext(f)[0]
                            return AppInfo(
                                found=True,
                                running=False,
                                name=title,
                                canonical_name=matched_family_key or q,
                                family=matched_family_key or q,
                                exe_path=full_path
                            )
            except Exception:
                pass

        # 6. Windows Registri orqali tekshirish
        if WINREG_AVAILABLE:
            reg_keys = [
                (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Uninstall'),
                (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\Uninstall'),
                (winreg.HKEY_LOCAL_MACHINE, r'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
                (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\App Paths'),
                (winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\App Paths'),
            ]
            for root, subkey in reg_keys:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        count = winreg.QueryInfoKey(key)[0]
                        for i in range(count):
                            try:
                                sub = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, sub) as app_key_reg:
                                    disp = ""
                                    try:
                                        disp, _ = winreg.QueryValueEx(app_key_reg, 'DisplayName')
                                    except Exception:
                                        disp = sub

                                    displ = str(disp).lower()
                                    if ("telegram" in q and "ayugram" in displ) or ("ayugram" in q and "ayugram" in displ):
                                        loc = self._safe_get_reg_val(app_key_reg, 'InstallLocation')
                                        return AppInfo(
                                            found=True,
                                            running=False,
                                            name="AyuGram Desktop",
                                            canonical_name="ayugram",
                                            family="telegram",
                                            exe_path=loc or str(disp)
                                        )

                                    if any(k in displ for k in [q] + (family_cfg["aliases"] if family_cfg else [])):
                                        loc = self._safe_get_reg_val(app_key_reg, 'InstallLocation')
                                        return AppInfo(
                                            found=True,
                                            running=False,
                                            name=str(disp),
                                            canonical_name=matched_family_key or q,
                                            family=matched_family_key or q,
                                            exe_path=loc or str(disp)
                                        )
                            except Exception:
                                pass
                except Exception:
                    pass

        # 7. Topilmadi
        default_title = family_cfg["title"] if family_cfg else q.capitalize()
        return AppInfo(
            found=False,
            running=False,
            name=default_title,
            canonical_name=matched_family_key or q,
            family=matched_family_key or q
        )

    def _safe_get_reg_val(self, key, val_name: str) -> str:
        try:
            val, _ = winreg.QueryValueEx(key, val_name)
            return str(val)
        except Exception:
            return ""

    def _get_title_for_path(self, path: str, family_cfg: Optional[Dict], fallback: str) -> str:
        p_lower = path.lower()
        if "ayugram" in p_lower:
            return "AyuGram Desktop (Telegram mijozi)"
        if "telegram" in p_lower:
            return "Telegram Desktop"
        if family_cfg and "title" in family_cfg:
            return family_cfg["title"]
        return fallback.capitalize()

    def _get_standard_paths_for_app(self, family_key: Optional[str], query: str) -> List[str]:
        """Tizimdagi barcha disklar va ma'lum kataloglarni dinamik qidirish"""
        paths = []

        # Telegram / AyuGram maxsus tekshiruvlari
        if family_key == "telegram" or "telegram" in query or "ayugram" in query:
            # D: disk va C: diskdagi barcha Telegram/AyuGram papkalari
            drives = ["D:\\", "C:\\"]
            for d in drives:
                if os.path.exists(d):
                    # To'g'ridan-to'g'ri ko'p uchraydigan nomlar
                    candidates = [
                        os.path.join(d, "Telegram akklar", "AyuGram", "AyuGram.exe"),
                        os.path.join(d, "Telegram", "Telegram.exe"),
                        os.path.join(d, "AyuGram", "AyuGram.exe"),
                        os.path.join(d, "Telegram akklar", "Telegram.exe"),
                        os.path.join(d, "Apps", "Telegram", "Telegram.exe"),
                        os.path.join(d, "Apps", "AyuGram", "AyuGram.exe"),
                    ]
                    paths.extend(candidates)

            # User AppData yo'llari
            paths.extend([
                os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe"),
                os.path.expandvars(r"%APPDATA%\AyuGram Desktop\AyuGram.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\AyuGram Desktop\AyuGram.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Telegram Desktop\Telegram.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Telegram Desktop\Telegram.exe"),
            ])

        # Chrome
        if family_key == "chrome" or "chrome" in query:
            paths.extend([
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ])

        # VS Code / Cursor
        if family_key == "code" or "code" in query or "vscode" in query:
            paths.extend([
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft VS Code\Code.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\cursor\Cursor.exe"),
            ])

        # Discord
        if family_key == "discord" or "discord" in query:
            paths.extend([
                os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"),
            ])

        # Brave
        if family_key == "brave" or "brave" in query:
            paths.extend([
                os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ])

        # Edge
        if family_key == "edge" or "edge" in query:
            paths.extend([
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
            ])

        # Spotify
        if family_key == "spotify" or "spotify" in query:
            paths.extend([
                os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            ])

        # Steam
        if family_key == "steam" or "steam" in query:
            paths.extend([
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Steam\steam.exe"),
                r"D:\Steam\steam.exe",
            ])

        # PyCharm
        if family_key == "pycharm" or "pycharm" in query:
            import glob
            for pat in [
                r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe",
                r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm.bat",
                r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm.BAT",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\PyCharm*\bin\pycharm64.exe"),
            ]:
                for match in glob.glob(pat):
                    if os.path.exists(match):
                        paths.append(match)

        return paths

    def get_realtime_inventory_summary(self) -> str:
        """AI dvigateli uchun tizimda o'rnatilgan va ishlayotgan barcha asosiy dasturlar xulosasi"""
        results = []
        checked_families = ["telegram", "ayugram", "chrome", "edge", "code", "pycharm", "opencode", "discord", "brave", "spotify", "steam", "cursor"]
        seen_names = set()

        for fam in checked_families:
            info = self.detect_app(fam)
            if not info.found or info.name in seen_names:
                continue
            seen_names.add(info.name)
            if info.running:
                results.append(f"• {info.name}: O'rnatilgan va ayni paytda ISHLAB TURIBDI")
            elif info.found:
                results.append(f"• {info.name}: O'rnatilgan")

        if not results:
            return "Asosiy dasturlar tekshirildi."
        return "\n".join(results)

    def get_gpu_names(self) -> List[str]:
        """Videokarta (GPU) nomlarini tezkor registridan olish"""
        gpus = []
        if not WINREG_AVAILABLE:
            return gpus
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}') as root:
                count = winreg.QueryInfoKey(root)[0]
                for i in range(count):
                    sub = winreg.EnumKey(root, i)
                    if sub.isdigit():
                        try:
                            with winreg.OpenKey(root, sub) as sk:
                                driver_desc, _ = winreg.QueryValueEx(sk, 'DriverDesc')
                                if driver_desc and driver_desc not in gpus:
                                    gpus.append(str(driver_desc))
                        except Exception:
                            pass
        except Exception:
            pass
        return gpus

    def get_realtime_system_specs(self) -> str:
        """Kompyuter apparat ma'lumotlarini dinamik ravishda to'liq shakllantirish (hardcoding yo'q!)"""
        try:
            os_name = f"{platform.system()} {platform.release()} ({platform.machine()})"
            node_name = platform.node()
            cpu_name = platform.processor() or "Standart protsessor"
            if WINREG_AVAILABLE:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
                        reg_name, _ = winreg.QueryValueEx(k, 'ProcessorNameString')
                        if reg_name:
                            cpu_name = str(reg_name).strip()
                except Exception:
                    pass

            cores_p = psutil.cpu_count(logical=False) or 1
            cores_l = psutil.cpu_count(logical=True) or 1
            cpu_usage = psutil.cpu_percent(interval=0.05)

            gpus = self.get_gpu_names()
            gpu_str = ", ".join(gpus) if gpus else "Standart video adapter"

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

            return (
                f"- Operatsion tizim: {os_name} (Host: {node_name})\n"
                f"- Protsessor (CPU): {cpu_name} ({cores_p} fiz / {cores_l} mantiqiy yadro, {cpu_usage}% band)\n"
                f"- Videokarta (GPU): {gpu_str}\n"
                f"- Tezkor xotira (RAM): {total_ram} GB (Band: {used_ram} GB, Bo'sh: {free_ram} GB)\n"
                f"- Disklar: {disks_str}"
            )
        except Exception as e:
            return f"Tizim ma'lumotlari: {e}"


# Singleton nusxa
_app_detector_instance: Optional[WindowsAppDetector] = None


def get_app_detector() -> WindowsAppDetector:
    global _app_detector_instance
    if _app_detector_instance is None:
        _app_detector_instance = WindowsAppDetector()
    return _app_detector_instance
