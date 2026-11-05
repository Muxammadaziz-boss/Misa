# ========== core/multi_agent/workspace/schema.py ==========
# Misa AI 9.0.0 — Workspace Autonomy & Execution Engine Schemas
# Typed schemas for local project workspaces, operations, files, commands, and activity

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Union


class WorkspaceMode(str, Enum):
    OBSERVE = "observe"                      # Read-only inspection, no modifications
    SUPERVISED = "supervised"                # Read freely, propose changes, human approval required for writes/commands
    CONTROLLED_AUTONOMY = "controlled_autonomy"  # Auto modifications inside workspace, auto safe commands, approval for destructive actions


class CommandStatus(str, Enum):
    STARTED = "started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_APPROVAL = "waiting_for_approval"


@dataclass
class WorkspaceConfig:
    workspace_id: str
    name: str
    root_path: str
    permitted_paths: List[str] = field(default_factory=list)
    mode: WorkspaceMode = WorkspaceMode.SUPERVISED
    is_active: bool = False
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "root_path": self.root_path,
            "permitted_paths": list(self.permitted_paths),
            "mode": self.mode.value if isinstance(self.mode, WorkspaceMode) else str(self.mode),
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "settings": dict(self.settings),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceConfig":
        mode_val = str(data.get("mode", "supervised")).lower()
        try:
            mode = WorkspaceMode(mode_val)
        except ValueError:
            mode = WorkspaceMode.SUPERVISED
        return cls(
            workspace_id=str(data.get("workspace_id", f"ws_{uuid.uuid4().hex[:8]}")),
            name=str(data.get("name", "Project")),
            root_path=str(data.get("root_path", "")),
            permitted_paths=list(data.get("permitted_paths", [])),
            mode=mode,
            is_active=bool(data.get("is_active", False)),
            created_at=str(data.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))),
            updated_at=str(data.get("updated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))),
            settings=dict(data.get("settings", {})),
        )


@dataclass
class FileMetadata:
    path: str
    relative_path: str
    size_bytes: int
    is_dir: bool
    modified_time: float
    extension: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommandExecutionRecord:
    command_id: str
    command: str
    cwd: str
    status: CommandStatus = CommandStatus.STARTED
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    duration_seconds: float = 0.0
    pid: Optional[int] = None
    executed_by: str = "misa-main"
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command": self.command,
            "cwd": self.cwd,
            "status": self.status.value if isinstance(self.status, CommandStatus) else str(self.status),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "pid": self.pid,
            "executed_by": self.executed_by,
            "error_message": self.error_message,
        }


@dataclass
class ProjectMap:
    root_path: str
    primary_language: str = "unknown"
    languages: Dict[str, int] = field(default_factory=dict)
    frameworks: List[str] = field(default_factory=list)
    entrypoints: List[str] = field(default_factory=list)
    important_modules: List[str] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    test_framework: Optional[str] = None
    build_system: Optional[str] = None
    scanned_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActivityEvent:
    event_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:8]}")
    tool_name: str = ""
    operation: str = ""
    agent_id: str = "misa-main"
    status: str = "running"  # running, completed, failed, cancelled, waiting_for_approval
    started_at: float = field(default_factory=time.time)
    duration_seconds: float = 0.0
    output_preview: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
