# -*- coding: utf-8 -*-
"""
Misa AI — RVC Model & Runtime On-Demand Installer Tests
Foydalanuvchi talabi bilan lokal AI modellarini yuklab olish,
'Yuklab olish zarur' statuslari va API integratsiyasini tekshirish.
"""

import os
import sys
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.voice.providers.rvc_installer import RVCInstaller, get_rvc_installer
from core.voice.providers.rvc_provider import RVCVoiceProvider
from core.voice.voice_registry import VoiceRegistry


def test_rvc_installer_status_needs_download():
    installer = RVCInstaller()
    status = installer.get_status()

    assert "installed" in status
    assert "needs_download" in status
    assert "status_label" in status
    assert "missing_components" in status

    # Lokal muhitda torch yoki hubert yo'q bo'lsa, 'Yuklab olish zarur' deb chiqishi kerak
    if not status["installed"]:
        assert status["needs_download"] is True
        assert status["status_label"] == "Yuklab olish zarur"
        assert status["badge"] == "Yuklab olish zarur"
        assert len(status["missing_components"]) > 0


def test_rvc_provider_returns_needs_download_badge():
    provider = RVCVoiceProvider()
    ashley_status = provider.get_voice_status("ashley")

    assert "status" in ashley_status
    if not ashley_status.get("runtime_ready"):
        assert ashley_status.get("needs_download") is True
        assert ashley_status.get("badge") == "Yuklab olish zarur"
        assert "Yuklab olish zarur" in ashley_status.get("reason", "")


def test_voice_registry_catalog_exposes_needs_download_badge():
    reg = VoiceRegistry()
    catalog = reg.get_catalog()

    ashley = next((v for v in catalog if v["id"] == "ashley"), None)
    yukari = next((v for v in catalog if v["id"] == "yukari"), None)

    assert ashley is not None
    assert yukari is not None

    # Hozirgi muhitda PyTorch/HuBERT yo'qligi sababli "Yuklab olish zarur" bo'lishi kerak
    if ashley["status"] == "needs_download":
        assert ashley["needs_download"] is True
        assert ashley["badge"] == "Yuklab olish zarur"

    if yukari["status"] == "needs_download":
        assert yukari["needs_download"] is True
        assert yukari["badge"] == "Yuklab olish zarur"


def test_installer_singleton_and_task_lifecycle():
    installer = get_rvc_installer()
    assert installer is not None
    status = installer.get_status()
    assert "task" in status
    assert status["task"]["state"] in ["idle", "downloading_hubert", "installing_packages", "completed", "error", "cancelled"]
