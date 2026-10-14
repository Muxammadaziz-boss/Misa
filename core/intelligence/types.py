# ========== types.py ==========
# Misa AI 7.x — Intelligence Core Types
# Normalized Data Structures for Context, Provider, Intent, Decision and Response

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntentCategory(str, Enum):
    CONVERSATION = "conversation"
    COMMAND = "command"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    TOOL_REQUEST = "tool_request"
    ERROR = "error"


class DecisionType(str, Enum):
    ANSWER = "answer"
    COMMAND = "command"
    TOOL = "tool"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"
    ERROR = "error"


@dataclass
class AIRequest:
    """Providerga yuboriladigan normalizatsiya qilingan so'rov"""
    message: str
    system_context: Dict[str, Any] = field(default_factory=dict)
    conversation: List[Dict[str, str]] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "system_context": self.system_context,
            "conversation": self.conversation,
            "memory": self.memory,
            "tools": self.tools,
            "metadata": self.metadata,
        }


@dataclass
class AIResponse:
    """AI provayderidan qaytadigan normalizatsiya qilingan javob"""
    provider: str
    model: str
    type: str = "answer"  # answer, command, clarification, confirmation, error
    content: str = ""
    intent: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    success: bool = True
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "type": self.type,
            "content": self.content,
            "intent": self.intent,
            "params": self.params,
            "usage": self.usage,
            "metadata": self.metadata,
            "success": self.success,
            "error_code": self.error_code,
        }


@dataclass
class Intent:
    """Aniqlangan niyat (Intent) ifodasi"""
    name: str
    category: IntentCategory = IntentCategory.CONVERSATION
    confidence: float = 1.0
    params: Dict[str, Any] = field(default_factory=dict)
    source: str = "llm"  # "llm", "local", "heuristic"
    requires_context: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value if isinstance(self.category, IntentCategory) else str(self.category),
            "confidence": self.confidence,
            "params": self.params,
            "source": self.source,
            "requires_context": self.requires_context,
        }


@dataclass
class Decision:
    """Qaror qabul qilish (Decision) qatlami chiqishi"""
    type: DecisionType
    content: str = ""
    intent: Optional[Intent] = None
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None
    clarification_question: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if isinstance(self.type, DecisionType) else str(self.type),
            "content": self.content,
            "intent": self.intent.to_dict() if self.intent else None,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "requires_confirmation": self.requires_confirmation,
            "confirmation_prompt": self.confirmation_prompt,
            "clarification_question": self.clarification_question,
        }


@dataclass
class IntelligenceResponse:
    """Intelligence Core ning yakuniy xulosaviy javobi"""
    type: str  # "answer", "command", "tool", "clarification", "confirmation", "error"
    content: str
    intent: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    tool_executed: Optional[str] = None
    tool_result: Optional[Any] = None
    verified: bool = True
    provider: str = "local"
    model: str = "none"
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_code: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.verified and self.type != "error"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "content": self.content,
            "intent": self.intent,
            "params": self.params,
            "tool_executed": self.tool_executed,
            "tool_result": self.tool_result,
            "verified": self.verified,
            "provider": self.provider,
            "model": self.model,
            "metadata": self.metadata,
            "error_code": self.error_code,
        }


# ========================================================
# AGENTIC MULTI-STEP EXECUTION TYPES (PHASE 31)
# ========================================================

class AgentState(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    VALIDATING = "validating"
    EXECUTING = "executing"
    OBSERVING = "observing"
    VERIFYING = "verifying"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class PlanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING_CONFIRMATION = "waiting_confirmation"


class VerificationStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class FailureCategory(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    PERMISSION_DENIED = "permission_denied"
    INVALID_PARAMETERS = "invalid_parameters"
    TOOL_UNAVAILABLE = "tool_unavailable"
    VERIFICATION_FAILED = "verification_failed"
    TIMEOUT = "timeout"
    SECURITY_BLOCKED = "security_blocked"


@dataclass
class VerificationResult:
    """Qadam natijasining verifikatsiya xulosasi"""
    verified: bool = False
    status: VerificationStatus = VerificationStatus.UNKNOWN
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified": self.verified,
            "status": self.status.value if isinstance(self.status, VerificationStatus) else str(self.status),
            "reason": self.reason,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        if not data:
            return cls()
        st = data.get("status", VerificationStatus.UNKNOWN)
        if isinstance(st, str):
            try:
                st = VerificationStatus(st)
            except ValueError:
                st = VerificationStatus.UNKNOWN
        return cls(
            verified=bool(data.get("verified", False)),
            status=st,
            reason=data.get("reason", ""),
            details=data.get("details", {}) or {},
        )


@dataclass
class StepResult:
    """Bajarilgan qadamning kuzatuv natijasi (OBSERVE)"""
    step_id: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    success: bool = False
    raw_result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "tool": self.tool,
            "parameters": self.parameters,
            "success": self.success,
            "raw_result": self.raw_result,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class PlanStep:
    """Agent rejasining bitta qadami (Planning Model 2.0)"""
    step_id: str
    order: int
    intent: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_result: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    status: StepStatus = StepStatus.PENDING
    retry_count: int = 0
    max_retries: int = 1
    observed_result: Optional[Any] = None
    verification: Optional[VerificationResult] = None
    error: Optional[str] = None
    
    # Phase 33 — Planning Model 2.0 Field additions
    description: str = ""
    purpose: str = ""
    dependencies: List[str] = field(default_factory=list)
    required_capability: str = ""
    verification_policy: str = "oracle_or_heuristic"
    failure_reason: Optional[str] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    precondition: str = ""
    postcondition: str = ""
    expected_observation: str = ""

    def __post_init__(self):
        if not self.description:
            self.description = self.intent
        if not self.required_capability and self.tool:
            self.required_capability = self.tool
        if not self.failure_reason and self.error:
            self.failure_reason = self.error

    @property
    def selected_tool(self) -> str:
        return self.tool

    @selected_tool.setter
    def selected_tool(self, val: str):
        self.tool = val

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "order": self.order,
            "intent": self.intent,
            "tool": self.tool,
            "selected_tool": self.selected_tool,
            "description": self.description or self.intent,
            "purpose": self.purpose,
            "dependencies": list(self.dependencies),
            "required_capability": self.required_capability,
            "parameters": self.parameters,
            "expected_result": self.expected_result,
            "precondition": self.precondition,
            "postcondition": self.postcondition,
            "expected_observation": self.expected_observation,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "status": self.status.value if isinstance(self.status, StepStatus) else str(self.status),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "retry_policy": self.retry_policy,
            "verification_policy": self.verification_policy,
            "observed_result": self.observed_result,
            "verification": self.verification.to_dict() if self.verification else None,
            "error": self.error,
            "failure_reason": self.failure_reason or self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanStep":
        risk = data.get("risk_level", RiskLevel.LOW)
        if isinstance(risk, str):
            try:
                risk = RiskLevel(risk.lower())
            except ValueError:
                risk = RiskLevel.LOW
        status = data.get("status", StepStatus.PENDING)
        if isinstance(status, str):
            try:
                status = StepStatus(status.lower())
            except ValueError:
                status = StepStatus.PENDING
        ver_data = data.get("verification")
        verification = VerificationResult.from_dict(ver_data) if ver_data else None

        tool_val = str(data.get("selected_tool") or data.get("tool", ""))
        return cls(
            step_id=str(data.get("step_id", "")),
            order=int(data.get("order", 0)),
            intent=str(data.get("intent", "")),
            tool=tool_val,
            parameters=dict(data.get("parameters", {}) or {}),
            expected_result=str(data.get("expected_result", "")),
            risk_level=risk,
            status=status,
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 1)),
            observed_result=data.get("observed_result"),
            verification=verification,
            error=data.get("error"),
            description=str(data.get("description", "")),
            purpose=str(data.get("purpose", "")),
            dependencies=list(data.get("dependencies", []) or []),
            required_capability=str(data.get("required_capability", "")),
            verification_policy=str(data.get("verification_policy", "oracle_or_heuristic")),
            failure_reason=data.get("failure_reason"),
            retry_policy=dict(data.get("retry_policy", {}) or {}),
            precondition=str(data.get("precondition", "")),
            postcondition=str(data.get("postcondition", "")),
            expected_observation=str(data.get("expected_observation", "")),
        )


@dataclass
class AgentPlan:
    """Ko'p bosqichli agentlik rejasi (Planning Model 2.0)"""
    plan_id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.PENDING
    created_at: str = ""
    current_step_index: int = 0
    max_steps: int = 8
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Phase 33 — Planning Model 2.0 Field additions
    intent: str = ""
    desired_outcome: str = ""
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    updated_at: str = ""
    plan_version: int = 1
    replan_count: int = 0
    max_replans: int = 2
    replan_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.intent:
            self.intent = self.goal
        if not self.desired_outcome:
            self.desired_outcome = f"'{self.goal}' maqsadini to'liq muvaffaqiyatli bajarish"
        if not self.execution_order and self.steps:
            self.execution_order = [s.step_id for s in self.steps]
        if not self.required_capabilities and self.steps:
            caps = []
            for s in self.steps:
                c = s.required_capability or s.tool
                if c and c not in caps:
                    caps.append(c)
            self.required_capabilities = caps
        if not self.dependencies and self.steps:
            self.dependencies = {s.step_id: list(s.dependencies) for s in self.steps if s.dependencies}
        self.calculate_plan_risk()

    def get_step(self, step_id: str) -> Optional[PlanStep]:
        """step_id orqali qadamni topish"""
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def get_dependencies(self, step_id: str) -> List[str]:
        """Qadamning bog'liqliklarini olish"""
        if step_id in self.dependencies:
            return list(self.dependencies[step_id])
        s = self.get_step(step_id)
        return list(s.dependencies) if s else []

    def get_ready_steps(self) -> List[PlanStep]:
        """Barcha bog'liqliklari yakunlangan (COMPLETED) va bajarilishga tayyor qadamlar"""
        ready: List[PlanStep] = []
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}
        for s in self.steps:
            if s.status == StepStatus.PENDING:
                deps = self.get_dependencies(s.step_id)
                if all(dep in completed_ids for dep in deps):
                    ready.append(s)
        return ready

    def calculate_plan_risk(self) -> RiskLevel:
        """Reja xavf darajasini qadamlar xavfi asosida aniqlash"""
        if not self.steps:
            self.risk_level = RiskLevel.LOW
            return self.risk_level

        # Agar birorta qadam HIGH bo'lsa -> HIGH
        if any(s.risk_level == RiskLevel.HIGH for s in self.steps):
            self.risk_level = RiskLevel.HIGH
        elif any(s.risk_level == RiskLevel.MEDIUM for s in self.steps):
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW
        return self.risk_level

    def create_next_version(self, reason: str, changed_steps: Optional[List[str]] = None) -> int:
        """Rejaning yangi versiyasini yaratish va replan tarixiga yozish"""
        old_version = self.plan_version
        self.plan_version += 1
        self.replan_count += 1
        import datetime
        self.updated_at = datetime.datetime.now().isoformat()

        self.replan_history.append({
            "version": self.plan_version,
            "from_version": old_version,
            "to_version": self.plan_version,
            "reason": reason,
            "changed_steps": changed_steps or [],
            "timestamp": self.updated_at,
        })
        return self.plan_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "intent": self.intent,
            "desired_outcome": self.desired_outcome,
            "assumptions": list(self.assumptions),
            "constraints": list(self.constraints),
            "steps": [s.to_dict() for s in self.steps],
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "execution_order": list(self.execution_order),
            "required_capabilities": list(self.required_capabilities),
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "status": self.status.value if isinstance(self.status, PlanStatus) else str(self.status),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "plan_version": self.plan_version,
            "replan_count": self.replan_count,
            "max_replans": self.max_replans,
            "replan_history": self.replan_history,
            "current_step_index": self.current_step_index,
            "max_steps": self.max_steps,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPlan":
        st = data.get("status", PlanStatus.PENDING)
        if isinstance(st, str):
            try:
                st = PlanStatus(st.lower())
            except ValueError:
                st = PlanStatus.PENDING

        risk = data.get("risk_level", RiskLevel.LOW)
        if isinstance(risk, str):
            try:
                risk = RiskLevel(risk.lower())
            except ValueError:
                risk = RiskLevel.LOW

        raw_steps = data.get("steps", [])
        steps = [PlanStep.from_dict(s) if isinstance(s, dict) else s for s in raw_steps]

        return cls(
            plan_id=str(data.get("plan_id", "")),
            goal=str(data.get("goal", "")),
            steps=steps,
            status=st,
            created_at=str(data.get("created_at", "")),
            current_step_index=int(data.get("current_step_index", 0)),
            max_steps=int(data.get("max_steps", 8)),
            metadata=dict(data.get("metadata", {}) or {}),
            intent=str(data.get("intent", "")),
            desired_outcome=str(data.get("desired_outcome", "")),
            assumptions=list(data.get("assumptions", []) or []),
            constraints=list(data.get("constraints", []) or []),
            dependencies=dict(data.get("dependencies", {}) or {}),
            execution_order=list(data.get("execution_order", []) or []),
            required_capabilities=list(data.get("required_capabilities", []) or []),
            risk_level=risk,
            updated_at=str(data.get("updated_at", "")),
            plan_version=int(data.get("plan_version", 1)),
            replan_count=int(data.get("replan_count", 0)),
            max_replans=int(data.get("max_replans", 2)),
            replan_history=list(data.get("replan_history", []) or []),
        )


@dataclass
class AgentExecutionState:
    """Agentning joriy ijro holati"""
    state: AgentState = AgentState.IDLE
    current_plan: Optional[AgentPlan] = None
    completed_steps: List[PlanStep] = field(default_factory=list)
    failed_steps: List[PlanStep] = field(default_factory=list)
    active_step: Optional[PlanStep] = None
    start_time: float = 0.0
    total_execution_time: float = 0.0
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value if isinstance(self.state, AgentState) else str(self.state),
            "current_plan": self.current_plan.to_dict() if self.current_plan else None,
            "completed_steps": [s.to_dict() for s in self.completed_steps],
            "failed_steps": [s.to_dict() for s in self.failed_steps],
            "active_step": self.active_step.to_dict() if self.active_step else None,
            "total_execution_time": round(self.total_execution_time, 2),
            "trace_id": self.trace_id,
        }

