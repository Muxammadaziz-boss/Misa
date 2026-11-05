# ========== core/multi_agent/workspace/fs_tools.py ==========
# Misa AI 9.0.0 — Native Workspace File System Engine
# Safe file inspection, line-range reads, grep content search, structured patch application,
# unified diff generation, automatic snapshots, and concurrent write locks.

import os
import re
import difflib
import logging
import threading
import time
import shutil
from typing import Dict, Any, List, Optional, Tuple

from core.multi_agent.workspace.schema import FileMetadata
from core.multi_agent.workspace.manager import WorkspaceManager, get_workspace_manager
from core.common_paths import get_data_dir

logger = logging.getLogger("misa.multi_agent.workspace.fs")


class FileSystemEngine:
    """
    Controlled Local Workspace File System Engine.
    All operations are confined within the active workspace jail.
    """

    def __init__(self, manager: Optional[WorkspaceManager] = None):
        self.manager = manager or get_workspace_manager()
        self._lock = threading.RLock()
        self._file_locks: Dict[str, str] = {}  # safe_path -> agent_id
        self._backup_dir = os.path.join(get_data_dir(), "workspace_snapshots")
        os.makedirs(self._backup_dir, exist_ok=True)

    # ========================================================
    # Concurrency & Write Locks
    # ========================================================

    def acquire_file_lock(self, safe_path: str, agent_id: str, timeout: float = 5.0) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                current_owner = self._file_locks.get(safe_path)
                if current_owner is None or current_owner == agent_id:
                    self._file_locks[safe_path] = agent_id
                    return True
            time.sleep(0.05)
        return False

    def release_file_lock(self, safe_path: str, agent_id: str) -> None:
        with self._lock:
            if self._file_locks.get(safe_path) == agent_id:
                del self._file_locks[safe_path]

    # ========================================================
    # Inspection & Reading
    # ========================================================

    def list_directory(self, rel_path: str = "", max_depth: int = 1) -> List[Dict[str, Any]]:
        """Lists directory entries with metadata."""
        safe_dir = self.manager.resolve_safe_path(rel_path, must_exist=True)
        if not os.path.isdir(safe_dir):
            raise NotADirectoryError(f"Path '{rel_path}' is not a directory.")

        active_ws = self.manager.get_active_workspace()
        root = active_ws.root_path if active_ws else ""

        results: List[Dict[str, Any]] = []
        try:
            with os.scandir(safe_dir) as entries:
                for entry in entries:
                    # Ignore common noisy directories
                    if entry.name in (".git", "node_modules", "__pycache__", ".venv", "target", "dist"):
                        continue
                    try:
                        stat = entry.stat()
                        is_dir = entry.is_dir()
                        rel = os.path.relpath(entry.path, root)
                        results.append({
                            "name": entry.name,
                            "path": rel,
                            "is_dir": is_dir,
                            "size_bytes": stat.st_size if not is_dir else 0,
                            "modified_time": stat.st_mtime,
                            "extension": os.path.splitext(entry.name)[1].lower() if not is_dir else "",
                        })
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error listing directory {safe_dir}: {e}")
            raise

        # Sort folders first, then alphabetically
        results.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return results

    def read_file(
        self,
        rel_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        max_bytes: int = 250000
    ) -> Dict[str, Any]:
        """Reads file content safely with optional line-range slicing."""
        safe_path = self.manager.resolve_safe_path(rel_path, must_exist=True)
        if os.path.isdir(safe_path):
            raise IsADirectoryError(f"Path '{rel_path}' is a directory, not a file.")

        size = os.path.getsize(safe_path)
        if size > max_bytes and start_line is None:
            # Prevent context blowout on huge files
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(500)]
            truncated = True
        else:
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            truncated = False

        total_lines = len(lines)
        if start_line is not None:
            s_idx = max(0, start_line - 1)
            e_idx = end_line if end_line is not None else total_lines
            selected = lines[s_idx:e_idx]
        else:
            selected = lines

        return {
            "path": rel_path,
            "total_lines": total_lines,
            "start_line": start_line or 1,
            "end_line": end_line or len(selected),
            "content": "".join(selected),
            "size_bytes": size,
            "truncated": truncated,
        }

    def search_files(self, pattern: str, base_path: str = "") -> List[str]:
        """Finds file paths matching glob/regex pattern within workspace."""
        safe_base = self.manager.resolve_safe_path(base_path, must_exist=True)
        active_ws = self.manager.get_active_workspace()
        root = active_ws.root_path if active_ws else ""

        regex = re.compile(pattern.replace("*", ".*").replace("?", "."), re.IGNORECASE)
        matched_files: List[str] = []

        for current_root, dirs, files in os.walk(safe_base):
            # Prune noisy directories
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "target", "dist")]
            for f in files:
                if regex.search(f):
                    full_p = os.path.join(current_root, f)
                    rel_p = os.path.relpath(full_p, root)
                    matched_files.append(rel_p)
                    if len(matched_files) >= 200:
                        break

        return matched_files

    def search_content(
        self,
        query: str,
        base_path: str = "",
        extensions: Optional[List[str]] = None,
        max_matches: int = 50
    ) -> List[Dict[str, Any]]:
        """Grep search inside file contents."""
        safe_base = self.manager.resolve_safe_path(base_path, must_exist=True)
        active_ws = self.manager.get_active_workspace()
        root = active_ws.root_path if active_ws else ""

        q_lower = query.lower()
        matches: List[Dict[str, Any]] = []

        allowed_exts = set([e.lower() for e in extensions]) if extensions else None

        for current_root, dirs, files in os.walk(safe_base):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "target", "dist")]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if allowed_exts and ext not in allowed_exts:
                    continue
                # Skip binaries
                if ext in (".exe", ".dll", ".pyd", ".pyc", ".png", ".jpg", ".zip", ".rar", ".ico"):
                    continue

                full_p = os.path.join(current_root, f)
                try:
                    if os.path.getsize(full_p) > 1000000:
                        continue
                    with open(full_p, "r", encoding="utf-8", errors="replace") as fl:
                        for line_no, line in enumerate(fl, 1):
                            if q_lower in line.lower():
                                rel_p = os.path.relpath(full_p, root)
                                matches.append({
                                    "path": rel_p,
                                    "line_number": line_no,
                                    "snippet": line.strip()[:200],
                                })
                                if len(matches) >= max_matches:
                                    return matches
                except Exception:
                    pass

        return matches

    def inspect_project_tree(self, max_depth: int = 3, max_files: int = 150) -> str:
        """Generates visual text representation of project hierarchy."""
        active_ws = self.manager.get_active_workspace()
        if not active_ws:
            return "No workspace connected."

        root = active_ws.root_path
        lines = [f"{active_ws.name} ({root})"]
        file_count = 0

        def walk(current_dir: str, prefix: str, depth: int):
            nonlocal file_count
            if depth > max_depth or file_count >= max_files:
                return

            try:
                entries = sorted(os.scandir(current_dir), key=lambda e: (not e.is_dir(), e.name.lower()))
            except Exception:
                return

            # Filter noisy
            filtered = [
                e for e in entries
                if e.name not in (".git", "node_modules", "__pycache__", ".venv", "target", "dist", ".pytest_cache")
            ]

            for i, entry in enumerate(filtered):
                if file_count >= max_files:
                    lines.append(f"{prefix}... [truncated]")
                    break

                is_last = (i == len(filtered) - 1)
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
                file_count += 1

                if entry.is_dir():
                    extension = "    " if is_last else "│   "
                    walk(entry.path, prefix + extension, depth + 1)

        walk(root, "", 1)
        return "\n".join(lines)

    # ========================================================
    # File Modifications, Patches & Snapshots
    # ========================================================

    def _create_snapshot(self, safe_path: str) -> Optional[str]:
        """Creates a timestamped snapshot of a file prior to modification."""
        if not os.path.isfile(safe_path):
            return None
        try:
            rel = os.path.basename(safe_path)
            snap_name = f"{rel}_{int(time.time()*1000)}.bak"
            snap_path = os.path.join(self._backup_dir, snap_name)
            shutil.copy2(safe_path, snap_path)
            return snap_path
        except Exception as e:
            logger.warning(f"Could not create file snapshot for {safe_path}: {e}")
            return None

    def create_file(self, rel_path: str, content: str, agent_id: str = "misa-main") -> Dict[str, Any]:
        """Creates a new file. Fails if file already exists."""
        safe_path = self.manager.resolve_safe_path(rel_path)
        if os.path.exists(safe_path):
            raise FileExistsError(f"File '{rel_path}' already exists inside workspace.")

        if not self.acquire_file_lock(safe_path, agent_id):
            raise RuntimeError(f"File '{rel_path}' is locked by another agent.")

        try:
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)
            with open(safe_path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            return {
                "ok": True,
                "action": "create",
                "path": rel_path,
                "bytes_written": len(content.encode("utf-8")),
            }
        finally:
            self.release_file_lock(safe_path, agent_id)

    def modify_file(self, rel_path: str, new_content: str, agent_id: str = "misa-main") -> Dict[str, Any]:
        """Overwrites an existing file after generating diff and snapshot."""
        safe_path = self.manager.resolve_safe_path(rel_path, must_exist=True)
        if os.path.isdir(safe_path):
            raise IsADirectoryError(f"Path '{rel_path}' is a directory.")

        if not self.acquire_file_lock(safe_path, agent_id):
            raise RuntimeError(f"File '{rel_path}' is locked by another agent.")

        try:
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                old_content = f.read()

            diff_str = self.get_unified_diff(rel_path, old_content, new_content)
            snapshot_path = self._create_snapshot(safe_path)

            with open(safe_path, "w", encoding="utf-8", newline="") as f:
                f.write(new_content)

            return {
                "ok": True,
                "action": "modify",
                "path": rel_path,
                "diff": diff_str,
                "snapshot": snapshot_path,
                "bytes_written": len(new_content.encode("utf-8")),
            }
        finally:
            self.release_file_lock(safe_path, agent_id)

    def apply_patch(
        self,
        rel_path: str,
        target_snippet: str,
        replacement_snippet: str,
        agent_id: str = "misa-main"
    ) -> Dict[str, Any]:
        """Applies a surgical drop-in patch to an existing file."""
        safe_path = self.manager.resolve_safe_path(rel_path, must_exist=True)
        if not self.acquire_file_lock(safe_path, agent_id):
            raise RuntimeError(f"File '{rel_path}' is locked by another agent.")

        try:
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Normalize CRLF/LF for robust matching
            norm_content = content.replace("\r\n", "\n")
            norm_target = target_snippet.replace("\r\n", "\n")
            norm_replacement = replacement_snippet.replace("\r\n", "\n")

            if norm_target not in norm_content:
                raise ValueError(
                    f"Patch target snippet not found in file '{rel_path}'. "
                    "Ensure target snippet matches existing source text exactly."
                )

            patched_content = norm_content.replace(norm_target, norm_replacement, 1)

            # Preserve original line endings if CRLF was predominant
            if "\r\n" in content:
                patched_content = patched_content.replace("\n", "\r\n")

            diff_str = self.get_unified_diff(rel_path, content, patched_content)
            snapshot_path = self._create_snapshot(safe_path)

            with open(safe_path, "w", encoding="utf-8", newline="") as f:
                f.write(patched_content)

            return {
                "ok": True,
                "action": "patch",
                "path": rel_path,
                "diff": diff_str,
                "snapshot": snapshot_path,
            }
        finally:
            self.release_file_lock(safe_path, agent_id)

    def rename_file(self, old_rel_path: str, new_rel_path: str, agent_id: str = "misa-main") -> Dict[str, Any]:
        """Renames or moves a file within workspace bounds."""
        safe_old = self.manager.resolve_safe_path(old_rel_path, must_exist=True)
        safe_new = self.manager.resolve_safe_path(new_rel_path)

        if os.path.exists(safe_new):
            raise FileExistsError(f"Destination path '{new_rel_path}' already exists.")

        os.makedirs(os.path.dirname(safe_new), exist_ok=True)
        shutil.move(safe_old, safe_new)
        return {
            "ok": True,
            "action": "rename",
            "old_path": old_rel_path,
            "new_path": new_rel_path,
        }

    def create_directory(self, rel_path: str) -> Dict[str, Any]:
        """Creates directory safely within workspace."""
        safe_path = self.manager.resolve_safe_path(rel_path)
        os.makedirs(safe_path, exist_ok=True)
        return {"ok": True, "action": "create_dir", "path": rel_path}

    def get_unified_diff(self, path: str, original: str, modified: str) -> str:
        """Computes unified diff between original and modified text."""
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3
        )
        return "".join(diff)


# Singleton
_fs_engine_instance: Optional[FileSystemEngine] = None
_fs_engine_lock = threading.Lock()


def get_filesystem_engine() -> FileSystemEngine:
    global _fs_engine_instance
    with _fs_engine_lock:
        if _fs_engine_instance is None:
            _fs_engine_instance = FileSystemEngine()
        return _fs_engine_instance
