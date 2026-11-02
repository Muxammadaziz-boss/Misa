# ========== core/v8/telegram_identity.py ==========
# Phase 39 — Universal Telegram Bot ↔ Misa User App
# Multi-User Telegram Identity & OTP Account Linking Engine
# Canonical numeric Telegram ID, salted SHA-256 OTP hashing, deep-link token verification

import os
import time
import json
import uuid
import hmac
import hashlib
import secrets
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Tuple, List

from core.v8.events import RemoteEventType, RemoteAuditLogger

logger = logging.getLogger("core.v8.telegram_identity")


@dataclass
class TelegramIdentity:
    """
    Universal Telegram Identity representation.
    Strictly canonicalized by positive integer telegram_user_id.
    Never relies on username as primary identity.
    """
    telegram_user_id: Any
    first_name: Optional[str] = None
    username: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    is_verified: bool = False
    is_linked: bool = False
    linked_at: float = field(default_factory=time.time)

    def is_valid(self) -> bool:
        is_valid, _ = self.validate_user_id(self.telegram_user_id)
        return is_valid

    @property
    def user_id(self) -> Optional[int]:
        is_valid, uid = self.validate_user_id(self.telegram_user_id)
        return uid if is_valid else None

    @classmethod
    def validate_user_id(cls, val: Any) -> Tuple[bool, Optional[int]]:
        """Validate and normalize arbitrary Telegram ID input to positive integer."""
        if val is None or isinstance(val, bool):
            return False, None
        try:
            if isinstance(val, int) and val > 0:
                return True, val
            if isinstance(val, str):
                s = val.strip()
                if s.isdigit() and int(s) > 0:
                    return True, int(s)
        except (ValueError, TypeError):
            pass
        return False, None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelegramIdentity":
        valid_fields = {
            "telegram_user_id", "first_name", "username",
            "created_at", "last_seen_at", "is_verified",
            "is_linked", "linked_at"
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class TelegramLinkRequest:
    """
    One-time pairing request for account linking.
    Plaintext OTP is NEVER stored. Only salted SHA-256 hash is persisted.
    """
    misa_user_id: str
    otp_hash: str
    salt: str
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    status: str = "PENDING"  # PENDING, VERIFIED, EXPIRED, FAILED
    attempt_count: int = 0
    telegram_user_id: Optional[int] = None
    used_at: Optional[float] = None
    link_token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    expected_telegram_user_id: Optional[int] = None
    _transient_auth_token: Optional[str] = field(default=None, repr=False, compare=False)

    def is_valid(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return self.status == "PENDING" and (now < self.expires_at) and (self.attempt_count < 5)

    def is_expired(self, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        return now >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("_transient_auth_token", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelegramLinkRequest":
        valid_fields = {
            "misa_user_id", "otp_hash", "salt", "request_id",
            "created_at", "expires_at", "status", "attempt_count",
            "telegram_user_id", "used_at", "link_token",
            "expected_telegram_user_id"
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


@dataclass
class UserTelegramLink:
    """
    Active persistent link between Misa User Account and Telegram Numeric ID.
    Enforces 1:1 active mapping between Misa user and Telegram account.
    """
    misa_user_id: str
    telegram_user_id: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    linked_at: float = field(default_factory=time.time)
    last_verified_at: float = field(default_factory=time.time)
    status: str = "ACTIVE"  # ACTIVE, REVOKED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.telegram_user_id, str):
            clean = self.telegram_user_id.strip()
            if clean.isdigit() and int(clean) > 0:
                self.telegram_user_id = int(clean)
            else:
                raise ValueError(f"Invalid telegram_user_id in link: {self.telegram_user_id}")
        elif not isinstance(self.telegram_user_id, int) or self.telegram_user_id <= 0:
            raise ValueError(f"Invalid telegram_user_id in link: {self.telegram_user_id}")

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"

    @property
    def username(self) -> Optional[str]:
        return self.metadata.get("username")

    @property
    def first_name(self) -> Optional[str]:
        return self.metadata.get("first_name")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserTelegramLink":
        valid_fields = {
            "misa_user_id", "telegram_user_id", "id",
            "linked_at", "last_verified_at", "status", "metadata"
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class TelegramIdentityManager:
    """
    Central Multi-User Telegram Identity & Account Linking Manager.
    Handles OTP generation, salted SHA-256 hashing, constant-time verification,
    deep-link tokens, rate limiting, and persistence without plaintext secrets.
    """

    DEFAULT_TTL: float = 300.0  # 5 minutes
    MAX_ATTEMPTS: int = 5
    RATE_LIMIT_MAX_REQUESTS: int = 3
    RATE_LIMIT_WINDOW: float = 600.0  # 10 minutes
    DEFAULT_BOT_USERNAME: str = "Misa_ai_agent_bot"

    _default_instance: Optional["TelegramIdentityManager"] = None

    def __init__(self, storage_path: Optional[str] = None, auto_load_supabase: Optional[bool] = None):
        self._auto_supabase = (storage_path is None) if auto_load_supabase is None else bool(auto_load_supabase)
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "v8_telegram_links.json"
        )
        self._links_by_tg: Dict[int, UserTelegramLink] = {}
        self._links_by_misa: Dict[str, UserTelegramLink] = {}
        self._identities: Dict[int, TelegramIdentity] = {}
        self._requests: Dict[str, TelegramLinkRequest] = {}  # request_id -> req
        self._requests_by_token: Dict[str, TelegramLinkRequest] = {}  # link_token -> req
        self._generation_history: Dict[str, List[float]] = {}  # misa_user_id -> timestamps
        
        # XAVFSIZLIK: Telegram foydalanuvchi uchun noto'g'ri OTP urinishlari limiti (brute-force oldini olish)
        self._telegram_otp_failures: Dict[int, List[float]] = {}  # telegram_user_id -> [timestamp, ...]
        self.MAX_TELEGRAM_OTP_FAILURES = 5  # Har 10 daqiqada maksimal noto'g'ri urinishlar
        self.TELEGRAM_OTP_FAILURE_WINDOW = 600.0  # 10 daqiqa
        
        self._audit = RemoteAuditLogger.get_instance()
        self.load()

    @classmethod
    def get_default_instance(cls, storage_path: Optional[str] = None) -> "TelegramIdentityManager":
        if cls._default_instance is None:
            cls._default_instance = cls(storage_path=storage_path)
        return cls._default_instance

    @staticmethod
    def hash_otp(otp: str, salt: str) -> str:
        """Compute salted SHA-256 hash of plaintext OTP."""
        clean_otp = str(otp).strip()
        data = f"{salt}:{clean_otp}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @classmethod
    def verify_otp_hash(cls, otp: str, salt: str, expected_hash: str) -> bool:
        """Constant-time verification of candidate OTP against stored salted hash."""
        candidate_hash = cls.hash_otp(otp, salt)
        return hmac.compare_digest(candidate_hash, expected_hash)

    def check_rate_limit(self, misa_user_id: str, current_time: Optional[float] = None) -> bool:
        """
        Check if user has exceeded max 3 OTP requests in the last 10 minutes.
        Returns True if request is allowed, False if rate limited.
        """
        now = current_time if current_time is not None else time.time()
        uid = str(misa_user_id)
        history = self._generation_history.get(uid, [])
        # Prune older than window
        cutoff = now - self.RATE_LIMIT_WINDOW
        recent = [t for t in history if t > cutoff]
        self._generation_history[uid] = recent
        return len(recent) < self.RATE_LIMIT_MAX_REQUESTS

    def record_rate_limit_attempt(self, misa_user_id: str, current_time: Optional[float] = None):
        now = current_time if current_time is not None else time.time()
        uid = str(misa_user_id)
        if uid not in self._generation_history:
            self._generation_history[uid] = []
        self._generation_history[uid].append(now)

    def create_link_request(
        self,
        misa_user_id: str,
        ttl: Optional[float] = None,
        bot_username: str = "Misa_ai_agent_bot",
        current_time: Optional[float] = None,
        expected_telegram_user_id: Optional[Any] = None,
        auth_token: Optional[str] = None
    ) -> Tuple[Optional[TelegramLinkRequest], Optional[str], Optional[str], Optional[str]]:
        """
        Generate a new 6-digit OTP and deep link for a Misa account.
        Returns (request, plaintext_otp, deep_link, error_message).
        Plaintext OTP is ONLY returned in this call and NEVER stored.
        """
        now = current_time if current_time is not None else time.time()
        uid = str(misa_user_id).strip()
        if not uid:
            return None, None, None, "INVALID_USER_ID: Misa User ID bo'sh bo'lishi mumkin emas"

        expected_tg_int: Optional[int] = None
        if expected_telegram_user_id is not None:
            is_valid_tg, expected_tg_int = TelegramIdentity.validate_user_id(expected_telegram_user_id)
            if not is_valid_tg or expected_tg_int is None:
                return None, None, None, "INVALID_TELEGRAM_ID: Kutilayotgan Telegram ID musbat butun son bo'lishi shart"

        # Rate limit check
        if not self.check_rate_limit(uid, now):
            self._audit.log(
                RemoteEventType.TELEGRAM_LINK_RATE_LIMITED,
                user_id=uid,
                window_seconds=self.RATE_LIMIT_WINDOW,
                max_requests=self.RATE_LIMIT_MAX_REQUESTS
            )
            return None, None, None, "RATE_LIMITED: 10 daqiqa ichida maksimal 3 ta kod so'rash mumkin"

        # Record attempt
        self.record_rate_limit_attempt(uid, now)

        # Expire any prior PENDING requests for the same user so only the latest code is active
        for old_req in list(self._requests.values()):
            if old_req.misa_user_id == uid and old_req.status == "PENDING":
                old_req.status = "EXPIRED"
                self.sync_request_to_supabase(old_req, auth_token=auth_token)

        # Generate cryptographically secure 6-digit OTP: [100000, 999999]
        plaintext_otp = f"{secrets.randbelow(900000) + 100000}"
        salt = secrets.token_hex(16)
        otp_hash = self.hash_otp(plaintext_otp, salt)

        req_ttl = ttl if ttl is not None else self.DEFAULT_TTL
        link_token = secrets.token_urlsafe(24)
        clean_bot = (bot_username or self.DEFAULT_BOT_USERNAME).lstrip("@").strip() or self.DEFAULT_BOT_USERNAME
        deep_link = f"https://t.me/{clean_bot}?start={link_token}"

        req = TelegramLinkRequest(
            misa_user_id=uid,
            otp_hash=otp_hash,
            salt=salt,
            created_at=now,
            expires_at=now + req_ttl,
            status="PENDING",
            attempt_count=0,
            link_token=link_token,
            expected_telegram_user_id=expected_tg_int,
            _transient_auth_token=auth_token
        )

        self._requests[req.request_id] = req
        self._requests_by_token[link_token] = req

        self.save()
        self.sync_request_to_supabase(req, auth_token=auth_token)
        self._sync_request_to_cloud_api(req, auth_token=auth_token)

        self._audit.log(
            RemoteEventType.TELEGRAM_LINK_REQUEST_CREATED,
            request_id=req.request_id,
            user_id=uid,
            expires_at=req.expires_at,
            ttl=req_ttl
        )

        logger.info(f"[TelegramIdentity] Yangi bog'lanish so'rovi yaratildi: req={req.request_id}, user={uid}, ttl={req_ttl}s")
        return req, plaintext_otp, deep_link, None

    def register_synced_request(
        self,
        req_data: Optional[Dict[str, Any]] = None,
        auth_token: Optional[str] = None,
        **kwargs: Any
    ) -> Optional[TelegramLinkRequest]:
        """
        Register or update a hashed TelegramLinkRequest received from a Desktop/Web client
        so the cloud webhook server can verify the OTP even before or without service_role key.
        """
        payload: Dict[str, Any] = {}
        if isinstance(req_data, dict):
            nested = req_data.get("request")
            if isinstance(nested, dict):
                payload.update(nested)
            else:
                payload.update(req_data)
        if kwargs:
            payload.update(kwargs)

        req_id = str(payload.get("request_id") or "").strip()
        uid = str(payload.get("misa_user_id") or "").strip()
        otp_hash = str(payload.get("otp_hash") or "").strip()
        salt = str(payload.get("salt") or "").strip()
        if not req_id or not uid or not otp_hash or not salt:
            return None

        req = TelegramLinkRequest.from_dict(payload)
        if auth_token:
            req._transient_auth_token = auth_token

        for old_req in list(self._requests.values()):
            if old_req.misa_user_id == uid and old_req.request_id != req.request_id and old_req.status == "PENDING":
                old_req.status = "EXPIRED"
                old_req._transient_auth_token = None

        self._requests[req.request_id] = req
        if req.link_token:
            self._requests_by_token[req.link_token] = req
        self.save()
        if self._auto_supabase or auth_token:
            self.sync_request_to_supabase(req, auth_token=auth_token)
        return req

    DEFAULT_CLOUD_API_URL = "https://misa.up.railway.app"

    def _resolve_cloud_api_url(self) -> str:
        """Resolve cloud API URL for Desktop <-> Railway OTP synchronization."""
        if (
            os.environ.get("RAILWAY_ENVIRONMENT")
            or os.environ.get("RAILWAY_PROJECT_ID")
            or os.environ.get("MISA_API_HOST", "").strip() == "0.0.0.0"
        ):
            return ""
        cloud_url = (
            os.environ.get("MISA_CLOUD_API_URL")
            or os.environ.get("MISA_BACKEND_URL")
            or (self.DEFAULT_CLOUD_API_URL if self._auto_supabase else "")
        ).strip().rstrip("/")
        if not cloud_url or "127.0.0.1" in cloud_url or "localhost" in cloud_url:
            return ""
        return cloud_url

    def _sync_request_to_cloud_api(self, req_obj: TelegramLinkRequest, auth_token: Optional[str] = None):
        """
        If running on a local desktop instance, push the hashed request to /api/telegram/link/sync
        on Railway so the cloud webhook handler can verify the OTP immediately.
        """
        cloud_url = self._resolve_cloud_api_url()
        if not cloud_url or not auth_token:
            return

        endpoint = f"{cloud_url}/api/telegram/link/sync"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        payload_bytes = json.dumps({"request": req_obj.to_dict()}).encode("utf-8")
        req_id = req_obj.request_id

        def _do_sync():
            try:
                import urllib.request
                http_req = urllib.request.Request(
                    endpoint,
                    data=payload_bytes,
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(http_req, timeout=3.5) as resp:
                    if resp.status in (200, 201):
                        logger.info(f"[TelegramIdentity] Cloud API ga request sinxronlandi: req={req_id}")
            except Exception as e:
                logger.debug(f"[TelegramIdentity] Cloud API sync o'tkazib yuborildi: {e}")

        try:
            import asyncio
            import threading
            asyncio.get_running_loop()
            threading.Thread(target=_do_sync, daemon=True).start()
        except RuntimeError:
            _do_sync()

    def _pull_status_from_cloud_api(self, request_id: str, auth_token: Optional[str] = None):
        """Pull verified OTP status and link from Railway Cloud API when polling on local desktop."""
        cloud_url = self._resolve_cloud_api_url()
        if not cloud_url or not auth_token or not request_id:
            return
        endpoint = f"{cloud_url}/api/telegram/link/status?request_id={request_id}"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json",
        }
        try:
            import urllib.request
            http_req = urllib.request.Request(endpoint, headers=headers, method="GET")
            with urllib.request.urlopen(http_req, timeout=3.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if not isinstance(data, dict) or not data.get("ok"):
                        return
                    remote_status = str(data.get("status") or "").strip().upper()
                    remote_attempts = int(data.get("attempt_count") or 0)
                    req = self._requests.get(request_id)
                    changed = False
                    if req:
                        if remote_attempts > req.attempt_count:
                            req.attempt_count = remote_attempts
                            changed = True
                        if req.status == "PENDING" and remote_status in ("VERIFIED", "EXPIRED", "FAILED"):
                            req.status = remote_status
                            if data.get("telegram_user_id"):
                                _, tg_uid = TelegramIdentity.validate_user_id(data.get("telegram_user_id"))
                                req.telegram_user_id = tg_uid
                            changed = True
                    link_data = data.get("link")
                    if isinstance(link_data, dict) and link_data.get("telegram_user_id") and link_data.get("misa_user_id"):
                        link_obj = UserTelegramLink.from_dict(link_data)
                        self._links_by_tg[link_obj.telegram_user_id] = link_obj
                        self._links_by_misa[link_obj.misa_user_id] = link_obj
                        changed = True
                    if changed:
                        self.save()
        except Exception as e:
            logger.debug(f"[TelegramIdentity] Cloud status pull o'tkazib yuborildi: {e}")

    def get_request(self, request_id: str, auth_token: Optional[str] = None, refresh: bool = False) -> Optional[TelegramLinkRequest]:
        req_id = str(request_id).strip()
        req = self._requests.get(req_id)
        if refresh or (req is None and (self._auto_supabase or auth_token)) or (req is not None and req.status == "PENDING" and (self._auto_supabase or auth_token)):
            effective_token = auth_token or (getattr(req, "_transient_auth_token", None) if req else None)
            self.load_requests_from_supabase(auth_token=effective_token, request_id=req_id)
            req = self._requests.get(req_id)
            if refresh and (req is None or req.status == "PENDING") and effective_token:
                self._pull_status_from_cloud_api(req_id, auth_token=effective_token)
                req = self._requests.get(req_id)
        return req

    def get_request_by_token(self, link_token: str, auth_token: Optional[str] = None) -> Optional[TelegramLinkRequest]:
        tok = str(link_token).strip()
        req = self._requests_by_token.get(tok)
        if req is None and (self._auto_supabase or auth_token):
            self.load_requests_from_supabase(auth_token=auth_token)
            req = self._requests_by_token.get(tok)
        return req

    @staticmethod
    def normalize_otp_input(raw_otp: Any) -> str:
        """Normalize user-entered OTP (strip spaces, hyphens, backticks, angle brackets)."""
        if raw_otp is None:
            return ""
        s = str(raw_otp).strip()
        if s.startswith("`") and s.endswith("`"):
            s = s.strip("`").strip()
        if s.startswith("<") and s.endswith(">"):
            s = s[1:-1].strip()
        # Allow "123 456" or "123-456" only if all parts are digits
        compact = s.replace(" ", "").replace("-", "")
        if compact.isdigit():
            return compact
        return s

    def verify_otp(
        self,
        otp: str,
        telegram_user_id: Any,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
        request_id: Optional[str] = None,
        current_time: Optional[float] = None,
        auth_token: Optional[str] = None,
        expected_misa_user_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[UserTelegramLink]]:
        """
        Verify candidate 6-digit OTP against pending request(s).
        Enforces single-use, TTL expiration, max 5 attempts lockout, ownership isolation, and constant-time match.
        """
        now = current_time if current_time is not None else time.time()
        is_valid_tg, tg_int = TelegramIdentity.validate_user_id(telegram_user_id)
        if not is_valid_tg or tg_int is None:
            return False, "INVALID_TELEGRAM_ID: Telegram ID musbat butun son bo'lishi shart", None

        candidate_otp = self.normalize_otp_input(otp)
        if not candidate_otp.isdigit() or len(candidate_otp) != 6:
            return False, "INVALID_FORMAT: OTP 6 xonali raqam bo'lishi shart", None

        # XAVFSIZLIK: Telegram user uchun brute-force himoyasi
        tg_failures = self._telegram_otp_failures.get(tg_int, [])
        # Eskirganlarni tozalash
        tg_failures = [t for t in tg_failures if t > now - self.TELEGRAM_OTP_FAILURE_WINDOW]
        self._telegram_otp_failures[tg_int] = tg_failures
        if len(tg_failures) >= self.MAX_TELEGRAM_OTP_FAILURES:
            return False, "RATE_LIMITED: Juda ko'p noto'g'ri urinishlar. 10 daqiqadan keyin qayta urinib ko'ring", None

        expected_uid = str(expected_misa_user_id).strip() if expected_misa_user_id else None

        # Resolve candidate request
        req: Optional[TelegramLinkRequest] = None
        if request_id:
            req_id_str = str(request_id).strip()
            req = self._requests.get(req_id_str)
            if not req and (self._auto_supabase or auth_token):
                self.load_requests_from_supabase(auth_token=auth_token, request_id=req_id_str)
                req = self._requests.get(req_id_str)
            if not req:
                return False, "REQUEST_NOT_FOUND: Bog'lanish so'rovi topilmadi", None
        else:
            def _find_matching_pending() -> Tuple[Optional[TelegramLinkRequest], List[TelegramLinkRequest]]:
                pending_list = [
                    r for r in self._requests.values()
                    if r.status == "PENDING" and (not r.is_expired(now)) and r.attempt_count < self.MAX_ATTEMPTS
                ]
                for r in sorted(pending_list, key=lambda x: x.created_at, reverse=True):
                    if self.verify_otp_hash(candidate_otp, r.salt, r.otp_hash):
                        return r, pending_list
                return None, pending_list

            req, matching_reqs = _find_matching_pending()
            # If not found locally in memory, pull latest pending requests from Supabase (Desktop <-> Railway sync)
            if not req and (self._auto_supabase or auth_token):
                self.load_requests_from_supabase(auth_token=auth_token)
                req, matching_reqs = _find_matching_pending()

            # If no pending match found, check any request matching OTP (e.g. verified, expired, failed)
            if not req:
                all_matching = [
                    r for r in self._requests.values()
                    if self.verify_otp_hash(candidate_otp, r.salt, r.otp_hash)
                ]
                if all_matching:
                    req = sorted(all_matching, key=lambda x: x.created_at, reverse=True)[0]
                elif matching_reqs:
                    if expected_uid:
                        user_pending = [r for r in matching_reqs if r.misa_user_id == expected_uid]
                        if user_pending:
                            req = sorted(user_pending, key=lambda x: x.created_at, reverse=True)[0]
                    else:
                        distinct_users = {r.misa_user_id for r in matching_reqs}
                        if len(distinct_users) == 1:
                            req = sorted(matching_reqs, key=lambda x: x.created_at, reverse=True)[0]

        if not req:
            # Noto'g'ri urinishni qayd qilish
            if tg_int not in self._telegram_otp_failures:
                self._telegram_otp_failures[tg_int] = []
            self._telegram_otp_failures[tg_int].append(now)
            return False, "INVALID_OR_EXPIRED_CODE: Bog'lanish kodi topilmadi yoki muddati tugagan", None

        effective_auth_token = auth_token or getattr(req, "_transient_auth_token", None)

        # Cross-user ownership enforcement (API caller vs request owner)
        if expected_uid and req.misa_user_id != expected_uid:
            self._audit.log(
                RemoteEventType.TELEGRAM_OTP_VERIFICATION_FAILED,
                request_id=req.request_id,
                user_id=expected_uid,
                telegram_user_id=str(tg_int),
                reason="USER_MISMATCH"
            )
            return False, "USER_MISMATCH: Ushbu tasdiqlash kodi boshqa foydalanuvchi hisobiga tegishli", None

        # Expected Telegram User ID enforcement (if request was bound to a specific Telegram ID)
        if req.expected_telegram_user_id is not None and req.expected_telegram_user_id != tg_int:
            self._audit.log(
                RemoteEventType.TELEGRAM_OTP_VERIFICATION_FAILED,
                request_id=req.request_id,
                user_id=req.misa_user_id,
                telegram_user_id=str(tg_int),
                reason="TELEGRAM_USER_MISMATCH"
            )
            return False, "TELEGRAM_USER_MISMATCH: Ushbu kod boshqa Telegram hisobi uchun mo'ljallangan", None

        # Check expiration
        if req.is_expired(now):
            req.status = "EXPIRED"
            self.save()
            self.sync_request_to_supabase(req, auth_token=effective_auth_token)
            req._transient_auth_token = None
            self._audit.log(
                RemoteEventType.TELEGRAM_LINK_EXPIRED,
                request_id=req.request_id,
                user_id=req.misa_user_id,
                telegram_user_id=str(tg_int)
            )
            return False, "CODE_EXPIRED: Tasdiqlash kodining muddati o'tgan (5 daqiqa)", None

        # Check status
        if req.status != "PENDING":
            if req.status == "VERIFIED":
                return False, "CODE_ALREADY_USED: Ushbu kod allaqachon ishlatilgan (Replay blocked)", None
            if req.status == "FAILED":
                return False, "MAX_ATTEMPTS_EXCEEDED: Ushbu so'rov bo'yicha urinishlar soni tugagan (5 ta)", None
            return False, f"REQUEST_INVALID: So'rov holati yaroqsiz: {req.status}", None

        # Check attempts
        if req.attempt_count >= self.MAX_ATTEMPTS:
            req.status = "FAILED"
            self.save()
            self.sync_request_to_supabase(req, auth_token=effective_auth_token)
            req._transient_auth_token = None
            return False, "MAX_ATTEMPTS_EXCEEDED: Maksimal 5 ta xato urinish qayd etildi", None

        # Constant-time comparison
        is_match = self.verify_otp_hash(candidate_otp, req.salt, req.otp_hash)
        if not is_match:
            if tg_int not in self._telegram_otp_failures:
                self._telegram_otp_failures[tg_int] = []
            self._telegram_otp_failures[tg_int].append(now)
            req.attempt_count += 1
            remaining = max(0, self.MAX_ATTEMPTS - req.attempt_count)
            if req.attempt_count >= self.MAX_ATTEMPTS:
                req.status = "FAILED"
            self.save()
            self.sync_request_to_supabase(req, auth_token=effective_auth_token)
            if req.status == "FAILED":
                req._transient_auth_token = None
            self._audit.log(
                RemoteEventType.TELEGRAM_OTP_VERIFICATION_FAILED,
                request_id=req.request_id,
                user_id=req.misa_user_id,
                telegram_user_id=str(tg_int),
                attempt_count=req.attempt_count,
                remaining_attempts=remaining
            )
            return False, f"INVALID_OTP: Kod noto'g'ri. Qolgan urinishlar soni: {remaining}", None

        # Prevent cross-user OTP hijacking if this Telegram ID is already actively linked to a DIFFERENT Misa user
        existing_tg_link = self.get_link_by_telegram_user(tg_int)
        if existing_tg_link and existing_tg_link.is_active and existing_tg_link.misa_user_id != req.misa_user_id:
            self._audit.log(
                RemoteEventType.TELEGRAM_OTP_VERIFICATION_FAILED,
                request_id=req.request_id,
                user_id=req.misa_user_id,
                telegram_user_id=str(tg_int),
                reason="TELEGRAM_ALREADY_LINKED"
            )
            return (
                False,
                "TELEGRAM_ALREADY_LINKED: Ushbu Telegram hisobi boshqa Misa hisobiga bog'langan. Avval /unlink buyrug'i orqali uzing",
                None
            )

        # Verification Success: mark single-use
        req.status = "VERIFIED"
        req.telegram_user_id = tg_int
        req.used_at = now
        if username:
            req.metadata["telegram_username"] = str(username)
        if first_name:
            req.metadata["telegram_first_name"] = str(first_name)

        # Revoke any prior active link for this Misa user or Telegram user (clean 1:1 mapping)
        self._revoke_existing_links(req.misa_user_id, tg_int)

        # Create active link
        meta = {}
        if username:
            meta["username"] = str(username)
        if first_name:
            meta["first_name"] = str(first_name)

        link = UserTelegramLink(
            misa_user_id=req.misa_user_id,
            telegram_user_id=tg_int,
            linked_at=now,
            last_verified_at=now,
            status="ACTIVE",
            metadata=meta
        )
        self._links_by_tg[tg_int] = link
        self._links_by_misa[req.misa_user_id] = link

        # Update or register Telegram Identity
        ident = self._identities.get(tg_int)
        if ident is None:
            ident = TelegramIdentity(
                telegram_user_id=tg_int,
                first_name=first_name,
                username=username,
                created_at=now,
                last_seen_at=now,
                is_verified=True,
                is_linked=True
            )
        else:
            ident.first_name = first_name or ident.first_name
            ident.username = username or ident.username
            ident.is_verified = True
            ident.is_linked = True
            ident.last_seen_at = now
        self._identities[tg_int] = ident

        self.save()
        self.sync_request_to_supabase(req, auth_token=effective_auth_token)
        self.sync_link_to_supabase(link, auth_token=effective_auth_token)
        req._transient_auth_token = None

        self._audit.log(
            RemoteEventType.TELEGRAM_OTP_VERIFICATION_SUCCESS,
            request_id=req.request_id,
            user_id=req.misa_user_id,
            telegram_user_id=str(tg_int)
        )
        self._audit.log(
            RemoteEventType.TELEGRAM_ACCOUNT_LINKED,
            request_id=req.request_id,
            user_id=req.misa_user_id,
            telegram_user_id=str(tg_int)
        )

        logger.info(f"[TelegramIdentity] Muvaffaqiyatli bog'landi: tg_id={tg_int} ↔ misa_user={req.misa_user_id}")
        return True, "OK: Misa hisobi Telegram bot bilan muvaffaqiyatli bog'landi", link

    def verify_link_token(
        self,
        link_token: str,
        telegram_user_id: Any,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
        current_time: Optional[float] = None,
        auth_token: Optional[str] = None,
        expected_misa_user_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[UserTelegramLink]]:
        """
        Verify deep-link token (e.g. from t.me/bot?start=<token>).
        Enforces single-use, TTL expiration, ownership isolation, and registers link.
        """
        now = current_time if current_time is not None else time.time()
        is_valid_tg, tg_int = TelegramIdentity.validate_user_id(telegram_user_id)
        if not is_valid_tg or tg_int is None:
            return False, "INVALID_TELEGRAM_ID: Telegram ID musbat butun son bo'lishi shart", None

        token_str = str(link_token).strip()
        req = self._requests_by_token.get(token_str)
        if not req and (self._auto_supabase or auth_token):
            self.load_requests_from_supabase(auth_token=auth_token)
            req = self._requests_by_token.get(token_str)
        if not req:
            return False, "INVALID_LINK_TOKEN: Havola yaroqsiz yoki topilmadi", None

        effective_auth_token = auth_token or getattr(req, "_transient_auth_token", None)

        expected_uid = str(expected_misa_user_id).strip() if expected_misa_user_id else None
        if expected_uid and req.misa_user_id != expected_uid:
            return False, "USER_MISMATCH: Ushbu havola boshqa foydalanuvchi hisobiga tegishli", None

        if req.expected_telegram_user_id is not None and req.expected_telegram_user_id != tg_int:
            return False, "TELEGRAM_USER_MISMATCH: Ushbu havola boshqa Telegram hisobi uchun mo'ljallangan", None

        if req.is_expired(now):
            req.status = "EXPIRED"
            self.save()
            self.sync_request_to_supabase(req, auth_token=effective_auth_token)
            req._transient_auth_token = None
            self._audit.log(
                RemoteEventType.TELEGRAM_LINK_EXPIRED,
                request_id=req.request_id,
                user_id=req.misa_user_id,
                telegram_user_id=str(tg_int)
            )
            return False, "CODE_EXPIRED: Havolaning muddati o'tgan (5 daqiqa)", None

        if req.status != "PENDING":
            if req.status == "VERIFIED":
                return False, "TOKEN_ALREADY_USED: Ushbu havola allaqachon ishlatilgan (Replay blocked)", None
            return False, f"TOKEN_INVALID: Havola holati yaroqsiz: {req.status}", None

        existing_tg_link = self.get_link_by_telegram_user(tg_int)
        if existing_tg_link and existing_tg_link.is_active and existing_tg_link.misa_user_id != req.misa_user_id:
            return (
                False,
                "TELEGRAM_ALREADY_LINKED: Ushbu Telegram hisobi boshqa Misa hisobiga bog'langan. Avval /unlink buyrug'i orqali uzing",
                None
            )

        # Verify success
        req.status = "VERIFIED"
        req.telegram_user_id = tg_int
        req.used_at = now
        if username:
            req.metadata["telegram_username"] = str(username)
        if first_name:
            req.metadata["telegram_first_name"] = str(first_name)

        self._revoke_existing_links(req.misa_user_id, tg_int)

        meta = {}
        if username:
            meta["username"] = str(username)
        if first_name:
            meta["first_name"] = str(first_name)

        link = UserTelegramLink(
            misa_user_id=req.misa_user_id,
            telegram_user_id=tg_int,
            linked_at=now,
            last_verified_at=now,
            status="ACTIVE",
            metadata=meta
        )
        self._links_by_tg[tg_int] = link
        self._links_by_misa[req.misa_user_id] = link

        ident = self._identities.get(tg_int)
        if ident is None:
            ident = TelegramIdentity(
                telegram_user_id=tg_int,
                first_name=first_name,
                username=username,
                created_at=now,
                last_seen_at=now,
                is_verified=True,
                is_linked=True
            )
        else:
            ident.first_name = first_name or ident.first_name
            ident.username = username or ident.username
            ident.is_verified = True
            ident.is_linked = True
            ident.last_seen_at = now
        self._identities[tg_int] = ident

        self.save()
        self.sync_request_to_supabase(req, auth_token=effective_auth_token)
        self.sync_link_to_supabase(link, auth_token=effective_auth_token)
        req._transient_auth_token = None

        self._audit.log(
            RemoteEventType.TELEGRAM_ACCOUNT_LINKED,
            request_id=req.request_id,
            user_id=req.misa_user_id,
            telegram_user_id=str(tg_int)
        )

        logger.info(f"[TelegramIdentity] Havola orqali muvaffaqiyatli bog'landi: tg_id={tg_int} ↔ user={req.misa_user_id}")
        return True, "OK: Misa hisobi havola orqali Telegram bot bilan muvaffaqiyatli bog'landi", link

    def _revoke_existing_links(self, misa_user_id: str, telegram_user_id: int):
        """Internal helper to clean up any prior active links for users being paired."""
        old_by_tg = self._links_by_tg.get(telegram_user_id)
        if old_by_tg and old_by_tg.is_active:
            old_by_tg.status = "REVOKED"
            if old_by_tg.misa_user_id in self._links_by_misa:
                del self._links_by_misa[old_by_tg.misa_user_id]

        old_by_misa = self._links_by_misa.get(misa_user_id)
        if old_by_misa and old_by_misa.is_active:
            old_by_misa.status = "REVOKED"
            if old_by_misa.telegram_user_id in self._links_by_tg:
                del self._links_by_tg[old_by_misa.telegram_user_id]

    def unlink(
        self,
        misa_user_id: Optional[str] = None,
        telegram_user_id: Optional[Any] = None,
        auth_token: Optional[str] = None
    ) -> bool:
        """
        Revoke active link relationship and cancel pending pairing requests.
        Can be invoked by Misa User ID or Telegram User ID.
        """
        link: Optional[UserTelegramLink] = None
        tg_int: Optional[int] = None
        if telegram_user_id is not None:
            _, tg_int = TelegramIdentity.validate_user_id(telegram_user_id)
            if tg_int:
                link = self._links_by_tg.get(tg_int)

        if not link and misa_user_id is not None:
            link = self._links_by_misa.get(str(misa_user_id))

        if not link and (self._auto_supabase or auth_token):
            self.load_from_supabase(auth_token=auth_token, user_id=str(misa_user_id) if misa_user_id else None)
            if tg_int:
                link = self._links_by_tg.get(tg_int)
            if not link and misa_user_id is not None:
                link = self._links_by_misa.get(str(misa_user_id))

        if link and link.is_active:
            tg_to_delete = link.telegram_user_id
            link.status = "REVOKED"
            if link.telegram_user_id in self._links_by_tg:
                del self._links_by_tg[link.telegram_user_id]
            if link.misa_user_id in self._links_by_misa:
                del self._links_by_misa[link.misa_user_id]

            # Update identity if present
            ident = self._identities.get(link.telegram_user_id)
            if ident:
                ident.is_linked = False

            # Cancel any pending requests for this user
            for r in self._requests.values():
                if r.misa_user_id == link.misa_user_id and r.status == "PENDING":
                    r.status = "EXPIRED"
                    self.sync_request_to_supabase(r, auth_token=auth_token)

            self.save()
            self.delete_link_from_supabase(tg_to_delete, auth_token=auth_token)

            self._audit.log(
                RemoteEventType.TELEGRAM_ACCOUNT_UNLINKED,
                user_id=link.misa_user_id,
                telegram_user_id=str(link.telegram_user_id)
            )
            logger.info(f"[TelegramIdentity] Bog'lanish bekor qilindi: tg={link.telegram_user_id}, misa={link.misa_user_id}")
            return True

        return False

    def get_link_by_misa_user(
        self,
        misa_user_id: str,
        auth_token: Optional[str] = None,
        refresh: bool = False
    ) -> Optional[UserTelegramLink]:
        uid = str(misa_user_id).strip()
        link = self._links_by_misa.get(uid)
        if (refresh or link is None) and (self._auto_supabase or auth_token):
            self.load_from_supabase(auth_token=auth_token, user_id=uid)
            link = self._links_by_misa.get(uid)
        return link if (link and link.is_active) else None

    def get_link_by_telegram_user(
        self,
        telegram_user_id: Any,
        auth_token: Optional[str] = None,
        refresh: bool = False
    ) -> Optional[UserTelegramLink]:
        _, tg_int = TelegramIdentity.validate_user_id(telegram_user_id)
        if not tg_int:
            return None
        link = self._links_by_tg.get(tg_int)
        if (refresh or link is None) and (self._auto_supabase or auth_token):
            self.load_from_supabase(auth_token=auth_token)
            link = self._links_by_tg.get(tg_int)
        return link if (link and link.is_active) else None

    def get_identity(self, telegram_user_id: Any) -> Optional[TelegramIdentity]:
        _, tg_int = TelegramIdentity.validate_user_id(telegram_user_id)
        if not tg_int:
            return None
        return self._identities.get(tg_int)

    def register_or_update_identity(
        self,
        telegram_user_id: Any,
        first_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> Optional[TelegramIdentity]:
        is_valid, tg_int = TelegramIdentity.validate_user_id(telegram_user_id)
        if not is_valid or tg_int is None:
            return None

        now = time.time()
        ident = self._identities.get(tg_int)
        link = self.get_link_by_telegram_user(tg_int)
        is_linked = link is not None and link.is_active

        if ident is None:
            ident = TelegramIdentity(
                telegram_user_id=tg_int,
                first_name=first_name,
                username=username,
                created_at=now,
                last_seen_at=now,
                is_verified=is_linked,
                is_linked=is_linked
            )
        else:
            if first_name:
                ident.first_name = first_name
            if username:
                ident.username = username
            ident.last_seen_at = now
            ident.is_linked = is_linked

        self._identities[tg_int] = ident
        return ident

    def list_active_links(self) -> List[UserTelegramLink]:
        return [lnk for lnk in self._links_by_tg.values() if lnk.is_active]

    def count_active_links(self) -> int:
        return len(self.list_active_links())

    def count_pending_requests(self, current_time: Optional[float] = None) -> int:
        now = current_time if current_time is not None else time.time()
        return sum(1 for r in self._requests.values() if r.status == "PENDING" and not r.is_expired(now))

    def cleanup_expired_requests(self, current_time: Optional[float] = None) -> int:
        now = current_time if current_time is not None else time.time()
        cleaned = 0
        for r in list(self._requests.values()):
            if r.status == "PENDING" and r.is_expired(now):
                r.status = "EXPIRED"
                cleaned += 1
        return cleaned

    def save(self):
        if not self.storage_path:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
            data = {
                "links": [lnk.to_dict() for lnk in self._links_by_tg.values()],
                "identities": [ident.to_dict() for ident in self._identities.values()],
                "requests": [req.to_dict() for req in self._requests.values()]
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[TelegramIdentity] Saqlashda xatolik: {e}")

    def load(self):
        if self.storage_path and os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                raw_links = data.get("links", [])
                for item in raw_links:
                    lnk = UserTelegramLink.from_dict(item)
                    if lnk.is_active:
                        self._links_by_tg[lnk.telegram_user_id] = lnk
                        self._links_by_misa[lnk.misa_user_id] = lnk

                raw_idents = data.get("identities", [])
                for item in raw_idents:
                    ident = TelegramIdentity.from_dict(item)
                    self._identities[ident.telegram_user_id] = ident

                raw_reqs = data.get("requests", [])
                for item in raw_reqs:
                    req = TelegramLinkRequest.from_dict(item)
                    self._requests[req.request_id] = req
                    if req.link_token:
                        self._requests_by_token[req.link_token] = req

                logger.info(f"[TelegramIdentity] Yuklandi: {len(self._links_by_tg)} ta faol link, {len(self._identities)} ta identity.")
            except Exception as e:
                logger.error(f"[TelegramIdentity] Yuklashda xatolik: {e}")

        if self._auto_supabase:
            self.load_from_supabase()
            self.load_requests_from_supabase()

    def _get_supabase_config(self) -> Tuple[str, str, str]:
        """Supabase ulanish ma'lumotlarini olish: (url, anon_key, secret_key)."""
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        anon = (
            os.environ.get("SUPABASE_PUBLISHABLE_KEY")
            or os.environ.get("SUPABASE_ANON_KEY", "")
        ).strip()
        secret = (
            os.environ.get("SUPABASE_SECRET_KEY")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        ).strip()
        return url, anon, secret

    def _build_supabase_headers(
        self,
        auth_token: Optional[str] = None,
        prefer: Optional[str] = None,
        content_type: Optional[str] = None,
        prefer_user_token: bool = False,
    ) -> Optional[Dict[str, str]]:
        """
        Supabase REST API uchun to'g'ri sarlavhalarni yaratish.
        MUHIM: Supabase yangi API key arxitekturasida (sb_publishable_... va sb_secret_...):
        - Agar `secret` (sb_secret_...) ishlatilsa, `apikey` va `Authorization: Bearer` IKKALASI HAM
          `secret` bo'lishi SHART! Aks holda (`apikey=sb_publishable_...`, `Authorization=Bearer sb_secret_...`)
          Supabase Gateway PGRST301 ('Expected 3 parts in JWT; got 1') 401 xatosini qaytaradi.
        - Agar foydalanuvchi JWT (`auth_token`, 3 qismli) ishlatilsa, `apikey` = `anon` (`sb_publishable_...`)
          va `Authorization` = `Bearer <auth_token>` bo'ladi.
        """
        url, anon, secret = self._get_supabase_config()
        if not url:
            return None

        clean_auth = str(auth_token or "").strip()
        is_user_jwt = clean_auth.count(".") == 2

        if prefer_user_token and is_user_jwt and (anon or secret):
            api_key = anon or secret
            bearer = clean_auth
        elif secret:
            api_key = secret
            bearer = secret
        elif is_user_jwt and anon:
            api_key = anon
            bearer = clean_auth
        elif anon:
            api_key = anon
            bearer = anon
        elif is_user_jwt:
            api_key = clean_auth
            bearer = clean_auth
        else:
            return None

        headers: Dict[str, str] = {
            "apikey": api_key,
            "Authorization": f"Bearer {bearer}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _ensure_supabase_profile(self, user_id: str, auth_token: Optional[str] = None) -> None:
        """Ensure public.profiles row exists for user_id to prevent 23503 FK errors on pairing/links."""
        url, _, _ = self._get_supabase_config()
        if not url:
            return
        headers = self._build_supabase_headers(
            auth_token=auth_token,
            prefer="resolution=ignore-duplicates",
            content_type="application/json",
        )
        if not headers:
            return
        uid_clean = str(user_id).strip()
        short_id = uid_clean.replace("-", "")[:8] or "user"
        payload = {
            "id": uid_clean,
            "username": f"user_{short_id}",
            "display_name": f"User {short_id}",
        }
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{url}/rest/v1/profiles?on_conflict=id",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3.5):
                pass
        except Exception:
            pass

    @staticmethod
    def _parse_iso_timestamp(val: Any, fallback: Optional[float] = None) -> Optional[float]:
        if val is None:
            return fallback
        if isinstance(val, (int, float)):
            return float(val)
        try:
            from datetime import datetime
            s = str(val).strip()
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s).timestamp()
        except Exception:
            return fallback

    def sync_request_to_supabase(self, req_obj: TelegramLinkRequest, auth_token: Optional[str] = None):
        """
        Telegram OTP bog'lanish so'rovini Supabase public.device_pairing_sessions jadvaliga sinxronlash.
        DIQQAT: Ochiq matnli OTP (plaintext_otp) hech qachon saqlanmaydi — faqat salted SHA-256 xesh saqlanadi.
        """
        url, _, _ = self._get_supabase_config()
        if not url:
            return

        uid_str = str(req_obj.misa_user_id).strip()
        req_id_str = str(req_obj.request_id).strip()
        try:
            uuid.UUID(uid_str)
            uuid.UUID(req_id_str)
        except (ValueError, AttributeError):
            logger.debug("[TelegramIdentity] user_id yoki request_id UUID emas, Supabase request sync o'tkazib yuborildi.")
            return

        headers = self._build_supabase_headers(
            auth_token=auth_token,
            prefer="resolution=merge-duplicates",
            content_type="application/json",
        )
        if not headers:
            return

        created_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(req_obj.created_at))
        expires_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(req_obj.expires_at))
        used_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(req_obj.used_at)) if req_obj.used_at else None

        payload = {
            "id": req_id_str,
            "user_id": uid_str,
            "pairing_code_hash": req_obj.otp_hash,
            "pairing_code_salt": req_obj.salt,
            "created_at": created_iso,
            "expires_at": expires_iso,
            "used_at": used_iso,
            "status": req_obj.status,
            "attempt_count": req_obj.attempt_count,
            "max_attempts": self.MAX_ATTEMPTS,
            "device_id": "telegram_otp",
            "request_metadata": {
                "link_token": req_obj.link_token,
                "telegram_user_id": req_obj.telegram_user_id,
                "expected_telegram_user_id": req_obj.expected_telegram_user_id,
                "created_at_epoch": req_obj.created_at,
                "expires_at_epoch": req_obj.expires_at,
                "used_at_epoch": req_obj.used_at,
            }
        }

        endpoint = f"{url}/rest/v1/device_pairing_sessions?on_conflict=id"
        payload_bytes = json.dumps(payload).encode("utf-8")

        try:
            import urllib.request
            import urllib.error
            http_req = urllib.request.Request(
                endpoint,
                data=payload_bytes,
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(http_req, timeout=4.0) as resp:
                    if resp.status in (200, 201, 204):
                        logger.info(f"[TelegramIdentity] Supabase device_pairing_sessions ga saqlandi: req={req_id_str}, status={req_obj.status}")
            except urllib.error.HTTPError as he:
                if he.code == 409:
                    # 23503 Foreign Key (profiles) ehtimoli — profilni yaratib qayta urinamiz
                    self._ensure_supabase_profile(uid_str, auth_token=auth_token)
                    retry_req = urllib.request.Request(endpoint, data=payload_bytes, headers=headers, method="POST")
                    with urllib.request.urlopen(retry_req, timeout=4.0) as resp:
                        if resp.status in (200, 201, 204):
                            logger.info(f"[TelegramIdentity] Supabase device_pairing_sessions ga (profile auto-heal bilan) saqlandi: req={req_id_str}")
                elif he.code in (401, 403) and auth_token:
                    alt_headers = self._build_supabase_headers(
                        auth_token=auth_token,
                        prefer="resolution=merge-duplicates",
                        content_type="application/json",
                        prefer_user_token=True,
                    )
                    if alt_headers and alt_headers != headers:
                        retry_req = urllib.request.Request(endpoint, data=payload_bytes, headers=alt_headers, method="POST")
                        with urllib.request.urlopen(retry_req, timeout=4.0) as resp:
                            if resp.status in (200, 201, 204):
                                logger.info(f"[TelegramIdentity] Supabase device_pairing_sessions ga user token bilan saqlandi: req={req_id_str}")
                else:
                    raise
        except Exception as e:
            logger.debug(f"[TelegramIdentity] Supabase request sync xatolik: {e}")

    def load_requests_from_supabase(
        self,
        auth_token: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Supabase public.device_pairing_sessions dan Telegram OTP so'rovlarini tortib olish."""
        url, _, _ = self._get_supabase_config()
        if not url:
            return

        headers = self._build_supabase_headers(auth_token=auth_token)
        if not headers:
            return

        query_parts = ["device_id=eq.telegram_otp", "select=*", "order=created_at.desc", "limit=50"]
        if request_id:
            try:
                uuid.UUID(str(request_id).strip())
                query_parts.append(f"id=eq.{str(request_id).strip()}")
            except (ValueError, AttributeError):
                return
        if user_id:
            try:
                uuid.UUID(str(user_id).strip())
                query_parts.append(f"user_id=eq.{str(user_id).strip()}")
            except (ValueError, AttributeError):
                pass

        endpoint = f"{url}/rest/v1/device_pairing_sessions?{'&'.join(query_parts)}"

        try:
            import urllib.request
            import urllib.error
            http_req = urllib.request.Request(endpoint, headers=headers, method="GET")
            raw_body = None
            try:
                with urllib.request.urlopen(http_req, timeout=4.0) as resp:
                    if resp.status == 200:
                        raw_body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as he:
                if he.code in (401, 403) and auth_token:
                    alt_headers = self._build_supabase_headers(auth_token=auth_token, prefer_user_token=True)
                    if alt_headers and alt_headers != headers:
                        retry_req = urllib.request.Request(endpoint, headers=alt_headers, method="GET")
                        with urllib.request.urlopen(retry_req, timeout=4.0) as resp:
                            if resp.status == 200:
                                raw_body = resp.read().decode("utf-8")
                else:
                    raise

            if raw_body is not None:
                rows = json.loads(raw_body)
                updated_any = False
                for row in rows:
                    req_id = str(row.get("id") or "").strip()
                    uid = str(row.get("user_id") or "").strip()
                    otp_hash = str(row.get("pairing_code_hash") or "").strip()
                    salt = str(row.get("pairing_code_salt") or "").strip()
                    if not req_id or not uid or not otp_hash or not salt:
                        continue

                    meta = row.get("request_metadata")
                    if not isinstance(meta, dict):
                        meta = {}

                    created_at = self._parse_iso_timestamp(
                        meta.get("created_at_epoch") or row.get("created_at"),
                        time.time()
                    ) or time.time()
                    expires_at = self._parse_iso_timestamp(
                        meta.get("expires_at_epoch") or row.get("expires_at"),
                        created_at + self.DEFAULT_TTL
                    ) or (created_at + self.DEFAULT_TTL)
                    used_at = self._parse_iso_timestamp(
                        meta.get("used_at_epoch") or row.get("used_at"),
                        None
                    )

                    link_token = str(meta.get("link_token") or "").strip()
                    tg_uid = meta.get("telegram_user_id")
                    if tg_uid is not None:
                        _, tg_uid = TelegramIdentity.validate_user_id(tg_uid)
                    exp_tg_uid = meta.get("expected_telegram_user_id")
                    if exp_tg_uid is not None:
                        _, exp_tg_uid = TelegramIdentity.validate_user_id(exp_tg_uid)

                    remote_status = str(row.get("status") or "PENDING").strip().upper()
                    remote_attempts = int(row.get("attempt_count") or 0)

                    existing = self._requests.get(req_id)
                    if existing is None:
                        new_req = TelegramLinkRequest(
                            request_id=req_id,
                            misa_user_id=uid,
                            otp_hash=otp_hash,
                            salt=salt,
                            created_at=created_at,
                            expires_at=expires_at,
                            status=remote_status,
                            attempt_count=remote_attempts,
                            telegram_user_id=tg_uid,
                            used_at=used_at,
                            link_token=link_token or secrets.token_urlsafe(24),
                            expected_telegram_user_id=exp_tg_uid
                        )
                        self._requests[req_id] = new_req
                        if new_req.link_token:
                            self._requests_by_token[new_req.link_token] = new_req
                        updated_any = True
                    else:
                        # Merge remote state if remote is terminal or has higher attempt count
                        if existing.status == "PENDING" and remote_status != "PENDING":
                            existing.status = remote_status
                            updated_any = True
                        if remote_attempts > existing.attempt_count:
                            existing.attempt_count = remote_attempts
                            updated_any = True
                        if tg_uid and not existing.telegram_user_id:
                            existing.telegram_user_id = tg_uid
                            updated_any = True
                        if used_at and not existing.used_at:
                            existing.used_at = used_at
                            updated_any = True
                        if link_token and link_token not in self._requests_by_token:
                            existing.link_token = link_token
                            self._requests_by_token[link_token] = existing

                if updated_any:
                    self.save()
        except Exception as e:
            logger.debug(f"[TelegramIdentity] Supabase dan so'rovlarni yuklashda xatolik: {e}")

    def sync_link_to_supabase(self, link: UserTelegramLink, auth_token: Optional[str] = None):
        """Telegram bog'lanishini Supabase public.telegram_links jadvaliga sinxronlash."""
        url, _, _ = self._get_supabase_config()
        if not url:
            return

        uid_str = str(link.misa_user_id).strip()
        try:
            uuid.UUID(uid_str)
        except (ValueError, AttributeError):
            logger.debug(f"[TelegramIdentity] misa_user_id '{uid_str}' UUID emas, Supabase sync o'tkazib yuborildi.")
            return

        headers = self._build_supabase_headers(
            auth_token=auth_token,
            prefer="resolution=merge-duplicates",
            content_type="application/json",
        )
        if not headers:
            return

        payload = {
            "user_id": uid_str,
            "telegram_user_id": link.telegram_user_id,
            "telegram_username": link.username or "",
            "first_name": link.first_name or "",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(link.last_verified_at))
        }

        endpoint = f"{url}/rest/v1/telegram_links?on_conflict=telegram_user_id"
        payload_bytes = json.dumps(payload).encode("utf-8")

        try:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(
                endpoint,
                data=payload_bytes,
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status in (200, 201, 204):
                        logger.info(f"[TelegramIdentity] Supabase public.telegram_links ga muvaffaqiyatli saqlandi: tg={link.telegram_user_id} -> user={uid_str}")
            except urllib.error.HTTPError as he:
                if he.code == 409:
                    self._ensure_supabase_profile(uid_str, auth_token=auth_token)
                    retry_req = urllib.request.Request(endpoint, data=payload_bytes, headers=headers, method="POST")
                    with urllib.request.urlopen(retry_req, timeout=5.0) as resp:
                        if resp.status in (200, 201, 204):
                            logger.info(f"[TelegramIdentity] Supabase public.telegram_links ga (profile auto-heal bilan) saqlandi: tg={link.telegram_user_id}")
                elif he.code in (401, 403) and auth_token:
                    alt_headers = self._build_supabase_headers(
                        auth_token=auth_token,
                        prefer="resolution=merge-duplicates",
                        content_type="application/json",
                        prefer_user_token=True,
                    )
                    if alt_headers and alt_headers != headers:
                        retry_req = urllib.request.Request(endpoint, data=payload_bytes, headers=alt_headers, method="POST")
                        with urllib.request.urlopen(retry_req, timeout=5.0) as resp:
                            if resp.status in (200, 201, 204):
                                logger.info(f"[TelegramIdentity] Supabase public.telegram_links ga user token bilan saqlandi: tg={link.telegram_user_id}")
                else:
                    raise
        except Exception as e:
            logger.warning(f"[TelegramIdentity] Supabase ga sinxronlashda xatolik: {e}")

    def delete_link_from_supabase(self, telegram_user_id: int, auth_token: Optional[str] = None):
        """Telegram bog'lanishini Supabase public.telegram_links jadvalidan o'chirish."""
        url, _, _ = self._get_supabase_config()
        if not url:
            return

        headers = self._build_supabase_headers(auth_token=auth_token)
        if not headers:
            return

        endpoint = f"{url}/rest/v1/telegram_links?telegram_user_id=eq.{telegram_user_id}"

        try:
            import urllib.request
            req = urllib.request.Request(endpoint, headers=headers, method="DELETE")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status in (200, 204):
                    logger.info(f"[TelegramIdentity] Supabase public.telegram_links dan o'chirildi: tg={telegram_user_id}")
        except Exception as e:
            logger.warning(f"[TelegramIdentity] Supabase dan o'chirishda xatolik: {e}")

    def load_from_supabase(self, auth_token: Optional[str] = None, user_id: Optional[str] = None):
        """Server yuklanganda yoki so'rov bo'yicha Supabase dan mavjud telegram_links ni tortib olish."""
        url, _, _ = self._get_supabase_config()
        if not url:
            return

        headers = self._build_supabase_headers(auth_token=auth_token)
        if not headers:
            return

        query = "select=*"
        if user_id:
            try:
                uuid.UUID(str(user_id).strip())
                query += f"&user_id=eq.{str(user_id).strip()}"
            except (ValueError, AttributeError):
                pass

        endpoint = f"{url}/rest/v1/telegram_links?{query}"

        try:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(endpoint, headers=headers, method="GET")
            raw_body = None
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        raw_body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as he:
                if he.code in (401, 403) and auth_token:
                    alt_headers = self._build_supabase_headers(auth_token=auth_token, prefer_user_token=True)
                    if alt_headers and alt_headers != headers:
                        retry_req = urllib.request.Request(endpoint, headers=alt_headers, method="GET")
                        with urllib.request.urlopen(retry_req, timeout=5.0) as resp:
                            if resp.status == 200:
                                raw_body = resp.read().decode("utf-8")
                else:
                    raise

            if raw_body is not None:
                rows = json.loads(raw_body)
                count = 0
                for row in rows:
                    tg_id = int(row.get("telegram_user_id"))
                    row_user_id = str(row.get("user_id"))
                    username = row.get("telegram_username")
                    first_name = row.get("first_name")

                    meta = {}
                    if username:
                        meta["username"] = username
                    if first_name:
                        meta["first_name"] = first_name

                    linked_ts = self._parse_iso_timestamp(row.get("created_at"), time.time()) or time.time()
                    verified_ts = self._parse_iso_timestamp(row.get("updated_at"), linked_ts) or linked_ts

                    link = UserTelegramLink(
                        misa_user_id=row_user_id,
                        telegram_user_id=tg_id,
                        linked_at=linked_ts,
                        last_verified_at=verified_ts,
                        status="ACTIVE",
                        metadata=meta
                    )
                    self._links_by_tg[tg_id] = link
                    self._links_by_misa[row_user_id] = link

                    ident = TelegramIdentity(
                        telegram_user_id=tg_id,
                        first_name=first_name,
                        username=username,
                        created_at=linked_ts,
                        last_seen_at=verified_ts,
                        is_verified=True,
                        is_linked=True
                    )
                    self._identities[tg_id] = ident
                    count += 1
                if count > 0:
                    self.save()
                    logger.info(f"[TelegramIdentity] Supabase dan {count} ta telegram link yuklandi.")
        except Exception as e:
            logger.debug(f"[TelegramIdentity] Supabase dan yuklashda xatolik (offline yoki kalit cheklovi): {e}")


