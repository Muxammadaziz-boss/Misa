# ========== core/multi_agent/workspace/workflow.py ==========
# Misa AI 9.0.0 — Autonomous Development Workflow Engine
# Executes the strict 9-step development lifecycle:
# UNDERSTAND -> ANALYZE -> PLAN -> DELEGATE -> IMPLEMENT -> EXECUTE -> REVIEW -> VERIFY -> REPORT

import time
import logging
from typing import Dict, Any, List, Optional, Callable

from core.multi_agent.workspace.manager import get_workspace_manager
from core.multi_agent.workspace.fs_tools import get_filesystem_engine
from core.multi_agent.workspace.terminal_tools import get_terminal_engine
from core.multi_agent.workspace.git_tools import get_git_engine
from core.multi_agent.workspace.dev_tools import get_project_understanding_engine
from core.multi_agent.workspace.tool_registry import get_workspace_tool_registry
from core.multi_agent.planner import TaskPlanner
from core.multi_agent.orchestrator import get_main_orchestrator

logger = logging.getLogger("misa.multi_agent.workspace.workflow")


def execute_autonomous_development_workflow(
    user_goal: str,
    event_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Executes an autonomous 9-step pair programming workflow inside the active workspace.
    """
    start_time = time.time()
    ws_mgr = get_workspace_manager()
    active_ws = ws_mgr.get_active_workspace()

    if not active_ws:
        raise RuntimeError("No active workspace connected.")

    fs = get_filesystem_engine()
    git = get_git_engine()
    dev = get_project_understanding_engine()
    reg = get_workspace_tool_registry()

    workflow_log: List[Dict[str, Any]] = []

    def emit_step(step_num: int, step_name: str, details: Dict[str, Any]):
        rec = {
            "step": step_num,
            "name": step_name,
            "timestamp": time.time(),
            "details": details,
        }
        workflow_log.append(rec)
        if event_callback:
            try:
                event_callback(rec)
            except Exception:
                pass
        logger.info(f"[Workflow Step {step_num}] {step_name}")

    # ========================================================
    # STEP 1 — UNDERSTAND
    # ========================================================
    emit_step(1, "UNDERSTAND", {
        "workspace": active_ws.name,
        "root_path": active_ws.root_path,
        "mode": active_ws.mode.value,
        "goal": user_goal,
    })
    git_stat = git.git_status()

    # ========================================================
    # STEP 2 — ANALYZE
    # ========================================================
    pmap = dev.analyze_project()
    relevant_files = fs.search_files("*", base_path="")[:20]
    emit_step(2, "ANALYZE", {
        "primary_language": pmap.primary_language,
        "frameworks": pmap.frameworks,
        "entrypoints": pmap.entrypoints,
        "dependencies_count": len(pmap.dependencies),
        "git_clean": git_stat.get("clean", True),
    })

    # ========================================================
    # STEP 3 — PLAN
    # ========================================================
    planner = TaskPlanner()
    plan_tasks = planner.plan(user_goal, context={"project": pmap.to_dict()})
    emit_step(3, "PLAN", {
        "total_subtasks": len(plan_tasks),
        "subtasks": [{"id": t.task_id, "title": t.title, "agent": t.assigned_agent_id} for t in plan_tasks],
    })

    # ========================================================
    # STEP 4 — DELEGATE
    # ========================================================
    assigned_specialists = sorted(list({t.assigned_agent_id for t in plan_tasks}))
    emit_step(4, "DELEGATE", {
        "assigned_specialists": assigned_specialists,
        "orchestrator": "misa-main",
    })

    # ========================================================
    # STEP 5 — IMPLEMENT
    # ========================================================
    # Execute plan through orchestrator
    orch = get_main_orchestrator()
    orch_result = orch.execute_goal(user_goal, context={"workspace_root": active_ws.root_path})

    files_modified = []
    # Inspect git diff to detect actual changes
    post_git_diff = git.git_diff()
    post_git_stat = git.git_status()
    files_modified = post_git_stat.get("modified", []) + post_git_stat.get("untracked", [])

    emit_step(5, "IMPLEMENT", {
        "files_modified": files_modified,
        "orchestration_ok": orch_result.get("ok", True),
    })

    # ========================================================
    # STEP 6 — EXECUTE
    # ========================================================
    commands_executed = []
    # If build command applies, run build
    build_rec = None
    if pmap.build_system and pmap.build_system != "Standard":
        build_rec = dev.run_build()
        commands_executed.append(build_rec.to_dict())

    emit_step(6, "EXECUTE", {
        "commands_executed": len(commands_executed),
        "build_status": build_rec.status.value if build_rec else "skipped",
    })

    # ========================================================
    # STEP 7 — REVIEW
    # ========================================================
    # Code security & quality review
    security_clearance = True
    security_notes = []
    if "rm -rf" in post_git_diff or "password" in post_git_diff.lower():
        security_clearance = False
        security_notes.append("Potential sensitive pattern detected in diff.")

    emit_step(7, "REVIEW", {
        "security_clearance": security_clearance,
        "security_auditor": "code-security-auditor",
        "notes": security_notes,
    })

    # ========================================================
    # STEP 8 — VERIFY
    # ========================================================
    # Run tests to evaluate actual results
    test_rec = dev.run_tests()
    commands_executed.append(test_rec.to_dict())
    tests_passed = test_rec.exit_code == 0
    emit_step(8, "VERIFY", {
        "test_command": test_rec.command,
        "tests_passed": tests_passed,
        "exit_code": test_rec.exit_code,
        "duration_seconds": test_rec.duration_seconds,
    })

    # ========================================================
    # STEP 9 — REPORT
    # ========================================================
    total_duration = round(time.time() - start_time, 2)
    final_report = {
        "ok": tests_passed and security_clearance,
        "goal": user_goal,
        "workspace": active_ws.name,
        "duration_seconds": total_duration,
        "summary": {
            "what_was_implemented": f"Autonomous implementation for: {user_goal}",
            "files_changed": files_modified,
            "commands_executed": [c.get("command") for c in commands_executed],
            "tests_passed": tests_passed,
            "tests_failed": not tests_passed,
            "remaining_issues": [] if tests_passed else [test_rec.error_message or test_rec.stderr[:200]],
        },
        "git_diff_preview": post_git_diff[:2000],
        "workflow_steps": workflow_log,
    }

    emit_step(9, "REPORT", final_report["summary"])
    return final_report
