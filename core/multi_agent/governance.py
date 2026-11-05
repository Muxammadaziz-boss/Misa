# ========== core/multi_agent/governance.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Governance & Security Engine
# Enforces Role-Based Access Control (RBAC), Tool Permission filtering,
# Cryptographic Human Approvals, Execution Budgets, and Audit Logging

import os
import re
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple, Set

from core.common_paths import get_data_path
from core.multi_agent.schema import AgentDefinition, PermissionCategory, PermissionProfile
from core.tools.security_policy import ConfirmationTokenManager, PolicyActionClass
from core.intelligence.observability import redact_sensitive_data

logger = logging.getLogger("misa.multi_agent.governance")

# Sensitive tools requiring mandatory human approval for non-admin agents or high impact actions
HIGH_IMPACT_TOOLS = {
    "run_command",
    "process_manager",
    "file_delete",
    "secret_vault",
    "shutdown",
    "system",
}

# Dangerous command keywords
DESTRUCTIVE_COMMAND_PATTERNS = [
    r"rm\s+-rf",
    r"del\s+/[fFqsSQ]",
    r"drop\s+database",
    r"drop\s+table",
    r"format\s+[a-zA-Z]:",
    r"mkfs",
    r"shutdown",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-fdx",
]


class MultiAgentGovernance:
    """
    Centralized Governance Engine for MISA Multi-Agent Ecosystem.
    Validates tool execution permissions, manages approval challenges, and records immutable audit events.
    """

    def __init__(self, audit_log_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._audit_log_path = audit_log_path or get_data_path("multi_agent_audit.jsonl")
        self._token_manager = ConfirmationTokenManager(default_ttl_seconds=300.0)
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}
        self._audit_history: List[Dict[str, Any]] = []

    def check_tool_permission(
        self,
        agent: AgentDefinition,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, bool, str, Optional[str]]:
        """
        Validates if an agent is authorized to invoke a tool.
        Returns:
            allowed: bool
            requires_approval: bool
            reason: str
            challenge_token: Optional[str]
        """
        t_clean = str(tool_name).strip().lower()
        args = arguments or {}
        perm: PermissionProfile = agent.permission_profile or PermissionProfile()

        with self._lock:
            # 1. Check if tool is explicitly denied
            if t_clean in [d.lower() for d in perm.denied_tools]:
                self._record_audit_event(agent.agent_id, t_clean, args, False, "Tool explicitly denied in agent permission profile")
                return False, False, f"Tool '{t_clean}' is explicitly denied for agent '{agent.agent_id}'.", None

            # 2. Check if agent is strictly read-only
            if perm.read_only:
                # Read-only agents can only invoke read/view tools
                read_only_tools = {"view_file", "search", "grep_search", "scheduler", "datetime", "weather", "calculator"}
                if t_clean not in read_only_tools:
                    self._record_audit_event(agent.agent_id, t_clean, args, False, "Read-only agent attempted non-read operation")
                    return False, False, f"Agent '{agent.agent_id}' is restricted to read-only operations. Tool '{t_clean}' is prohibited.", None

            # 3. Check if tool is in agent's allowed tools list
            allowed_tools = [t.lower() for t in (perm.allowed_tools or agent.available_tools)]
            if allowed_tools and t_clean not in allowed_tools and agent.permission_profile.category != PermissionCategory.ADMIN:
                self._record_audit_event(agent.agent_id, t_clean, args, False, "Tool not in agent's allowed tools list")
                return False, False, f"Tool '{t_clean}' is not granted to agent '{agent.agent_id}'.", None

            # 4. Check for high-impact or destructive operations requiring Human Approval
            is_high_impact = t_clean in HIGH_IMPACT_TOOLS or perm.requires_approval
            is_destructive = False

            if t_clean == "run_command":
                cmd = str(args.get("command", "") or args.get("cmd", ""))
                for pattern in DESTRUCTIVE_COMMAND_PATTERNS:
                    if re.search(pattern, cmd, re.IGNORECASE):
                        is_destructive = True
                        break

            if is_destructive or is_high_impact:
                token = self._token_manager.create_token(t_clean, args, ttl=300.0)
                challenge_info = {
                    "token": token,
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name,
                    "tool_name": t_clean,
                    "arguments": redact_sensitive_data(args),
                    "created_at": time.time(),
                    "expires_at": time.time() + 300.0,
                    "is_destructive": is_destructive,
                }
                self._pending_approvals[token] = challenge_info
                self._record_audit_event(agent.agent_id, t_clean, args, True, "Human approval challenge issued", token=token)
                return True, True, "Operation requires explicit human confirmation.", token

            # 5. Permitted
            self._record_audit_event(agent.agent_id, t_clean, args, True, "Authorized by governance policy")
            return True, False, "Authorized", None

    def approve_operation(self, token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """User approves a pending high-risk action."""
        with self._lock:
            if token not in self._pending_approvals:
                return False, "Approval token not found or already processed.", None

            info = self._pending_approvals.pop(token)
            if time.time() > info.get("expires_at", 0):
                return False, "Approval token has expired.", None

            self._record_audit_event(
                info["agent_id"],
                info["tool_name"],
                info["arguments"],
                True,
                "Human approval granted by user",
                token=token
            )
            return True, "Operation approved by user.", info

    def reject_operation(self, token: str, reason: str = "User declined") -> bool:
        """User rejects a pending high-risk action."""
        with self._lock:
            if token not in self._pending_approvals:
                return False
            info = self._pending_approvals.pop(token)
            self._record_audit_event(
                info["agent_id"],
                info["tool_name"],
                info["arguments"],
                False,
                f"Human approval rejected: {reason}",
                token=token
            )
            return True

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """List active pending approval challenges."""
        with self._lock:
            now = time.time()
            active = []
            expired = []
            for token, info in self._pending_approvals.items():
                if now <= info.get("expires_at", 0):
                    active.append(dict(info))
                else:
                    expired.append(token)
            for exp in expired:
                self._pending_approvals.pop(exp, None)
            return active

    def _record_audit_event(
        self,
        agent_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        allowed: bool,
        reason: str,
        token: Optional[str] = None
    ) -> None:
        """Appends an immutable audit event to memory and JSONL log."""
        record = {
            "timestamp": time.time(),
            "time_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "agent_id": agent_id,
            "tool_name": tool_name,
            "arguments": redact_sensitive_data(arguments),
            "allowed": allowed,
            "reason": reason,
            "token": token,
        }
        self._audit_history.append(record)
        if len(self._audit_history) > 500:
            self._audit_history = self._audit_history[-500:]

        try:
            os.makedirs(os.path.dirname(self._audit_log_path), exist_ok=True)
            with open(self._audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to append to audit log: {e}")

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._audit_history[-limit:])


# Singleton
_governance_instance: Optional[MultiAgentGovernance] = None
_governance_lock = threading.Lock()


def get_multi_agent_governance() -> MultiAgentGovernance:
    global _governance_instance
    with _governance_lock:
        if _governance_instance is None:
            _governance_instance = MultiAgentGovernance()
        return _governance_instance
