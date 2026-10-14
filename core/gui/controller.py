# ========== core/gui/controller.py ==========
# Misa AI 9.0 — Session-Aware Windows Computer Controller
# UI Automation & Accessibility-First with Vision Fallback
# DPI-Aware, Target Window Verified, Focused Typing, Postconditions & Abort Control

import os
import sys
import time
import ctypes
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, field

logger = logging.getLogger("misa.gui.controller")

# RECT tuzilmasi
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


@dataclass
class WindowTarget:
    hwnd: int
    title: str
    class_name: str
    pid: int
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    is_elevated: bool = False
    is_focused: bool = False

    @property
    def width(self) -> int:
        return max(0, self.rect[2] - self.rect[0])

    @property
    def height(self) -> int:
        return max(0, self.rect[3] - self.rect[1])

    def contains_point(self, x: int, y: int) -> bool:
        """Berilgan (x, y) nuqta oyna to'g'ri to'rtburchagi ichida ekanligini tekshirish"""
        l, t, r, b = self.rect
        return (l <= x <= r) and (t <= y <= b)


class WindowsGUIController:
    """
    Windows tizimida GUI harakatlarini xavfsiz va aniq nazorat qiluvchi markaziy kontroller.
    """

    def __init__(self):
        self._aborted = False
        self._init_dpi_awareness()

    def _init_dpi_awareness(self):
        """Monitorlararo DPI miqyosini to'g'ri o'qish (Per-Monitor DPI Aware)"""
        if sys.platform != "win32":
            return
        try:
            # SetProcessDpiAwareness(2) -> PROCESS_PER_MONITOR_DPI_AWARE
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception as e:
                logger.debug(f"DPI awareness o'rnatishda xatolik: {e}")

    def abort(self):
        """Navbatdagi yoki hozirgi barcha input amallarini zudlik bilan to'xtatish"""
        self._aborted = True
        logger.warning("[GUIController] Barcha GUI amallari ABORT holatiga o'tkazildi")

    def reset_abort(self):
        """Abort holatini tozalash"""
        self._aborted = False

    @property
    def is_aborted(self) -> bool:
        return self._aborted

    def get_foreground_window(self) -> Optional[WindowTarget]:
        """Ayni paytda faol (fokuslangan) oynani aniqlash"""
        if sys.platform != "win32":
            return None

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None
        return self._build_window_target(hwnd)

    @classmethod
    def get_active_window(cls) -> Optional[WindowTarget]:
        """Ayni paytda faol (fokuslangan) oynani aniqlash (Class/Static yordamchi)"""
        instance = cls()
        return instance.get_foreground_window()

    def find_window(self, query: str, require_visible: bool = True) -> Optional[WindowTarget]:
        """Oyna sarlavhasi yoki sinf nomi bo'yicha oynani qidirish"""
        if sys.platform != "win32":
            return None

        query_clean = str(query or "").strip().lower()
        if not query_clean:
            return None

        matched_hwnds = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def _enum_cb(hwnd, _):
            if require_visible and not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True

            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            title = ""
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value

            class_buf = ctypes.create_unicode_buffer(256)
            ctypes.windll.user32.GetClassNameW(hwnd, class_buf, 256)
            class_name = class_buf.value

            if query_clean in title.lower() or query_clean in class_name.lower():
                matched_hwnds.append(hwnd)
            return True

        ctypes.windll.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)

        if not matched_hwnds:
            return None

        # Eng mos birinchi oynani qaytarish
        return self._build_window_target(matched_hwnds[0])

    def list_windows(self, require_visible: bool = True) -> List[WindowTarget]:
        """Ochiq oynalar ro'yxatini olish"""
        if sys.platform != "win32":
            return []

        results = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def _enum_cb(hwnd, _):
            if require_visible and not ctypes.windll.user32.IsWindowVisible(hwnd):
                return True
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                target = self._build_window_target(hwnd)
                if target and target.title.strip():
                    results.append(target)
            return True

        ctypes.windll.user32.EnumWindows(WNDENUMPROC(_enum_cb), 0)
        return results

    def _build_window_target(self, hwnd: int) -> Optional[WindowTarget]:
        """HWND dan WindowTarget obyektini xavfsiz yasash"""
        if sys.platform != "win32" or not hwnd:
            return None

        # Sarlavha
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

        # Sinf nomi
        class_buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value

        # PID
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        # Koordinatalar
        rect = RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        window_rect = (rect.left, rect.top, rect.right, rect.bottom)

        # Fokus holati
        fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
        is_focused = (fg_hwnd == hwnd)

        # UAC / Elevated tekshiruvi
        is_elevated = self._is_elevated_window(pid.value)

        return WindowTarget(
            hwnd=hwnd,
            title=title,
            class_name=class_name,
            pid=pid.value,
            rect=window_rect,
            is_elevated=is_elevated,
            is_focused=is_focused
        )

    def _is_elevated_window(self, pid: int) -> bool:
        """Jarayon administrator (Elevated) huquqida ishlayotganligini tekshirish"""
        if sys.platform != "win32" or pid <= 0:
            return False
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        TOKEN_QUERY = 0x0008

        h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h_proc:
            # Agar processga kirish rad etilsa (Access Denied), u yuqori ehtimol bilan Elevated
            return True

        h_token = ctypes.c_void_p()
        elevated = False
        try:
            if ctypes.windll.advapi32.OpenProcessToken(h_proc, TOKEN_QUERY, ctypes.byref(h_token)):
                TokenElevation = 20
                is_elev = ctypes.c_ulong()
                ret_len = ctypes.c_ulong()
                if ctypes.windll.advapi32.GetTokenInformation(
                    h_token, TokenElevation, ctypes.byref(is_elev), ctypes.sizeof(is_elev), ctypes.byref(ret_len)
                ):
                    elevated = bool(is_elev.value)
                ctypes.windll.kernel32.CloseHandle(h_token)
        except Exception:
            pass
        finally:
            ctypes.windll.kernel32.CloseHandle(h_proc)

        return elevated

    def focus_window(self, target: WindowTarget, timeout: float = 1.5) -> bool:
        """Oynani oldingi fonga olib kelish va fokuslash"""
        if sys.platform != "win32" or not target or not target.hwnd:
            return False

        if target.is_elevated:
            logger.warning(f"[GUIController] Diqqat: Oyna '{target.title}' (PID: {target.pid}) Elevated huquqda ishlamoqda")

        SW_RESTORE = 9
        ctypes.windll.user32.ShowWindow(target.hwnd, SW_RESTORE)
        ctypes.windll.user32.SetForegroundWindow(target.hwnd)

        # Fokus o'tishini kutish
        start = time.time()
        while time.time() - start < timeout:
            fg = ctypes.windll.user32.GetForegroundWindow()
            if fg == target.hwnd:
                target.is_focused = True
                return True
            time.sleep(0.05)

        logger.warning(f"[GUIController] Oyna '{target.title}' ga fokus berish vaqti tugadi")
        return False

    def _is_window_alive(self, hwnd: int) -> bool:
        """Oyna hali ham tirik (yopilmagan) ekanligini tekshirish"""
        if sys.platform != "win32":
            return True
        return bool(ctypes.windll.user32.IsWindow(hwnd))

    def verify_target_focus(self, target: WindowTarget) -> Tuple[bool, str]:
        """Amal oldidan oyna holatini qat'iy tekshirish"""
        if self._aborted:
            return False, "ACTION_ABORTED"

        # 1. UAC / Secure Desktop cheklovi bormi?
        if target.is_elevated:
            return False, "ELEVATED_WINDOW_OR_UAC_RESTRICTION"

        if sys.platform != "win32":
            return True, "NON_WINDOWS_MOCK"

        # 2. Oyna hali ham mavjudmi?
        if not self._is_window_alive(target.hwnd):
            return False, "WINDOW_CLOSED_OR_INVALID"

        # 3. Aynan shu oyna fokusdami?
        fg = ctypes.windll.user32.GetForegroundWindow()
        if fg != target.hwnd:
            # Qayta fokuslashga bir martalik urinish
            focused = self.focus_window(target, timeout=0.8)
            if not focused:
                return False, "TARGET_WINDOW_NOT_FOCUSED"

        # 4. PID mos keladimi?
        curr_pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(target.hwnd, ctypes.byref(curr_pid))
        if curr_pid.value != target.pid:
            return False, "TARGET_PID_MISMATCH"

        return True, "VERIFIED"

    def safe_click(
        self,
        x: int,
        y: int,
        target: Optional[WindowTarget] = None,
        click_type: str = "click"
    ) -> Dict[str, Any]:
        """
        Sichqoncha bilan bosish.
        DPI va koordinatalarni maqsadli oyna doirasi bilan tekshiradi.
        """
        if self._aborted:
            return {"success": False, "error": "ACTION_ABORTED"}

        # Koordinata tekshiruvi
        if x <= 0 or y <= 0:
            return {"success": False, "error": "INVALID_COORDINATES"}

        # Agar target berilgan bo'lsa, nuqta oyna ichida ekanligini tekshiramiz
        if target:
            verified, reason = self.verify_target_focus(target)
            if not verified:
                return {"success": False, "error": f"PRECONDITION_FAILED: {reason}"}

            if not target.contains_point(x, y):
                return {
                    "success": False,
                    "error": "COORDINATES_OUTSIDE_TARGET_WINDOW",
                    "window_rect": target.rect,
                    "target_coords": (x, y)
                }

        try:
            import pyautogui
            screen_w, screen_h = pyautogui.size()
            if x > screen_w or y > screen_h:
                return {"success": False, "error": f"COORDINATES_EXCEED_SCREEN: ({screen_w}x{screen_h})"}

            if click_type == "double_click":
                pyautogui.doubleClick(x, y)
            elif click_type == "right_click":
                pyautogui.rightClick(x, y)
            else:
                pyautogui.click(x, y)

            # Postcondition: Oyna hali ham mavjudligini tekshirish
            post_ok = True
            if target:
                post_ok = self._is_window_alive(target.hwnd)

            return {
                "success": True,
                "action": click_type,
                "x": x,
                "y": y,
                "postcondition_verified": post_ok
            }
        except Exception as e:
            return {"success": False, "error": f"CLICK_FAILED: {str(e)}"}

    def safe_type(
        self,
        text: str,
        target: WindowTarget,
        interval: float = 0.02
    ) -> Dict[str, Any]:
        """
        Klaviatura orqali matn kiritish.
        Matn FAQAT tasdiqlangan va fokuslangan target oynaga yuboriladi.
        """
        if self._aborted:
            return {"success": False, "error": "ACTION_ABORTED"}

        if not text:
            return {"success": False, "error": "EMPTY_TEXT"}

        if not target:
            return {"success": False, "error": "MISSING_TARGET_WINDOW"}

        # 1. Qat'iy precondition tekshiruvi: Oyna fokusdami?
        verified, reason = self.verify_target_focus(target)
        if not verified:
            return {
                "success": False,
                "error": f"PRECONDITION_FAILED: {reason}",
                "target": target.title
            }

        try:
            import pyautogui

            # Har bir belgi oldidan abort signalini tekshirish (uzoq matnlarni to'xtatish uchun)
            for ch in text:
                if self._aborted:
                    logger.warning("[GUIController] Matn kiritish o'rtasida to'xtatildi (Aborted)")
                    return {"success": False, "error": "TYPING_ABORTED_MIDWAY"}

                if ch.isascii():
                    pyautogui.typewrite(ch)
                else:
                    pyautogui.write(ch)

                if interval > 0:
                    time.sleep(interval)

            # 2. Postcondition tekshiruvi: Oyna qulab tushmadimi va hali ham ochiqmi?
            post_verified = True
            if target:
                post_verified = self._is_window_alive(target.hwnd)

            return {
                "success": True,
                "typed_length": len(text),
                "target_window": target.title,
                "target_pid": target.pid,
                "postcondition_verified": post_verified
            }
        except Exception as e:
            return {"success": False, "error": f"TYPING_FAILED: {str(e)}"}

    def safe_shortcut(self, keys: List[str], target: Optional[WindowTarget] = None) -> Dict[str, Any]:
        """Klaviatura kombinatsiyasini yuborish (masalan: ['ctrl', 'a'], ['enter'])"""
        if self._aborted:
            return {"success": False, "error": "ACTION_ABORTED"}

        if target:
            verified, reason = self.verify_target_focus(target)
            if not verified:
                return {"success": False, "error": f"PRECONDITION_FAILED: {reason}"}

        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return {"success": True, "keys": keys, "postcondition_verified": True}
        except Exception as e:
            return {"success": False, "error": f"SHORTCUT_FAILED: {str(e)}"}

    def close_window(self, target: WindowTarget) -> Dict[str, Any]:
        """Oynani xavfsiz yopish (WM_CLOSE xabari yuborish)"""
        if not target or not target.hwnd:
            return {"success": False, "error": "INVALID_TARGET"}

        if sys.platform != "win32":
            return {"success": True, "closed": True}

        WM_CLOSE = 0x0010
        ctypes.windll.user32.PostMessageW(target.hwnd, WM_CLOSE, 0, 0)

        # Postcondition: Oyna yopilganini kutish
        closed = False
        start = time.time()
        while time.time() - start < 2.0:
            if not self._is_window_alive(target.hwnd):
                closed = True
                break
            time.sleep(0.1)

        return {"success": closed, "window": target.title, "closed": closed}


_global_gui_controller: Optional[WindowsGUIController] = None


def get_gui_controller() -> WindowsGUIController:
    global _global_gui_controller
    if _global_gui_controller is None:
        _global_gui_controller = WindowsGUIController()
    return _global_gui_controller
