# ========== core/multi_agent/dispatcher.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Task Dispatcher
# Resolves DAG dependencies, manages concurrency, handles cancellation propagation, and dispatches tasks

import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Dict, List, Optional, Callable, Any, Set

from core.multi_agent.schema import TaskDefinition, TaskStatus
from core.multi_agent.executor import AgentExecutor

logger = logging.getLogger("misa.multi_agent.dispatcher")


class TaskDispatcher:
    """
    Coordinates execution of multi-agent plans.
    Enforces DAG dependencies, concurrency ceilings, intermediate result propagation,
    and cascading cancellation.
    """

    def __init__(self, executor: Optional[AgentExecutor] = None, max_concurrency: int = 4):
        self.executor = executor or AgentExecutor()
        self.max_concurrency = max_concurrency
        self._lock = threading.RLock()

    def dispatch_plan(
        self,
        tasks: List[TaskDefinition],
        cancel_event: Optional[threading.Event] = None,
        status_callback: Optional[Callable[[TaskDefinition], None]] = None
    ) -> List[TaskDefinition]:
        """
        Executes a collection of tasks respecting dependencies until all are finished.
        """
        if not tasks:
            return []

        task_map: Dict[str, TaskDefinition] = {t.task_id: t for t in tasks}
        intermediate_results: Dict[str, Any] = {}
        futures: Dict[Future, str] = {}
        completed_ids: Set[str] = set()
        failed_or_cancelled_ids: Set[str] = set()

        pool = ThreadPoolExecutor(max_workers=self.max_concurrency, thread_name_prefix="misa_agent_worker")

        try:
            while True:
                # 1. Check for global cancellation
                if cancel_event and cancel_event.is_set():
                    self._propagate_cancellation(tasks, status_callback)
                    break

                # 2. Check for blocked tasks (if any dependency failed or was cancelled)
                with self._lock:
                    for t in tasks:
                        if t.status in (TaskStatus.PENDING, TaskStatus.QUEUED):
                            if any(dep in failed_or_cancelled_ids for dep in t.dependencies):
                                t.status = TaskStatus.BLOCKED
                                t.error_message = "Blocked due to failed or cancelled dependency."
                                if status_callback:
                                    status_callback(t)

                # 3. Find newly eligible tasks (all dependencies in completed_ids)
                ready_tasks: List[TaskDefinition] = []
                with self._lock:
                    for t in tasks:
                        if t.status == TaskStatus.PENDING:
                            all_deps_done = all(dep in completed_ids for dep in t.dependencies)
                            if all_deps_done:
                                t.status = TaskStatus.QUEUED
                                ready_tasks.append(t)
                                if status_callback:
                                    status_callback(t)

                # 4. Schedule ready tasks up to concurrency limit
                for ready_task in ready_tasks:
                    # Package copy of intermediate results
                    with self._lock:
                        curr_results = dict(intermediate_results)
                    fut = pool.submit(
                        self.executor.execute_task,
                        task=ready_task,
                        intermediate_results=curr_results,
                        cancel_event=cancel_event,
                        status_callback=status_callback
                    )
                    futures[fut] = ready_task.task_id

                # 5. Check if all tasks are in a terminal state
                with self._lock:
                    all_terminal = all(
                        t.status in (
                            TaskStatus.COMPLETED,
                            TaskStatus.FAILED,
                            TaskStatus.CANCELLED,
                            TaskStatus.BLOCKED,
                            TaskStatus.WAITING_FOR_APPROVAL,
                        )
                        for t in tasks
                    )
                    if all_terminal and not futures:
                        break

                # 6. Wait for at least one running task to complete
                if futures:
                    done_futures = [f for f in futures if f.done()]
                    if not done_futures:
                        time.sleep(0.05)
                        continue

                    for df in done_futures:
                        tid = futures.pop(df)
                        try:
                            finished_task: TaskDefinition = df.result()
                            task_map[tid] = finished_task
                            with self._lock:
                                if finished_task.status == TaskStatus.COMPLETED:
                                    completed_ids.add(tid)
                                    if finished_task.output_result:
                                        intermediate_results[tid] = finished_task.output_result
                                elif finished_task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED):
                                    failed_or_cancelled_ids.add(tid)
                        except Exception as ex:
                            logger.error(f"Error retrieving task execution result for {tid}: {ex}")
                            with self._lock:
                                task_map[tid].status = TaskStatus.FAILED
                                task_map[tid].error_message = str(ex)
                                failed_or_cancelled_ids.add(tid)
                else:
                    time.sleep(0.05)

        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        return tasks

    def _propagate_cancellation(
        self,
        tasks: List[TaskDefinition],
        status_callback: Optional[Callable[[TaskDefinition], None]]
    ) -> None:
        """Cascades cancellation to all unfinished tasks."""
        with self._lock:
            for t in tasks:
                if t.status in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.REVIEWING):
                    t.status = TaskStatus.CANCELLED
                    t.error_message = "Task cancelled by parent plan cancellation."
                    t.completed_at = time.time()
                    if status_callback:
                        status_callback(t)
