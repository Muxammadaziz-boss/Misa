# ========== tests/test_multi_provider_system.py ==========
# Misa AI 9.0.0 — Comprehensive Multi-Provider LLM Integration Test Suite
# Tests: Initialization, Missing Key, Invalid Key, Timeout, 429, 500, Model Unavailable,
# Fallback, Streaming, Tool Calling, Health, Cooldown, Routing, Disabled Provider, Malformed Response.

import os
import sys
import time
import json
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from typing import Optional, List, Dict, Any
from core.intelligence.types import AIRequest, AIResponse
from core.providers.base import (
    LLMProvider,
    StreamChunk,
    ModelMetadata,
    ProviderHealth,
    TaskCategory,
    Capability,
)
from core.providers.errors import (
    ProviderError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    ServerNetworkError,
    ModelUnavailableError,
    MalformedResponseError,
    ProviderDisabledError,
)
from core.providers.health import HealthMonitor
from core.providers.registry import ModelRegistry, CURATED_MODELS
from core.providers.config import ProviderConfigManager
from core.providers.openai_compatible import OpenAICompatibleProvider
from core.providers.gemini import GeminiProvider
from core.providers.router import ModelRouter
from core.providers.manager import ProviderSystem


class MockLLMProvider(LLMProvider):
    """Testlar uchun soxta (mock) LLM provayderi (haqiqiy API kalit talab qilmaydi)."""

    def __init__(
        self,
        name: str,
        available: bool = True,
        return_response: Optional[AIResponse] = None,
        raise_exc: Optional[Exception] = None,
        stream_chunks: Optional[list] = None,
        capabilities: Optional[list] = None,
    ):
        self._name = name.lower()
        self._available = available
        self._return_response = return_response
        self._raise_exc = raise_exc
        self._stream_chunks = stream_chunks or ["Salom", " ", "Misa!"]
        self._capabilities = capabilities or [Capability.CHAT.value]
        self._health = ProviderHealth(provider=self._name)

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    def generate(self, request: AIRequest) -> AIResponse:
        if self._raise_exc:
            raise self._raise_exc
        return self._return_response or AIResponse(
            provider=self._name,
            model=request.metadata.get("model", "mock-model") if request.metadata else "mock-model",
            type="answer",
            content=f"Mock javob from {self._name}",
            success=True,
        )

    def stream(self, request: AIRequest):
        if self._raise_exc:
            raise self._raise_exc
        for chunk in self._stream_chunks:
            yield StreamChunk(text=chunk, is_final=False)
        yield StreamChunk(text="", is_final=True)

    def health_check(self) -> ProviderHealth:
        return self._health

    def supports(self, capability: str) -> bool:
        return capability.lower() in [c.lower() for c in self._capabilities]


class TestMultiProviderSystem(unittest.TestCase):
    """Misa Ko'p Provayderli Tizimi uchun to'liq testlar to'plami."""

    def setUp(self):
        from core.providers.health import get_health_monitor
        get_health_monitor().reset()
        self.health_monitor = HealthMonitor()
        self.registry = ModelRegistry()
        self.config_manager = ProviderConfigManager()

    def tearDown(self):
        from core.providers.health import get_health_monitor
        get_health_monitor().reset()

    # 1. PROVIDER INITIALIZATION
    def test_provider_initialization(self):
        groq = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", health_monitor=self.health_monitor, registry=self.registry)
        self.assertEqual(groq.name, "groq")
        self.assertEqual(groq.base_url, "https://api.groq.com/openai/v1")

        cerebras = OpenAICompatibleProvider(name="cerebras", base_url="https://api.cerebras.ai/v1", health_monitor=self.health_monitor, registry=self.registry)
        self.assertEqual(cerebras.name, "cerebras")

        gemini = GeminiProvider(base_url="https://generativelanguage.googleapis.com/v1beta", health_monitor=self.health_monitor, registry=self.registry)
        self.assertEqual(gemini.name, "gemini")

        # Curated modellarni tekshirish
        groq_models = self.registry.get_models_for_provider("groq")
        self.assertTrue(len(groq_models) >= 2)
        cerebras_models = self.registry.get_models_for_provider("cerebras")
        self.assertTrue(len(cerebras_models) >= 2)
        gemini_models = self.registry.get_models_for_provider("gemini")
        self.assertTrue(len(gemini_models) >= 2)

    # 2. MISSING API KEY
    def test_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="", health_monitor=self.health_monitor, registry=self.registry)
            self.assertFalse(prov.is_available())
            req = AIRequest(message="Salom")
            with self.assertRaises(AuthenticationError):
                prov.generate(req)

    # 3. INVALID API KEY (HTTP 401 / 403)
    @patch("requests.post")
    def test_invalid_api_key(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Invalid API Key"
        mock_post.return_value = mock_resp

        prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="invalid_key", health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="Salom")

        with self.assertRaises(AuthenticationError) as ctx:
            prov.generate(req)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(prov.health_check().status, "unavailable")

    # 4. TIMEOUT
    @patch("requests.post")
    def test_timeout(self, mock_post):
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="test_key", timeout=1.0, health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="Salom")

        with self.assertRaises(TimeoutError):
            prov.generate(req)
        self.assertEqual(prov.health_check().consecutive_failures, 1)

    # 5. HTTP 429 RATE LIMIT & COOLDOWN
    @patch("requests.post")
    def test_http_429_rate_limit(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"retry-after": "45"}
        mock_resp.text = "Rate limit exceeded"
        mock_post.return_value = mock_resp

        prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="test_key", health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="Salom")

        with self.assertRaises(RateLimitError) as ctx:
            prov.generate(req)
        self.assertEqual(ctx.exception.retry_after_seconds, 45.0)
        self.assertTrue(self.health_monitor.is_cooling_down("groq"))
        self.assertEqual(prov.health_check().status, "cooling_down")

    # 6. HTTP 500 SERVER NETWORK ERROR
    @patch("requests.post")
    def test_http_500_server_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = "Service Unavailable"
        mock_post.return_value = mock_resp

        prov = OpenAICompatibleProvider(name="cerebras", base_url="https://api.cerebras.ai/v1", api_key="test_key", health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="Salom")

        with self.assertRaises(ServerNetworkError) as ctx:
            prov.generate(req)
        self.assertEqual(ctx.exception.status_code, 503)

    # 7. MODEL UNAVAILABLE (HTTP 404)
    @patch("requests.post")
    def test_model_unavailable(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Model not found"
        mock_post.return_value = mock_resp

        prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="test_key", health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="Salom", metadata={"model": "non-existent-model"})

        with self.assertRaises(ModelUnavailableError):
            prov.generate(req)

    # 8. AUTOMATIC FALLBACK SYSTEM
    def test_fallback_chain(self):
        # 1-provayder: 429 xato beradi
        p1 = MockLLMProvider("groq", raise_exc=RateLimitError("Quota tugadi", provider="groq"))
        # 2-provayder: Timeout xato beradi
        p2 = MockLLMProvider("cerebras", raise_exc=TimeoutError("Vaqt tugadi", provider="cerebras"))
        # 3-provayder: Muvaffaqiyatli javob beradi
        p3_resp = AIResponse(provider="gemini", model="gemini-2.0-flash", type="answer", content="Muvaffaqiyatli javob!", success=True)
        p3 = MockLLMProvider("gemini", return_response=p3_resp)

        router = ModelRouter(
            providers={"groq": p1, "cerebras": p2, "gemini": p3},
            registry=self.registry,
            health_monitor=self.health_monitor,
            config_manager=self.config_manager,
            max_retries=3
        )

        req = AIRequest(message="Menga Python bo'yicha yordam ber")
        result = router.route_and_generate(req)

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.content, "Muvaffaqiyatli javob!")

    # 9. STREAMING & GRACEFUL FALLBACK
    def test_streaming_success(self):
        p = MockLLMProvider("groq", stream_chunks=["Salom", ", ", "dunyo!"])
        req = AIRequest(message="Salom")
        chunks = list(p.stream(req))

        self.assertTrue(len(chunks) >= 3)
        joined = "".join(c.text for c in chunks)
        self.assertEqual(joined, "Salom, dunyo!")
        self.assertTrue(chunks[-1].is_final)

    @patch("requests.post")
    def test_streaming_fallback_to_generate(self, mock_post):
        # Streaming 400 beradi, lekin generate() 200 beradi
        mock_resp_stream = MagicMock()
        mock_resp_stream.status_code = 400

        mock_resp_gen = MagicMock()
        mock_resp_gen.status_code = 200
        mock_resp_gen.json.return_value = {
            "choices": [{"message": {"content": "Fallback oqimsiz matn"}}]
        }

        mock_post.side_effect = [mock_resp_stream, mock_resp_gen]

        prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="test_key", health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="Salom")
        chunks = list(prov.stream(req))

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "Fallback oqimsiz matn")
        self.assertTrue(chunks[0].is_final)

    # 10. TOOL / FUNCTION CALLING
    @patch("requests.post")
    def test_tool_calling_normalization(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{
                "message": {
                    "content": None,
                    "tool_calls": [{
                        "id": "call_12345",
                        "type": "function",
                        "function": {
                            "name": "open_youtube",
                            "arguments": "{\"query\": \"uzbek music\"}"
                        }
                    }]
                }
            }],
            "usage": {"total_tokens": 42}
        }
        mock_post.return_value = mock_resp

        prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="test_key", health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="YouTube och", tools=[{"name": "open_youtube"}])
        resp = prov.generate(req)

        self.assertEqual(resp.type, "command")
        self.assertEqual(resp.intent, "open_youtube")
        self.assertEqual(resp.params, {"query": "uzbek music"})
        self.assertTrue(resp.success)

    # 11. HEALTH STATUS MONITORING
    def test_health_monitoring(self):
        monitor = HealthMonitor()
        monitor.record_success("groq", latency_ms=180.0)
        h = monitor.get_health("groq")
        self.assertEqual(h.status, "healthy")
        self.assertAlmostEqual(h.latency_ms, 180.0, delta=1.0)
        self.assertEqual(h.success_count, 1)

        # 429 xatolik
        err = RateLimitError("429", provider="groq")
        monitor.record_failure("groq", err, latency_ms=250.0)
        h2 = monitor.get_health("groq")
        self.assertEqual(h2.status, "cooling_down")
        self.assertEqual(h2.rate_limit_count, 1)

    # 12. PROVIDER COOLDOWN & AUTO-HEAL
    def test_provider_cooldown_and_auto_heal(self):
        monitor = HealthMonitor()
        monitor.record_failure("cerebras", RateLimitError("429", provider="cerebras"))
        self.assertTrue(monitor.is_cooling_down("cerebras"))

        # Sun'iy ravishda cooldown muddatini o'tkazamiz
        h = monitor._states["cerebras"]
        h.cooldown_until = time.time() - 10.0  # O'tmishda qoldi

        # Endi is_cooling_down False qaytarishi va status healthy bo'lishi kerak
        self.assertFalse(monitor.is_cooling_down("cerebras"))
        self.assertEqual(monitor.get_health("cerebras").status, "healthy")

    # 13. TASK CLASSIFICATION & ROUTING
    def test_task_classification_and_routing(self):
        router = ModelRouter(registry=self.registry, health_monitor=self.health_monitor, config_manager=self.config_manager)

        # Vision vazifasi
        req_vision = AIRequest(message="Ekran skrinshotida nima ko'rinmoqda?", metadata={"vision": True})
        self.assertEqual(router.classify_task(req_vision), TaskCategory.VISION)

        # Coding vazifasi
        req_code = AIRequest(message="Python da binary search algoritmini yozib ber")
        self.assertEqual(router.classify_task(req_code), TaskCategory.CODING)

        # Tool calling vazifasi
        req_tool = AIRequest(message="Kompyuter ovozini 50 qil", tools=[{"name": "volume_set"}])
        self.assertEqual(router.classify_task(req_tool), TaskCategory.TOOL_CALLING)

        # Fast response vazifasi
        req_fast = AIRequest(message="Salom")
        self.assertEqual(router.classify_task(req_fast), TaskCategory.FAST_RESPONSE)

    # 14. DISABLED PROVIDER HANDLING
    def test_disabled_provider_excluded_from_routing(self):
        p1 = MockLLMProvider("groq")
        p2 = MockLLMProvider("cerebras")
        router = ModelRouter(
            providers={"groq": p1, "cerebras": p2},
            registry=self.registry,
            health_monitor=self.health_monitor,
            config_manager=self.config_manager
        )

        # Groq ni o'chiramiz
        self.config_manager.set_provider_enabled("groq", False)

        req = AIRequest(message="Salom")
        candidates = router.select_candidate_models(req)
        providers_in_candidates = [c[0].name for c in candidates]

        self.assertNotIn("groq", providers_in_candidates)
        self.assertIn("cerebras", providers_in_candidates)

        # Qayta yoqamiz
        self.config_manager.set_provider_enabled("groq", True)

    # 15. MALFORMED PROVIDER RESPONSE
    @patch("requests.post")
    def test_malformed_provider_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": []}  # Bo'sh choices
        mock_post.return_value = mock_resp

        prov = OpenAICompatibleProvider(name="groq", base_url="https://api.groq.com/openai/v1", api_key="test_key", health_monitor=self.health_monitor, registry=self.registry)
        req = AIRequest(message="Salom")

        with self.assertRaises(MalformedResponseError):
            prov.generate(req)

    # 16. PROVIDER SYSTEM FACADE AND SAFE SUMMARY
    def test_provider_system_facade(self):
        ps = ProviderSystem()
        summary = ps.get_status_summary()

        self.assertIn("total_providers", summary)
        self.assertIn("providers", summary)
        self.assertIn("groq", summary["providers"])
        self.assertIn("cerebras", summary["providers"])
        self.assertIn("gemini", summary["providers"])
        self.assertIn("openrouter", summary["providers"])
        self.assertIn("nvidia", summary["providers"])

        # API kalitlar xom shaklda oshkor qilinmaganligini tasdiqlash
        for p_name, p_data in summary["providers"].items():
            raw_k = getattr(ps.get_provider(p_name), "api_key", "")
            if raw_k:
                self.assertNotIn(raw_k, str(p_data))


if __name__ == "__main__":
    unittest.main()
