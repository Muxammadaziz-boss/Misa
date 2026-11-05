# ========== core/multi_agent/workspace/terminal_tools.py ==========
# Misa AI 9.0.0 — Native Terminal Execution Engine
# Asynchronous process spawning, stdout/stderr streaming, execution timeout,
# command status tracking, and safe process tree cancellation.

import os
import re
import sys
import time
import uuid
import signal
import logging
import threading
import subprocess
from typing import Dict, Any, List, Optional, Tuple, Callable

from core.multi_agent.workspace.schema import CommandExecutionRecord, CommandStatus
from core.multi_agent.workspace.manager import WorkspaceManager, get_workspace_manager
from core.multi_agent.governance import get_multi_agent_governance

logger = logging.getLogger("misa.multi_agent.workspace.terminal")

# Safe command patterns (commonly used in development)
SAFE_DEV_COMMANDS = [
    r"^python\b",
    r"^pytest\b",
    r"^node\b",
    r"^npm\b",
    r"^npx\b",
    r"^cargo\b",
    r"^git\b",
    r"^dir\b",
    r"^echo\b",
    r"^tsc\b",
    r"^vite\b",
]

# Destructive or system-level command patterns requiring explicit user approval
DESTRUCTIVE_COMMANDS = [
    r"rm\s+-rf",
    r"del\s+/[fFqsSQ]",
    r"format\s+[a-zA-Z]:",
    r"shutdown",
    r"mkfs",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-fdx",
    r"drop\s+database",
    r"drop\s+table",
]


class TerminalEngine:
    """
    Controlled Local Workspace Terminal Engine.
    Executes development commands inside the active workspace directory,
    captures outputs incrementally, and enforces cancellation and timeouts.
    """

    def __init__(self, manager: Optional[WorkspaceManager] = None):
        self.manager = manager or get_workspace_manager()
        self._lock = threading.RLock()
        self._commands: Dict[str, CommandExecutionRecord] = {}
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._output_listeners: Dict[str, List[Callable[[str], None]]] = {}

    def run_command(
        self,
        command: str,
        cwd_relative: Optional[str] = None,
        timeout_seconds: float = 60.0,
        agent_id: str = "misa-main",
        on_output_chunk: Optional[Callable[[str], None]] = None
    ) -> CommandExecutionRecord:
        """
        Executes a command synchronously within the workspace boundaries.
        Captures stdout and stderr, enforces timeouts, and detects failures.
        """
        active_ws = self.manager.get_active_workspace()
        if not active_ws:
            raise RuntimeError("No active workspace configured.")

        # Resolve working directory inside workspace
        work_dir = self.manager.resolve_safe_path(cwd_relative or "")
        cmd_clean = command.strip()

        # Check for destructive patterns
        for pattern in DESTRUCTIVE_COMMANDS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                gov = get_multi_agent_governance()
                # Create approval challenge
                token_mgr = gov._token_manager
                token = token_mgr.create_token("run_command", {"command": cmd_clean}, ttl=300.0)
                cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
                record = CommandExecutionRecord(
                    command_id=cmd_id,
                    command=cmd_clean,
                    cwd=work_dir,
                    status=CommandStatus.WAITING_FOR_APPROVAL,
                    executed_by=agent_id,
                    error_message=f"Command requires human confirmation. Token: {token}",
                )
                with self._lock:
                    self._commands[cmd_id] = record
                return record

        cmd_id = f"cmd_{uuid.uuid4().hex[:8]}"
        record = CommandExecutionRecord(
            command_id=cmd_id,
            command=cmd_clean,
            cwd=work_dir,
            status=CommandStatus.RUNNING,
            started_at=time.time(),
            executed_by=agent_id,
        )

        with self._lock:
            self._commands[cmd_id] = record

        stdout_chunks: List[str] = []
        stderr_chunks: List[str] = []

        is_win = sys.platform.startswith("win")
        # On Windows use shell=True for builtin commands or pwsh/cmd
        shell_cmd = cmd_clean

        start_time = time.time()
        process = None

        try:
            process = subprocess.Popen(
                shell_cmd,
                cwd=work_dir,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                bufsize=1,
            )

            record.pid = process.pid
            with self._lock:
                self._active_processes[cmd_id] = process

            # Read stdout and stderr with timeout
            stdout_data, stderr_data = process.communicate(timeout=timeout_seconds)

            record.stdout = stdout_data or ""
            record.stderr = stderr_data or ""
            record.exit_code = process.returncode
            record.completed_at = time.time()
            record.duration_seconds = round(record.completed_at - start_time, 2)

            if process.returncode == 0:
                record.status = CommandStatus.COMPLETED
            else:
                record.status = CommandStatus.FAILED
                record.error_message = f"Process exited with non-zero code: {process.returncode}"

            if on_output_chunk and record.stdout:
                on_output_chunk(record.stdout)

        except subprocess.TimeoutExpired:
            logger.warning(f"Command '{cmd_clean}' timed out after {timeout_seconds}s.")
            self.cancel_command(cmd_id)
            record.status = CommandStatus.FAILED
            record.error_message = f"Execution timed out after {timeout_seconds} seconds."
            record.completed_at = time.time()
            record.duration_seconds = timeout_seconds

        except Exception as e:
            logger.error(f"Command execution error: {e}")
            record.status = CommandStatus.FAILED
            record.error_message = str(e)
            record.completed_at = time.time()
            record.duration_seconds = round(record.completed_at - start_time, 2)

        finally:
            with self._lock:
                self._active_processes.pop(cmd_id, None)

        return record

    def cancel_command(self, command_id: str) -> bool:
        """Terminates an active process safely (including entire child process tree on Windows)."""
        with self._lock:
            proc = self._active_processes.get(command_id)
            record = self._commands.get(command_id)

            if not proc:
                return False

            pid = proc.pid
            try:
                if sys.platform.startswith("win"):
                    # Use taskkill /F /T /PID on Windows to terminate process tree
                    subprocess.run(
                        f"taskkill /F /T /PID {pid}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5.0
                    )
                else:
                    proc.terminate()
                    time.sleep(0.2)
                    if proc.poll() is None:
                        proc.kill()
            except Exception as e:
                logger.warning(f"Error terminating process {pid}: {e}")

            if record:
                record.status = CommandStatus.CANCELLED
                record.completed_at = time.time()
                record.error_message = "Command was cancelled by user."

            self._active_processes.pop(command_id, None)
            return True

    def get_command_status(self, command_id: str) -> Optional[CommandExecutionRecord]:
        with self._lock:
            return self._commands.get(command_id)

    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [c.to_dict() for c in list(self._commands.values())[-limit:]]


# Singleton
_terminal_engine_instance: Optional[TerminalEngine] = None
_terminal_engine_lock = threading.Lock()


def get_terminal_engine() -> TerminalEngine:
    global _terminal_engine_instance
    with _terminal_engine_lock:
        if _terminal_engine_instance is None:
            _terminal_engine_instance = TerminalEngine()
        return _terminal_engine_instance
