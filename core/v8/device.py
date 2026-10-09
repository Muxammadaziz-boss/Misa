import os
import json
import time
import socket
import getpass
import platform
import uuid
import hashlib
import secrets
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Tuple, List

from core.v8.heartbeat import DeviceState
from core.v8.events import RemoteEventType, RemoteAuditLogger

logger = logging.getLogger("core.v8.device")


def get_current_app_version() -> str:
    """Tizimning joriy versiyasini dinamik olish (yagona haqiqat manbai)."""
    try:
        from config import get_config
        ver = get_config("app.version")
        if ver:
            return str(ver).strip()
    except Exception:
        pass
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cfg_path = os.path.join(base_dir, "data", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                v = data.get("app", {}).get("version")
                if v:
                    return str(v).strip()
    except Exception:
        pass
    return "9.0.1"


@dataclass
class DeviceIdentity:
    """
    Qurilmaning barqaror va deterministik identifikatori.
    """
    device_id: str
    hostname: str
    username: str = "admin"
    os_name: str = "Windows"
    os_version: str = "10"
    os_release: str = "10.0"
    architecture: str = "x86_64"
    mac_address: str = "00:00:00:00:00:00"
    local_ip: str = "127.0.0.1"
    fingerprint: str = ""
    agent_version: str = field(default_factory=get_current_app_version)
    misa_version: str = field(default_factory=get_current_app_version)
    last_seen: Optional[str] = None
    status: DeviceState = DeviceState.OFFLINE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if isinstance(self.status, DeviceState):
            data["status"] = self.status.value
        data["hardware_fingerprint"] = self.fingerprint
        return data

    @property
    def hardware_fingerprint(self) -> str:
        return self.fingerprint

    @property
    def platform(self) -> str:
        return self.os_name

    @property
    def name(self) -> str:
        return str(self.metadata.get("friendly_name") or self.hostname)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceIdentity":
        data = dict(data)
        if "status" in data and isinstance(data["status"], str):
            try:
                data["status"] = DeviceState(data["status"])
            except ValueError:
                data["status"] = DeviceState.OFFLINE
        valid_fields = {
            "device_id", "hostname", "username", "os_name", "os_version",
            "os_release", "architecture", "mac_address", "local_ip",
            "fingerprint", "agent_version", "misa_version", "last_seen",
            "status", "metadata"
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class DeviceIdentityManager:
    """
    Qurilma identifikatsiyasini aniqlash va boshqarish.
    """

    @staticmethod
    def get_mac_address() -> str:
        try:
            node = uuid.getnode()
            return ':'.join(['{:02x}'.format((node >> i) & 0xff) for i in range(0, 48, 8)][::-1])
        except Exception:
            return "00:00:00:00:00:00"

    @staticmethod
    def get_local_ip() -> str:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "127.0.0.1"

    @classmethod
    def compute_fingerprint(
        cls,
        hostname: Optional[str] = None,
        machine: Optional[str] = None,
        mac: Optional[str] = None
    ) -> str:
        """To'liq 64-belgili SHA-256 apparat xeshini hisoblash"""
        h = (hostname or socket.gethostname()).lower().strip()
        m = (machine or platform.machine()).lower().strip()
        mc = (mac or cls.get_mac_address()).lower().strip()
        raw = f"{h}|{m}|{mc}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def generate_fingerprint(cls, hostname: str, machine: str, mac: str) -> str:
        return cls.compute_fingerprint(hostname, machine, mac)[:16]

    @classmethod
    def create_local_identity(cls, override_device_id: Optional[str] = None) -> DeviceIdentity:
        hostname = socket.gethostname()
        username = getpass.getuser()
        mac = cls.get_mac_address()
        machine = platform.machine()
        fingerprint = cls.compute_fingerprint(hostname, machine, mac)

        dev_id = override_device_id or f"{username}@{hostname}"

        return DeviceIdentity(
            device_id=dev_id,
            hostname=hostname,
            username=username,
            os_name=platform.system(),
            os_version=platform.version(),
            os_release=platform.release(),
            architecture=machine,
            mac_address=mac,
            local_ip=cls.get_local_ip(),
            fingerprint=fingerprint,
            agent_version=get_current_app_version(),
            misa_version=get_current_app_version(),
            status=DeviceState.ONLINE
        )


@dataclass
class DevicePairingRecord:
    device_id: str
    paired_user_id: str
    pairing_token: str
    fingerprint: str
    mac_address: str
    created_at: float = field(default_factory=time.time)
    last_authenticated_at: float = field(default_factory=time.time)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevicePairingRecord":
        return cls(**data)


class DeviceRegistry:
    """
    Qurilmalarni ro'yxatga olish, autentifikatsiya va pairing xotirasi.
    Impersonation (soxtalashtirish) hujumlaridan himoyalangan.
    """

    _default_instance: Optional["DeviceRegistry"] = None

    @classmethod
    def get_default_instance(cls, storage_path: Optional[str] = None) -> "DeviceRegistry":
        if cls._default_instance is None:
            cls._default_instance = DeviceRegistry(storage_path=storage_path)
        return cls._default_instance

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self._devices: Dict[str, DeviceIdentity] = {}
        self._pairings: Dict[str, DevicePairingRecord] = {}  # device_id -> pairing
        self._audit = RemoteAuditLogger.get_instance()
        if storage_path and os.path.exists(storage_path):
            self.load()

    def register_device(self, identity: DeviceIdentity) -> Tuple[bool, str]:
        return self.register_or_update(identity)

    def register_or_update(
        self,
        identity: DeviceIdentity,
        pairing_token: Optional[str] = None,
        enforce_pairing: bool = False
    ) -> Tuple[bool, str]:
        """
        Qurilmani ro'yxatga olish yoki yangilash.
        """
        dev_id = identity.device_id

        # Impersonation tekshiruvi (agar avval mavjud bo'lsa)
        if dev_id in self._devices:
            existing = self._devices[dev_id]
            if existing.fingerprint and identity.fingerprint and existing.fingerprint != identity.fingerprint:
                self._audit.log(
                    RemoteEventType.DEVICE_AUTH_FAILED,
                    device_id=dev_id,
                    reason="Fingerprint mismatch"
                )
                return False, "DEVICE_AUTH_FAILED: Qurilma apparat xeshi mos kelmadi (impersonation detected)"

        # Pairing tekshiruvi (agar ushbu qurilma pair qilingan bo'lsa)
        if dev_id in self._pairings:
            pairing = self._pairings[dev_id]
            if not pairing.is_active:
                return False, "DEVICE_AUTH_FAILED: Qurilma pairing holati faol emas"
            if pairing_token and pairing.pairing_token != pairing_token:
                self._audit.log(
                    RemoteEventType.DEVICE_AUTH_FAILED,
                    device_id=dev_id,
                    reason="Invalid pairing token"
                )
                return False, "DEVICE_AUTH_FAILED: Noto'g'ri pairing token"
            pairing.last_authenticated_at = time.time()
        elif enforce_pairing:
            return False, "DEVICE_AUTH_FAILED: Qurilma avval Telegram foydalanuvchisi bilan pair qilinmagan"

        identity.last_seen = time.strftime("%Y-%m-%d %H:%M:%S")
        identity.status = DeviceState.ONLINE
        self._devices[dev_id] = identity

        self._audit.log(
            RemoteEventType.DEVICE_REGISTERED,
            device_id=dev_id,
            hostname=identity.hostname,
            os=f"{identity.os_name} {identity.os_release}"
        )
        self.save()
        return True, "OK"

    def pair_device(
        self,
        device_id: str,
        user_id: str,
        fingerprint: str,
        mac_address: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DevicePairingRecord:
        """Qurilmani muayyan Telegram user_id ga bog'lash (pairing)"""
        token = secrets.token_hex(16)
        record = DevicePairingRecord(
            device_id=device_id,
            paired_user_id=str(user_id),
            pairing_token=token,
            fingerprint=fingerprint,
            mac_address=mac_address,
            metadata=metadata or {}
        )
        self._pairings[device_id] = record
        self.save()
        return record

    def verify_pairing(
        self,
        device_id: str,
        user_id: str,
        token: Optional[str] = None,
        fingerprint: Optional[str] = None
    ) -> Tuple[bool, str]:
        if device_id not in self._pairings:
            return False, "DEVICE_NOT_PAIRED: Qurilma topilmadi yoki hali bog'lanmagan"

        pairing = self._pairings[device_id]
        if not pairing.is_active:
            return False, "PAIRING_INACTIVE: Bog'lanish o'chirilgan"

        if pairing.paired_user_id != str(user_id):
            return False, "UNAUTHORIZED_DEVICE_USER: Ushbu foydalanuvchiga bu qurilmani boshqarish ruxsat etilmagan"

        if token and pairing.pairing_token != token:
            return False, "INVALID_PAIRING_TOKEN: Token mos kelmadi"

        if fingerprint and pairing.fingerprint != fingerprint:
            return False, "FINGERPRINT_MISMATCH: Apparat xeshi mos kelmadi"

        return True, "OK"

    def get_paired_device_for_user(self, user_id: str) -> Optional[DeviceIdentity]:
        str_uid = str(user_id)
        for dev_id, pairing in self._pairings.items():
            if pairing.paired_user_id == str_uid and pairing.is_active:
                return self._devices.get(dev_id)
        return None

    def get_device(self, device_id: str) -> Optional[DeviceIdentity]:
        return self._devices.get(device_id)

    def list_devices(self) -> List[DeviceIdentity]:
        return list(self._devices.values())

    def unpair_device(self, device_id: str) -> bool:
        if device_id in self._pairings:
            self._pairings[device_id].is_active = False
            self.save()
            return True
        return False

    def save(self):
        if not self.storage_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
            data = {
                "devices": {k: v.to_dict() for k, v in self._devices.items()},
                "pairings": {k: v.to_dict() for k, v in self._pairings.items()}
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[DeviceRegistry] Saqlashda xatolik: {e}")

    def load(self):
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._devices = {k: DeviceIdentity.from_dict(v) for k, v in data.get("devices", {}).items()}
            self._pairings = {k: DevicePairingRecord.from_dict(v) for k, v in data.get("pairings", {}).items()}
        except Exception as e:
            logger.error(f"[DeviceRegistry] Yuklashda xatolik: {e}")
