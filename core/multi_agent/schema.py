# ========== core/multi_agent/schema.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Runtime Schemas
# Typed schemas, state machines, validation and serialization for multi-agent platform

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Union


class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    DISABLED = "disabled"
    ERROR = "error"


class PermissionCategory(str, Enum):
    READ = "read"
    ANALYZE = "analyze"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    BLOCKED = "blocked"


class MessageType(str, Enum):
    TASK_REQUEST = "TASK_REQUEST"
    TASK_ACCEPTED = "TASK_ACCEPTED"
    TASK_PROGRESS = "TASK_PROGRESS"
    TASK_RESULT = "TASK_RESULT"
    TASK_FAILED = "TASK_FAILED"
    REVIEW_REQUEST = "REVIEW_REQUEST"
    REVIEW_RESULT = "REVIEW_RESULT"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CONTEXT_REQUEST = "CONTEXT_REQUEST"


@dataclass
class ModelPreference:
    tier: str = "global_default"  # global_default, configured_reasoning, configured_coding, fast_chat
    preferred_model: Optional[str] = None
    fallback_enabled: bool = True
    temperature: float = 0.3
    max_tokens: int = 4096

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ModelPreference":
        if not data:
            return cls()
        return cls(
            tier=str(data.get("tier", "global_default")),
            preferred_model=data.get("preferred_model"),
            fallback_enabled=bool(data.get("fallback_enabled", True)),
            temperature=float(data.get("temperature", 0.3)),
            max_tokens=int(data.get("max_tokens", 4096)),
        )


@dataclass
class PermissionProfile:
    category: PermissionCategory = PermissionCategory.READ
    allowed_tools: List[str] = field(default_factory=list)
    denied_tools: List[str] = field(default_factory=list)
    requires_approval: bool = False
    read_only: bool = True
    allowed_paths: List[str] = field(default_factory=list)
    can_delegate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value if isinstance(self.category, PermissionCategory) else str(self.category)
        return d

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "PermissionProfile":
        if not data:
            return cls()
        cat_val = str(data.get("category", "read")).lower()
        try:
            category = PermissionCategory(cat_val)
        except ValueError:
            category = PermissionCategory.READ
        return cls(
            category=category,
            allowed_tools=list(data.get("allowed_tools", [])),
            denied_tools=list(data.get("denied_tools", [])),
            requires_approval=bool(data.get("requires_approval", False)),
            read_only=bool(data.get("read_only", True)),
            allowed_paths=list(data.get("allowed_paths", [])),
            can_delegate=bool(data.get("can_delegate", False)),
        )


@dataclass
class ContextPolicy:
    max_context_tokens: int = 8192
    include_user_profile: bool = True
    include_project_memory: bool = True
    shared_context_access: bool = True
    isolated_scratchpad: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ContextPolicy":
        if not data:
            return cls()
        return cls(
            max_context_tokens=int(data.get("max_context_tokens", 8192)),
            include_user_profile=bool(data.get("include_user_profile", True)),
            include_project_memory=bool(data.get("include_project_memory", True)),
            shared_context_access=bool(data.get("shared_context_access", True)),
            isolated_scratchpad=bool(data.get("isolated_scratchpad", True)),
        )


@dataclass
class MemoryPolicy:
    retention_days: int = 30
    persist_history: bool = True
    private_memory: bool = True
    max_stored_tasks: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "MemoryPolicy":
        if not data:
            return cls()
        return cls(
            retention_days=int(data.get("retention_days", 30)),
            persist_history=bool(data.get("persist_history", True)),
            private_memory=bool(data.get("private_memory", True)),
            max_stored_tasks=int(data.get("max_stored_tasks", 100)),
        )


@dataclass
class ExecutionLimits:
    timeout_seconds: float = 60.0
    max_tokens: int = 8192
    max_retries: int = 2
    max_delegation_depth: int = 3
    cost_budget_usd: float = 0.50

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ExecutionLimits":
        if not data:
            return cls()
        return cls(
            timeout_seconds=float(data.get("timeout_seconds", 60.0)),
            max_tokens=int(data.get("max_tokens", 8192)),
            max_retries=int(data.get("max_retries", 2)),
            max_delegation_depth=int(data.get("max_delegation_depth", 3)),
            cost_budget_usd=float(data.get("cost_budget_usd", 0.50)),
        )


@dataclass
class AgentDefinition:
    agent_id: str
    name: str
    description: str
    role: str
    department: str
    system_instructions: str
    capabilities: List[str] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    model_preference: ModelPreference = field(default_factory=ModelPreference)
    permission_profile: PermissionProfile = field(default_factory=PermissionProfile)
    context_policy: ContextPolicy = field(default_factory=ContextPolicy)
    memory_policy: MemoryPolicy = field(default_factory=MemoryPolicy)
    execution_limits: ExecutionLimits = field(default_factory=ExecutionLimits)
    status: AgentStatus = AgentStatus.ACTIVE
    version: str = "1.0.0"
    is_builtin: bool = False
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    updated_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "department": self.department,
            "system_instructions": self.system_instructions,
            "capabilities": list(self.capabilities),
            "available_tools": list(self.available_tools),
            "model_preference": self.model_preference.to_dict(),
            "permission_profile": self.permission_profile.to_dict(),
            "context_policy": self.context_policy.to_dict(),
            "memory_policy": self.memory_policy.to_dict(),
            "execution_limits": self.execution_limits.to_dict(),
            "status": self.status.value if isinstance(self.status, AgentStatus) else str(self.status),
            "version": self.version,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentDefinition":
        if not data.get("agent_id") or not data.get("name"):
            raise ValueError("AgentDefinition talab qilinadigan 'agent_id' yoki 'name' maydonlariga ega emas.")

        status_val = str(data.get("status", "active")).lower()
        try:
            status = AgentStatus(status_val)
        except ValueError:
            status = AgentStatus.ACTIVE

        return cls(
            agent_id=str(data["agent_id"]).strip(),
            name=str(data["name"]).strip(),
            description=str(data.get("description", "")).strip(),
            role=str(data.get("role", "")).strip(),
            department=str(data.get("department", "General")).strip(),
            system_instructions=str(data.get("system_instructions", "")),
            capabilities=list(data.get("capabilities", [])),
            available_tools=list(data.get("available_tools", [])),
            model_preference=ModelPreference.from_dict(data.get("model_preference")),
            permission_profile=PermissionProfile.from_dict(data.get("permission_profile")),
            context_policy=ContextPolicy.from_dict(data.get("context_policy")),
            memory_policy=MemoryPolicy.from_dict(data.get("memory_policy")),
            execution_limits=ExecutionLimits.from_dict(data.get("execution_limits")),
            status=status,
            version=str(data.get("version", "1.0.0")),
            is_builtin=bool(data.get("is_builtin", False)),
            created_at=str(data.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))),
            updated_at=str(data.get("updated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))),
        )


@dataclass
class AgentMessage:
    message_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    conversation_id: str = "default"
    task_id: str = ""
    sender_agent: str = "misa-main"
    recipient_agent: str = ""
    message_type: MessageType = MessageType.TASK_REQUEST
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "task_id": self.task_id,
            "sender_agent": self.sender_agent,
            "recipient_agent": self.recipient_agent,
            "message_type": self.message_type.value if isinstance(self.message_type, MessageType) else str(self.message_type),
            "payload": dict(self.payload),
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        mtype_val = str(data.get("message_type", "TASK_REQUEST"))
        try:
            mtype = MessageType(mtype_val)
        except ValueError:
            mtype = MessageType.TASK_REQUEST
        return cls(
            message_id=str(data.get("message_id", f"msg_{uuid.uuid4().hex[:12]}")),
            conversation_id=str(data.get("conversation_id", "default")),
            task_id=str(data.get("task_id", "")),
            sender_agent=str(data.get("sender_agent", "misa-main")),
            recipient_agent=str(data.get("recipient_agent", "")),
            message_type=mtype,
            payload=dict(data.get("payload", {})),
            correlation_id=str(data.get("correlation_id", "")),
            timestamp=float(data.get("timestamp", time.time())),
        )


@dataclass
class TaskDefinition:
    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:10]}")
    parent_task_id: Optional[str] = None
    root_task_id: Optional[str] = None
    title: str = ""
    description: str = ""
    assigned_agent_id: str = "misa-main"
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # task_ids that must complete first
    input_context: Dict[str, Any] = field(default_factory=dict)
    output_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    depth: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    requires_approval: bool = False
    approval_token: Optional[str] = None
    approval_granted: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "root_task_id": self.root_task_id or self.task_id,
            "title": self.title,
            "description": self.description,
            "assigned_agent_id": self.assigned_agent_id,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "dependencies": list(self.dependencies),
            "input_context": dict(self.input_context),
            "output_result": self.output_result,
            "error_message": self.error_message,
            "depth": self.depth,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "requires_approval": self.requires_approval,
            "approval_token": self.approval_token,
            "approval_granted": self.approval_granted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskDefinition":
        st_val = str(data.get("status", "pending")).lower()
        try:
            status = TaskStatus(st_val)
        except ValueError:
            status = TaskStatus.PENDING
        return cls(
            task_id=str(data.get("task_id", f"task_{uuid.uuid4().hex[:10]}")),
            parent_task_id=data.get("parent_task_id"),
            root_task_id=data.get("root_task_id"),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            assigned_agent_id=str(data.get("assigned_agent_id", "misa-main")),
            status=status,
            dependencies=list(data.get("dependencies", [])),
            input_context=dict(data.get("input_context", {})),
            output_result=data.get("output_result"),
            error_message=data.get("error_message"),
            depth=int(data.get("depth", 0)),
            created_at=float(data.get("created_at", time.time())),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            tokens_used=int(data.get("tokens_used", 0)),
            cost_usd=float(data.get("cost_usd", 0.0)),
            requires_approval=bool(data.get("requires_approval", False)),
            approval_token=data.get("approval_token"),
            approval_granted=data.get("approval_granted"),
        )
