# ========== core/multi_agent/monitor.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Observability & Performance Monitor
# Telemetry tracking, token budgets, failure rates, duration benchmarks, and health metrics

import time
import logging
import threading
from typing import Dict, Any, List, Optional

from core.multi_agent.schema import TaskDefinition, TaskStatus

logger = logging.getLogger("misa.multi_agent.monitor")


class ExecutionMonitor:
    """
    Centralized Observability & Telemetry Collector for Multi-Agent Runtime.
    Aggregates runtime statistics, latency, token consumption, and failure rates.
    """

    def __init__(self, max_run_history: int = 50):
        self._lock = threading.RLock()
        self._max_run_history = max_run_history
        self._total_runs = 0
        self._total_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._cancelled_tasks = 0
        self._total_tokens = 0
        self._recent_runs: List[Dict[str, Any]] = []
        self._agent_stats: Dict[str, Dict[str, Any]] = {}

    def record_run(self, run_data: Dict[str, Any]) -> None:
        """Records summary metrics of an orchestration run."""
        with self._lock:
            self._total_runs += 1
            self._total_tasks += run_data.get("total_tasks", 0)
            self._completed_tasks += run_data.get("completed_tasks", 0)
            self._failed_tasks += run_data.get("failed_tasks", 0)
            self._cancelled_tasks += run_data.get("cancelled_tasks", 0)
            self._total_tokens += run_data.get("total_tokens", 0)

            record = {
                "run_id": run_data.get("run_id"),
                "query": run_data.get("query"),
                "ok": run_data.get("ok", False),
                "duration_seconds": run_data.get("duration_seconds", 0.0),
                "total_tokens": run_data.get("total_tokens", 0),
                "agents_involved": run_data.get("agents_involved", []),
                "total_tasks": run_data.get("total_tasks", 0),
                "completed_tasks": run_data.get("completed_tasks", 0),
                "timestamp": time.time(),
            }
            self._recent_runs.append(record)
            if len(self._recent_runs) > self._max_run_history:
                self._recent_runs = self._recent_runs[-self._max_run_history:]

            # Record per-task metrics for individual agents
            for task_dict in run_data.get("tasks", []):
                aid = task_dict.get("assigned_agent_id", "unknown")
                st = task_dict.get("status")
                tok = task_dict.get("tokens_used", 0)
                dur = 0.0
                if task_dict.get("completed_at") and task_dict.get("started_at"):
                    dur = task_dict["completed_at"] - task_dict["started_at"]

                if aid not in self._agent_stats:
                    self._agent_stats[aid] = {
                        "tasks_executed": 0,
                        "tasks_succeeded": 0,
                        "tasks_failed": 0,
                        "total_tokens": 0,
                        "total_duration": 0.0,
                    }

                stat = self._agent_stats[aid]
                stat["tasks_executed"] += 1
                if st == TaskStatus.COMPLETED.value:
                    stat["tasks_succeeded"] += 1
                elif st == TaskStatus.FAILED.value:
                    stat["tasks_failed"] += 1
                stat["total_tokens"] += tok
                stat["total_duration"] += dur

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Returns unified dashboard metrics."""
        with self._lock:
            # Per agent summaries
            agent_summaries = {}
            for aid, stat in self._agent_stats.items():
                exec_count = stat["tasks_executed"]
                avg_dur = round(stat["total_duration"] / max(1, exec_count), 2)
                success_rate = round((stat["tasks_succeeded"] / max(1, exec_count)) * 100, 1)
                agent_summaries[aid] = {
                    "tasks_executed": exec_count,
                    "tasks_succeeded": stat["tasks_succeeded"],
                    "tasks_failed": stat["tasks_failed"],
                    "success_rate_percent": success_rate,
                    "avg_duration_seconds": avg_dur,
                    "total_tokens": stat["total_tokens"],
                }

            return {
                "total_runs": self._total_runs,
                "total_tasks": self._total_tasks,
                "completed_tasks": self._completed_tasks,
                "failed_tasks": self._failed_tasks,
                "cancelled_tasks": self._cancelled_tasks,
                "total_tokens": self._total_tokens,
                "overall_success_rate": round(
                    (self._completed_tasks / max(1, self._total_tasks)) * 100, 1
                ),
                "recent_runs": list(reversed(self._recent_runs)),
                "agent_metrics": agent_summaries,
            }


# Singleton
_monitor_instance: Optional[ExecutionMonitor] = None
_monitor_lock = threading.Lock()


def get_execution_monitor() -> ExecutionMonitor:
    global _monitor_instance
    with _monitor_lock:
        if _monitor_instance is None:
            _monitor_instance = ExecutionMonitor()
        return _monitor_instance
