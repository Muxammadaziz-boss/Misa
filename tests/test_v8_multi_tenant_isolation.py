# ========== tests/test_v8_multi_tenant_isolation.py ==========
# Phase 41 & 42 — Multi-Tenant Isolation & Health Check Test Suite
# Verifies RLS contracts, cross-user security isolation, and /api/health endpoint

import os
import shutil
import tempfile
import unittest
import asyncio
import json
import time

from core.v8.account_device import (
    MisaUser,
    MisaProfile,
    AccountDeviceManager,
)
from core.v8.device_pairing import DevicePairingManager
from core.v8.device_enrollment import (
    MockCredentialStore,
    DeviceEnrollmentManager,
)
from core.v8.device_agent_crypto import DeviceAgentCrypto
from core.v8.device_auth import DeviceAuthManager
from core.api_server import (
    handle_health,
    handle_oauth_callback,
    handle_oauth_session_save,
    handle_oauth_session_get,
)


class MockRequest:
    """Mock aiohttp request for endpoint testing."""
    def __init__(self, method="GET", query=None, headers=None, body=None, match_info=None, remote="127.0.0.1"):
        self.method = method
        self.query = query or {}
        self.headers = headers or {}
        self._body = body or {}
        self.match_info = match_info or {}
        self.remote = remote

    async def json(self):
        return self._body

    async def text(self):
        return json.dumps(self._body)


class TestV8MultiTenantIsolation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="misa_multitenant_test_")
        self.pairing_storage = os.path.join(self.temp_dir, "pairing.json")
        self.device_storage = os.path.join(self.temp_dir, "devices.json")
        self.cred_storage = os.path.join(self.temp_dir, "credentials.json")

        self.device_mgr = AccountDeviceManager(storage_path=self.device_storage)
        self.pairing_mgr = DevicePairingManager(storage_path=self.pairing_storage)
        self.enrollment_mgr = DeviceEnrollmentManager(
            account_device_mgr=self.device_mgr,
            storage_path=self.cred_storage
        )
        self.device_auth_mgr = DeviceAuthManager(enrollment_mgr=self.enrollment_mgr)

        AccountDeviceManager._default_instance = self.device_mgr
        DevicePairingManager._default_instance = self.pairing_mgr
        DeviceEnrollmentManager._default_instance = self.enrollment_mgr
        DeviceAuthManager._default_instance = self.device_auth_mgr

        # Create two separate users
        self.user_a = self.device_mgr.register_or_get_user(
            user_id="user-tenant-a-uuid",
            username="tenant_a"
        )
        self.user_b = self.device_mgr.register_or_get_user(
            user_id="user-tenant-b-uuid",
            username="tenant_b"
        )

    def tearDown(self):
        AccountDeviceManager._default_instance = None
        DevicePairingManager._default_instance = None
        DeviceEnrollmentManager._default_instance = None
        DeviceAuthManager._default_instance = None
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_endpoint_schema_and_status(self):
        """1. GET /api/health schema and status test"""
        req = MockRequest(method="GET")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resp = loop.run_until_complete(handle_health(req))
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.text)
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data.get("app"), "Misa AI")
            self.assertIn(data.get("version"), ["9.0.0", "9.0.1", "9.0.2", "9.2", "9.2.0", "9.3.0"])
            self.assertIn(data.get("supabase"), ["configured", "not_configured"])
            self.assertIn("environment", data)
            self.assertIn("timestamp", data)
        finally:
            loop.close()

    def test_health_endpoint_zero_secret_leaks(self):
        """2. Ensure /api/health NEVER leaks service role key or JWT secrets"""
        old_sr = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        old_jwt = os.environ.get("SUPABASE_JWT_SECRET")
        try:
            os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "super-secret-service-role-key-999"
            os.environ["SUPABASE_JWT_SECRET"] = "super-secret-jwt-secret-888"

            req = MockRequest(method="GET")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                resp = loop.run_until_complete(handle_health(req))
                body_str = resp.text
                self.assertNotIn("super-secret-service-role-key-999", body_str)
                self.assertNotIn("super-secret-jwt-secret-888", body_str)
                self.assertNotIn("service_role", body_str.lower())
                self.assertNotIn("jwt_secret", body_str.lower())
            finally:
                loop.close()
        finally:
            if old_sr is not None:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = old_sr
            else:
                os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            if old_jwt is not None:
                os.environ["SUPABASE_JWT_SECRET"] = old_jwt
            else:
                os.environ.pop("SUPABASE_JWT_SECRET", None)

    def test_oauth_callback_html_serving(self):
        """3. GET /api/auth/callback serves HTML callback page with token parsing logic"""
        req = MockRequest(method="GET")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            resp = loop.run_until_complete(handle_oauth_callback(req))
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.content_type, "text/html")
            self.assertIn("Misa AI", resp.text)
            self.assertIn("access_token", resp.text)
            self.assertIn("/api/auth/callback/session", resp.text)
        finally:
            loop.close()

    def test_oauth_session_save_and_retrieve(self):
        """4. Verify OAuth token exchange between browser callback and desktop app"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # 1. Browser posts tokens
            post_req = MockRequest(
                method="POST",
                body={"access_token": "fake-oauth-access-token-123", "refresh_token": "fake-refresh-456"}
            )
            save_resp = loop.run_until_complete(handle_oauth_session_save(post_req))
            self.assertEqual(save_resp.status, 200)
            data = json.loads(save_resp.text)
            self.assertTrue(data.get("ok"))

            # 2. Desktop app retrieves tokens (one-time consume)
            get_req = MockRequest(method="GET")
            get_resp = loop.run_until_complete(handle_oauth_session_get(get_req))
            self.assertEqual(get_resp.status, 200)
            get_data = json.loads(get_resp.text)
            self.assertTrue(get_data.get("ok"))
            self.assertEqual(get_data.get("session", {}).get("access_token"), "fake-oauth-access-token-123")

            # 3. Next call should return None (already consumed)
            next_resp = loop.run_until_complete(handle_oauth_session_get(get_req))
            next_data = json.loads(next_resp.text)
            self.assertFalse(next_data.get("ok"))
            self.assertIsNone(next_data.get("session"))
        finally:
            loop.close()

    def test_cross_tenant_device_isolation(self):
        """5. User A device cannot be accessed, renamed, or modified by User B"""
        dev_a = self.device_mgr.register_device(
            user_id=self.user_a.id,
            device_id="PC-AGENT-A1",
            name="Alice Work PC",
            hostname="ALICE-DESKTOP",
            platform="windows"
        )
        self.assertIsNotNone(dev_a)

        # User A can see their device
        devs_a = self.device_mgr.get_devices_for_user(self.user_a.id)
        self.assertEqual(len(devs_a), 1)
        self.assertEqual(devs_a[0].device_id, "PC-AGENT-A1")

        # User B cannot see User A's device
        devs_b = self.device_mgr.get_devices_for_user(self.user_b.id)
        self.assertEqual(len(devs_b), 0)

        # User B cannot get User A's device directly
        dev_b_lookup = self.device_mgr.get_device("PC-AGENT-A1", user_id=self.user_b.id)
        self.assertIsNone(dev_b_lookup)

        # User B cannot rename User A's device
        ok_rename, msg_rename, renamed = self.device_mgr.rename_device(
            device_id_or_uuid="PC-AGENT-A1",
            user_id=self.user_b.id,
            new_name="Hacked Name"
        )
        self.assertFalse(ok_rename)
        self.assertIsNone(renamed)
        # Verify original name intact
        intact_dev = self.device_mgr.get_device("PC-AGENT-A1", user_id=self.user_a.id)
        self.assertEqual(intact_dev.name, "Alice Work PC")

    def test_cross_tenant_device_revocation_denied(self):
        """4. User B cannot revoke User A's device"""
        dev_a = self.device_mgr.register_device(
            user_id=self.user_a.id,
            device_id="PC-AGENT-A2",
            name="Alice Laptop",
            hostname="ALICE-LAPTOP",
            platform="windows"
        )
        # Attempt revocation by User B
        ok_revoke, msg_revoke = self.device_mgr.revoke_device(
            device_id_or_uuid="PC-AGENT-A2",
            user_id=self.user_b.id
        )
        self.assertFalse(ok_revoke)

        # Device remains active for User A
        dev_check = self.device_mgr.get_device("PC-AGENT-A2", user_id=self.user_a.id)
        self.assertFalse(dev_check.is_revoked)

    def test_cross_tenant_pairing_session_hijacking_prevented(self):
        """5. User B cannot verify, complete or cancel User A's pairing session"""
        sess, raw_code = self.pairing_mgr.start_pairing(user_id=self.user_a.id)
        self.assertIsNotNone(sess)
        self.assertEqual(sess.user_id, self.user_a.id)

        # User B tries to verify User A's pairing code
        ok, msg, _ = self.pairing_mgr.verify_code(
            pairing_id=sess.id,
            code=raw_code,
            user_id=self.user_b.id
        )
        self.assertFalse(ok)
        self.assertIn("UNAUTHORIZED", msg)

        # User B cannot cancel User A's pairing session
        ok_cancel, msg_cancel = self.pairing_mgr.cancel_pairing(sess.id, user_id=self.user_b.id)
        self.assertFalse(ok_cancel)
        self.assertIn("UNAUTHORIZED", msg_cancel)

    def test_cross_tenant_device_crypto_credential_isolation(self):
        """6. User B cannot view or revoke User A's cryptographic credentials"""
        mock_store = MockCredentialStore()
        agent_crypto = DeviceAgentCrypto(device_id="SECURE-PC-A", credential_store=mock_store)

        ok, msg, cred, dev = self.enrollment_mgr.enroll_device(
            user_id=self.user_a.id,
            device_id="SECURE-PC-A",
            public_key=agent_crypto.public_key_hex,
            name="Alice Secured PC",
            hostname="ALICE-DESKTOP",
            platform_name="Windows"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(cred)

        # User A has access to credential
        cred_a = self.enrollment_mgr.get_credential("SECURE-PC-A", user_id=self.user_a.id)
        self.assertIsNotNone(cred_a)
        self.assertEqual(cred_a.public_key, agent_crypto.public_key_hex)

        # User B cannot access User A's credential
        cred_b = self.enrollment_mgr.get_credential("SECURE-PC-A", user_id=self.user_b.id)
        self.assertIsNone(cred_b)

        # User B cannot revoke User A's credential
        rev_ok = self.enrollment_mgr.revoke_credential("SECURE-PC-A", user_id=self.user_b.id)
        self.assertFalse(rev_ok)



if __name__ == "__main__":
    unittest.main()
