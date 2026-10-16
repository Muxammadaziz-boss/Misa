# ========== core/v8/events.py ==========
# Phase 36 — Remote Audit & Structured Event Logging
# Safe, Correlated & Sensitive-Data Redacted

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger("core.v8.audit")


class RemoteEventType(str, Enum):
    REMOTE_REQUEST_RECEIVED = "REMOTE_REQUEST_RECEIVED"
    REMOTE_REQUEST_AUTHORIZED = "REMOTE_REQUEST_AUTHORIZED"
    REMOTE_REQUEST_DENIED = "REMOTE_REQUEST_DENIED"
    DEVICE_REGISTERED = "DEVICE_REGISTERED"
    DEVICE_AUTH_FAILED = "DEVICE_AUTH_FAILED"
    WOL_REQUESTED = "WOL_REQUESTED"
    WOL_SENT = "WOL_SENT"
    WOL_FAILED = "WOL_FAILED"
    DEVICE_WAKING = "DEVICE_WAKING"
    DEVICE_ONLINE = "DEVICE_ONLINE"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    COMMAND_STARTED = "COMMAND_STARTED"
    COMMAND_COMPLETED = "COMMAND_COMPLETED"
    COMMAND_FAILED = "COMMAND_FAILED"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    AGENT_CONNECTED = "AGENT_CONNECTED"
    AGENT_DISCONNECTED = "AGENT_DISCONNECTED"
    # Phase 37 — Session Authentication & Cooldown Events
    AUTH_CHALLENGE_ISSUED = "AUTH_CHALLENGE_ISSUED"
    AUTH_ATTEMPT_SUCCESS = "AUTH_ATTEMPT_SUCCESS"
    AUTH_ATTEMPT_FAILED = "AUTH_ATTEMPT_FAILED"
    AUTH_COOLDOWN_ACTIVATED = "AUTH_COOLDOWN_ACTIVATED"
    SESSION_OPENED = "SESSION_OPENED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SESSION_CLOSED = "SESSION_CLOSED"
    # Phase 38 — User Linking & Permission Center Events
    ACCOUNT_LINKED = "ACCOUNT_LINKED"
    ACCOUNT_UNLINKED = "ACCOUNT_UNLINKED"
    DEVICE_PAIRED = "DEVICE_PAIRED"
    DEVICE_UNPAIRED = "DEVICE_UNPAIRED"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_REVOKED = "PERMISSION_REVOKED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    COMMAND_RECEIVED = "COMMAND_RECEIVED"
    COMMAND_AUTHORIZED = "COMMAND_AUTHORIZED"
    COMMAND_DENIED = "COMMAND_DENIED"
    COMMAND_EXECUTED = "COMMAND_EXECUTED"
    # Phase 39 — Universal Telegram Bot ↔ Misa User Account Linking Events
    TELEGRAM_LINK_REQUEST_CREATED = "TELEGRAM_LINK_REQUEST_CREATED"
    TELEGRAM_OTP_VERIFICATION_SUCCESS = "TELEGRAM_OTP_VERIFICATION_SUCCESS"
    TELEGRAM_OTP_VERIFICATION_FAILED = "TELEGRAM_OTP_VERIFICATION_FAILED"
    TELEGRAM_ACCOUNT_LINKED = "TELEGRAM_ACCOUNT_LINKED"
    TELEGRAM_ACCOUNT_UNLINKED = "TELEGRAM_ACCOUNT_UNLINKED"
    TELEGRAM_LINK_EXPIRED = "TELEGRAM_LINK_EXPIRED"
    TELEGRAM_LINK_RATE_LIMITED = "TELEGRAM_LINK_RATE_LIMITED"
    # Phase 40 — Universal Account & Multi-Device Management Events
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    ACCOUNT_UPDATED = "ACCOUNT_UPDATED"
    TELEGRAM_LINKED = "TELEGRAM_LINKED"
    TELEGRAM_UNLINKED = "TELEGRAM_UNLINKED"
    DEVICE_ADDED = "DEVICE_ADDED"
    DEVICE_RENAMED = "DEVICE_RENAMED"
    DEVICE_SELECTED = "DEVICE_SELECTED"
    DEVICE_REVOKED = "DEVICE_REVOKED"
    SESSION_CREATED = "SESSION_CREATED"
    SESSION_LOCKED = "SESSION_LOCKED"
    SESSION_LOGOUT = "SESSION_LOGOUT"
    SESSION_EXPIRED_P40 = "SESSION_EXPIRED"
    # Phase 41 — Account Registration & Authentication Events
    ACCOUNT_REGISTERED = "ACCOUNT_REGISTERED"
    ACCOUNT_LOGIN_SUCCESS = "ACCOUNT_LOGIN_SUCCESS"
    ACCOUNT_LOGIN_FAILED = "ACCOUNT_LOGIN_FAILED"
    ACCOUNT_LOGOUT = "ACCOUNT_LOGOUT"
    ACCOUNT_LOGOUT_ALL = "ACCOUNT_LOGOUT_ALL"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
    EMAIL_VERIFICATION_REQUESTED = "EMAIL_VERIFICATION_REQUESTED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    SESSION_REVOKED = "SESSION_REVOKED"
    # Phase 42 — Secure PC Agent Enrollment & Pairing Events
    DEVICE_PAIRING_STARTED = "DEVICE_PAIRING_STARTED"
    DEVICE_PAIRING_FAILED = "DEVICE_PAIRING_FAILED"
    DEVICE_PAIRING_EXPIRED = "DEVICE_PAIRING_EXPIRED"
    DEVICE_PAIRING_COMPLETED = "DEVICE_PAIRING_COMPLETED"
    DEVICE_ENROLLED = "DEVICE_ENROLLED"
    DEVICE_CREDENTIAL_CREATED = "DEVICE_CREDENTIAL_CREATED"
    DEVICE_AUTH_SUCCESS = "DEVICE_AUTH_SUCCESS"
    DEVICE_REENROLLED = "DEVICE_REENROLLED"
    # Phase 44 — Google OAuth & Account Linking Events
    OAUTH_STARTED = "OAUTH_STARTED"
    OAUTH_COMPLETED = "OAUTH_COMPLETED"
    OAUTH_FAILED = "OAUTH_FAILED"
    GOOGLE_LINK_STARTED = "GOOGLE_LINK_STARTED"
    GOOGLE_LINK_COMPLETED = "GOOGLE_LINK_COMPLETED"
    GOOGLE_LINK_FAILED = "GOOGLE_LINK_FAILED"
    GOOGLE_UNLINKED = "GOOGLE_UNLINKED"
    # Phase 45 — Real Windows PC Agent Lifecycle Events
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_STOPPING = "AGENT_STOPPING"
    AGENT_STOPPED = "AGENT_STOPPED"
    ENROLLMENT_STARTED = "ENROLLMENT_STARTED"
    ENROLLMENT_COMPLETED = "ENROLLMENT_COMPLETED"
    ENROLLMENT_FAILED = "ENROLLMENT_FAILED"
    AUTH_STARTED = "AUTH_STARTED"
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILED = "AUTH_FAILED"
    HEARTBEAT_SENT = "HEARTBEAT_SENT"
    HEARTBEAT_FAILED = "HEARTBEAT_FAILED"
    RECONNECT_STARTED = "RECONNECT_STARTED"
    RECONNECT_SUCCESS = "RECONNECT_SUCCESS"
    RECONNECT_FAILED = "RECONNECT_FAILED"
    CREDENTIAL_LOADED = "CREDENTIAL_LOADED"
    CREDENTIAL_REVOKED = "CREDENTIAL_REVOKED"
    CRASH_RECOVERY = "CRASH_RECOVERY"
    # Phase 46 — Real Remote Tool Execution Events
    REMOTE_COMMAND_SUBMITTED = "REMOTE_COMMAND_SUBMITTED"
    REMOTE_COMMAND_DISPATCHED = "REMOTE_COMMAND_DISPATCHED"
    REMOTE_COMMAND_CONFIRMED = "REMOTE_COMMAND_CONFIRMED"
    REMOTE_COMMAND_REJECTED = "REMOTE_COMMAND_REJECTED"
    REMOTE_COMMAND_SUCCEEDED = "REMOTE_COMMAND_SUCCEEDED"
    REMOTE_COMMAND_FAILED = "REMOTE_COMMAND_FAILED"
    REMOTE_COMMAND_TIMEOUT = "REMOTE_COMMAND_TIMEOUT"
    REMOTE_COMMAND_EXPIRED = "REMOTE_COMMAND_EXPIRED"
    REMOTE_COMMAND_CANCELLED = "REMOTE_COMMAND_CANCELLED"
    REMOTE_COMMAND_REPLAY_BLOCKED = "REMOTE_COMMAND_REPLAY_BLOCKED"
    REMOTE_CONFIRMATION_REQUESTED = "REMOTE_CONFIRMATION_REQUESTED"
    REMOTE_CONFIRMATION_ACCEPTED = "REMOTE_CONFIRMATION_ACCEPTED"
    REMOTE_CONFIRMATION_EXPIRED = "REMOTE_CONFIRMATION_EXPIRED"
    REMOTE_PERMISSION_DENIED = "REMOTE_PERMISSION_DENIED"
    # Phase 47 — Full Agent Access & User Consent Events
    FULL_ACCESS_WARNING_SHOWN = "FULL_ACCESS_WARNING_SHOWN"
    FULL_ACCESS_WARNING_ACKNOWLEDGED = "FULL_ACCESS_WARNING_ACKNOWLEDGED"
    FULL_ACCESS_REAUTH_PASSED = "FULL_ACCESS_REAUTH_PASSED"
    FULL_ACCESS_REAUTH_FAILED = "FULL_ACCESS_REAUTH_FAILED"
    FULL_ACCESS_ENABLED = "FULL_ACCESS_ENABLED"
    FULL_ACCESS_DISABLED = "FULL_ACCESS_DISABLED"
    FULL_ACCESS_CROSS_TENANT_BLOCKED = "FULL_ACCESS_CROSS_TENANT_BLOCKED"
    FULL_ACCESS_PERMISSION_OVERRIDE = "FULL_ACCESS_PERMISSION_OVERRIDE"
    FULL_ACCESS_EMERGENCY_REVOKE = "FULL_ACCESS_EMERGENCY_REVOKE"
    FULL_ACCESS_DEVICE_SCOPE_VIOLATION = "FULL_ACCESS_DEVICE_SCOPE_VIOLATION"


def sanitize_sensitive_string(val: str) -> str:
    """Telegram token, API kalitlar va parollarni xavfsiz niqoblash"""
    if not isinstance(val, str):
        return str(val)
    # Telegram bot token regex-like match: 123456789:ABCdef...
    if ":" in val and len(val) > 20:
        parts = val.split(":")
        if parts[0].isdigit():
            return f"{parts[0]}:***MASKED_TELEGRAM_TOKEN***"
    if val.startswith("sk-") or val.startswith("AIza") or len(val) >= 32:
        return f"{val[:4]}***MASKED_SECRET***{val[-3:] if len(val) > 8 else ''}"
    return val


def sanitize_event_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Tadbir parametrlari ichidagi maxfiy ma'lumotlarni tozalash"""
    cleaned = {}
    sensitive_keys = {
        "token", "bot_token", "password", "secret", "pairing_token",
        "auth_header", "pin", "auth_code", "session_token",
        "pairing_code", "raw_code", "code", "pairing_secret", "raw_file_content",
        "private_key", "device_private_key", "raw_nonce", "raw_credential",
        "challenge_nonce", "keypair", "device_session_token",
        "secret_hash", "otp", "otp_hash", "link_token",
        "password_confirmation", "raw_password", "current_password",
        "new_password", "new_password_confirmation", "raw_token",
        "raw_otp", "reset_token", "verification_token", "password_hash",
        "token_hash", "access_token", "refresh_token", "authorization_code",
        "client_secret", "google_token", "id_token", "authorization_header",
        "session_secret",
        "reauth_proof", "confirmation_token", "warning_token"
    }
    for k, v in data.items():
        if k.lower() in sensitive_keys:
            cleaned[k] = "***REDACTED***"
        elif isinstance(v, str):
            cleaned[k] = sanitize_sensitive_string(v)
        elif isinstance(v, dict):
            cleaned[k] = sanitize_event_data(v)
        else:
            cleaned[k] = v
    return cleaned


@dataclass
class RemoteAuditEvent:
    event_type: RemoteEventType
    request_id: Optional[str] = None
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # Contract-compliant status resolution (never undefined)
        status_val = str(self.details.get("status") or "").strip().lower()
        if not status_val:
            ev_upper = self.event_type.value.upper()
            if any(w in ev_upper for w in ("DENIED", "FAILED", "REJECTED", "BLOCKED", "TIMEOUT", "EXPIRED", "REVOKED", "VIOLATION", "ERROR")):
                status_val = "denied" if "DENIED" in ev_upper else "failed"
            elif any(w in ev_upper for w in ("SUCCESS", "AUTHORIZED", "COMPLETED", "ENABLED", "PASSED", "ONLINE")):
                status_val = "authorized" if "AUTHORIZED" in ev_upper else "success"
            else:
                status_val = "info"

        event_uid = self.request_id or f"evt_{int(self.timestamp * 1000)}"
        return {
            "event_id": event_uid,
            "id": event_uid,
            "event_type": self.event_type.value,
            "action": str(self.details.get("action") or self.event_type.value),
            "status": status_val,
            "request_id": self.request_id,
            "device_id": self.device_id,
            "user_id": self.user_id,
            "telegram_user_id": str(self.details.get("telegram_user_id") or self.user_id or ""),
            "timestamp": self.timestamp,
            "details": sanitize_event_data(self.details)
        }


class RemoteAuditLogger:
    """
    Tizimdagi barcha masofaviy amallar auditi.
    Xotirada keshlaydi, loglarga yozadi va xavfsiz formatlaydi.
    """
    _instance: Optional["RemoteAuditLogger"] = None

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._history: List[RemoteAuditEvent] = []
        self._subscribers: List[Callable[[RemoteAuditEvent], None]] = []

    @classmethod
    def get_instance(cls) -> "RemoteAuditLogger":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def log(
        self,
        event_type: RemoteEventType,
        request_id: Optional[str] = None,
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **details
    ) -> RemoteAuditEvent:
        clean_details = sanitize_event_data(details)
        event = RemoteAuditEvent(
            event_type=event_type,
            request_id=request_id,
            device_id=device_id,
            user_id=user_id,
            timestamp=time.time(),
            details=clean_details
        )
        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history.pop(0)

        log_msg = (
            f"[V8_AUDIT] {event_type.value} | req={request_id or '-'} | "
            f"dev={device_id or '-'} | user={user_id or '-'} | {clean_details}"
        )
        warning_events = (
            RemoteEventType.REMOTE_REQUEST_DENIED,
            RemoteEventType.DEVICE_AUTH_FAILED,
            RemoteEventType.COMMAND_FAILED,
            RemoteEventType.WOL_FAILED,
            RemoteEventType.AUTH_ATTEMPT_FAILED,
            RemoteEventType.AUTH_COOLDOWN_ACTIVATED,
            RemoteEventType.TELEGRAM_OTP_VERIFICATION_FAILED,
            RemoteEventType.TELEGRAM_LINK_RATE_LIMITED,
            RemoteEventType.TELEGRAM_LINK_EXPIRED
        )
        if event_type in warning_events:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        for sub in self._subscribers:
            try:
                sub(event)
            except Exception as e:
                logger.error(f"Audit subscriber error: {e}")

        return event

    def log_event(self, event: RemoteAuditEvent) -> RemoteAuditEvent:
        """RemoteAuditEvent obyektini to'g'ridan-to'g'ri qayd qilish"""
        details = dict(event.details)
        dev_id = details.pop("device_id", event.device_id)
        req_id = details.pop("request_id", event.request_id)
        u_id = details.pop("user_id", event.user_id)
        ev_type = details.pop("event_type", event.event_type)
        return self.log(
            event_type=ev_type,
            request_id=req_id,
            device_id=dev_id,
            user_id=u_id,
            **details
        )

    def get_history(
        self,
        event_type: Optional[RemoteEventType] = None,
        device_id: Optional[str] = None,
        limit: int = 50
    ) -> List[RemoteAuditEvent]:
        res = self._history
        if event_type:
            res = [e for e in res if e.event_type == event_type]
        if device_id:
            res = [e for e in res if e.device_id == device_id]
        return res[-limit:]

    def subscribe(self, subscriber: Callable[[RemoteAuditEvent], None]):
        self._subscribers.append(subscriber)

    def clear(self):
        self._history.clear()
