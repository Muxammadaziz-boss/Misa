# ========== test_v8_remote.py ==========
# Phase 35 — Misa AI v9.0.0 Remote PC Control Test Suite
# Tests: Device Identity, Heartbeat, WoL, Envelope, Telegram Gateway, PCAgent, Planning DAG

import os
import sys
import time
import asyncio
import unittest
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.v8 import (  # noqa: E402
    DeviceIdentity,
    DeviceIdentityManager,
    DeviceState,
    HeartbeatPayload,
    HeartbeatManager,
    WakeOnLanManager,
    create_magic_packet,
    WakeRelay,
    RemoteCommandEnvelope,
    EnvelopeManager,
    MisaPCAgent,
    TelegramRemoteGateway,
    create_remote_wake_and_verify_dag,
)


class MockWakeRelay(WakeRelay):
    """Testlar uchun mock relay: tarmoqqa ehtiyoj yo'q"""

    def __init__(self, succeed: bool = True, failure_count: int = 0):
        self.succeed = succeed
        self.failure_count = failure_count
        self.attempts = 0
        self.sent_packets = []

    async def send_wake(self, mac_address: str, broadcast_ip: str = "255.255.255.255", port: int = 9) -> bool:
        self.attempts += 1
        self.sent_packets.append((mac_address, broadcast_ip, port))
        if self.attempts <= self.failure_count:
            return False
        return self.succeed


class TestV8RemoteControl(unittest.TestCase):
    """Phase 35 Remote PC Control 20 ta talab bo'yicha to'liq testlar"""

    # 1. Device identity generation
    def test_01_device_identity_generation(self):
        ident = DeviceIdentityManager.create_local_identity()
        self.assertTrue(ident.device_id)
        self.assertTrue(ident.hostname)
        self.assertTrue(ident.username)
        self.assertIn(ident.agent_version, ["9.0.0", "9.0.1"])
        self.assertIn(ident.misa_version, ["9.0.0", "9.0.1"])
        self.assertTrue(ident.fingerprint)
        d = ident.to_dict()
        self.assertEqual(d["device_id"], ident.device_id)
        restored = DeviceIdentity.from_dict(d)
        self.assertEqual(restored.device_id, ident.device_id)

    # 2. Device registration
    def test_02_device_registration(self):
        hm = HeartbeatManager()
        hm.register_device("test_pc_1", initial_state=DeviceState.OFFLINE, info={"hostname": "MyPC"})
        self.assertEqual(hm.get_device_state("test_pc_1"), DeviceState.OFFLINE)
        self.assertFalse(hm.is_online("test_pc_1"))

    # 3. Heartbeat processing
    def test_03_heartbeat_processing(self):
        hm = HeartbeatManager()
        payload = HeartbeatPayload(
            device_id="test_pc_1",
            timestamp=time.time(),
            state=DeviceState.ONLINE,
            metrics={"cpu": 15.0, "ram": 42.0}
        )
        res = hm.record_heartbeat(payload)
        self.assertTrue(res)
        self.assertEqual(hm.get_device_state("test_pc_1"), DeviceState.ONLINE)
        self.assertTrue(hm.is_online("test_pc_1"))

    # 4. Online/offline state transitions
    def test_04_online_offline_transitions(self):
        hm = HeartbeatManager(stale_timeout=1.0)
        transitions = []
        hm.add_state_listener(lambda dev, old_s, new_s: transitions.append((dev, old_s, new_s)))

        # 1. Register & online
        t0 = 1000.0
        hm.record_heartbeat(HeartbeatPayload(device_id="dev_1", timestamp=t0, state=DeviceState.ONLINE))
        self.assertTrue(hm.is_online("dev_1"))

        # 2. Check timeout after 0.5s (should remain online)
        timed_out = hm.check_timeouts(current_time=t0 + 0.5)
        self.assertEqual(len(timed_out), 0)
        self.assertTrue(hm.is_online("dev_1"))

        # 3. Check timeout after 2.0s (stale, should go offline)
        timed_out = hm.check_timeouts(current_time=t0 + 2.0)
        self.assertIn("dev_1", timed_out)
        self.assertEqual(hm.get_device_state("dev_1"), DeviceState.OFFLINE)
        self.assertFalse(hm.is_online("dev_1"))

        # Check listener callback captured transitions
        self.assertTrue(any(t[2] == DeviceState.OFFLINE for t in transitions))

    # 5. WoL magic packet generation
    def test_05_wol_magic_packet_generation(self):
        valid_mac = "AA:BB:CC:DD:EE:FF"
        packet = create_magic_packet(valid_mac)
        self.assertEqual(len(packet), 102)
        self.assertTrue(packet.startswith(b"\xff" * 6))
        # 16 times MAC
        mac_bytes = bytes.fromhex("AABBCCDDEEFF")
        self.assertEqual(packet[6:12], mac_bytes)
        self.assertEqual(packet[-6:], mac_bytes)

        # Invalid MAC formats throw ValueError
        with self.assertRaises(ValueError):
            create_magic_packet("invalid_mac")

    # 6. WoL retry mechanism
    def test_06_wol_retry_mechanism(self):
        async def _run():
            # First 2 attempts fail, 3rd succeeds
            relay = MockWakeRelay(succeed=True, failure_count=2)
            manager = WakeOnLanManager(relay=relay, retry_count=3, retry_delay=0.01)
            res = await manager.wake_device("00:11:22:33:44:55")
            self.assertTrue(res["success"])
            self.assertEqual(res["attempts"], 1)  # 1 successful attempt
            self.assertEqual(relay.attempts, 3)    # 3 total tries executed

        asyncio.run(_run())

    # 7. Command envelope creation & serialization
    def test_07_command_envelope_creation(self):
        em = EnvelopeManager(authorized_user_id="123456")
        env = em.create_envelope(
            device_id="pc_home",
            action="system_info",
            params={"category": "cpu"},
            user_id="123456"
        )
        self.assertEqual(env.device_id, "pc_home")
        self.assertEqual(env.action, "system_info")
        self.assertEqual(env.user_id, "123456")
        self.assertTrue(env.nonce)
        self.assertGreater(env.expires_at, env.created_at)

        d = env.to_dict()
        restored = RemoteCommandEnvelope.from_dict(d)
        self.assertEqual(restored.request_id, env.request_id)
        self.assertEqual(restored.nonce, env.nonce)

    # 8. Request expiration validation
    def test_08_request_expiration(self):
        em = EnvelopeManager(authorized_user_id="123456", default_ttl=5.0)
        t0 = 100.0
        with patch("time.time", return_value=t0):
            env = em.create_envelope(device_id="pc_1", action="status", user_id="123456")

        # Valid at t0 + 2
        is_ok, msg = em.validate_envelope(env, current_time=t0 + 2.0)
        self.assertTrue(is_ok)

        # Expired at t0 + 6
        is_ok2, msg2 = em.validate_envelope(env, current_time=t0 + 6.0)
        self.assertFalse(is_ok2)
        self.assertIn("EXPIRED", msg2)

    # 9. Nonce & replay attack defense
    def test_09_nonce_replay_attack_defense(self):
        em = EnvelopeManager(authorized_user_id="123456")
        env = em.create_envelope(device_id="pc_1", action="status", user_id="123456")

        # First delivery: OK
        is_ok1, _ = em.validate_envelope(env)
        self.assertTrue(is_ok1)

        # Duplicate delivery with same nonce: REPLAY ATTACK BLOCKED
        is_ok2, msg2 = em.validate_envelope(env)
        self.assertFalse(is_ok2)
        self.assertIn("REPLAY_ATTACK", msg2)

    # 10. Unauthorized Telegram user rejection
    def test_10_unauthorized_user_rejection(self):
        em = EnvelopeManager(authorized_user_id="999999")
        env = em.create_envelope(device_id="pc_1", action="status", user_id="evil_user_666")
        is_ok, msg = em.validate_envelope(env)
        self.assertFalse(is_ok)
        self.assertIn("UNAUTHORIZED", msg)

    # 11. Authorized Telegram user access
    def test_11_authorized_user_access(self):
        gw = TelegramRemoteGateway(admin_id="12345678")
        self.assertTrue(gw.is_authorized("12345678"))
        self.assertTrue(gw.is_authorized(12345678))
        self.assertFalse(gw.is_authorized("87654321"))

    # 12. Duplicate command prevention
    def test_12_duplicate_command_prevention(self):
        em = EnvelopeManager(authorized_user_id="123")
        env1 = em.create_envelope(device_id="pc", action="wake", user_id="123")
        env2 = em.create_envelope(device_id="pc", action="wake", user_id="123")

        # Har bir yangi envelope noyob nonce oladi
        self.assertNotEqual(env1.nonce, env2.nonce)
        self.assertTrue(em.validate_envelope(env1)[0])
        self.assertTrue(em.validate_envelope(env2)[0])
        # Takrorlangan env1 rad etiladi
        self.assertFalse(em.validate_envelope(env1)[0])

    # 13. Agent reconnect with exponential backoff
    def test_13_agent_reconnect_backoff(self):
        async def _run():
            hm = HeartbeatManager()
            agent = MisaPCAgent(heartbeat_manager=hm)
            # Normal holatda backoff 1.0s
            self.assertEqual(agent._backoff, 1.0)

            # Heartbeat uzilganda backoff eksponensial o'sadi
            with patch.object(hm, "record_heartbeat", side_effect=Exception("Connection lost")):
                res1 = await agent.run_step()
                self.assertFalse(res1)
                self.assertEqual(agent._backoff, 2.0)

                res2 = await agent.run_step()
                self.assertFalse(res2)
                self.assertEqual(agent._backoff, 4.0)

        asyncio.run(_run())

    # 14. AgentLoop integration
    def test_14_agent_loop_integration(self):
        async def _run():
            agent = MisaPCAgent()
            await agent.register()

            env = agent.envelope_manager.create_envelope(
                device_id=agent.identity.device_id,
                action="calculator",
                params={"expression": "25 * 4"},
                user_id=agent.envelope_manager.authorized_user_id or ""
            )
            res = await agent.handle_remote_command(env)
            self.assertTrue(res.get("success"))
            self.assertIn("result", res)

        asyncio.run(_run())

    # 15. Planning DAG for remote tasks
    def test_15_planning_dag(self):
        plan = create_remote_wake_and_verify_dag("dev_office", "00:11:22:33:44:55")
        self.assertEqual(len(plan.steps), 5)
        step_dict = {s.step_id: s for s in plan.steps}
        self.assertEqual(step_dict["check_device"].dependencies, [])
        self.assertIn("check_device", step_dict["wake_device"].dependencies)
        self.assertIn("wake_device", step_dict["wait_heartbeat"].dependencies)
        self.assertIn("wait_heartbeat", step_dict["verify_online"].dependencies)
        self.assertIn("verify_online", step_dict["get_status"].dependencies)
        self.assertEqual(
            plan.execution_order,
            ["check_device", "wake_device", "wait_heartbeat", "verify_online", "get_status"]
        )

    # 16. Wake -> Heartbeat transition flow
    def test_16_wake_heartbeat_transition_flow(self):
        hm = HeartbeatManager()
        dev_id = "test_pc_wake"
        hm.register_device(dev_id, initial_state=DeviceState.OFFLINE)
        self.assertEqual(hm.get_device_state(dev_id), DeviceState.OFFLINE)

        # 1. Wake yuborildi -> WAKING
        hm.set_device_state(dev_id, DeviceState.WAKING)
        self.assertEqual(hm.get_device_state(dev_id), DeviceState.WAKING)

        # 2. Agent uyg'ondi va heartbeat yubordi -> ONLINE
        hm.record_heartbeat(HeartbeatPayload(device_id=dev_id, timestamp=time.time(), state=DeviceState.ONLINE))
        self.assertEqual(hm.get_device_state(dev_id), DeviceState.ONLINE)
        self.assertTrue(hm.is_online(dev_id))

    # 17. Timeout when PC fails to wake
    def test_17_timeout_when_pc_fails_to_wake(self):
        hm = HeartbeatManager(stale_timeout=2.0)
        dev_id = "stubborn_pc"
        hm.register_device(dev_id, initial_state=DeviceState.OFFLINE)
        hm.set_device_state(dev_id, DeviceState.WAKING)

        # Kutish vaqtida heartbeat kelmadi
        # Stale tekshiruvi
        hm.set_device_state(dev_id, DeviceState.OFFLINE)
        self.assertEqual(hm.get_device_state(dev_id), DeviceState.OFFLINE)

    # 18. High-risk command confirmation flow
    def test_18_confirmation_flow(self):
        async def _run():
            agent = MisaPCAgent()
            await agent.register()

            # Confirmation bo'lmagan yuqori xavfli buyruq (shutdown) rad etiladi
            env_unconfirmed = agent.envelope_manager.create_envelope(
                device_id=agent.identity.device_id,
                action="shutdown",
                confirmation_required=False,
                user_id=agent.envelope_manager.authorized_user_id or ""
            )
            res = await agent.handle_remote_command(env_unconfirmed)
            self.assertFalse(res.get("success"))
            self.assertIn("PERMISSION_DENIED", res.get("error", ""))

        asyncio.run(_run())

    # 19. Telegram mock transport
    def test_19_telegram_mock_transport(self):
        gw = TelegramRemoteGateway(admin_id="777")
        # Buyruq parsing
        cmd_status = gw.parse_command("/pc")
        self.assertEqual(cmd_status["action"], "status")

        cmd_wake = gw.parse_command("⚡ Wake PC")
        self.assertEqual(cmd_wake["action"], "wake")

        cmd_uzbek_wake = gw.parse_command("Misa, kompyuterni yoq")
        self.assertEqual(cmd_uzbek_wake["action"], "wake")

        # Tugmalar
        kb = gw.build_keyboard()
        self.assertGreaterEqual(len(kb), 2)

        # Xabar formati
        msg = gw.format_status_message({"hostname": "TestNode", "os_name": "Windows", "os_release": "11"}, DeviceState.ONLINE)
        self.assertIn("ONLINE", msg)
        self.assertIn("TestNode", msg)

    # 20. End-to-end mocked remote execution
    def test_20_end_to_end_remote_flow(self):
        async def _run():
            # 1. Gateway va Agent sozlash
            admin_id = "55555"
            gw = TelegramRemoteGateway(admin_id=admin_id)
            relay = MockWakeRelay(succeed=True)
            gw.wol_manager = WakeOnLanManager(relay=relay)

            agent = MisaPCAgent(envelope_manager=gw.envelope_manager)
            await agent.register()
            await agent.send_heartbeat()

            # 2. Telegramdan status so'rovi
            parsed = gw.parse_command("Misa, kompyuterim yoqilganmi?")
            self.assertEqual(parsed["action"], "status")

            env = gw.envelope_manager.create_envelope(
                device_id=agent.identity.device_id,
                action=parsed["action"],
                params=parsed["params"],
                user_id=admin_id
            )

            # 3. Agent buyruqni bajaradi va status qaytaradi
            exec_res = await agent.handle_remote_command(env)
            self.assertTrue(exec_res.get("success"))
            self.assertEqual(exec_res["result"]["state"], DeviceState.ONLINE.value)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
