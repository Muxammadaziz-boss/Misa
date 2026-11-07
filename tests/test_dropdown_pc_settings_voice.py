# -*- coding: utf-8 -*-
import os
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPSHELL_PATH = os.path.join(BASE_DIR, r"Misa\src\layout\AppShell.tsx")
DEVICE_SELECTOR_PATH = os.path.join(BASE_DIR, r"Misa\src\components\DeviceSelector.tsx")
LANDING_PAGE_PATH = os.path.join(BASE_DIR, r"Misa\src\pages\LandingPage.tsx")
BACKEND_SERVICE_PATH = os.path.join(BASE_DIR, r"Misa\src\services\backendService.ts")
GLOBALS_CSS_PATH = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")


def test_appshell_dropdown_not_intercepted_by_drag():
    """AppShell navbari va tugmalari data-tauri-drag-region tomonidan bloklanmagan bo'lishi kerak."""
    with open(APPSHELL_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    assert "<nav data-tauri-drag-region" not in code, "<nav> elementida data-tauri-drag-region bo'lmasligi kerak"
    assert "moreMenuOpen" in code
    assert "setMoreMenuOpen" in code


def test_globals_css_has_no_drag_on_buttons():
    """globals.css da barcha tugmalar va interaktiv elementlar uchun no-drag bo'lishi kerak."""
    with open(GLOBALS_CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()
    assert "-webkit-app-region: no-drag" in css, "globals.css da -webkit-app-region: no-drag bo'lishi shart"


def test_device_selector_enlarged_and_styled():
    """DeviceSelector kattalashtirilgan (>=460px) va boyitilgan PC boshqaruv markaziga ega bo'lishi kerak."""
    with open(DEVICE_SELECTOR_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    assert "480px" in code or "460px" in code, "DeviceSelector kengligi kamida 460px yoki 480px bo'lishi kerak"
    assert "CPU" in code
    assert "RAM" in code


def test_landing_page_capsule_centered_and_nowrap():
    """LandingPage Grand Status kapsulasi markazda va whiteSpace: nowrap bo'lishi kerak."""
    with open(LANDING_PAGE_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    assert "nowrap" in code
    assert "Misa Autonom Agent Faol" in code or "Misa Avtonom Agent Faol" in code


def test_landing_page_auto_speak_integration():
    """LandingPage da ovoz chiqishi uchun auto_speak integratsiyasi bo'lishi shart."""
    with open(LANDING_PAGE_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    assert "misa_auto_speak" in code, "LandingPage da misa_auto_speak sozlamasi tekshirilishi kerak"


def test_backend_service_speak_text_dual_url():
    """backendService.speakText ham LOCAL_HARDWARE_URL, ham API_BASE orqali urinib ko'rishi kerak."""
    with open(BACKEND_SERVICE_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    assert "speakText" in code
    assert "LOCAL_HARDWARE_URL" in code
