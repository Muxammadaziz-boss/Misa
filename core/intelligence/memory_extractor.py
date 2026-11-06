# ========== memory_extractor.py ==========
# Misa AI v9.4.0 - Autonomous Semantic Memory Extractor
# Extracts meaningful user facts, preferences, work contexts, and notes
# from conversations automatically in the background.

import re
import logging
from typing import List, Dict, Any, Optional
from core.intelligence.memory_types import MemoryType, MemorySource, MemoryConfidence
from core.intelligence.memory_policy import MemoryPolicy

logger = logging.getLogger("misa.intelligence.memory_extractor")


class MemoryExtractor:
    """
    Suhbat matnidan avtonom tarzda foydalanuvchi ma'lumotlarini ajratib oluvchi
    va xotiraga (AgentMemory) yozuvchi modul.
    """

    # O'zbek, Rus va Ingliz tillaridagi aniq patternlar
    PATTERNS = [
        # Ism
        {
            "type": MemoryType.FACT,
            "category": "Shaxsiy",
            "key": "foydalanuvchi_ismi",
            "regexes": [
                r"(?:mening\s+ismim|ismim|otim)\s+([A-ZА-ЯЁA-Za-zʻʼ'\-]+)",
                r"(?:my\s+name\s+is|i\s+am)\s+([A-Za-zʻʼ'\-]+)",
                r"(?:меня\s+зовут|мое\s+имя)\s+([A-Za-zА-Яа-яЁёʻʼ'\-]+)",
            ],
            "importance": 0.95,
            "confidence": 0.95,
        },
        # Shahar / Yashash joyi
        {
            "type": MemoryType.FACT,
            "category": "Shaxsiy",
            "key": "foydalanuvchi_shahri",
            "regexes": [
                r"(?:men\s+)?([A-Za-zА-Яа-яЁёʻʼ'\-]+)(?:da|da\s+turaman|da\s+yashayman|danman)\b",
                r"(?:yashash\s+joyim|shahrim)\s+([A-Za-zА-Яа-яЁёʻʼ'\-]+)",
                r"i\s+live\s+in\s+([A-Za-zʻʼ'\-]+)",
                r"я\s+живу\s+в\s+([A-Za-zА-Яа-яЁёʻʼ'\-]+)",
            ],
            "importance": 0.85,
            "confidence": 0.90,
        },
        # Kasb / Mutaxassislik
        {
            "type": MemoryType.WORK_CONTEXT,
            "category": "Loyihalar",
            "key": "foydalanuvchi_kasbi",
            "regexes": [
                r"(?:men\s+)?([A-Za-zА-Яа-яЁё\s]{3,30}?)\s*(?:dasturchisiman|mutaxassisiman|muhandisiman|bo'lib\s+ishlayman|bo'lib\s+faoliyat\s+yuritaman)",
                r"(?:kasbim|mutaxassisligim)\s+([A-Za-zА-Яа-яЁё\s]{3,30})",
                r"i\s+work\s+as\s+(?:a\s+|an\s+)?([A-Za-z\s]{3,30})",
                r"я\s+работаю\s+([A-Za-zА-Яа-яЁё\s]{3,30})",
            ],
            "importance": 0.85,
            "confidence": 0.85,
        },
        # Faol Loyiha
        {
            "type": MemoryType.WORK_CONTEXT,
            "category": "Loyihalar",
            "key": "faol_loyiha",
            "regexes": [
                r"(?:mening\s+loyiham|loyihamiz|ustida\s+ishlayotgan\s+loyiham)\s*[:\-]?\s*([A-Za-z0-9А-Яа-яЁё_\-\.\s]{3,40})",
                r"my\s+project\s+is\s+([A-Za-z0-9_\-\.\s]{3,40})",
                r"(?:мой\s+проект|наш\s+проект)\s*[:\-]?\s*([A-Za-z0-9А-Яа-яЁё_\-\.\s]{3,40})",
            ],
            "importance": 0.90,
            "confidence": 0.85,
        },
        # Aniq Eslatma / Buyruq ("eslab qol: ...")
        {
            "type": MemoryType.NOTE,
            "category": "Boshqa",
            "key": "eslatma",
            "regexes": [
                r"(?:buni\s+eslab\s+qol|eslab\s+qol|xotirangda\s+saqla)\s*[:\-]?\s*(.+)",
                r"(?:remember\s+that|remember\s+this|remember)\s*[:\-]?\s*(.+)",
                r"(?:запомни|сохрани\s+в\s+памяти)\s*[:\-]?\s*(.+)",
            ],
            "importance": 0.95,
            "confidence": 1.0,
        },
        # Afzallik / Did (Preferences)
        {
            "type": MemoryType.PREFERENCE,
            "category": "Afzalliklar",
            "key": "afzallik",
            "regexes": [
                r"(?:menga\s+yoqadi|men\s+yoqtiraman|sevimli\s+tilim|sevimli\s+mavzum)\s*[:\-]?\s*([A-Za-z0-9А-Яа-яЁё_\-\s]{2,40})",
                r"i\s+prefer\s+([A-Za-z0-9_\-\s]{2,40})",
                r"(?:мне\s+нравится|я\s+предпочитаю)\s+([A-Za-z0-9А-Яа-яЁё_\-\s]{2,40})",
            ],
            "importance": 0.80,
            "confidence": 0.80,
        },
    ]

    @classmethod
    def extract_from_text(cls, text: str) -> List[Dict[str, Any]]:
        """
        Foydalanuvchi yozgan matndan aniq faktlarni ajratib oladi.
        """
        if not text or len(text.strip()) < 3:
            return []

        extracted = []
        cleaned = text.strip()

        for pat in cls.PATTERNS:
            for rgx in pat["regexes"]:
                match = re.search(rgx, cleaned, re.IGNORECASE)
                if match:
                    val = match.group(1).strip().strip(".,;:!?\"'")
                    if not val or len(val) < 2:
                        continue

                    # Ignored noisy common words
                    if val.lower() in {"nima", "qanday", "nega", "kim", "salom", "qayerda", "hello", "hi", "test"}:
                        continue

                    key = pat["key"]
                    if key in ("eslatma", "afzallik"):
                        slug = re.sub(r"[^a-z0-9]+", "_", val[:24].lower()).strip("_")
                        key = f"{key}_{slug}" if slug else key

                    extracted.append({
                        "key": key,
                        "content": val,
                        "type": pat["type"],
                        "category": pat["category"],
                        "importance": pat["importance"],
                        "confidence": pat["confidence"],
                        "source": MemorySource.CONVERSATION,
                    })
                    break  # Har bir pattern uchun birinchi moslik kifoya

        return extracted

    @classmethod
    def process_and_save(cls, memory_store, user_text: str, agent_response: str = "") -> List[str]:
        """
        Matndan faktlarni ajratib olib, xotiraga (AgentMemory) saqlaydi.
        Muvaffaqiyatli saqlangan kalitlar ro'yxatini qaytaradi.
        """
        candidates = cls.extract_from_text(user_text)
        if not candidates or not memory_store:
            return []

        saved_keys = []
        for cand in candidates:
            try:
                # Xavfsizlik va ruxsat tekshiruvi
                allowed = memory_store.save_knowledge(
                    key=cand["key"],
                    value=cand["content"],
                    memory_type=cand["type"],
                    source=cand["source"],
                    confidence=cand["confidence"],
                    importance=cand["importance"],
                    pinned=False,
                    category=cand["category"],
                )
                if allowed:
                    saved_keys.append(cand["key"])
                    logger.info(f"Yangi avtonom bilim saqlandi: {cand['key']} = '{cand['content']}'")
            except Exception as e:
                logger.warning(f"Bilimni saqlashda xatolik ({cand.get('key')}): {e}")

        return saved_keys
