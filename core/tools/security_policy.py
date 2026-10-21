# ========== core/tools/security_policy.py ==========
# Misa AI 9.0 — Authoritative Tool Security & Confirmation Policy
# Unifies tool metadata, permissions, confirmation tokens, replay protection and local API isolation

import time
import json
import secrets
import hashlib
import logging
from typing import Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

from core.intelligence.types import RiskLevel
from core.intelligence.permission import PermissionEngine
from core.intelligence.observability import redact_sensitive_data

logger = logging.getLogger("misa.tools.security_policy")


class PolicyActionClass(str, Enum):
    READ_ONLY = "read_only"
    CONFIRMATION_REQUIRED = "confirmation_required"
    DESTRUCTIVE_OR_POWER = "destructive_or_power"


@dataclass
class PolicyDecision:
    allowed: bool
    requires_confirmation: bool
    risk_level: RiskLevel
    reason: str
    prompt: Optional[str] = None
    challenge_token: Optional[str] = None
    action_class: PolicyActionClass = PolicyActionClass.READ_ONLY


class ConfirmationTokenManager:
    """
    Kriptografik bir martalik tasdiqlash tokenlarini boshqaruvchi (One-Time Confirmation Tokens).
    Muddati (TTL), parametrlarning xeshi va replay-attack himoyasini ta'minlaydi.
    """

    def __init__(self, default_ttl_seconds: float = 180.0):
        self.default_ttl = default_ttl_seconds
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._max_tokens = 500

    def _hash_params(self, params: Optional[Dict[str, Any]]) -> str:
        try:
            normalized = json.dumps(params or {}, sort_keys=True, default=str)
        except Exception:
            normalized = str(params or {})
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def create_token(self, tool_name: str, params: Optional[Dict[str, Any]] = None, ttl: Optional[float] = None) -> str:
        """Yangi bir martalik tasdiqlash tokenini yaratish"""
        self._purge_expired()
        token = secrets.token_urlsafe(32)
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        now = time.time()

        self._tokens[token] = {
            "token": token,
            "tool_name": str(tool_name).strip().lower(),
            "params_hash": self._hash_params(params),
            "created_at": now,
            "expires_at": now + ttl_seconds,
            "used": False
        }
        return token

    def verify_and_consume(self, token: Optional[str], tool_name: str, params: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Tokenni tekshirish va uni bekor qilish (Consume token to prevent replay).
        """
        if not token or not str(token).strip():
            return False, "MISSING_CONFIRMATION_TOKEN"

        token_str = str(token).strip()
        record = self._tokens.get(token_str)
        if not record:
            return False, "INVALID_TOKEN"

        if record.get("used", False):
            return False, "TOKEN_ALREADY_USED"

        now = time.time()
        if now > record.get("expires_at", 0.0):
            return False, "TOKEN_EXPIRED"

        clean_tool = str(tool_name).strip().lower()
        if record.get("tool_name") != clean_tool:
            return False, "TOOL_NAME_MISMATCH"

        curr_hash = self._hash_params(params)
        if record.get("params_hash") != curr_hash:
            return False, "PARAMS_MISMATCH"

        # Replay attack oldini olish uchun ishlatilgan deb belgilaymiz
        record["used"] = True
        return True, "OK"

    def _purge_expired(self):
        now = time.time()
        self._tokens = {k: v for k, v in self._tokens.items() if not v.get("used", False) and v.get("expires_at", 0.0) >= now}
        if len(self._tokens) > self._max_tokens:
            # Eng eski tokenlarni o'chirish
            sorted_tokens = sorted(self._tokens.items(), key=lambda x: x[1].get("created_at", 0.0))
            self._tokens = dict(sorted_tokens[-self._max_tokens:])


class AuthoritativeSecurityPolicy:
    """
    Misa AI ning barcha vositalar (Tools) va chaqiruvlar uchun yagona vakolatli xavfsizlik siyosati.
    Tool metadata, ruxsatlar dvigateli va tasdiqlash tokenlarini birlashtiradi.
    """

    # User confirmation majburiy bo'lgan amallar ro'yxati
    KEYBOARD_ACTIONS: Set[str] = {
        "keyboard_type", "send_keys", "hotkey", "press_key", "type_text",
        "key_down", "key_up", "paste", "keyboard_input"
    }

    MOUSE_ACTIONS: Set[str] = {
        "screen_click", "mouse_click", "double_click", "right_click",
        "mouse_move_click", "mouse_drag", "mouse_scroll", "mouse_press"
    }

    CLIPBOARD_WRITE_ACTIONS: Set[str] = {
        "clipboard_set", "clipboard_write", "copy_to_clipboard", "set_clipboard"
    }

    FILE_WRITE_OR_DELETE_ACTIONS: Set[str] = {
        "file_write", "file_delete", "file_move", "file_create", "file_append",
        "file_truncate", "destructive_file_op", "delete_all_reminders",
        "clear_memory", "delete_plugin", "create_file", "modify_file"
    }

    PROCESS_CLOSE_ACTIONS: Set[str] = {
        "process_kill", "close_window", "kill_app", "close_chrome", "task_kill"
    }

    BROWSER_NAV_ACTIONS: Set[str] = {
        "browser_navigate", "open_url", "navigate_url", "browser_open", "browse_to"
    }

    NETWORK_ACTIONS: Set[str] = {
        "http_request", "send_network", "webhook_call", "api_call", "socket_send"
    }

    POWER_ACTIONS: Set[str] = {
        "shutdown", "restart", "system_shutdown", "system_restart",
        "sleep", "hibernate", "lock", "power_action", "sign_out", "logoff"
    }

    # Faqat xavfsiz o'qish (Read-only) amallari
    SAFE_READ_ONLY_TOOLS: Set[str] = {
        "system_info", "battery_status", "cpu_metrics", "ram_metrics",
        "list_processes", "list_files", "read_file", "file_read", "search_files",
        "get_weather", "get_time", "get_date", "get_status", "get_reminder",
        "list_reminders", "get_memory", "search_web", "clipboard_get",
        "get_clipboard", "window_list", "get_active_window", "screen_analyze",
        "screen_capture", "screenshot"
    }

    def __init__(self, permission_engine: Optional[PermissionEngine] = None):
        self.permission_engine = permission_engine or PermissionEngine()
        self.token_manager = ConfirmationTokenManager()

    def is_read_only(self, tool_name: str, tool_obj: Optional[Any] = None) -> bool:
        """Amalning mutlaqo read-only ekanligini tekshirish"""
        clean = (tool_name or "").lower().strip()
        if clean in self.SAFE_READ_ONLY_TOOLS:
            return True
        if tool_obj:
            is_dest = bool(getattr(tool_obj, "destructive", False))
            req_confirm = bool(getattr(tool_obj, "requires_confirmation", False))
            cat = str(getattr(tool_obj, "category", "") or "").lower()
            if not is_dest and not req_confirm and cat in ("query", "info", "read", "status", "system_info"):
                return True
        return False

    def is_confirmation_required(self, tool_name: str, tool_obj: Optional[Any] = None) -> Tuple[bool, str, RiskLevel]:
        """
        Tool metadata va harakat turiga ko'ra tasdiqlash talab etilishini aniqlash.
        """
        clean = (tool_name or "").lower().strip()

        # 1. Quvvat amallari (Power actions)
        if clean in self.POWER_ACTIONS or any(p in clean for p in ("shutdown", "restart", "reboot", "poweroff")):
            return True, "Kompyuter quvvatini boshqarish (shutdown/restart) uchun tasdiqlash talab etiladi", RiskLevel.HIGH

        # 2. Fayl o'chirish yoki yozish
        if clean in self.FILE_WRITE_OR_DELETE_ACTIONS or any(w in clean for w in ("file_delete", "delete_file", "file_write", "overwrite")):
            return True, "Fayl tizimiga o'zgartirish kiritish yoki o'chirish uchun tasdiqlash talab etiladi", RiskLevel.HIGH

        # 3. Process yoki oynani yopish
        if clean in self.PROCESS_CLOSE_ACTIONS or any(k in clean for k in ("kill", "close_window", "close_chrome")):
            return True, "Dastur yoki oynani yopish uchun tasdiqlash talab etiladi", RiskLevel.HIGH

        # 4. Klaviatura orqali matn yoki tugma yuborish
        if clean in self.KEYBOARD_ACTIONS or "type" in clean or "key" in clean:
            return True, "Klaviatura orqali matn kiritish uchun tasdiqlash talab etiladi", RiskLevel.HIGH

        # 5. Sichqoncha tugmasini bosish
        if clean in self.MOUSE_ACTIONS or "click" in clean or "drag" in clean:
            return True, "Ekranga sichqoncha orqali bosish (click) uchun tasdiqlash talab etiladi", RiskLevel.HIGH

        # 6. Clipboardga yozish
        if clean in self.CLIPBOARD_WRITE_ACTIONS or "clipboard_set" in clean or "copy_to" in clean:
            return True, "Klipbordga ma'lumot yozish uchun tasdiqlash talab etiladi", RiskLevel.MEDIUM

        # 7. Brauzer navigatsiyasi
        if clean in self.BROWSER_NAV_ACTIONS or "navigate" in clean or "open_url" in clean:
            return True, "Brauzerda havola ochish yoki navigatsiya uchun tasdiqlash talab etiladi", RiskLevel.HIGH

        # 8. Tarmoq so'rovlari
        if clean in self.NETWORK_ACTIONS or "http_request" in clean or "webhook" in clean:
            return True, "Tashqi tarmoqqa so'rov yuborish uchun tasdiqlash talab etiladi", RiskLevel.HIGH

        # 9. Tool metadata tekshiruvi (destructive / requires_confirmation / risk_level)
        if tool_obj:
            if bool(getattr(tool_obj, "destructive", False)):
                return True, f"'{tool_name}' destruktiv amal bo'lgani sababli tasdiqlash talab etiladi", RiskLevel.HIGH
            if bool(getattr(tool_obj, "requires_confirmation", False)):
                return True, f"'{tool_name}' vositasi foydalanuvchi tasdig'ini talab qiladi", RiskLevel.HIGH
            
            tool_risk = str(getattr(tool_obj, "risk_level", "LOW") or "").lower()
            if tool_risk in ("high", "critical", "risklevel.high", "risklevel.critical"):
                return True, f"'{tool_name}' yuqori xavfli vosita hisoblanadi", RiskLevel.HIGH

        # 10. PermissionEngine orqali tekshirish
        perm_risk, perm_req, perm_prompt = self.permission_engine.evaluate(clean)
        if perm_req:
            return True, perm_prompt or f"'{tool_name}' uchun tasdiqlash talab etiladi", perm_risk

        return False, "", RiskLevel.LOW

    def evaluate(
        self,
        tool_name: str,
        tool_obj: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        confirmation_token: Optional[str] = None
    ) -> PolicyDecision:
        """
        Vakolatli xavfsizlik qarorini qabul qilish.
        """
        clean = (tool_name or "").lower().strip()

        # A) Read-only tekshiruvi
        if self.is_read_only(clean, tool_obj):
            return PolicyDecision(
                allowed=True,
                requires_confirmation=False,
                risk_level=RiskLevel.LOW,
                reason="READ_ONLY_AUTO_ALLOWED",
                action_class=PolicyActionClass.READ_ONLY
            )

        # B) Tasdiqlash talabi tekshiruvi
        req_confirm, prompt, risk = self.is_confirmation_required(clean, tool_obj)
        if not req_confirm:
            return PolicyDecision(
                allowed=True,
                requires_confirmation=False,
                risk_level=risk,
                reason="LOW_RISK_AUTO_ALLOWED",
                action_class=PolicyActionClass.READ_ONLY
            )

        # C) Tasdiqlash talab qilinadi — agar token berilgan bo'lsa tekshiramiz
        if confirmation_token:
            valid, token_msg = self.token_manager.verify_and_consume(confirmation_token, clean, params)
            if valid:
                logger.info(f"[AuthoritativeSecurityPolicy] '{clean}' amali tasdiqlash tokeni bilan ruxsat berildi")
                return PolicyDecision(
                    allowed=True,
                    requires_confirmation=True,
                    risk_level=risk,
                    reason=f"TOKEN_VERIFIED ({token_msg})",
                    prompt=prompt,
                    action_class=PolicyActionClass.CONFIRMATION_REQUIRED
                )
            else:
                logger.warning(f"[AuthoritativeSecurityPolicy] '{clean}' uchun yaroqsiz token: {token_msg}")
                # Yangi challenge token beramiz
                challenge = self.token_manager.create_token(clean, params)
                return PolicyDecision(
                    allowed=False,
                    requires_confirmation=True,
                    risk_level=risk,
                    reason=f"INVALID_CONFIRMATION_TOKEN: {token_msg}",
                    prompt=prompt,
                    challenge_token=challenge,
                    action_class=PolicyActionClass.CONFIRMATION_REQUIRED
                )

        # D) Token berilmagan — yangi challenge token yaratiladi
        challenge = self.token_manager.create_token(clean, params)
        logger.info(f"[AuthoritativeSecurityPolicy] '{clean}' amali uchun tasdiqlash talab qilinadi. Challenge yaratildi.")
        return PolicyDecision(
            allowed=False,
            requires_confirmation=True,
            risk_level=risk,
            reason="CONFIRMATION_REQUIRED",
            prompt=prompt,
            challenge_token=challenge,
            action_class=PolicyActionClass.CONFIRMATION_REQUIRED
        )


# Singleton
_security_policy_instance: Optional[AuthoritativeSecurityPolicy] = None


def get_security_policy() -> AuthoritativeSecurityPolicy:
    global _security_policy_instance
    if _security_policy_instance is None:
        _security_policy_instance = AuthoritativeSecurityPolicy()
    return _security_policy_instance


# Ichki API sessiya tokeni (127.0.0.1 lokal chaqiruvlarni boshqa jarayonlardan himoyalash uchun)
_INTERNAL_API_SESSION_TOKEN: str = secrets.token_urlsafe(32)


def get_internal_api_session_token() -> str:
    """Backend ishga tushganda yaratilgan yagona ichki sessiya tokeni"""
    return _INTERNAL_API_SESSION_TOKEN


def verify_internal_api_request(headers: Dict[str, str], body: Optional[Dict[str, Any]] = None) -> bool:
    """
    127.0.0.1 /api/plugins/execute kabi xavfli lokal endpointlarni faqat ruxsatli
    Misa Desktop / supervisor chaqirishi mumkinligini tasdiqlash.
    """
    token = get_internal_api_session_token()
    
    # 1. Header orqali tekshirish
    auth_header = headers.get("X-Misa-Session-Token") or headers.get("x-misa-session-token")
    if auth_header and secrets.compare_digest(auth_header.strip(), token):
        return True

    bearer = headers.get("Authorization") or headers.get("authorization")
    if bearer and bearer.lower().startswith("bearer "):
        provided = bearer[7:].strip()
        if secrets.compare_digest(provided, token):
            return True

    # 2. Body orqali tekshirish
    if body and isinstance(body, dict):
        body_token = str(body.get("session_token", "") or "").strip()
        if body_token and secrets.compare_digest(body_token, token):
            return True

    return False
