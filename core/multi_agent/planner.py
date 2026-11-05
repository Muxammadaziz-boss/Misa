# ========== core/multi_agent/planner.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Task Planner
# Decomposes goals into a Directed Acyclic Graph (DAG) of specialized subtasks

import re
import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Set, Tuple

from core.multi_agent.schema import TaskDefinition, TaskStatus, AgentDefinition, AgentStatus
from core.multi_agent.registry import AgentRegistry, get_agent_registry

logger = logging.getLogger("misa.multi_agent.planner")


class TaskPlanner:
    """
    Task Planner for MISA Native Multi-Agent Platform.
    Analyzes user intent, matches capabilities to registered specialist agents,
    and constructs a DAG-validated execution plan with explicit dependency tracking.
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or get_agent_registry()

    def plan(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
        max_depth: int = 3
    ) -> List[TaskDefinition]:
        """
        Decomposes user query into an executable sequence of TaskDefinitions.
        Supports both heuristic domain decomposition and capability-based specialist assignment.
        """
        query_clean = (user_query or "").strip()
        if not query_clean:
            return []

        root_task_id = f"task_{uuid.uuid4().hex[:10]}"
        context_dict = dict(context or {})

        # 1. Check if query is simple single-turn or requires multi-agent orchestration
        is_complex, domain_hints = self._analyze_query_complexity(query_clean)

        if not is_complex:
            # Direct single task for Misa Main
            return [
                TaskDefinition(
                    task_id=root_task_id,
                    root_task_id=root_task_id,
                    title="Direct Response",
                    description=query_clean,
                    assigned_agent_id="misa-main",
                    status=TaskStatus.PENDING,
                    dependencies=[],
                    input_context=context_dict,
                    depth=0,
                )
            ]

        # 2. Complex Goal: Build Multi-Agent DAG Plan
        tasks: List[TaskDefinition] = []
        dep_map: Dict[str, List[str]] = {}

        # Heuristic specialist mapping based on domain hints
        specialists = self._select_specialists_for_domains(domain_hints, query_clean)

        # Stage 1: Preliminary analysis tasks (can run concurrently)
        analysis_task_ids: List[str] = []
        for agent_id, subtask_title, subtask_desc in specialists:
            tid = f"task_{uuid.uuid4().hex[:10]}"
            task = TaskDefinition(
                task_id=tid,
                parent_task_id=root_task_id,
                root_task_id=root_task_id,
                title=subtask_title,
                description=f"{subtask_desc}\n\nScope: {query_clean}",
                assigned_agent_id=agent_id,
                status=TaskStatus.PENDING,
                dependencies=[],
                input_context=context_dict,
                depth=1,
            )
            tasks.append(task)
            analysis_task_ids.append(tid)

        # Stage 2: Synthesis and verification task (depends on all analysis tasks)
        synthesis_id = f"task_{uuid.uuid4().hex[:10]}"
        synthesis_task = TaskDefinition(
            task_id=synthesis_id,
            parent_task_id=root_task_id,
            root_task_id=root_task_id,
            title="Consolidate Findings & Produce Verified Outcome",
            description=f"Synthesize intermediate outputs from specialist agents and generate verified, actionable report for: {query_clean}",
            assigned_agent_id="misa-main",
            status=TaskStatus.PENDING,
            dependencies=analysis_task_ids,
            input_context=context_dict,
            depth=1,
        )
        tasks.append(synthesis_task)

        # 3. Validate DAG (Cycle Detection)
        self.validate_plan_dag(tasks)

        logger.info(f"Planned {len(tasks)} tasks for query: '{query_clean[:50]}...'")
        return tasks

    def _analyze_query_complexity(self, query: str) -> Tuple[bool, List[str]]:
        """Determines if query requires multi-specialist collaboration."""
        q = query.lower()
        words_in_q = set(re.findall(r"\b\w+\b", q))

        def has_any(keywords: List[str]) -> bool:
            for k in keywords:
                if len(k) <= 3:
                    if k in words_in_q:
                        return True
                else:
                    if k in q:
                        return True
            return False

        # Keywords triggering multi-specialist flows
        domains: List[str] = []
        if has_any(["audit", "tekshir", "xavfsizlik", "security", "zaiflik", "vulnerability"]):
            domains.append("security")
        if has_any(["arxitektura", "architecture", "tizim", "tuzilma", "boundary", "refactor"]):
            domains.append("architecture")
        if has_any(["frontend", "ui", "ux", "dizayn", "komponent", "tugma", "react", "interfeys"]):
            domains.append("frontend")
        if has_any(["backend", "api", "endpoint", "server", "marshrut", "aiohttp"]):
            domains.append("backend")
        if has_any(["baza", "database", "sqlite", "supabase", "jadval", "schema", "migratsiya"]):
            domains.append("database")
        if has_any(["ovoz", "audio", "mikrofon", "speech", "tts", "stt", "wake", "wakeword"]):
            domains.append("audio")
        if has_any(["test", "sinov", "qa", "pytest", "coverage", "tekshirish"]):
            domains.append("test")
        if has_any(["reliz", "release", "chiqarish", "packaging", "installer", "versiya"]):
            domains.append("release")
        if has_any(["tauri", "desktop", "oyna", "window", "rust", "tray"]):
            domains.append("desktop")
        if has_any(["prompt", "llm", "ai provayder", "gemini", "groq", "model"]):
            domains.append("ai")

        is_complex = len(domains) > 0 or len(q.split()) > 15
        return is_complex, domains

    def _select_specialists_for_domains(self, domains: List[str], query: str) -> List[Tuple[str, str, str]]:
        """Selects suitable specialists from registry based on matched domains."""
        specialists: List[Tuple[str, str, str]] = []

        if "security" in domains:
            specialists.append(("security-architect", "Security Architecture & Trust Boundaries", "Evaluate security policies, authentication flows, and attack vectors."))
            specialists.append(("code-security-auditor", "Code Security & Vulnerability Audit", "Inspect source code, dependencies, and configuration for exploitable patterns."))
            if "architecture" not in domains:
                specialists.append(("system-architect", "System Architecture & Boundaries", "Map structural boundaries and request lifecycles."))
            specialists.append(("test-architect", "Security Test Strategy & Gap Analysis", "Identify missing security test coverage and boundary edge cases."))

        elif "frontend" in domains:
            specialists.append(("ui-ux-architect", "UI/UX & Design Token Review", "Audit Ultra Glass aesthetic consistency, layout hierarchy, and usability."))
            specialists.append(("frontend-specialist", "Frontend Implementation & State Logic", "Inspect or implement React 19 components and backendService bindings."))
            specialists.append(("test-architect", "Frontend Regression & Component Testing", "Validate component rendering, responsive states, and error handling."))

        elif "backend" in domains:
            specialists.append(("system-architect", "Backend Architecture & Boundary Review", "Analyze asynchronous data flow and service ownership."))
            specialists.append(("backend-specialist", "Backend Service & API Implementation", "Design or review Python aiohttp route handlers and business logic."))
            specialists.append(("test-architect", "API Contract & Integration Testing", "Verify endpoints with unit and integration tests."))

        elif "audio" in domains:
            specialists.append(("audio-engineer", "Audio Pipeline & Hardware Analysis", "Review audio capture/playback, STT/TTS pipeline, and wake-word detector."))
            specialists.append(("backend-specialist", "Audio Service Integration", "Verify asynchronous audio service IPC and backend endpoints."))
            specialists.append(("test-architect", "Audio Pipeline Verification", "Ensure device fallback and error recovery pass test suites."))

        elif "database" in domains:
            specialists.append(("database-architect", "Database Schema & Migration Review", "Evaluate schema normalization, data integrity, and indexing."))
            specialists.append(("backend-specialist", "Persistence Integration", "Check repository patterns and ORM/raw SQL execution safety."))

        elif "desktop" in domains:
            specialists.append(("tauri-specialist", "Desktop Shell & Tauri Lifecycle Review", "Audit Tauri v2 configuration, window controls, and IPC security."))
            specialists.append(("frontend-specialist", "Desktop UI Integration", "Check desktop shell responsiveness and window drag behavior."))

        elif "release" in domains:
            specialists.append(("release-auditor", "Release Candidate & Build Verification", "Check package dependencies, changelog entries, and build artifacts."))
            specialists.append(("code-security-auditor", "Pre-Release Security Clearance", "Audit codebase for unredacted secrets or release vulnerabilities."))
            specialists.append(("test-architect", "Full Regression Verification", "Run full test suites across unit, integration, and UI tests."))

        elif "ai" in domains:
            specialists.append(("ai-architect", "AI Infrastructure & Model Routing Analysis", "Evaluate provider fallback, context budgeting, and routing tiers."))
            specialists.append(("prompt-engineer", "System Prompt & Persona Optimization", "Refine system instructions, few-shot examples, and output constraints."))

        else:
            # General technical request: System Architect + Project Manager
            specialists.append(("system-architect", "System Analysis & Architectural Design", "Analyze system capabilities, trade-offs, and technical feasibility."))
            specialists.append(("project-manager", "Milestone & Task Breakdown", "Structure implementation steps and acceptance criteria."))

        # Filter out disabled agents in registry
        active_specialists = []
        for aid, title, desc in specialists:
            agent = self.registry.get_agent(aid)
            if agent and agent.status in (AgentStatus.ACTIVE, AgentStatus.IDLE):
                active_specialists.append((aid, title, desc))

        return active_specialists or [("misa-main", "Primary Execution", "Direct orchestration and resolution.")]

    @staticmethod
    def validate_plan_dag(tasks: List[TaskDefinition]) -> None:
        """
        Validates that tasks form a valid Directed Acyclic Graph (DAG) with no circular dependencies.
        Raises ValueError if a cycle is detected.
        """
        task_ids = {t.task_id for t in tasks}
        graph: Dict[str, List[str]] = {t.task_id: [] for t in tasks}

        for t in tasks:
            for dep in t.dependencies:
                if dep in task_ids:
                    graph[dep].append(t.task_id)

        # Cycle detection using DFS coloring: 0=unvisited, 1=visiting, 2=visited
        visited: Dict[str, int] = {tid: 0 for tid in task_ids}

        def dfs(node: str) -> bool:
            visited[node] = 1
            for neighbor in graph.get(node, []):
                if visited[neighbor] == 1:
                    return True  # Cycle detected!
                if visited[neighbor] == 0:
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False

        for tid in task_ids:
            if visited[tid] == 0:
                if dfs(tid):
                    raise ValueError(f"Circular dependency detected in multi-agent plan involving task: {tid}")
