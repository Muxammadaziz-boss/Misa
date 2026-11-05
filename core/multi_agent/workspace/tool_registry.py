# ========== core/multi_agent/workspace/tool_registry.py ==========
# Misa AI 9.0.0 — Central Workspace Tool Registry & Activity Bus
# Coordinates all workspace tools, validates inputs, enforces permissions, and emits live activity events.

import time
import uuid
import logging
import threading
from typing import Dict, Any, List, Optional, Callable, Tuple

from core.multi_agent.workspace.schema import ActivityEvent, WorkspaceMode
from core.multi_agent.workspace.manager import WorkspaceManager, get_workspace_manager
from core.multi_agent.workspace.fs_tools import FileSystemEngine, get_filesystem_engine
from core.multi_agent.workspace.terminal_tools import TerminalEngine, get_terminal_engine
from core.multi_agent.workspace.git_tools import GitEngine, get_git_engine
from core.multi_agent.workspace.dev_tools import ProjectUnderstandingEngine, get_project_understanding_engine
from core.multi_agent.governance import MultiAgentGovernance, get_multi_agent_governance

logger = logging.getLogger("misa.multi_agent.workspace.registry")


class WorkspaceToolRegistry:
    """
    Central Workspace Tool Registry.
    Validates arguments, enforces sandbox jail boundaries, checks operation mode policies,
    and publishes live execution activity events to UI subscribers.
    """

    def __init__(
        self,
        manager: Optional[WorkspaceManager] = None,
        fs_engine: Optional[FileSystemEngine] = None,
        terminal: Optional[TerminalEngine] = None,
        git_engine: Optional[GitEngine] = None,
        dev_engine: Optional[ProjectUnderstandingEngine] = None,
        governance: Optional[MultiAgentGovernance] = None,
    ):
        self.manager = manager or get_workspace_manager()
        self.fs = fs_engine or get_filesystem_engine()
        self.terminal = terminal or get_terminal_engine()
        self.git = git_engine or get_git_engine()
        self.dev = dev_engine or get_project_understanding_engine()
        self.governance = governance or get_multi_agent_governance()

        self._lock = threading.RLock()
        self._activity_history: List[ActivityEvent] = []
        self._activity_listeners: List[Callable[[ActivityEvent], None]] = []

    # ========================================================
    # Live Activity Bus & Event Publishing
    # ========================================================

    def subscribe_activity(self, callback: Callable[[ActivityEvent], None]) -> None:
        with self._lock:
            if callback not in self._activity_listeners:
                self._activity_listeners.append(callback)

    def unsubscribe_activity(self, callback: Callable[[ActivityEvent], None]) -> None:
        with self._lock:
            if callback in self._activity_listeners:
                self._activity_listeners.remove(callback)

    def _publish_event(self, event: ActivityEvent) -> None:
        with self._lock:
            self._activity_history.append(event)
            if len(self._activity_history) > 200:
                self._activity_history = self._activity_history[-200:]
            listeners = list(self._activity_listeners)

        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in activity listener callback: {e}")

    def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.to_dict() for a in self._activity_history[-limit:]]

    # ========================================================
    # Central Tool Execution Router
    # ========================================================

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_id: str = "misa-main"
    ) -> Dict[str, Any]:
        """
        Executes a workspace tool with boundary checking and live telemetry.
        """
        t_name = tool_name.strip().lower()
        event = ActivityEvent(
            tool_name=t_name,
            operation=f"Executing {t_name} with params: {list(arguments.keys())}",
            agent_id=agent_id,
            status="running",
            started_at=time.time(),
        )
        self._publish_event(event)
        start_time = time.time()

        # 1. Mode Policy Verification
        allowed, req_approval, reason = self.manager.check_operation_policy(t_name)
        if not allowed:
            event.status = "failed"
            event.error = reason
            event.duration_seconds = round(time.time() - start_time, 2)
            self._publish_event(event)
            raise PermissionError(reason)

        if req_approval:
            # Generate cryptographic approval challenge
            token = self.governance._token_manager.create_token(t_name, arguments, ttl=300.0)
            event.status = "waiting_for_approval"
            event.output_preview = f"Requires human approval. Token: {token}"
            event.duration_seconds = round(time.time() - start_time, 2)
            self._publish_event(event)
            return {
                "ok": False,
                "status": "waiting_for_approval",
                "approval_token": token,
                "message": reason,
                "tool": t_name,
                "arguments": arguments,
            }

        try:
            # 2. Dispatch to specific tool implementation
            result = self._dispatch(t_name, arguments, agent_id)

            event.status = "completed"
            event.duration_seconds = round(time.time() - start_time, 2)
            # Safe summary for preview
            preview = str(result)[:300] if result else "Success"
            event.output_preview = preview
            self._publish_event(event)

            return {"ok": True, "data": result}

        except Exception as e:
            logger.error(f"Workspace tool '{t_name}' execution error: {e}")
            event.status = "failed"
            event.error = str(e)
            event.duration_seconds = round(time.time() - start_time, 2)
            self._publish_event(event)
            return {"ok": False, "error": str(e)}

    def _dispatch(self, tool_name: str, args: Dict[str, Any], agent_id: str) -> Any:
        """Internal router mapping tool names to actual engines."""
        # --- File System Tools ---
        p_val = args.get("path") or args.get("rel_path", "")
        if tool_name == "list_directory":
            return self.fs.list_directory(
                rel_path=p_val,
                max_depth=int(args.get("max_depth", 1))
            )
        elif tool_name == "read_file":
            return self.fs.read_file(
                rel_path=p_val,
                start_line=args.get("start_line"),
                end_line=args.get("end_line")
            )
        elif tool_name == "search_files":
            return self.fs.search_files(
                pattern=args.get("pattern", "*"),
                base_path=args.get("base_path", "")
            )
        elif tool_name == "search_content":
            return self.fs.search_content(
                query=args.get("query", ""),
                base_path=args.get("base_path", ""),
                extensions=args.get("extensions")
            )
        elif tool_name == "inspect_project_tree":
            return self.fs.inspect_project_tree(
                max_depth=int(args.get("max_depth", 3)),
                max_files=int(args.get("max_files", 150))
            )
        elif tool_name == "create_file":
            return self.fs.create_file(
                rel_path=p_val,
                content=args.get("content", ""),
                agent_id=agent_id
            )
        elif tool_name == "modify_file":
            return self.fs.modify_file(
                rel_path=p_val,
                new_content=args.get("content") or args.get("new_content", ""),
                agent_id=agent_id
            )
        elif tool_name == "apply_patch":
            return self.fs.apply_patch(
                rel_path=p_val,
                target_snippet=args.get("target_snippet") or args.get("old_snippet", ""),
                replacement_snippet=args.get("replacement_snippet", ""),
                agent_id=agent_id
            )
        elif tool_name == "rename_file":
            return self.fs.rename_file(
                old_rel_path=args.get("old_path", ""),
                new_rel_path=args.get("new_path", ""),
                agent_id=agent_id
            )
        elif tool_name == "create_directory":
            return self.fs.create_directory(rel_path=args.get("path", ""))

        # --- Terminal Tools ---
        elif tool_name == "run_command":
            rec = self.terminal.run_command(
                command=args.get("command", ""),
                cwd_relative=args.get("cwd"),
                timeout_seconds=float(args.get("timeout", 60.0)),
                agent_id=agent_id
            )
            return rec.to_dict()
        elif tool_name == "cancel_command":
            return {"cancelled": self.terminal.cancel_command(args.get("command_id", ""))}
        elif tool_name == "get_command_status":
            rec = self.terminal.get_command_status(args.get("command_id", ""))
            return rec.to_dict() if rec else None

        # --- Git Tools ---
        elif tool_name == "git_status":
            return self.git.git_status()
        elif tool_name == "git_diff":
            return self.git.git_diff(
                cached=bool(args.get("cached", False)),
                file_path=args.get("file_path")
            )
        elif tool_name == "git_log":
            return self.git.git_log(limit=int(args.get("limit", 10)))
        elif tool_name == "git_branch":
            return self.git.git_branch()
        elif tool_name == "git_create_branch":
            return self.git.git_create_branch(args.get("branch_name", ""))

        # --- Development & Project Understanding Tools ---
        elif tool_name in ("analyze_project", "inspect_project_configuration"):
            return self.dev.analyze_project().to_dict()
        elif tool_name == "inspect_dependencies":
            return self.dev.analyze_project().dependencies
        elif tool_name == "run_tests":
            rec = self.dev.run_tests(custom_command=args.get("command"))
            return rec.to_dict()
        elif tool_name == "run_build":
            rec = self.dev.run_build(custom_command=args.get("command"))
            return rec.to_dict()

        else:
            raise NotImplementedError(f"Workspace tool '{tool_name}' is not recognized.")


# Singleton
_workspace_tool_registry_instance: Optional[WorkspaceToolRegistry] = None
_workspace_tool_registry_lock = threading.Lock()


def get_workspace_tool_registry() -> WorkspaceToolRegistry:
    global _workspace_tool_registry_instance
    with _workspace_tool_registry_lock:
        if _workspace_tool_registry_instance is None:
            _workspace_tool_registry_instance = WorkspaceToolRegistry()
        return _workspace_tool_registry_instance
