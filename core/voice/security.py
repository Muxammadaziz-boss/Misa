# -*- coding: utf-8 -*-
"""
Misa AI — Voice Command Security & Destructive Action Guard
Xavfli buyruqlar (kompyuterni o'chirish, qayta ishga tushirish, fayllarni o'chirish)
uchun ovozli tasdiqlash (Confirmation Gate) talab qilish moduli.
Tasodifiy fon ovozlari yoki noto'g'ri eshitishlar natijasida tizimga zarar yetishining oldini oladi.
"""

import re
import time
import logging
from typing import Optional, Tuple, Callable, Any, Dict

logger = logging.getLogger("VoiceSecurity")

DANGEROUS_PATTERNS = [
    (r"\b(?:kompyuter(?:ni)?\s+(?:o['']?chir|ochir)|tizimni\s+o['']?chir|shutdown)\b", "kompyuterni o'chirish"),
    (r"\b(?:qayta\s+ishga\s+tushir|restart|reboot)\b", "kompyuterni qayta ishga tushirish"),
    (r"\b(?:(?:fayl|fayllar|barcha\s+fayllar|hamma\s+fayllar).*?o['']?chir|format(?:lash)?|o['']?chirib\s+tashla|delete\s+all)\b", "fayllarni o'chirish"),
    (r"\b(?:jarayon(?:ni)?\s+to['']?xtat|process\s+kill|kill\s+process)\b", "tizim jarayonini majburiy to'xtatish"),
]

AFFIRMATIVE_RESPONSES = {"ha", "tasdiqlayman", "albatta", "mayli", "bajar", "ha albatta", "ha tasdiqlayman"}
NEGATIVE_RESPONSES = {"yo'q", "yoq", "kerakmas", "bekor", "to'xtat", "bekor qil"}


class VoiceSecurityGuard:
    """Ovoz orqali xavfli amallarni tasdiqlash boshqaruvchisi"""

    def __init__(self, confirmation_timeout: float = 18.0):
        self.confirmation_timeout = confirmation_timeout
        self._pending_action: Optional[Dict[str, Any]] = None

    def has_pending_action(self) -> bool:
        """Tasdiqlash kutilayotgan amal bormi?"""
        if not self._pending_action:
            return False
        if time.time() - self._pending_action["timestamp"] > self.confirmation_timeout:
            self._pending_action = None
            return False
        return True

    def check_for_destructive_intent(self, command_text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Buyruq xavfli ekanligini tekshirish.
        Qaytaradi: (xavflimi, amal_tavsifi, foydalanuvchiga_savol)
        """
        if not command_text:
            return False, None, None

        cmd_lower = command_text.lower().strip()
        for pattern, desc in DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower):
                prompt = f"{desc.capitalize()}ni tasdiqlaysizmi? Tasdiqlash uchun 'Ha' yoki 'Tasdiqlayman' deng."
                return True, desc, prompt

        return False, None, None

    def stage_pending_action(self, action_desc: str, callback: Callable[[], Any], params: Any = None) -> None:
        """Tasdiqlash uchun amalni saqlab qo'yish"""
        self._pending_action = {
            "desc": action_desc,
            "callback": callback,
            "params": params,
            "timestamp": time.time()
        }
        logger.warning(f"VoiceSecurity: Xavfli amal tasdiqlash uchun kutish rejimiga olindi: {action_desc}")

    def evaluate_confirmation(self, user_response: str) -> Tuple[bool, str, Optional[Any]]:
        """
        Foydalanuvchi javobini tekshirish ('Ha' yoki 'Yo'q').
        Qaytaradi: (bajarildimi, xabar_matni, natija)
        """
        if not self.has_pending_action():
            return False, "", None

        resp_clean = re.sub(r"[^\w\s']", "", user_response.lower()).strip()
        action = self._pending_action
        self._pending_action = None

        if resp_clean in AFFIRMATIVE_RESPONSES or any(w in AFFIRMATIVE_RESPONSES for w in resp_clean.split()):
            logger.info(f"VoiceSecurity: Amal tasdiqlandi: {action['desc']}")
            try:
                res = action["callback"]() if action["params"] is None else action["callback"](action["params"])
                return True, f"{action['desc'].capitalize()} amalga oshirilmoqda.", res
            except Exception as e:
                logger.error(f"Xavfli amalni bajarishda xatolik: {e}")
                return False, f"Xatolik yuz berdi: {e}", None
        else:
            logger.info(f"VoiceSecurity: Amal bekor qilindi: {action['desc']}")
            return False, f"{action['desc'].capitalize()} bekor qilindi.", None


# Global nusxa
_security_guard_instance: Optional[VoiceSecurityGuard] = None


def get_security_guard() -> VoiceSecurityGuard:
    global _security_guard_instance
    if _security_guard_instance is None:
        _security_guard_instance = VoiceSecurityGuard()
    return _security_guard_instance
