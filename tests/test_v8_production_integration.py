# ========== tests/test_v8_production_integration.py ==========
# Phase 46 & Production Integration Regression Tests
# Tests production CORS, remote IP handling, auth resolution, Telegram sync, and Supabase security

import os
import sys
import json
import time
import unittest
import asyncio
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from core.api_server import (
    create_app,
    cors_middleware,
    is_production_or_remote_enabled,
    resolve_auth_identity,
)
from core.v8.telegram_identity import (
    TelegramIdentityManager,
    UserTelegramLink,
    TelegramIdentity,
)


class TestCORSProductionIntegration(unittest.TestCase):
    """Test production vs development CORS and remote IP security middleware."""

    def setUp(self):
        self._orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_is_production_or_remote_enabled_default_dev(self):
        os.environ["ENVIRONMENT"] = "development"
        os.environ.pop("RAILWAY_ENVIRONMENT", None)
        os.environ.pop("MISA_ALLOW_REMOTE_API", None)
        self.assertFalse(is_production_or_remote_enabled())

    def test_is_production_or_remote_enabled_railway(self):
        os.environ["RAILWAY_ENVIRONMENT"] = "production"
        self.assertTrue(is_production_or_remote_enabled())

    def test_is_production_or_remote_enabled_explicit_flag(self):
        os.environ["MISA_ALLOW_REMOTE_API"] = "true"
        self.assertTrue(is_production_or_remote_enabled())

    def test_is_production_or_remote_enabled_env_production(self):
        os.environ["ENVIRONMENT"] = "production"
        self.assertTrue(is_production_or_remote_enabled())


class TestProductionAPIServerIntegration(AioHTTPTestCase):
    """Integration test suite for aiohttp API Server with production middleware."""

    async def get_application(self):
        self._orig_env = dict(os.environ)
        os.environ["ENVIRONMENT"] = "production"
        os.environ["RAILWAY_ENVIRONMENT"] = "production"
        os.environ["MISA_ALLOW_REMOTE_API"] = "true"
        return create_app()

    def tearDown(self):
        super().tearDown()
        if hasattr(self, "_orig_env"):
            os.environ.clear()
            os.environ.update(self._orig_env)

    @unittest_run_loop
    async def test_health_endpoint_200(self):
        resp = await self.client.request("GET", "/health")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertEqual(data.get("status"), "ok")

    @unittest_run_loop
    async def test_options_preflight_returns_204_with_cors_headers(self):
        headers = {
            "Origin": "https://misa.up.railway.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        }
        resp = await self.client.request("OPTIONS", "/api/telegram/status", headers=headers)
        self.assertEqual(resp.status, 204)
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "https://misa.up.railway.app")
        self.assertIn("GET", resp.headers.get("Access-Control-Allow-Methods", ""))
        self.assertIn("Authorization", resp.headers.get("Access-Control-Allow-Headers", ""))

    @unittest_run_loop
    async def test_telegram_status_allowed_in_production(self):
        headers = {
            "Origin": "https://misa.up.railway.app",
        }
        resp = await self.client.request("GET", "/api/telegram/status", headers=headers)
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "https://misa.up.railway.app")


class TestResolveAuthIdentityProduction(unittest.TestCase):
    """Test identity resolution, token validation, and cross-tenant protection."""

    def setUp(self):
        self._orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_legacy_admin_param_mapped_to_authenticated_user(self):
        fake_user = MagicMock()
        fake_user.id = "44444444-4444-4444-4444-444444444444"
        fake_session = MagicMock()

        req = MagicMock()
        req.headers = {
            "Authorization": "Bearer fake-token-123",
            "X-Misa-User-Id": "admin"
        }
        req.query = {"misa_user_id": "admin"}

        with patch("core.v8.AccountAuthManager.get_default_instance") as mock_auth_cls:
            mock_mgr = MagicMock()
            mock_mgr.authenticate_token.return_value = (fake_session, fake_user)
            mock_auth_cls.return_value = mock_mgr

            user_id, user, session, err = resolve_auth_identity(req, required=True)
            self.assertIsNone(err)
            self.assertEqual(user_id, "44444444-4444-4444-4444-444444444444")

    def test_cross_tenant_foreign_uuid_rejected(self):
        fake_user = MagicMock()
        fake_user.id = "44444444-4444-4444-4444-444444444444"
        fake_session = MagicMock()

        req = MagicMock()
        req.headers = {
            "Authorization": "Bearer fake-token-123",
            "X-Misa-User-Id": "99999999-9999-9999-9999-999999999999"
        }
        req.query = {}

        with patch("core.v8.AccountAuthManager.get_default_instance") as mock_auth_cls:
            mock_mgr = MagicMock()
            mock_mgr.authenticate_token.return_value = (fake_session, fake_user)
            mock_auth_cls.return_value = mock_mgr

            user_id, user, session, err = resolve_auth_identity(req, required=True)
            self.assertIsNotNone(err)
            self.assertEqual(err.status, 403)

    def test_missing_token_when_auth_enforced_returns_401(self):
        os.environ["MISA_REQUIRE_AUTH"] = "true"
        req = MagicMock()
        req.headers = {}
        req.query = {}

        with patch("core.v8.AccountAuthManager.get_default_instance") as mock_auth_cls:
            mock_mgr = MagicMock()
            mock_mgr.is_configured.return_value = True
            mock_auth_cls.return_value = mock_mgr

            user_id, user, session, err = resolve_auth_identity(req, required=True)
            self.assertIsNotNone(err)
            self.assertEqual(err.status, 401)


class TestTelegramIdentitySupabaseSync(unittest.TestCase):
    """Test Supabase persistence synchronization for TelegramIdentityManager."""

    def setUp(self):
        self._orig_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)
        TelegramIdentityManager._default_instance = None

    def test_supabase_config_parsing(self):
        os.environ["SUPABASE_URL"] = "https://vdcssmzguxfknqkfxbed.supabase.co/"
        os.environ["SUPABASE_PUBLISHABLE_KEY"] = "sb_publishable_test"
        os.environ["SUPABASE_SECRET_KEY"] = "sb_secret_test"

        mgr = TelegramIdentityManager.get_default_instance()
        url, anon, secret = mgr._get_supabase_config()
        self.assertEqual(url, "https://vdcssmzguxfknqkfxbed.supabase.co")
        self.assertEqual(anon, "sb_publishable_test")
        self.assertEqual(secret, "sb_secret_test")

    def test_sync_link_to_supabase_with_uuid(self):
        os.environ["SUPABASE_URL"] = "https://example.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "test-secret"

        mgr = TelegramIdentityManager.get_default_instance()
        test_uuid = "12345678-1234-5678-1234-567812345678"
        link = UserTelegramLink(
            misa_user_id=test_uuid,
            telegram_user_id=123456789,
            metadata={"username": "testuser", "first_name": "Test"}
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 201
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            mgr.sync_link_to_supabase(link)
            self.assertTrue(mock_urlopen.called)

    def test_delete_link_from_supabase(self):
        os.environ["SUPABASE_URL"] = "https://example.supabase.co"
        os.environ["SUPABASE_SECRET_KEY"] = "test-secret"

        mgr = TelegramIdentityManager.get_default_instance()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 204
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            mgr.delete_link_from_supabase(123456789)
            self.assertTrue(mock_urlopen.called)


class TestGoogleOAuthRedirectAndSecurity(AioHTTPTestCase):
    """Tests for Google OAuth redirect chain, environment separation, state validation, and token security."""

    async def get_application(self):
        self._orig_env = dict(os.environ)
        os.environ.pop("RAILWAY_ENVIRONMENT", None)
        os.environ.pop("RAILWAY_PROJECT_ID", None)
        os.environ.pop("MISA_ENV", None)
        os.environ["ENVIRONMENT"] = "production"
        os.environ["MISA_ALLOW_REMOTE_API"] = "true"
        return create_app()

    def tearDown(self):
        super().tearDown()
        if hasattr(self, "_orig_env"):
            os.environ.clear()
            os.environ.update(self._orig_env)

    @unittest_run_loop
    async def test_oauth_callback_html_scrubs_tokens_and_sets_no_store_headers(self):
        resp = await self.client.request("GET", "/api/auth/callback?state=test_state_123")
        self.assertEqual(resp.status, 200)
        self.assertIn("no-store", resp.headers.get("Cache-Control", ""))
        self.assertEqual(resp.headers.get("Referrer-Policy"), "no-referrer")
        text = await resp.text()
        self.assertIn("window.history.replaceState", text)
        self.assertIn("/api/auth/callback/session", text)
        self.assertNotIn("localhost:140", text)

    @unittest_run_loop
    async def test_oauth_session_save_and_one_time_retrieve(self):
        state = "oauth_state_valid_987654"
        save_resp = await self.client.request(
            "POST",
            "/api/auth/callback/session",
            json={
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20ifQ.sig123",
                "refresh_token": "refresh_tok_abc",
                "state": state,
            },
        )
        self.assertEqual(save_resp.status, 200)
        self.assertIn("no-store", save_resp.headers.get("Cache-Control", ""))
        save_data = await save_resp.json()
        self.assertTrue(save_data.get("ok"))
        self.assertEqual(save_data.get("state"), state)

        # Wrong state must NOT retrieve the session
        wrong_resp = await self.client.request("GET", "/api/auth/callback/session?state=wrong_state_000")
        self.assertEqual(wrong_resp.status, 404)

        # Omitted state must NOT leak a state-bound session
        no_state_resp = await self.client.request("GET", "/api/auth/callback/session")
        self.assertEqual(no_state_resp.status, 404)

        # Correct state retrieves the session once
        get_resp = await self.client.request("GET", f"/api/auth/callback/session?state={state}")
        self.assertEqual(get_resp.status, 200)
        get_data = await get_resp.json()
        self.assertTrue(get_data.get("ok"))
        self.assertEqual(get_data["session"]["refresh_token"], "refresh_tok_abc")

        # Second request with the same state must be rejected (one-time session)
        replay_resp = await self.client.request("GET", f"/api/auth/callback/session?state={state}")
        self.assertEqual(replay_resp.status, 404)

    @unittest_run_loop
    async def test_oauth_pending_state_returns_200_pending(self):
        """Pre-registered state while waiting for browser returns 200 with status pending (not 404)."""
        pending_state = "oauth_pending_state_12345"
        init_resp = await self.client.request(
            "POST",
            "/api/auth/callback/session",
            json={"state": pending_state, "action": "init"},
        )
        self.assertEqual(init_resp.status, 200)

        # Polling while pending must return 200 OK with status="pending", NOT 404
        poll_resp = await self.client.request(
            "GET",
            f"/api/auth/callback/session?state={pending_state}",
            headers={"Accept": "application/json"},
        )
        self.assertEqual(poll_resp.status, 200)
        poll_data = await poll_resp.json()
        self.assertFalse(poll_data.get("ok"))
        self.assertEqual(poll_data.get("status"), "pending")
        self.assertIsNone(poll_data.get("session"))

    @unittest_run_loop
    async def test_oauth_html_accept_serves_landing_page(self):
        """Browser redirect to /api/auth/callback/session with Accept: text/html serves landing page."""
        html_resp = await self.client.request(
            "GET",
            "/api/auth/callback/session?state=test_state_html",
            headers={"Accept": "text/html,application/xhtml+xml"},
        )
        self.assertEqual(html_resp.status, 200)
        self.assertIn("text/html", html_resp.headers.get("Content-Type", ""))
        body = await html_resp.text()
        self.assertIn("Misa AI", body)
        self.assertIn("/api/auth/callback/session", body)

    @unittest_run_loop
    async def test_oauth_invalid_or_expired_state_rejected(self):
        from core.api_server import _pending_oauth_sessions, _pending_oauth_lock

        # 1. Invalid state characters rejected with 400 on POST
        bad_post = await self.client.request(
            "POST",
            "/api/auth/callback/session",
            json={"access_token": "tok_123", "state": "bad state <script>alert(1)</script>"},
        )
        self.assertEqual(bad_post.status, 400)

        # 2. Invalid state characters rejected with 400 on GET
        bad_get = await self.client.request(
            "GET",
            "/api/auth/callback/session?state=invalid%20state%20with%20spaces",
        )
        self.assertEqual(bad_get.status, 400)

        # 3. Empty token/code payload rejected with 400
        empty_post = await self.client.request(
            "POST",
            "/api/auth/callback/session",
            json={"state": "valid_state_empty"},
        )
        self.assertEqual(empty_post.status, 400)

        # 4. Expired state rejected with 404
        expired_state = "expired_state_111"
        with _pending_oauth_lock:
            _pending_oauth_sessions[expired_state] = (time.time() - 10.0, {"access_token": "tok_exp"})

        exp_get = await self.client.request("GET", f"/api/auth/callback/session?state={expired_state}")
        self.assertEqual(exp_get.status, 404)

    @unittest_run_loop
    async def test_oauth_tokens_never_leaked_in_errors_or_audit_logs(self):
        from core.api_server import _redact_oauth_secrets
        from core.v8.events import RemoteAuditLogger

        raw = "Failed at http://localhost:140/#access_token=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcde&refresh_token=sec_ref_99"
        redacted = _redact_oauth_secrets(raw)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", redacted)
        self.assertNotIn("sec_ref_99", redacted)
        self.assertIn("[REDACTED]", redacted)

        # Save an OAuth error containing a token and verify GET redacts it
        err_state = "err_state_test_555"
        await self.client.request(
            "POST",
            "/api/auth/callback/session",
            json={
                "state": err_state,
                "error": "access_denied: access_token=leaked_tok_999",
            },
        )
        err_get = await self.client.request("GET", f"/api/auth/callback/session?state={err_state}")
        self.assertEqual(err_get.status, 400)
        err_body = await err_get.text()
        self.assertNotIn("leaked_tok_999", err_body)

        # Verify audit log does not contain tokens
        audit_events = [e.to_dict() for e in RemoteAuditLogger.get_instance().get_history(limit=10)]
        serialized_audit = json.dumps(audit_events)
        self.assertNotIn("leaked_tok_999", serialized_audit)
        self.assertNotIn("refresh_tok_abc", serialized_audit)

    def test_frontend_environment_separation_blocks_localhost_140_and_preserves_tauri(self):
        backend_service_path = os.path.join(
            BASE_DIR, "Misa", "src", "services", "backendService.ts"
        )
        with open(backend_service_path, "r", encoding="utf-8") as f:
            ts_code = f.read()

        # Verify required functions and protections exist in backendService.ts
        self.assertIn("FORBIDDEN_FRONTEND_PORTS = new Set([\"140\", \"1420\", \"1421\", \"5173\"])", ts_code)
        self.assertIn("export function isTauriRuntime", ts_code)
        self.assertIn("__TAURI_INTERNALS__", ts_code)
        self.assertIn("tauri.localhost", ts_code)
        self.assertIn("export function isProductionWebRuntime", ts_code)
        self.assertIn("export function resolveOAuthCallbackBase", ts_code)
        self.assertIn("export function resolveOAuthRedirectUrl", ts_code)
        self.assertIn("export function scrubUrlOAuthTokens", ts_code)
        self.assertIn("export function redactSensitiveTokens", ts_code)


class TestTelegramOTPCompleteAuditSuite(AioHTTPTestCase):
    """Comprehensive 14-point audit & regression suite for Telegram OTP linking, Supabase sync, and security."""

    def setUp(self):
        self._orig_env = dict(os.environ)
        super().setUp()

    async def get_application(self):
        import tempfile
        self._temp_dir = tempfile.mkdtemp(prefix="misa_tg_audit_")
        self._storage_path = os.path.join(self._temp_dir, "tg_links.json")
        os.environ["ENVIRONMENT"] = "production"
        os.environ["MISA_ALLOW_REMOTE_API"] = "true"
        os.environ["TELEGRAM_BOT_USERNAME"] = "Misa_ai_agent_bot"
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
        os.environ.pop("SUPABASE_ANON_KEY", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        TelegramIdentityManager._default_instance = TelegramIdentityManager(storage_path=self._storage_path)
        return create_app()

    def tearDown(self):
        import shutil
        TelegramIdentityManager._default_instance = None
        if hasattr(self, "_temp_dir"):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        super().tearDown()
        os.environ.clear()
        os.environ.update(self._orig_env)

    @unittest_run_loop
    async def test_01_bot_username_consistency_across_backend_and_frontend(self):
        """Bot username must be Misa_ai_agent_bot across API, Bot, IdentityManager, and Frontend."""
        status_resp = await self.client.request("GET", "/api/telegram/status")
        self.assertEqual(status_resp.status, 200)
        status_data = await status_resp.json()
        self.assertEqual(status_data.get("bot_username"), "Misa_ai_agent_bot")

        mgr = TelegramIdentityManager.get_default_instance()
        req, otp, deep_link, err = mgr.create_link_request("11111111-1111-4111-8111-111111111111")
        self.assertIsNone(err)
        self.assertTrue(deep_link.startswith("https://t.me/Misa_ai_agent_bot?start="))

        tg_page_path = os.path.join(BASE_DIR, "Misa", "src", "pages", "TelegramIntegrationPage.tsx")
        with open(tg_page_path, "r", encoding="utf-8") as f:
            tg_page_code = f.read()
        self.assertIn("Misa_ai_agent_bot", tg_page_code)
        self.assertNotIn("MisaUniversalBot", tg_page_code)

        bs_path = os.path.join(BASE_DIR, "Misa", "src", "services", "backendService.ts")
        with open(bs_path, "r", encoding="utf-8") as f:
            bs_code = f.read()
        self.assertIn("Misa_ai_agent_bot", bs_code)
        self.assertNotIn("MisaUniversalBot", bs_code)

    @unittest_run_loop
    async def test_02_bot_otp_formats_and_command_variants(self):
        """Test plain 6-digit OTP, spaced OTP, /link <otp>, /link@Misa_ai_agent_bot <otp>, and /start <token>."""
        from core.v8.telegram_gateway import MockTelegramTransport
        from core.v8.universal_bot import UniversalTelegramBot

        mgr = TelegramIdentityManager.get_default_instance()
        transport = MockTelegramTransport()
        bot = UniversalTelegramBot(transport=transport, identity_manager=mgr)
        self.assertEqual(bot.bot_username, "Misa_ai_agent_bot")

        # 1. Plain 6-digit OTP with space ("123 456")
        req1, otp1, _, _ = mgr.create_link_request("user_fmt_1")
        spaced_otp = f"{otp1[:3]} {otp1[3:]}"
        await bot.process_update({
            "message": {
                "message_id": 1,
                "chat": {"id": 910001},
                "from": {"id": 910001, "first_name": "Umid", "username": "umid_uz"},
                "text": spaced_otp,
            }
        })
        self.assertIn("muvaffaqiyatli bog'landi", transport.sent_messages[-1]["text"])
        self.assertNotIn("Tasdiqlash kodi talab qilinadi", transport.sent_messages[-1]["text"])

        # 2. /link@Misa_ai_agent_bot <otp>
        req2, otp2, _, _ = mgr.create_link_request("user_fmt_2")
        await bot.process_update({
            "message": {
                "message_id": 2,
                "chat": {"id": 910002},
                "from": {"id": 910002, "first_name": "Dilshod"},
                "text": f"/link@Misa_ai_agent_bot <{otp2}>",
            }
        })
        self.assertIn("muvaffaqiyatli bog'landi", transport.sent_messages[-1]["text"])

        # 3. /start@Misa_ai_agent_bot <link_token>
        req3, _, _, _ = mgr.create_link_request("user_fmt_3")
        await bot.process_update({
            "message": {
                "message_id": 3,
                "chat": {"id": 910003},
                "from": {"id": 910003, "first_name": "Kamola"},
                "text": f"/start@Misa_ai_agent_bot {req3.link_token}",
            }
        })
        self.assertIn("Tabriklaymiz", transport.sent_messages[-1]["text"])

        # 4. Reject bot sender (from.is_bot = True)
        msg_count_before = len(transport.sent_messages)
        res_bot = await bot.process_update({
            "message": {
                "message_id": 4,
                "chat": {"id": 910004},
                "from": {"id": 910004, "is_bot": True, "first_name": "SpamBot"},
                "text": "/start",
            }
        })
        self.assertIsNone(res_bot)
        self.assertEqual(len(transport.sent_messages), msg_count_before)

    @unittest_run_loop
    async def test_03_distributed_desktop_to_railway_supabase_otp_sync_e2e(self):
        """
        Simulate Desktop App (Instance A) creating OTP -> syncing to Supabase device_pairing_sessions ->
        Railway Webhook Bot (Instance B) loading from Supabase & verifying OTP ->
        Desktop App (Instance A) polling status and seeing VERIFIED & CONNECTED.
        """
        from core.v8.telegram_gateway import MockTelegramTransport
        from core.v8.universal_bot import UniversalTelegramBot

        os.environ["SUPABASE_URL"] = "https://vdcssmzguxfknqkfxbed.supabase.co"
        os.environ["SUPABASE_PUBLISHABLE_KEY"] = "sb_pub_test"
        os.environ["SUPABASE_SECRET_KEY"] = "sb_sec_test"

        # Simulated Supabase tables in memory
        supabase_pairing_table = {}
        supabase_links_table = {}

        def fake_urlopen(http_req, timeout=5.0):
            url = http_req.full_url
            method = http_req.get_method()
            body_raw = http_req.data.decode("utf-8") if http_req.data else ""

            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp

            if "device_pairing_sessions" in url:
                if method == "POST":
                    row = json.loads(body_raw)
                    # Verify plaintext OTP is NEVER in Supabase payload
                    self.assertNotIn("otp", row)
                    self.assertIn("pairing_code_hash", row)
                    supabase_pairing_table[row["id"]] = row
                    mock_resp.status = 201
                    mock_resp.read.return_value = b"[]"
                    return mock_resp
                elif method == "GET":
                    rows = list(supabase_pairing_table.values())
                    mock_resp.status = 200
                    mock_resp.read.return_value = json.dumps(rows).encode("utf-8")
                    return mock_resp

            if "telegram_links" in url:
                if method == "POST":
                    row = json.loads(body_raw)
                    supabase_links_table[int(row["telegram_user_id"])] = row
                    mock_resp.status = 201
                    mock_resp.read.return_value = b"[]"
                    return mock_resp
                elif method == "GET":
                    rows = list(supabase_links_table.values())
                    mock_resp.status = 200
                    mock_resp.read.return_value = json.dumps(rows).encode("utf-8")
                    return mock_resp
                elif method == "DELETE":
                    supabase_links_table.clear()
                    mock_resp.status = 204
                    mock_resp.read.return_value = b""
                    return mock_resp

            mock_resp.status = 200
            mock_resp.read.return_value = b"[]"
            return mock_resp

        user_uuid = "22222222-2222-4222-8222-222222222222"
        desktop_file = os.path.join(self._temp_dir, "desktop_links.json")
        railway_file = os.path.join(self._temp_dir, "railway_links.json")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            desktop_mgr = TelegramIdentityManager(storage_path=desktop_file, auto_load_supabase=True)
            railway_mgr = TelegramIdentityManager(storage_path=railway_file, auto_load_supabase=True)

            # Step 1: Desktop App generates OTP
            req, plaintext_otp, deep_link, err = desktop_mgr.create_link_request(
                misa_user_id=user_uuid,
                auth_token="user_jwt_token"
            )
            self.assertIsNone(err)
            self.assertIn(req.request_id, supabase_pairing_table)
            # Plaintext OTP must never be in the Supabase row
            self.assertNotIn(plaintext_otp, json.dumps(supabase_pairing_table))

            # Step 2: User sends OTP to Telegram Bot running on Railway (which has separate local storage!)
            transport = MockTelegramTransport()
            railway_bot = UniversalTelegramBot(transport=transport, identity_manager=railway_mgr)
            await railway_bot.process_update({
                "message": {
                    "message_id": 55,
                    "chat": {"id": 777888999},
                    "from": {"id": 777888999, "first_name": "Sardor", "username": "sardor_tg"},
                    "text": plaintext_otp,
                }
            })
            self.assertIn("Hisob muvaffaqiyatli bog'landi", transport.sent_messages[-1]["text"])
            self.assertEqual(supabase_pairing_table[req.request_id]["status"], "VERIFIED")
            self.assertIn(777888999, supabase_links_table)

            # Step 3: Desktop App polls status from its own manager (refreshed from Supabase)
            refreshed_req = desktop_mgr.get_request(req.request_id, auth_token="user_jwt_token", refresh=True)
            self.assertIsNotNone(refreshed_req)
            self.assertEqual(refreshed_req.status, "VERIFIED")

            desktop_link = desktop_mgr.get_link_by_misa_user(user_uuid, auth_token="user_jwt_token", refresh=True)
            self.assertIsNotNone(desktop_link)
            self.assertEqual(desktop_link.telegram_user_id, 777888999)

    @unittest_run_loop
    async def test_04_cross_user_otp_abuse_and_idor_protection(self):
        """User B cannot verify User A's OTP or inspect User A's request_id status (403 Forbidden)."""
        mgr = TelegramIdentityManager.get_default_instance()
        user_a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        user_b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

        req_a, otp_a, _, err = mgr.create_link_request(user_a)
        self.assertIsNone(err)

        # 1. Direct manager check: User B trying to verify User A's OTP
        ok_cross, msg_cross, _ = mgr.verify_otp(
            otp=otp_a,
            telegram_user_id=500001,
            expected_misa_user_id=user_b
        )
        self.assertFalse(ok_cross)
        self.assertIn("USER_MISMATCH", msg_cross)

        fake_user_b = MagicMock()
        fake_user_b.id = user_b
        fake_session_b = MagicMock()

        with patch("core.v8.AccountAuthManager.get_default_instance") as mock_auth_cls:
            mock_auth_mgr = MagicMock()
            mock_auth_mgr.authenticate_token.return_value = (fake_session_b, fake_user_b)
            mock_auth_cls.return_value = mock_auth_mgr

            # 2. API check: Authenticated User B calling GET /api/telegram/link/status?request_id=<User A's request_id>
            status_resp = await self.client.request(
                "GET",
                f"/api/telegram/link/status?request_id={req_a.request_id}",
                headers={"Authorization": "Bearer user_b_token"}
            )
            self.assertEqual(status_resp.status, 403)

            # 3. API check: Authenticated User B calling POST /api/telegram/link/verify with User A's OTP
            verify_resp = await self.client.request(
                "POST",
                "/api/telegram/link/verify",
                json={"otp": otp_a, "telegram_user_id": 500001, "request_id": req_a.request_id},
                headers={"Authorization": "Bearer user_b_token"}
            )
            self.assertEqual(verify_resp.status, 403)

        # 4. Already-linked Telegram user trying to redeem another user's OTP
        ok_a, _, _ = mgr.verify_otp(otp=otp_a, telegram_user_id=500001, expected_misa_user_id=user_a)
        self.assertTrue(ok_a)

        req_b, otp_b, _, _ = mgr.create_link_request(user_b)
        ok_hijack, msg_hijack, _ = mgr.verify_otp(otp=otp_b, telegram_user_id=500001)
        self.assertFalse(ok_hijack)
        self.assertIn("TELEGRAM_ALREADY_LINKED", msg_hijack)

        # 5. Expected Telegram ID mismatch
        req_bound, otp_bound, _, _ = mgr.create_link_request("user_bound", expected_telegram_user_id=600001)
        ok_wrong_tg, msg_wrong_tg, _ = mgr.verify_otp(otp=otp_bound, telegram_user_id=600002)
        self.assertFalse(ok_wrong_tg)
        self.assertIn("TELEGRAM_USER_MISMATCH", msg_wrong_tg)


class TestRailwayLinuxAndWebhookOTPReadiness(AioHTTPTestCase):
    """
    10-point regression suite verifying:
    1. Linux import safety when 'winreg' is unavailable
    2. Headless/Railway mode skipping 'main.py' without logging 'No module named main'
    3. Webhook update parsing & awaiting bot handler completion before HTTP 200
    4. Telegram sendMessage error logging & Markdown plain-text fallback without leaking bot token
    5. Invalid, expired, and reused OTP rejection
    6. Valid OTP linking misa_user_id <-> telegram_user_id (including transient JWT Supabase sync)
    7. Cross-user OTP verification rejection
    8. Missing/invalid JWT returning 401 on protected endpoints
    9. Frontend backendService.ts sending Authorization: Bearer header
    10. Linked state persistence across manager restart & /ready endpoint diagnostics
    """

    def setUp(self):
        self._orig_env = dict(os.environ)
        super().setUp()

    async def get_application(self):
        import tempfile
        self._temp_dir = tempfile.mkdtemp(prefix="misa_railway_diag_")
        self._storage_path = os.path.join(self._temp_dir, "tg_links_diag.json")
        os.environ["ENVIRONMENT"] = "production"
        os.environ["MISA_ALLOW_REMOTE_API"] = "true"
        os.environ["TELEGRAM_BOT_TOKEN"] = "123456789:AAFakeSecretTokenForTestingOnly999"
        os.environ["TELEGRAM_WEBHOOK_SECRET"] = "railway_webhook_secret_xyz"
        os.environ["TELEGRAM_BOT_USERNAME"] = "Misa_ai_agent_bot"
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_PUBLISHABLE_KEY", None)
        os.environ.pop("SUPABASE_ANON_KEY", None)
        os.environ.pop("SUPABASE_SECRET_KEY", None)
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        TelegramIdentityManager._default_instance = TelegramIdentityManager(storage_path=self._storage_path)
        return create_app()

    def tearDown(self):
        import shutil
        TelegramIdentityManager._default_instance = None
        if hasattr(self, "_temp_dir"):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        super().tearDown()
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_01_linux_mode_command_dispatcher_imports_without_winreg(self):
        """1. Linux rejimida (winreg yo'q bo'lganda) command_dispatcher va backend xatosiz import bo'lishi."""
        import importlib
        import core.command_dispatcher as cd_mod

        orig_winreg = sys.modules.get("winreg")
        try:
            sys.modules["winreg"] = None  # Simulate Linux where import winreg raises ModuleNotFoundError
            reloaded = importlib.reload(cd_mod)
            self.assertFalse(reloaded.WINREG_AVAILABLE)
            self.assertIsNone(reloaded.winreg)
            dispatcher = reloaded.CommandDispatcher()
            gpus = reloaded.get_system_gpus()
            self.assertIsInstance(gpus, list)
            specs = reloaded.get_system_specs_summary()
            self.assertIsInstance(specs, str)
            self.assertIsNotNone(dispatcher)
        finally:
            if orig_winreg is not None:
                sys.modules["winreg"] = orig_winreg
            else:
                sys.modules.pop("winreg", None)
            importlib.reload(cd_mod)

    def test_02_headless_server_mode_skips_main_without_error_log(self):
        """2. main moduli bo'lmaganda server qulamasligi va 'No module named main' xatosi logga chiqmasligi."""
        import core.api_server as api_srv

        orig_main = api_srv._main
        orig_attempted = api_srv._main_load_attempted
        try:
            api_srv._main = None
            api_srv._main_load_attempted = False
            os.environ["RAILWAY_ENVIRONMENT"] = "production"

            with patch.object(api_srv.logger, "error") as mock_err:
                res = api_srv.get_modules()
                self.assertEqual(len(res), 6)
                for call in mock_err.call_args_list:
                    logged_msg = str(call.args[0]) if call.args else ""
                    self.assertNotIn("No module named 'main'", logged_msg)
                    self.assertNotIn("No module named 'winreg'", logged_msg)
        finally:
            api_srv._main = orig_main
            api_srv._main_load_attempted = orig_attempted

    @unittest_run_loop
    async def test_03_webhook_update_invokes_bot_handler_synchronously_before_200(self):
        """3. Telegram webhook update kelganda handler chaqirilishi va javob yuborilishi."""
        from unittest.mock import AsyncMock
        from core.v8.telegram_gateway import MockTelegramTransport
        from core.v8.universal_bot import UniversalTelegramBot
        from core.v8.telegram_webhook import TelegramWebhookService

        mgr = TelegramIdentityManager.get_default_instance()
        req, otp, _, _ = mgr.create_link_request("user_webhook_sync")

        transport = MockTelegramTransport()
        bot = UniversalTelegramBot(transport=transport, identity_manager=mgr)
        svc = TelegramWebhookService(
            bot=bot,
            webhook_secret="railway_webhook_secret_xyz",
            transport=transport,
        )

        mock_request = MagicMock()
        mock_request.match_info = {"secret": "railway_webhook_secret_xyz"}
        mock_request.content_type = "application/json"
        mock_request.headers = {
            "Content-Type": "application/json",
            "X-Telegram-Bot-Api-Secret-Token": "railway_webhook_secret_xyz",
        }
        mock_request.content_length = 250
        update_payload = {
            "update_id": 880011,
            "message": {
                "message_id": 701,
                "chat": {"id": 44556677},
                "from": {"id": 44556677, "first_name": "Jasur", "username": "jasur_dev"},
                "text": f"/link {otp}",
            },
        }
        mock_request.read = AsyncMock(return_value=json.dumps(update_payload).encode("utf-8"))

        resp = await svc.handle_webhook(mock_request)
        self.assertEqual(resp.status, 200)
        # Because handle_webhook awaits the shielded task, send_message has ALREADY completed when 200 returns
        self.assertEqual(len(transport.sent_messages), 1)
        self.assertIn("muvaffaqiyatli bog'landi", transport.sent_messages[0]["text"])
        self.assertEqual(len(svc._active_handlers), 0)
        self.assertIsNotNone(mgr.get_link_by_misa_user("user_webhook_sync"))

    @unittest_run_loop
    async def test_04_aiohttp_transport_send_message_logs_errors_and_redacts_token(self):
        """4. sendMessage chaqiruvi xato holatlari loglanishi, Markdown fallback ishlashi va token sizmasligi."""
        from core.v8.telegram_gateway import AiohttpTelegramTransport

        secret_bot_token = "999888777:AAUltraSecretBotTokenDoNotLeak"
        transport = AiohttpTelegramTransport(bot_token=secret_bot_token)

        calls = []

        class FakeResp:
            def __init__(self, status, payload):
                self.status = status
                self._payload = payload

            async def json(self, content_type=None):
                return self._payload

            async def text(self):
                return json.dumps(self._payload)

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class FakeSession:
            closed = False

            def post(self, url, json=None):
                calls.append((url, dict(json or {})))
                if len(calls) == 1:
                    return FakeResp(
                        400,
                        {
                            "ok": False,
                            "error_code": 400,
                            "description": f"Bad Request: can't parse entities with token {secret_bot_token}",
                        },
                    )
                return FakeResp(200, {"ok": True, "result": {"message_id": 123}})

            async def close(self):
                self.closed = True

        transport._session = FakeSession()
        transport._session_loop = asyncio.get_running_loop()

        with patch("core.v8.telegram_gateway.logger") as mock_logger:
            result = await transport.send_message(chat_id=12345, text="Hello *broken_markdown")
            self.assertTrue(result.get("ok"))
            # First attempt had parse_mode=Markdown, second retried without parse_mode
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][1].get("parse_mode"), "Markdown")
            self.assertNotIn("parse_mode", calls[1][1])
            # Verify token never appeared in warning/error logs
            for call in mock_logger.warning.call_args_list + mock_logger.error.call_args_list:
                log_str = " ".join(str(a) for a in call.args)
                self.assertNotIn(secret_bot_token, log_str)

    def test_05_invalid_expired_and_reused_otp_rejected(self):
        """5. Noto'g'ri, muddati o'tgan va ikkinchi marta ishlatilgan OTP rad etilishi."""
        mgr = TelegramIdentityManager.get_default_instance()
        req, otp, _, err = mgr.create_link_request("user_otp_edge")
        self.assertIsNone(err)

        # Invalid OTP
        ok_bad, msg_bad, _ = mgr.verify_otp("000000", telegram_user_id=70001)
        self.assertFalse(ok_bad)
        self.assertIn("INVALID_OTP", msg_bad)

        # Expired OTP
        req_exp, otp_exp, _, _ = mgr.create_link_request("user_otp_exp", ttl=1)
        req_exp.expires_at = time.time() - 5
        ok_exp, msg_exp, _ = mgr.verify_otp(otp_exp, telegram_user_id=70002)
        self.assertFalse(ok_exp)
        self.assertTrue("EXPIRED" in msg_exp or "INVALID_OTP" in msg_exp)

        # Valid OTP first use succeeds, second use (reuse) fails
        ok_first, _, _ = mgr.verify_otp(otp, telegram_user_id=70003)
        self.assertTrue(ok_first)
        ok_reuse, msg_reuse, _ = mgr.verify_otp(otp, telegram_user_id=70004)
        self.assertFalse(ok_reuse)

    def test_06_valid_otp_links_misa_and_telegram_user_with_transient_jwt_sync(self):
        """6. To'g'ri OTP misa_user_id va telegram_user_id ni bog'lashi (transient JWT bilan Supabase sync)."""
        os.environ["SUPABASE_URL"] = "https://vdcssmzguxfknqkfxbed.supabase.co"
        os.environ["SUPABASE_PUBLISHABLE_KEY"] = "sb_pub_key"
        # Intentionally NO SUPABASE_SECRET_KEY to verify transient user JWT fallback!
        os.environ.pop("SUPABASE_SECRET_KEY", None)
        os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)

        captured_Auth_headers = []

        def fake_urlopen(http_req, timeout=5.0):
            auth_hdr = http_req.get_header("Authorization") or http_req.headers.get("Authorization")
            captured_Auth_headers.append((http_req.full_url, auth_hdr))
            mock_resp = MagicMock()
            mock_resp.__enter__.return_value = mock_resp
            mock_resp.status = 201
            mock_resp.read.return_value = b"[]"
            return mock_resp

        user_uuid = "33333333-3333-4333-8333-333333333333"
        user_jwt = "eyJhbGciOiJIUzI1NiJ9.user_jwt_payload.sig"

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            mgr = TelegramIdentityManager(storage_path=self._storage_path, auto_load_supabase=False)
            req, otp, _, err = mgr.create_link_request(user_uuid, auth_token=user_jwt)
            self.assertIsNone(err)
            # Ensure transient token is never serialized to disk
            self.assertNotIn("_transient_auth_token", req.to_dict())
            with open(self._storage_path, "r", encoding="utf-8") as f:
                self.assertNotIn(user_jwt, f.read())

            # Webhook verifies OTP without passing auth_token directly (uses req._transient_auth_token)
            ok, msg, linked = mgr.verify_otp(otp, telegram_user_id=888999, username="misa_fan")
            self.assertTrue(ok, msg)
            self.assertIsNotNone(linked)
            self.assertEqual(linked.misa_user_id, user_uuid)
            self.assertEqual(linked.telegram_user_id, 888999)
            # Verify Supabase calls used Bearer <user_jwt>
            self.assertTrue(any(h == f"Bearer {user_jwt}" for _, h in captured_Auth_headers))

    @unittest_run_loop
    async def test_07_cross_user_otp_verification_blocked(self):
        """7. Boshqa user OTP'ni tasdiqlay olmasligi."""
        mgr = TelegramIdentityManager.get_default_instance()
        req_owner, otp_owner, _, _ = mgr.create_link_request("owner_user_id")

        ok, msg, _ = mgr.verify_otp(
            otp=otp_owner,
            telegram_user_id=990011,
            expected_misa_user_id="attacker_user_id",
        )
        self.assertFalse(ok)
        self.assertIn("USER_MISMATCH", msg)

    @unittest_run_loop
    async def test_08_missing_or_invalid_token_returns_401(self):
        """8. Token yo'q yoki noto'g'ri bo'lsa 401 qaytishi."""
        os.environ["MISA_REQUIRE_AUTH"] = "true"
        for method, path in [
            ("POST", "/api/telegram/link/start"),
            ("POST", "/api/telegram/link/verify"),
            ("GET", "/api/telegram/link/status"),
            ("GET", "/api/telegram/account"),
            ("POST", "/api/telegram/unlink"),
        ]:
            resp_no_tok = await self.client.request(method, path)
            self.assertEqual(resp_no_tok.status, 401, f"Expected 401 on {method} {path} without token")

            resp_bad_tok = await self.client.request(
                method,
                path,
                headers={"Authorization": "Bearer invalid_expired_or_forged_jwt"},
            )
            self.assertEqual(resp_bad_tok.status, 401, f"Expected 401 on {method} {path} with invalid token")

    def test_09_frontend_sends_authorization_bearer_header(self):
        """9. Frontend Authorization: Bearer yuborishi."""
        bs_path = os.path.join(BASE_DIR, "Misa", "src", "services", "backendService.ts")
        with open(bs_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Authorization", content)
        self.assertIn("Bearer ${token}", content)
        self.assertIn("this.getAuthHeaders()", content)
        for endpoint in [
            "/api/telegram/link/start",
            "/api/telegram/link/verify",
            "/api/telegram/link/status",
            "/api/telegram/account",
            "/api/telegram/unlink",
        ]:
            self.assertIn(endpoint, content)

    @unittest_run_loop
    async def test_10_linked_state_persists_across_reload_and_ready_check(self):
        """10. Bog'langan holat qayta yuklanganda saqlanishi va /ready diagnostikasi."""
        mgr1 = TelegramIdentityManager(storage_path=self._storage_path)
        req, otp, _, _ = mgr1.create_link_request("persistent_user_99")
        ok, _, _ = mgr1.verify_otp(otp, telegram_user_id=55443322, username="persist_uz")
        self.assertTrue(ok)

        # Reload a brand-new manager instance from the same storage path
        mgr2 = TelegramIdentityManager(storage_path=self._storage_path)
        loaded_link = mgr2.get_link_by_misa_user("persistent_user_99")
        self.assertIsNotNone(loaded_link)
        self.assertEqual(loaded_link.telegram_user_id, 55443322)
        self.assertEqual(loaded_link.metadata.get("username"), "persist_uz")

        # Verify /ready endpoint returns 200 and includes platform/supabase/telegram checks
        ready_resp = await self.client.request("GET", "/ready")
        self.assertEqual(ready_resp.status, 200)
        ready_data = await ready_resp.json()
        self.assertEqual(ready_data.get("status"), "ready")
        self.assertIn("checks", ready_data)
        self.assertIn("telegram_bot", ready_data["checks"])
        self.assertIn("platform", ready_data["checks"])
        self.assertIn("supabase", ready_data["checks"])


if __name__ == "__main__":
    unittest.main()



