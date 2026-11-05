# ========== tests/test_workspace_execution_engine.py ==========
# Misa AI 9.0.0 — Comprehensive Workspace Execution Engine Test Suite
# Tests Workspace Manager, Sandbox Jail, File System Engine, Snapshots,
# Terminal Engine, Safety Policies, Project Understanding, and the 9-Step Autonomous Workflow.

import os
import sys
import time
import json
import pytest
import threading
from pathlib import Path
from unittest.mock import MagicMock

from core.multi_agent.workspace.schema import (
    WorkspaceConfig,
    WorkspaceMode,
    FileMetadata,
    CommandStatus,
    CommandExecutionRecord,
    ActivityEvent,
)
from core.multi_agent.workspace.manager import WorkspaceManager
from core.multi_agent.workspace.fs_tools import FileSystemEngine
from core.multi_agent.workspace.terminal_tools import TerminalEngine
from core.multi_agent.workspace.git_tools import GitEngine
from core.multi_agent.workspace.dev_tools import ProjectUnderstandingEngine
from core.multi_agent.workspace.tool_registry import WorkspaceToolRegistry
from core.multi_agent.workspace.workflow import execute_autonomous_development_workflow
from core.multi_agent.governance import MultiAgentGovernance


@pytest.fixture
def test_workspace_dir(tmp_path):
    """Creates a temporary workspace structure for testing."""
    ws_dir = tmp_path / "sample_project"
    ws_dir.mkdir(parents=True, exist_ok=True)

    # Add sample files
    (ws_dir / "README.md").write_text("# Sample Project\nWelcome to testing.", encoding="utf-8")
    (ws_dir / "package.json").write_text(json.dumps({
        "name": "sample-app",
        "version": "1.0.0",
        "scripts": {"test": "echo tests passed"},
        "dependencies": {"react": "^18.0.0", "express": "^4.18.0"}
    }, indent=2), encoding="utf-8")

    src_dir = ws_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "app.py").write_text("""# Sample App
def add(a, b):
    return a + b

def sub(a, b):
    return a - b
""", encoding="utf-8")

    return str(ws_dir)


@pytest.fixture
def ws_manager(test_workspace_dir, tmp_path):
    storage_path = str(tmp_path / "test_workspaces.json")
    mgr = WorkspaceManager(storage_path=storage_path)
    mgr.connect_workspace(test_workspace_dir, name="Sample Test Project", mode=WorkspaceMode.SUPERVISED)
    return mgr


# ========================================================
# 1. WORKSPACE MANAGER & SANDBOX JAIL TESTS
# ========================================================

class TestWorkspaceManager:
    def test_connect_and_active_workspace(self, ws_manager, test_workspace_dir):
        active = ws_manager.get_active_workspace()
        assert active is not None
        assert os.path.normpath(active.root_path) == os.path.normpath(test_workspace_dir)
        assert active.name == "Sample Test Project"
        assert active.mode == WorkspaceMode.SUPERVISED

    def test_mode_update(self, ws_manager):
        active = ws_manager.get_active_workspace()
        updated = ws_manager.update_mode(active.workspace_id, WorkspaceMode.OBSERVE)
        assert updated.mode == WorkspaceMode.OBSERVE
        assert ws_manager.get_active_workspace().mode == WorkspaceMode.OBSERVE

    def test_path_traversal_jail_blocks_escape(self, ws_manager):
        # 1. Parent folder navigation
        with pytest.raises(PermissionError) as exc_info:
            ws_manager.resolve_safe_path("../outside.txt")
        assert "Access Denied" in str(exc_info.value) or "boundary" in str(exc_info.value).lower()

        # 2. Deep nested relative traversal
        with pytest.raises(PermissionError):
            ws_manager.resolve_safe_path("src/../../outside.txt")

        # 3. System drive root escape on Windows
        with pytest.raises(PermissionError):
            ws_manager.resolve_safe_path("C:\\Windows\\System32\\cmd.exe")

    def test_mode_policy_enforcement(self, ws_manager):
        active = ws_manager.get_active_workspace()

        # In OBSERVE mode: reads are allowed, writes and terminal are forbidden
        ws_manager.update_mode(active.workspace_id, WorkspaceMode.OBSERVE)
        allowed, req_app, _ = ws_manager.check_operation_policy("read_file")
        assert allowed is True
        assert req_app is False

        allowed, _, reason = ws_manager.check_operation_policy("create_file")
        assert allowed is False
        assert "OBSERVE" in reason

        allowed, _, reason = ws_manager.check_operation_policy("run_command")
        assert allowed is False

        # In SUPERVISED mode: reads allowed without approval, writes require approval
        ws_manager.update_mode(active.workspace_id, WorkspaceMode.SUPERVISED)
        allowed, req_app, _ = ws_manager.check_operation_policy("read_file")
        assert allowed is True
        assert req_app is False

        allowed, req_app, _ = ws_manager.check_operation_policy("modify_file")
        assert allowed is True
        assert req_app is True

        # In CONTROLLED_AUTONOMY mode: safe writes allowed automatically
        ws_manager.update_mode(active.workspace_id, WorkspaceMode.CONTROLLED_AUTONOMY)
        allowed, req_app, _ = ws_manager.check_operation_policy("modify_file")
        assert allowed is True
        assert req_app is False


# ========================================================
# 2. FILE SYSTEM ENGINE TESTS
# ========================================================

class TestFileSystemEngine:
    def test_list_and_read_files(self, ws_manager):
        fs = FileSystemEngine(manager=ws_manager)
        entries = fs.list_directory("")
        names = [e["name"] for e in entries]
        assert "README.md" in names
        assert "package.json" in names
        assert "src" in names

        # Sliced read
        read_res = fs.read_file("src/app.py", start_line=2, end_line=3)
        assert "def add(a, b):" in read_res["content"]
        assert read_res["start_line"] == 2
        assert read_res["end_line"] == 3

    def test_create_and_patch_file(self, ws_manager):
        fs = FileSystemEngine(manager=ws_manager)
        create_res = fs.create_file("src/calculator.py", "def multiply(x, y):\n    return x * y\n")
        assert create_res["ok"] is True
        assert create_res["action"] == "create"

        # Apply drop-in patch
        old_part = "return x * y"
        new_part = "return x * y  # Multiplies two numbers"
        patch_res = fs.apply_patch("src/calculator.py", old_part, new_part)
        assert patch_res["ok"] is True
        assert patch_res["action"] == "patch"

        # Verify content
        read_res = fs.read_file("src/calculator.py")
        assert "# Multiplies two numbers" in read_res["content"]

    def test_file_modification_creates_snapshot(self, ws_manager):
        fs = FileSystemEngine(manager=ws_manager)
        mod_res = fs.modify_file("README.md", "# Modified Title\nNew description.")
        assert mod_res["ok"] is True
        assert mod_res["snapshot"] is not None
        assert os.path.exists(mod_res["snapshot"])

    def test_search_and_tree(self, ws_manager):
        fs = FileSystemEngine(manager=ws_manager)
        # Search content
        matches = fs.search_content("add(a, b)")
        assert len(matches) > 0
        assert any("src/app.py" in m["path"] or "src\\app.py" in m["path"] for m in matches)

        # Tree structure
        tree_text = fs.inspect_project_tree(max_depth=2)
        assert "Sample Test Project" in tree_text
        assert "README.md" in tree_text

    def test_concurrency_file_locks(self, ws_manager):
        fs = FileSystemEngine(manager=ws_manager)
        safe_path = ws_manager.resolve_safe_path("src/app.py")

        # Agent 1 acquires lock
        assert fs.acquire_file_lock(safe_path, "agent_1") is True
        # Agent 1 can re-acquire
        assert fs.acquire_file_lock(safe_path, "agent_1") is True
        # Agent 2 cannot acquire while agent 1 holds it
        assert fs.acquire_file_lock(safe_path, "agent_2", timeout=0.1) is False

        # Release lock
        fs.release_file_lock(safe_path, "agent_1")
        # Now Agent 2 can acquire
        assert fs.acquire_file_lock(safe_path, "agent_2") is True
        fs.release_file_lock(safe_path, "agent_2")


# ========================================================
# 3. TERMINAL ENGINE & POLICY TESTS
# ========================================================

class TestTerminalEngine:
    def test_execute_safe_command(self, ws_manager):
        term = TerminalEngine(manager=ws_manager)
        rec = term.run_command(f'"{sys.executable}" -c "print(\'MISA_AUTONOMY_OK\')"', timeout_seconds=10.0)
        assert rec.status == CommandStatus.COMPLETED
        assert "MISA_AUTONOMY_OK" in rec.stdout
        assert rec.exit_code == 0
        assert rec.duration_seconds >= 0.0

    def test_destructive_command_requires_approval(self, ws_manager):
        term = TerminalEngine(manager=ws_manager)
        rec = term.run_command("rm -rf /")
        assert rec.status == CommandStatus.WAITING_FOR_APPROVAL
        assert "requires human confirmation" in rec.error_message.lower()
        assert rec.exit_code is None

    def test_command_timeout(self, ws_manager):
        term = TerminalEngine(manager=ws_manager)
        # Sleep for 3 seconds with a 0.5 second timeout
        rec = term.run_command(f'"{sys.executable}" -c "import time; time.sleep(3)"', timeout_seconds=0.5)
        assert rec.status == CommandStatus.FAILED
        assert "timed out" in (rec.error_message or "").lower()


# ========================================================
# 4. PROJECT UNDERSTANDING & GIT TESTS
# ========================================================

class TestProjectUnderstanding:
    def test_project_analysis(self, ws_manager):
        dev = ProjectUnderstandingEngine(manager=ws_manager)
        pmap = dev.analyze_project()
        assert os.path.basename(pmap.root_path) == "sample_project"
        assert "Python" in pmap.languages or "JavaScript" in pmap.languages
        assert "react" in pmap.dependencies or "express" in pmap.dependencies


# ========================================================
# 5. WORKSPACE TOOL REGISTRY & TELEMETRY TESTS
# ========================================================

class TestWorkspaceToolRegistry:
    def test_tool_execution_and_activity_event(self, ws_manager):
        fs = FileSystemEngine(manager=ws_manager)
        term = TerminalEngine(manager=ws_manager)
        git = GitEngine(manager=ws_manager)
        dev = ProjectUnderstandingEngine(manager=ws_manager)
        gov = MultiAgentGovernance()

        reg = WorkspaceToolRegistry(
            manager=ws_manager,
            fs_engine=fs,
            terminal=term,
            git_engine=git,
            dev_engine=dev,
            governance=gov,
        )

        events_received = []
        reg.subscribe_activity(lambda ev: events_received.append(ev))

        # Execute read tool (read_file is allowed in SUPERVISED mode without approval)
        res = reg.execute_tool("read_file", {"rel_path": "README.md"}, agent_id="misa-main")
        assert res["ok"] is True
        assert "Sample Project" in res["data"]["content"]

        # Check emitted telemetry events
        assert len(events_received) >= 2  # "running" then "completed"
        assert events_received[-1].status == "completed"
        assert events_received[-1].tool_name == "read_file"


# ========================================================
# 6. 9-STEP AUTONOMOUS DEVELOPMENT WORKFLOW TESTS
# ========================================================

class TestAutonomousWorkflow:
    def test_execute_autonomous_development_workflow(self, ws_manager, monkeypatch):
        # Configure global manager singleton
        from core.multi_agent.workspace import manager, fs_tools, terminal_tools, git_tools, dev_tools, tool_registry
        from core.multi_agent import orchestrator

        # Switch to controlled autonomy for auto-execution in workflow test
        active = ws_manager.get_active_workspace()
        ws_manager.update_mode(active.workspace_id, WorkspaceMode.CONTROLLED_AUTONOMY)

        fs = FileSystemEngine(manager=ws_manager)
        term = TerminalEngine(manager=ws_manager)
        git = GitEngine(manager=ws_manager)
        dev = ProjectUnderstandingEngine(manager=ws_manager)
        reg = WorkspaceToolRegistry(
            manager=ws_manager,
            fs_engine=fs,
            terminal=term,
            git_engine=git,
            dev_engine=dev,
        )

        # Mock orchestrator.execute_goal and dev.run_tests to be independent of network
        mock_orch = MagicMock()
        mock_orch.execute_goal.return_value = {"ok": True, "result": "Implementation complete"}

        mock_test_rec = CommandExecutionRecord(
            command_id="cmd_test",
            command="python -m unittest",
            cwd=active.root_path,
            status=CommandStatus.COMPLETED,
            exit_code=0,
            stdout="Ran 2 tests in 0.001s. OK",
            stderr="",
            duration_seconds=0.01,
        )
        monkeypatch.setattr(dev, "run_tests", lambda: mock_test_rec)
        monkeypatch.setattr(orchestrator, "get_main_orchestrator", lambda: mock_orch)

        monkeypatch.setattr(manager, "_ws_manager_instance", ws_manager)
        monkeypatch.setattr(fs_tools, "_fs_engine_instance", fs)
        monkeypatch.setattr(terminal_tools, "_terminal_engine_instance", term)
        monkeypatch.setattr(git_tools, "_git_engine_instance", git)
        monkeypatch.setattr(dev_tools, "_project_engine_instance", dev)
        monkeypatch.setattr(tool_registry, "_workspace_tool_registry_instance", reg)

        steps_received = []

        result = execute_autonomous_development_workflow(
            user_goal="Inspect application and prepare unit test report",
            event_callback=lambda s: steps_received.append(s)
        )

        assert result["ok"] is True
        assert len(result["workflow_steps"]) == 9

        step_names = [s["name"] for s in result["workflow_steps"]]
        assert "UNDERSTAND" in step_names
        assert "ANALYZE" in step_names
        assert "PLAN" in step_names
        assert "DELEGATE" in step_names
        assert "IMPLEMENT" in step_names
        assert "EXECUTE" in step_names
        assert "REVIEW" in step_names
        assert "VERIFY" in step_names
        assert "REPORT" in step_names

        # Validate final report structure
        report = result["report"] if "report" in result else result["summary"]
        assert "what_was_implemented" in report
        assert "files_changed" in report
        assert "commands_executed" in report
        assert "tests_passed" in report
        assert "tests_failed" in report
