# -*- coding: utf-8 -*-
"""
Misa AI — Multi-Turn Voice Conversation Session Manager
Ko'p bosqichli suhbat konteksti va 'Follow-up' (ketma-ket savol berish) oynasi boshqaruvi.
Foydalanuvchi har bir savol boshida "Misa" deyishi shart emas:
Misa gapirib bo'lgach 7 soniya davomida keyingi savolni to'g'ridan-to'g'ri tinglaydi.
"""

import time
import uuid
import logging
import threading
from typing import Dict, Any, List, Optional

logger = logging.getLogger("VoiceSessionManager")


class ConversationSession:
    """
    Yagona ovozli suhbat sessiyasi.
    """

    def __init__(self, follow_up_window: float = 7.0):
        self.session_id: str = f"v_sess_{uuid.uuid4().hex[:10]}"
        self.conversation_id: str = f"v_conv_{uuid.uuid4().hex[:8]}"
        self.follow_up_window = follow_up_window  # soniyada

        self.history: List[Dict[str, str]] = []
        self.active_turn: int = 0
        self.last_user_message: str = ""
        self.last_assistant_message: str = ""
        self.last_speech_completed_time: float = 0.0

        self._in_follow_up: bool = False
        self._lock = threading.Lock()

    def reset_session(self) -> None:
        """Sessiyani butunlay yangilash"""
        with self._lock:
            self.session_id = f"v_sess_{uuid.uuid4().hex[:10]}"
            self.conversation_id = f"v_conv_{uuid.uuid4().hex[:8]}"
            self.history.clear()
            self.active_turn = 0
            self.last_user_message = ""
            self.last_assistant_message = ""
            self.last_speech_completed_time = 0.0
            self._in_follow_up = False

    def on_wake_word_activated(self) -> None:
        """'Misa' aytilganda yangi bosqichni boshlash"""
        with self._lock:
            self._in_follow_up = False

    def on_assistant_finished_speaking(self) -> None:
        """Yordamchi gapirib bo'ldi — 7 soniyalik Follow-up oynasini ochish"""
        with self._lock:
            self.last_speech_completed_time = time.time()
            self._in_follow_up = True
            logger.info(f"SessionManager: Follow-up oynasi ochildi ({self.follow_up_window}s davomida 'Misa'siz tinglaydi)")

    def is_in_follow_up_window(self) -> bool:
        """Hozir follow-up oynasidamizmi?"""
        with self._lock:
            if not self._in_follow_up:
                return False
            elapsed = time.time() - self.last_speech_completed_time
            if elapsed <= self.follow_up_window:
                return True
            self._in_follow_up = False
            return False

    def close_follow_up(self) -> None:
        """Follow-up oynasini yopish (kutish vaqti tugadi yoki mavzu yakunlandi)"""
        with self._lock:
            self._in_follow_up = False

    def record_turn(self, user_text: str, assistant_text: str) -> None:
        """
        Navbatdagi suhbat bosqichini xotiraga saqlash.
        Tizimning barcha agent va xotira modullariga kontekstni uzatadi.
        """
        with self._lock:
            self.active_turn += 1
            self.last_user_message = user_text
            self.last_assistant_message = assistant_text
            self.history.append({
                "role": "user",
                "content": user_text,
                "turn": self.active_turn,
                "timestamp": time.time()
            })
            self.history.append({
                "role": "assistant",
                "content": assistant_text,
                "turn": self.active_turn,
                "timestamp": time.time()
            })
            # Xotirani 12 ta so'nggi xabarda ushlash
            if len(self.history) > 24:
                self.history = self.history[-24:]

        # Asosiy Agent xotirasiga ham yozish (agar mavjud bo'lsa)
        self._sync_to_agent_memory(user_text, assistant_text)

    def _sync_to_agent_memory(self, user_text: str, assistant_text: str) -> None:
        """Barcha qismlar (ReAct Agent, Chat) uchun yagona xotiraga integratsiya qilish"""
        try:
            import main
            if hasattr(main, "_agent_memory") and main._agent_memory:
                main._agent_memory.add_user_message(user_text)
                main._agent_memory.add_assistant_message(assistant_text)
        except Exception as e:
            logger.debug(f"Agent memory sync xatosi: {e}")

    def get_context_for_prompt(self, max_turns: int = 4) -> str:
        """AI uchun oldingi suhbat qisqacha kontekstini tayyorlash"""
        with self._lock:
            recent = self.history[-(max_turns * 2):]
            if not recent:
                return ""
            lines = []
            for item in recent:
                prefix = "Foydalanuvchi: " if item["role"] == "user" else "Misa: "
                lines.append(f"{prefix}{item['content']}")
            return "\n".join(lines)


# Global yagona nusxa
_session_manager_instance: Optional[ConversationSession] = None


def get_session_manager() -> ConversationSession:
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = ConversationSession()
    return _session_manager_instance
