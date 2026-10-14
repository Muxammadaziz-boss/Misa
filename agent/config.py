# ========== agent/config.py ==========
# Phase 45 — Windows PC Agent Configuration Manager
# Environment, configuration file, and safe default management

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

logger = logging.getLogger("misa.agent.config")


@dataclass
class AgentConfig:
    """
    Misa Windows PC Agent konfiguratsiya modeli.
    Maxfiy kalitlar hech qachon ushbu konfiguratsiyada saqlanmaydi.
    """
    backend_url: str = "http://127.0.0.1:18420"
    device_id: Optional[str] = None
    friendly_name: Optional[str] = None
    heartbeat_interval: float = 30.0
    heartbeat_timeout: float = 60.0
    reconnect_base_delay: float = 1.0
    reconnect_max_delay: float = 60.0
    reconnect_jitter: bool = True
    protocol_version: str = "1.0"
    agent_version: str = "9.0.1"
    poll_interval: float = 3.0
    vault_dir: Optional[str] = None
    config_path: Optional[str] = None
    ca_cert_path: Optional[str] = None

    @property
    def device_name(self) -> Optional[str]:
        return self.friendly_name

    @property
    def heartbeat_interval_seconds(self) -> float:
        return self.heartbeat_interval

    @property
    def poll_interval_seconds(self) -> float:
        return self.poll_interval

    def validate(self):
        """Konfiguratsiya parametrlarini xavfsizlik va mantiqiy jihatdan tekshirish"""
        if not self.backend_url or not (
            self.backend_url.startswith("http://") or self.backend_url.startswith("https://")
        ):
            raise ValueError(f"Noto'g'ri backend_url: '{self.backend_url}'. HTTP yoki HTTPS talab etiladi.")

        if self.heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval musbat son bo'lishi shart")

        if self.reconnect_base_delay <= 0 or self.reconnect_max_delay < self.reconnect_base_delay:
            raise ValueError("Noto'g'ri reconnect delay parametrlari")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(
        cls,
        config_path: Optional[str] = None,
        env_prefix: str = "MISA_AGENT_"
    ) -> "AgentConfig":
        """
        Konfiguratsiyani fayldan va muhit o'zgaruvchilaridan (env) xavfsiz yuklash.
        Ustuvorlik: Environment variables > Config file > Default values
        """
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        default_dir = os.path.join(appdata, "MisaAI", "agent")
        default_cfg_file = os.path.join(default_dir, "agent_config.json")

        def _get_env(key: str) -> Optional[str]:
            val = os.environ.get(f"{env_prefix}{key}")
            if val is not None:
                return val
            if env_prefix == "MISA_AGENT_":
                return os.environ.get(f"MISA_AGENT_{key}")
            return None

        cfg_file = config_path or _get_env("CONFIG_PATH") or default_cfg_file
        file_data: Dict[str, Any] = {}

        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
            except Exception as e:
                logger.warning(f"[AgentConfig] Konfiguratsiya faylini o'qishda xato: {e}")

        backend_url = (
            _get_env("BACKEND_URL")
            or file_data.get("backend_url")
            or "http://127.0.0.1:18420"
        )
        device_id = (
            _get_env("DEVICE_ID")
            or file_data.get("device_id")
        )
        friendly_name = (
            _get_env("FRIENDLY_NAME")
            or file_data.get("friendly_name")
        )
        heartbeat_interval = float(
            _get_env("HEARTBEAT_INTERVAL")
            or file_data.get("heartbeat_interval")
            or 30.0
        )
        heartbeat_timeout = float(
            _get_env("HEARTBEAT_TIMEOUT")
            or file_data.get("heartbeat_timeout")
            or 60.0
        )
        reconnect_base_delay = float(
            _get_env("RECONNECT_BASE_DELAY")
            or file_data.get("reconnect_base_delay")
            or 1.0
        )
        reconnect_max_delay = float(
            _get_env("RECONNECT_MAX_DELAY")
            or file_data.get("reconnect_max_delay")
            or 60.0
        )
        vault_dir = (
            _get_env("VAULT_DIR")
            or file_data.get("vault_dir")
            or os.path.join(default_dir, "vault")
        )

        cfg = cls(
            backend_url=backend_url.rstrip("/"),
            device_id=device_id,
            friendly_name=friendly_name,
            heartbeat_interval=heartbeat_interval,
            heartbeat_timeout=heartbeat_timeout,
            reconnect_base_delay=reconnect_base_delay,
            reconnect_max_delay=reconnect_max_delay,
            reconnect_jitter=file_data.get("reconnect_jitter", True),
            protocol_version="1.0",
            agent_version="9.0.0",
            vault_dir=vault_dir,
            config_path=cfg_file
        )
        cfg.validate()
        return cfg

    def save(self, target_path: Optional[str] = None) -> bool:
        """Konfiguratsiyani faylga yozish"""
        path = target_path or self.config_path
        if not path:
            return False
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = {
                "backend_url": self.backend_url,
                "device_id": self.device_id,
                "friendly_name": self.friendly_name,
                "heartbeat_interval": self.heartbeat_interval,
                "heartbeat_timeout": self.heartbeat_timeout,
                "reconnect_base_delay": self.reconnect_base_delay,
                "reconnect_max_delay": self.reconnect_max_delay,
                "reconnect_jitter": self.reconnect_jitter,
                "vault_dir": self.vault_dir,
                "agent_version": self.agent_version,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"[AgentConfig] Konfiguratsiyani saqlashda xato: {e}")
            return False

    @classmethod
    def from_env_or_file(cls, *args, **kwargs) -> "AgentConfig":
        """Konfiguratsiyani yuklash (alias)"""
        return cls.load(*args, **kwargs)


def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """Agent konfiguratsiyasini env yoki fayldan yuklash"""
    return AgentConfig.load(config_path=config_path)
