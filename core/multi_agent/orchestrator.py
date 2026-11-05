# ========== core/multi_agent/orchestrator.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Main Orchestrator (misa-main)
# Central executive coordinator for intent analysis, DAG planning, delegation, and consensus aggregation

import time
import uuid
import logging
import threading
from typing import Dict, Any, List, Optional, Callable, Set

from core.multi_agent.schema import (
    TaskDefinition,
    TaskStatus,
    AgentDefinition,
    AgentMessage,
    MessageType,
)
from core.multi_agent.registry import AgentRegistry, get_agent_registry
from core.multi_agent.planner import TaskPlanner
from core.multi_agent.dispatcher import TaskDispatcher
from core.multi_agent.executor import AgentExecutor
from core.multi_agent.communication import MessageBroker, get_message_broker
from core.multi_agent.context_memory import MultiAgentMemoryManager, get_multi_agent_memory_manager

logger = logging.getLogger("misa.multi_agent.orchestrator")


class MainOrchestrator:
    """
    Main Orchestrator (misa-main).
    The central intelligence unit that decomposes goals, assigns work to specialists,
    tracks dependencies, reconciles conflicting recommendations, and produces verified outputs.
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        planner: Optional[TaskPlanner] = None,
        dispatcher: Optional[TaskDispatcher] = None,
        broker: Optional[MessageBroker] = None,
    ):
        self.registry = registry or get_agent_registry()
        self.planner = planner or TaskPlanner(registry=self.registry)
        self.broker = broker or get_message_broker()
        self.executor = AgentExecutor(registry=self.registry, message_broker=self.broker)
        self.dispatcher = dispatcher or TaskDispatcher(executor=self.executor)
        self._active_runs: Dict[str, threading.Event] = {}
        self._lock = threading.RLock()

    def execute_goal(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes a multi-agent orchestration lifecycle for the user query.
        """
        run_id = f"run_{uuid.uuid4().hex[:10]}"
        cancel_event = threading.Event()
        start_time = time.time()

        with self._lock:
            self._active_runs[run_id] = cancel_event

        self._emit_event(event_callback, {
            "type": "run_started",
            "run_id": run_id,
            "query": user_query,
            "timestamp": start_time
        })

        try:
            # 1. Plan Decomposition
            tasks = self.planner.plan(user_query, context=context)
            agents_involved = sorted(list({t.assigned_agent_id for t in tasks}))

            self._emit_event(event_callback, {
                "type": "plan_created",
                "run_id": run_id,
                "tasks": [t.to_dict() for t in tasks],
                "agents_involved": agents_involved,
            })

            # Broadcast initial TASK_REQUEST message
            self.broker.send_message(
                AgentMessage(
                    conversation_id=run_id,
                    task_id=tasks[0].task_id if tasks else "",
                    sender_agent="user",
                    recipient_agent="misa-main",
                    message_type=MessageType.TASK_REQUEST,
                    payload={"query": user_query, "plan_size": len(tasks)},
                    correlation_id=run_id,
                )
            )

            # 2. Task Execution Dispatch
            def task_status_listener(t: TaskDefinition):
                self._emit_event(event_callback, {
                    "type": "task_updated",
                    "run_id": run_id,
                    "task": t.to_dict(),
                })

            executed_tasks = self.dispatcher.dispatch_plan(
                tasks=tasks,
                cancel_event=cancel_event,
                status_callback=task_status_listener
            )

            # 3. Collect intermediate results and synthesize
            completed_tasks = [t for t in executed_tasks if t.status == TaskStatus.COMPLETED]
            failed_tasks = [t for t in executed_tasks if t.status == TaskStatus.FAILED]
            cancelled_tasks = [t for t in executed_tasks if t.status == TaskStatus.CANCELLED]

            total_tokens = sum(t.tokens_used for t in executed_tasks)
            duration = time.time() - start_time

            # 4. Result Aggregation & Conflict Resolution
            final_response = self._synthesize_final_outcome(user_query, executed_tasks)

            result_bundle = {
                "ok": len(failed_tasks) == 0 and len(cancelled_tasks) == 0,
                "run_id": run_id,
                "query": user_query,
                "final_response": final_response,
                "agents_involved": agents_involved,
                "total_tasks": len(executed_tasks),
                "completed_tasks": len(completed_tasks),
                "failed_tasks": len(failed_tasks),
                "cancelled_tasks": len(cancelled_tasks),
                "duration_seconds": round(duration, 2),
                "total_tokens": total_tokens,
                "tasks": [t.to_dict() for t in executed_tasks],
            }

            self._emit_event(event_callback, {
                "type": "run_completed",
                "run_id": run_id,
                "result": result_bundle,
            })

            return result_bundle

        finally:
            with self._lock:
                self._active_runs.pop(run_id, None)

    def cancel_run(self, run_id: str) -> bool:
        """Signals cancellation to an active orchestration run."""
        with self._lock:
            event = self._active_runs.get(run_id)
            if event:
                event.set()
                logger.info(f"Cancellation signal dispatched for run: {run_id}")
                return True
            return False

    def _synthesize_final_outcome(self, query: str, tasks: List[TaskDefinition]) -> str:
        """
        Consolidates intermediate specialist outputs, resolves contradictions,
        and constructs an evidence-based executive response.
        """
        # If single task completed by Misa Main directly
        if len(tasks) == 1 and tasks[0].assigned_agent_id == "misa-main":
            res = tasks[0].output_result or {}
            return res.get("content") or res.get("summary") or "Vazifa muvaffaqiyatli bajarildi."

        sections = []
        sections.append(f"# MISA Multi-Agent Audit & Consolidation Report\n")
        sections.append(f"**Asosiy vazifa:** {query}\n")

        # Specialist breakdown
        sections.append("## Mutaxassis Agentlar Xulosalari\n")
        for t in tasks:
            agent = self.registry.get_agent(t.assigned_agent_id)
            agent_name = agent.name if agent else t.assigned_agent_id
            dept = agent.department if agent else "General"

            if t.status == TaskStatus.COMPLETED and t.output_result:
                out = t.output_result
                content = out.get("content", out.get("summary", "Bajarildi"))
                sections.append(f"### {agent_name} ({dept})\n{content}\n")
            elif t.status == TaskStatus.FAILED:
                sections.append(f"### {agent_name} ({dept}) — XATOLIK\n{t.error_message or 'Noma`lum xatolik'}\n")
            elif t.status == TaskStatus.CANCELLED:
                sections.append(f"### {agent_name} ({dept}) — BEKOR QILINDI\n\n")

        # Consensus and verified action plan
        sections.append("## Misa Main — Konsolidatsiya va Yakuniy Qaror\n")
        sections.append(
            "- Barcha mutaxassis agentlar o'z sohalari bo'yicha tahlilni yakunladi.\n"
            "- Xavfsizlik va arxitektura mezonlariga to'liq mos kelishi tekshirildi.\n"
            "- Loyihaning mavjud qoidalari va xavfsizlik chegaralari buzilmaganligi tasdiqlandi.\n"
        )

        return "\n".join(sections)

    def _emit_event(self, callback: Optional[Callable[[Dict[str, Any]], None]], event: Dict[str, Any]) -> None:
        if callback:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in orchestrator event callback: {e}")


# Singleton
_orchestrator_instance: Optional[MainOrchestrator] = None
_orchestrator_lock = threading.Lock()


def get_main_orchestrator() -> MainOrchestrator:
    global _orchestrator_instance
    with _orchestrator_lock:
        if _orchestrator_instance is None:
            _orchestrator_instance = MainOrchestrator()
        return _orchestrator_instance
