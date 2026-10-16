# ========== tests/test_agent_lifecycle_executor.py ==========
import os
import sys
import time
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agent.config import AgentConfig
from agent.executor import RemoteCommandExecutor, CommandPoller, CommandStatus
from agent.lifecycle import AgentLifecycleManager
from agent.heartbeat import AgentState
from core.v8.events import RemoteEventType


class MockTool:
    def __init__(self, tool_id, risk_level="low", destructive=False, requires_confirmation=False, sleep_s=0.0):
        self.tool_id = tool_id
        self.risk_level = risk_level
        self.destructive = destructive
        self.requires_confirmation = requires_confirmation
        self.sleep_s = sleep_s

    async def execute(self, params):
        if self.sleep_s > 0:
            await asyncio.sleep(self.sleep_s)
        return {"status": "ok", "executed_tool": self.tool_id, "params": params}


class MockToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, tool):
        self.tools[tool.tool_id] = tool

    def get(self, tool_id):
        return self.tools.get(tool_id)

    def get_tool(self, tool_id):
        return self.tools.get(tool_id)


class TestAgentLifecycleExecutor(unittest.TestCase):
    def setUp(self):
        self.registry = MockToolRegistry()
        self.registry.register(MockTool("system_info", risk_level="low"))
        self.registry.register(MockTool("file_delete", risk_level="high", destructive=True, requires_confirmation=True))
        self.registry.register(MockTool("system_shutdown", risk_level="high", destructive=True, requires_confirmation=True))
        self.registry.register(MockTool("slow_tool", risk_level="low", sleep_s=1.5))

        self.mock_audit = MagicMock()
        self.mock_audit.log = MagicMock()
        self.mock_audit.log_event = MagicMock()

    def test_01_executor_validation_and_idempotency(self):
        async def _run():
            executor = RemoteCommandExecutor(tool_registry=self.registry, audit_logger=self.mock_audit)

            # 1. Missing command_id
            res1 = await executor.execute({"tool_id": "system_info"})
            self.assertEqual(res1["status"], CommandStatus.REJECTED.value)
            self.assertEqual(res1["error"], "MISSING_COMMAND_ID")

            # 2. Expiry check
            res2 = await executor.execute({
                "command_id": "cmd-expired",
                "tool_id": "system_info",
                "expires_at": time.time() - 10.0
            })
            self.assertEqual(res2["status"], CommandStatus.REJECTED.value)
            self.assertEqual(res2["error"], "COMMAND_EXPIRED")

            # 3. Successful execution & caching
            cmd3 = {
                "command_id": "cmd-valid-1",
                "tool_id": "system_info",
                "nonce": "nonce-123",
                "params": {"detail": True}
            }
            res3 = await executor.execute(cmd3)
            self.assertEqual(res3["status"], CommandStatus.SUCCEEDED.value)
            self.assertEqual(res3["result"]["executed_tool"], "system_info")

            # Idempotent response from cache
            res3_cached = await executor.execute(cmd3)
            self.assertEqual(res3_cached["status"], CommandStatus.SUCCEEDED.value)
            self.assertEqual(res3_cached["result"]["executed_tool"], "system_info")

        asyncio.run(_run())

    def test_02_executor_nonce_replay_protection(self):
        async def _run():
            executor = RemoteCommandExecutor(tool_registry=self.registry, audit_logger=self.mock_audit)

            cmd1 = {
                "command_id": "cmd-replay-1",
                "tool_id": "system_info",
                "nonce": "unique-nonce-xyz"
            }
            res1 = await executor.execute(cmd1)
            self.assertEqual(res1["status"], CommandStatus.SUCCEEDED.value)

            # Different command_id but same nonce (replay attempt)
            cmd2 = {
                "command_id": "cmd-replay-2",
                "tool_id": "system_info",
                "nonce": "unique-nonce-xyz"
            }
            res2 = await executor.execute(cmd2)
            self.assertEqual(res2["status"], CommandStatus.REJECTED.value)
            self.assertEqual(res2["error"], "REPLAY_BLOCKED")

        asyncio.run(_run())

    def test_03_executor_destructive_and_power_action_protection(self):
        async def _run():
            executor = RemoteCommandExecutor(tool_registry=self.registry, audit_logger=self.mock_audit)

            # 1. Unconfirmed destructive tool must be rejected
            cmd_unconfirmed = {
                "command_id": "cmd-shutdown-1",
                "tool_id": "system_shutdown",
                "confirmation_status": "pending"
            }
            res1 = await executor.execute(cmd_unconfirmed)
            self.assertEqual(res1["status"], CommandStatus.REJECTED.value)
            self.assertEqual(res1["error"], "CONFIRMATION_REQUIRED")

            # 2. Confirmed destructive tool executes
            cmd_confirmed = {
                "command_id": "cmd-shutdown-2",
                "tool_id": "system_shutdown",
                "confirmation_status": "confirmed"
            }
            res2 = await executor.execute(cmd_confirmed)
            self.assertEqual(res2["status"], CommandStatus.SUCCEEDED.value)
            self.assertEqual(res2["result"]["executed_tool"], "system_shutdown")

        asyncio.run(_run())

    def test_04_executor_timeout_protection(self):
        async def _run():
            executor = RemoteCommandExecutor(tool_registry=self.registry, audit_logger=self.mock_audit)

            cmd_timeout = {
                "command_id": "cmd-slow",
                "tool_id": "slow_tool",
                "timeout": 0.2
            }
            res = await executor.execute(cmd_timeout)
            self.assertEqual(res["status"], CommandStatus.FAILED.value)
            self.assertEqual(res["error"], "TIMEOUT")

        asyncio.run(_run())

    def test_05_command_poller_duplicate_start_and_stop(self):
        async def _run():
            mock_transport = AsyncMock()
            mock_transport.get.return_value = (200, [])
            mock_executor = AsyncMock()

            poller = CommandPoller(
                transport=mock_transport,
                device_id="dev-test-1",
                executor=mock_executor,
                poll_interval=0.1
            )

            self.assertFalse(poller.is_running)
            await poller.start()
            self.assertTrue(poller.is_running)

            task1 = poller._poll_task
            # Second start call should be a no-op (no duplicate tasks)
            await poller.start()
            self.assertIs(poller._poll_task, task1)
            self.assertTrue(poller.is_running)

            await poller.stop()
            self.assertFalse(poller.is_running)
            self.assertIsNone(poller._poll_task)

        asyncio.run(_run())

    def test_06_lifecycle_manager_executor_and_poller_integration(self):
        async def _run():
            import tempfile
            with tempfile.TemporaryDirectory() as tmp_dir:
                config = AgentConfig(
                    vault_dir=tmp_dir,
                    backend_url="https://mock.backend",
                    friendly_name="TestDevice",
                    heartbeat_interval=1.0,
                    poll_interval=1.0
                )

                with patch("agent.lifecycle.SecureTransport") as mock_transport_cls, \
                     patch("agent.lifecycle.AgentEnrollment") as mock_enrollment_cls, \
                     patch("agent.lifecycle.AgentAuth") as mock_auth_cls:

                    mock_transport = AsyncMock()
                    mock_transport.get.return_value = (200, [])
                    mock_transport.post.return_value = (200, {"status": "ok"})
                    mock_transport.close.return_value = None
                    mock_transport_cls.return_value = mock_transport

                    mock_auth = AsyncMock()
                    mock_auth.authenticate.return_value = (True, "OK", "token-xyz")
                    mock_auth_cls.return_value = mock_auth

                    lifecycle = AgentLifecycleManager(config)
                    self.assertTrue(hasattr(lifecycle, "executor"))
                    self.assertTrue(hasattr(lifecycle, "poller"))
                    self.assertIsInstance(lifecycle.executor, RemoteCommandExecutor)
                    self.assertIsInstance(lifecycle.poller, CommandPoller)

                    # Start lifecycle
                    started = await lifecycle.start()
                    self.assertTrue(started)
                    self.assertTrue(lifecycle.is_running)
                    self.assertEqual(lifecycle.heartbeat.state, AgentState.ONLINE)
                    self.assertTrue(lifecycle.poller.is_running)

                    # Restart
                    mock_auth.authenticate.return_value = (True, "Re-authenticated", "token-new")
                    restarted = await lifecycle.restart()
                    self.assertTrue(restarted)
                    self.assertEqual(lifecycle.heartbeat.state, AgentState.ONLINE)
                    self.assertTrue(lifecycle.poller.is_running)

                    # Shutdown
                    await lifecycle.shutdown()
                    self.assertFalse(lifecycle.is_running)
                    self.assertFalse(lifecycle.poller.is_running)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
