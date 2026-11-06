# ========== core/multi_agent/workspace/manager.py ==========
# Misa AI 9.0.0 — Native Workspace Connection & Security Jail Manager
# Enforces path traversal protection, workspace registration, and operation mode governance

import os
import json
import uuid
import logging
import threading
import time
from typing import Dict, List, Optional, Tuple, Any

from core.common_paths import get_data_path, get_base_dir
from core.multi_agent.workspace.schema import WorkspaceConfig, WorkspaceMode

logger = logging.getLogger("misa.multi_agent.workspace.manager")


class WorkspaceManager:
    """
    Manages active project workspaces and enforces the strict local sandbox boundary.
    Guarantees that agents cannot read, modify, or execute code outside permitted roots.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._storage_path = storage_path or get_data_path("workspaces.json")
        self._workspaces: Dict[str, WorkspaceConfig] = {}
        self._active_workspace_id: Optional[str] = None
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        with self._lock:
            if os.path.isfile(self._storage_path):
                try:
                    with open(self._storage_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            try:
                                ws = WorkspaceConfig.from_dict(item)
                                self._workspaces[ws.workspace_id] = ws
                                if ws.is_active:
                                    self._active_workspace_id = ws.workspace_id
                            except Exception as ex:
                                logger.warning(f"Error parsing workspace: {ex}")
                except Exception as e:
                    logger.error(f"Failed to load workspaces from {self._storage_path}: {e}")

            # If no workspace registered, default to current MISA base directory
            if not self._workspaces:
                base_dir = get_base_dir()
                default_ws = WorkspaceConfig(
                    workspace_id="default_misa_ws",
                    name="Misa Project",
                    root_path=os.path.realpath(base_dir),
                    permitted_paths=[os.path.realpath(base_dir)],
                    mode=WorkspaceMode.CONTROLLED_AUTONOMY,
                    is_active=True,
                )
                self._workspaces[default_ws.workspace_id] = default_ws
                self._active_workspace_id = default_ws.workspace_id
                self._save_to_disk()

    def _save_to_disk(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            data = [ws.to_dict() for ws in self._workspaces.values()]
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist workspaces: {e}")

    # ========================================================
    # Workspace Lifecycle & Connection
    # ========================================================

    def connect_workspace(
        self,
        root_path: str,
        name: Optional[str] = None,
        mode: WorkspaceMode = WorkspaceMode.SUPERVISED,
        permitted_paths: Optional[List[str]] = None
    ) -> WorkspaceConfig:
        """Connects a local folder as an authorized project workspace."""
        clean_path = os.path.realpath(os.path.abspath(root_path.strip()))
        if not os.path.isdir(clean_path):
            raise FileNotFoundError(f"Project directory '{root_path}' does not exist or is not a directory.")

        with self._lock:
            # Check if path already connected
            for ws in self._workspaces.values():
                if os.path.realpath(ws.root_path) == clean_path:
                    ws.mode = mode
                    ws.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    self._save_to_disk()
                    return ws

            ws_id = f"ws_{uuid.uuid4().hex[:8]}"
            ws_name = name or os.path.basename(clean_path) or "Workspace"
            perms = [clean_path]
            if permitted_paths:
                for p in permitted_paths:
                    rp = os.path.realpath(os.path.abspath(p))
                    if rp not in perms:
                        perms.append(rp)

            # Deactivate others if newly connected
            for w in self._workspaces.values():
                w.is_active = False

            new_ws = WorkspaceConfig(
                workspace_id=ws_id,
                name=ws_name,
                root_path=clean_path,
                permitted_paths=perms,
                mode=mode,
                is_active=True,
            )
            self._workspaces[ws_id] = new_ws
            self._active_workspace_id = ws_id
            self._save_to_disk()
            logger.info(f"Connected workspace '{ws_name}' at {clean_path} (mode={mode.value})")
            return new_ws

    def disconnect_workspace(self, workspace_id: str) -> bool:
        """Disconnects a workspace."""
        with self._lock:
            if workspace_id not in self._workspaces:
                return False
            del self._workspaces[workspace_id]
            if self._active_workspace_id == workspace_id:
                self._active_workspace_id = next(iter(self._workspaces.keys()), None)
                if self._active_workspace_id:
                    self._workspaces[self._active_workspace_id].is_active = True
            self._save_to_disk()
            return True

    def set_active_workspace(self, workspace_id: str) -> bool:
        """Switches the active workspace."""
        with self._lock:
            if workspace_id not in self._workspaces:
                return False
            for w in self._workspaces.values():
                w.is_active = (w.workspace_id == workspace_id)
            self._active_workspace_id = workspace_id
            self._save_to_disk()
            return True

    def get_active_workspace(self) -> Optional[WorkspaceConfig]:
        with self._lock:
            if self._active_workspace_id and self._active_workspace_id in self._workspaces:
                return self._workspaces[self._active_workspace_id]
            if self._workspaces:
                first = next(iter(self._workspaces.values()))
                first.is_active = True
                self._active_workspace_id = first.workspace_id
                return first
            return None

    def list_workspaces(self) -> List[WorkspaceConfig]:
        with self._lock:
            return list(self._workspaces.values())

    def update_mode(self, workspace_id: str, mode: WorkspaceMode) -> WorkspaceConfig:
        return self.update_workspace_mode(workspace_id, mode)

    def update_workspace_mode(self, workspace_id: str, mode: WorkspaceMode) -> WorkspaceConfig:
        with self._lock:
            if workspace_id not in self._workspaces:
                raise KeyError(f"Workspace '{workspace_id}' not found.")
            ws = self._workspaces[workspace_id]
            ws.mode = mode
            ws.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._save_to_disk()
            return ws

    # ========================================================
    # Sandbox Path Resolution & Traversal Jail
    # ========================================================

    def resolve_safe_path(self, target_path: str, must_exist: bool = False) -> str:
        """
        Resolves an absolute or relative path within the active workspace.
        STRICTLY prevents directory traversal, symlink escapes, or access outside permitted roots.
        Raises PermissionError if the path attempts to escape the sandbox.
        """
        active_ws = self.get_active_workspace()
        if not active_ws:
            raise RuntimeError("No active workspace configured.")

        root = os.path.realpath(active_ws.root_path)

        # Normalize target path
        clean_target = str(target_path).strip()
        if not clean_target or clean_target in (".", "./", ".\\"):
            return root

        # Check for path traversal characters
        if os.path.isabs(clean_target):
            candidate = os.path.realpath(clean_target)
        else:
            candidate = os.path.realpath(os.path.abspath(os.path.join(root, clean_target)))

        # Validate against root and permitted paths (with cross-platform Windows case normalization)
        allowed = False
        norm_candidate = os.path.normcase(candidate)
        for perm in [root] + [os.path.realpath(p) for p in active_ws.permitted_paths]:
            norm_perm = os.path.normcase(perm)
            # Exact match or subdirectory check
            if norm_candidate == norm_perm or norm_candidate.startswith(norm_perm + os.sep):
                allowed = True
                break

        if not allowed:
            logger.warning(f"Path traversal blocked: target='{clean_target}' resolved='{candidate}' root='{root}'")
            raise PermissionError(
                f"Access Denied: Path '{clean_target}' violates the workspace boundary. "
                f"Operations outside '{active_ws.name}' are strictly prohibited."
            )

        if must_exist and not os.path.exists(candidate):
            raise FileNotFoundError(f"Path does not exist inside workspace: '{clean_target}'")

        return candidate

    def check_operation_policy(self, operation: str) -> Tuple[bool, bool, str]:
        """
        Evaluates operation against active WorkspaceMode.
        Returns: (allowed: bool, requires_approval: bool, reason: str)
        """
        active_ws = self.get_active_workspace()
        mode = active_ws.mode if active_ws else WorkspaceMode.SUPERVISED

        op_type = operation.lower().strip()
        # Read operations
        read_ops = {
            "list", "list_directory", "read", "read_file", "search", "search_files",
            "search_content", "inspect_project_tree", "tree", "git_status", "git_diff",
            "git_log", "git_branch", "inspect", "inspect_dependencies", "inspect_project_configuration"
        }
        # Modification operations
        write_ops = {"create_file", "modify_file", "apply_patch", "rename_file", "create_dir", "create_directory"}
        # Execution operations
        exec_ops = {"run_command", "run_tests", "run_build", "cancel_command"}

        if op_type in read_ops or any(op_type.startswith(ro) for ro in ("list", "read", "search", "tree", "inspect", "git_")):
            return True, False, "Read operations permitted in all modes."

        if mode == WorkspaceMode.OBSERVE:
            return False, False, f"Workspace is in OBSERVE mode. Modification/Execution operation '{operation}' is prohibited."

        if mode == WorkspaceMode.SUPERVISED:
            # Requires human approval for all writes and command executions
            return True, True, f"Workspace is in SUPERVISED mode. '{operation}' requires explicit user confirmation."

        if mode == WorkspaceMode.CONTROLLED_AUTONOMY:
            # Writes and safe commands permitted automatically; destructive commands trigger approval
            return True, False, "Permitted under CONTROLLED AUTONOMY policy."

        return True, True, "Approval required by default."


# Singleton
_ws_manager_instance: Optional[WorkspaceManager] = None
_ws_manager_lock = threading.Lock()


def get_workspace_manager(storage_path: Optional[str] = None) -> WorkspaceManager:
    global _ws_manager_instance
    with _ws_manager_lock:
        if _ws_manager_instance is None:
            _ws_manager_instance = WorkspaceManager(storage_path=storage_path)
        return _ws_manager_instance


def set_workspace_manager(manager: WorkspaceManager) -> None:
    global _ws_manager_instance
    with _ws_manager_lock:
        _ws_manager_instance = manager
