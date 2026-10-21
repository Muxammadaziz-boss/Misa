# ========== core/mcp/bridge.py ==========
# Misa AI v9.0 — MCP to Misa ToolRegistry Dynamic Bridge
# Tashqi MCP vositalarini Misa'ning ichki Tool tizimiga moslashtirish va ulash

import logging
from typing import Dict, Any, List
from core.mcp.manager import get_mcp_manager

logger = logging.getLogger(__name__)


def mount_mcp_tools_to_registry(registry) -> int:
    """
    Barcha faol MCP serverlardagi vositalarni (masalan: Stitch, GitHub, DB va h.k.)
    Misa ToolRegistry ga dinamik ravishda biriktirish.
    """
    from core.agent_tools import Tool

    mcp_mgr = get_mcp_manager()
    tools = mcp_mgr.get_all_tools(force_refresh=False)
    mounted_count = 0

    for mcp_tool in tools:
        server_id = mcp_tool.get("server_id")
        orig_name = mcp_tool.get("name")
        qualified_name = mcp_tool.get("misa_qualified_name", f"mcp_{server_id}_{orig_name}")
        description = mcp_tool.get("description", f"MCP Tool from {server_id}: {orig_name}")
        schema = mcp_tool.get("inputSchema", {})
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}

        # Misa parametr formatiga moslashtirish
        param_dict = {}
        for p_name, p_info in properties.items():
            param_dict[p_name] = {
                "type": p_info.get("type", "string"),
                "description": p_info.get("description", p_name),
            }

        # Asbobni chaqiruvchi closure
        def _make_caller(s_id: str, t_name: str):
            def _caller(**kwargs):
                logger.info(f"[MCPBridge] Calling {s_id}:{t_name} with params={kwargs}")
                res = mcp_mgr.call_tool(s_id, t_name, kwargs)
                if not res.get("ok"):
                    return f"❌ MCP xatolik ({s_id}/{t_name}): {res.get('error')}"
                data = res.get("data")
                if isinstance(data, dict):
                    # Agar bu Stitch andozasi bo'lsa
                    if "screens" in data or "project" in data:
                        return data
                return res.get("raw") or str(data)
            return _caller

        from core.intelligence.types import RiskLevel

        misa_tool = Tool(
            name=qualified_name,
            description=f"[{mcp_tool.get('server_name', server_id)}] {description}",
            parameters=param_dict,
            function=_make_caller(server_id, orig_name),
            category="mcp",
            capabilities=["mcp", server_id],
            aliases=[f"{server_id}_{orig_name}"],
            risk_level=RiskLevel.LOW,
            timeout=float(schema.get("timeout", 120.0)),
        )

        try:
            registry.register(misa_tool)
            mounted_count += 1
        except Exception as e:
            logger.warning(f"[MCPBridge] Tool '{qualified_name}' ro'yxatdan o'tkazishda ogohlantirish: {e}")

    logger.info(f"[MCPBridge] Jami {mounted_count} ta MCP vositalari Misa ToolRegistry ga muvaffaqiyatli ulandi")
    return mounted_count
