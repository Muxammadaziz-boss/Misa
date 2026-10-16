# ========== core/gui/window_events.py ==========
# Misa AI 9.0 — Windows Event Hook & Window Change Observer
# Listens to EVENT_SYSTEM_FOREGROUND and Window State Changes with Polling Fallback

import sys
import time
import ctypes
import logging
import threading
from typing import Callable, Optional, List, Dict, Any

logger = logging.getLogger("misa.gui.window_events")

# WinEvent konstantalari
EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000


class WindowEventObserver:
    """
    Windows tizimida faol oyna o'zgarishlarini (Foreground Window Changes)
    WinEvent hook orqali yoki polling fallback yordamida kuzatuvchi servis.
    """

    def __init__(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self._callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._hook_handle = None
        self._last_hwnd = 0
        self._lock = threading.Lock()

    def set_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self._callback = callback

    def start(self):
        """Kuzatuvni ishga tushirish"""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_observer, daemon=True, name="window_event_observer")
            self._thread.start()
            logger.info("[WindowEventObserver] Oyna hodisalarini kuzatish boshlandi")

    def stop(self):
        """Kuzatuvni to'xtatish"""
        with self._lock:
            self._running = False
            if self._hook_handle and sys.platform == "win32":
                try:
                    ctypes.windll.user32.UnhookWinEvent(self._hook_handle)
                except Exception as e:
                    logger.debug(f"Unhook error: {e}")
                self._hook_handle = None

            if self._thread and self._thread.is_alive():
                # Thread daemon bo'lgani uchun o'zi tugaydi
                self._thread = None
            logger.info("[WindowEventObserver] Oyna hodisalarini kuzatish to'xtatildi")

    def _run_observer(self):
        """Asosiy sikl: WinEvent Hook yoki Polling Fallback"""
        if sys.platform != "win32":
            self._polling_loop()
            return

        # Windowsda WinEventHook o'rnatishga urinish
        hook_installed = False
        try:
            WINEVENTPROC = ctypes.WINFUNCTYPE(
                None,
                ctypes.c_void_p,  # hWinEventHook
                ctypes.c_ulong,   # event
                ctypes.c_void_p,  # hwnd
                ctypes.c_long,    # idObject
                ctypes.c_long,    # idChild
                ctypes.c_ulong,   # dwEventThread
                ctypes.c_ulong    # dwmsEventTime
            )

            def _event_handler(hHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
                if event == EVENT_SYSTEM_FOREGROUND and hwnd:
                    self._on_window_changed(int(hwnd))

            self._win_event_proc = WINEVENTPROC(_event_handler)
            self._hook_handle = ctypes.windll.user32.SetWinEventHook(
                EVENT_SYSTEM_FOREGROUND,
                EVENT_SYSTEM_FOREGROUND,
                0,
                self._win_event_proc,
                0,
                0,
                WINEVENT_OUTOFCONTEXT
            )
            if self._hook_handle:
                hook_installed = True
                logger.info("[WindowEventObserver] WinEventHook muvaffaqiyatli o'rnatildi ✓")
        except Exception as e:
            logger.warning(f"[WindowEventObserver] WinEventHook o'rnatib bo'lmadi: {e}, Polling rejimiga o'tiladi")

        if hook_installed:
            # Win32 Message Loop
            msg = ctypes.wintypes.MSG() if hasattr(ctypes, "wintypes") else None
            while self._running:
                # Polling fallback orqali xavfsizlikni kafolatlaymiz
                self._check_active_window()
                time.sleep(0.3)
        else:
            self._polling_loop()

    def _polling_loop(self):
        """Zaxira polling sikli (300ms)"""
        while self._running:
            self._check_active_window()
            time.sleep(0.3)

    def _check_active_window(self):
        if sys.platform != "win32":
            return
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd and hwnd != self._last_hwnd:
            self._on_window_changed(hwnd)

    def _on_window_changed(self, hwnd: int):
        self._last_hwnd = hwnd
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        data = {
            "hwnd": hwnd,
            "title": title,
            "pid": pid.value,
            "timestamp": time.time()
        }

        if self._callback:
            try:
                self._callback(data)
            except Exception as e:
                logger.debug(f"Callback xatolik: {e}")
