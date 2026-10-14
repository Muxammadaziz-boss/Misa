# ========== test_v9_ai_database_keys.py ==========
# Tests for AI Key Manager, Database Sync, Quota Cooldown & Automatic AI on Login

import os
import json
import time
import unittest
from unittest.mock import patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop


from core.v8.ai_key_manager import AIKeyManager, get_ai_key_manager
from core.intelligence.types import AIRequest
from core.intelligence.gemini_provider import GeminiProvider
from core.api_server import create_app


class TestAIKeyManager(unittest.TestCase if hasattr(__import__('unittest'), 'TestCase') else object):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "MISA_GEMINI_API_KEY": ""
        }, clear=False)
        self.env_patcher.start()
        self.mgr = AIKeyManager()
        self.mgr._system_keys = {"gemini": [], "openrouter": []}
        self.mgr._user_keys = {}
        self.mgr._key_cooldowns = {}

    def tearDown(self):
        self.env_patcher.stop()

    def test_register_and_get_system_key(self):
        self.mgr.register_system_key("gemini", "AIzaSyTestSystemKey1")
        self.assertEqual(self.mgr.get_active_gemini_key(), "AIzaSyTestSystemKey1")

    def test_user_key_priority_over_system_key(self):
        self.mgr.register_system_key("gemini", "AIzaSyTestSystemKey1")
        self.mgr.set_user_key("user_123", "gemini", "AIzaSyUserPersonalKey")
        # For user_123, personal key must take precedence
        self.assertEqual(self.mgr.get_active_gemini_key(user_id="user_123"), "AIzaSyUserPersonalKey")
        # For other users, system key is used
        self.assertEqual(self.mgr.get_active_gemini_key(user_id="other_user"), "AIzaSyTestSystemKey1")

    def test_mark_key_failed_triggers_cooldown_and_fallback(self):
        self.mgr.register_system_key("gemini", "AIzaSyBackupWorkingKey")
        self.mgr.register_system_key("gemini", "AIzaSyPrimaryExhaustedKey")
        
        # Most recently registered key is prepended and active
        self.assertEqual(self.mgr.get_active_gemini_key(), "AIzaSyPrimaryExhaustedKey")
        
        # Mark 429 quota failure on primary key
        self.mgr.mark_key_failed("AIzaSyPrimaryExhaustedKey", cooldown_seconds=60.0)
        
        # Next active key must automatically become the backup working key!
        self.assertEqual(self.mgr.get_active_gemini_key(), "AIzaSyBackupWorkingKey")

    def test_sync_from_user_session_metadata(self):
        metadata = {
            "gemini_api_key": "AIzaSySessionCustomKey",
            "preferred_model": "gemini-3.1-flash-lite"
        }
        self.mgr.sync_from_user_session("user_abc", metadata)
        self.assertEqual(self.mgr.get_active_gemini_key(user_id="user_abc"), "AIzaSySessionCustomKey")
        self.assertEqual(self.mgr.get_preferred_model("gemini"), "gemini-3.1-flash-lite")

    def test_status_summary_masking(self):
        self.mgr.register_system_key("gemini", "AIzaSy1234567890abcdef")
        summary = self.mgr.get_status_summary()
        self.assertTrue(summary["gemini_configured"])
        self.assertTrue(summary["masked_key"].startswith("AIzaSy12...cdef"))
        self.assertEqual(summary["status"], "ready")


class TestAIEndpointsIntegration(AioHTTPTestCase):
    async def get_application(self):
        return create_app()

    @unittest_run_loop
    async def test_ai_config_get(self):
        resp = await self.client.request("GET", "/api/ai/config")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("config", data)
        self.assertIn("gemini_configured", data["config"])

    @unittest_run_loop
    async def test_ai_sync_endpoint(self):
        resp = await self.client.request("POST", "/api/ai/sync")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertTrue(data.get("ok"))

