# -*- coding: utf-8 -*-
"""
Misa AI — Voice Cancellation Token
Ko'p tarmoqli (thread-safe) to'xtatish va bekor qilish mexanizmi.
Audio ijrosi, LLM javob generatsiyasi va TTS sintezini tezkor (<100ms) bekor qilish uchun.
"""

import threading
from typing import Callable, List


class CancellationToken:
    """
    Oqimlararo xavfsiz bekor qilish tokeni.
    "To'xta" komandasi yoki yangi kiruvchi so'rov kelganda barcha davom etayotgan
    audio jarayonlarini bir zumda to'xtatadi.
    """

    def __init__(self):
        self._cancelled_event = threading.Event()
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Bekor qilish signalini yuborish va barcha callbacklarni chaqirish"""
        with self._lock:
            if self._cancelled_event.is_set():
                return
            self._cancelled_event.set()
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb()
            except Exception:
                pass

    @property
    def is_cancelled(self) -> bool:
        """Token bekor qilinganmi?"""
        return self._cancelled_event.is_set()

    def reset(self) -> None:
        """Tokenni dastlabki faol holatga qaytarish"""
        self._cancelled_event.clear()
        with self._lock:
            self._callbacks.clear()

    def add_callback(self, cb: Callable[[], None]) -> None:
        """Bekor qilish vaqtida ishga tushadigan tinglovchi qo'shish"""
        with self._lock:
            if self.is_cancelled:
                try:
                    cb()
                except Exception:
                    pass
            else:
                self._callbacks.append(cb)

    def register_callback(self, cb: Callable[[], None]) -> None:
        """add_callback uchun qulay muqobil (alias)"""
        self.add_callback(cb)
