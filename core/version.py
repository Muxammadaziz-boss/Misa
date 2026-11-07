# -*- coding: utf-8 -*-
"""
Misa AI — Central Canonical Version Definition (Single Source of Truth)
Barcha modullar, API server, Desktop UI va agentlar uchun yagona haqiqat manbai.
"""

APP_VERSION = "9.4.0"
APP_VERSION_NAME = "v9.4"
APP_NAME = "Misa AI"
APP_RELEASE_DATE = "2026-11-06"
APP_CODENAME = "Universal Intelligence Hub & Clean UX"

def get_version_info() -> dict:
    return {
        "version": APP_VERSION,
        "version_name": APP_VERSION_NAME,
        "app": APP_NAME,
        "release_date": APP_RELEASE_DATE,
        "codename": APP_CODENAME,
    }
