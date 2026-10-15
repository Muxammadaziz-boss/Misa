# ========== test_plugins_api.py ==========
# Phase 14 — Plugin Center API Unit Tests (5 states: installed, available, disabled, error, updates)

import os
import sys
import json
import asyncio
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.agent_plugins import get_plugin_manager, AVAILABLE_TEMPLATES
from core.agent_tools import get_registry
from core.api_server import (
    handle_plugins_list,
    handle_plugins_toggle,
    handle_plugins_install,
    handle_plugins_uninstall,
    handle_plugins_update,
    handle_plugins_execute,
)


class MockRequest:
    def __init__(self, json_data=None, query_data=None, headers=None):
        self._json_data = json_data or {}
        self.query = query_data or {}
        self.headers = headers or {}

    async def json(self):
        return self._json_data


class TestPluginsAPI(unittest.TestCase):
    """Plugin Center backend API va 5 xil holat testlari"""

    def setUp(self):
        self.pm = get_plugin_manager()
        self.reg = get_registry()

    def test_plugins_list_structure_and_stats(self):
        """GET /api/plugins barcha 5 xil holat (installed, available, disabled, error, updates) bo'yicha ma'lumot beradi"""
        async def _run():
            resp = await handle_plugins_list(MockRequest())
            data = json.loads(resp.text)
            self.assertTrue(data.get("ok"))
            self.assertIn("plugins", data)
            self.assertIn("stats", data)
            self.assertIn("categories", data)

            stats = data["stats"]
            self.assertIn("installed", stats)
            self.assertIn("available", stats)
            self.assertIn("disabled", stats)
            self.assertIn("error", stats)
            self.assertIn("updates", stats)
            self.assertGreaterEqual(stats["installed"], 29) # kamida 29 ta tool

            # Har bir plagin kerakli maydonlarga ega ekanligini tekshirish
            plugins = data["plugins"]
            for p in plugins[:5]:
                self.assertIn("id", p)
                self.assertIn("name", p)
                self.assertIn("description", p)
                self.assertIn("status", p)
                self.assertIn(p["status"], ["installed", "available", "disabled", "error", "updates"])

        asyncio.run(_run())

    def test_plugin_install_toggle_uninstall_flow(self):
        """Plaginni o'rnatish, yoqish/o'chirish va o'chirish hayotiy sikli"""
        async def _run():
            test_plugin_name = "test_unit_search"
            custom_data = {
                "name": test_plugin_name,
                "description": "Test maqsadida yaratilgan plagin",
                "category": "Dasturlash",
                "type": "url",
                "url": "https://example.com/test?q={query}",
                "parameters": {"query": {"type": "string", "description": "So'rov"}},
                "version": "1.0.0"
            }

            # 1. Install
            resp_inst = await handle_plugins_install(MockRequest({"name": test_plugin_name, "data": custom_data}))
            data_inst = json.loads(resp_inst.text)
            self.assertTrue(data_inst.get("ok"))

            # Ro'yxatda borligini tekshirish
            resp_list = await handle_plugins_list(MockRequest())
            data_list = json.loads(resp_list.text)
            matching = [p for p in data_list["plugins"] if p["name"] == test_plugin_name]
            self.assertEqual(len(matching), 1)
            self.assertEqual(matching[0]["status"], "installed")

            # 2. Toggle (Disable)
            resp_dis = await handle_plugins_toggle(MockRequest({"name": test_plugin_name, "enabled": False}))
            data_dis = json.loads(resp_dis.text)
            self.assertTrue(data_dis.get("ok"))

            resp_list2 = await handle_plugins_list(MockRequest())
            data_list2 = json.loads(resp_list2.text)
            matching_dis = [p for p in data_list2["plugins"] if p["name"] == test_plugin_name]
            self.assertEqual(len(matching_dis), 1)
            self.assertEqual(matching_dis[0]["status"], "disabled")

            # 3. Toggle (Enable back)
            resp_en = await handle_plugins_toggle(MockRequest({"name": test_plugin_name, "enabled": True}))
            data_en = json.loads(resp_en.text)
            self.assertTrue(data_en.get("ok"))

            # 4. Uninstall
            resp_un = await handle_plugins_uninstall(MockRequest({"name": test_plugin_name}))
            data_un = json.loads(resp_un.text)
            self.assertTrue(data_un.get("ok"))

        asyncio.run(_run())

    def test_plugin_execute(self):
        """POST /api/plugins/execute vositani muvaffaqiyatli ishga tushiradi"""
        async def _run():
            resp = await handle_plugins_execute(MockRequest(
                json_data={
                    "name": "calculator",
                    "params": {"expression": "12 * 12"}
                },
                headers={"Origin": "tauri://localhost"}
            ))
            data = json.loads(resp.text)
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("tool"), "calculator")
            self.assertIn("result", data)
            calc_res = data["result"].get("result", {})
            self.assertEqual(calc_res.get("result"), 144)

        asyncio.run(_run())

    def test_plugin_execute_unauthorized_rejected(self):
        """POST /api/plugins/execute ruxsatsiz origin yoki tokensiz so'rovni 403 bilan rad etadi"""
        async def _run():
            resp = await handle_plugins_execute(MockRequest(
                json_data={
                    "name": "calculator",
                    "params": {"expression": "12 * 12"}
                },
                headers={"Origin": "http://evil-site.com"}
            ))
            data = json.loads(resp.text)
            self.assertFalse(data.get("ok"))
            self.assertEqual(resp.status, 403)
            self.assertEqual(data.get("error"), "UNAUTHORIZED_LOCAL_CALLER")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
