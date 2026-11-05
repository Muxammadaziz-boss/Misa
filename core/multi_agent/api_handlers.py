# ========== core/multi_agent/api_handlers.py ==========
# Misa AI 9.0.0 — Native Multi-Agent HTTP REST & WebSocket API Handlers
# Implements REST endpoints for the Agent Registry, Orchestrator, Governance, and Telemetry

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from aiohttp import web

from core.multi_agent.registry import get_agent_registry
from core.multi_agent.orchestrator import get_main_orchestrator
from core.multi_agent.planner import TaskPlanner
from core.multi_agent.communication import get_message_broker
from core.multi_agent.governance import get_multi_agent_governance
from core.multi_agent.monitor import get_execution_monitor
from core.multi_agent.schema import AgentDefinition, AgentStatus

logger = logging.getLogger("misa.multi_agent.api")


def _cors_json_response(data: Any, status: int = 200) -> web.Response:
    """Helper to return JSON response with CORS headers."""
    return web.json_response(
        data,
        status=status,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }
    )


async def handle_multi_agent_overview(request: web.Request) -> web.Response:
    """GET /api/multi-agent/overview"""
    try:
        registry = get_agent_registry()
        monitor = get_execution_monitor()
        all_agents = registry.list_agents()

        active_count = sum(1 for a in all_agents if a.status in (AgentStatus.ACTIVE, AgentStatus.IDLE))
        disabled_count = sum(1 for a in all_agents if a.status == AgentStatus.DISABLED)
        error_count = sum(1 for a in all_agents if a.status == AgentStatus.ERROR)

        telemetry = monitor.get_telemetry_snapshot()

        return _cors_json_response({
            "ok": True,
            "data": {
                "total_agents": len(all_agents),
                "active_agents": active_count,
                "disabled_agents": disabled_count,
                "error_agents": error_count,
                "departments": registry.get_all_departments(),
                "total_capabilities": len(registry.get_all_capabilities()),
                "telemetry": telemetry,
            }
        })
    except Exception as e:
        logger.error(f"Error in handle_multi_agent_overview: {e}")
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_agents_list(request: web.Request) -> web.Response:
    """GET /api/multi-agent/agents"""
    try:
        registry = get_agent_registry()
        department = request.query.get("department")
        status_param = request.query.get("status")

        status = None
        if status_param:
            try:
                status = AgentStatus(status_param.lower())
            except ValueError:
                pass

        agents = registry.list_agents(department=department, status=status)
        return _cors_json_response({
            "ok": True,
            "data": [a.to_dict() for a in agents],
            "departments": registry.get_all_departments(),
            "capabilities": sorted(list(registry.get_all_capabilities())),
        })
    except Exception as e:
        logger.error(f"Error in handle_multi_agent_agents_list: {e}")
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_agent_get(request: web.Request) -> web.Response:
    """GET /api/multi-agent/agents/{agent_id}"""
    try:
        agent_id = request.match_info.get("agent_id", "")
        agent = get_agent_registry().get_agent(agent_id)
        if not agent:
            return _cors_json_response({"ok": False, "error": f"Agent '{agent_id}' not found."}, status=404)
        return _cors_json_response({"ok": True, "data": agent.to_dict()})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_agent_create(request: web.Request) -> web.Response:
    """POST /api/multi-agent/agents"""
    try:
        data = await request.json()
        agent = AgentDefinition.from_dict(data)
        saved = get_agent_registry().register_agent(agent)
        return _cors_json_response({"ok": True, "data": saved.to_dict()}, status=201)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=400)


async def handle_multi_agent_agent_update(request: web.Request) -> web.Response:
    """PUT /api/multi-agent/agents/{agent_id}"""
    try:
        agent_id = request.match_info.get("agent_id", "")
        updates = await request.json()
        updated = get_agent_registry().update_agent(agent_id, updates)
        return _cors_json_response({"ok": True, "data": updated.to_dict()})
    except KeyError:
        return _cors_json_response({"ok": False, "error": f"Agent '{agent_id}' not found."}, status=404)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=400)


async def handle_multi_agent_agent_delete(request: web.Request) -> web.Response:
    """DELETE /api/multi-agent/agents/{agent_id}"""
    try:
        agent_id = request.match_info.get("agent_id", "")
        deleted = get_agent_registry().delete_agent(agent_id)
        if not deleted:
            return _cors_json_response({"ok": False, "error": f"Agent '{agent_id}' not found."}, status=404)
        return _cors_json_response({"ok": True, "message": f"Agent '{agent_id}' deleted."})
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_agent_enable(request: web.Request) -> web.Response:
    """POST /api/multi-agent/agents/{agent_id}/enable"""
    agent_id = request.match_info.get("agent_id", "")
    ok = get_agent_registry().enable_agent(agent_id)
    if not ok:
        return _cors_json_response({"ok": False, "error": f"Agent '{agent_id}' not found."}, status=404)
    return _cors_json_response({"ok": True, "message": f"Agent '{agent_id}' enabled."})


async def handle_multi_agent_agent_disable(request: web.Request) -> web.Response:
    """POST /api/multi-agent/agents/{agent_id}/disable"""
    try:
        agent_id = request.match_info.get("agent_id", "")
        ok = get_agent_registry().disable_agent(agent_id)
        if not ok:
            return _cors_json_response({"ok": False, "error": f"Agent '{agent_id}' not found."}, status=404)
        return _cors_json_response({"ok": True, "message": f"Agent '{agent_id}' disabled."})
    except PermissionError as pe:
        return _cors_json_response({"ok": False, "error": str(pe)}, status=403)


async def handle_multi_agent_plan(request: web.Request) -> web.Response:
    """POST /api/multi-agent/plan - Preview DAG execution plan without executing"""
    try:
        body = await request.json()
        query = str(body.get("query", "")).strip()
        if not query:
            return _cors_json_response({"ok": False, "error": "Query parameter cannot be empty."}, status=400)

        planner = TaskPlanner()
        tasks = planner.plan(query, context=body.get("context"))
        return _cors_json_response({
            "ok": True,
            "data": {
                "query": query,
                "total_tasks": len(tasks),
                "tasks": [t.to_dict() for t in tasks],
                "agents_involved": sorted(list({t.assigned_agent_id for t in tasks})),
            }
        })
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_execute(request: web.Request) -> web.Response:
    """POST /api/multi-agent/execute - Executes a multi-agent orchestration lifecycle"""
    try:
        body = await request.json()
        query = str(body.get("query", "")).strip()
        if not query:
            return _cors_json_response({"ok": False, "error": "Query parameter cannot be empty."}, status=400)

        orchestrator = get_main_orchestrator()
        monitor = get_execution_monitor()

        # Capture app's loop for background thread events
        loop = asyncio.get_running_loop()

        def ws_event_broadcaster(event: Dict[str, Any]):
            # Import broadcast_ws dynamically
            try:
                from core.api_server import broadcast_ws
                asyncio.run_coroutine_threadsafe(
                    broadcast_ws("multi_agent_event", event),
                    loop
                )
            except Exception:
                pass

        # Run synchronously or in executor thread to prevent blocking event loop
        result = await loop.run_in_executor(
            None,
            lambda: orchestrator.execute_goal(
                user_query=query,
                context=body.get("context"),
                event_callback=ws_event_broadcaster
            )
        )

        # Record metrics in monitor
        monitor.record_run(result)

        return _cors_json_response({"ok": True, "data": result})
    except Exception as e:
        logger.error(f"Error in handle_multi_agent_execute: {e}")
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_cancel(request: web.Request) -> web.Response:
    """POST /api/multi-agent/cancel"""
    try:
        body = await request.json()
        run_id = str(body.get("run_id", "")).strip()
        if not run_id:
            return _cors_json_response({"ok": False, "error": "Missing run_id."}, status=400)

        ok = get_main_orchestrator().cancel_run(run_id)
        return _cors_json_response({"ok": ok, "message": f"Cancellation requested for {run_id}." if ok else "Run not active."})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_messages(request: web.Request) -> web.Response:
    """GET /api/multi-agent/messages"""
    try:
        conversation_id = request.query.get("conversation_id")
        task_id = request.query.get("task_id")
        limit = int(request.query.get("limit", 100))

        broker = get_message_broker()
        messages = broker.get_messages(conversation_id=conversation_id, task_id=task_id, limit=limit)
        return _cors_json_response({
            "ok": True,
            "data": [m.to_dict() for m in messages]
        })
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_approvals_list(request: web.Request) -> web.Response:
    """GET /api/multi-agent/approvals"""
    try:
        gov = get_multi_agent_governance()
        pending = gov.get_pending_approvals()
        return _cors_json_response({"ok": True, "data": pending})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_approval_approve(request: web.Request) -> web.Response:
    """POST /api/multi-agent/approvals/{token}/approve"""
    try:
        token = request.match_info.get("token", "")
        gov = get_multi_agent_governance()
        ok, msg, info = gov.approve_operation(token)
        return _cors_json_response({"ok": ok, "message": msg, "data": info}, status=200 if ok else 400)
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_approval_reject(request: web.Request) -> web.Response:
    """POST /api/multi-agent/approvals/{token}/reject"""
    try:
        token = request.match_info.get("token", "")
        body = await request.json() if request.can_read_body else {}
        reason = body.get("reason", "Declined by user")
        gov = get_multi_agent_governance()
        ok = gov.reject_operation(token, reason=reason)
        return _cors_json_response({"ok": ok, "message": "Rejected" if ok else "Token not found"})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_audit(request: web.Request) -> web.Response:
    """GET /api/multi-agent/audit"""
    try:
        limit = int(request.query.get("limit", 100))
        trail = get_multi_agent_governance().get_audit_trail(limit=limit)
        return _cors_json_response({"ok": True, "data": trail})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


async def handle_multi_agent_telemetry(request: web.Request) -> web.Response:
    """GET /api/multi-agent/telemetry"""
    try:
        snapshot = get_execution_monitor().get_telemetry_snapshot()
        return _cors_json_response({"ok": True, "data": snapshot})
    except Exception as e:
        return _cors_json_response({"ok": False, "error": str(e)}, status=500)


def register_multi_agent_routes(app: web.Application) -> None:
    """Registers all native multi-agent API endpoints on the aiohttp application."""
    app.router.add_get("/api/multi-agent/overview", handle_multi_agent_overview)
    app.router.add_get("/api/multi-agent/agents", handle_multi_agent_agents_list)
    app.router.add_post("/api/multi-agent/agents", handle_multi_agent_agent_create)
    app.router.add_get("/api/multi-agent/agents/{agent_id}", handle_multi_agent_agent_get)
    app.router.add_put("/api/multi-agent/agents/{agent_id}", handle_multi_agent_agent_update)
    app.router.add_delete("/api/multi-agent/agents/{agent_id}", handle_multi_agent_agent_delete)
    app.router.add_post("/api/multi-agent/agents/{agent_id}/enable", handle_multi_agent_agent_enable)
    app.router.add_post("/api/multi-agent/agents/{agent_id}/disable", handle_multi_agent_agent_disable)
    app.router.add_post("/api/multi-agent/plan", handle_multi_agent_plan)
    app.router.add_post("/api/multi-agent/execute", handle_multi_agent_execute)
    app.router.add_post("/api/multi-agent/cancel", handle_multi_agent_cancel)
    app.router.add_get("/api/multi-agent/messages", handle_multi_agent_messages)
    app.router.add_get("/api/multi-agent/approvals", handle_multi_agent_approvals_list)
    app.router.add_post("/api/multi-agent/approvals/{token}/approve", handle_multi_agent_approval_approve)
    app.router.add_post("/api/multi-agent/approvals/{token}/reject", handle_multi_agent_approval_reject)
    app.router.add_get("/api/multi-agent/audit", handle_multi_agent_audit)
    app.router.add_get("/api/multi-agent/telemetry", handle_multi_agent_telemetry)
    logger.info("Registered all Native Multi-Agent endpoints on API Server.")
