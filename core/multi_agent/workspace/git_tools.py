# ========== core/multi_agent/workspace/git_tools.py ==========
# Misa AI 9.0.0 — Native Workspace Git Tools Engine
# Git status checks, diff inspections, branch tracking, commit history, and checkpointing.

import os
import subprocess
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.multi_agent.workspace.manager import WorkspaceManager, get_workspace_manager

logger = logging.getLogger("misa.multi_agent.workspace.git")


class GitEngine:
    """
    Git Inspection & Workflow Engine for local workspaces.
    Runs non-destructive Git queries and branch management.
    """

    def __init__(self, manager: Optional[WorkspaceManager] = None):
        self.manager = manager or get_workspace_manager()

    def _run_git(self, args: List[str]) -> Tuple[int, str, str]:
        active_ws = self.manager.get_active_workspace()
        if not active_ws:
            return 1, "", "No active workspace configured."

        root = active_ws.root_path
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=root,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=20.0
            )
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            return 1, "", str(e)

    def is_git_repository(self) -> bool:
        code, stdout, _ = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return code == 0 and "true" in stdout.lower()

    def git_status(self) -> Dict[str, Any]:
        """Returns clean/dirty state, modified, untracked, and staged files."""
        if not self.is_git_repository():
            return {
                "is_git": False,
                "clean": True,
                "modified": [],
                "untracked": [],
                "staged": [],
                "branch": "none"
            }

        # Branch name
        _, branch_out, _ = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        current_branch = branch_out.strip() or "main"

        # Porcelain status
        code, status_out, _ = self._run_git(["status", "--porcelain"])
        modified = []
        untracked = []
        staged = []

        for line in status_out.splitlines():
            if len(line) < 3:
                continue
            x = line[0]
            y = line[1]
            file_path = line[3:].strip()

            if x != " " and x != "?":
                staged.append(file_path)
            if y == "M" or y == "D":
                modified.append(file_path)
            if x == "?" and y == "?":
                untracked.append(file_path)

        return {
            "is_git": True,
            "clean": len(modified) == 0 and len(untracked) == 0 and len(staged) == 0,
            "branch": current_branch,
            "modified": modified,
            "untracked": untracked,
            "staged": staged,
        }

    def git_diff(self, cached: bool = False, file_path: Optional[str] = None) -> str:
        """Returns diff string for working tree or staged changes."""
        args = ["diff"]
        if cached:
            args.append("--cached")
        if file_path:
            args.append(file_path)
        code, stdout, stderr = self._run_git(args)
        return stdout if code == 0 else f"Error retrieving diff: {stderr}"

    def git_log(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent commits."""
        code, stdout, _ = self._run_git([
            "log",
            f"-n{limit}",
            "--pretty=format:%H%x09%an%x09%ad%x09%s",
            "--date=iso"
        ])
        commits: List[Dict[str, Any]] = []
        if code == 0 and stdout:
            for line in stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    })
        return commits

    def git_branch(self) -> Dict[str, Any]:
        """Lists local branches and current active branch."""
        code, stdout, _ = self._run_git(["branch"])
        branches = []
        current = "main"
        if code == 0 and stdout:
            for line in stdout.splitlines():
                clean = line.strip()
                if clean.startswith("*"):
                    current = clean[1:].strip()
                    branches.append(current)
                else:
                    branches.append(clean)
        return {"current_branch": current, "branches": branches}

    def git_create_branch(self, branch_name: str) -> Dict[str, Any]:
        """Creates and switches to a new Git branch."""
        b_clean = branch_name.strip()
        code, stdout, stderr = self._run_git(["checkout", "-b", b_clean])
        return {
            "ok": code == 0,
            "branch": b_clean,
            "message": stdout or stderr,
        }


# Singleton
_git_engine_instance: Optional[GitEngine] = None


def get_git_engine() -> GitEngine:
    global _git_engine_instance
    if _git_engine_instance is None:
        _git_engine_instance = GitEngine()
    return _git_engine_instance
