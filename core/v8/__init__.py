# ========== core/v8/__init__.py ==========
# Misa AI v9.0.0 — Phase 38: Misa Online Remote Control + User Permission Center
# Package initialization, versioning & exports

from core.v8.device import (
    DeviceIdentity,
    DeviceIdentityManager,
    DevicePairingRecord,
    DeviceRegistry
)
from core.v8.heartbeat import DeviceState, HeartbeatPayload, HeartbeatManager
from core.v8.wol import (
    WakeOnLanManager,
    create_magic_packet,
    WakeRelay,
    LocalBroadcastRelay
)
from core.v8.envelope import (
    RemoteCommandEnvelope,
    EnvelopeManager,
    RateLimiter
)
from core.v8.pc_agent import MisaPCAgent
from core.v8.telegram_gateway import (
    TelegramRemoteGateway,
    TelegramTransport,
    MockTelegramTransport,
    AiohttpTelegramTransport
)
from core.v8.auth_session import (
    RemoteAuthSession,
    SessionManager,
    RemoteAuthEngine
)
from core.v8.user_linking import (
    PairingToken,
    UserDeviceLink,
    UserLinkingStore
)
from core.v8.telegram_identity import (
    TelegramIdentity,
    TelegramLinkRequest,
    UserTelegramLink,
    TelegramIdentityManager
)
from core.v8.universal_bot import UniversalTelegramBot
from core.v8.account_device import (
    MisaUser,
    Device,
    UserDeviceLink as AccountUserDeviceLink,
    UserDeviceContext,
    AccountDeviceManager
)
from core.v8.account_auth import (
    SupabaseAuthManager,
    AccountAuthManager,
    SupabaseSessionClaims,
    AccountSession,
    AuthRateLimiter
)
from core.v8.permission_center import (
    PermissionCategory,
    PermissionDefinition,
    UserPermissionProfile,
    PermissionStore,
    STANDARD_PERMISSIONS
)
from core.v8.remote_tools import (
    RemoteToolDefinition,
    RemoteToolRegistry
)
from core.v8.remote_orchestrator import (
    RemoteOrchestrator,
    create_remote_wake_and_verify_dag
)
from core.v8.device_pairing import (
    DevicePairingSession,
    DevicePairingManager
)
from core.v8.device_enrollment import (
    DeviceCredential,
    SecureCredentialStore,
    WindowsCredentialStore,
    MockCredentialStore,
    DeviceEnrollmentManager
)
from core.v8.device_auth import (
    DeviceAuthChallenge,
    DeviceSession,
    DeviceAuthManager
)
from core.v8.device_agent_crypto import DeviceAgentCrypto
from core.v8.events import (
    RemoteEventType,
    RemoteAuditLogger,
    RemoteAuditEvent,
    sanitize_sensitive_string,
    sanitize_event_data
)
from core.v8.agent_access import (
    AccessLevel,
    AgentAccessGrant,
    AgentAccessManager,
    FULL_ACCESS_SECURITY_WARNING_TEXT,
    DEFAULT_POLICY_VERSION
)
from core.v8.update_service import (
    UpdateService,
    UpdateCrypto,
    SemVer,
    UpdateState,
    UpdateManifest,
    UpdateArtifact,
    UpdateStateManager,
    get_update_service,
    DEFAULT_TRUSTED_PUBLIC_KEY
)

__version__ = "9.2.0"
PHASE = 48

__all__ = [
    "__version__",
    "PHASE",
    # Phase 48 — Secure Auto Update & Release System
    "UpdateService",
    "UpdateCrypto",
    "SemVer",
    "UpdateState",
    "UpdateManifest",
    "UpdateArtifact",
    "UpdateStateManager",
    "get_update_service",
    "DEFAULT_TRUSTED_PUBLIC_KEY",
    # Account & Auth (Phase 41 - Supabase Auth)
    "SupabaseAuthManager",
    "AccountAuthManager",
    "SupabaseSessionClaims",
    "AccountSession",
    "AuthRateLimiter",
    # Device & Accounts (Phase 40)
    "MisaUser",
    "Device",
    "AccountDeviceManager",
    "UserDeviceContext",
    # Device (Phase 35)
    "DeviceIdentity",
    "DeviceIdentityManager",
    "DevicePairingRecord",
    "DeviceRegistry",
    # Heartbeat
    "DeviceState",
    "HeartbeatPayload",
    "HeartbeatManager",
    # Wake-on-LAN
    "WakeOnLanManager",
    "create_magic_packet",
    "WakeRelay",
    "LocalBroadcastRelay",
    # Envelope & Security
    "RemoteCommandEnvelope",
    "EnvelopeManager",
    "RateLimiter",
    # Agent & Gateway
    "MisaPCAgent",
    "TelegramRemoteGateway",
    "TelegramTransport",
    "MockTelegramTransport",
    "AiohttpTelegramTransport",
    # Session & Authentication
    "RemoteAuthSession",
    "SessionManager",
    "RemoteAuthEngine",
    # User Linking & Permission Center (Phase 38)
    "TelegramIdentity",
    "PairingToken",
    "UserDeviceLink",
    "UserLinkingStore",
    "PermissionCategory",
    "PermissionDefinition",
    "UserPermissionProfile",
    "PermissionStore",
    "STANDARD_PERMISSIONS",
    # Universal Telegram Bot & Identity (Phase 39)
    "TelegramLinkRequest",
    "UserTelegramLink",
    "TelegramIdentityManager",
    "UniversalTelegramBot",
    # Remote Tools (Phase 38)
    "RemoteToolDefinition",
    "RemoteToolRegistry",
    # Orchestrator & DAG
    "RemoteOrchestrator",
    "create_remote_wake_and_verify_dag",
    # Audit & Events
    "RemoteEventType",
    "RemoteAuditLogger",
    "RemoteAuditEvent",
    "sanitize_sensitive_string",
    "sanitize_event_data",
    # PC Agent Enrollment & Pairing (Phase 42)
    "DevicePairingSession",
    "DevicePairingManager",
    "DeviceCredential",
    "SecureCredentialStore",
    "WindowsCredentialStore",
    "MockCredentialStore",
    "DeviceEnrollmentManager",
    "DeviceAuthChallenge",
    "DeviceSession",
    "DeviceAuthManager",
    "DeviceAgentCrypto",
    # Phase 47 — Full Agent Access & User Consent
    "AccessLevel",
    "AgentAccessGrant",
    "AgentAccessManager",
    "FULL_ACCESS_SECURITY_WARNING_TEXT",
    "DEFAULT_POLICY_VERSION",
]
