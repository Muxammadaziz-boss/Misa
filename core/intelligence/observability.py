# ========== observability.py ==========
# Misa AI 7.x — Context Observability, Pipeline Tracing & Memory Metrics
# Process-Local, Bounded, Sensitive-Redacted Telemetry Subsystem

import re
import time
import uuid
import datetime
import logging
from collections import deque
from threading import RLock
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core.intelligence.memory_policy import MemoryPolicy

logger = logging.getLogger(__name__)

# Extra patterns for sensitive strings
ADDITIONAL_SENSITIVE_PATTERNS = [
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{6,}", re.I),
    re.compile(r"sk-[a-zA-Z0-9_\-\.]{10,}", re.I),
    re.compile(r"AIza[0-9A-Za-z-_]{16,}", re.I),
    re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}", re.I),
    re.compile(r"sbp_[a-zA-Z0-9]{20,}", re.I),
    re.compile(r"misa_[a-zA-Z0-9]{20,}", re.I),
]

# Phase 30 Core Stages (11 stages)
CORE_TRACE_STAGES = [
    "REQUEST",
    "LOCAL_DISPATCH",
    "TASK_CONTEXT",
    "MEMORY_RETRIEVAL",
    "SELECTED_MEMORY",
    "PROVIDER",
    "INTENT",
    "PERMISSION",
    "DECISION",
    "TOOL",
    "RESPONSE",
]

# Phase 31 Agent Multi-Step Stages (10 stages)
AGENT_TRACE_STAGES = [
    "PLAN_CREATED",
    "PLAN_VALIDATED",
    "STEP_STARTED",
    "STEP_COMPLETED",
    "STEP_FAILED",
    "STEP_VERIFIED",
    "PLAN_PAUSED",
    "PLAN_RESUMED",
    "PLAN_COMPLETED",
    "PLAN_ABORTED",
]

# Phase 32 Tool System 2.0 Stages (9 stages)
TOOL_TRACE_STAGES = [
    "TOOL_DISCOVERED",
    "TOOL_SELECTED",
    "TOOL_VALIDATION_FAILED",
    "TOOL_PERMISSION_CHECKED",
    "TOOL_STARTED",
    "TOOL_COMPLETED",
    "TOOL_FAILED",
    "TOOL_TIMEOUT",
    "TOOL_BLOCKED",
]

# Phase 33 Planning & Reasoning 2.0 Stages (7 stages)
PLANNING_TRACE_STAGES = [
    "PLAN_OPTIMIZED",
    "STEP_DEPENDENCY_RESOLVED",
    "STEP_READY",
    "STEP_BLOCKED",
    "PLAN_REPLAN_REQUIRED",
    "PLAN_REPLANNED",
    "PLAN_VERSION_CREATED",
]

ALL_TRACE_STAGES = CORE_TRACE_STAGES + AGENT_TRACE_STAGES + TOOL_TRACE_STAGES + PLANNING_TRACE_STAGES


def redact_sensitive_data(obj: Any) -> Any:
    """Ma'lumotlar ichidagi har qanday maxfiy token, parol yoki API kalitlarni yashirish"""
    if isinstance(obj, str):
        redacted = obj
        for pattern in MemoryPolicy.SENSITIVE_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        for pattern in ADDITIONAL_SENSITIVE_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    elif isinstance(obj, dict):
        res = {}
        sensitive_keys = {
            "password", "api_key", "secret", "token", "auth", "credential",
            "private_key", "session_token", "jwt", "authorization",
            "access_token", "refresh_token", "cookie", "signature"
        }
        for k, v in obj.items():
            if any(sk in str(k).lower() for sk in sensitive_keys) and isinstance(v, str):
                res[k] = "[REDACTED]"
            else:
                res[k] = redact_sensitive_data(v)
        return res
    elif isinstance(obj, list):
        return [redact_sensitive_data(item) for item in obj]
    return obj


@dataclass
class ContextTraceStage:
    """Quvurdagi bitta intellektual bosqich qaydlari"""
    stage: str
    status: str = "ok"          # "ok", "skipped", "error"
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        safe_details = redact_sensitive_data(self.details)
        return {
            "stage": self.stage,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "details": safe_details,
            "data": safe_details,  # Alias for flexibility
        }


class ContextTrace:
    """So'rovning to'liq intellektual ijro izi (Context Trace)"""

    def __init__(
        self,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        query: str = ""
    ):
        self.trace_id = trace_id or request_id or str(uuid.uuid4())[:8]
        self.query = query
        self.start_time = time.time()
        self.timestamp = datetime.datetime.now().isoformat()
        self.stages: List[ContextTraceStage] = []
        self._current_stage_name: Optional[str] = None
        self._current_stage_start: float = 0.0
        self.success: bool = True
        self.duration_ms: float = 0.0

    def start_stage(self, stage_name: str):
        """Yangi bosqichni boshlash"""
        self._current_stage_name = stage_name
        self._current_stage_start = time.time()

    def end_stage(
        self,
        stage_name: Optional[str] = None,
        status: str = "ok",
        details: Optional[Dict[str, Any]] = None
    ):
        """Joriy bosqichni yakunlash"""
        name = stage_name or self._current_stage_name or "UNKNOWN"
        duration = (time.time() - self._current_stage_start) * 1000.0 if self._current_stage_start else 0.0
        stage = ContextTraceStage(
            stage=name,
            status=status,
            duration_ms=duration,
            details=redact_sensitive_data(details or {})
        )
        self.stages.append(stage)
        self._current_stage_name = None

    def add_stage(
        self,
        stage_name: str,
        status: Any = "ok",
        duration_ms: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Tayyor bosqichni qo'shish (status va details har xil tartibda yoki kwargs orqali bo'lishi mumkin)"""
        if isinstance(status, dict):
            details = status
            status = "ok"
        if details is None and "data" in kwargs:
            details = kwargs["data"]
        if "details" in kwargs and details is None:
            details = kwargs["details"]
        if "status" in kwargs:
            status = kwargs["status"]
        if "duration_ms" in kwargs:
            duration_ms = kwargs["duration_ms"]

        safe_details = redact_sensitive_data(details or {})
        self.stages.append(ContextTraceStage(
            stage=stage_name,
            status=str(status),
            duration_ms=float(duration_ms),
            details=safe_details
        ))

    def finish(self, success: bool = True):
        """Trace jarayonini tugatish va umumiy davomiylikni hisoblash"""
        self.success = success
        self.duration_ms = round((time.time() - self.start_time) * 1000.0, 2)

    def to_dict(self) -> Dict[str, Any]:
        total_duration = self.duration_ms or round((time.time() - self.start_time) * 1000.0, 2)
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "timestamp": self.timestamp,
            "success": self.success,
            "total_duration_ms": total_duration,
            "duration_ms": total_duration,
            "stage_count": len(self.stages),
            "stages": [s.to_dict() for s in self.stages],
        }


class MemoryMetricsManager:
    """
    Xotira quyi tizimi uchun yengil va mahalliy (in-process) telemetriya metrikalari.
    Tashqi og'ir bazalar yoki xizmatlarga bog'lanmagan.
    """

    def __init__(self):
        self._lock = RLock()
        self.total_retrieval_requests = 0
        self.total_memories_retrieved = 0
        self.retrieval_hits = 0
        self.rejected_writes_total = 0
        self.rejected_writes_sensitive = 0
        self.rejected_writes_policy = 0
        self.deleted_items_count = 0

    @property
    def hit_count(self) -> int:
        with self._lock:
            return self.retrieval_hits

    @property
    def hit_rate(self) -> float:
        with self._lock:
            if self.total_retrieval_requests == 0:
                return 0.0
            return round(self.retrieval_hits / self.total_retrieval_requests, 3)

    @property
    def sensitive_data_rejections(self) -> int:
        with self._lock:
            return self.rejected_writes_sensitive

    @property
    def policy_rejections(self) -> int:
        with self._lock:
            return self.rejected_writes_policy

    @property
    def user_deletions(self) -> int:
        with self._lock:
            return self.deleted_items_count

    def record_retrieval(
        self,
        query_or_count: Any = 0,
        retrieved_count: int = 0,
        was_hit: Optional[bool] = None
    ):
        with self._lock:
            self.total_retrieval_requests += 1
            if isinstance(query_or_count, int):
                count = query_or_count
            else:
                count = retrieved_count
            self.total_memories_retrieved += count
            if was_hit is True or (was_hit is None and count > 0):
                self.retrieval_hits += 1

    def record_write_rejection(self, reason: str):
        with self._lock:
            self.rejected_writes_total += 1
            if "SENSITIVE" in reason:
                self.rejected_writes_sensitive += 1
            else:
                self.rejected_writes_policy += 1

    def record_sensitive_rejection(self):
        with self._lock:
            self.rejected_writes_total += 1
            self.rejected_writes_sensitive += 1

    def record_policy_rejection(self):
        with self._lock:
            self.rejected_writes_total += 1
            self.rejected_writes_policy += 1

    def record_deletion(self):
        with self._lock:
            self.deleted_items_count += 1

    def get_metrics(self, agent_memory=None) -> Dict[str, Any]:
        with self._lock:
            hit_rate = self.hit_rate
            avg_selected = 0.0
            if self.total_retrieval_requests > 0:
                avg_selected = round(self.total_memories_retrieved / self.total_retrieval_requests, 2)

            total_memories = 0
            active_memories = 0
            pinned_memories = 0
            superseded_memories = 0

            if agent_memory:
                try:
                    items = agent_memory.get_memory_items()
                    total_memories = len(items)
                    active_memories = sum(1 for m in items if (m.is_active() if callable(getattr(m, "is_active", None)) else bool(getattr(m, "is_active", True))))
                    pinned_memories = sum(1 for m in items if getattr(m, "pinned", False))
                    superseded_memories = sum(1 for m in items if not (m.is_active() if callable(getattr(m, "is_active", None)) else bool(getattr(m, "is_active", True))))
                except Exception as e:
                    logger.warning(f"Metrikalarda xotira hisoblash xatoligi: {e}")

            return {
                "total_memories": total_memories,
                "active_memories": active_memories,
                "pinned_memories": pinned_memories,
                "superseded_memories": superseded_memories,
                "retrieval_requests_total": self.total_retrieval_requests,
                "total_retrieval_requests": self.total_retrieval_requests,
                "memories_retrieved_total": self.total_memories_retrieved,
                "average_selected_per_request": avg_selected,
                "memory_hit_count": self.retrieval_hits,
                "memory_hit_rate": hit_rate,
                "hit_rate": hit_rate,
                "rejected_writes_total": self.rejected_writes_total,
                "rejected_writes_sensitive": self.rejected_writes_sensitive,
                "sensitive_data_rejections": self.rejected_writes_sensitive,
                "rejected_writes_policy": self.rejected_writes_policy,
                "policy_rejections": self.rejected_writes_policy,
                "deleted_items_total": self.deleted_items_count,
                "user_deletions": self.deleted_items_count,
            }

    def snapshot(self, agent_memory=None) -> Dict[str, Any]:
        """get_metrics uchun qulay alias"""
        return self.get_metrics(agent_memory=agent_memory)


class ObservabilityManager:
    """
    Kuzatuv (Observability) va so'rovlar izini (Context Trace) boshqaruvchi markaziy xizmat.
    Cheklangan RAM foydalanishi uchun 25 ta so'nggi traceni ring-bufferda saqlaydi.
    """

    def __init__(self, max_traces: int = 25):
        self._lock = RLock()
        self.max_traces = max_traces
        self._traces = deque(maxlen=max_traces)
        self.metrics = MemoryMetricsManager()

    def start_trace(self, query: str = "") -> ContextTrace:
        """Yangi ContextTrace boshlash"""
        return ContextTrace(query=query)

    def end_trace(self, trace: ContextTrace, success: bool = True):
        """Trace yakunlab xotiraga saqlash"""
        trace.finish(success=success)
        self.record_trace(trace)

    def create_trace(self, request_id: Optional[str] = None) -> ContextTrace:
        return ContextTrace(request_id=request_id)

    def record_trace(self, trace: ContextTrace):
        with self._lock:
            self._traces.append(trace)

    def get_trace(self, trace_id: str) -> Optional[ContextTrace]:
        with self._lock:
            for t in self._traces:
                if t.trace_id == trace_id:
                    return t
            return None

    def get_trace_obj(self, trace_id: str) -> Optional[ContextTrace]:
        """get_trace uchun qulay alias"""
        return self.get_trace(trace_id)

    def get_recent_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._traces)
            return [t.to_dict() for t in items[-limit:]]

    def get_all_traces(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [t.to_dict() for t in list(self._traces)]

    def get_last_trace(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._traces:
                return None
            last = self._traces[-1]
            return last.to_dict() if hasattr(last, "to_dict") else last

    def clear_traces(self):
        with self._lock:
            self._traces.clear()

    def clear(self):
        """clear_traces uchun qulay alias"""
        self.clear_traces()


# Global singleton
_observability_manager = None


def get_observability_manager() -> ObservabilityManager:
    """Global ObservabilityManager instansiyasini olish"""
    global _observability_manager
    if _observability_manager is None:
        _observability_manager = ObservabilityManager()
    return _observability_manager
