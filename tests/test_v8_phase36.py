# ========== tests/test_v8_phase36.py ==========
# Phase 36 — Misa AI v9.0.0 Remote PC Control Integration Test Suite
# Exactly 40 comprehensive tests covering:
# Device (1-5), Heartbeat (6-10), WoL (11-15), Security (16-22),
# Agent (23-27), Remote Pipeline (28-33), Confirmation (34-36), Telegram (37-40)

import os
import sys
import time
import asyncio
import unittest
import tempfile
import shutil
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.v8 import (  # noqa: E402
    DeviceIdentity,
    DeviceIdentityManager,
    DeviceRegistry,
    DeviceState,
    HeartbeatPayload,
    HeartbeatManager,
    WakeOnLanManager,
    create_magic_packet,
    WakeRelay,
    EnvelopeManager,
    MisaPCAgent,
    TelegramRemoteGateway,
    MockTelegramTransport,
    RemoteOrchestrator
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


class TestV8Phase36(unittest.TestCase):
    """
    Phase 36: Real Telegram ↔ Misa ↔ Windows PC Agent Integration
    40 ta talab bo'yicha to'liq test to'plami.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="misa_v8_test_")
        self.registry_path = os.path.join(self.test_dir, "devices.json")
        self.registry = DeviceRegistry(storage_path=self.registry_path)
        self.admin_id = "123456789"
        self.transport = MockTelegramTransport()
        self.gateway = TelegramRemoteGateway(
            admin_id=self.admin_id,
            transport=self.transport
        )
        self.heartbeat_mgr = HeartbeatManager(stale_timeout=2.0)
        self.relay = MockWakeRelay(succeed=True)
        self.wol_mgr = WakeOnLanManager(relay=self.relay)
        self.envelope_mgr = EnvelopeManager(authorized_user_id=self.admin_id)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # ========================================================
    # 1–5: DEVICE
    # ========================================================

    def test_01_device_identity(self):
        """1. Device identity yaratilishi va atributlari tekshiruvi"""
        ident = DeviceIdentityManager.create_local_identity()
        self.assertTrue(ident.device_id)
        self.assertTrue(ident.hostname)
        self.assertIn(ident.agent_version, ["9.0.0", "9.0.1"])
        self.assertIn(ident.misa_version, ["9.0.0", "9.0.1"])
        self.assertTrue(ident.fingerprint)
        d = ident.to_dict()
        restored = DeviceIdentity.from_dict(d)
        self.assertEqual(restored.device_id, ident.device_id)
        self.assertEqual(restored.fingerprint, ident.fingerprint)

    def test_02_fingerprint(self):
        """2. Apparat barmoq izi (fingerprint) SHA-256 xeshi va mustahkamligi"""
        fp1 = DeviceIdentityManager.compute_fingerprint()
        fp2 = DeviceIdentityManager.compute_fingerprint()
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)  # SHA-256 64 ta hex belgidan iborat
        int(fp1, 16)  # To'g'ri hex formati ekanligini tekshirish

    def test_03_registration(self):
        """3. Qurilmani DeviceRegistry va HeartbeatManager ga ro'yxatga olish"""
        ident = DeviceIdentity(
            device_id="office_pc",
            hostname="OFFICE-DESKTOP",
            mac_address="AA:BB:CC:11:22:33",
            fingerprint="abc123def456" * 5
        )
        ok, msg = self.registry.register_or_update(ident)
        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        saved = self.registry.get_device("office_pc")
        self.assertIsNotNone(saved)
        self.assertEqual(saved.hostname, "OFFICE-DESKTOP")

    def test_04_duplicate_device(self):
        """4. Boshqa apparat xeshi bilan qurilmani soxtalashtirish (impersonation) to'silishi"""
        ident1 = DeviceIdentity(
            device_id="unique_pc",
            hostname="PC-1",
            fingerprint="1111111111111111111111111111111111111111111111111111111111111111"
        )
        self.registry.register_or_update(ident1)

        # Xuddi shu device_id, lekin o'zgargan fingerprint (soxtalashtirish urinishi)
        ident2 = DeviceIdentity(
            device_id="unique_pc",
            hostname="PC-1",
            fingerprint="2222222222222222222222222222222222222222222222222222222222222222"
        )
        ok, msg = self.registry.register_or_update(ident2)
        self.assertFalse(ok)
        self.assertIn("impersonation", msg)

    def test_05_pairing(self):
        """5. Telegram foydalanuvchisi va qurilma o'rtasida pairing token generatsiyasi va tekshiruvi"""
        dev_id = "home_pc_5"
        pairing_record = self.registry.pair_device(
            device_id=dev_id,
            user_id="user_777",
            fingerprint="fp_hash_value_123",
            mac_address="00:11:22:33:44:55"
        )
        self.assertTrue(pairing_record.pairing_token)
        self.assertEqual(pairing_record.paired_user_id, "user_777")

        # To'g'ri token va fingerprint bilan verifikatsiya
        ok, _ = self.registry.verify_pairing(
            device_id=dev_id,
            user_id="user_777",
            token=pairing_record.pairing_token,
            fingerprint="fp_hash_value_123"
        )
        self.assertTrue(ok)

        # Noto'g'ri foydalanuvchi rad etilishi
        ok_wrong_user, msg_user = self.registry.verify_pairing(
            device_id=dev_id,
            user_id="hacker_999",
            token=pairing_record.pairing_token
        )
        self.assertFalse(ok_wrong_user)

    # ========================================================
    # 6–10: HEARTBEAT
    # ========================================================

    def test_06_heartbeat_receive(self):
        """6. Heartbeat payload qabul qilinishi va metrikalar saqlanishi"""
        payload = HeartbeatPayload(
            device_id="node_6",
            timestamp=time.time(),
            agent_version="9.0.0",
            state=DeviceState.ONLINE,
            metrics={"cpu": 22.5, "ram": 55.0}
        )
        res = self.heartbeat_mgr.record_heartbeat(payload)
        self.assertTrue(res)
        self.assertEqual(self.heartbeat_mgr.get_device_state("node_6"), DeviceState.ONLINE)
        self.assertTrue(self.heartbeat_mgr.is_online("node_6"))

    def test_07_heartbeat_timeout(self):
        """7. Heartbeat kechikishi va timeout aniqlanishi"""
        t0 = 1000.0
        payload = HeartbeatPayload(device_id="node_7", timestamp=t0, state=DeviceState.ONLINE)
        self.heartbeat_mgr.record_heartbeat(payload)

        # 1.5s o'tganda (timeout=2.0s) -> hali ham online
        timed_out_1 = self.heartbeat_mgr.check_timeouts(current_time=t0 + 1.5)
        self.assertEqual(len(timed_out_1), 0)

        # 2.5s o'tganda -> timeout sodir bo'lishi kerak
        timed_out_2 = self.heartbeat_mgr.check_timeouts(current_time=t0 + 2.5)
        self.assertIn("node_7", timed_out_2)

    def test_08_offline_transition(self):
        """8. Timeout sababli qurilmaning OFFLINE holatiga o'tishi"""
        t0 = 2000.0
        self.heartbeat_mgr.record_heartbeat(HeartbeatPayload(device_id="node_8", timestamp=t0, state=DeviceState.ONLINE))
        self.assertTrue(self.heartbeat_mgr.is_online("node_8"))

        self.heartbeat_mgr.check_timeouts(current_time=t0 + 3.0)
        self.assertEqual(self.heartbeat_mgr.get_device_state("node_8"), DeviceState.OFFLINE)
        self.assertFalse(self.heartbeat_mgr.is_online("node_8"))

    def test_09_reconnect(self):
        """9. Tarmoq uzilishidan so'ng agentning avtomatik qayta ulanishi (reconnect)"""
        async def _run():
            agent = MisaPCAgent(heartbeat_manager=self.heartbeat_mgr)
            await agent.register()
            self.assertTrue(agent.is_running)

            await agent.disconnect()
            self.assertFalse(agent.is_running)
            self.assertEqual(self.heartbeat_mgr.get_device_state(agent.identity.device_id), DeviceState.OFFLINE)

            reconnected = await agent.reconnect()
            self.assertTrue(reconnected)
            self.assertTrue(agent.is_running)
            self.assertEqual(self.heartbeat_mgr.get_device_state(agent.identity.device_id), DeviceState.ONLINE)

        asyncio.run(_run())

    def test_10_state_transition(self):
        """10. To'liq holat mashinasi (FSM) o'tishlari va listener xabardor qilinishi"""
        events = []
        self.heartbeat_mgr.add_state_listener(lambda dev, old_s, new_s: events.append((old_s, new_s)))

        self.heartbeat_mgr.register_device("fsm_dev", initial_state=DeviceState.OFFLINE)
        self.heartbeat_mgr.set_device_state("fsm_dev", DeviceState.WAKING)
        self.heartbeat_mgr.set_device_state("fsm_dev", DeviceState.CONNECTING)
        self.heartbeat_mgr.set_device_state("fsm_dev", DeviceState.ONLINE)
        self.heartbeat_mgr.set_device_state("fsm_dev", DeviceState.OFFLINE)

        expected = [
            (DeviceState.OFFLINE, DeviceState.WAKING),
            (DeviceState.WAKING, DeviceState.CONNECTING),
            (DeviceState.CONNECTING, DeviceState.ONLINE),
            (DeviceState.ONLINE, DeviceState.OFFLINE)
        ]
        self.assertEqual(events, expected)

    # ========================================================
    # 11–15: WOL
    # ========================================================

    def test_11_magic_packet(self):
        """11. WoL Magic Packet (102 bayt, 6x0xFF + 16xMAC) tuzilishi"""
        mac = "12:34:56:78:9A:BC"
        packet = create_magic_packet(mac)
        self.assertEqual(len(packet), 102)
        self.assertEqual(packet[:6], b"\xff" * 6)
        mac_raw = bytes.fromhex("123456789ABC")
        for i in range(16):
            start = 6 + (i * 6)
            self.assertEqual(packet[start:start + 6], mac_raw)

    def test_12_invalid_mac(self):
        """12. Noto'g'ri MAC manzilda ValueError qo'zg'alishi"""
        invalid_macs = ["not_a_mac", "12:34:56", "12-34-56-78-9A-BC-DE", ""]
        for bad_mac in invalid_macs:
            with self.assertRaises(ValueError):
                create_magic_packet(bad_mac)

    def test_13_broadcast_configuration(self):
        """13. Broadcast IP va port parametrlarining konfiguratsiya qilinishi"""
        async def _run():
            custom_ip = "192.168.1.255"
            custom_port = 7
            relay = MockWakeRelay(succeed=True)
            mgr = WakeOnLanManager(relay=relay)
            await mgr.wake_device("11:22:33:44:55:66", broadcast_ip=custom_ip, port=custom_port)
            self.assertEqual(len(relay.sent_packets), 1)
            mac, b_ip, p = relay.sent_packets[0]
            self.assertEqual(b_ip, custom_ip)
            self.assertEqual(p, custom_port)

        asyncio.run(_run())

    def test_14_retry(self):
        """14. Vaqtinchalik tarmoq xatosida qayta urinish (retry) mexanizmi"""
        async def _run():
            # Dastlabki 2 ta urinish xato beradi, 3-sida muvaffaqiyat
            relay = MockWakeRelay(succeed=True, failure_count=2)
            mgr = WakeOnLanManager(relay=relay, retry_count=3, retry_delay=0.01)
            res = await mgr.wake_device("AA:BB:CC:DD:EE:FF")
            self.assertTrue(res["success"])
            self.assertEqual(relay.attempts, 3)

        asyncio.run(_run())

    def test_15_mock_relay(self):
        """15. MockWakeRelay izolatsiyasi (haqiqiy tarmoqqa murojaatsiz)"""
        async def _run():
            relay = MockWakeRelay(succeed=True)
            res = await relay.send_wake("00:11:22:33:44:55")
            self.assertTrue(res)
            self.assertEqual(len(relay.sent_packets), 1)

        asyncio.run(_run())

    # ========================================================
    # 16–22: SECURITY
    # ========================================================

    def test_16_unauthorized_user(self):
        """16. Ruxsatsiz Telegram foydalanuvchisi so'rovining rad etilishi"""
        em = EnvelopeManager(authorized_user_id=self.admin_id)
        env = em.create_envelope(device_id="pc", action="status", user_id="unauthorized_999")
        ok, msg = em.validate_envelope(env)
        self.assertFalse(ok)
        self.assertIn("UNAUTHORIZED", msg)

    def test_17_authorized_user(self):
        """17. Vakolatli Telegram foydalanuvchisi so'rovining qabul qilinishi"""
        em = EnvelopeManager(authorized_user_id=self.admin_id)
        env = em.create_envelope(device_id="pc", action="status", user_id=self.admin_id)
        ok, msg = em.validate_envelope(env)
        self.assertTrue(ok)
        self.assertEqual(msg, "OK")

    def test_18_expired_request(self):
        """18. Muddati o'tgan (expired) so'rovning rad etilishi"""
        em = EnvelopeManager(authorized_user_id=self.admin_id, default_ttl=5.0)
        t0 = 5000.0
        with patch("time.time", return_value=t0):
            env = em.create_envelope(device_id="pc", action="status", user_id=self.admin_id)

        # 6 soniyadan keyin (TTL tugagan)
        ok, msg = em.validate_envelope(env, current_time=t0 + 6.0)
        self.assertFalse(ok)
        self.assertIn("EXPIRED", msg)

    def test_19_replay_request(self):
        """19. Bir xil nonce bilan Replay Attack aniqlanishi va to'silishi"""
        em = EnvelopeManager(authorized_user_id=self.admin_id)
        env = em.create_envelope(device_id="pc", action="status", user_id=self.admin_id)

        # 1-marta: qabul qilinadi
        ok1, _ = em.validate_envelope(env)
        self.assertTrue(ok1)

        # 2-marta takrorlangan nonce: REPLAY ATTACK BLOCKED
        ok2, msg2 = em.validate_envelope(env)
        self.assertFalse(ok2)
        self.assertIn("REPLAY_ATTACK", msg2)

    def test_20_duplicate_request(self):
        """20. Idempotentlik: bajarilgan buyruq qayta yuborilganda ikkinchi marta bajarilmasligi"""
        em = EnvelopeManager(authorized_user_id=self.admin_id)
        env = em.create_envelope(device_id="pc", action="status", user_id=self.admin_id)

        em.record_execution_result(env.request_id, {"success": True, "cached": True})
        self.assertTrue(em.is_executed(env.request_id))

        ok, msg = em.validate_envelope(env)
        self.assertFalse(ok)
        self.assertIn("DUPLICATE_REQUEST", msg)

    def test_21_invalid_nonce(self):
        """21. Nonce bo'sh bo'lgan konvertning rad etilishi"""
        em = EnvelopeManager(authorized_user_id=self.admin_id)
        env = em.create_envelope(device_id="pc", action="status", user_id=self.admin_id)
        env.nonce = ""
        ok, msg = em.validate_envelope(env)
        self.assertFalse(ok)
        self.assertIn("INVALID_NONCE", msg)

    def test_22_malformed_envelope(self):
        """22. Noto'g'ri / chala to'ldirilgan (malformed) konvertning rad etilishi"""
        em = EnvelopeManager(authorized_user_id=self.admin_id)
        env = em.create_envelope(device_id="pc", action="", user_id=self.admin_id)
        ok, msg = em.validate_envelope(env)
        self.assertFalse(ok)
        self.assertIn("MALFORMED_ENVELOPE", msg)

    # ========================================================
    # 23–27: AGENT
    # ========================================================

    def test_23_connect(self):
        """23. Agentning ishga tushishi, ro'yxatdan o'tishi va ONLINE bo'lishi"""
        async def _run():
            agent = MisaPCAgent(heartbeat_manager=self.heartbeat_mgr)
            res = await agent.register()
            self.assertTrue(res)
            self.assertEqual(agent.agent_state, "ONLINE")
            self.assertTrue(self.heartbeat_mgr.is_online(agent.identity.device_id))

        asyncio.run(_run())

    def test_24_disconnect(self):
        """24. Agentning xavfsiz to'xtatilishi va OFFLINE holatiga o'tishi"""
        async def _run():
            agent = MisaPCAgent(heartbeat_manager=self.heartbeat_mgr)
            await agent.register()
            await agent.disconnect()
            self.assertEqual(agent.agent_state, "OFFLINE")
            self.assertFalse(agent.is_running)

        asyncio.run(_run())

    def test_25_reconnect(self):
        """25. Tarmoq tiklangach agentning qayta ulanishi va backoff tiklanishi"""
        async def _run():
            agent = MisaPCAgent(heartbeat_manager=self.heartbeat_mgr)
            agent._backoff = 8.0
            await agent.reconnect()
            self.assertEqual(agent._backoff, 1.0)
            self.assertEqual(agent.agent_state, "ONLINE")

        asyncio.run(_run())

    def test_26_command_receive(self):
        """26. Agent tomonidan xavfsiz buyruqning qabul qilinishi va bajarilishi"""
        async def _run():
            agent = MisaPCAgent(envelope_manager=self.envelope_mgr)
            await agent.register()

            env = self.envelope_mgr.create_envelope(
                device_id=agent.identity.device_id,
                action="status",
                user_id=self.admin_id
            )
            res = await agent.handle_remote_command(env)
            self.assertTrue(res.get("success"))
            self.assertEqual(res["result"]["hostname"], agent.identity.hostname)

        asyncio.run(_run())

    def test_27_command_result(self):
        """27. Buyruq natijasi formati va maxfiy ma'lumotlar oshkor bo'lmasligi"""
        async def _run():
            agent = MisaPCAgent(envelope_manager=self.envelope_mgr)
            await agent.register()

            env = self.envelope_mgr.create_envelope(
                device_id=agent.identity.device_id,
                action="calculator",
                params={"expression": "12 * 12"},
                user_id=self.admin_id
            )
            res = await agent.handle_remote_command(env)
            self.assertTrue(res.get("success"))
            self.assertIn("result", res)
            self.assertNotIn("password", str(res))
            self.assertNotIn("token", str(res))

        asyncio.run(_run())

    # ========================================================
    # 28–33: REMOTE PIPELINE
    # ========================================================

    def test_28_status(self):
        """28. Status so'rovi: Telegramdan PC holatini olish"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                heartbeat_manager=self.heartbeat_mgr,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            res = await orch.handle_message(chat_id=100, user_id=self.admin_id, text="/pc")
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("action"), "status")
            self.assertTrue(any("Kompyuter Holati" in m.get("text", "") for m in self.transport.sent_messages))

        asyncio.run(_run())

    def test_29_wake(self):
        """29. Wake so'rovi: WoL paketi yuborilib WAKING holatiga o'tishi"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                heartbeat_manager=self.heartbeat_mgr,
                wol_manager=self.wol_mgr,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            dev_id = "test_pc_29"
            self.heartbeat_mgr.register_device(dev_id, initial_state=DeviceState.OFFLINE)

            # Heartbeat kelmaydi, timeout kutish 0.2s qilib beriladi
            res = await orch.execute_wake_pipeline(
                device_id=dev_id,
                mac_address="00:11:22:33:44:55",
                chat_id=100,
                user_id=self.admin_id,
                wait_timeout=0.2,
                poll_interval=0.05
            )
            self.assertFalse(res.get("success"))
            self.assertEqual(len(self.relay.sent_packets), 1)

        asyncio.run(_run())

    def test_30_wake_heartbeat(self):
        """30. Wake -> Heartbeat -> Online muvaffaqiyatli ketma-ketligi"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                heartbeat_manager=self.heartbeat_mgr,
                wol_manager=self.wol_mgr,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            dev_id = "test_pc_30"
            self.heartbeat_mgr.register_device(dev_id, initial_state=DeviceState.OFFLINE)

            # WoL jo'natilgach boshqa asinxron korutina heartbeat yuboradi
            async def _send_wake_delayed():
                await asyncio.sleep(0.1)
                self.heartbeat_mgr.record_heartbeat(HeartbeatPayload(device_id=dev_id, timestamp=time.time(), state=DeviceState.ONLINE))

            asyncio.create_task(_send_wake_delayed())

            res = await orch.execute_wake_pipeline(
                device_id=dev_id,
                mac_address="00:11:22:33:44:55",
                chat_id=100,
                user_id=self.admin_id,
                wait_timeout=2.0,
                poll_interval=0.05
            )
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("state"), "online")
            self.assertEqual(self.heartbeat_mgr.get_device_state(dev_id), DeviceState.ONLINE)

        asyncio.run(_run())

    def test_31_wake_timeout(self):
        """31. Kompyuter uyg'onmaganda aniq xatolik xabari bilan to'xtash"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                heartbeat_manager=self.heartbeat_mgr,
                wol_manager=self.wol_mgr,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            dev_id = "stubborn_node_31"
            self.heartbeat_mgr.register_device(dev_id, initial_state=DeviceState.OFFLINE)

            res = await orch.execute_wake_pipeline(
                device_id=dev_id,
                mac_address="AA:BB:CC:DD:EE:FF",
                chat_id=100,
                user_id=self.admin_id,
                wait_timeout=0.2,
                poll_interval=0.05
            )
            self.assertFalse(res.get("success"))
            self.assertEqual(res.get("error"), "HEARTBEAT_TIMEOUT")
            # Telegram xabarida sabab ko'rsatilgan
            self.assertTrue(any("uyg'onmadi" in m.get("text", "") for m in self.transport.sent_messages))

        asyncio.run(_run())

    def test_32_verify_online(self):
        """32. Kompyuter allaqachon online bo'lganda ortiqcha WoL yuborilmasligi"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                heartbeat_manager=self.heartbeat_mgr,
                wol_manager=self.wol_mgr,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            dev_id = "already_online_pc"
            self.heartbeat_mgr.register_device(dev_id, initial_state=DeviceState.ONLINE)

            res = await orch.execute_wake_pipeline(
                device_id=dev_id,
                mac_address="11:22:33:44:55:66",
                chat_id=100,
                user_id=self.admin_id
            )
            self.assertTrue(res.get("success"))
            self.assertEqual(len(self.relay.sent_packets), 0)  # WoL yuborilmadi

        asyncio.run(_run())

    def test_33_complete_task(self):
        """33. Kompyuter online bo'lgach asbob (calculator) orqali to'liq topshiriq bajarilishi"""
        async def _run():
            agent = MisaPCAgent(envelope_manager=self.envelope_mgr)
            await agent.register()

            env = self.envelope_mgr.create_envelope(
                device_id=agent.identity.device_id,
                action="calculator",
                params={"expression": "100 + 250"},
                user_id=self.admin_id
            )
            res = await agent.handle_remote_command(env)
            self.assertTrue(res.get("success"))
            self.assertIn("350", str(res.get("result")))

        asyncio.run(_run())

    # ========================================================
    # 34–36: CONFIRMATION
    # ========================================================

    def test_34_dangerous_action_confirmation(self):
        """34. Xavfli amal (shutdown) uchun avtomatik confirmation so'rovi chiqishi"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            res = await orch.handle_message(chat_id=100, user_id=self.admin_id, text="/shutdown")
            self.assertTrue(res.get("confirmation_required"))
            self.assertTrue(res.get("request_id"))
            # Confirmation tugmalari yuborilgan
            last_msg = self.transport.sent_messages[-1]
            self.assertIn("inline_keyboard", last_msg.get("reply_markup", {}))

        asyncio.run(_run())

    def test_35_expired_confirmation(self):
        """35. Muddati o'tgan (expired) tasdiqlash tugmasi bosilganda rad etilishi"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            # 0.1s TTL bilan saqlash
            env = self.envelope_mgr.create_envelope(device_id="pc", action="shutdown", user_id=self.admin_id)
            self.gateway.store_pending_confirmation(env.request_id, env, ttl=0.1)

            await asyncio.sleep(0.15)
            # Tasdiqlash bosildi
            res = await orch.handle_callback_query(
                callback_query_id="cb_1",
                chat_id=100,
                user_id=self.admin_id,
                data=f"confirm_yes:{env.request_id}"
            )
            self.assertFalse(res.get("success"))
            self.assertEqual(res.get("error"), "CONFIRMATION_EXPIRED")

        asyncio.run(_run())

    def test_36_cancelled_confirmation(self):
        """36. Foydalanuvchi tasdiqlashni bekor qilganda (confirm_no) xavfli amal bajarilmasligi"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            env = self.envelope_mgr.create_envelope(device_id="pc", action="restart", user_id=self.admin_id)
            self.gateway.store_pending_confirmation(env.request_id, env, ttl=60.0)

            res = await orch.handle_callback_query(
                callback_query_id="cb_2",
                chat_id=100,
                user_id=self.admin_id,
                data=f"confirm_no:{env.request_id}"
            )
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("action"), "cancelled")
            self.assertIsNone(self.gateway.get_pending_confirmation(env.request_id))

        asyncio.run(_run())

    # ========================================================
    # 37–40: TELEGRAM
    # ========================================================

    def test_37_command_parser(self):
        """37. Telegram buyruqlar va o'zbek tili tabiiy matnlarini parse qilish"""
        self.assertEqual(self.gateway.parse_command("/pc")["action"], "status")
        self.assertEqual(self.gateway.parse_command("/status")["action"], "status")
        self.assertEqual(self.gateway.parse_command("🟢 PC Status")["action"], "status")
        self.assertEqual(self.gateway.parse_command("Misa, kompyuterim yoqilganmi?")["action"], "status")

        self.assertEqual(self.gateway.parse_command("/wake")["action"], "wake")
        self.assertEqual(self.gateway.parse_command("⚡ Wake PC")["action"], "wake")
        self.assertEqual(self.gateway.parse_command("Misa, kompyuterni yoq")["action"], "wake")

        self.assertEqual(self.gateway.parse_command("/restart")["action"], "restart")
        self.assertTrue(self.gateway.parse_command("/restart")["high_risk"])

        self.assertEqual(self.gateway.parse_command("/shutdown")["action"], "shutdown")
        self.assertTrue(self.gateway.parse_command("/shutdown")["high_risk"])

        pair_cmd = self.gateway.parse_command("/pair secret_token_abc")
        self.assertEqual(pair_cmd["action"], "pair")
        self.assertEqual(pair_cmd["params"]["pairing_token"], "secret_token_abc")

    def test_38_callback_button(self):
        """38. Inline tugmalar (callback query) javob berish va marshrutlash"""
        async def _run():
            update = {
                "callback_query": {
                    "id": "cb_query_1",
                    "from": {"id": int(self.admin_id)},
                    "data": "btn_status",
                    "message": {"chat": {"id": 100}}
                }
            }
            res = await self.gateway.handle_update(update)
            self.assertTrue(res.get("handled"))
            self.assertTrue(res.get("authorized"))
            self.assertEqual(res.get("button_key"), "btn_status")
            self.assertEqual(len(self.transport.answered_callbacks), 1)

        asyncio.run(_run())

    def test_39_authorization(self):
        """39. Begona foydalanuvchilarning Update darajasida to'liq to'silishi"""
        async def _run():
            bad_update = {
                "message": {
                    "chat": {"id": 666},
                    "from": {"id": 666},
                    "text": "/pc"
                }
            }
            res = await self.gateway.handle_update(bad_update)
            self.assertTrue(res.get("handled"))
            self.assertFalse(res.get("authorized"))
            self.assertEqual(res.get("action"), "denied")
            self.assertTrue(any("Ruxsat berilmadi" in m.get("text", "") for m in self.transport.sent_messages))

        asyncio.run(_run())

    def test_40_mocked_telegram_e2e(self):
        """40. Mocked Telegram E2E simulyatsiyasi: Xabar -> Gateway -> WoL -> Agent -> Natija"""
        async def _run():
            orch = RemoteOrchestrator(
                gateway=self.gateway,
                heartbeat_manager=self.heartbeat_mgr,
                wol_manager=self.wol_mgr,
                envelope_manager=self.envelope_mgr,
                device_registry=self.registry
            )
            # 1. Qurilma dastlab oflayn
            dev_id = orch.pc_agent.identity.device_id
            self.heartbeat_mgr.register_device(dev_id, initial_state=DeviceState.OFFLINE)
            self.assertFalse(self.heartbeat_mgr.is_online(dev_id))

            # 2. Telegram foydalanuvchi "Misa, kompyuterni yoq" deb yozadi
            async def _wake_pc_agent():
                await asyncio.sleep(0.1)
                await orch.pc_agent.send_heartbeat()

            asyncio.create_task(_wake_pc_agent())

            res = await orch.handle_message(
                chat_id=500,
                user_id=self.admin_id,
                text="Misa, kompyuterni yoq"
            )
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("state"), "online")

            # 3. Telegramga barcha bosqichlar va tayyorlik xabari kelgan
            sent_texts = [m.get("text", "") for m in self.transport.sent_messages]
            self.assertTrue(any("online bo'ldi" in t for t in sent_texts))
            self.assertTrue(any("Masofaviy boshqaruv tayyor" in t for t in sent_texts))

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
