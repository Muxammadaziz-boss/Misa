# ========== agent_memory.py ==========
# Agent uzoq muddatli xotira tizimi
# Suhbat tarixi + Foydalanuvchi profili + Bilimlar bazasi

import os
import json
import logging
import datetime
from collections import deque
from threading import RLock
from typing import Optional, List, Dict, Any

from core.intelligence.memory_types import (
    MemoryItem,
    MemoryType,
    MemorySource,
    MemoryConfidence,
)
from core.intelligence.memory_policy import MemoryPolicy
from core.intelligence.memory_retriever import MemoryRetriever

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Loyiha ildizi


class AgentMemory:
    """Agent xotirasi — 3 darajali:

    1. Qisqa muddatli (RAM) — joriy suhbat konteksti
    2. O'rta muddatli (fayl) — suhbat tarixi
    3. Uzoq muddatli (fayl) — foydalanuvchi profili va bilimlar
    """

    def __init__(self, max_short_term=20, max_conversations=100):
        self._lock = RLock()

        # Qisqa muddatli xotira (RAM)
        self._short_term = deque(maxlen=max_short_term)

        # Fayl yo'llari
        self._conversations_file = os.path.join(
            BASE_DIR, "data", "agent_conversations.json"
        )
        self._profile_file = os.path.join(BASE_DIR, "data", "agent_profile.json")
        self._knowledge_file = os.path.join(BASE_DIR, "data", "agent_knowledge.json")

        self._max_conversations = max_conversations

        # Yuklash
        self._profile = self._load_json(
            self._profile_file,
            {
                "ism": "",
                "ovoz_turi": "erkak",
                "til": "uz",
                "qiziqishlar": [],
                "yoqtirgan_platformalar": [],
                "yaratilgan": datetime.datetime.now().isoformat(),
            },
        )
        self._knowledge = self._load_json(self._knowledge_file, {})
        self._conversations = self._load_json(self._conversations_file, [])

        logger.info(
            f"AgentMemory yuklandi: {len(self._conversations)} suhbat, {len(self._knowledge)} bilim"
        )

    # ========== QISQA MUDDATLI XOTIRA ==========

    def add_to_context(self, role: str, content: str):
        """Joriy suhbatga xabar qo'shish"""
        with self._lock:
            self._short_term.append(
                {
                    "role": role,
                    "content": content,
                    "time": datetime.datetime.now().isoformat(),
                }
            )

    def get_context(self, last_n: int = 10) -> list:
        """Joriy suhbat kontekstini olish"""
        with self._lock:
            items = list(self._short_term)
            return items[-last_n:]

    def clear_context(self):
        """Joriy suhbatni tozalash"""
        with self._lock:
            self._short_term.clear()

    # ========== SUHBAT TARIXI ==========

    def add_conversation(self, user_input: str, agent_response: str):
        """Suhbatni tarixga qo'shish"""
        should_save = False
        with self._lock:
            self._conversations.append(
                {
                    "user": user_input,
                    "agent": agent_response,
                    "time": datetime.datetime.now().isoformat(),
                }
            )

            # Cheklanishdan oshsa eski suhbatlarni o'chirish
            while len(self._conversations) > self._max_conversations:
                self._conversations.pop(0)

            # Har 5 ta suhbatda faylga saqlash (flag)
            if len(self._conversations) % 5 == 0:
                should_save = True

        # Fayl I/O — lock tashqarisida (boshqa threadlar bloklanmaydi)
        if should_save:
            self._save_conversations()

    def get_conversations(self, last_n: int = 20) -> list:
        """Oxirgi N ta suhbat"""
        with self._lock:
            return self._conversations[-last_n:]

    def search_conversations(self, query: str, limit: int = 5) -> list:
        """Suhbatlardan qidirish"""
        with self._lock:
            query_lower = query.lower()
            results = []
            for conv in reversed(self._conversations):
                if (
                    query_lower in conv["user"].lower()
                    or query_lower in conv["agent"].lower()
                ):
                    results.append(conv)
                    if len(results) >= limit:
                        break
            return results

    def get_history_for_ai(self, last_n: int = 6) -> list:
        """AI uchun suhbat tarixi formatda"""
        conversations = self.get_conversations(last_n)
        history = []
        for conv in conversations:
            history.append({"role": "user", "content": conv["user"]})
            history.append({"role": "assistant", "content": conv["agent"]})
        return history

    def clear_conversations(self):
        """Barcha suhbatlar tarixini tozalash"""
        with self._lock:
            self._conversations.clear()
            self._save_conversations()

    # ========== FOYDALANUVCHI PROFILI ==========

    def set_profile(self, key: str, value):
        """Profil ma'lumotini o'zgartirish"""
        with self._lock:
            self._profile[key] = value
            self._save_json(self._profile_file, self._profile)
            logger.debug(f"Profil yangilandi: {key} = {value}")

    def get_profile(self, key: str = None, default=None):
        """Profil ma'lumotini olish"""
        with self._lock:
            if key:
                return self._profile.get(key, default)
            return self._profile.copy()

    # ========== BILIMLAR BAZASI ==========

    def save_knowledge(
        self,
        key: str,
        value: str = "",
        memory_type: Optional[MemoryType] = None,
        source: MemorySource = MemorySource.USER,
        confidence: float = 1.0,
        importance: float = 0.5,
        pinned: bool = False,
        category: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        """Yangi bilim saqlash (MemoryPolicy xavfsizlik, maxfiylik va deduplikatsiya bilan)"""
        if content is not None and not value:
            value = content
        if category and memory_type is None:
            cat_lower = str(category).lower()
            if "work" in cat_lower:
                memory_type = MemoryType.WORK_CONTEXT
            elif "pref" in cat_lower:
                memory_type = MemoryType.PREFERENCE
            elif "task" in cat_lower:
                memory_type = MemoryType.TASK
            elif "note" in cat_lower:
                memory_type = MemoryType.NOTE
            else:
                memory_type = MemoryType.FACT

        with self._lock:
            decision = MemoryPolicy.evaluate_write(
                key=key,
                content=value,
                source=source,
                memory_type=memory_type,
                existing_knowledge=self._knowledge,
            )

            if not decision.allowed:
                logger.warning(
                    f"Bilim saqlash rad etildi: key='{key}', sabab='{decision.reason}'"
                )
                try:
                    from core.intelligence.observability import get_observability_manager
                    get_observability_manager().metrics.record_write_rejection(decision.reason)
                except Exception:
                    pass
                return False

            if memory_type is None:
                memory_type = MemoryPolicy.classify_type(key, decision.sanitized_content)

            # Duplikat bo'lsa: mavjud xotirani yangilaymiz
            if decision.is_duplicate and decision.existing_key:
                target_key = decision.existing_key
                if target_key in self._knowledge:
                    existing = self._knowledge[target_key]
                    if isinstance(existing, dict):
                        existing["access_count"] = existing.get("access_count", 0) + 1
                        existing["updated_at"] = datetime.datetime.now().isoformat()
                        if pinned:
                            existing["pinned"] = True
                        self._save_json(self._knowledge_file, self._knowledge)
                        return True

            # Yangi xotira yaratish
            item = MemoryItem(
                key=key,
                content=decision.sanitized_content,
                type=memory_type if isinstance(memory_type, MemoryType) else MemoryType(memory_type),
                source=source if isinstance(source, MemorySource) else MemorySource(source),
                importance=importance,
                confidence=confidence,
                pinned=pinned,
            )

            # Ziddiyatli xotiralar tekshiruvi va yangilanishi
            existing_items = self.get_memory_items()
            MemoryPolicy.resolve_conflict(item, existing_items)
            for ex in existing_items:
                if ex.key in self._knowledge and not ex.is_active():
                    self._knowledge[ex.key]["superseded_by"] = ex.superseded_by

            self._knowledge[key] = item.to_dict()
            self._save_json(self._knowledge_file, self._knowledge)
            logger.debug(f"Bilim saqlandi ({item.type.value}): {key} = {decision.sanitized_content}")
            return True

    def update_knowledge_item(
        self,
        item_id_or_key: str,
        key: Optional[str] = None,
        content: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        importance: Optional[float] = None,
        pinned: Optional[bool] = None,
    ) -> Optional[MemoryItem]:
        """Mavjud xotira elementini xavfsiz tahrirlash (ID yoki kalit bo'yicha)"""
        with self._lock:
            target_key = None
            existing_dict = None

            if item_id_or_key in self._knowledge:
                target_key = item_id_or_key
                existing_dict = self._knowledge[target_key]
            else:
                for k, v in self._knowledge.items():
                    if isinstance(v, dict) and v.get("id") == item_id_or_key:
                        target_key = k
                        existing_dict = v
                        break

            if not target_key or not existing_dict:
                logger.warning(f"Tahrirlash uchun xotira topilmadi: {item_id_or_key}")
                return None

            current_item = MemoryItem.from_dict(target_key, existing_dict)

            new_key = key.strip() if key is not None and key.strip() else current_item.key
            new_content = content.strip() if content is not None else current_item.content
            new_type = memory_type if memory_type is not None else current_item.type
            if isinstance(new_type, str):
                try:
                    new_type = MemoryType(new_type)
                except ValueError:
                    new_type = current_item.type
            new_importance = float(importance) if importance is not None else current_item.importance
            new_pinned = bool(pinned) if pinned is not None else current_item.pinned

            # Xavfsizlik va MemoryPolicy tekshiruvi
            decision = MemoryPolicy.evaluate_write(
                key=new_key,
                content=new_content,
                source=current_item.source,
                memory_type=new_type,
            )

            if not decision.allowed:
                logger.warning(f"Xotirani tahrirlash rad etildi: {decision.reason} ({new_key})")
                try:
                    from core.intelligence.observability import get_observability_manager
                    get_observability_manager().metrics.record_write_rejection(decision.reason)
                except Exception:
                    pass
                return None

            if new_key != target_key:
                del self._knowledge[target_key]

            updated_item = MemoryItem(
                id=current_item.id,
                key=new_key,
                content=decision.sanitized_content,
                type=new_type,
                source=current_item.source,
                importance=new_importance,
                confidence=current_item.confidence,
                created_at=current_item.created_at,
                updated_at=datetime.datetime.now().isoformat(),
                last_used_at=current_item.last_used_at,
                access_count=current_item.access_count,
                superseded_by=current_item.superseded_by,
                pinned=new_pinned,
                metadata=current_item.metadata,
            )

            self._knowledge[new_key] = updated_item.to_dict()
            self._save_json(self._knowledge_file, self._knowledge)
            logger.info(f"Xotira tahrirlandi: id='{updated_item.id}', key='{new_key}'")
            return updated_item

    def delete_knowledge_item(self, item_id_or_key: str) -> bool:
        """Xotirani ID yoki kalit bo'yicha xavfsiz o'chirish"""
        with self._lock:
            target_key = None
            if item_id_or_key in self._knowledge:
                target_key = item_id_or_key
            else:
                for k, v in self._knowledge.items():
                    if isinstance(v, dict) and v.get("id") == item_id_or_key:
                        target_key = k
                        break

            if target_key and target_key in self._knowledge:
                del self._knowledge[target_key]
                self._save_json(self._knowledge_file, self._knowledge)
                try:
                    from core.intelligence.observability import get_observability_manager
                    get_observability_manager().metrics.record_deletion()
                except Exception:
                    pass
                logger.info(f"Xotira o'chirildi: key='{target_key}'")
                return True

            logger.warning(f"O'chirish uchun xotira topilmadi: {item_id_or_key}")
            return False

    def pin_knowledge_item(self, item_id_or_key: str, pinned: bool = True) -> bool:
        """Xotirani qadash (pin) yoki qadoqdan chiqarish"""
        with self._lock:
            target_key = None
            if item_id_or_key in self._knowledge:
                target_key = item_id_or_key
            else:
                for k, v in self._knowledge.items():
                    if isinstance(v, dict) and v.get("id") == item_id_or_key:
                        target_key = k
                        break

            if target_key and target_key in self._knowledge:
                val = self._knowledge[target_key]
                if isinstance(val, dict):
                    val["pinned"] = pinned
                    val["updated_at"] = datetime.datetime.now().isoformat()
                    self._save_json(self._knowledge_file, self._knowledge)
                    logger.info(f"Xotira qadalishi o'zgardi: key='{target_key}', pinned={pinned}")
                    return True

            return False

    def get_memory_item_by_id(self, item_id_or_key: str) -> Optional[MemoryItem]:
        """ID yoki kalit bo'yicha MemoryItem obyektini olish"""
        with self._lock:
            if item_id_or_key in self._knowledge:
                return MemoryItem.from_dict(item_id_or_key, self._knowledge[item_id_or_key])
            for k, v in self._knowledge.items():
                if isinstance(v, dict) and v.get("id") == item_id_or_key:
                    return MemoryItem.from_dict(k, v)
            return None

    def get_memory_items(self) -> List[MemoryItem]:
        """Barcha bilimlarni normalizatsiya qilingan MemoryItem ro'yxati sifatida olish"""
        with self._lock:
            items = []
            for k, v in self._knowledge.items():
                try:
                    items.append(MemoryItem.from_dict(k, v))
                except Exception as e:
                    logger.warning(f"MemoryItem yaratishda xatolik ({k}): {e}")
            return items

    def retrieve_relevant(
        self,
        query: str,
        limit: int = 6,
        task_entities: Optional[List[str]] = None,
    ) -> List[MemoryItem]:
        """So'rov bo'yicha eng mos xotiralarni saralab qaytarish"""
        with self._lock:
            items = self.get_memory_items()
            retrieved = MemoryRetriever.retrieve(
                query=query,
                items=items,
                limit=limit,
                task_entities=task_entities,
            )
            for item in retrieved:
                if item.key in self._knowledge and isinstance(self._knowledge[item.key], dict):
                    self._knowledge[item.key]["access_count"] = item.access_count
                    self._knowledge[item.key]["last_used_at"] = item.last_used_at
            return retrieved

    def get_knowledge(self, key: str = None) -> dict:
        """Bilim olish"""
        with self._lock:
            if key:
                if key in self._knowledge:
                    self._knowledge[key]["access_count"] += 1
                    return self._knowledge[key]
                return None
            return self._knowledge.copy()

    def get_knowledge_summary(self) -> str:
        """AI prompt uchun bilimlar xulosasi"""
        with self._lock:
            if not self._knowledge:
                return ""

            lines = []
            for key, data in self._knowledge.items():
                lines.append(f"- {key}: {data['value']}")
            return "\n".join(lines)

    def delete_knowledge(self, key: str) -> bool:
        """Bilimni o'chirish (orqaga qaytuvchanlik)"""
        return self.delete_knowledge_item(key)

    def clear_knowledge(self):
        """Barcha saqlangan bilimlarni tozalash"""
        with self._lock:
            self._knowledge.clear()
            self._save_json(self._knowledge_file, self._knowledge)

    @property
    def knowledge(self) -> List[MemoryItem]:
        """Barcha bilimlarni MemoryItem ro'yxati sifatida olish"""
        return self.get_memory_items()

    @property
    def knowledge_file(self) -> str:
        """agent_knowledge.json fayl yo'li"""
        return self._knowledge_file

    def add_knowledge(
        self,
        key: str,
        content: str,
        category: str = "general",
        confidence: float = 1.0,
        pinned: bool = False,
    ) -> bool:
        """save_knowledge uchun qulay alias"""
        return self.save_knowledge(
            key=key,
            content=content,
            category=category,
            confidence=confidence,
            pinned=pinned,
        )

    # ========== STATISTIKA ==========

    @property
    def stats(self) -> dict:
        """Xotira statistikasi"""
        with self._lock:
            items = self.get_memory_items()
            return {
                "kontekst_hajmi": len(self._short_term),
                "suhbatlar_soni": len(self._conversations),
                "bilimlar_soni": len(self._knowledge),
                "faol_bilimlar_soni": sum(1 for m in items if m.is_active()),
                "pinned_bilimlar_soni": sum(1 for m in items if getattr(m, "pinned", False)),
                "profil_toliq": bool(self._profile.get("ism")),
            }

    # ========== ICHKI FUNKSIYALAR ==========

    def _load_json(self, path: str, default):
        """JSON faylni yuklash"""
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"JSON yuklash xatolik ({path}): {e}")
        return default

    def _save_json(self, path: str, data):
        """JSON faylga xavfsiz va atomik saqlash (Windows-safe fallback bilan)"""
        temp_path = f"{path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            try:
                os.replace(temp_path, path)
            except OSError:
                # Windows fallback: agar os.replace vaqtincha bloklangan bo'lsa
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"JSON saqlash xatolik ({path}): {e}")

    def _save_conversations(self):
        """Suhbatlarni faylga saqlash"""
        self._save_json(self._conversations_file, self._conversations)

    def save_all(self):
        """Barchasini faylga saqlash"""
        with self._lock:
            self._save_conversations()
            self._save_json(self._profile_file, self._profile)
            self._save_json(self._knowledge_file, self._knowledge)
            logger.info("AgentMemory: barcha ma'lumotlar saqlandi")


# Global singleton
_memory = None


def get_memory() -> AgentMemory:
    """Global AgentMemory olish (singleton — duplikat yaratmaydi)"""
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory
