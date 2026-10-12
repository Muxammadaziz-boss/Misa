# ========== tests/test_v8_telegram_production.py ==========
# Phase 46 — Telegram Production Webhook, Security, Railway readiness tests

import os
import asyncio
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from core.v8.telegram_gateway import MockTelegramTransport
from core.v8.telegram_identity import TelegramIdentityManager
from core.v8.account_device import AccountDeviceManager
from core.v8.auth_session import SessionManager
from core.v8.universal_bot import UniversalTelegramBot
from core.v8.telegram_webhook import (
    UpdateIdempotencyStore,
    TelegramWebhookService,
    register_telegram_routes,
    build_telegram_webhook_service,
)
from core.api_server import create_app, handle_health


class TestTelegramBotCommandsProduction(unittest.TestCase):
    """Core bot commands including /session and /logout."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="misa_tg_prod_")
        self.tg_storage = os.path.join(self.temp_dir, "tg.json")
        self.adm_storage = os.path.join(self.temp_dir, "adm.json")
        self.identity_mgr = TelegramIdentityManager(storage_path=self.tg_storage)
        self.adm = AccountDeviceManager(storage_path=self.adm_storage)
        self.transport = MockTelegramTransport()
        self.bot = UniversalTelegramBot(
            identity_manager=self.identity_mgr,
            account_device_manager=self.adm,
            transport=self.transport,
        )
        req, otp, _, _ = self.identity_mgr.create_link_request("user_a")
        self.identity_mgr.verify_otp(otp, telegram_user_id=111222, username="user_a")
        self.adm.register_device("user_a", "pc-1", "Uy PC", status="online")
        self.adm.select_device("user_a", "pc-1")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        SessionManager._default_instance = None

    def _msg(self, tg_id, text):
        return {
            "message": {
                "message_id": 1,
                "chat": {"id": tg_id},
                "from": {"id": tg_id, "username": "u"},
                "text": text,
            }
        }

    def test_start_help_link_account_devices_select(self):
        for cmd in ("/start", "/help", "/account", "/devices"):
            asyncio.run(self.bot.process_update(self._msg(111222, cmd)))
        texts = " ".join(m["text"] for m in self.transport.sent_messages)
        self.assertIn("/link", texts)
        self.assertIn("Uy PC", texts)

    def test_status_shows_device_state(self):
        asyncio.run(self.bot.process_update(self._msg(111222, "/status")))
        text = self.transport.sent_messages[-1]["text"]
        self.assertIn("ONLINE", text)
        self.assertIn("Uy PC", text)

    def test_session_and_logout_flow(self):
        sm = SessionManager.get_default_instance()
        sm.create_session("user_a", "pc-1", ttl=900.0)

        asyncio.run(self.bot.process_update(self._msg(111222, "/session")))
        self.assertIn("Faol", self.transport.sent_messages[-1]["text"])
        self.assertNotIn("session_id", self.transport.sent_messages[-1]["text"].lower())

        asyncio.run(self.bot.process_update(self._msg(111222, "/logout")))
        self.assertIn("yopildi", self.transport.sent_messages[-1]["text"].lower())

        asyncio.run(self.bot.process_update(self._msg(111222, "/session")))
        self.assertIn("Faol emas", self.transport.sent_messages[-1]["text"])


class TestTelegramWebhookSecurity(unittest.TestCase):
    def setUp(self):
        self.transport = MockTelegramTransport()
        self.bot = UniversalTelegramBot(transport=self.transport)
        self.svc = TelegramWebhookService(
            bot=self.bot,
            transport=self.transport,
            webhook_secret="test-webhook-secret-xyz",
            bot_token="123456789:AAFakeTokenForTestsOnly",
        )

    def test_idempotency_duplicate_update(self):
        store = UpdateIdempotencyStore()
        self.assertTrue(store.claim(100))
        self.assertFalse(store.claim(100))
        self.assertTrue(store.claim(101))

    def test_invalid_secret_rejected(self):
        async def _run():
            req = MagicMock()
            req.match_info = {"secret": "wrong-secret"}
            req.headers = {}
            req.path = "/telegram/webhook/wrong-secret"
            resp = await self.svc.handle_webhook(req)
            self.assertEqual(resp.status, 403)

        asyncio.run(_run())


class TestTelegramWebhookIntegration(AioHTTPTestCase):
    def setUp(self):
        super().setUp()
        self._env_patch = patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "123456789:AAFakeTokenForTestsOnly",
                "TELEGRAM_WEBHOOK_SECRET": "integration-secret-abc",
                "TELEGRAM_USE_WEBHOOK": "true",
                "TELEGRAM_BOT_USERNAME": "TestBot",
            },
            clear=False,
        )
        self._env_patch.start()
        self.transport = MockTelegramTransport()
        self.bot = UniversalTelegramBot(transport=self.transport)
        self.svc = TelegramWebhookService(
            bot=self.bot,
            transport=self.transport,
            webhook_secret="integration-secret-abc",
            bot_token="123456789:AAFakeTokenForTestsOnly",
        )

    def tearDown(self):
        self._env_patch.stop()
        super().tearDown()

    async def get_application(self):
        app = web.Application()
        register_telegram_routes(app, self.svc)
        return app

    async def test_valid_webhook_secret_accepts_update(self):
        update = {
            "update_id": 42,
            "message": {
                "message_id": 1,
                "chat": {"id": 999},
                "from": {"id": 999},
                "text": "/help",
            },
        }
        path = self.svc.webhook_path()
        resp = await self.client.post(
            path,
            json=update,
            headers={"X-Telegram-Bot-Api-Secret-Token": "integration-secret-abc"},
        )
        self.assertEqual(resp.status, 200)
        await asyncio.sleep(0.05)
        self.assertTrue(len(self.transport.sent_messages) >= 1)

    async def test_duplicate_update_idempotent(self):
        update = {
            "update_id": 77,
            "message": {
                "message_id": 2,
                "chat": {"id": 888},
                "from": {"id": 888},
                "text": "/start",
            },
        }
        path = self.svc.webhook_path()
        headers = {"X-Telegram-Bot-Api-Secret-Token": "integration-secret-abc"}
        r1 = await self.client.post(path, json=update, headers=headers)
        r2 = await self.client.post(path, json=update, headers=headers)
        self.assertEqual(r1.status, 200)
        self.assertEqual(r2.status, 200)
        await asyncio.sleep(0.05)
        self.assertEqual(len(self.transport.sent_messages), 1)

    async def test_invalid_webhook_secret_forbidden(self):
        resp = await self.client.post(
            "/telegram/webhook/wrong",
            json={"update_id": 1, "message": {"text": "/start"}},
        )
        self.assertEqual(resp.status, 403)

    async def test_malformed_payload_rejected(self):
        path = self.svc.webhook_path()
        resp = await self.client.post(path, data=b"not-json")
        self.assertIn(resp.status, (400, 415))

    async def test_oversized_payload_rejected_413(self):
        path = self.svc.webhook_path()
        huge_payload = b"x" * (256 * 1024 + 10)
        resp = await self.client.post(path, data=huge_payload, headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status, 413)

    async def test_ready_endpoint(self):
        resp = await self.client.get("/ready")
        self.assertIn(resp.status, (200, 503))
        data = await resp.json()
        self.assertIn("checks", data)
        self.assertIn("telegram_bot", data["checks"])

    async def test_shutdown_rejects_new_updates(self):
        await self.svc.begin_shutdown()
        path = self.svc.webhook_path()
        resp = await self.client.post(
            path,
            json={"update_id": 999},
            headers={"X-Telegram-Bot-Api-Secret-Token": "integration-secret-abc"},
        )
        self.assertEqual(resp.status, 503)


class TestMultiTenantIsolationTelegram(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="misa_tg_isolation_")
        self.tg_storage = os.path.join(self.temp_dir, "tg.json")
        self.adm_storage = os.path.join(self.temp_dir, "adm.json")
        self.identity_mgr = TelegramIdentityManager(storage_path=self.tg_storage)
        self.adm = AccountDeviceManager(storage_path=self.adm_storage)
        self.transport = MockTelegramTransport()
        self.bot = UniversalTelegramBot(
            identity_manager=self.identity_mgr,
            account_device_manager=self.adm,
            transport=self.transport,
        )
        req_a, otp_a, _, _ = self.identity_mgr.create_link_request("user_a")
        req_b, otp_b, _, _ = self.identity_mgr.create_link_request("user_b")
        self.identity_mgr.verify_otp(otp_a, telegram_user_id=1001)
        self.identity_mgr.verify_otp(otp_b, telegram_user_id=2002)
        self.adm.register_device("user_a", "dev-a", "A PC", status="online")
        self.adm.register_device("user_b", "dev-b", "B PC", status="online")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cross_user_device_access_denied(self):
        async def _run():
            await self.bot.process_update({
                "message": {
                    "chat": {"id": 1001},
                    "from": {"id": 1001},
                    "text": "/select dev-b",
                }
            })
            text = self.transport.sent_messages[-1]["text"]
            self.assertNotIn("B PC", text)
            self.assertTrue("Xatolik" in text or "topilmadi" in text.lower())

        asyncio.run(_run())


class TestRailwayHealthEndpoints(unittest.TestCase):
    def test_health_liveness_no_secrets(self):
        async def _run():
            req = MagicMock()
            resp = await handle_health(req)
            body = resp.body
            import json
            data = json.loads(body.decode())
            self.assertEqual(data.get("status"), "ok")
            for forbidden in (
                "TELEGRAM_BOT_TOKEN",
                "SUPABASE_SECRET",
                "service_role",
                "access_token",
            ):
                self.assertNotIn(forbidden, body.decode())

        asyncio.run(_run())

    @patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "123:ABC",
            "TELEGRAM_WEBHOOK_SECRET": "sec",
            "TELEGRAM_USE_WEBHOOK": "true",
        },
    )
    def test_build_webhook_service_configured(self):
        svc = build_telegram_webhook_service()
        self.assertIsNotNone(svc)
        self.assertIn("/telegram/webhook/", svc.webhook_path())


class TestRailwayProductionFixes(unittest.TestCase):
    """Regression tests for Railway Telegram OTP linking, Supabase PGRST301, webhook secret redaction, and OAuth state errors."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="misa_prod_fixes_")
        self.tg_storage = os.path.join(self.temp_dir, "tg_local.json")
        self.cloud_storage = os.path.join(self.temp_dir, "tg_cloud.json")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        TelegramIdentityManager._default_instance = None

    def test_supabase_headers_never_mix_publishable_with_sb_secret(self):
        mgr = TelegramIdentityManager(storage_path=self.tg_storage)
        with patch.object(
            mgr,
            "_get_supabase_config",
            return_value=("https://example.supabase.co", "sb_publishable_anon123", "sb_secret_srv456"),
        ):
            # Service-role / sb_secret mode (no user JWT): apikey MUST match sb_secret
            h_srv = mgr._build_supabase_headers(auth_token=None, prefer_user_token=False)
            self.assertEqual(h_srv["apikey"], "sb_secret_srv456")
            self.assertEqual(h_srv["Authorization"], "Bearer sb_secret_srv456")

            # Valid 3-part user JWT with prefer_user_token=True: apikey=anon, Authorization=Bearer <jwt>
            fake_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTEifQ.c2lnbmF0dXJl"
            h_jwt = mgr._build_supabase_headers(auth_token=fake_jwt, prefer_user_token=True)
            self.assertEqual(h_jwt["apikey"], "sb_publishable_anon123")
            self.assertEqual(h_jwt["Authorization"], f"Bearer {fake_jwt}")

    def test_link_sync_nested_payload_and_cloud_otp_verification(self):
        from core.api_server import handle_telegram_link_sync

        local_mgr = TelegramIdentityManager(storage_path=self.tg_storage)
        cloud_mgr = TelegramIdentityManager(storage_path=self.cloud_storage)
        TelegramIdentityManager._default_instance = cloud_mgr

        req_obj, raw_otp, _, _ = local_mgr.create_link_request("user-sync-1")
        nested_payload = {"request": req_obj.to_dict()}

        async def _run():
            mock_req = MagicMock()
            mock_req.headers = {}
            mock_req.json = AsyncMock(return_value=nested_payload)
            with patch(
                "core.api_server.resolve_auth_identity",
                return_value=("user-sync-1", {"id": "user-sync-1"}, None, None),
            ):
                resp = await handle_telegram_link_sync(mock_req)
            self.assertEqual(resp.status, 200)

            ok, msg, acc = cloud_mgr.verify_otp(
                raw_otp,
                telegram_user_id=777888999,
                username="railway_tester",
                first_name="Tester",
            )
            self.assertTrue(ok, f"Expected OTP verification to succeed after sync, got: {msg}")
            self.assertIsNotNone(acc)
            self.assertEqual(acc.misa_user_id, "user-sync-1")

        asyncio.run(_run())

    def test_webhook_registration_redacts_secret_in_logs(self):
        transport = MockTelegramTransport()
        bot = UniversalTelegramBot(transport=transport)
        secret = "super_sensitive_webhook_secret_999"
        svc = TelegramWebhookService(
            bot=bot,
            transport=transport,
            webhook_secret=secret,
            bot_token="123456:AAFakeToken",
        )

        mock_resp = MagicMock()
        mock_resp.json = AsyncMock(return_value={"ok": True})
        mock_post_cm = MagicMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_post_cm.__aexit__ = AsyncMock(return_value=None)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)
        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        async def _run():
            with patch("aiohttp.ClientSession", return_value=mock_session_cm):
                with self.assertLogs("core.v8.telegram_webhook", level="INFO") as cm:
                    ok, _ = await svc.register_webhook("https://misa.up.railway.app")
                    self.assertTrue(ok)
            combined_logs = "\n".join(cm.output)
            self.assertNotIn(secret, combined_logs)
            self.assertIn("[REDACTED]", combined_logs)

        asyncio.run(_run())

    def test_otp_bruteforce_rate_limit_per_telegram_user(self):
        mgr = TelegramIdentityManager(storage_path=self.tg_storage)
        mgr.create_link_request("victim_user")
        attacker_tg_id = 666555444

        for i in range(5):
            ok, msg, _ = mgr.verify_otp(f"{100000 + i}", telegram_user_id=attacker_tg_id)
            self.assertFalse(ok)

        ok6, msg6, _ = mgr.verify_otp("999999", telegram_user_id=attacker_tg_id)
        self.assertFalse(ok6)
        self.assertIn("RATE_LIMITED", msg6)

    def test_oauth_callback_bad_oauth_state_returns_clear_message(self):
        from core.api_server import handle_oauth_callback

        async def _run():
            req = MagicMock()
            req.query = {
                "error": "invalid_request",
                "error_code": "bad_oauth_state",
                "error_description": "OAuth state not found or expired",
            }
            req.headers = {"Host": "misa.up.railway.app"}
            resp = await handle_oauth_callback(req)
            self.assertEqual(resp.status, 200)
            self.assertIn("bad_oauth_state", resp.text)
            self.assertIn("muddati tugagan", resp.text)

        asyncio.run(_run())

    def test_oauth_state_creation_storage_and_retrieval_consistency(self):
        import json
        from core.api_server import (
            handle_oauth_session_save,
            handle_oauth_session_get,
            _pending_oauth_sessions,
            _pending_oauth_lock,
        )

        with _pending_oauth_lock:
            _pending_oauth_sessions.clear()

        async def _run():
            state_id = "oauth_state_lifecycle_test_001"

            # 1. Pre-register state (creation: action="init")
            init_req = MagicMock()
            init_req.query = {}
            init_req.json = AsyncMock(return_value={"state": state_id, "action": "init"})
            init_resp = await handle_oauth_session_save(init_req)
            self.assertEqual(init_resp.status, 200)
            init_body = json.loads(init_resp.text)
            self.assertEqual(init_body["status"], "pending")
            self.assertEqual(init_body["state"], state_id)

            # 2. Early poll BEFORE callback completes must return 404 (pending) and MUST NOT pop the state!
            early_get = MagicMock()
            early_get.query = {"state": state_id}
            early_resp = await handle_oauth_session_get(early_get)
            self.assertIn(early_resp.status, (200, 404))
            early_body = json.loads(early_resp.text)
            self.assertEqual(early_body["status"], "pending")
            self.assertIn(state_id, _pending_oauth_sessions)

            # 3. Callback arrives WITHOUT state (e.g., Supabase stripped ?state=... on redirect):
            #    It must bind to the pre-registered pending state_id!
            cb_req = MagicMock()
            cb_req.query = {}
            cb_req.json = AsyncMock(
                return_value={
                    "state": "",
                    "access_token": "tok_bound_to_pending_123",
                    "refresh_token": "ref_bound_123",
                }
            )
            cb_resp = await handle_oauth_session_save(cb_req)
            self.assertEqual(cb_resp.status, 200)
            cb_body = json.loads(cb_resp.text)
            self.assertEqual(cb_body["state"], state_id)

            # 4. Subsequent poll with state_id retrieves the completed session and pops it (one-time use)
            final_get = MagicMock()
            final_get.query = {"state": state_id}
            final_resp = await handle_oauth_session_get(final_get)
            self.assertEqual(final_resp.status, 200)
            final_body = json.loads(final_resp.text)
            self.assertTrue(final_body["ok"])
            self.assertEqual(final_body["session"]["access_token"], "tok_bound_to_pending_123")

            # 5. Replay poll with same state_id returns 404
            replay_resp = await handle_oauth_session_get(final_get)
            self.assertEqual(replay_resp.status, 404)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()


