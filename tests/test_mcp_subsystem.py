# ========== tests/test_mcp_subsystem.py ==========
# Misa AI v9.0 — Universal MCP Subsystem & Stitch Integration Tests

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.mcp.client import MCPClient
from core.mcp.manager import MCPManager, get_mcp_manager
from core.mcp.bridge import mount_mcp_tools_to_registry
from core.agent_tools import ToolRegistry, Tool, create_default_registry


def test_mcp_manager_singleton_and_config():
    mgr = get_mcp_manager()
    assert mgr is not None
    assert isinstance(mgr, MCPManager)

    servers = mgr.list_servers()
    assert isinstance(servers, list)
    server_ids = [s.get("id") for s in servers]
    assert "stitch" in server_ids

    stitch_cfg = mgr.get_servers().get("stitch")
    assert stitch_cfg is not None
    assert stitch_cfg.get("enabled") is True
    assert "https://stitch.googleapis.com/mcp" in (stitch_cfg.get("url") or stitch_cfg.get("endpoint", ""))


def test_mcp_extensibility_add_and_toggle_server(tmp_path):
    test_config_path = str(tmp_path / "test_mcp_servers.json")
    mgr = MCPManager(config_path=test_config_path)

    # 1. Kelajakdagi yangi MCP serverni qo'shish (masalan: sqlite yoki github)
    success = mgr.register_server(
        "github_mcp",
        {
            "name": "GitHub Repository Manager MCP",
            "description": "Repo va issue larni boshqarish",
            "transport": "http",
            "url": "https://api.github-mcp.local/mcp",
            "headers": {"Authorization": "Bearer test-token"},
            "category": "Dasturlash",
            "enabled": True,
        }
    )
    assert success is True
    assert "github_mcp" in mgr.get_servers()

    # 2. Serverni o'chirish/yoqish (toggle)
    toggled = mgr.toggle_server("github_mcp", enabled=False)
    assert toggled is True
    assert mgr.get_servers()["github_mcp"]["enabled"] is False

    toggled_back = mgr.toggle_server("github_mcp", enabled=True)
    assert toggled_back is True
    assert mgr.get_servers()["github_mcp"]["enabled"] is True

    # 3. Serverni o'chirish (remove)
    removed = mgr.remove_server("github_mcp")
    assert removed is True
    assert "github_mcp" not in mgr.get_servers()


def test_mcp_bridge_mounting():
    reg = ToolRegistry()
    initial_count = reg.count

    # Mock tool list from MCPManager
    mock_tools = [
        {
            "name": "generate_mock_ui",
            "description": "Mock UI generator",
            "server_id": "test_server",
            "server_name": "Test Server",
            "misa_qualified_name": "mcp_test_server_generate_mock_ui",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "UI prompt"}
                }
            }
        }
    ]

    with patch.object(MCPManager, "get_all_tools", return_value=mock_tools):
        mounted = mount_mcp_tools_to_registry(reg)
        assert mounted == 1
        assert reg.count == initial_count + 1

        tool = reg.get("mcp_test_server_generate_mock_ui")
        assert tool is not None
        assert tool.name == "mcp_test_server_generate_mock_ui"
        assert "prompt" in tool.parameters


def test_stitch_ui_designer_registration():
    reg = create_default_registry()
    stitch_tool = reg.get("stitch_ui_designer")
    assert stitch_tool is not None
    assert "prompt" in stitch_tool.parameters
    assert "ui_design" in stitch_tool.capabilities

    # Taxalluslar orqali topish
    alias_tool = reg.get("stitch")
    assert alias_tool is not None
    assert alias_tool.name == "stitch_ui_designer"

    andoza_tool = reg.get("andoza")
    assert andoza_tool is not None
    assert andoza_tool.name == "stitch_ui_designer"


def test_mcp_client_rpc_formatting():
    client = MCPClient(
        server_id="test",
        transport="http",
        url="http://localhost:9999/mcp",
        headers={"X-Test": "123"}
    )
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {"text": "{\"status\": \"ok\", \"screen\": \"dashboard\"}"}
                ]
            }
        }
        mock_post.return_value = mock_resp

        call_res = client.call_tool("create_screen", {"title": "Dashboard"})
        assert call_res.get("ok") is True
        assert call_res.get("data", {}).get("status") == "ok"
