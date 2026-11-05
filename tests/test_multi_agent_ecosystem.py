# ========== tests/test_multi_agent_ecosystem.py ==========
# Misa AI 9.0.0 — Comprehensive Multi-Agent Test Suite
# Tests Registry, Planner, Dispatcher, Executor, Orchestrator, Communication, Memory, Governance, and Security

import os
import time
import json
import pytest
import threading
from typing import Dict, Any, List

from core.multi_agent.schema import (
    AgentDefinition,
    AgentStatus,
    PermissionCategory,
    PermissionProfile,
    ContextPolicy,
    MemoryPolicy,
    ExecutionLimits,
    ModelPreference,
    TaskDefinition,
    TaskStatus,
    AgentMessage,
    MessageType,
)
from core.multi_agent.registry import AgentRegistry
from core.multi_agent.planner import TaskPlanner
from core.multi_agent.communication import MessageBroker
from core.multi_agent.context_memory import MultiAgentMemoryManager
from core.multi_agent.governance import MultiAgentGovernance
from core.multi_agent.executor import AgentExecutor
from core.multi_agent.dispatcher import TaskDispatcher
from core.multi_agent.orchestrator import MainOrchestrator
from core.multi_agent.monitor import ExecutionMonitor


@pytest.fixture
def tmp_registry_path(tmp_path):
    return str(tmp_path / "test_agent_registry.json")


@pytest.fixture
def clean_registry(tmp_registry_path):
    return AgentRegistry(storage_path=tmp_registry_path)


# ========================================================
# 1. AGENT REGISTRY TESTS
# ========================================================

class TestAgentRegistry:
    def test_initial_15_agents_registered(self, clean_registry):
        agents = clean_registry.list_agents()
        assert len(agents) >= 15
        expected_ids = {
            "misa-main", "system-architect", "project-manager", "frontend-specialist",
            "backend-specialist", "tauri-specialist", "database-architect", "ai-architect",
            "prompt-engineer", "audio-engineer", "security-architect", "code-security-auditor",
            "ui-ux-architect", "test-architect", "release-auditor"
        }
        found_ids = {a.agent_id for a in agents}
        assert expected_ids.issubset(found_ids)

    def test_schema_validation_on_missing_fields(self):
        with pytest.raises(ValueError):
            AgentDefinition.from_dict({"agent_id": ""})

    def test_register_and_get_user_agent(self, clean_registry):
        custom = AgentDefinition(
            agent_id="custom-researcher",
            name="Custom Researcher",
            description="Performs deep literature analysis",
            role="Research Specialist",
            department="Research",
            system_instructions="You are a researcher.",
            capabilities=["literature_review", "data_extraction"],
            is_builtin=False,
        )
        clean_registry.register_agent(custom)
        fetched = clean_registry.get_agent("custom-researcher")
        assert fetched is not None
        assert fetched.name == "Custom Researcher"
        assert fetched.department == "Research"
        assert not fetched.is_builtin

    def test_builtin_agents_cannot_be_deleted(self, clean_registry):
        with pytest.raises(PermissionError):
            clean_registry.delete_agent("misa-main")
        with pytest.raises(PermissionError):
            clean_registry.delete_agent("security-architect")

    def test_delete_user_agent(self, clean_registry):
        custom = AgentDefinition(
            agent_id="temp-worker",
            name="Temp Worker",
            description="Temporary",
            role="Worker",
            department="General",
            system_instructions="Work",
            is_builtin=False,
        )
        clean_registry.register_agent(custom)
        assert clean_registry.get_agent("temp-worker") is not None
        deleted = clean_registry.delete_agent("temp-worker")
        assert deleted is True
        assert clean_registry.get_agent("temp-worker") is None

    def test_enable_and_disable_agent(self, clean_registry):
        assert clean_registry.disable_agent("system-architect") is True
        agent = clean_registry.get_agent("system-architect")
        assert agent.status == AgentStatus.DISABLED

        assert clean_registry.enable_agent("system-architect") is True
        agent = clean_registry.get_agent("system-architect")
        assert agent.status == AgentStatus.ACTIVE

    def test_cannot_disable_misa_main(self, clean_registry):
        with pytest.raises(PermissionError):
            clean_registry.disable_agent("misa-main")

    def test_capability_discovery(self, clean_registry):
        sec_agents = clean_registry.find_agents_by_capability("vulnerability")
        assert len(sec_agents) >= 1
        assert any(a.agent_id == "code-security-auditor" for a in sec_agents)

    def test_import_export_json(self, clean_registry):
        exported_str = clean_registry.export_agent_json("misa-main")
        data = json.loads(exported_str)
        assert data["agent_id"] == "misa-main"
        assert "capabilities" in data


# ========================================================
# 2. TASK PLANNER & DAG TESTS
# ========================================================

class TestTaskPlanner:
    def test_simple_query_produces_single_task(self, clean_registry):
        planner = TaskPlanner(registry=clean_registry)
        tasks = planner.plan("Salom, bugun ob-havo qanday?")
        assert len(tasks) == 1
        assert tasks[0].assigned_agent_id == "misa-main"
        assert tasks[0].dependencies == []

    def test_complex_security_audit_produces_dag(self, clean_registry):
        planner = TaskPlanner(registry=clean_registry)
        tasks = planner.plan("Audit the authentication architecture and missing security tests")
        assert len(tasks) >= 3

        # Should include security specialists
        assigned = {t.assigned_agent_id for t in tasks}
        assert "security-architect" in assigned
        assert "code-security-auditor" in assigned
        assert "misa-main" in assigned

        # Synthesis task must depend on upstream analysis tasks
        synthesis_task = [t for t in tasks if t.assigned_agent_id == "misa-main"][0]
        assert len(synthesis_task.dependencies) > 0

    def test_dag_validation_cycle_detection(self):
        t1 = TaskDefinition(task_id="t1", dependencies=["t2"])
        t2 = TaskDefinition(task_id="t2", dependencies=["t1"])
        with pytest.raises(ValueError, match="Circular dependency"):
            TaskPlanner.validate_plan_dag([t1, t2])


# ========================================================
# 3. COMMUNICATION PROTOCOL TESTS
# ========================================================

class TestMessageBroker:
    def test_send_and_subscribe(self):
        broker = MessageBroker()
        received = []

        def on_msg(m):
            received.append(m)

        broker.subscribe("frontend-specialist", on_msg)

        msg = AgentMessage(
            sender_agent="misa-main",
            recipient_agent="frontend-specialist",
            message_type=MessageType.TASK_REQUEST,
            payload={"task": "Implement UI Component"}
        )
        broker.send_message(msg)

        assert len(received) == 1
        assert received[0].message_type == MessageType.TASK_REQUEST
        assert received[0].payload["task"] == "Implement UI Component"

    def test_correlation_tracing(self):
        broker = MessageBroker()
        corr_id = "trace_123"

        msg1 = AgentMessage(task_id="t1", correlation_id=corr_id, sender_agent="a1", recipient_agent="a2")
        msg2 = AgentMessage(task_id="t2", correlation_id=corr_id, sender_agent="a2", recipient_agent="a1")
        broker.send_message(msg1)
        broker.send_message(msg2)

        traced = broker.get_messages(correlation_id=corr_id)
        assert len(traced) == 2


# ========================================================
# 4. CONTEXT & MEMORY ISOLATION TESTS
# ========================================================

class TestContextAndMemory:
    def test_private_memory_isolation(self, clean_registry):
        mem = MultiAgentMemoryManager()
        mem.record_agent_observation("security-architect", "Detected open port 8080")

        # security-architect private context
        sec_agent = clean_registry.get_agent("security-architect")
        sec_bundle = mem.assemble_context_for_agent(sec_agent)
        scratch = sec_bundle.get("agent_private_scratchpad", {})
        obs = [o["observation"] for o in scratch.get("observations", [])]
        assert "Detected open port 8080" in obs

        # frontend-specialist private context should NOT see security observation
        front_agent = clean_registry.get_agent("frontend-specialist")
        front_bundle = mem.assemble_context_for_agent(front_agent)
        front_scratch = front_bundle.get("agent_private_scratchpad", {})
        front_obs = [o["observation"] for o in front_scratch.get("observations", [])]
        assert "Detected open port 8080" not in front_obs


# ========================================================
# 5. GOVERNANCE & SECURITY TESTS
# ========================================================

class TestGovernanceAndSecurity:
    def test_read_only_agent_denied_write_tools(self, clean_registry):
        gov = MultiAgentGovernance()
        auditor = clean_registry.get_agent("code-security-auditor")
        assert auditor.permission_profile.read_only is True

        allowed, _, reason, _ = gov.check_tool_permission(auditor, "write_file", {"path": "test.txt"})
        assert allowed is False
        assert "read-only" in reason.lower()

    def test_destructive_command_triggers_human_approval(self, clean_registry):
        gov = MultiAgentGovernance()
        backend_agent = clean_registry.get_agent("backend-specialist")

        allowed, req_approval, _, token = gov.check_tool_permission(
            backend_agent,
            "run_command",
            {"command": "rm -rf /critical/data"}
        )
        assert allowed is True
        assert req_approval is True
        assert token is not None

        # Verify token in pending approvals
        pending = gov.get_pending_approvals()
        assert any(p["token"] == token for p in pending)

        # Approve token
        approved, msg, _ = gov.approve_operation(token)
        assert approved is True

        # Replay attempt must fail (one-time token)
        re_approved, _, _ = gov.approve_operation(token)
        assert re_approved is False


# ========================================================
# 6. EXECUTOR, DISPATCHER & ORCHESTRATOR TESTS
# ========================================================

class TestExecutionAndOrchestration:
    def test_task_state_machine_execution(self, clean_registry):
        executor = AgentExecutor(registry=clean_registry)
        task = TaskDefinition(
            title="Inspect Architecture",
            description="Inspect system interfaces",
            assigned_agent_id="system-architect",
        )
        assert task.status == TaskStatus.PENDING

        res = executor.execute_task(task)
        assert res.status == TaskStatus.COMPLETED
        assert res.output_result is not None
        assert res.completed_at is not None
        assert res.tokens_used > 0

    def test_dispatcher_concurrency_and_dependencies(self, clean_registry):
        dispatcher = TaskDispatcher(executor=AgentExecutor(registry=clean_registry), max_concurrency=2)

        t1 = TaskDefinition(task_id="t1", title="Task 1", description="Scope 1", assigned_agent_id="system-architect")
        t2 = TaskDefinition(task_id="t2", title="Task 2", description="Scope 2", assigned_agent_id="security-architect")
        t3 = TaskDefinition(task_id="t3", title="Synthesis", description="Scope 3", assigned_agent_id="misa-main", dependencies=["t1", "t2"])

        results = dispatcher.dispatch_plan([t1, t2, t3])
        assert all(t.status == TaskStatus.COMPLETED for t in results)

    def test_cancellation_propagation(self, clean_registry):
        dispatcher = TaskDispatcher(executor=AgentExecutor(registry=clean_registry))
        cancel_event = threading.Event()
        cancel_event.set()  # Pre-cancelled

        t1 = TaskDefinition(task_id="t1", title="Task 1", assigned_agent_id="system-architect")
        t2 = TaskDefinition(task_id="t2", title="Task 2", assigned_agent_id="security-architect", dependencies=["t1"])

        results = dispatcher.dispatch_plan([t1, t2], cancel_event=cancel_event)
        assert all(t.status == TaskStatus.CANCELLED for t in results)

    def test_main_orchestrator_end_to_end(self, clean_registry):
        orch = MainOrchestrator(registry=clean_registry)
        result = orch.execute_goal("Audit the authentication architecture and code security")

        assert result["ok"] is True
        assert len(result["agents_involved"]) >= 2
        assert result["total_tasks"] >= 2
        assert "Audit & Consolidation Report" in result["final_response"]
        assert result["duration_seconds"] >= 0.0

    def test_execution_monitor_telemetry(self):
        mon = ExecutionMonitor()
        sample_run = {
            "run_id": "test_run_1",
            "query": "Test query",
            "ok": True,
            "duration_seconds": 1.25,
            "total_tokens": 450,
            "agents_involved": ["system-architect", "misa-main"],
            "total_tasks": 2,
            "completed_tasks": 2,
            "tasks": [
                {
                    "assigned_agent_id": "system-architect",
                    "status": "completed",
                    "tokens_used": 200,
                    "started_at": 100.0,
                    "completed_at": 100.5,
                },
                {
                    "assigned_agent_id": "misa-main",
                    "status": "completed",
                    "tokens_used": 250,
                    "started_at": 100.5,
                    "completed_at": 101.25,
                }
            ]
        }
        mon.record_run(sample_run)
        snap = mon.get_telemetry_snapshot()
        assert snap["total_runs"] == 1
        assert snap["total_tasks"] == 2
        assert snap["overall_success_rate"] == 100.0
        assert "system-architect" in snap["agent_metrics"]
        assert snap["agent_metrics"]["system-architect"]["tasks_succeeded"] == 1
