# ========== core/v8/account_device.py ==========
# Phase 40 — Universal Account & Multi-Device Management 2.0
# Multi-User Identity -> Account -> Multi-Device Architecture
# TelegramIdentity -> MisaUser -> Device -> UserPermissionProfile -> RemoteAuthSession

import os
import time
import json
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Tuple, List

from core.v8.events import RemoteEventType, RemoteAuditLogger
from core.v8.device import DeviceIdentity, get_current_app_version

logger = logging.getLogger("core.v8.account_device")


@dataclass
class MisaUser:
    """
    Misa foydalanuvchi hisobi / public.profiles.
    Supabase auth.users.id bilan 1:1 bog'langan.
    Parol Misa tizimida hech qachon saqlanmaydi (Supabase Auth boshqaradi).
    """
    id: str  # auth.users.id (UUID)
    username: str
    email: str = ""
    display_name: str = ""
    avatar_url: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: str = "ACTIVE"  # ACTIVE, DISABLED, REVOKED
    is_verified: bool = False
    last_login_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status.upper() == "ACTIVE"

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        data = asdict(self)
        data["is_active"] = self.is_active
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MisaUser":
        valid_fields = {
            "id", "username", "email", "display_name", "avatar_url",
            "created_at", "updated_at", "status",
            "is_verified", "last_login_at", "metadata"
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


MisaProfile = MisaUser


@dataclass
class Device:
    """
    Foydalanuvchiga tegishli apparat kompyuter qurilmasi.
    Apparat identifikatori (device_id) va foydalanuvchi qulayligi uchun berilgan nom (name) ajratilgan.
    """
    misa_user_id: str
    device_id: str
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str = ""
    platform: str = "windows"
    agent_version: str = field(default_factory=get_current_app_version)
    status: str = "offline"  # online, offline, standby, revoked
    created_at: float = field(default_factory=time.time)
    last_seen_at: Optional[float] = None
    last_heartbeat_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_revoked(self) -> bool:
        return self.status.lower() == "revoked"

    @property
    def is_online(self) -> bool:
        return self.status.lower() == "online"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        valid_fields = {
            "id", "misa_user_id", "device_id", "name", "hostname",
            "platform", "agent_version", "status", "created_at",
            "last_seen_at", "last_heartbeat_at", "metadata"
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def to_device_identity(self) -> DeviceIdentity:
        """Phase 35 DeviceIdentity modeliga moslashtirish"""
        return DeviceIdentity(
            device_id=self.device_id,
            hostname=self.hostname or self.name,
            agent_version=self.agent_version,
            metadata=dict(self.metadata)
        )

    @classmethod
    def from_device_identity(
        cls,
        ident: DeviceIdentity,
        user_id: str,
        name: Optional[str] = None
    ) -> "Device":
        """Phase 35 DeviceIdentity dan Device yaratish"""
        return cls(
            misa_user_id=str(user_id),
            device_id=ident.device_id,
            name=name or ident.hostname or "Kompyuter",
            hostname=ident.hostname,
            platform=ident.os_name.lower() if hasattr(ident, "os_name") else "windows",
            agent_version=ident.agent_version,
            status=ident.status.value if hasattr(ident.status, "value") else str(ident.status),
            metadata=dict(ident.metadata)
        )


@dataclass
class UserDeviceLink:
    """
    Foydalanuvchi hisobi va qurilma o'rtasidagi doimiy egalik bog'lanishi.
    """
    misa_user_id: str
    device_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    linked_at: float = field(default_factory=time.time)
    status: str = "ACTIVE"  # ACTIVE, REVOKED
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status.upper() == "ACTIVE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserDeviceLink":
        valid_fields = {"id", "misa_user_id", "device_id", "linked_at", "status", "metadata"}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class UserDeviceContext:
    """
    Foydalanuvchining hozirda faol tanlangan qurilma konteksti.
    Har bir foydalanuvchi uchun alohida boshqariladi (global state yo'q).
    """
    user_id: str
    device_id: str
    selected_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def is_valid(self, current_time: Optional[float] = None) -> bool:
        if self.expires_at is None:
            return True
        now = current_time if current_time is not None else time.time()
        return now < self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserDeviceContext":
        return cls(**data)


class AccountDeviceManager:
    """
    Ko'p foydalanuvchili hisoblar va ko'p qurilmalar arxitekturasi boshqaruvchisi.
    TelegramIdentity -> MisaUser -> Device zanjiri va qat'iy foydalanuvchi izolatsiyasini ta'minlaydi.
    """

    _default_instance: Optional["AccountDeviceManager"] = None

    def __init__(
        self,
        storage_path: Optional[str] = None,
        session_manager=None,
        perm_store=None
    ):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "v8_accounts_devices.json"
        )
        self._users: Dict[str, MisaUser] = {}  # user_id -> MisaUser
        self._devices: Dict[str, Device] = {}  # device.id (UUID) -> Device
        self._devices_by_hw_id: Dict[str, str] = {}  # hw_device_id -> device.id (UUID)
        self._user_devices: Dict[str, List[str]] = {}  # user_id -> List[device.id]
        self._links: Dict[str, UserDeviceLink] = {}  # link.id -> UserDeviceLink
        self._contexts: Dict[str, UserDeviceContext] = {}  # user_id -> UserDeviceContext

        self._session_manager = session_manager
        self._perm_store = perm_store
        self._audit = RemoteAuditLogger.get_instance()

        self.load()

    @classmethod
    def get_default_instance(cls, storage_path: Optional[str] = None) -> "AccountDeviceManager":
        inst = getattr(cls, "_instance", None) or cls._default_instance
        if inst is None:
            cls._default_instance = cls(storage_path=storage_path)
            return cls._default_instance
        return inst

    @classmethod
    def get_instance(cls, *args, **kwargs) -> "AccountDeviceManager":
        return cls.get_default_instance(*args, **kwargs)

    # ========================================================
    # 1. USER ACCOUNT MANAGEMENT
    # ========================================================

    def register_or_get_user(self, user_id: str, username: Optional[str] = None) -> MisaUser:
        """Foydalanuvchi hisobini ro'yxatga olish yoki mavjudini qaytarish"""
        uid = str(user_id).strip()
        if not uid:
            raise ValueError("user_id bo'sh bo'lishi mumkin emas")

        if uid in self._users:
            user = self._users[uid]
            if username and user.username != username:
                user.username = username
                user.updated_at = time.time()
                self.save()
            return user

        uname = username or uid
        user = MisaUser(
            id=uid,
            username=uname,
            created_at=time.time(),
            updated_at=time.time(),
            status="ACTIVE"
        )
        self._users[uid] = user
        self.save()

        self._audit.log(
            RemoteEventType.ACCOUNT_CREATED,
            user_id=uid,
            details={"username": uname}
        )
        logger.info(f"[AccountDeviceManager] Yangi hisob ro'yxatga olindi: id={uid}, username={uname}")
        return user

    def get_user(self, user_id: str) -> Optional[MisaUser]:
        """Foydalanuvchini id orqali olish"""
        return self._users.get(str(user_id).strip())

    def list_users(self) -> List[MisaUser]:
        """Barcha foydalanuvchilar ro'yxati"""
        return list(self._users.values())

    def get_user_by_username(self, username: str) -> Optional[MisaUser]:
        """Foydalanuvchini username (case-insensitive) orqali olish"""
        uname = str(username).strip().lower()
        if not uname:
            return None
        for user in self._users.values():
            if user.username.strip().lower() == uname:
                return user
        return None

    def get_user_by_email(self, email: str) -> Optional[MisaUser]:
        """Foydalanuvchini email (case-insensitive canonical) orqali olish"""
        em = str(email).strip().lower()
        if not em:
            return None
        for user in self._users.values():
            if user.email.strip().lower() == em:
                return user
        return None

    def create_user(
        self,
        username: str,
        email: str = "",
        user_id: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        status: str = "ACTIVE",
        is_verified: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> MisaUser:
        """Yangi Misa foydalanuvchi hisobi/profilini yaratish (auth.users.id bilan bog'langan)"""
        uid = str(user_id or uuid.uuid4()).strip()
        uname = str(username).strip()
        disp_name = str(display_name or uname).strip()
        user = MisaUser(
            id=uid,
            username=uname,
            email=str(email).strip().lower(),
            display_name=disp_name,
            avatar_url=str(avatar_url or ""),
            created_at=time.time(),
            updated_at=time.time(),
            status=status.upper(),
            is_verified=is_verified,
            metadata=metadata or {}
        )
        self._users[uid] = user
        self.save()
        return user

    def upsert_profile_from_supabase(
        self,
        user_id: str,
        email: str = "",
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_verified: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MisaUser:
        """Supabase auth.users JWT ma'lumotlaridan Misa profilini yaratish yoki yangilash"""
        uid = str(user_id).strip()
        user = self._users.get(uid)
        uname = (username or (user.username if user else "") or (email.split("@")[0] if email else uid)).strip()
        disp = (display_name or (user.display_name if user else "") or uname).strip()

        if user:
            user.email = str(email or user.email).strip().lower()
            if username:
                user.username = uname
            if display_name:
                user.display_name = disp
            if avatar_url is not None:
                user.avatar_url = avatar_url
            user.is_verified = is_verified or user.is_verified
            user.updated_at = time.time()
            if metadata:
                user.metadata.update(metadata)
            self._users[uid] = user
        else:
            user = MisaUser(
                id=uid,
                username=uname,
                email=str(email).strip().lower(),
                display_name=disp,
                avatar_url=str(avatar_url or ""),
                created_at=time.time(),
                updated_at=time.time(),
                status="ACTIVE",
                is_verified=is_verified,
                metadata=metadata or {}
            )
            self._users[uid] = user

        self.save()
        return user

    def update_user(self, user: MisaUser):
        """Foydalanuvchi ma'lumotlarini saqlash"""
        user.updated_at = time.time()
        self._users[user.id] = user
        self.save()

    def update_user_status(self, user_id: str, status: str) -> bool:
        """Foydalanuvchi holatini yangilash (ACTIVE, DISABLED, REVOKED)"""
        user = self.get_user(user_id)
        if not user:
            return False
        old_status = user.status
        user.status = status.upper()
        user.updated_at = time.time()
        self.save()

        self._audit.log(
            RemoteEventType.ACCOUNT_UPDATED,
            user_id=user.id,
            details={"old_status": old_status, "new_status": user.status}
        )
        return True

    # ========================================================
    # 2. DEVICE REGISTRATION & OWNERSHIP
    # ========================================================

    def register_device(
        self,
        user_id: str,
        device_id: str,
        name: Optional[str] = None,
        hostname: str = "",
        platform: str = "windows",
        agent_version: Optional[str] = None,
        status: str = "offline",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Device:
        """
        Qurilmani aniq foydalanuvchiga biriktirish va ro'yxatdan o'tkazish.
        Agar qurilma boshqa foydalanuvchiga tegishli bo'lsa, xatolik beriladi.
        """
        if not agent_version or agent_version == "9.0.0":
            agent_version = get_current_app_version()
        uid = str(user_id).strip()
        hw_id = str(device_id).strip()
        if not uid or not hw_id:
            raise ValueError("user_id va device_id bo'sh bo'lishi mumkin emas")

        # Foydalanuvchi mavjudligini ta'minlash
        self.register_or_get_user(uid)

        # Do'stona nomni tozalash va tekshirish
        dev_name = (name or hostname or "Mening Kompyuterim").strip()
        if len(dev_name) > 64:
            dev_name = dev_name[:64].strip()

        # Agar apparat ID ilgari ro'yxatga olingan bo'lsa
        if hw_id in self._devices_by_hw_id:
            existing_uuid = self._devices_by_hw_id[hw_id]
            existing_device = self._devices.get(existing_uuid)
            if existing_device:
                if existing_device.misa_user_id in ("local_user", "Ustoz") and uid not in ("local_user", "Ustoz"):
                    old_owner = existing_device.misa_user_id
                    if old_owner in self._user_devices and existing_device.id in self._user_devices[old_owner]:
                        self._user_devices[old_owner].remove(existing_device.id)
                    existing_device.misa_user_id = uid
                    self._user_devices.setdefault(uid, [])
                    if existing_device.id not in self._user_devices[uid]:
                        self._user_devices[uid].append(existing_device.id)
                # Boshqa foydalanuvchiga tegishli va bekor qilinmagan bo'lsa - xatolik
                if existing_device.misa_user_id != uid and not existing_device.is_revoked:
                    raise ValueError(
                        f"Qurilma '{hw_id}' allaqachon boshqa hisobga ({existing_device.misa_user_id}) biriktirilgan"
                    )
                # Shu foydalanuvchiga tegishli bo'lsa - yangilash
                if existing_device.misa_user_id == uid:
                    if name:
                        existing_device.name = dev_name
                    if hostname:
                        existing_device.hostname = hostname
                    existing_device.platform = platform
                    existing_device.agent_version = agent_version
                    if status:
                        existing_device.status = status
                    if metadata and isinstance(metadata, dict):
                        existing_device.metadata.update(metadata)
                    existing_device.last_seen_at = time.time()
                    self.save()
                    return existing_device

        # Yangi qurilma yaratish
        device = Device(
            misa_user_id=uid,
            device_id=hw_id,
            name=dev_name,
            hostname=hostname,
            platform=platform,
            agent_version=agent_version,
            status=status,
            created_at=time.time(),
            last_seen_at=time.time(),
            metadata=metadata or {}
        )
        self._devices[device.id] = device
        self._devices_by_hw_id[hw_id] = device.id

        if uid not in self._user_devices:
            self._user_devices[uid] = []
        if device.id not in self._user_devices[uid]:
            self._user_devices[uid].append(device.id)

        # Egalik bog'lanishini (UserDeviceLink) yaratish
        link = UserDeviceLink(
            misa_user_id=uid,
            device_id=hw_id,
            linked_at=time.time(),
            status="ACTIVE"
        )
        self._links[link.id] = link

        self.save()

        self._audit.log(
            RemoteEventType.DEVICE_ADDED,
            user_id=uid,
            device_id=hw_id,
            details={"name": dev_name, "hostname": hostname, "uuid": device.id}
        )
        logger.info(f"[AccountDeviceManager] Yangi qurilma ulandi: user={uid}, dev={hw_id}, name='{dev_name}'")
        return device

    def get_devices_for_user(self, user_id: str, include_revoked: bool = False) -> List[Device]:
        """
        Faqat so'ralgan foydalanuvchiga tegishli qurilmalarni olish.
        Qat'iy multi-tenant izolatsiya: begona foydalanuvchi qurilmalari mutlaqo ko'rinmaydi.
        """
        uid = str(user_id).strip()
        device_ids = self._user_devices.get(uid, [])
        result = []
        for dev_uuid in device_ids:
            dev = self._devices.get(dev_uuid)
            if dev and (include_revoked or not dev.is_revoked):
                result.append(dev)
        return result

    def get_device(self, device_id_or_uuid: str, user_id: Optional[str] = None) -> Optional[Device]:
        """
        Qurilmani UUID yoki apparat device_id orqali qidirish.
        Agar user_id berilgan bo'lsa, qat'iy egalik tekshiruvi o'tkaziladi.
        """
        query = str(device_id_or_uuid).strip()
        dev = self._devices.get(query)
        if not dev and query in self._devices_by_hw_id:
            dev = self._devices.get(self._devices_by_hw_id[query])

        if not dev:
            import urllib.parse
            unquoted = urllib.parse.unquote(query)
            for d in self._devices.values():
                if (
                    d.id == query
                    or d.device_id == query
                    or (bool(d.hostname) and d.hostname.lower() == query.lower())
                    or (unquoted != query and (
                        d.id == unquoted
                        or d.device_id == unquoted
                        or (bool(d.hostname) and d.hostname.lower() == unquoted.lower())
                    ))
                ):
                    dev = d
                    break

        if not dev:
            return None

        if user_id is not None and dev.misa_user_id != str(user_id).strip():
            # Begona foydalanuvchiga tegishli bo'lsa, topilmadi sifatida yashirish
            return None

        return dev

    def get_device_by_hw_id(self, hw_id: str, user_id: Optional[str] = None) -> Optional[Device]:
        """Apparat device_id bo'yicha qurilmani olish (alias)"""
        return self.get_device(hw_id, user_id=user_id)

    # ========================================================
    # 3. FRIENDLY RENAMING
    # ========================================================

    def rename_device(
        self,
        device_id_or_uuid: str,
        user_id: str,
        new_name: str
    ) -> Tuple[bool, str, Optional[Device]]:
        """
        Qurilma do'stona nomini yangilash.
        Egalik tekshiruvi va qat'iy validatsiya bilan himoyalangan.
        """
        dev = self.get_device(device_id_or_uuid, user_id=user_id)
        if not dev:
            return False, "NOT_FOUND: Qurilma topilmadi yoki hisobingizga tegishli emas", None

        if dev.is_revoked:
            return False, "DEVICE_REVOKED: Bekor qilingan qurilma nomini o'zgartirib bo'lmaydi", None

        clean_name = str(new_name).strip()
        if not clean_name:
            return False, "VALIDATION_ERROR: Qurilma nomi bo'sh bo'lishi mumkin emas", None

        if len(clean_name) > 64:
            return False, "VALIDATION_ERROR: Qurilma nomi 64 belgidan oshmasligi kerak", None

        old_name = dev.name
        dev.name = clean_name
        self.save()

        self._audit.log(
            RemoteEventType.DEVICE_RENAMED,
            user_id=dev.misa_user_id,
            device_id=dev.device_id,
            details={"old_name": old_name, "new_name": clean_name}
        )
        logger.info(f"[AccountDeviceManager] Qurilma nomi o'zgartirildi: dev={dev.device_id}, '{old_name}' -> '{clean_name}'")
        return True, "OK: Qurilma nomi muvaffaqiyatli yangilandi", dev

    # ========================================================
    # 4. CASCADING DEVICE REVOCATION
    # ========================================================

    def revoke_device(
        self,
        device_id_or_uuid: str,
        user_id: str,
        session_manager=None,
        perm_store=None
    ) -> Tuple[bool, str]:
        """
        Qurilmani bekor qilish (Revoke):
        1. Device holati 'revoked' ga o'tkaziladi.
        2. UserDeviceLink holati 'REVOKED' qilinadi.
        3. Ushbu qurilma bo'yicha barcha faol autentifikatsiya sessiyalari uziladi.
        4. Foydalanuvchi ruxsatlar profili (PermissionStore) tozalanadi/bekor qilinadi.
        5. Agar foydalanuvchida ushbu qurilma tanlangan bo'lsa, tanlov konteksti tozalanadi.
        """
        dev = self.get_device(device_id_or_uuid, user_id=user_id)
        if not dev:
            return False, "NOT_FOUND: Qurilma topilmadi yoki hisobingizga tegishli emas"

        if dev.is_revoked:
            return True, "ALREADY_REVOKED: Qurilma allaqachon bekor qilingan"

        # 1. Qurilma holatini o'zgartirish
        dev.status = "revoked"

        # 2. Bog'lanish holatini REVOKED qilish
        for link in self._links.values():
            if link.misa_user_id == dev.misa_user_id and link.device_id == dev.device_id:
                link.status = "REVOKED"

        # 3. Kaskadli sessiya tozalash
        sm = session_manager or self._session_manager
        if sm is None:
            try:
                from core.v8.auth_session import SessionManager
                sm = SessionManager.get_default_instance()
            except Exception:
                sm = None

        if sm and hasattr(sm, "terminate_device_sessions"):
            sm.terminate_device_sessions(dev.device_id, user_id=dev.misa_user_id)
            sm.terminate_device_sessions(dev.id, user_id=dev.misa_user_id)

        # 4. Kaskadli ruxsatlarni tozalash
        ps = perm_store or self._perm_store
        if ps is None:
            try:
                from core.v8.permission_center import PermissionStore
                ps = PermissionStore.get_default_instance()
            except Exception:
                ps = None

        if ps and hasattr(ps, "revoke_device_permissions"):
            ps.revoke_device_permissions(dev.misa_user_id, dev.device_id)
            ps.revoke_device_permissions(dev.misa_user_id, dev.id)

        # 5. Faol tanlov kontekstini tozalash
        uid = dev.misa_user_id
        if uid in self._contexts:
            ctx = self._contexts[uid]
            if ctx.device_id in (dev.device_id, dev.id):
                self.clear_selected_device(uid)

        # 6. Phase 42 Kaskad: DeviceCredential va DeviceSession bekor qilish
        try:
            from core.v8.device_enrollment import DeviceEnrollmentManager
            dem = DeviceEnrollmentManager.get_default_instance()
            dem.revoke_credential(dev.device_id, user_id=dev.misa_user_id)
            dem.revoke_credential(dev.id, user_id=dev.misa_user_id)
        except Exception as e:
            logger.debug(f"[AccountDeviceManager] Credential bekor qilishda ogohlantirish: {e}")

        try:
            from core.v8.device_auth import DeviceAuthManager
            dam = DeviceAuthManager.get_default_instance()
            dam.terminate_device_sessions(dev.device_id)
            dam.terminate_device_sessions(dev.id)
        except Exception as e:
            logger.debug(f"[AccountDeviceManager] Device session to'xtatishda ogohlantirish: {e}")

        try:
            from core.v8.device_pairing import DevicePairingManager
            dpm = DevicePairingManager.get_default_instance()
            dpm.revoke_sessions_for_device(dev.device_id, user_id=dev.misa_user_id)
            dpm.revoke_sessions_for_device(dev.id, user_id=dev.misa_user_id)
        except Exception as e:
            logger.debug(f"[AccountDeviceManager] Pairing sessiyalarni bekor qilishda ogohlantirish: {e}")

        self.save()

        self._audit.log(
            RemoteEventType.DEVICE_REVOKED,
            user_id=dev.misa_user_id,
            device_id=dev.device_id,
            details={"device_name": dev.name, "uuid": dev.id}
        )
        logger.info(f"[AccountDeviceManager] Qurilma bekor qilindi va barcha sessiyalar uzildi: dev={dev.device_id}")
        return True, "OK: Qurilma muvaffaqiyatli bekor qilindi va bog'langan sessiyalar to'xtatildi"

    # ========================================================
    # 5. DEVICE SELECTION CONTEXT (PER-USER, NO GLOBAL STATE)
    # ========================================================

    def select_device(
        self,
        user_id: str,
        device_id_or_uuid: str,
        ttl: Optional[float] = None
    ) -> Tuple[bool, str, Optional[Device]]:
        """
        Foydalanuvchi uchun faol boshqaruv qurilmasini tanlash.
        Qat'iy egalik tekshiruvi: faqat o'ziga tegishli faol qurilmani tanlash mumkin.
        """
        uid = str(user_id).strip()
        dev = self.get_device(device_id_or_uuid, user_id=uid)
        if not dev:
            return False, "NOT_FOUND: Qurilma topilmadi yoki hisobingizga tegishli emas", None

        if dev.is_revoked:
            return False, "DEVICE_REVOKED: Bekor qilingan qurilmani tanlab bo'lmaydi", None

        expires_at = (time.time() + ttl) if ttl is not None else None
        ctx = UserDeviceContext(
            user_id=uid,
            device_id=dev.device_id,
            selected_at=time.time(),
            expires_at=expires_at
        )
        self._contexts[uid] = ctx
        self.save()

        self._audit.log(
            RemoteEventType.DEVICE_SELECTED,
            user_id=uid,
            device_id=dev.device_id,
            details={"device_name": dev.name, "uuid": dev.id}
        )
        logger.info(f"[AccountDeviceManager] Qurilma tanlandi: user={uid}, dev={dev.device_id} ('{dev.name}')")
        return True, "OK: Qurilma muvaffaqiyatli tanlandi", dev

    def get_selected_device(self, user_id: str) -> Optional[Device]:
        """
        Foydalanuvchining hozirda faol tanlangan qurilmasini olish.
        Muddati o'tgan yoki bekor qilingan bo'lsa, avtomatik tozalanadi.
        """
        uid = str(user_id).strip()
        ctx = self._contexts.get(uid)
        if not ctx:
            return None

        if not ctx.is_valid():
            self.clear_selected_device(uid)
            return None

        dev = self.get_device(ctx.device_id, user_id=uid)
        if not dev or dev.is_revoked:
            self.clear_selected_device(uid)
            return None

        return dev

    def clear_selected_device(self, user_id: str) -> bool:
        """Foydalanuvchining tanlangan qurilma kontekstini tozalash"""
        uid = str(user_id).strip()
        if uid in self._contexts:
            del self._contexts[uid]
            self.save()
            return True
        return False

    def select_device_by_query(self, user_id: str, query: str) -> Tuple[bool, str, Optional[Device]]:
        """
        Telegram Bot yoki CLI orqali qidiruv so'rovi (nom yoki ID) bo'yicha qurilma tanlash.
        Aniqlanmagan yoki noaniq (ambiguous) holatlarda xavfsiz ogohlantirish qaytaradi.
        """
        uid = str(user_id).strip()
        q = str(query).strip().lower()
        if not q:
            return False, "VALIDATION_ERROR: Qurilma nomi yoki ID sini kiriting", None

        devices = self.get_devices_for_user(uid, include_revoked=False)
        if not devices:
            return False, "NO_DEVICES: Sizning hisobingizga birorta ham faol qurilma ulanmagan", None

        # 1. Aniq moslik (Exact match) - device_id yoki id (UUID)
        for d in devices:
            if d.device_id.lower() == q or d.id.lower() == q:
                return self.select_device(uid, d.device_id)

        # 2. Aniq nom bo'yicha moslik (Exact match on name)
        for d in devices:
            if d.name.strip().lower() == q:
                return self.select_device(uid, d.device_id)

        # 3. Qisman moslik (Substring / Prefix match)
        matches = []
        for d in devices:
            if (
                q in d.name.lower()
                or d.device_id.lower().startswith(q)
                or d.id.lower().startswith(q)
            ):
                matches.append(d)

        if len(matches) == 1:
            return self.select_device(uid, matches[0].device_id)

        if len(matches) > 1:
            names = ", ".join(f"'{d.name}' (`{d.device_id}`)" for d in matches)
            return (
                False,
                f"AMBIGUOUS: '{query}' so'rovi bo'yicha bir nechta qurilma topildi: {names}. "
                "Iltimos, aniqroq nom yoki apparat ID sini ko'rsating.",
                None
            )

        return False, f"NOT_FOUND: '{query}' nomli yoki ID li qurilma hisobingizda topilmadi", None

    # ========================================================
    # 6. HEARTBEAT & TELEMETRY SYNC
    # ========================================================

    def update_device_heartbeat(self, device_id: str, status: Optional[str] = None):
        """Qurilmaning oxirgi aloqa vaqti va holatini yangilash"""
        hw_id = str(device_id).strip()
        dev = self.get_device(hw_id)
        if not dev:
            return

        now = time.time()
        dev.last_seen_at = now
        dev.last_heartbeat_at = now
        if status and not dev.is_revoked:
            dev.status = status.lower()
        self.save()

    # ========================================================
    # 7. ACCOUNT SUMMARY
    # ========================================================

    def get_user_account_summary(
        self,
        user_id: str,
        tg_identity_mgr=None,
        session_mgr=None
    ) -> Dict[str, Any]:
        """Foydalanuvchi hisobi, ulangan qurilmalari va sessiyalari umumiy ma'lumoti"""
        uid = str(user_id).strip()
        user = self.get_user(uid) or self.register_or_get_user(uid)
        devices = self.get_devices_for_user(uid, include_revoked=False)
        selected_device = self.get_selected_device(uid)

        # Telegram bog'lanish ma'lumotlari
        tg_link = None
        tg_ident = None
        if tg_identity_mgr:
            tg_link = tg_identity_mgr.get_link_by_misa_user(uid)
            if tg_link:
                tg_ident = tg_identity_mgr.get_identity(tg_link.telegram_user_id)

        # Faol sessiyalar soni
        active_sessions_count = 0
        if session_mgr and hasattr(session_mgr, "get_sessions_for_user"):
            active_sessions_count = len(session_mgr.get_sessions_for_user(uid))

        return {
            "user_id": user.id,
            "username": user.username,
            "status": user.status,
            "created_at": user.created_at,
            "devices_count": len(devices),
            "active_sessions_count": active_sessions_count,
            "selected_device": selected_device.to_dict() if selected_device else None,
            "telegram_linked": tg_link is not None and tg_link.is_active,
            "telegram_identity": tg_ident.to_dict() if tg_ident else None
        }

    # ========================================================
    # 8. PERSISTENCE (SAFE JSON STORAGE)
    # ========================================================

    def save(self):
        """Ma'lumotlarni doimiy faylga atomik va xavfsiz saqlash"""
        if not self.storage_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
            data = {
                "users": {k: v.to_dict() for k, v in self._users.items()},
                "devices": {k: v.to_dict() for k, v in self._devices.items()},
                "devices_by_hw_id": self._devices_by_hw_id,
                "user_devices": self._user_devices,
                "links": {k: v.to_dict() for k, v in self._links.items()},
                "contexts": {k: v.to_dict() for k, v in self._contexts.items()}
            }
            tmp_path = f"{self.storage_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if os.path.exists(self.storage_path):
                os.replace(tmp_path, self.storage_path)
            else:
                os.rename(tmp_path, self.storage_path)
        except Exception as e:
            logger.error(f"[AccountDeviceManager] Saqlashda xatolik: {e}")

    def load(self):
        """Fayldan mavjud hisoblar va qurilmalarni tiklash"""
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            users_raw = data.get("users", {})
            self._users = {k: MisaUser.from_dict(v) for k, v in users_raw.items()}

            devices_raw = data.get("devices", {})
            self._devices = {k: Device.from_dict(v) for k, v in devices_raw.items()}

            self._devices_by_hw_id = data.get("devices_by_hw_id", {})
            self._user_devices = data.get("user_devices", {})

            links_raw = data.get("links", {})
            self._links = {k: UserDeviceLink.from_dict(v) for k, v in links_raw.items()}

            contexts_raw = data.get("contexts", {})
            self._contexts = {k: UserDeviceContext.from_dict(v) for k, v in contexts_raw.items()}

            logger.info(
                f"[AccountDeviceManager] Yuklandi: {len(self._users)} ta hisob, "
                f"{len(self._devices)} ta qurilma, {len(self._contexts)} ta kontekst"
            )
        except Exception as e:
            logger.error(f"[AccountDeviceManager] Yuklashda xatolik: {e}")
