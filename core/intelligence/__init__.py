# ========== __init__.py ==========
# Misa AI 7.x — Intelligence Core Package
# Modular Intelligence Architecture (Context -> Intent -> Reasoning -> Decision -> Tool -> Verification -> Response)

from core.intelligence.types import (
    RiskLevel,
    IntentCategory,
    DecisionType,
    AIRequest,
    AIResponse,
    Intent,
    Decision,
    IntelligenceResponse,
    AgentState,
    PlanStatus,
    StepStatus,
    VerificationStatus,
    FailureCategory,
    VerificationResult,
    StepResult,
    PlanStep,
    AgentPlan,
    AgentExecutionState,
)
from core.intelligence.memory_types import (
    MemoryType,
    MemorySource,
    MemoryConfidence,
    MemoryItem,
    ActiveTaskContext,
)
from core.intelligence.memory_policy import (
    MemoryPolicy,
    PolicyDecision,
)
from core.intelligence.memory_retriever import MemoryRetriever
from core.intelligence.task_context import (
    TaskContextManager,
    get_task_context_manager,
)
from core.intelligence.provider import (
    AIProvider,
    ProviderManager,
)
from core.intelligence.gemini_provider import GeminiProvider
from core.intelligence.openrouter_provider import OpenRouterProvider
from core.intelligence.context import ContextEngine
from core.intelligence.intent import IntentEngine
from core.intelligence.decision import DecisionEngine
from core.intelligence.permission import PermissionEngine
from core.intelligence.verifier import AgentVerifier
from core.intelligence.agent_loop import AgentLoop, get_agent_loop
from core.intelligence.orchestrator import IntelligenceOrchestrator
from core.intelligence.adapter import CompatibilityAdapter
from core.intelligence.text_cleaner import extract_clean_response_text
from core.intelligence.planner import (
    GoalDecomposer,
    DependencyGraph,
    PlanOptimizer,
    PlanValidator,
    ReplanningEngine,
)
from core.intelligence.observability import (
    ContextTraceStage,
    ContextTrace,
    MemoryMetricsManager,
    ObservabilityManager,
    get_observability_manager,
    redact_sensitive_data,
    AGENT_TRACE_STAGES,
    CORE_TRACE_STAGES,
    TOOL_TRACE_STAGES,
    PLANNING_TRACE_STAGES,
    ALL_TRACE_STAGES,
)

__all__ = [
    "RiskLevel",
    "IntentCategory",
    "DecisionType",
    "AIRequest",
    "AIResponse",
    "Intent",
    "Decision",
    "IntelligenceResponse",
    "MemoryType",
    "MemorySource",
    "MemoryConfidence",
    "MemoryItem",
    "ActiveTaskContext",
    "MemoryPolicy",
    "PolicyDecision",
    "MemoryRetriever",
    "TaskContextManager",
    "get_task_context_manager",
    "AIProvider",
    "ProviderManager",
    "GeminiProvider",
    "OpenRouterProvider",
    "ContextEngine",
    "IntentEngine",
    "DecisionEngine",
    "PermissionEngine",
    "AgentVerifier",
    "AgentLoop",
    "get_agent_loop",
    "IntelligenceOrchestrator",
    "CompatibilityAdapter",
    "get_orchestrator",
    "ContextTraceStage",
    "ContextTrace",
    "MemoryMetricsManager",
    "ObservabilityManager",
    "get_observability_manager",
    "redact_sensitive_data",
    "AgentState",
    "PlanStatus",
    "StepStatus",
    "VerificationStatus",
    "FailureCategory",
    "VerificationResult",
    "StepResult",
    "PlanStep",
    "AgentPlan",
    "AgentExecutionState",
    "AGENT_TRACE_STAGES",
    "CORE_TRACE_STAGES",
    "GoalDecomposer",
    "DependencyGraph",
    "PlanOptimizer",
    "PlanValidator",
    "ReplanningEngine",
    "TOOL_TRACE_STAGES",
    "PLANNING_TRACE_STAGES",
    "ALL_TRACE_STAGES",
]


_orchestrator = None


def get_orchestrator() -> IntelligenceOrchestrator:
    """Global IntelligenceOrchestrator singleton instansiyasini olish"""
    global _orchestrator
    if _orchestrator is None:
        from core.agent_tools import get_registry
        from core.command_dispatcher import CommandDispatcher
        from core.intelligence.agent_loop import get_agent_loop

        registry = get_registry()
        dispatcher = CommandDispatcher()
        loop = get_agent_loop()

        _orchestrator = IntelligenceOrchestrator(
            tool_registry=registry,
            command_dispatcher=dispatcher,
            agent_loop=loop
        )
    return _orchestrator
