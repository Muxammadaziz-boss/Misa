# ========== core/providers/config.py ==========
# Misa AI 9.0.0 — Central Multi-Provider Configuration System

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = REPO_ROOT / "data" / "config.json"

DEFAULT_PROVIDER_SETTINGS = {
    "groq": {
        "enabled": True,
        "priority": 95,
        "timeout": 15.0,
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
    },
    "cerebras": {
        "enabled": True,
        "priority": 92,
        "timeout": 15.0,
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama-3.3-70b",
    },
    "gemini": {
        "enabled": True,
        "priority": 94,
        "timeout": 15.0,
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.0-flash",
    },
    "openrouter": {
        "enabled": True,
        "priority": 80,
        "timeout": 20.0,
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "nvidia": {
        "enabled": True,
        "priority": 74,
        "timeout": 20.0,
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "meta/llama-3.3-70b-instruct",
    },
}


class ProviderConfigManager:
    """
    Provayderlar konfiguratsiyasini boshqarish klassi.
    Provayderlarni kodni o'zgartirmasdan yoqish/o'chirish, ustuvorligini
    va timeout parametrlarini sozlash imkonini beradi.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path or CONFIG_FILE
        self._settings = self._load()

    def _load(self) -> Dict[str, Any]:
        settings = json.loads(json.dumps(DEFAULT_PROVIDER_SETTINGS))
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    prov_data = data.get("providers", {})
                    for p_name, p_cfg in prov_data.items():
                        if p_name in settings and isinstance(p_cfg, dict):
                            settings[p_name].update(p_cfg)
                        else:
                            settings[p_name] = p_cfg
            except Exception as e:
                logger.warning(f"[ProviderConfigManager] config.json yuklashda xatolik: {e}")
        return settings

    def save(self) -> bool:
        try:
            full_cfg = {}
            if self._config_path.exists():
                with open(self._config_path, "r", encoding="utf-8") as f:
                    full_cfg = json.load(f)
            full_cfg["providers"] = self._settings
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(full_cfg, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"[ProviderConfigManager] Sozlamalarni saqlashda xatolik: {e}")
            return False

    def is_provider_enabled(self, provider: str) -> bool:
        p = provider.lower()
        # Env orqali bevosita o'chirishni ham tekshirish (masalan: MISA_GROQ_ENABLED=false)
        env_val = os.getenv(f"MISA_{p.upper()}_ENABLED", "").strip().lower()
        if env_val in ("0", "false", "no"):
            return False
        return self._settings.get(p, {}).get("enabled", True)

    def set_provider_enabled(self, provider: str, enabled: bool) -> bool:
        p = provider.lower()
        if p not in self._settings:
            self._settings[p] = {"enabled": enabled, "priority": 50}
        else:
            self._settings[p]["enabled"] = enabled
        return self.save()

    def get_provider_priority(self, provider: str) -> int:
        return self._settings.get(provider.lower(), {}).get("priority", 50)

    def set_provider_priority(self, provider: str, priority: int) -> bool:
        p = provider.lower()
        if p not in self._settings:
            self._settings[p] = {"enabled": True, "priority": priority}
        else:
            self._settings[p]["priority"] = priority
        return self.save()

    def get_provider_timeout(self, provider: str) -> float:
        return float(self._settings.get(provider.lower(), {}).get("timeout", 15.0))

    def get_all_settings(self) -> Dict[str, Any]:
        return dict(self._settings)


_global_config_manager: Optional[ProviderConfigManager] = None


def get_provider_config_manager() -> ProviderConfigManager:
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ProviderConfigManager()
    return _global_config_manager
