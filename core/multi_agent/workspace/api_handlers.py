# ========== core/multi_agent/workspace/api_handlers.py ==========
# Misa AI 9.0.0 — Workspace HTTP REST & WebSocket API Controller
# Endpoints for file management, terminal execution, Git inspections, project maps, and autonomous workflows.

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional
from aiohttp import web

from core.multi_agent.workspace.manager import get_workspace_manager
from core.multi_agent.workspace.fs_tools import get_filesystem_engine
from core.multi_agent.workspace.terminal_tools import get_terminal_engine
from core.multi_agent.workspace.git_tools import get_git_engine
from core.multi_agent.workspace.dev_tools import get_project_understanding_engine
from core.multi_agent.workspace.tool_registry import get_workspace_tool_registry
from core.multi_agent.workspace.schema import WorkspaceMode

logger = logging.getLogger("misa.multi_agent.workspace.api")


def _cors_json_response(data: Any, status: int = 200) -> web.Response:
    return web.json_response(
        data,
        status=status,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )


# ========================================================
# Workspace CRUD Handlers
# ========================================================

async def handle_workspace_get(request: web.Request) -> web.Response:
    """GET /api/workspace"""
    try:
        mgr = get_workspace_manager()
        active = mgr.get_active_workspace()
        all_ws = mgr.list_workspaces()
        return _cors_json_response({
            "ok": True,
            "data": {
                "active_workspace": active.to_dict() if active else None,
                "workspaces": [w.to_dict() for w in all_ws],
            }
        })
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_connect(request: web.Request) -> web.Response:
    """POST /api/workspace/connect"""
    try:
        body = await request.json()
        path = str(body.get("path", "")).strip()
        name = body.get("name")
        mode_str = str(body.get("mode", "supervised")).lower()

        try:
            mode = WorkspaceMode(mode_str)
        except ValueError:
            mode = WorkspaceMode.SUPERVISED

        ws = get_workspace_manager().connect_workspace(root_path=path, name=name, mode=mode)
        return _cors_json_response({"ok": True, "data": ws.to_dict()}, status=201)
    except FileNotFoundError as fnf:
        return _cors_json_response({"ok": False, "error": str(fnf)}, status=404)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=400)


async def handle_workspace_disconnect(request: web.Request) -> web.Response:
    """POST /api/workspace/disconnect"""
    try:
        body = await request.json()
        ws_id = str(body.get("workspace_id", "")).strip()
        ok = get_workspace_manager().disconnect_workspace(ws_id)
        return _cors_json_response({"ok": ok})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_select(request: web.Request) -> web.Response:
    """POST /api/workspace/select"""
    try:
        body = await request.json()
        ws_id = str(body.get("workspace_id", "")).strip()
        ok = get_workspace_manager().set_active_workspace(ws_id)
        return _cors_json_response({"ok": ok})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_mode(request: web.Request) -> web.Response:
    """POST /api/workspace/mode"""
    try:
        body = await request.json()
        ws_id = str(body.get("workspace_id", "")).strip()
        mode_str = str(body.get("mode", "supervised")).lower()
        mode = WorkspaceMode(mode_str)
        ws = get_workspace_manager().update_workspace_mode(ws_id, mode)
        return _cors_json_response({"ok": True, "data": ws.to_dict()})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=400)


# ========================================================
# File System Handlers
# ========================================================

async def handle_workspace_tree(request: web.Request) -> web.Response:
    """GET /api/workspace/tree"""
    try:
        max_depth = int(request.query.get("max_depth", 3))
        fs = get_filesystem_engine()
        tree_str = fs.inspect_project_tree(max_depth=max_depth)
        return _cors_json_response({"ok": True, "data": {"tree": tree_str}})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_files(request: web.Request) -> web.Response:
    """GET /api/workspace/files"""
    try:
        path = request.query.get("path", "")
        max_depth = int(request.query.get("max_depth", 1))
        fs = get_filesystem_engine()
        entries = fs.list_directory(rel_path=path, max_depth=max_depth)
        return _cors_json_response({"ok": True, "data": entries})
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_file_read(request: web.Request) -> web.Response:
    """GET /api/workspace/file/read"""
    try:
        path = request.query.get("path", "")
        start_line = int(request.query["start_line"]) if "start_line" in request.query else None
        end_line = int(request.query["end_line"]) if "end_line" in request.query else None

        fs = get_filesystem_engine()
        file_data = fs.read_file(rel_path=path, start_line=start_line, end_line=end_line)
        return _cors_json_response({"ok": True, "data": file_data})
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)
    except FileNotFoundError as fnf:
        return _cors_json_response({"ok": False, "error": str(fnf)}, status=404)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_file_create(request: web.Request) -> web.Response:
    """POST /api/workspace/file/create"""
    try:
        body = await request.json()
        path = str(body.get("path", "")).strip()
        content = body.get("content", "")
        agent_id = str(body.get("agent_id", "misa-main"))

        reg = get_workspace_tool_registry()
        res = reg.execute_tool("create_file", {"path": path, "content": content}, agent_id=agent_id)
        return _cors_json_response(res, status=201 if res.get("ok") else 400)
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_file_modify(request: web.Request) -> web.Response:
    """POST /api/workspace/file/modify"""
    try:
        body = await request.json()
        path = str(body.get("path", "")).strip()
        content = body.get("content", "")
        agent_id = str(body.get("agent_id", "misa-main"))

        reg = get_workspace_tool_registry()
        res = reg.execute_tool("modify_file", {"path": path, "content": content}, agent_id=agent_id)
        return _cors_json_response(res)
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_file_patch(request: web.Request) -> web.Response:
    """POST /api/workspace/file/patch"""
    try:
        body = await request.json()
        path = str(body.get("path", "")).strip()
        target = body.get("target_snippet", "")
        replacement = body.get("replacement_snippet", "")
        agent_id = str(body.get("agent_id", "misa-main"))

        reg = get_workspace_tool_registry()
        res = reg.execute_tool(
            "apply_patch",
            {"path": path, "target_snippet": target, "replacement_snippet": replacement},
            agent_id=agent_id
        )
        return _cors_json_response(res)
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_search(request: web.Request) -> web.Response:
    """GET /api/workspace/search"""
    try:
        query = request.query.get("query", "")
        mode = request.query.get("mode", "content")  # content | files
        base_path = request.query.get("base_path", "")

        fs = get_filesystem_engine()
        if mode == "files":
            results = fs.search_files(pattern=query, base_path=base_path)
        else:
            results = fs.search_content(query=query, base_path=base_path)

        return _cors_json_response({"ok": True, "data": results})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


# ========================================================
# Terminal & Command Handlers
# ========================================================

async def handle_workspace_command_run(request: web.Request) -> web.Response:
    """POST /api/workspace/command/run"""
    try:
        body = await request.json()
        command = str(body.get("command", "")).strip()
        cwd = body.get("cwd")
        timeout = float(body.get("timeout", 60.0))
        agent_id = str(body.get("agent_id", "misa-main"))

        reg = get_workspace_tool_registry()
        loop = asyncio.get_running_loop()

        res = await loop.run_in_executor(
            None,
            lambda: reg.execute_tool(
                "run_command",
                {"command": command, "cwd": cwd, "timeout": timeout},
                agent_id=agent_id
            )
        )
        return _cors_json_response(res)
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_command_cancel(request: web.Request) -> web.Response:
    """POST /api/workspace/command/cancel"""
    try:
        body = await request.json()
        cmd_id = str(body.get("command_id", "")).strip()
        reg = get_workspace_tool_registry()
        res = reg.execute_tool("cancel_command", {"command_id": cmd_id})
        return _cors_json_response(res)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


# ========================================================
# Git Handlers
# ========================================================

async def handle_workspace_git_status(request: web.Request) -> web.Response:
    """GET /api/workspace/git/status"""
    try:
        git = get_git_engine()
        status_data = git.git_status()
        return _cors_json_response({"ok": True, "data": status_data})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_git_diff(request: web.Request) -> web.Response:
    """GET /api/workspace/git/diff"""
    try:
        cached = request.query.get("cached", "false").lower() == "true"
        file_path = request.query.get("file_path")
        git = get_git_engine()
        diff_str = git.git_diff(cached=cached, file_path=file_path)
        return _cors_json_response({"ok": True, "data": {"diff": diff_str}})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_git_log(request: web.Request) -> web.Response:
    """GET /api/workspace/git/log"""
    try:
        limit = int(request.query.get("limit", 10))
        git = get_git_engine()
        commits = git.git_log(limit=limit)
        return _cors_json_response({"ok": True, "data": commits})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


# ========================================================
# Project Analysis & Dev Tools Handlers
# ========================================================

async def handle_workspace_project_analysis(request: web.Request) -> web.Response:
    """GET /api/workspace/project/analysis"""
    try:
        dev = get_project_understanding_engine()
        pmap = dev.analyze_project()
        return _cors_json_response({"ok": True, "data": pmap.to_dict()})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_project_tests(request: web.Request) -> web.Response:
    """POST /api/workspace/project/tests"""
    try:
        body = await request.json() if request.can_read_body else {}
        cmd = body.get("command")
        dev = get_project_understanding_engine()
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, lambda: dev.run_tests(custom_command=cmd))
        return _cors_json_response({"ok": res.status.value == "completed", "data": res.to_dict()})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_project_build(request: web.Request) -> web.Response:
    """POST /api/workspace/project/build"""
    try:
        body = await request.json() if request.can_read_body else {}
        cmd = body.get("command")
        dev = get_project_understanding_engine()
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, lambda: dev.run_build(custom_command=cmd))
        return _cors_json_response({"ok": res.status.value == "completed", "data": res.to_dict()})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_workspace_activity(request: web.Request) -> web.Response:
    """GET /api/workspace/activity"""
    try:
        limit = int(request.query.get("limit", 50))
        reg = get_workspace_tool_registry()
        acts = reg.get_recent_activity(limit=limit)
        return _cors_json_response({"ok": True, "data": acts})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


# ========================================================
# Autonomous Development Workflow (9-Step Pipeline)
# ========================================================

async def handle_workspace_workflow_execute(request: web.Request) -> web.Response:
    """
    POST /api/workspace/workflow/execute
    Executes the 9-Step Autonomous Development Workflow:
    UNDERSTAND -> ANALYZE -> PLAN -> DELEGATE -> IMPLEMENT -> EXECUTE -> REVIEW -> VERIFY -> REPORT
    """
    try:
        body = await request.json()
        request_query = str(body.get("prompt", "")).strip()
        if not request_query:
            return _cors_json_response({"ok": False, "error": "Prompt cannot be empty."}, status=400)

        from core.multi_agent.workspace.workflow import execute_autonomous_development_workflow

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: execute_autonomous_development_workflow(request_query)
        )
        return _cors_json_response({"ok": True, "data": result})
    except Exception as e:
        logger.error(f"Error in autonomous dev workflow: {e}")
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


def register_workspace_routes(app: web.Application) -> None:
    """Registers all Workspace execution engine routes on aiohttp API Server."""
    app.router.add_get("/api/workspace", handle_workspace_get)
    app.router.add_post("/api/workspace/connect", handle_workspace_connect)
    app.router.add_post("/api/workspace/disconnect", handle_workspace_disconnect)
    app.router.add_post("/api/workspace/select", handle_workspace_select)
    app.router.add_post("/api/workspace/mode", handle_workspace_mode)

    app.router.add_get("/api/workspace/tree", handle_workspace_tree)
    app.router.add_get("/api/workspace/files", handle_workspace_files)
    app.router.add_get("/api/workspace/file/read", handle_workspace_file_read)
    app.router.add_post("/api/workspace/file/create", handle_workspace_file_create)
    app.router.add_post("/api/workspace/file/modify", handle_workspace_file_modify)
    app.router.add_post("/api/workspace/file/patch", handle_workspace_file_patch)
    app.router.add_get("/api/workspace/search", handle_workspace_search)

    app.router.add_post("/api/workspace/command/run", handle_workspace_command_run)
    app.router.add_post("/api/workspace/command/cancel", handle_workspace_command_cancel)

    app.router.add_get("/api/workspace/git/status", handle_workspace_git_status)
    app.router.add_get("/api/workspace/git/diff", handle_workspace_git_diff)
    app.router.add_get("/api/workspace/git/log", handle_workspace_git_log)

    app.router.add_get("/api/workspace/project/analysis", handle_workspace_project_analysis)
    app.router.add_post("/api/workspace/project/tests", handle_workspace_project_tests)
    app.router.add_post("/api/workspace/project/build", handle_workspace_project_build)
    app.router.add_get("/api/workspace/activity", handle_workspace_activity)
    app.router.add_post("/api/workspace/workflow/execute", handle_workspace_workflow_execute)
    logger.info("Registered all Native Workspace Execution routes on API Server.")
