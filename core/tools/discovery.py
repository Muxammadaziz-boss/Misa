# ========== discovery.py ==========
# Misa AI 7.x — Capability Registry & Discovery Engine
# Indexing Tools by Semantic Capabilities, Aliases & Heuristics

import re
import logging
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Common natural language keywords to semantic capability mapping (Uzbek & English)
CAPABILITY_KEYWORD_PATTERNS: Dict[str, List[str]] = {
    "calculation": [
        "hisobla", "hisob", "qancha", "necha", "ko'paytir", "bo'l", "qo'sh", "ayir",
        "calculate", "calc", "math", "sum", "multiply", "divide", "add", "subtract"
    ],
    "weather": [
        "ob-havo", "obhavo", "havo", "harorat", "yomg'ir", "qor", "quyosh",
        "weather", "forecast", "temperature", "rain", "sunny"
    ],
    "currency": [
        "valyuta", "kurs", "dollar", "yevro", "som", "so'm", "rubl",
        "currency", "exchange", "rate", "usd", "eur", "rub"
    ],
    "system_information": [
        "tizim", "kompyuter", "protsessor", "ram", "xotira", "disk", "gpu", "cpu", "specs",
        "system", "specs", "hardware", "os", "disk_space"
    ],
    "web_search": [
        "qidir", "internet", "google", "veb", "top", "sayt", "manba",
        "search", "web", "internet", "find", "lookup"
    ],
    "datetime": [
        "vaqt", "soat", "bugun", "kecha", "ertaga", "sana", "oy", "yil",
        "time", "clock", "date", "today", "tomorrow", "now"
    ],
    "reminder": [
        "eslat", "eslatma", "eslatib qo'y", "budilnik",
        "remind", "reminder", "alarm"
    ],
    "scheduler": [
        "jadval", "reja", "har kuni", "vazifa rejalashtir",
        "schedule", "scheduler", "cron", "recurring"
    ],
    "translation": [
        "tarjima", "inglizchaga", "o'zbekchaga", "ruschaga", "ma'nosi",
        "translate", "translation", "translator"
    ],
    "file_read": [
        "faylni o'qi", "fayl och", "matnni o'qi", "fayllar",
        "read file", "open file", "list files", "file reader"
    ],
    "file_write": [
        "faylga yoz", "fayl yarat", "saqla", "fayl saqlash",
        "write file", "save file", "create file"
    ],
    "app_detection": [
        "dastur", "o'rnatilgan", "ilova", "programma", "app",
        "application", "installed apps", "software"
    ],
    "clipboard": [
        "bufer", "nusxa", "clipboard", "copy", "paste"
    ],
    "audio_playback": [
        "musiqa", "qo'shiq", "mp3", "ijro", "music", "play music", "song"
    ],
    "system_power": [
        "o'chir", "o'chirish", "qayta yukla", "shutdown", "restart", "power off"
    ],
    "process_management": [
        "jarayon", "task manager", "process", "kill process"
    ],
    "ui_design": [
        "andoza", "andozalar", "andoza yarat", "dizayn", "ui", "ux", "maket", "shablon",
        "veb dizayn", "landing page", "interfeys", "stitch", "ekran yarat", "frontend",
        "design", "template", "wireframe", "prototype", "screen", "veb sahifa"
    ],
}


class CapabilityRegistry:
    """
    Qobiliyatlarni indekslash va qidirish registri.
    Vositalarni qobiliyatlar (capabilities) va taxalluslar (aliases) bo'yicha indekslaydi.
    """

    def __init__(self):
        self._capability_index: Dict[str, Set[str]] = {}
        self._alias_index: Dict[str, str] = {}
        self._tool_capabilities: Dict[str, Set[str]] = {}

    def register_tool(self, tool_name: str, capabilities: List[str], aliases: Optional[List[str]] = None):
        """Asbobning barcha qobiliyatlari va taxalluslarini ro'yxatdan o'tkazish"""
        name_clean = tool_name.lower().strip()
        caps = set(c.lower().strip() for c in (capabilities or []))

        # Asbob nomi ham birlamchi qobiliyat hisoblanadi
        caps.add(name_clean)

        self._tool_capabilities[name_clean] = caps

        for cap in caps:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(name_clean)

        # Taxalluslar
        for alias in (aliases or []):
            alias_clean = alias.lower().strip()
            self._alias_index[alias_clean] = name_clean

    def unregister_tool(self, tool_name: str):
        """Asbobni indeksdan olib tashlash"""
        name_clean = tool_name.lower().strip()
        caps = self._tool_capabilities.pop(name_clean, set())

        for cap in caps:
            if cap in self._capability_index:
                self._capability_index[cap].discard(name_clean)
                if not self._capability_index[cap]:
                    del self._capability_index[cap]

        # Aliaslarni tozalash
        aliases_to_remove = [k for k, v in self._alias_index.items() if v == name_clean]
        for a in aliases_to_remove:
            del self._alias_index[a]

    def find_by_capability(self, capability: str) -> List[str]:
        """Berilgan qobiliyatga ega barcha asboblar nomini qaytarish"""
        cap_clean = capability.lower().strip()
        if cap_clean in self._capability_index:
            return sorted(list(self._capability_index[cap_clean]))
        
        # Qisman moslik qidirish (masalan, "calc" -> "calculation")
        matches = set()
        for c, tools in self._capability_index.items():
            if cap_clean in c or c in cap_clean:
                matches.update(tools)
        return sorted(list(matches))

    def find_by_alias(self, alias: str) -> Optional[str]:
        """Taxallus orqali to'g'ridan-to'g'ri asbob nomini topish"""
        alias_clean = alias.lower().strip()
        return self._alias_index.get(alias_clean)

    def discover_capabilities_for_text(self, text: str) -> List[Tuple[str, float]]:
        """
        Matn (foydalanuvchi so'rovi yoki maqsad) asosida talab qilinayotgan qobiliyatlarni aniqlash.
        Qaytaradi: [(capability_name, confidence_score), ...]
        """
        if not text:
            return []

        text_lower = text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))
        results: List[Tuple[str, float]] = []

        # 1. To'g'ridan-to'g'ri indekslangan qobiliyatlarni tekshirish
        for cap in self._capability_index.keys():
            if cap in text_lower:
                results.append((cap, 1.0))

        # 2. Kalit so'z namunalari orqali aniqlash
        for cap, keywords in CAPABILITY_KEYWORD_PATTERNS.items():
            hit_count = sum(1 for kw in keywords if kw in text_lower or kw in words)
            if hit_count > 0:
                score = min(1.0, 0.6 + (hit_count * 0.2))
                # Agar ushbu qobiliyat allaqachon qo'shilgan bo'lsa, maksimal balni olamiz
                existing = [i for i, (c, _) in enumerate(results) if c == cap]
                if existing:
                    idx = existing[0]
                    results[idx] = (cap, max(results[idx][1], score))
                else:
                    results.append((cap, score))

        # Ballar bo'yicha kamayish tartibida saralash
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def list_all_capabilities(self) -> Dict[str, List[str]]:
        """Barcha qobiliyatlar va ularga tegishli asboblar ro'yxati"""
        return {cap: sorted(list(tools)) for cap, tools in self._capability_index.items()}

    def get_tool_capabilities(self, tool_name: str) -> List[str]:
        """Muayyan asbobning qobiliyatlari"""
        name_clean = tool_name.lower().strip()
        return sorted(list(self._tool_capabilities.get(name_clean, set())))
