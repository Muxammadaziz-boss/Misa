# ========== test_e2e_lifecycle.py ==========
# Phase 23 — Complete E2E Lifecycle & Subsystem Integration Test
# Launch -> Backend -> Home -> Chat -> Voice -> Commands -> Memory -> Scheduler -> Plugins -> Account -> Close

import os
import sys
import json
import asyncio
import unittest
from unittest import mock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.api_server import (
    create_app,
    handle_status,
    handle_chat,
    handle_chat_clear,
    handle_voice_start,
    handle_voice_stop,
    handle_voice_speak,
    handle_commands_list,
    handle_commands_execute,
    handle_memory_get,
    handle_memory_knowledge_save,
    handle_memory_knowledge_delete,
    handle_scheduler_list,
    handle_scheduler_add,
    handle_scheduler_remove,
    handle_plugins_list,
    handle_plugins_install,
    handle_plugins_uninstall,
    handle_account_get,
    handle_account_update,
    _read_config,
    _write_config,
)


class MockRequest:
    def __init__(self, json_data=None, query_data=None, method="GET", origin=None, remote="127.0.0.1"):
        self._json_data = json_data or {}
        self.query = query_data or {}
        self.method = method
        self.headers = {}
        if origin:
            self.headers["Origin"] = origin
        self.remote = remote

    async def json(self):
        return self._json_data


class TestE2ELifecycle(unittest.TestCase):
    """Phase 23: To'liq E2E hayotiy tsikl va integratsiya sinovi"""

    def setUp(self):
        self.original_config = _read_config()
        self.original_user_name = "Muxammadaziz"
        user_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "foydalanuvchi_ismi.txt")
        if os.path.exists(user_file):
            with open(user_file, "r", encoding="utf-8") as f:
                self.original_user_name = f.read().strip() or "Muxammadaziz"

    def tearDown(self):
        _write_config(self.original_config)
        user_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "foydalanuvchi_ismi.txt")
        if os.path.exists(user_file):
            with open(user_file, "w", encoding="utf-8") as f:
                f.write(self.original_user_name)

    def test_complete_e2e_flow(self):
        """E2E Tsikl: Launch -> Home -> Chat -> Voice -> Commands -> Memory -> Scheduler -> Plugins -> Account -> Close"""
        async def _run_e2e():
            # 1. LAUNCH & BACKEND STARTUP
            app = create_app()
            self.assertIsNotNone(app)

            status_resp = await handle_status(MockRequest())
            self.assertEqual(status_resp.status, 200)
            status_data = json.loads(status_resp.text)
            self.assertEqual(status_data.get("status"), "online")
            self.assertTrue(str(status_data.get("version", "")).startswith("9.0"))

            # 2. HOME / LANDING
            acc_resp = await handle_account_get(MockRequest())
            self.assertEqual(acc_resp.status, 200)
            acc_data = json.loads(acc_resp.text)
            self.assertTrue(acc_data.get("ok"))
            self.assertIn("name", acc_data)

            # 3. CHAT
            chat_resp = await handle_chat(MockRequest({"query": "Salom Misa", "mode": "ask"}))
            self.assertEqual(chat_resp.status, 200)
            chat_data = json.loads(chat_resp.text)
            self.assertTrue(chat_data.get("ok"))
            self.assertIn("response", chat_data)

            clear_resp = await handle_chat_clear(MockRequest())
            self.assertEqual(clear_resp.status, 200)

            # 4. VOICE
            with mock.patch("threading.Thread.start"):
                v_start = await handle_voice_start(MockRequest())
                self.assertEqual(v_start.status, 200)
                v_start_data = json.loads(v_start.text)
                self.assertTrue(v_start_data.get("ok"))
                self.assertEqual(v_start_data.get("status"), "listening")

                v_stop = await handle_voice_stop(MockRequest())
                self.assertEqual(v_stop.status, 200)
                v_stop_data = json.loads(v_stop.text)
                self.assertTrue(v_stop_data.get("ok"))
                self.assertEqual(v_stop_data.get("status"), "stopped")

            # 5. COMMANDS
            cmd_resp = await handle_commands_list(MockRequest())
            self.assertEqual(cmd_resp.status, 200)
            cmd_data = json.loads(cmd_resp.text)
            self.assertTrue(cmd_data.get("ok"))
            self.assertGreaterEqual(len(cmd_data.get("commands", [])), 25)

            exec_resp = await handle_commands_execute(MockRequest({
                "command": "calculator",
                "parameters": {"expression": "25 * 4"}
            }))
            self.assertEqual(exec_resp.status, 200)
            exec_data = json.loads(exec_resp.text)
            self.assertTrue(exec_data.get("ok"))
            self.assertIn("100", str(exec_data.get("result", "")))

            # 6. MEMORY
            save_k = await handle_memory_knowledge_save(MockRequest({
                "key": "e2e_test_key",
                "value": "e2e_test_val"
            }))
            self.assertEqual(save_k.status, 200)

            mem_resp = await handle_memory_get(MockRequest())
            self.assertEqual(mem_resp.status, 200)
            mem_data = json.loads(mem_resp.text)
            self.assertTrue(mem_data.get("ok"))
            keys = [item.get("key") for item in mem_data.get("knowledge", [])]
            self.assertIn("e2e_test_key", keys)

            del_k = await handle_memory_knowledge_delete(MockRequest(query_data={"key": "e2e_test_key"}))
            self.assertEqual(del_k.status, 200)

            # 7. SCHEDULER
            add_task = await handle_scheduler_add(MockRequest({
                "text": "E2E Eslatma sinovi",
                "delay_minutes": 15,
                "type": "reminder"
            }))
            self.assertEqual(add_task.status, 200)
            add_task_data = json.loads(add_task.text)
            self.assertTrue(add_task_data.get("ok"))
            task_id = add_task_data.get("task_id") or add_task_data.get("id")
            self.assertIsNotNone(task_id)

            sched_list = await handle_scheduler_list(MockRequest())
            sched_data = json.loads(sched_list.text)
            self.assertTrue(sched_data.get("ok"))

            del_task = await handle_scheduler_remove(MockRequest(query_data={"task_id": task_id}))
            self.assertEqual(del_task.status, 200)

            # 8. PLUGINS
            plg_list = await handle_plugins_list(MockRequest())
            self.assertEqual(plg_list.status, 200)
            plg_data = json.loads(plg_list.text)
            self.assertTrue(plg_data.get("ok"))
            self.assertIn("stats", plg_data)

            inst_resp = await handle_plugins_install(MockRequest({"name": "github_search"}))
            self.assertEqual(inst_resp.status, 200)

            uninst_resp = await handle_plugins_uninstall(MockRequest({"name": "github_search"}))
            self.assertEqual(uninst_resp.status, 200)

            # 9. ACCOUNT
            upd_acc = await handle_account_update(MockRequest({
                "name": "E2E Sinov Foydalanuvchisi"
            }))
            self.assertEqual(upd_acc.status, 200)

            acc_check = await handle_account_get(MockRequest())
            acc_check_data = json.loads(acc_check.text)
            self.assertEqual(acc_check_data.get("name"), "E2E Sinov Foydalanuvchisi")

            # 10. CLEAN CLOSE
            # Asl holatga qaytarish tearDown da bajariladi

        asyncio.run(_run_e2e())


if __name__ == "__main__":
    unittest.main()
