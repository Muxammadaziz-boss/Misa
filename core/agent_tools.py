# ========== agent_tools.py ==========
# AI Agent Tool/Plugin tizimi
# Har bir tool — agent chaqira oladigan funksiya

import os
import re
import json
import math
import logging
import datetime
import webbrowser
import subprocess
import base64
from urllib.parse import quote_plus
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set

from core.intelligence.types import RiskLevel
from core.tools.contract import (
    ToolContract2,
    ToolErrorCode,
    ToolHealth,
    ToolResult,
)
from core.tools.discovery import CapabilityRegistry
from core.tools.selector import SmartToolSelector, ToolSelectionResult
from core.tools.runner import get_tool_runner

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Loyiha ildizi


# ========================================================
# TOOL DATACLASS (Tool Contract 2.0)
# ========================================================


@dataclass
class Tool(ToolContract2):
    """Bitta tool/plugin tavsifi (Tool Contract 2.0 bilan kengaytirilgan)"""
    def __init__(self, *args, **kwargs):
        if "func" in kwargs and "function" not in kwargs:
            kwargs["function"] = kwargs.pop("func")
        super().__init__(*args, **kwargs)


# ========================================================
# TOOL REGISTRY
# ========================================================


class ToolRegistry:
    """Tool'larni ro'yxatdan o'tkazish va boshqarish (Tool System 2.0)"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self.capability_registry = CapabilityRegistry()

    def register(self, tool: Tool):
        """Yangi tool qo'shish"""
        self._tools[tool.name] = tool
        self.capability_registry.register_tool(
            tool_name=tool.name,
            capabilities=tool.capabilities,
            aliases=tool.aliases
        )
        logger.debug(f"Tool ro'yxatdan o'tdi: {tool.name} (capabilities={tool.capabilities})")

    def unregister(self, name: str) -> bool:
        """Toolni ro'yxatdan o'chirish"""
        if name in self._tools:
            del self._tools[name]
            self.capability_registry.unregister_tool(name)
            logger.debug(f"Tool ro'yxatdan o'chirildi: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """Tool ni nomi yoki taxallusi bo'yicha olish"""
        if not name:
            return None
        clean_name = str(name).strip()
        if clean_name in self._tools:
            return self._tools[clean_name]
        # Check alias
        resolved = self.capability_registry.find_by_alias(clean_name)
        if resolved and resolved in self._tools:
            return self._tools[resolved]
        return None

    def find_by_capability(self, capability: str) -> List[Tool]:
        """Berilgan qobiliyatga ega barcha faol asboblar"""
        names = self.capability_registry.find_by_capability(capability)
        return [self._tools[n] for n in names if n in self._tools]

    def select_tool(
        self,
        required_capability: str,
        context: Optional[Any] = None,
        candidate_params: Optional[Dict[str, Any]] = None,
        prefer_low_risk: bool = True
    ) -> ToolSelectionResult:
        """SmartToolSelector yordamida qobiliyat uchun eng mos asbobni tanlash"""
        candidates = self.find_by_capability(required_capability)
        if not candidates:
            single = self.get(required_capability)
            if single:
                candidates = [single]

        return SmartToolSelector.select_best_tool(
            required_capability=required_capability,
            candidate_tools=candidates,
            context=context,
            candidate_params=candidate_params,
            prefer_low_risk=prefer_low_risk
        )

    def discover_capabilities_for_text(self, text: str) -> List[Tuple[str, float]]:
        """Matndan talab qilinayotgan qobiliyatlarni aniqlash"""
        return self.capability_registry.discover_capabilities_for_text(text)

    def call(self, name: str, **kwargs) -> Any:
        """Tool ni nomi, taxallusi yoki qobiliyati bo'yicha chaqirish (SafeToolRunner orqali)"""
        tool = self.get(name)
        if not tool:
            candidates = self.find_by_capability(name)
            if candidates:
                sel = self.select_tool(name, candidate_params=kwargs)
                if sel and sel.tool:
                    tool = sel.tool

        if not tool:
            return ToolResult(
                success=False,
                code=ToolErrorCode.TOOL_NOT_FOUND,
                error=f"Tool '{name}' topilmadi",
                tool=name
            )
        return tool.call(**kwargs)

    def list_tools(self) -> list:
        """Barcha tool'larni ro'yxati (dict formatda)"""
        return [t.to_dict() for t in self._tools.values()]

    def list_names(self) -> list:
        """Faqat nomlar"""
        return list(self._tools.keys())

    def tools_prompt(self) -> str:
        """AI prompt uchun tool'lar tavsifi"""
        lines = []
        for tool in self._tools.values():
            params_str = ", ".join(
                f"{k}: {v.get('type', 'string') if isinstance(v, dict) else 'string'}" for k, v in tool.parameters.items()
            )
            caps_str = f" [capabilities: {', '.join(tool.capabilities)}]" if tool.capabilities else ""
            lines.append(f"- {tool.name}({params_str}) — {tool.description}{caps_str}")
        return "\n".join(lines)

    @property
    def count(self):
        return len(self._tools)


# ========================================================
# O'RNATILGAN TOOL'LAR
# ========================================================


# --- 1. WEB SEARCH (Haqiqiy natijali!) ---
def _web_search(query: str, platform: str = "google") -> dict:
    """Internetda qidirish — haqiqiy natija qaytaradi (DuckDuckGo API)"""
    import requests

    # YouTube va Wikipedia — brauzerda ochish
    if platform in ("youtube", "wikipedia"):
        urls = {
            "youtube": f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            "wikipedia": f"https://uz.wikipedia.org/w/index.php?search={quote_plus(query)}",
        }
        webbrowser.open(urls[platform])
        return {"message": f"'{query}' {platform}'da ochildi", "url": urls[platform]}

    # Google/default — DuckDuckGo API orqali haqiqiy natija olish
    try:
        resp = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10,
            headers={"User-Agent": "MisaAI/3.1"},
        )
        data = resp.json()

        # 1. Instant Answer (eng yaxshi natija)
        if data.get("AbstractText"):
            return {
                "answer": data["AbstractText"][:500],
                "source": data.get("AbstractSource", ""),
                "url": data.get("AbstractURL", ""),
                "message": data["AbstractText"][:300],
            }

        # 2. Direct Answer (hisob-kitoblar, sanalar)
        if data.get("Answer"):
            return {"answer": str(data["Answer"]), "message": str(data["Answer"])}

        # 3. Related Topics
        results = []
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(topic["Text"])

        if results:
            combined = "\n".join(f"• {r}" for r in results[:3])
            return {
                "results": results,
                "message": f"'{query}' bo'yicha natijalar:\n{combined}",
            }

        # 4. Natija topilmadi — brauzerni OCHMA!
        # Agent o'z AI bilimidan javob bersin (Gemini kuchida!)
        return {
            "message": "Internetda aniq javob topilmadi. O'z bilimingdan javob ber.",
            "no_results": True,
        }

    except Exception as e:
        # API xato — Agent o'zi javob bersin
        return {
            "message": f"Qidiruv API ishlamadi. O'z bilimingdan javob ber.",
            "error": str(e),
            "no_results": True,
        }


TOOL_WEB_SEARCH = Tool(
    name="web_search",
    description="Internetda qidirish — haqiqiy natija qaytaradi. Savolga javob topish, ma'lumot olish uchun ishlatiladi",
    parameters={
        "query": {"type": "string", "description": "Qidiruv so'rovi", "required": True},
        "platform": {
            "type": "string",
            "description": "Platforma: google (default, natija qaytaradi), youtube, wikipedia",
            "required": False,
        },
    },
    function=_web_search,
    category="internet",
    capabilities=['web_search', 'internet_search', 'search', 'google', 'duckduckgo'],
    aliases=['search', 'google', 'qidiruv', 'internet'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=True,
    destructive=False,
)


# --- 2. CALCULATOR ---
def _calculator(expression: str) -> dict:
    """Xavfsiz matematik hisob-kitob (ast moduli orqali, eval EMAS!)"""
    import ast
    import operator

    # Faqat raqamlar va matematik belgilarga ruxsat
    allowed = set("0123456789.+-*/()% ")
    if not all(c in allowed for c in expression):
        # So'z bilan yozilgan raqamlarni ham qo'llab-quvvatlash
        replacements = {
            "plyus": "+",
            "minus": "-",
            "ko'paytir": "*",
            "bo'l": "/",
            "plus": "+",
            "karra": "*",
            "foiz": "%",
        }
        for word, symbol in replacements.items():
            expression = expression.replace(word, symbol)

        # Raqamlarni ajratib olish
        expression = re.sub(r"[^0-9.+\-*/()% ]", "", expression)

    if not expression.strip():
        return {"error": "Matematik ifoda topilmadi"}

    # Xavfsiz operatorlar
    SAFE_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def _safe_eval(node):
        """AST orqali xavfsiz hisoblash — faqat raqam va operatorlarga ruxsat"""
        if isinstance(node, ast.Expression):
            return _safe_eval(node.body)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPS:
            left = _safe_eval(node.left)
            right = _safe_eval(node.right)
            return SAFE_OPS[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPS:
            return SAFE_OPS[type(node.op)](_safe_eval(node.operand))
        else:
            raise ValueError(f"Ruxsat etilmagan ifoda")

    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)

        # Natijani chiroyli formatlash
        if isinstance(result, float):
            if result == int(result):
                result = int(result)
            else:
                result = round(result, 6)

        return {
            "expression": expression.strip(),
            "result": result,
            "message": f"{expression.strip()} = {result}",
        }
    except ZeroDivisionError:
        return {"error": "Nolga bo'lib bo'lmaydi"}
    except Exception as e:
        return {"error": f"Hisoblash xatolik: {e}"}


TOOL_CALCULATOR = Tool(
    name="calculator",
    description="Matematik hisob-kitob qilish (qo'shish, ayirish, ko'paytirish, bo'lish, foiz)",
    parameters={
        "expression": {
            "type": "string",
            "description": "Matematik ifoda, masalan: '2 + 2', '100 * 15 / 100'",
            "required": True,
        },
    },
    function=_calculator,
    category="utility",
    capabilities=['calculation', 'math', 'arithmetic', 'compute'],
    aliases=['calc', 'hisobla', 'hisoblagich', 'math'],
    risk_level=RiskLevel.LOW,
    timeout=5.0,
    idempotent=True,
    destructive=False,
)


# --- 3. SYSTEM CONTROL ---
def _system_control(action: str, value: str = "") -> dict:
    """Tizim boshqaruvi — ilova ochish (aqlli: ishlayaptimi tekshiradi), ekran qulflash"""
    import subprocess
    import ctypes

    actions = {
        "lock": lambda: subprocess.run(
            ["rundll32.exe", "user32.dll,LockWorkStation"], shell=False
        ),
        "open_youtube": lambda: webbrowser.open("https://www.youtube.com"),
        "open_telegram": lambda: webbrowser.open("telegram:"),
        "open_chrome": lambda: webbrowser.open("https://google.com"),
        "open_discord": lambda: webbrowser.open("discord:"),
        "open_vscode": lambda: subprocess.Popen(["code"], shell=False),
        "open_explorer": lambda: subprocess.Popen(["explorer"], shell=False),
        "open_cmd": lambda: subprocess.Popen(
            ["cmd"], creationflags=subprocess.CREATE_NEW_CONSOLE
        ),
    }

    # Ilova → oyna nomi mapping (fokusga olish uchun)
    APP_WINDOW_NAMES = {
        "open_telegram": ["telegram"],
        "open_chrome": ["chrome", "google chrome"],
        "open_discord": ["discord"],
        "open_vscode": ["visual studio code", "vs code"],
    }

    if action in actions:
        # Ilova ochish — avval ishlayaptimi tekshir
        if action in APP_WINDOW_NAMES:
            try:
                import psutil

                window_names = APP_WINDOW_NAMES[action]
                is_running = False
                for proc in psutil.process_iter(["name"]):
                    proc_name = (proc.info["name"] or "").lower()
                    if any(wn in proc_name for wn in window_names):
                        is_running = True
                        break

                if is_running:
                    # Ishlayapti — oynani fokusga olish
                    try:
                        import ctypes
                        from ctypes import wintypes

                        user32 = ctypes.windll.user32
                        WNDENUMPROC = ctypes.WINFUNCTYPE(
                            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
                        )

                        # Xavfsiz xotira tiplari bilan ishlash (Crashes oldini oladi)
                        user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
                        user32.IsWindowVisible.argtypes = [wintypes.HWND]
                        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
                        user32.GetWindowTextW.argtypes = [
                            wintypes.HWND,
                            ctypes.c_wchar_p,
                            ctypes.c_int,
                        ]
                        user32.SetForegroundWindow.argtypes = [wintypes.HWND]

                        hwnd_list = []

                        def enum_cb(hwnd, _):
                            if user32.IsWindowVisible(hwnd):
                                length = user32.GetWindowTextLengthW(hwnd)
                                if length > 0:
                                    buf = ctypes.create_unicode_buffer(length + 1)
                                    user32.GetWindowTextW(hwnd, buf, length + 1)
                                    title = buf.value.lower()
                                    if any(wn in title for wn in window_names):
                                        hwnd_list.append(hwnd)
                            return True

                        # Python GC'dan himoyalash
                        safe_cb = WNDENUMPROC(enum_cb)
                        user32.EnumWindows(safe_cb, 0)

                        if hwnd_list:
                            user32.SetForegroundWindow(
                                hwnd_list[0]
                            )  # Birinchi oynani fokusga olish
                            return {
                                "message": f"{action}: allaqachon ochiq, fokusga olindi",
                                "was_running": True,
                            }
                    except Exception:
                        pass
            except ImportError:
                pass

        actions[action]()
        return {
            "message": f"{action} bajarildi",
            "action": action,
            "was_running": False,
        }

    elif action == "open_app" and value:
        # Xavfsiz ilova ochish — PowerShell Start-Process orqali
        # Umumiy ilova nomlari mapping
        APP_ALIASES = {
            "steam": "steam",
            "notepad": "notepad",
            "paint": "mspaint",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "calculator": "calc",
            "kalkulyator": "calc",
            "bloknotni": "notepad",
            "bloknot": "notepad",
            "spotify": "spotify",
            "obs": "obs64",
        }
        app_cmd = APP_ALIASES.get(value.lower().strip(), value)

        try:
            # PowerShell Start-Process — xavfsiz, shell injection yo'q
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f"Start-Process '{app_cmd}'"],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return {"message": f"'{value}' ochildi", "app": app_cmd}
        except Exception as e:
            return {"error": f"'{value}' ochilmadi: {e}"}
    else:
        return {
            "error": f"Noma'lum harakat: {action}",
            "available": list(actions.keys()) + ["open_app"],
        }


TOOL_SYSTEM = Tool(
    name="system_control",
    description="Kompyuter tizimini boshqarish — ilova ochish, ekranni qulflash",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: lock, open_youtube, open_telegram, open_chrome, open_discord, open_vscode, open_explorer, open_cmd",
            "required": True,
        },
        "value": {
            "type": "string",
            "description": "Qo'shimcha qiymat (ixtiyoriy)",
            "required": False,
        },
    },
    function=_system_control,
    category="system",
    capabilities=['system_power', 'system_control', 'power_management', 'app_launcher'],
    aliases=['system', 'power', 'tizim'],
    risk_level=RiskLevel.HIGH,
    timeout=10.0,
    idempotent=False,
    destructive=True,
)


# --- 4. MUSIC PLAYER ---
def _music_player(action: str, query: str = "", platform: str = "youtube") -> dict:
    """Musiqa qidirish va boshqarish"""
    import ctypes

    if action == "search":
        if not query:
            return {"error": "Qo'shiq nomi kerak"}

        urls = {
            "youtube": f"https://www.youtube.com/results?search_query={quote_plus(query)}+music",
            "yandex": f"https://music.yandex.ru/search?text={quote_plus(query)}",
            "spotify": f"https://open.spotify.com/search/{quote_plus(query)}",
        }
        url = urls.get(platform, urls["youtube"])
        webbrowser.open(url)
        return {"message": f"'{query}' {platform}'da qidirilmoqda", "url": url}

    elif action == "play":
        ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)  # MEDIA_PLAY_PAUSE
        ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
        return {"message": "Musiqa ijro etilmoqda"}

    elif action == "pause":
        ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
        ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)
        return {"message": "Musiqa to'xtatildi"}

    elif action == "next":
        ctypes.windll.user32.keybd_event(0xB0, 0, 0, 0)  # MEDIA_NEXT
        ctypes.windll.user32.keybd_event(0xB0, 0, 2, 0)
        return {"message": "Keyingi trek"}

    elif action == "previous":
        ctypes.windll.user32.keybd_event(0xB1, 0, 0, 0)  # MEDIA_PREV
        ctypes.windll.user32.keybd_event(0xB1, 0, 2, 0)
        return {"message": "Oldingi trek"}

    else:
        return {
            "error": f"Noma'lum: {action}",
            "available": ["search", "play", "pause", "next", "previous"],
        }


TOOL_MUSIC = Tool(
    name="music_player",
    description="Musiqa qidirish (YouTube, Yandex, Spotify) va boshqarish (play, pause, next, previous)",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: search, play, pause, next, previous",
            "required": True,
        },
        "query": {
            "type": "string",
            "description": "Qo'shiq nomi (faqat search uchun kerak)",
            "required": False,
        },
        "platform": {
            "type": "string",
            "description": "Platforma: youtube, yandex, spotify. Default: youtube",
            "required": False,
        },
    },
    function=_music_player,
    category="media",
    capabilities=['music', 'audio_playback', 'media'],
    aliases=['music', 'musiqa', 'pleer'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=False,
    destructive=False,
)


# --- 5. WEATHER ---
def _weather(city: str = "Tashkent") -> dict:
    """Ob-havo ma'lumotini olish"""
    import requests
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key:
        return {"error": "Ob-havo API kaliti topilmadi"}

    # O'zbek shahar nomlari
    SHAHAR = {
        "toshkent": "Tashkent",
        "samarqand": "Samarkand",
        "buxoro": "Bukhara",
        "andijon": "Andijan",
        "namangan": "Namangan",
        "fargona": "Fergana",
        "navoiy": "Navoi",
        "nukus": "Nukus",
        "qarshi": "Karshi",
        "jizzax": "Jizzakh",
        "termiz": "Termez",
        "urganch": "Urgench",
    }
    city_en = SHAHAR.get(city.lower().strip(), city)

    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city_en, "appid": api_key, "units": "metric", "lang": "en"},
            timeout=10,
        )
        if resp.status_code != 200:
            return {"error": f"Ob-havo olinmadi: {resp.status_code}"}

        data = resp.json()
        return {
            "city": city,
            "temp": round(data["main"]["temp"]),
            "feels_like": round(data["main"]["feels_like"]),
            "humidity": data["main"]["humidity"],
            "wind": round(data["wind"]["speed"], 1),
            "description": data["weather"][0]["description"],
            "message": f"{city}: {round(data['main']['temp'])}°C, {data['weather'][0]['description']}",
        }
    except Exception as e:
        return {"error": f"Ob-havo xatolik: {e}"}


TOOL_WEATHER = Tool(
    name="weather",
    description="Ob-havo ma'lumotini olish — harorat, namlik, shamol. O'zbekiston va dunyo shaharlari",
    parameters={
        "city": {
            "type": "string",
            "description": "Shahar nomi, masalan: Toshkent, Farg'ona, Samarqand. Default: Tashkent",
            "required": False,
        },
    },
    function=_weather,
    category="info",
    capabilities=['weather', 'forecast', 'temperature', 'climate'],
    aliases=['ob_havo', 'obhavo', 'weather_info'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=True,
    destructive=False,
)


# --- 6. REMINDER ---
def _reminder(action: str, text: str = "", number: int = 0) -> dict:
    """Eslatmalar boshqaruvi"""
    fayl = os.path.join(BASE_DIR, "eslatmalar.txt")

    if action == "add":
        if not text:
            return {"error": "Eslatma matni kerak"}
        sana = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(fayl, "a", encoding="utf-8") as f:
            f.write(f"[{sana}] {text}\n")
        return {"message": f"Eslatma saqlandi: {text}"}

    elif action == "list":
        if not os.path.exists(fayl):
            return {"message": "Eslatmalar yo'q", "reminders": []}
        with open(fayl, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        return {"message": f"{len(lines)} ta eslatma", "reminders": lines[-10:]}

    elif action == "delete":
        if not os.path.exists(fayl):
            return {"error": "Eslatmalar yo'q"}
        with open(fayl, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return {"error": "Eslatmalar yo'q"}

        idx = (number - 1) if number > 0 else -1
        removed = lines.pop(idx).strip()
        with open(fayl, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return {"message": f"O'chirildi: {removed}"}

    else:
        return {"error": f"Noma'lum: {action}", "available": ["add", "list", "delete"]}


TOOL_REMINDER = Tool(
    name="reminder",
    description="Eslatmalar: yangi qo'shish, ro'yxatini ko'rish, o'chirish",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: add, list, delete",
            "required": True,
        },
        "text": {
            "type": "string",
            "description": "Eslatma matni (add uchun)",
            "required": False,
        },
        "number": {
            "type": "integer",
            "description": "O'chiriladigan eslatma raqami (delete uchun)",
            "required": False,
        },
    },
    function=_reminder,
    category="productivity",
    capabilities=['reminder', 'alarm', 'notification_schedule'],
    aliases=['eslatma', 'eslat'],
    risk_level=RiskLevel.LOW,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 7. FILE MANAGER ---
def _file_manager(action: str, path: str = "", query: str = "") -> dict:
    """Fayl boshqaruvi"""
    import subprocess

    if action == "open":
        if not path:
            return {"error": "Fayl yo'li kerak"}
        if os.path.exists(path):
            os.startfile(path)
            return {"message": f"Ochildi: {path}"}
        else:
            return {"error": f"Topilmadi: {path}"}

    elif action == "open_folder":
        target = path or os.path.expanduser("~\\Desktop")
        subprocess.Popen(["explorer", target], shell=False)
        return {"message": f"Papka ochildi: {target}"}

    elif action == "list":
        target = path or BASE_DIR
        if not os.path.isdir(target):
            return {"error": f"Papka emas: {target}"}
        items = os.listdir(target)[:30]
        return {"message": f"{len(items)} ta element", "items": items}

    elif action == "search":
        if not query:
            return {"error": "Qidiruv so'rovi kerak"}
        target = path or os.path.expanduser("~\\Desktop")
        results = []
        for root, dirs, files in os.walk(target):
            for f in files:
                if query.lower() in f.lower():
                    results.append(os.path.join(root, f))
                    if len(results) >= 10:
                        break
            if len(results) >= 10:
                break
        return {"message": f"{len(results)} ta topildi", "results": results}

    else:
        return {
            "error": f"Noma'lum: {action}",
            "available": ["open", "open_folder", "list", "search"],
        }


TOOL_FILE = Tool(
    name="file_manager",
    description="Fayl boshqaruvi: ochish, papka ochish, ro'yxat ko'rish, fayl qidirish",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: open, open_folder, list, search",
            "required": True,
        },
        "path": {
            "type": "string",
            "description": "Fayl/papka yo'li (ixtiyoriy)",
            "required": False,
        },
        "query": {
            "type": "string",
            "description": "Qidiruv so'rovi (search uchun)",
            "required": False,
        },
    },
    function=_file_manager,
    category="utility",
    capabilities=['file_read', 'file_list', 'file_management', 'file_search'],
    aliases=['files', 'fayllar', 'file', 'fayl'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=True,
    destructive=False,
)


# --- 8. KNOWLEDGE (User Memory) ---
def _knowledge(action: str, key: str = "", value: str = "") -> dict:
    """Foydalanuvchi haqida bilimlarni saqlash va o'qish"""
    fayl = os.path.join(BASE_DIR, "data", "agent_knowledge.json")

    # Mavjud bilimlarni yuklash
    data = {}
    if os.path.exists(fayl):
        try:
            with open(fayl, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    if action == "save":
        if not key or not value:
            return {"error": "Key va value kerak"}
        data[key] = {"value": value, "saved_at": datetime.datetime.now().isoformat()}
        with open(fayl, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return {"message": f"Saqlandi: {key} = {value}"}

    elif action == "get":
        if key and key in data:
            return {
                "key": key,
                "value": data[key]["value"],
                "saved_at": data[key]["saved_at"],
            }
        elif not key:
            # Barcha bilimlar
            summary = {k: v["value"] for k, v in data.items()}
            return {"message": f"{len(summary)} ta bilim", "knowledge": summary}
        else:
            return {"error": f"'{key}' topilmadi"}

    elif action == "delete":
        if key in data:
            del data[key]
            with open(fayl, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return {"message": f"O'chirildi: {key}"}
        return {"error": f"'{key}' topilmadi"}

    else:
        return {"error": f"Noma'lum: {action}", "available": ["save", "get", "delete"]}


TOOL_KNOWLEDGE = Tool(
    name="knowledge",
    description="Foydalanuvchi haqida ma'lumotlarni eslab qolish va esga olish. Masalan: yoqtirgan til, ism, qiziqishlari",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: save (saqlash), get (o'qish), delete (o'chirish)",
            "required": True,
        },
        "key": {
            "type": "string",
            "description": "Bilim kaliti, masalan: 'favorite_language', 'hobby'",
            "required": False,
        },
        "value": {
            "type": "string",
            "description": "Bilim qiymati (save uchun)",
            "required": False,
        },
    },
    function=_knowledge,
    category="memory",
    capabilities=['knowledge_base', 'memory_store', 'fact_retrieval'],
    aliases=['bilim', 'xotira', 'facts'],
    risk_level=RiskLevel.LOW,
    timeout=5.0,
    idempotent=True,
    destructive=False,
)


# --- 9. DATETIME ---
def _datetime_tool(action: str = "now") -> dict:
    """Sana va vaqt ma'lumoti"""
    now = datetime.datetime.now()

    if action == "time":
        return {
            "message": f"Hozir soat {now.strftime('%H:%M')}",
            "time": now.strftime("%H:%M:%S"),
        }
    elif action == "date":
        return {
            "message": f"Bugun {now.strftime('%Y-yil %d-%B')}",
            "date": now.strftime("%Y-%m-%d"),
        }
    elif action == "now":
        return {
            "message": f"{now.strftime('%Y-yil %d-%B, %H:%M')}",
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": now.strftime("%A"),
        }
    else:
        return {"error": f"Noma'lum: {action}", "available": ["time", "date", "now"]}


TOOL_DATETIME = Tool(
    name="datetime",
    description="Hozirgi sana va vaqtni olish",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: time (vaqt), date (sana), now (ikkalasi). Default: now",
            "required": False,
        },
    },
    function=_datetime_tool,
    category="info",
    capabilities=['datetime', 'clock', 'current_time', 'calendar'],
    aliases=['vaqt', 'soat', 'sana', 'time', 'date'],
    risk_level=RiskLevel.LOW,
    timeout=3.0,
    idempotent=True,
    destructive=False,
)


# --- 10. SCHEDULER (Vaqtli vazifalar) ---
def _scheduler_tool(action: str, text: str = "", time_expr: str = "") -> dict:
    """Vaqtli vazifalar — eslatma, buyruq"""
    from core.agent_scheduler import get_scheduler, parse_time_expression

    scheduler = get_scheduler()

    if action == "add":
        if not text:
            return {"error": "Vazifa matni kerak"}

        # Vaqtni parse qilish
        time_info = parse_time_expression(time_expr) if time_expr else None

        if time_info and "delay_seconds" in time_info:
            task_id = scheduler.add(
                "reminder", {"text": text}, delay_seconds=time_info["delay_seconds"]
            )
            daqiqa = time_info["delay_seconds"] // 60
            return {
                "message": f"Eslatma {daqiqa} daqiqadan keyin: '{text}'",
                "task_id": task_id,
            }
        elif time_info and "run_at" in time_info:
            task_id = scheduler.add(
                "reminder", {"text": text}, run_at=time_info["run_at"]
            )
            vaqt = time_info["run_at"].strftime("%H:%M")
            return {"message": f"Eslatma soat {vaqt} da: '{text}'", "task_id": task_id}
        elif time_info and "repeat_seconds" in time_info:
            task_id = scheduler.add(
                "reminder",
                {"text": text},
                delay_seconds=time_info["repeat_seconds"],
                repeat_seconds=time_info["repeat_seconds"],
            )
            return {"message": f"Takroriy eslatma: '{text}'", "task_id": task_id}
        else:
            # Default: 5 daqiqadan keyin
            task_id = scheduler.add("reminder", {"text": text}, delay_seconds=300)
            return {
                "message": f"Eslatma 5 daqiqadan keyin: '{text}'",
                "task_id": task_id,
            }

    elif action == "list":
        tasks = scheduler.list_tasks()
        return {"message": f"{len(tasks)} ta vazifa", "tasks": tasks}

    elif action == "delete":
        if text:
            ok = scheduler.remove(text)
            return {"message": f"O'chirildi" if ok else "Topilmadi"}
        return {"error": "Vazifa ID kerak"}

    else:
        return {"error": f"Noma'lum: {action}", "available": ["add", "list", "delete"]}


TOOL_SCHEDULER = Tool(
    name="scheduler",
    description="Vaqtli vazifalar: eslatma qo'yish (X daqiqadan keyin, soat X da), ro'yxat ko'rish, o'chirish",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: add, list, delete",
            "required": True,
        },
        "text": {
            "type": "string",
            "description": "Eslatma matni (add uchun) yoki vazifa ID (delete uchun)",
            "required": False,
        },
        "time_expr": {
            "type": "string",
            "description": "Vaqt ifodasi: '5 daqiqadan keyin', 'soat 14:00', 'har 30 daqiqada'",
            "required": False,
        },
    },
    function=_scheduler_tool,
    category="productivity",
    capabilities=['scheduler', 'task_schedule', 'cron'],
    aliases=['reja', 'jadval', 'schedule'],
    risk_level=RiskLevel.MEDIUM,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 11. RAG READER (Fayl o'qish) ---
def _rag_reader(action: str, path: str = "", query: str = "") -> dict:
    """Lokal fayllarni o'qish — .txt, .py, .json, .md, .csv"""
    RUXSAT_KENGAYTMALAR = {
        ".txt",
        ".py",
        ".json",
        ".md",
        ".csv",
        ".log",
        ".ini",
        ".cfg",
        ".toml",
        ".yaml",
        ".yml",
        ".html",
        ".css",
        ".js",
    }
    MAX_SIZE = 3000  # Maksimal belgilar soni

    if action == "read":
        if not path:
            return {"error": "Fayl yo'li kerak"}
        if not os.path.exists(path):
            return {"error": f"Fayl topilmadi: {path}"}

        _, ext = os.path.splitext(path)
        if ext.lower() not in RUXSAT_KENGAYTMALAR:
            return {
                "error": f"Bu fayl turi qo'llab-quvvatlanmaydi: {ext}. Faqat: {', '.join(RUXSAT_KENGAYTMALAR)}"
            }

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(MAX_SIZE)

            total_lines = content.count("\n") + 1
            truncated = len(content) >= MAX_SIZE

            return {
                "path": path,
                "lines": total_lines,
                "truncated": truncated,
                "content": content,
                "message": f"{os.path.basename(path)}: {total_lines} qator"
                + (" (qisqartirildi)" if truncated else ""),
            }
        except Exception as e:
            return {"error": f"O'qish xatolik: {e}"}

    elif action == "search":
        if not query:
            return {"error": "Qidiruv so'rovi kerak"}
        target = path or BASE_DIR

        results = []
        try:
            for root, dirs, files in os.walk(target):
                # .git, __pycache__ dan o'tish
                dirs[:] = [
                    d
                    for d in dirs
                    if d not in {".git", "__pycache__", ".venv", "node_modules"}
                ]
                for fname in files:
                    _, ext = os.path.splitext(fname)
                    if ext.lower() not in RUXSAT_KENGAYTMALAR:
                        continue

                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if query.lower() in line.lower():
                                    results.append(
                                        {
                                            "file": fpath,
                                            "line": i,
                                            "text": line.strip()[:100],
                                        }
                                    )
                                    if len(results) >= 15:
                                        break
                    except Exception:
                        pass
                    if len(results) >= 15:
                        break
                if len(results) >= 15:
                    break
        except Exception as e:
            return {"error": f"Qidirish xatolik: {e}"}

        return {"message": f"'{query}': {len(results)} ta natija", "results": results}

    elif action == "info":
        target = path or BASE_DIR
        if not os.path.exists(target):
            return {"error": f"Topilmadi: {target}"}

        if os.path.isfile(target):
            size = os.path.getsize(target)
            return {
                "path": target,
                "type": "file",
                "size": size,
                "size_human": f"{size / 1024:.1f} KB",
                "message": f"{os.path.basename(target)}: {size / 1024:.1f} KB",
            }
        elif os.path.isdir(target):
            files = [
                f for f in os.listdir(target) if os.path.isfile(os.path.join(target, f))
            ]
            dirs = [
                d for d in os.listdir(target) if os.path.isdir(os.path.join(target, d))
            ]
            return {
                "path": target,
                "type": "directory",
                "files": len(files),
                "dirs": len(dirs),
                "items": files[:20] + [d + "/" for d in dirs[:10]],
                "message": f"{len(files)} fayl, {len(dirs)} papka",
            }

    else:
        return {"error": f"Noma'lum: {action}", "available": ["read", "search", "info"]}


TOOL_RAG = Tool(
    name="rag_reader",
    description="Lokal fayllarni o'qish va ichidan qidirish. .py, .txt, .json, .md fayllarni o'qiy oladi",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: read (o'qish), search (ichidan qidirish), info (ma'lumot)",
            "required": True,
        },
        "path": {
            "type": "string",
            "description": "Fayl yoki papka yo'li",
            "required": False,
        },
        "query": {
            "type": "string",
            "description": "Qidiruv so'rovi (search uchun)",
            "required": False,
        },
    },
    function=_rag_reader,
    category="utility",
    capabilities=['document_reading', 'rag', 'pdf_reader', 'text_extraction'],
    aliases=['hujjat', 'rag', 'read_doc'],
    risk_level=RiskLevel.LOW,
    timeout=15.0,
    idempotent=True,
    destructive=False,
)


# --- 12. CURRENCY (Valyuta kurslari) ---
def _currency(from_currency: str = "USD", to_currency: str = "UZS") -> dict:
    """Valyuta kurslarini olish (CBU API)"""
    import requests

    try:
        resp = requests.get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/", timeout=10)
        if resp.status_code != 200:
            return {"error": f"CBU API xatolik: {resp.status_code}"}

        data = resp.json()

        # Valyuta kodlari
        kursi = {}
        for item in data:
            code = item.get("Ccy", "")
            rate = float(item.get("Rate", 0))
            name = item.get("CcyNm_UZ", "")
            kursi[code] = {"rate": rate, "name": name}

        if from_currency.upper() == "UZS":
            return {"message": "UZS bazaviy valyuta (1 UZS = 1 UZS)", "rate": 1}

        target = from_currency.upper()
        if target in kursi:
            rate = kursi[target]["rate"]
            name = kursi[target]["name"]
            return {
                "from": target,
                "to": "UZS",
                "rate": rate,
                "name": name,
                "message": f"1 {target} = {rate:,.2f} UZS ({name})",
            }

        # Eng ko'p so'raladigan valyutalar
        popular = ["USD", "EUR", "RUB", "GBP", "JPY", "KRW", "CNY", "TRY"]
        available = [c for c in popular if c in kursi]
        return {"error": f"'{target}' topilmadi", "available": available}

    except Exception as e:
        return {"error": f"Valyuta kursi xatolik: {e}"}


TOOL_CURRENCY = Tool(
    name="currency",
    description="Valyuta kurslarini olish — Dollar, Yevro, Rubl, va boshqalar (CBU.uz)",
    parameters={
        "from_currency": {
            "type": "string",
            "description": "Valyuta kodi: USD, EUR, RUB, GBP. Default: USD",
            "required": False,
        },
        "to_currency": {
            "type": "string",
            "description": "Maqsad valyuta. Default: UZS",
            "required": False,
        },
    },
    function=_currency,
    category="info",
    capabilities=['currency_exchange', 'currency_converter', 'valyuta'],
    aliases=['valyuta', 'kurs', 'dollar', 'exchange'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=True,
    destructive=False,
)


# --- 13. TRANSLATOR (Tarjima) ---
def _translator(text: str, to_lang: str = "uz", from_lang: str = "auto") -> dict:
    """Matnni tarjima qilish (Google Translate orqali)"""
    import requests

    lang_map = {
        "uz": "uz",
        "uzbek": "uz",
        "o'zbek": "uz",
        "en": "en",
        "ingliz": "en",
        "english": "en",
        "ru": "ru",
        "rus": "ru",
        "russian": "ru",
    }

    target = lang_map.get(to_lang.lower(), to_lang)
    source = (
        lang_map.get(from_lang.lower(), from_lang) if from_lang != "auto" else "auto"
    )

    try:
        # Google Translate API (bepul, cheklangan)
        resp = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text},
            timeout=10,
        )

        if resp.status_code != 200:
            return {"error": f"Tarjima xatolik: {resp.status_code}"}

        data = resp.json()
        translated = "".join(part[0] for part in data[0] if part[0])
        detected = data[2] if len(data) > 2 else source

        return {
            "original": text,
            "translated": translated,
            "from_lang": detected,
            "to_lang": target,
            "message": f"[{detected}→{target}] {translated}",
        }
    except Exception as e:
        return {"error": f"Tarjima xatolik: {e}"}


TOOL_TRANSLATOR = Tool(
    name="translator",
    description="Matnni tarjima qilish — o'zbek, ingliz, rus tillari orasida",
    parameters={
        "text": {
            "type": "string",
            "description": "Tarjima qilinadigan matn",
            "required": True,
        },
        "to_lang": {
            "type": "string",
            "description": "Maqsad til: uz, en, ru. Default: uz",
            "required": False,
        },
        "from_lang": {
            "type": "string",
            "description": "Manba til: auto, uz, en, ru. Default: auto",
            "required": False,
        },
    },
    function=_translator,
    category="utility",
    capabilities=['translation', 'translate', 'language_translation'],
    aliases=['tarjima', 'translate', 'tarjimon'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=True,
    destructive=False,
)


# --- 14. SCREEN ANALYZE (Ekran tahlil) ---
def _screen_analyze(question: str = "Ekranda nima bor?") -> dict:
    """Ekranni screenshot olib, AI bilan tahlil qilish"""
    try:
        from core.ai_engine import ekran_tahlil

        result = ekran_tahlil(question)
        if result:
            return {"message": result, "question": question}
        else:
            return {"error": "Ekran tahlil qilinmadi"}
    except ImportError:
        return {"error": "ai_engine moduli topilmadi"}
    except Exception as e:
        return {"error": f"Ekran tahlil xatolik: {e}"}


TOOL_SCREEN = Tool(
    name="screen_analyze",
    description="Ekranni screenshot olib, AI bilan tahlil qilish. Ekranda nima borligini ko'rish",
    parameters={
        "question": {
            "type": "string",
            "description": "Ekran haqida savol, masalan: 'Ekranda qaysi ilova ochiq?'. Default: 'Ekranda nima bor?'",
            "required": False,
        },
    },
    function=_screen_analyze,
    category="system",
    capabilities=['screen_vision', 'screen_ocr', 'desktop_vision'],
    aliases=['ekran', 'screen', 'vision'],
    risk_level=RiskLevel.LOW,
    timeout=15.0,
    idempotent=True,
    destructive=False,
)


# --- 15. FILE WRITE (Fayl yozish) ---
def _file_write(path: str, content: str, mode: str = "write") -> dict:
    """Fayl yaratish yoki yozish — kod, HTML, CSS, JSON, matn fayllar"""
    import shutil

    MAX_FILE_SIZE = 50000  # 50KB limit

    # Xavfsizlik — faqat matn fayllariga ruxsat
    RUXSAT_KENGAYTMALAR = {
        ".txt",
        ".py",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".json",
        ".md",
        ".csv",
        ".xml",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".sh",
        ".bat",
        ".ps1",
        ".sql",
        ".env",
        ".gitignore",
        ".jsx",
        ".tsx",
        ".vue",
        ".svelte",
        ".php",
        ".rb",
        ".go",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rs",
        ".swift",
    }

    if not path:
        return {"error": "Fayl yo'li kerak"}

    if len(content) > MAX_FILE_SIZE:
        return {
            "error": f"Fayl juda katta ({len(content)} belgi). Maksimal: {MAX_FILE_SIZE}"
        }

    # Kengaytmani tekshirish
    _, ext = os.path.splitext(path)
    if ext.lower() not in RUXSAT_KENGAYTMALAR:
        return {
            "error": f"'{ext}' fayl turi qo'llab-quvvatlanmaydi. Ruxsat: {', '.join(sorted(RUXSAT_KENGAYTMALAR)[:10])}..."
        }

    # To'liq yo'l yaratish (nisbiy yo'l bo'lsa, Desktop ga yozadi)
    if not os.path.isabs(path):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        path = os.path.join(desktop, path)

    try:
        # Papkani yaratish (agar yo'q bo'lsa)
        papka = os.path.dirname(path)
        if papka:
            os.makedirs(papka, exist_ok=True)

        if mode == "append":
            with open(path, "a", encoding="utf-8") as f:
                f.write(content)
            return {
                "success": True,
                "path": path,
                "message": f"Qo'shildi: {os.path.basename(path)}",
                "size": len(content),
            }
        else:
            # Mavjud faylni backup qilish
            if os.path.exists(path):
                backup = path + ".bak"
                shutil.copy2(path, backup)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "success": True,
                "path": path,
                "message": f"Yaratildi: {os.path.basename(path)}",
                "size": len(content),
            }
    except PermissionError:
        return {"error": f"Ruxsat yo'q: {path}"}
    except Exception as e:
        return {"error": f"Yozish xatolik: {e}"}


TOOL_FILE_WRITE = Tool(
    name="file_write",
    description="Fayl yaratish yoki yozish. Kod, HTML, CSS, Python, JavaScript va boshqa matn fayllarni yaratadi. Nisbiy yo'l berilsa Desktop ga yozadi.",
    parameters={
        "path": {
            "type": "string",
            "description": "Fayl yo'li. Masalan: 'login.html', 'styles.css', yoki to'liq yo'l",
            "required": True,
        },
        "content": {
            "type": "string",
            "description": "Faylga yoziladigan mazmun (kod, matn)",
            "required": True,
        },
        "mode": {
            "type": "string",
            "description": "Rejim: 'write' (yangi yozish) yoki 'append' (qo'shish). Default: write",
            "required": False,
        },
    },
    function=_file_write,
    category="coding",
    capabilities=['file_write', 'file_create', 'code_generation'],
    aliases=['fayl_yozish', 'write_file', 'save_file'],
    risk_level=RiskLevel.MEDIUM,
    timeout=10.0,
    idempotent=False,
    destructive=False,
)


def _app_check(category: str = "code_editor", app_name: str = "") -> dict:
    """Kompyuterda o'rnatilgan ilovalarni tekshirish + ishlayaptimi (process check)"""
    import subprocess
    import glob
    import psutil

    # Mashhur ilovalar bazasi
    APP_DATABASE = {
        "code_editor": {
            "cursor": {
                "cmd": "cursor",
                "paths": [r"C:\Users\*\AppData\Local\Programs\cursor\Cursor.exe"],
                "priority": 1,
            },
            "vscode": {
                "cmd": "code",
                "paths": [
                    r"C:\Program Files\Microsoft VS Code\Code.exe",
                    r"C:\Users\*\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                ],
                "priority": 2,
            },
            "sublime": {
                "cmd": "subl",
                "paths": [
                    r"C:\Program Files\Sublime Text\sublime_text.exe",
                    r"C:\Program Files\Sublime Text 3\sublime_text.exe",
                ],
                "priority": 3,
            },
            "notepad++": {
                "cmd": "notepad++",
                "paths": [
                    r"C:\Program Files\Notepad++\notepad++.exe",
                    r"C:\Program Files (x86)\Notepad++\notepad++.exe",
                ],
                "priority": 4,
            },
            "pycharm": {
                "cmd": None,
                "paths": [r"C:\Program Files\JetBrains\PyCharm*\bin\pycharm64.exe"],
                "priority": 5,
            },
            "webstorm": {
                "cmd": None,
                "paths": [r"C:\Program Files\JetBrains\WebStorm*\bin\webstorm64.exe"],
                "priority": 6,
            },
            "vim": {"cmd": "vim", "paths": [], "priority": 7},
            "notepad": {
                "cmd": "notepad",
                "paths": [r"C:\Windows\notepad.exe"],
                "priority": 99,
            },
        },
        "browser": {
            "chrome": {
                "cmd": "chrome",
                "paths": [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                ],
                "priority": 1,
            },
            "brave": {
                "cmd": "brave",
                "paths": [
                    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
                ],
                "priority": 2,
            },
            "firefox": {
                "cmd": "firefox",
                "paths": [r"C:\Program Files\Mozilla Firefox\firefox.exe"],
                "priority": 3,
            },
            "edge": {
                "cmd": "msedge",
                "paths": [
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
                ],
                "priority": 4,
            },
        },
        "terminal": {
            "windows_terminal": {
                "cmd": "wt",
                "paths": [r"C:\Users\*\AppData\Local\Microsoft\WindowsApps\wt.exe"],
                "priority": 1,
            },
            "powershell": {
                "cmd": "powershell",
                "paths": [r"C:\Windows\System32\WindowsPowerShell\*\powershell.exe"],
                "priority": 2,
            },
            "cmd": {
                "cmd": "cmd",
                "paths": [r"C:\Windows\System32\cmd.exe"],
                "priority": 3,
            },
            "git_bash": {
                "cmd": "bash",
                "paths": [r"C:\Program Files\Git\bin\bash.exe"],
                "priority": 4,
            },
        },
        "dev_tools": {
            "node": {"cmd": "node", "paths": [], "priority": 1},
            "python": {"cmd": "python", "paths": [], "priority": 2},
            "git": {
                "cmd": "git",
                "paths": [r"C:\Program Files\Git\bin\git.exe"],
                "priority": 3,
            },
            "npm": {"cmd": "npm", "paths": [], "priority": 4},
            "pip": {"cmd": "pip", "paths": [], "priority": 5},
        },
    }

    # Process nomlari — ishlayaptimi tekshirish uchun
    PROCESS_NAMES = {
        "vscode": ["code.exe"],
        "cursor": ["cursor.exe"],
        "sublime": ["sublime_text.exe"],
        "notepad++": ["notepad++.exe"],
        "pycharm": ["pycharm64.exe"],
        "chrome": ["chrome.exe"],
        "brave": ["brave.exe"],
        "firefox": ["firefox.exe"],
        "edge": ["msedge.exe"],
        "telegram": ["telegram.exe"],
        "discord": ["discord.exe"],
        "node": ["node.exe"],
        "python": ["python.exe"],
    }

    # Process ro'yxatini bir marta olish (cache) — har safar full scan qilmaslik
    _active_processes = {}
    try:
        for proc in psutil.process_iter(["name", "pid"]):
            pname = (proc.info["name"] or "").lower()
            if pname:
                _active_processes[pname] = proc.info["pid"]
    except Exception:
        pass

    def _is_running(name):
        """Process ishlayaptimi tekshirish (cached)"""
        proc_names = PROCESS_NAMES.get(name, [f"{name}.exe"])
        for pname in proc_names:
            pid = _active_processes.get(pname.lower())
            if pid is not None:
                return {"running": True, "pid": pid}
        return {"running": False, "pid": None}

    def _check_app(name, info):
        """Bitta ilovani tekshirish (o'rnatilganmi + ishlayaptimi)"""
        running_info = _is_running(name)

        # 1. PATH da bormi? (cmd orqali)
        if info.get("cmd"):
            try:
                result = subprocess.run(
                    ["where", info["cmd"]],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW
                    if hasattr(subprocess, "CREATE_NO_WINDOW")
                    else 0,
                )
                if result.returncode == 0:
                    found_path = result.stdout.strip().split("\n")[0]
                    return {
                        "name": name,
                        "found": True,
                        "path": found_path,
                        "method": "PATH",
                        **running_info,
                    }
            except Exception:
                pass

        # 2. Standart o'rnatish joylarida bormi?
        for pattern in info.get("paths", []):
            matches = glob.glob(pattern)
            if matches:
                return {
                    "name": name,
                    "found": True,
                    "path": matches[0],
                    "method": "path_scan",
                    **running_info,
                }

        # 3. Process ishlayapti lekin PATH da yo'q
        if running_info["running"]:
            return {
                "name": name,
                "found": True,
                "path": "(process)",
                "method": "process",
                **running_info,
            }

        return {"name": name, "found": False, **running_info}

    # Aniq ilova nomi berilgan bo'lsa
    if app_name:
        try:
            from core.app_detector import get_app_detector
            info = get_app_detector().detect_app(app_name)
            if info.found:
                return {
                    "name": info.name,
                    "found": True,
                    "running": info.running,
                    "pid": info.pid,
                    "path": info.exe_path,
                    "family": info.family,
                    "canonical_name": info.canonical_name,
                    "message": info.format_uzbek_response(app_name),
                }
        except Exception as e:
            logger.warning(f"AppDetector xatosi _app_check da: {e}")

        app_name_lower = app_name.lower().strip()
        for cat_name, apps in APP_DATABASE.items():
            if app_name_lower in apps:
                result = _check_app(app_name_lower, apps[app_name_lower])
                return result
        # Bazada yo'q — where bilan tekshiramiz
        try:
            result = subprocess.run(
                ["where", app_name],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )
            if result.returncode == 0:
                return {
                    "name": app_name,
                    "found": True,
                    "path": result.stdout.strip().split("\n")[0],
                }
        except Exception:
            pass
        return {"name": app_name, "found": False}

    # Kategoriya bo'yicha barcha ilovalarni tekshirish
    if category not in APP_DATABASE:
        return {
            "error": f"Kategoriya topilmadi: {category}",
            "available": list(APP_DATABASE.keys()),
        }

    found = []
    not_found = []

    for name, info in APP_DATABASE[category].items():
        result = _check_app(name, info)
        if result["found"]:
            result["priority"] = info["priority"]
            found.append(result)
        else:
            not_found.append(name)

    # Priority bo'yicha tartiblash
    found.sort(key=lambda x: x.get("priority", 99))
    best = found[0]["name"] if found else None

    return {
        "category": category,
        "found": [f["name"] for f in found],
        "found_details": found,
        "not_found": not_found,
        "best": best,
        "message": f"{category}: {len(found)} ta topildi — {', '.join(f['name'] for f in found)}"
        if found
        else f"{category}: hech narsa topilmadi",
    }


TOOL_APP_CHECK = Tool(
    name="app_check",
    description="Kompyuterda o'rnatilgan ilovalarni tekshirish. Code editorlar, brauzerlar, terminallar, dev tools — barchasini topadi",
    parameters={
        "category": {
            "type": "string",
            "description": "Kategoriya: code_editor, browser, terminal, dev_tools. Default: code_editor",
            "required": False,
        },
        "app_name": {
            "type": "string",
            "description": "Aniq ilova nomi: vscode, cursor, chrome, node, python. Berilsa faqat shu tekshiriladi",
            "required": False,
        },
    },
    function=_app_check,
    category="system",
    capabilities=['app_detection', 'software_check', 'installed_apps'],
    aliases=['dasturlar', 'apps', 'check_app'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=True,
    destructive=False,
)


# --- 17. ASK USER (Foydalanuvchidan so'rash) ---
_ask_user_callback = None  # main.py dan o'rnatiladi


def set_ask_user_callback(callback):
    """main.py dan tingla() funksiyasini o'rnatish"""
    global _ask_user_callback
    _ask_user_callback = callback


def _ask_user(question: str) -> dict:
    """Foydalanuvchidan savol so'rash va javobni kutish"""
    if not question:
        return {"error": "Savol matni kerak"}

    # GUI ga savolni ko'rsatish
    try:
        # main.py dagi gui_ga_xabar_yuborish va tingla() orqali
        if _ask_user_callback:
            answer = _ask_user_callback(question)
            if answer:
                return {
                    "question": question,
                    "answer": answer,
                    "message": f"User javobi: {answer}",
                }
            else:
                return {
                    "question": question,
                    "answer": "",
                    "message": "User javob bermadi",
                    "timeout": True,
                }
        else:
            # Fallback — input() orqali (GUI bo'lmasa)
            logger.warning("ask_user: callback o'rnatilmagan, input() ishlatilmoqda")
            return {
                "question": question,
                "answer": "",
                "no_callback": True,
                "message": f"Savolni foydalanuvchiga aytib bering: {question}",
            }
    except Exception as e:
        return {"error": f"Savol so'rash xatolik: {e}"}


TOOL_ASK_USER = Tool(
    name="ask_user",
    description="Foydalanuvchidan savol so'rash va javobini kutish. Masalan: 'Qaysi tilda yozayin?', 'Bootstrap ishlatayinmi?', 'O'rnatayinmi?'",
    parameters={
        "question": {
            "type": "string",
            "description": "Foydalanuvchiga beriladigan savol",
            "required": True,
        },
    },
    function=_ask_user,
    category="interaction",
    capabilities=['user_interaction', 'ask_question', 'clarify_with_user'],
    aliases=['savol', "so'rash", 'ask'],
    risk_level=RiskLevel.LOW,
    timeout=30.0,
    idempotent=False,
    destructive=False,
)


# --- 18. SCREEN CLICK (Ekranda bosish) ---
def _screen_click(
    action: str = "click", x: int = 0, y: int = 0, window: str = "", text: str = ""
) -> dict:
    """Ekranda sichqoncha bilan bosish, oyna fokusga olish"""
    import ctypes
    import pyautogui

    if action == "click":
        if x <= 0 or y <= 0:
            return {"error": "x va y koordinatalar kerak (0 dan katta)"}
        screen_w, screen_h = pyautogui.size()
        if x > screen_w or y > screen_h:
            return {
                "error": f"Koordinata ekrandan tashqarida. Ekran: {screen_w}x{screen_h}"
            }
        pyautogui.click(x, y)
        return {"message": f"Bosildi: ({x}, {y})", "x": x, "y": y}

    elif action == "double_click":
        if x <= 0 or y <= 0:
            return {"error": "x va y koordinatalar kerak"}
        pyautogui.doubleClick(x, y)
        return {"message": f"Ikki marta bosildi: ({x}, {y})", "x": x, "y": y}

    elif action == "right_click":
        if x <= 0 or y <= 0:
            return {"error": "x va y koordinatalar kerak"}
        pyautogui.rightClick(x, y)
        return {"message": f"O'ng tugma bosildi: ({x}, {y})", "x": x, "y": y}

    elif action == "focus_window":
        if not window:
            return {"error": "window nomi kerak"}
        window_lower = window.lower()
        try:
            hwnd_list = []
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
            )

            def enum_cb(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value.lower()
                        if window_lower in title:
                            hwnd_list.append((hwnd, buf.value))
                return True

            ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)

            if hwnd_list:
                hwnd, title = hwnd_list[0]
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                return {
                    "message": f"Oyna fokusga olindi: {title}",
                    "window": title,
                    "found": True,
                }
            else:
                return {"message": f"'{window}' oynasi topilmadi", "found": False}
        except Exception as e:
            return {"error": f"Fokus xatolik: {e}"}

    elif action == "list_windows":
        # Barcha ochiq oynalarni ro'yxati
        try:
            windows = []
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
            )

            def enum_cb(hwnd, _):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                        if buf.value.strip():
                            windows.append(buf.value)
                return True

            ctypes.windll.user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
            return {"message": f"{len(windows)} ta oyna ochiq", "windows": windows[:20]}
        except Exception as e:
            return {"error": f"Oynalar ro'yxati xatolik: {e}"}

    elif action == "scroll":
        amount = y if y != 0 else -3  # y = scroll miqdori (manfiy = pastga)
        pyautogui.scroll(amount)
        direction = "yuqoriga" if amount > 0 else "pastga"
        return {"message": f"Scroll {direction}: {abs(amount)}", "amount": amount}

    else:
        return {
            "error": f"Noma'lum: {action}",
            "available": [
                "click",
                "double_click",
                "right_click",
                "focus_window",
                "list_windows",
                "scroll",
            ],
        }


TOOL_SCREEN_CLICK = Tool(
    name="screen_click",
    description="Ekranda sichqoncha bilan bosish, oynani fokusga olish, ochiq oynalar ro'yxati. Koordinatalarni screen_analyze dan oling",
    parameters={
        "action": {
            "type": "string",
            "description": "Harakat: click, double_click, right_click, focus_window, list_windows, scroll",
            "required": True,
        },
        "x": {
            "type": "integer",
            "description": "X koordinata (click/double_click/right_click uchun)",
            "required": False,
        },
        "y": {
            "type": "integer",
            "description": "Y koordinata (click uchun) yoki scroll miqdori (scroll uchun)",
            "required": False,
        },
        "window": {
            "type": "string",
            "description": "Oyna nomi (focus_window uchun). Masalan: 'Telegram', 'Chrome'",
            "required": False,
        },
    },
    function=_screen_click,
    category="interaction",
    capabilities=['mouse_click', 'gui_interaction', 'desktop_automation'],
    aliases=['bosish', 'click', 'mouse'],
    risk_level=RiskLevel.MEDIUM,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 19. KEYBOARD TYPE (Matn yozish) ---
def _keyboard_type(text: str, interval: float = 0.02) -> dict:
    """Fokuslanagan ilovaga matn yozish"""
    import pyautogui
    import time

    if not text:
        return {"error": "Matn kerak"}

    if len(text) > 5000:
        return {"error": f"Matn juda uzun ({len(text)} belgi). Maksimal: 5000"}

    try:
        time.sleep(0.3)  # Ilova tayyorlanishi uchun
        pyautogui.typewrite(
            text, interval=interval
        ) if text.isascii() else pyautogui.write(text)
        return {
            "message": f"Yozildi: {text[:50]}{'...' if len(text) > 50 else ''}",
            "length": len(text),
        }
    except Exception as e:
        return {"error": f"Yozish xatolik: {e}"}


TOOL_KEYBOARD_TYPE = Tool(
    name="keyboard_type",
    description="Fokuslanagan ilovaga matn yozish. Masalan: qidiruv maydoniga matn kiritish, fayl nomi yozish",
    parameters={
        "text": {"type": "string", "description": "Yoziladigan matn", "required": True},
        "interval": {
            "type": "number",
            "description": "Harflar orasidagi pauza (soniya). Default: 0.02",
            "required": False,
        },
    },
    function=_keyboard_type,
    category="interaction",
    capabilities=['keyboard_input', 'type_text', 'desktop_automation'],
    aliases=['yozish', 'type', 'keyboard'],
    risk_level=RiskLevel.MEDIUM,
    timeout=10.0,
    idempotent=False,
    destructive=False,
)


# --- 20. KEYBOARD SHORTCUT (Tugma bosish) ---
def _keyboard_shortcut(keys: str, repeat: int = 1) -> dict:
    """Klaviatura shortcutlari — Ctrl+F, Enter, Alt+Tab va boshqalar"""
    import keyboard as kb
    import time

    if not keys:
        return {"error": "Tugma kerak"}

    # Mashhur shortcutlar lug'ati (o'zbekcha -> shortcut)
    SHORTCUT_MAP = {
        "qidirish": "ctrl+f",
        "qidir": "ctrl+f",
        "saqlash": "ctrl+s",
        "saqla": "ctrl+s",
        "nusxalash": "ctrl+c",
        "nusxa": "ctrl+c",
        "joylash": "ctrl+v",
        "qaytarish": "ctrl+z",
        "barchasi": "ctrl+a",
        "yangi": "ctrl+n",
        "yopish": "alt+f4",
        "oyna_almash": "alt+tab",
    }

    actual_keys = SHORTCUT_MAP.get(keys.lower(), keys)

    try:
        for i in range(repeat):
            kb.send(actual_keys)
            if repeat > 1:
                time.sleep(0.1)
        return {
            "message": f"'{actual_keys}' bosildi"
            + (f" ({repeat} marta)" if repeat > 1 else ""),
            "keys": actual_keys,
        }
    except Exception as e:
        return {"error": f"Shortcut xatolik: {e}"}


TOOL_KEYBOARD_SHORTCUT = Tool(
    name="keyboard_shortcut",
    description="Klaviatura shortcutlari yuborish. Masalan: 'ctrl+f' (qidirish), 'enter', 'alt+tab' (oyna almash), 'ctrl+s' (saqlash), 'escape'",
    parameters={
        "keys": {
            "type": "string",
            "description": "Tugma yoki shortcut: 'enter', 'ctrl+f', 'alt+tab', 'escape', 'tab', 'ctrl+s'. O'zbekcha ham bo'ladi: 'qidirish', 'saqlash'",
            "required": True,
        },
        "repeat": {
            "type": "integer",
            "description": "Necha marta bosish. Default: 1",
            "required": False,
        },
    },
    function=_keyboard_shortcut,
    category="interaction",
    capabilities=['hotkey', 'keyboard_shortcut', 'key_combination'],
    aliases=['klaviatura', 'shortcut', 'hotkey'],
    risk_level=RiskLevel.MEDIUM,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 21. CLIPBOARD (Nusxa) ---
def _clipboard(action: str = "get", text: str = "") -> dict:
    """Clipboard bilan ishlash: olish (get) yoki qo'yish (set)"""
    try:
        import win32clipboard

        win32clipboard.OpenClipboard()
        if action == "get":
            try:
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                return {
                    "message": data[:500] if data else "Clipboard bo'sh",
                    "content": data or "",
                }
            except:
                win32clipboard.CloseClipboard()
                return {"message": "Clipboard bo'sh", "content": ""}
        elif action == "set":
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            return {"message": f"Nusxalandi: {text[:50]}..."}
        else:
            win32clipboard.CloseClipboard()
            return {"error": "Noto'g'ri action. 'get' yoki 'set'"}
    except ImportError:
        return {"error": "win32clipboard mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


TOOL_CLIPBOARD = Tool(
    name="clipboard",
    description="Bufer (clipboard) dan matn olish yoki bu yerga matn qo'yish",
    parameters={
        "action": {
            "type": "string",
            "description": "'get' (olish) yoki 'set' (qo'yish). Default: get",
            "required": False,
        },
        "text": {
            "type": "string",
            "description": "Qo'yiladigan matn (action='set' bo'lsa)",
            "required": False,
        },
    },
    function=_clipboard,
    category="system",
    capabilities=['clipboard', 'copy_paste', 'clipboard_history'],
    aliases=['bufer', 'clipboard', 'copy'],
    risk_level=RiskLevel.LOW,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 22. PROCESS MANAGER (Protseslar) ---
def _process_manager(action: str = "list", name: str = "", pid: int = 0) -> dict:
    """Process'lar bilan ishlash: ro'yxat (list), to'xtatish (kill)"""
    try:
        import psutil

        if action == "list":
            procs = [
                (p.pid, p.name(), p.cpu_percent())
                for p in psutil.process_iter(["name", "cpu_percent"])
            ]
            return {"processes": procs[:30], "message": f"{len(procs)} ta process"}
        elif action == "kill":
            for p in psutil.process_iter(["name", "pid"]):
                if name.lower() in (p.info["name"] or "").lower():
                    p.terminate()
                    return {"message": f"{name} to'xtatildi"}
            return {"error": f"'{name}' topilmadi"}
        elif action == "info":
            try:
                p = psutil.Process(pid)
                return {
                    "name": p.name(),
                    "cpu": p.cpu_percent(),
                    "memory": p.memory_info().rss // (1024**2),
                    "status": p.status(),
                }
            except:
                return {"error": f"PID {pid} topilmadi"}
        else:
            return {"error": "action: 'list', 'kill', yoki 'info'"}
    except ImportError:
        return {"error": "psutil mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


TOOL_PROCESS_MANAGER = Tool(
    name="process_manager",
    description="Protseslar ro'yxatini ko'rish yoki ularni to'xtatish",
    parameters={
        "action": {
            "type": "string",
            "description": "'list' (ro'yxat), 'kill' (to'xtatish), 'info' (ma'lumot). Default: list",
            "required": False,
        },
        "name": {
            "type": "string",
            "description": "Process nomi (action='kill' uchun)",
            "required": False,
        },
        "pid": {
            "type": "integer",
            "description": "Process PID (action='info' uchun)",
            "required": False,
        },
    },
    function=_process_manager,
    category="system",
    capabilities=['process_management', 'task_manager', 'kill_process'],
    aliases=['jarayon', 'process', 'tasklist'],
    risk_level=RiskLevel.MEDIUM,
    timeout=10.0,
    idempotent=False,
    destructive=True,
)


# --- 23. AUDIO CONTROL (Ovoz) ---
def _audio_control(action: str = "get", level: int = 50) -> dict:
    """Sistema ovozini boshqarish"""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        if action == "get":
            current = int(volume.GetMasterVolumeLevelScalar() * 100)
            muted = volume.GetMute()
            return {
                "level": current,
                "muted": bool(muted),
                "message": f"Ovoz: {current}%{' (ovoz ochiq)' if not muted else ' (ovoz yopiq)'}",
            }
        elif action == "set":
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            return {"message": f"Ovoz {level}% ga qo'yildi"}
        elif action == "up":
            current = int(volume.GetMasterVolumeLevelScalar() * 100)
            volume.SetMasterVolumeLevelScalar(min(current + 10, 100) / 100, None)
            return {"message": f"Ovoz +10%, hozir {min(current + 10, 100)}%"}
        elif action == "down":
            current = int(volume.GetMasterVolumeLevelScalar() * 100)
            volume.SetMasterVolumeLevelScalar(max(current - 10, 0) / 100, None)
            return {"message": f"Ovoz -10%, hozir {max(current - 10, 0)}%"}
        elif action == "mute":
            volume.SetMute(1, None)
            return {"message": "Ovoz o'chirildi"}
        elif action == "unmute":
            volume.SetMute(0, None)
            return {"message": "Ovoz yoqildi"}
        else:
            return {"error": "action: 'get', 'set', 'up', 'down', 'mute', 'unmute'"}
    except ImportError:
        return {"error": "pycaw mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


TOOL_AUDIO_CONTROL = Tool(
    name="audio_control",
    description="Sistema ovozini olish, o'rnatish, oshirish/pasaytirish, mute/qo'shish",
    parameters={
        "action": {
            "type": "string",
            "description": "'get' (olish), 'set' (o'rnatish), 'up', 'down', 'mute', 'unmute'. Default: get",
            "required": False,
        },
        "level": {
            "type": "integer",
            "description": "Ovoz darajasi 0-100 (action='set' uchun)",
            "required": False,
        },
    },
    function=_audio_control,
    category="system",
    capabilities=['volume_control', 'mute_audio', 'sound_system'],
    aliases=['ovoz', 'tovush', 'volume'],
    risk_level=RiskLevel.LOW,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 24. SYSTEM INFO (Tizim ma'lumot) ---
def _system_info(category: str = "all") -> dict:
    """Sistema ma'lumotlarini olish"""
    try:
        import psutil
        import platform
        import os

        info = {}
        if category in ("all", "cpu"):
            cpu_name = platform.processor() or "CPU"
            if os.name == "nt":
                try:
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
                        reg_name, _ = winreg.QueryValueEx(k, 'ProcessorNameString')
                        if reg_name:
                            cpu_name = str(reg_name).strip()
                except Exception:
                    pass
            info["cpu_model"] = cpu_name
            info["cpu_usage"] = f"{psutil.cpu_percent()}%"
            info["cpu_cores"] = f"{psutil.cpu_count(logical=False) or 1} fiz / {psutil.cpu_count(logical=True) or 1} mantiqiy"
        if category in ("all", "gpu", "videokarta"):
            gpus = []
            if os.name == "nt":
                try:
                    import winreg
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
            if gpus:
                g = gpus[0]
                info["gpu_model"] = g["name"]
                if g.get("vram_gb"):
                    info["gpu_vram"] = f"{g['vram_gb']} GB"
                if g.get("driver"):
                    info["gpu_driver"] = g["driver"]
            else:
                info["gpu_model"] = "Standart video adapter"
        if category in ("all", "ram"):
            mem = psutil.virtual_memory()
            info["ram"] = (
                f"{mem.percent}% ({round(mem.used / (1024**3), 1)}GB / {round(mem.total / (1024**3), 1)}GB)"
            )
        if category in ("all", "disk"):
            root_drive = "C:\\" if os.name == "nt" else "/"
            disk = psutil.disk_usage(root_drive)
            info["disk"] = f"{disk.percent}% ({round(disk.free / (1024**3), 1)}GB bo'sh / {round(disk.total / (1024**3), 1)}GB)"
        if category in ("all", "battery"):
            bat = psutil.sensors_battery()
            if bat:
                info["battery"] = (
                    f"{bat.percent}%{' (zaryadda)' if bat.power_plugged else ''}"
                )
        return {
            "info": info,
            "message": " | ".join(f"{k}: {v}" for k, v in info.items()),
        }
    except ImportError:
        return {"error": "psutil mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


TOOL_SYSTEM_INFO = Tool(
    name="system_info",
    description="CPU, RAM, GPU (videokarta), Disk, Battery haqida ma'lumot olish",
    parameters={
        "category": {
            "type": "string",
            "description": "'all', 'cpu', 'gpu', 'ram', 'disk', 'battery'. Default: all",
            "required": False,
        },
    },
    function=_system_info,
    category="system",
    capabilities=['system_information', 'hardware_specs', 'os_metrics'],
    aliases=['tizim_info', 'kompyuter', 'specs', 'sysinfo'],
    risk_level=RiskLevel.LOW,
    timeout=5.0,
    idempotent=True,
    destructive=False,
)


# --- 25. WINDOW MANAGER (Oynalar) ---
def _window_manager(
    action: str = "list", window: str = "", width: int = 0, height: int = 0
) -> dict:
    """Oynalarni boshqarish"""
    try:
        import ctypes
        from ctypes import wintypes

        EnumWindows = ctypes.windll.user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
        )
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible

        windows = []

        def callback(hwnd, _):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buff, length + 1)
                    windows.append(buff.value)
            return True

        if action == "list":
            EnumWindows(EnumWindowsProc(callback), 0)
            visible = [w for w in windows if w][:20]
            return {"windows": visible, "message": f"{len(visible)} ta oyna"}
        elif action == "minimize":
            hwnd = ctypes.windll.user32.FindWindowW(None, window)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 6)
                return {"message": f"{window} kichraytirildi"}
            return {"error": f"'{window}' topilmadi"}
        elif action == "maximize":
            hwnd = ctypes.windll.user32.FindWindowW(None, window)
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 3)
                return {"message": f"{window} kattalashtirildi"}
            return {"error": f"'{window}' topilmadi"}
        elif action == "close":
            hwnd = ctypes.windll.user32.FindWindowW(None, window)
            if hwnd:
                ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)
                return {"message": f"{window} yopildi"}
            return {"error": f"'{window}' topilmadi"}
        elif action == "resize":
            hwnd = ctypes.windll.user32.FindWindowW(None, window)
            if hwnd:
                ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, width, height, 0x0040)
                return {"message": f"{window} o'lchami {width}x{height}"}
            return {"error": f"'{window}' topilmadi"}
        else:
            return {
                "error": "action: 'list', 'minimize', 'maximize', 'close', 'resize'"
            }
    except ImportError:
        return {"error": "ctypes/windll mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


TOOL_WINDOW_MANAGER = Tool(
    name="window_manager",
    description="Oynalar ro'yxatini ko'rish, kichraytirish, kattalashtirish, yopish, o'lchamini o'zgartirish",
    parameters={
        "action": {
            "type": "string",
            "description": "'list', 'minimize', 'maximize', 'close', 'resize'. Default: list",
            "required": False,
        },
        "window": {
            "type": "string",
            "description": "Oyna nomi (minimize/maximize/close/resize uchun)",
            "required": False,
        },
        "width": {
            "type": "integer",
            "description": "Eni pikselda (action='resize' uchun)",
            "required": False,
        },
        "height": {
            "type": "integer",
            "description": "Bo'yi pikselda (action='resize' uchun)",
            "required": False,
        },
    },
    function=_window_manager,
    category="system",
    capabilities=['window_management', 'window_focus', 'window_resize'],
    aliases=['oyna', 'window', 'deraza'],
    risk_level=RiskLevel.MEDIUM,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 26. NOTIFICATION (Eslatma) ---
def _notification(
    title: str = "Misa AI", message: str = "", duration: int = 5
) -> dict:
    """Windows notification yuborish"""
    try:
        try:
            from plyer import notification

            notification.notify(title=title, message=message, timeout=duration)
            return {"message": f"Eslatma yuborildi: {title}"}
        except ImportError:
            import base64
            b64_title = base64.b64encode(str(title).encode("utf-8")).decode("ascii")
            b64_msg = base64.b64encode(str(message).encode("utf-8")).decode("ascii")
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
                "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                f"$tText = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_title}')); "
                f"$mText = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_msg}')); "
                "$template.GetElementsByTagName('text')[0].AppendChild($template.CreateTextNode($tText)); "
                "$template.GetElementsByTagName('text')[1].AppendChild($template.CreateTextNode($mText)); "
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Misa AI').Show([Windows.UI.Notifications.ToastNotification]::new($template))"
            )
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True)
            return {"message": f"Eslatma yuborildi: {title}"}
    except Exception as e:
        return {"error": str(e)}


TOOL_NOTIFICATION = Tool(
    name="notification",
    description="Windows notification (eslatma) yuborish",
    parameters={
        "title": {
            "type": "string",
            "description": "Eslatma sarlavhasi. Default: 'Misa AI'",
            "required": False,
        },
        "message": {"type": "string", "description": "Eslatma matni", "required": True},
        "duration": {
            "type": "integer",
            "description": "Davomiylik sekundda. Default: 5",
            "required": False,
        },
    },
    function=_notification,
    category="system",
    capabilities=['desktop_notification', 'toast_message', 'alert_user'],
    aliases=['bildirishnoma', 'toast', 'notify'],
    risk_level=RiskLevel.LOW,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


# --- 27. VECTOR SEARCH (Semantic xotira) ---
def _vector_search(
    action: str = "search", query: str = "", path: str = "", n_results: int = 5
) -> dict:
    """Semantic xotira — fayllarni vektor shaklida saqlash va qidirish"""
    try:
        from core.vector_memory import get_vector_memory

        vm = get_vector_memory()

        if not vm._client:
            return {"error": "ChromaDB ishlamayapti"}

        if action == "search":
            if not query:
                return {"error": "So'rov (query) kerak"}
            results = vm.search(query, n_results=n_results)
            if not results:
                return {"message": "Hech narsa topilmadi", "results": []}

            formatted = []
            for r in results:
                formatted.append(
                    {
                        "text": r["text"][:300] + "..."
                        if len(r.get("text", "")) > 300
                        else r.get("text", ""),
                        "source": r.get("metadata", {}).get("source", "Noma'lum"),
                        "relevance": f"{r.get('relevance', 0) * 100:.0f}%",
                    }
                )
            return {"results": formatted, "count": len(formatted)}

        elif action == "add":
            if not path:
                return {"error": "Fayl yo'li (path) kerak"}
            if not os.path.exists(path):
                return {"error": f"Fayl topilmadi: {path}"}

            success = vm.add_file(path)
            if success:
                return {"message": f"Fayl qo'shildi: {os.path.basename(path)}"}
            return {"error": "Fayl qo'shilmadi"}

        elif action == "scan":
            if not path:
                return {"error": "Papka yo'li (path) kerak"}
            if not os.path.exists(path):
                return {"error": f"Papka topilmadi: {path}"}

            count = 0
            supported = (
                ".txt",
                ".md",
                ".py",
                ".js",
                ".html",
                ".css",
                ".json",
                ".yaml",
                ".yml",
                ".xml",
                ".pdf",
                ".docx",
            )
            for root, _, files in os.walk(path):
                for f in files:
                    if f.endswith(supported):
                        full_path = os.path.join(root, f)
                        try:
                            if vm.add_file(full_path):
                                count += 1
                        except Exception:
                            pass
            return {
                "message": f"{count} ta fayl vektor bazasiga qo'shildi",
                "count": count,
            }

        elif action == "count":
            return {
                "count": vm.count(),
                "message": f"Vektor bazada {vm.count()} ta hujjat",
            }

        else:
            return {"error": "action: 'search', 'add', 'scan', 'count'"}

    except ImportError:
        return {"error": "vector_memory mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


def _sandbox_execute(code: str = "", timeout: int = 10) -> dict:
    """Python kodni xavfsiz sandbox muhitida bajarish"""
    if not code:
        return {"error": "Kod (code) parametri kerak"}
    try:
        from core.sandbox import execute_safe

        result = execute_safe(code, timeout)
        if result.get("error"):
            return {"error": result["error"]}
        output = result.get("output", "").strip()
        if not output:
            output = "(Hech qanday natija yo'q)"
        return {"output": output, "success": True}
    except ImportError:
        return {"error": "sandbox mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


TOOL_SANDBOX = Tool(
    name="sandbox_execute_python",
    description="Python kodni xavfsiz izolatsiyalangan muhitda bajarish. Natijani konsolga chiqaradi. Har qanday foydali Python kodi uchun ishlatilsin.",
    parameters={
        "code": {
            "type": "string",
            "description": "Bajariladigan Python kod. print() orqali natija chiqaring.",
            "required": True,
        },
        "timeout": {
            "type": "integer",
            "description": "Vaqt chegarasi (soniyada). Default: 10",
            "required": False,
        },
    },
    function=_sandbox_execute,
    category="utility",
    capabilities=['python_execution', 'code_sandbox', 'isolated_run'],
    aliases=['python', 'sandbox', 'kod'],
    risk_level=RiskLevel.MEDIUM,
    timeout=15.0,
    idempotent=True,
    destructive=False,
)


def _secret_vault(action: str = "get", key: str = "", value: str = "") -> dict:
    """Maxfiy ma'lumotlarni boshqarish ( SecureVault )"""
    try:
        from core.secure_vault import get_secret, set_secret, is_vault_unlocked

        if not is_vault_unlocked():
            return {
                "error": "Vault qulflangan. Master parol kiritilishi kerak.",
                "locked": True,
            }

        if action == "get":
            if not key:
                return {"error": "key parametri kerak"}
            secret = get_secret(key)
            if secret is None:
                return {"error": f"'{key}' topilmadi"}
            return {"key": key, "value": secret}
        elif action == "set":
            if not key or not value:
                return {"error": "key va value parametrlari kerak"}
            set_secret(key, value)
            return {"message": f"'{key}' saqlandi"}
        else:
            return {"error": "action: 'get' yoki 'set'"}
    except ImportError:
        return {"error": "secure_vault mavjud emas"}
    except Exception as e:
        return {"error": str(e)}


TOOL_SECRET_VAULT = Tool(
    name="secret_vault",
    description="Maxfiy ma'lumotlarni olish yoki saqlash (API kalitlari, parollar). Vault qulflangan bo'lsa xato qaytaradi.",
    parameters={
        "action": {
            "type": "string",
            "description": "'get' (olish) yoki 'set' (saqlash)",
            "required": True,
        },
        "key": {
            "type": "string",
            "description": "Maxfiy ma'lumot nomi (kalit)",
            "required": True,
        },
        "value": {
            "type": "string",
            "description": "Saqlanadigan qiymat (action='set' uchun)",
            "required": False,
        },
    },
    function=_secret_vault,
    category="utility",
    capabilities=['credential_vault', 'secret_storage', 'api_key_storage'],
    aliases=['vault', 'maxfiy', 'kalit'],
    risk_level=RiskLevel.HIGH,
    timeout=5.0,
    idempotent=False,
    destructive=False,
)


TOOL_VECTOR_SEARCH = Tool(
    name="vector_search",
    description="Semantic xotira — fayllarni vektor bazasiga saqlash va ma'noga qarab qidirish",
    parameters={
        "action": {
            "type": "string",
            "description": "'search' (qidirish), 'add' (fayl qo'shish), 'scan' (papkani skanerlash), 'count' (sonini ko'rish). Default: search",
            "required": False,
        },
        "query": {
            "type": "string",
            "description": "Qidiruv so'rovi (action='search' uchun)",
            "required": False,
        },
        "path": {
            "type": "string",
            "description": "Fayl yoki papka yo'li (action='add' yoki 'scan' uchun)",
            "required": False,
        },
        "n_results": {
            "type": "integer",
            "description": "Qancha natija ko'rsatish. Default: 5",
            "required": False,
        },
    },
    function=_vector_search,
    category="knowledge",
    capabilities=['vector_search', 'semantic_memory', 'embedding_search'],
    aliases=['vektor', 'semantic', 'vector_memory'],
    risk_level=RiskLevel.LOW,
    timeout=10.0,
    idempotent=True,
    destructive=False,
)


# ========================================================
# GLOBAL REGISTRY — Barcha tool'lar
# ========================================================


def create_default_registry() -> ToolRegistry:
    """Standart tool'lar bilan registry yaratish"""
    registry = ToolRegistry()
    # Asosiy tool'lar (v2)
    registry.register(TOOL_WEB_SEARCH)
    registry.register(TOOL_CALCULATOR)
    registry.register(TOOL_SYSTEM)
    registry.register(TOOL_MUSIC)
    registry.register(TOOL_WEATHER)
    registry.register(TOOL_REMINDER)
    registry.register(TOOL_FILE)
    registry.register(TOOL_KNOWLEDGE)
    registry.register(TOOL_DATETIME)
    # Yangi tool'lar (v3)
    registry.register(TOOL_SCHEDULER)
    registry.register(TOOL_RAG)
    registry.register(TOOL_CURRENCY)
    registry.register(TOOL_TRANSLATOR)
    registry.register(TOOL_SCREEN)
    # Yangi tool'lar (v3.1 — Autonomous Agent)
    registry.register(TOOL_FILE_WRITE)
    registry.register(TOOL_APP_CHECK)
    registry.register(TOOL_ASK_USER)
    # Vision + Input tool'lar (v3.2 — Desktop Agent)
    registry.register(TOOL_SCREEN_CLICK)
    registry.register(TOOL_KEYBOARD_TYPE)
    registry.register(TOOL_KEYBOARD_SHORTCUT)
    # Yangi system tool'lar (v3.3)
    registry.register(TOOL_CLIPBOARD)
    registry.register(TOOL_PROCESS_MANAGER)
    registry.register(TOOL_AUDIO_CONTROL)
    registry.register(TOOL_SYSTEM_INFO)
    registry.register(TOOL_WINDOW_MANAGER)
    registry.register(TOOL_NOTIFICATION)
    # Yangi knowledge tool'lar (v3.4 — Vector Memory)
    registry.register(TOOL_VECTOR_SEARCH)
    # Yangi utility tool'lar (v3.5 — Sandbox + SecureVault)
    registry.register(TOOL_SANDBOX)
    registry.register(TOOL_SECRET_VAULT)
    logger.info(f"Tool Registry: {registry.count} ta tool ro'yxatdan o'tdi")
    return registry


# Global registry singleton
_registry = None


def get_registry() -> ToolRegistry:
    """Global registry olish"""
    global _registry
    if _registry is None:
        _registry = create_default_registry()
    return _registry


# Alias
get_tool_registry = get_registry
