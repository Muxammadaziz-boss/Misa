# ========== core/v8/update_service.py ==========
# Misa AI v8.0.0 — Phase 48: Secure Auto Update & Release System
# Fail-closed, cryptographically signed (Ed25519 + SHA-256), crash-safe,
# atomic staging and rollback update engine for Windows Desktop.

import os
import re
import sys
import time
import json
import shutil
import hashlib
import logging
import asyncio
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Callable, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger("core.v8.update_service")

# Default official Misa Update Authority Public Key (Ed25519 - 64 hex chars)
# Private key is NEVER stored in repository or client bundle.
DEFAULT_TRUSTED_PUBLIC_KEY = "b4be839fd62657c0e786e1a2ad590c05c45c511371d041137c5ca9ac57c29829"

# Default update repository / manifest endpoints
DEFAULT_GITHUB_OWNER = "Muxammadaziz-boss"
DEFAULT_GITHUB_REPO = "Misa"
DEFAULT_MANIFEST_URL = f"https://raw.githubusercontent.com/{DEFAULT_GITHUB_OWNER}/{DEFAULT_GITHUB_REPO}/main/release/v9.0.2/version_manifest.json"

# Auto-check minimum interval: 6 hours (21600 seconds)
MIN_AUTO_CHECK_INTERVAL_SEC = 6 * 3600

# Max allowed manifest JSON size: 2 MB
MAX_MANIFEST_BYTES = 2 * 1024 * 1024


class UpdateState(str, Enum):
    IDLE = "IDLE"
    CHECKING = "CHECKING"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    UP_TO_DATE = "UP_TO_DATE"
    DOWNLOADING = "DOWNLOADING"
    VERIFYING = "VERIFYING"
    STAGING = "STAGING"
    INSTALLING = "INSTALLING"
    RESTARTING = "RESTARTING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLED_BACK = "ROLLED_BACK"


# Strict State Machine Valid Transitions
_VALID_TRANSITIONS: Dict[UpdateState, List[UpdateState]] = {
    UpdateState.IDLE: [
        UpdateState.CHECKING,
        UpdateState.UPDATE_AVAILABLE,
        UpdateState.UP_TO_DATE,
        UpdateState.DOWNLOADING,
        UpdateState.STAGING,
        UpdateState.INSTALLING,
        UpdateState.ROLLED_BACK,
        UpdateState.FAILED,
    ],
    UpdateState.CHECKING: [UpdateState.UPDATE_AVAILABLE, UpdateState.UP_TO_DATE, UpdateState.FAILED, UpdateState.IDLE],
    UpdateState.UP_TO_DATE: [UpdateState.CHECKING, UpdateState.IDLE],
    UpdateState.UPDATE_AVAILABLE: [UpdateState.DOWNLOADING, UpdateState.CHECKING, UpdateState.CANCELLED, UpdateState.IDLE],
    UpdateState.DOWNLOADING: [UpdateState.VERIFYING, UpdateState.FAILED, UpdateState.CANCELLED],
    UpdateState.VERIFYING: [UpdateState.STAGING, UpdateState.FAILED],
    UpdateState.STAGING: [UpdateState.INSTALLING, UpdateState.FAILED, UpdateState.ROLLED_BACK],
    UpdateState.INSTALLING: [UpdateState.RESTARTING, UpdateState.SUCCESS, UpdateState.FAILED, UpdateState.ROLLED_BACK],
    UpdateState.RESTARTING: [UpdateState.SUCCESS, UpdateState.FAILED, UpdateState.ROLLED_BACK],
    UpdateState.SUCCESS: [UpdateState.IDLE, UpdateState.CHECKING],
    UpdateState.FAILED: [UpdateState.IDLE, UpdateState.CHECKING, UpdateState.ROLLED_BACK, UpdateState.DOWNLOADING],
    UpdateState.CANCELLED: [UpdateState.IDLE, UpdateState.CHECKING],
    UpdateState.ROLLED_BACK: [UpdateState.IDLE, UpdateState.CHECKING],
}


class SemVer:
    """
    Deterministic Semantic Versioning parser and comparator.
    Adheres to SemVer 2.0.0: major.minor.patch[-prerelease]
    Disallows loose string comparisons.
    """
    _SEMVER_REGEX = re.compile(
        r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?$"
    )

    def __init__(self, major: int, minor: int, patch: int, prerelease: Optional[str] = None):
        self.major = int(major)
        self.minor = int(minor)
        self.patch = int(patch)
        self.prerelease = str(prerelease) if prerelease is not None else None

    @classmethod
    def parse(cls, version_str: str) -> "SemVer":
        if not isinstance(version_str, str):
            raise ValueError(f"Version must be string, got {type(version_str)}")
        clean = version_str.strip()
        match = cls._SEMVER_REGEX.match(clean)
        if not match:
            raise ValueError(f"Invalid SemVer string: '{version_str}'")
        groups = match.groupdict()
        return cls(
            major=int(groups["major"]),
            minor=int(groups["minor"]),
            patch=int(groups["patch"]),
            prerelease=groups["prerelease"]
        )

    def _tuple(self) -> Tuple[int, int, int]:
        return (self.major, self.minor, self.patch)

    def is_prerelease(self) -> bool:
        return self.prerelease is not None and len(self.prerelease) > 0

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SemVer):
            try:
                other = SemVer.parse(str(other))
            except Exception:
                return False
        return (self._tuple() == other._tuple()) and (self.prerelease == other.prerelease)

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, SemVer):
            other = SemVer.parse(str(other))
        if self._tuple() < other._tuple():
            return True
        if self._tuple() > other._tuple():
            return False
        # If numerical parts are equal:
        # A release without prerelease tag has higher precedence than with prerelease tag
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is not None and other.prerelease is not None:
            return self.prerelease < other.prerelease
        return False

    def __le__(self, other: Any) -> bool:
        return self == other or self < other

    def __gt__(self, other: Any) -> bool:
        return not (self <= other)

    def __ge__(self, other: Any) -> bool:
        return not (self < other)

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-{self.prerelease}"
        return base

    def __repr__(self) -> str:
        return f"SemVer({str(self)})"


def sanitize_filename(filename: str) -> str:
    """
    Prevents path traversal attacks and rejects dangerous filename patterns.
    Strictly strips directory paths and disallows relative segments (.., /).
    """
    if not filename or not isinstance(filename, str):
        raise ValueError("Filename must be a non-empty string")
    basename = os.path.basename(filename.replace("\\", "/"))
    # Disallow .., empty, or forbidden characters
    if ".." in basename or "/" in basename or "\\" in basename:
        raise ValueError(f"Path traversal detected in filename: '{filename}'")
    safe_name = re.sub(r'[^a-zA-Z0-9_.\-]', '_', basename)
    if not safe_name or safe_name in ('.', '..'):
        raise ValueError(f"Dangerous filename rejected: '{filename}'")
    return safe_name


def sanitize_release_notes(notes: Any) -> List[str]:
    """
    Sanitizes release notes to prevent HTML/XSS injection.
    Strips raw HTML tags and dangerous protocols.
    """
    if isinstance(notes, str):
        notes = [notes]
    if not isinstance(notes, (list, tuple)):
        return []

    clean_notes = []
    for item in notes:
        s = str(item).strip()
        # Remove any HTML tags <...>
        clean_text = re.sub(r'<[^>]*>', '', s)
        # Block javascript: or data: URIs
        clean_text = re.sub(r'javascript:', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'data:text/html', '', clean_text, flags=re.IGNORECASE)
        if clean_text:
            clean_notes.append(clean_text)
    return clean_notes


@dataclass
class UpdateArtifact:
    name: str
    size_bytes: int
    sha256: str
    signature: str = ""
    url: str = ""
    size_mb: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateArtifact":
        raw_name = data.get("name", "")
        safe_name = sanitize_filename(raw_name)
        size_bytes = int(data.get("size_bytes", 0))
        size_mb = float(data.get("size_mb", round(size_bytes / (1024 * 1024), 2)))
        sha256_hash = str(data.get("sha256", "")).strip().lower()
        signature = str(data.get("signature", "")).strip().lower()
        url = str(data.get("url", "")).strip()

        return cls(
            name=safe_name,
            size_bytes=size_bytes,
            size_mb=size_mb,
            sha256=sha256_hash,
            signature=signature,
            url=url
        )


@dataclass
class UpdateManifest:
    version: str
    release_date: str
    channel: str = "stable"
    mandatory: bool = False
    minimum_supported_version: str = "8.0.0"
    artifacts: List[UpdateArtifact] = field(default_factory=list)
    release_notes: List[str] = field(default_factory=list)
    raw_json: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateManifest":
        if not isinstance(data, dict):
            raise ValueError("Manifest payload must be a JSON object")

        version_str = str(data.get("version", "")).strip()
        if not version_str:
            raise ValueError("Manifest missing required 'version' field")
        # Validate version as valid SemVer
        SemVer.parse(version_str)

        release_date = str(data.get("release_date", "")).strip()
        channel = str(data.get("channel", "stable")).strip().lower()
        mandatory = bool(data.get("mandatory", False))
        min_ver = str(data.get("minimum_supported_version", "8.0.0")).strip()

        # Parse artifacts from either 'files' or 'windows' structures
        artifacts: List[UpdateArtifact] = []
        if "files" in data and isinstance(data["files"], list):
            for f in data["files"]:
                if isinstance(f, dict):
                    artifacts.append(UpdateArtifact.from_dict(f))
        elif "windows" in data and isinstance(data["windows"], dict):
            for arch, info in data["windows"].items():
                if isinstance(info, dict):
                    info_copy = dict(info)
                    if "name" not in info_copy:
                        info_copy["name"] = f"Misa-AI-v{version_str}-{arch}.exe"
                    artifacts.append(UpdateArtifact.from_dict(info_copy))

        release_notes = sanitize_release_notes(data.get("release_notes", []))

        return cls(
            version=version_str,
            release_date=release_date,
            channel=channel,
            mandatory=mandatory,
            minimum_supported_version=min_ver,
            artifacts=artifacts,
            release_notes=release_notes,
            raw_json=data
        )


class UpdateCrypto:
    """
    Cryptographic verification engine.
    - Dual verification: SHA-256 for integrity + Ed25519 for authenticity.
    - Strictly fail-closed: any error results in rejection.
    """

    def __init__(self, trusted_public_key_hex: Optional[str] = None):
        key = (
            trusted_public_key_hex
            or os.environ.get("MISA_UPDATE_PUBLIC_KEY")
            or DEFAULT_TRUSTED_PUBLIC_KEY
        ).strip().lower()
        self.trusted_public_key_hex = key
        self._public_key_cache: Optional[ed25519.Ed25519PublicKey] = None
        self._load_trusted_key()

    def _load_trusted_key(self):
        try:
            raw_bytes = bytes.fromhex(self.trusted_public_key_hex)
            if len(raw_bytes) != 32:
                raise ValueError("Ed25519 public key must be 32 bytes (64 hex characters)")
            self._public_key_cache = ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)
        except Exception as e:
            logger.error(f"[UpdateCrypto] Invalid trusted public key '{self.trusted_public_key_hex}': {e}")
            self._public_key_cache = None

    @staticmethod
    def compute_sha256_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest().lower()

    @staticmethod
    def compute_sha256_file(filepath: str) -> str:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest().lower()

    def verify_hash(self, filepath: str, expected_sha256: str) -> bool:
        """Verifies file SHA-256 integrity."""
        if not os.path.exists(filepath):
            logger.warning(f"[UpdateCrypto] File not found: {filepath}")
            return False
        if not expected_sha256:
            logger.warning("[UpdateCrypto] Empty expected SHA-256 hash")
            return False

        computed = self.compute_sha256_file(filepath)
        matches = (computed == expected_sha256.strip().lower())
        if not matches:
            logger.error(f"[UpdateCrypto] SHA-256 mismatch! computed={computed} expected={expected_sha256}")
        return matches

    def verify_signature(
        self,
        data_to_verify: bytes,
        signature_hex: str,
        custom_pub_key_hex: Optional[str] = None
    ) -> bool:
        """
        Verifies Ed25519 digital signature over raw data bytes.
        Fail-closed: Returns False on any error or signature mismatch.
        """
        if not signature_hex or not data_to_verify:
            return False

        try:
            pub_key = self._public_key_cache
            if custom_pub_key_hex:
                raw_pub = bytes.fromhex(custom_pub_key_hex.strip().lower())
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)

            if pub_key is None:
                logger.error("[UpdateCrypto] No valid public key available for verification")
                return False

            sig_bytes = bytes.fromhex(signature_hex.strip().lower())
            pub_key.verify(sig_bytes, data_to_verify)
            return True
        except (InvalidSignature, ValueError, Exception) as e:
            logger.warning(f"[UpdateCrypto] Ed25519 signature verification failed: {e}")
            return False

    def verify_artifact(
        self,
        filepath: str,
        expected_sha256: str,
        signature_hex: str,
        custom_pub_key_hex: Optional[str] = None
    ) -> bool:
        """
        Dual verification:
        1. SHA-256 matches.
        2. Ed25519 signature over the SHA-256 hash string passes.
        """
        if not self.verify_hash(filepath, expected_sha256):
            return False

        if not signature_hex:
            logger.error("[UpdateCrypto] Fail-closed: Signature is missing for artifact")
            return False

        # Verify signature over the canonical SHA-256 digest bytes
        canonical_msg = expected_sha256.strip().lower().encode("utf-8")
        return self.verify_signature(
            data_to_verify=canonical_msg,
            signature_hex=signature_hex,
            custom_pub_key_hex=custom_pub_key_hex
        )


class UpdateStateManager:
    """
    Crash-resilient, persistent update state tracker.
    Stores state in JSON with atomic file replacement (temp file -> rename).
    Survives power loss and sudden crashes.
    """

    def __init__(self, state_file_path: Optional[str] = None):
        if state_file_path:
            self.state_file = Path(state_file_path)
        else:
            base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home() / ".misa")
            self.state_file = Path(base) / "Misa" / "update_state.json"

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._current_state = UpdateState.IDLE
        self._state_data: Dict[str, Any] = {}
        self.load()

    @property
    def current_state(self) -> UpdateState:
        return self._current_state

    def load(self) -> Dict[str, Any]:
        """Loads state from disk safely."""
        if not self.state_file.exists():
            self._current_state = UpdateState.IDLE
            self._state_data = {
                "state": UpdateState.IDLE.value,
                "current_version": "9.0.0",
                "target_version": None,
                "download_progress": 0,
                "updated_at": time.time()
            }
            return self._state_data

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_st = data.get("state", UpdateState.IDLE.value)
                try:
                    self._current_state = UpdateState(raw_st)
                except ValueError:
                    self._current_state = UpdateState.IDLE
                self._state_data = data
                return self._state_data
        except Exception as e:
            logger.warning(f"[UpdateStateManager] Error reading state file, resetting to IDLE: {e}")
            self._current_state = UpdateState.IDLE
            return {"state": UpdateState.IDLE.value}

    def transition_to(
        self,
        new_state: UpdateState,
        extra_data: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Validates transition and persists state atomically.
        """
        valid_targets = _VALID_TRANSITIONS.get(self._current_state, [])
        if not force and new_state not in valid_targets:
            logger.error(
                f"[UpdateStateManager] Invalid state transition: {self._current_state} -> {new_state}. "
                f"Valid: {valid_targets}"
            )
            return False

        self._current_state = new_state
        self._state_data["state"] = new_state.value
        self._state_data["updated_at"] = time.time()
        if extra_data:
            self._state_data.update(extra_data)

        self._save_atomic()
        return True

    def _save_atomic(self):
        """Atomic write using temp file and rename."""
        tmp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._state_data, f, indent=2)
            # Atomic rename on Windows/POSIX
            tmp_file.replace(self.state_file)
        except Exception as e:
            logger.error(f"[UpdateStateManager] Failed to save state atomically: {e}")
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

    def get_data(self) -> Dict[str, Any]:
        return dict(self._state_data)


class UpdateService:
    """
    Production-grade Secure Auto-Update & Release Service for Misa AI Desktop.
    
    Invariants:
    - HTTPS only (rejects unencrypted HTTP)
    - Dual verification: SHA-256 (integrity) + Ed25519 (authenticity)
    - Fail-closed: invalid artifacts are purged immediately
    - Atomic staging & rollback
    - Zero execution of arbitrary scripts / shell commands (0 eval/exec/os.system/shell=True)
    """

    def __init__(
        self,
        current_version: str = "9.0.0",
        channel: str = "stable",
        manifest_url: Optional[str] = None,
        trusted_public_key: Optional[str] = None,
        staging_dir: Optional[str] = None,
        backup_dir: Optional[str] = None,
        state_file_path: Optional[str] = None
    ):
        self.current_version = current_version
        self.channel = channel.lower()
        self.manifest_url = manifest_url or DEFAULT_MANIFEST_URL
        self.crypto = UpdateCrypto(trusted_public_key)
        self.state_manager = UpdateStateManager(state_file_path)

        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or str(Path.home() / ".misa")
        self.staging_dir = Path(staging_dir) if staging_dir else Path(base) / "Misa" / "updates" / "staging"
        self.backup_dir = Path(backup_dir) if backup_dir else Path(base) / "Misa" / "updates" / "backups"

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._last_manifest: Optional[UpdateManifest] = None
        self._last_checked_time: float = 0.0
        self._active_download_lock = asyncio.Lock()
        self._audit_events: List[Dict[str, Any]] = []

    def record_audit(self, event_type: str, details: Dict[str, Any]):
        evt = {
            "event": event_type,
            "timestamp": time.time(),
            "channel": self.channel,
            "current_version": self.current_version,
            "details": details
        }
        self._audit_events.append(evt)
        logger.info(f"[UpdateAudit] {event_type}: {details}")

    def get_audit_events(self) -> List[Dict[str, Any]]:
        return list(self._audit_events)

    def _validate_transport_url(self, url: str) -> bool:
        """
        Strict HTTPS enforcement. Blocks HTTP fallback.
        Permits local loopback http://127.0.0.1 or http://localhost strictly for unit test fixtures.
        """
        if not url or not isinstance(url, str):
            return False
        clean = url.strip().lower()
        if clean.startswith("https://"):
            return True
        # Allow loopback for isolated tests only
        if clean.startswith("http://127.0.0.1") or clean.startswith("http://localhost"):
            return True
        logger.error(f"[UpdateService] Insecure transport URL blocked: {url}")
        return False

    async def check_for_updates(
        self,
        force: bool = False,
        custom_manifest: Optional[Dict[str, Any]] = None,
        custom_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Checks for available updates against remote or passed manifest.
        Respects 6-hour rate limit unless forced.
        """
        now = time.time()
        if not force and (now - self._last_checked_time < MIN_AUTO_CHECK_INTERVAL_SEC):
            return {
                "update_available": False,
                "reason": "rate_limited",
                "current_version": self.current_version,
                "channel": self.channel
            }

        url = custom_url or self.manifest_url
        if not custom_manifest and not self._validate_transport_url(url):
            self.state_manager.transition_to(UpdateState.FAILED, {"error": "Insecure HTTP URL rejected"})
            self.record_audit("UPDATE_CHECK_FAILED", {"reason": "insecure_transport", "url": url})
            return {
                "update_available": False,
                "error": "HTTPS is required for update checks",
                "current_version": self.current_version
            }

        self.state_manager.transition_to(UpdateState.CHECKING)
        self._last_checked_time = now

        try:
            if custom_manifest:
                manifest_data = custom_manifest
            else:
                import aiohttp
                timeout = aiohttp.ClientTimeout(total=15.0)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise RuntimeError(f"Update server returned HTTP {response.status}")
                        text = await response.text()
                        if len(text.encode("utf-8")) > MAX_MANIFEST_BYTES:
                            raise ValueError("Oversized manifest metadata rejected")
                        manifest_data = json.loads(text)

            manifest = UpdateManifest.from_dict(manifest_data)
            self._last_manifest = manifest

            # Check channel
            if manifest.channel != self.channel:
                logger.info(f"[UpdateService] Ignoring release for different channel: {manifest.channel} != {self.channel}")
                self.state_manager.transition_to(UpdateState.UP_TO_DATE)
                return {
                    "update_available": False,
                    "reason": "channel_mismatch",
                    "current_version": self.current_version
                }

            # SemVer comparison
            current_sem = SemVer.parse(self.current_version)
            target_sem = SemVer.parse(manifest.version)

            if target_sem > current_sem:
                self.state_manager.transition_to(UpdateState.UPDATE_AVAILABLE, {
                    "target_version": manifest.version,
                    "mandatory": manifest.mandatory
                })
                self.record_audit("UPDATE_AVAILABLE", {
                    "target_version": manifest.version,
                    "mandatory": manifest.mandatory
                })
                return {
                    "update_available": True,
                    "current_version": self.current_version,
                    "target_version": manifest.version,
                    "release_date": manifest.release_date,
                    "mandatory": manifest.mandatory,
                    "minimum_supported_version": manifest.minimum_supported_version,
                    "release_notes": manifest.release_notes,
                    "artifacts": [asdict(a) for a in manifest.artifacts]
                }
            else:
                self.state_manager.transition_to(UpdateState.UP_TO_DATE)
                return {
                    "update_available": False,
                    "current_version": self.current_version,
                    "target_version": manifest.version,
                    "reason": "already_up_to_date"
                }

        except Exception as e:
            logger.error(f"[UpdateService] Update check failed: {e}")
            self.state_manager.transition_to(UpdateState.FAILED, {"error": str(e)})
            self.record_audit("UPDATE_CHECK_ERROR", {"error": str(e)})
            return {
                "update_available": False,
                "error": str(e),
                "current_version": self.current_version
            }

    async def download_and_verify_artifact(
        self,
        artifact: UpdateArtifact,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        mock_source_path: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Downloads the specified artifact, verifying SHA-256 and Ed25519 signature.
        Fail-closed: Immediately purges corrupted or unsigned binaries.
        
        Returns: (success: bool, staged_file_path: Optional[str], error_message: Optional[str])
        """
        async with self._active_download_lock:
            # Transition state to DOWNLOADING
            if not self.state_manager.transition_to(UpdateState.DOWNLOADING, {
                "artifact_name": artifact.name,
                "download_progress": 0
            }):
                return False, None, "Invalid state transition to DOWNLOADING"

            temp_file = self.staging_dir / f"{artifact.name}.downloading"
            staged_file = self.staging_dir / artifact.name

            try:
                # 1. Transport Validation
                if not mock_source_path:
                    if not self._validate_transport_url(artifact.url):
                        raise ValueError(f"Insecure download URL blocked: {artifact.url}")

                # 2. Download or copy mock
                if mock_source_path:
                    if not os.path.exists(mock_source_path):
                        raise FileNotFoundError(f"Mock source file missing: {mock_source_path}")
                    shutil.copy2(mock_source_path, temp_file)
                    if progress_callback:
                        progress_callback(100, 100)
                else:
                    import aiohttp
                    timeout = aiohttp.ClientTimeout(total=300.0)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(artifact.url) as resp:
                            if resp.status != 200:
                                raise RuntimeError(f"Download failed with HTTP {resp.status}")
                            total_bytes = int(resp.headers.get("Content-Length", 0))
                            downloaded = 0

                            with open(temp_file, "wb") as f:
                                async for chunk in resp.content.iter_chunked(65536):
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if progress_callback and total_bytes > 0:
                                        pct = int((downloaded / total_bytes) * 100)
                                        progress_callback(pct, 100)
                                        self.state_manager._state_data["download_progress"] = pct

                # 3. Transition to VERIFYING
                self.state_manager.transition_to(UpdateState.VERIFYING)

                # 4. Cryptographic Verification (SHA-256 + Ed25519)
                is_verified = self.crypto.verify_artifact(
                    filepath=str(temp_file),
                    expected_sha256=artifact.sha256,
                    signature_hex=artifact.signature
                )

                if not is_verified:
                    # Fail-closed: immediately delete untrusted file
                    if temp_file.exists():
                        temp_file.unlink()
                    self.state_manager.transition_to(UpdateState.FAILED, {
                        "error": "Cryptographic verification failed (tampered hash or invalid signature)"
                    })
                    self.record_audit("VERIFICATION_FAILED", {
                        "artifact": artifact.name,
                        "sha256": artifact.sha256
                    })
                    return False, None, "Verification failed: integrity/signature check mismatch"

                # 5. Transition to STAGING & atomic move
                self.state_manager.transition_to(UpdateState.STAGING)
                if staged_file.exists():
                    staged_file.unlink()
                temp_file.replace(staged_file)

                self.record_audit("ARTIFACT_STAGED", {
                    "artifact": artifact.name,
                    "path": str(staged_file)
                })
                return True, str(staged_file), None

            except Exception as e:
                # Cleanup on failure
                if temp_file.exists():
                    temp_file.unlink(missing_ok=True)
                self.state_manager.transition_to(UpdateState.FAILED, {"error": str(e)})
                self.record_audit("DOWNLOAD_FAILED", {"artifact": artifact.name, "error": str(e)})
                return False, None, str(e)

    def create_rollback_backup(self, current_executable_path: str) -> Optional[str]:
        """
        Creates a backup copy of current executable before applying update.
        """
        if not os.path.exists(current_executable_path):
            logger.warning(f"[UpdateService] Executable to backup not found: {current_executable_path}")
            return None

        clean_name = sanitize_filename(os.path.basename(current_executable_path))
        backup_file = self.backup_dir / f"{clean_name}.backup_{self.current_version}"
        try:
            shutil.copy2(current_executable_path, backup_file)
            self.state_manager._state_data["backup_file"] = str(backup_file)
            self.state_manager._save_atomic()
            self.record_audit("BACKUP_CREATED", {"backup_file": str(backup_file)})
            return str(backup_file)
        except Exception as e:
            logger.error(f"[UpdateService] Backup failed: {e}")
            return None

    def rollback(self, target_executable_path: str) -> bool:
        """
        Rolls back to the previous backup version.
        """
        backup_file_str = self.state_manager.get_data().get("backup_file")
        if not backup_file_str or not os.path.exists(backup_file_str):
            logger.error(f"[UpdateService] Rollback failed: backup file missing: {backup_file_str}")
            return False

        try:
            shutil.copy2(backup_file_str, target_executable_path)
            self.state_manager.transition_to(UpdateState.ROLLED_BACK)
            self.record_audit("UPDATE_ROLLED_BACK", {
                "restored_from": backup_file_str,
                "target": target_executable_path
            })
            return True
        except Exception as e:
            logger.error(f"[UpdateService] Rollback restoration failed: {e}")
            return False

    def post_update_verify(self, new_running_version: str) -> Dict[str, Any]:
        """
        Post-update verification executed on application startup.
        Verifies version bump, logs audit event, and cleans staging.
        """
        saved_data = self.state_manager.get_data()
        target_ver = saved_data.get("target_version")
        last_state = saved_data.get("state")

        if last_state in (UpdateState.INSTALLING.value, UpdateState.RESTARTING.value):
            if new_running_version == target_ver:
                self.state_manager.transition_to(UpdateState.SUCCESS, {
                    "current_version": new_running_version,
                    "target_version": None
                })
                self.record_audit("UPDATE_COMPLETED", {
                    "version": new_running_version
                })
                # Clean up staging directory
                for f in self.staging_dir.glob("*"):
                    try:
                        if f.is_file():
                            f.unlink()
                    except Exception:
                        pass
                return {"status": "success", "version": new_running_version}
            else:
                self.state_manager.transition_to(UpdateState.FAILED, {
                    "error": f"Startup version mismatch: expected {target_ver}, running {new_running_version}"
                })
                self.record_audit("UPDATE_FAILED", {
                    "expected": target_ver,
                    "actual": new_running_version
                })
                return {"status": "failed", "expected": target_ver, "actual": new_running_version}

        return {"status": "normal", "version": new_running_version}


# Global singleton instance
_update_service_instance: Optional[UpdateService] = None


def get_update_service() -> UpdateService:
    global _update_service_instance
    if _update_service_instance is None:
        _update_service_instance = UpdateService()
    return _update_service_instance
