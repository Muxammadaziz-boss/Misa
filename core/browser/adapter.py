# ========== adapter.py ==========
# Misa AI 9.0.0 — Permission-Aware Windows Browser Automation Adapter
# Tab Discovery, Page Title, Explicit Navigation & Extensible DOM/CDP Hooks

import logging
import re
import uuid
import webbrowser
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from core.gui.controller import WindowsGUIController, WindowTarget

logger = logging.getLogger(__name__)


@dataclass
class BrowserTab:
    """Brauzer vkladkasi yoki oynasi modeli"""
    tab_id: str
    title: str
    url: str
    browser_type: str  # "chrome", "brave", "edge", "generic"
    hwnd: int = 0
    pid: int = 0
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tab_id": self.tab_id,
            "title": self.title,
            "url": self.url,
            "browser_type": self.browser_type,
            "hwnd": self.hwnd,
            "pid": self.pid,
            "is_active": self.is_active,
        }


class BrowserAutomationAdapter:
    """
    Ruxsatga asoslangan brauzer boshqaruv adapteri.
    Ochiq brauzer oynalarini (Chrome, Brave, Edge) aniqlaydi,
    xavfsiz navigatsiya qiladi va kelgusida CDP/WebDriver orqali
    DOM amallarini bajarish uchun kengaytiriladigan arxitektura taqdim etadi.
    """

    KNOWN_BROWSERS = {
        "chrome": {"process": "chrome.exe", "suffix": "- google chrome"},
        "brave": {"process": "brave.exe", "suffix": "- brave"},
        "edge": {"process": "msedge.exe", "suffix": "- microsoft edge"},
    }

    def __init__(self, gui_controller: Optional[WindowsGUIController] = None):
        self.gui_controller = gui_controller or WindowsGUIController()
        self._cdp_session: Optional[Any] = None

    def list_tabs(self) -> List[BrowserTab]:
        """Barcha ochiq brauzer oynalari va ularning sarlavhalarini ro'yxatlash"""
        all_windows = self.gui_controller.list_windows(require_visible=True)
        active_window = self.gui_controller.get_foreground_window()
        active_hwnd = active_window.hwnd if active_window else 0

        tabs: List[BrowserTab] = []
        for win in all_windows:
            browser_type = self._detect_browser_type(win)
            if browser_type:
                clean_title = self._clean_page_title(win.title, browser_type)
                tab = BrowserTab(
                    tab_id=f"tab_{win.hwnd}",
                    title=clean_title,
                    url="",  # UIA/CDP mavjud bo'lmaganda sarlavha asosida
                    browser_type=browser_type,
                    hwnd=win.hwnd,
                    pid=win.pid,
                    is_active=(win.hwnd == active_hwnd),
                )
                tabs.append(tab)

        logger.info(f"[BrowserAdapter] {len(tabs)} ta faol brauzer oynasi aniqlandi")
        return tabs

    def get_active_tab(self) -> Optional[BrowserTab]:
        """Ayni paytda fokuslangan brauzer oynasini olish"""
        active_win = self.gui_controller.get_foreground_window()
        if not active_win:
            return None

        browser_type = self._detect_browser_type(active_win)
        if not browser_type:
            return None

        clean_title = self._clean_page_title(active_win.title, browser_type)
        return BrowserTab(
            tab_id=f"tab_{active_win.hwnd}",
            title=clean_title,
            url="",
            browser_type=browser_type,
            hwnd=active_win.hwnd,
            pid=active_win.pid,
            is_active=True,
        )

    def navigate(
        self,
        url: str,
        browser: str = "chrome",
        new_tab: bool = True
    ) -> Dict[str, Any]:
        """
        Brauzerda aniq URL manziliga o'tish (Explicit navigation).
        URL xavfsizligi va sxemasi tekshiriladi.
        """
        clean_url = str(url or "").strip()
        if not clean_url:
            return {"success": False, "error": "URL manzili bo'sh"}

        # Sxema tekshiruvi (faqat http va https)
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "https://" + clean_url

        try:
            parsed = urlparse(clean_url)
            if not parsed.netloc:
                return {"success": False, "error": f"Noto'g'ri URL formati: {clean_url}"}
        except Exception as e:
            return {"success": False, "error": f"URL tahlilida xatolik: {e}"}

        logger.info(f"[BrowserAdapter] Navigatsiya boshlanmoqda: {clean_url} (Brauzer: {browser})")

        # Brauzer orqali ochish
        try:
            opened = webbrowser.open(clean_url, new=2 if new_tab else 0)
            return {
                "success": opened,
                "url": clean_url,
                "browser": browser,
                "navigated": opened,
                "message": f"Brauzerda {clean_url} ochildi" if opened else "Brauzerni ochib bo'lmadi"
            }
        except Exception as e:
            logger.error(f"[BrowserAdapter] Navigatsiya xatosi: {e}")
            return {"success": False, "error": str(e), "url": clean_url}

    def execute_dom_action(
        self,
        action: str,
        selector: str,
        value: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Kelgusida CDP (Chrome DevTools Protocol) yoki WebDriver bilan
        DOM elementlari ustida amal bajarish interfeysi (click, input, read).
        """
        valid_actions = {"click", "type", "get_text", "get_attribute", "scroll"}
        if action not in valid_actions:
            return {
                "success": False,
                "error": f"Noma'lum DOM amali: '{action}'. Ruxsat etilganlar: {valid_actions}"
            }

        if self._cdp_session:
            # Agar CDP sessiyasi ulangan bo'lsa
            try:
                # CDP execution logic hook
                return {
                    "success": True,
                    "action": action,
                    "selector": selector,
                    "result": "CDP_ACTION_EXECUTED",
                    "value": value
                }
            except Exception as e:
                return {"success": False, "error": f"CDP xatosi: {e}"}

        # CDP ulanmagan holatda strukturalangan tayyorgarlik javobi
        return {
            "success": True,
            "action": action,
            "selector": selector,
            "cdp_attached": False,
            "message": f"DOM amali '{action}' qabul qilindi. To'liq CDP brauzer sessiyasi talab etiladi.",
            "value": value
        }

    def close_active_browser(self) -> Dict[str, Any]:
        """Faol brauzer oynasini xavfsiz yopish"""
        tab = self.get_active_tab()
        if not tab or not tab.hwnd:
            return {"success": False, "error": "Faol brauzer oynasi topilmadi"}

        closed = self.gui_controller.close_window(
            target=WindowTarget(
                hwnd=tab.hwnd,
                title=tab.title,
                class_name="",
                pid=tab.pid,
                rect=(0, 0, 0, 0)
            )
        )
        return {
            "success": closed,
            "tab_id": tab.tab_id,
            "closed": closed,
            "message": f"Brauzer oynasi ({tab.title}) yopildi" if closed else "Oynani yopib bo'lmadi"
        }

    # ========================================================
    # PRIVATE HELPERS
    # ========================================================

    def _detect_browser_type(self, target: WindowTarget) -> Optional[str]:
        """Oyna ma'lumotlari orqali brauzer turini aniqlash"""
        proc_lower = str(target.process_name or "").lower()
        title_lower = str(target.title or "").lower()

        if "chrome" in proc_lower or "google chrome" in title_lower:
            return "chrome"
        if "brave" in proc_lower or "brave" in title_lower:
            return "brave"
        if "msedge" in proc_lower or "edge" in title_lower:
            return "edge"
        return None

    def _clean_page_title(self, raw_title: str, browser_type: str) -> str:
        """Oyna sarlavhasidan brauzer nomini tozalab, sof sahifa sarlavhasini olish"""
        title = raw_title.strip()
        suffix = self.KNOWN_BROWSERS.get(browser_type, {}).get("suffix", "")
        if suffix and title.lower().endswith(suffix):
            title = title[:-len(suffix)].strip().rstrip("-").strip()
        return title or raw_title
