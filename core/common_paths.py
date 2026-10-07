# ========== core/common_paths.py ==========
# Misa AI 9.0.0 — Unified Path & Portable Storage Resolver
# Ensures all data, configs, memories and vaults are reliably saved
# across standalone portable distributions, dev environments, and restricted permissions.

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_RESOLVED_BASE_DIR: str = ""
_RESOLVED_DATA_DIR: str = ""


def get_base_dir() -> str:
    """Loyihaning haqiqiy asosiy (root) papkasini aniqlash."""
    global _RESOLVED_BASE_DIR
    if _RESOLVED_BASE_DIR:
        return _RESOLVED_BASE_DIR

    if getattr(sys, "frozen", False):
        # PyInstaller onedir: sys.executable odatda backend/misa_backend.exe yoki misa_backend.exe bo'ladi
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        # Agar backend ichida bo'lsa, bitta yuqoriga chiqamiz
        parent = os.path.dirname(exe_dir)
        if os.path.basename(exe_dir).lower() == "backend" and parent:
            _RESOLVED_BASE_DIR = parent
        else:
            _RESOLVED_BASE_DIR = exe_dir
    else:
        # Dev muhiti: core/ ning ota papkasi
        _RESOLVED_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return _RESOLVED_BASE_DIR


def get_data_dir() -> str:
    """
    Xavfsiz va ishonchli 'data' katalogini aniqlash.
    1. MISA_DATA_DIR muhit o'zgaruvchisi (agar o'rnatilgan bo'lsa)
    2. Mahalliy loyiha/portable papkasidagi 'data'
    3. Agar mahalliy papkaga yozish huquqi bo'lmasa -> %APPDATA%/MisaAI/data fallback
    """
    global _RESOLVED_DATA_DIR
    if _RESOLVED_DATA_DIR:
        return _RESOLVED_DATA_DIR

    # 1. Custom env
    if custom := os.environ.get("MISA_DATA_DIR"):
        try:
            os.makedirs(custom, exist_ok=True)
            _RESOLVED_DATA_DIR = custom
            return _RESOLVED_DATA_DIR
        except Exception:
            pass

    # 2. Mahalliy katalog (Portable-friendly)
    base = get_base_dir()
    local_data = os.path.join(base, "data")
    try:
        os.makedirs(local_data, exist_ok=True)
        test_file = os.path.join(local_data, ".write_test")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_file)
        _RESOLVED_DATA_DIR = local_data
        return _RESOLVED_DATA_DIR
    except Exception:
        pass

    # 3. %APPDATA%/MisaAI/data fallback
    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    safe_data = os.path.join(appdata, "MisaAI", "data")
    try:
        os.makedirs(safe_data, exist_ok=True)
        _RESOLVED_DATA_DIR = safe_data
        return _RESOLVED_DATA_DIR
    except Exception as e:
        logger.error(f"Data papkasi yaratishda jiddiy xatolik: {e}")
        _RESOLVED_DATA_DIR = local_data
        return _RESOLVED_DATA_DIR


def get_data_path(*parts: str) -> str:
    """Data papkasi ichidagi fayl yo'lini olish va papkasi mavjudligini ta'minlash."""
    data_dir = get_data_dir()
    full_path = os.path.join(data_dir, *parts)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    return full_path
