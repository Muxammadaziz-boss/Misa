# ========== test_memory_intelligence.py ==========
# Misa AI 7.x — Phase 29: Memory & Context Intelligence Unit Tests
# 25 Comprehensive Test Cases covering Normalization, Policies, Retrieval, Continuity & Resilience

import os
import sys
import unittest
from unittest.mock import MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.intelligence.memory_types import (
    MemoryType,
    MemorySource,
    MemoryConfidence,
    MemoryItem,
    ActiveTaskContext,
)
from core.intelligence.memory_policy import (
    MemoryPolicy,
    PolicyDecision,
)
from core.intelligence.memory_retriever import MemoryRetriever
from core.intelligence.task_context import (
    TaskContextManager,
    get_task_context_manager,
)
from core.intelligence.context import ContextEngine
from core.agent_memory import AgentMemory


class TestMemoryIntelligence(unittest.TestCase):
    """Phase 29 Memory & Context Intelligence Unit Tests"""

    def setUp(self):
        self.memory = AgentMemory(max_short_term=10, max_conversations=50)
        self.memory.clear_knowledge()
        self.memory.clear_conversations()
        self.memory.clear_context()

    def tearDown(self):
        self.memory.clear_knowledge()
        self.memory.clear_conversations()
        self.memory.clear_context()

    # 1. Normalization of memory item
    def test_01_memory_item_normalization(self):
        item = MemoryItem(
            key="til",
            content="Python",
            type=MemoryType.FACT,
            source=MemorySource.USER,
            importance=0.8,
            confidence=1.0,
        )
        d = item.to_dict()
        self.assertEqual(d["key"], "til")
        self.assertEqual(d["content"], "Python")
        self.assertEqual(d["value"], "Python")  # Legacy field
        self.assertEqual(d["type"], "fact")
        self.assertEqual(d["source"], "user")
        self.assertTrue(item.is_active())

        # Deserialization
        reconstructed = MemoryItem.from_dict("til", d)
        self.assertEqual(reconstructed.key, "til")
        self.assertEqual(reconstructed.content, "Python")
        self.assertEqual(reconstructed.type, MemoryType.FACT)

    # 2. Fact vs preference classification
    def test_02_fact_vs_preference_classification(self):
        t1 = MemoryPolicy.classify_type("sevimli_rang", "ko'k rangni yoqtiraman")
        t2 = MemoryPolicy.classify_type("mavzu", "qora tema ishlataman")
        t3 = MemoryPolicy.classify_type("kasb", "dasturchi")
        t4 = MemoryPolicy.classify_type("vazifa", "loyihada ishlayapman")
        t5 = MemoryPolicy.classify_type("eslatma", "kechki 8 da dori ichishni eslat")

        self.assertEqual(t1, MemoryType.PREFERENCE)
        self.assertEqual(t2, MemoryType.PREFERENCE)
        self.assertEqual(t3, MemoryType.FACT)
        self.assertEqual(t4, MemoryType.TASK)
        self.assertEqual(t5, MemoryType.NOTE)

    # 3. Explicit memory save
    def test_03_explicit_memory_save(self):
        ok = self.memory.save_knowledge("shahar", "Toshkent", source=MemorySource.USER)
        self.assertTrue(ok)
        k = self.memory.get_knowledge("shahar")
        self.assertIsNotNone(k)
        self.assertEqual(k["value"], "Toshkent")
        self.assertEqual(k["type"], "fact")
        self.assertEqual(k["confidence"], 1.0)

    # 4. Inferred low-confidence handling
    def test_04_inferred_confidence_levels(self):
        item = MemoryItem(
            key="taxminiy_did",
            content="ehtimol jazz musiqani yoqtiradi",
            confidence=MemoryConfidence.LOW.value,
        )
        self.assertEqual(item.confidence, 0.3)
        self.assertLess(item.confidence, MemoryConfidence.HIGH.value)

    # 5. Secret rejection (API key)
    def test_05_secret_rejection_api_key(self):
        gemini_secret = "AIzaSyD9FakeSecretKey35CharactersLengthX"
        openai_secret = "sk-proj-FakeOpenAIKey1234567890abcdefghijklmn"
        github_secret = "ghp_FakeGitHubPersonalAccessToken123456"

        self.assertTrue(MemoryPolicy.contains_sensitive_data(gemini_secret))
        self.assertTrue(MemoryPolicy.contains_sensitive_data(openai_secret))
        self.assertTrue(MemoryPolicy.contains_sensitive_data(github_secret))

        # AgentMemory save rejection
        res = self.memory.save_knowledge("api_key", gemini_secret)
        self.assertFalse(res)
        self.assertIsNone(self.memory.get_knowledge("api_key"))

    # 6. Secret rejection (password)
    def test_06_secret_rejection_password(self):
        pwd_content = "parol: MySecretPass123!"
        self.assertTrue(MemoryPolicy.contains_sensitive_data(pwd_content))
        res = self.memory.save_knowledge("user_password", pwd_content)
        self.assertFalse(res)
        self.assertIsNone(self.memory.get_knowledge("user_password"))

    # 7. Duplicate detection: same key and content updates recency
    def test_07_duplicate_detection_same_key(self):
        self.memory.save_knowledge("til", "Python")
        initial_time = self.memory.get_knowledge("til")["saved_at"]
        initial_access = self.memory.get_knowledge("til")["access_count"]

        # Duplicate write
        ok = self.memory.save_knowledge("til", "Python")
        self.assertTrue(ok)
        updated = self.memory.get_knowledge("til")
        self.assertGreaterEqual(updated["access_count"], initial_access)

    # 8. Duplicate fuzzy detection: synonymous key
    def test_08_duplicate_fuzzy_detection(self):
        existing = {"sevimli_rang": {"value": "ko'k"}}
        decision = MemoryPolicy.evaluate_write(
            key="yoqtirgan_sevimli_rang",
            content="ko'k",
            existing_knowledge=existing
        )
        self.assertTrue(decision.is_duplicate)
        self.assertEqual(decision.existing_key, "sevimli_rang")

    # 9. Memory update on change
    def test_09_memory_update_on_change(self):
        self.memory.save_knowledge("rejim", "qora")
        self.assertEqual(self.memory.get_knowledge("rejim")["value"], "qora")

        # Update with new value
        self.memory.save_knowledge("rejim", "yorug'")
        self.assertEqual(self.memory.get_knowledge("rejim")["value"], "yorug'")

    # 10. Relevance ranking (lexical overlap)
    def test_10_relevance_ranking_lexical_overlap(self):
        self.memory.save_knowledge("sevimli_rang", "yashil")
        self.memory.save_knowledge("dasturlash_tili", "Python va Django")
        self.memory.save_knowledge("shahar", "Samarqand")

        results = self.memory.retrieve_relevant("Django da veb sayt yaratish", limit=2)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].key, "dasturlash_tili")

    # 11. Recency ranking
    def test_11_recency_ranking(self):
        tokens = {"python"}
        item_fresh = MemoryItem(key="fresh", content="python dasturchisi", importance=0.5)
        item_stale = MemoryItem(key="stale", content="python dasturchisi", importance=0.5)
        item_stale.created_at = "2020-01-01T00:00:00"
        item_stale.updated_at = "2020-01-01T00:00:00"

        score_fresh = MemoryRetriever.calculate_relevance_score(tokens, item_fresh)
        score_stale = MemoryRetriever.calculate_relevance_score(tokens, item_stale)
        self.assertGreater(score_fresh, score_stale)

    # 12. Task relevance boost
    def test_12_task_relevance_boost(self):
        tokens = {"xabar"}
        item_tg = MemoryItem(key="bot", content="telegram xabar yuborish", importance=0.5)
        item_other = MemoryItem(key="sms", content="xabar yuborish", importance=0.5)

        score_normal = MemoryRetriever.calculate_relevance_score(tokens, item_tg, task_entities=[])
        score_boosted = MemoryRetriever.calculate_relevance_score(tokens, item_tg, task_entities=["telegram"])
        self.assertGreater(score_boosted, score_normal)

    # 13. Bounded retrieval limit
    def test_13_bounded_retrieval_limit(self):
        for i in range(10):
            self.memory.save_knowledge(f"key_{i}", f"umumiy ma'lumot {i}")

        retrieved = self.memory.retrieve_relevant("ma'lumot", limit=4)
        self.assertLessEqual(len(retrieved), 4)

    # 14. Context budget
    def test_14_context_budget_respect(self):
        retriever = MemoryRetriever()
        items = [
            MemoryItem(key=f"k{i}", content=f"content {i}")
            for i in range(20)
        ]
        res = retriever.retrieve("content", items, limit=5)
        self.assertEqual(len(res), 5)

    # 15. Conversation continuity bounded history
    def test_15_conversation_continuity_bounded(self):
        for i in range(10):
            self.memory.add_conversation(f"User {i}", f"Agent {i}")

        history = self.memory.get_history_for_ai(last_n=3)
        self.assertEqual(len(history), 6)  # 3 turns * 2 (user + assistant)
        self.assertEqual(history[-2]["content"], "User 9")
        self.assertEqual(history[-1]["content"], "Agent 9")

    # 16. Reference hinting from active task
    def test_16_reference_hinting_from_active_task(self):
        tm = TaskContextManager()
        tm.set_active_task("Telegram botini tuzish", entities=["telegram"])

        hint = tm.resolve_reference_hint("shunga qanday xabar yuboraman?", [])
        self.assertIsNotNone(hint)
        self.assertIn("telegram", hint)

    # 17. Reference hinting from conversation history
    def test_17_reference_hinting_from_conversation(self):
        tm = TaskContextManager()
        history = [
            {"role": "user", "content": "Men GitHub dagi loyihamni tekshirmoqchiman"},
            {"role": "assistant", "content": "Albatta, github loyihangizni ko'ramiz"},
        ]

        hint = tm.resolve_reference_hint("undagi fayllarni ochib ber", history)
        self.assertIsNotNone(hint)
        self.assertIn("github", hint)

    # 18. Active task context tracking
    def test_18_active_task_context_lifecycle(self):
        tm = TaskContextManager()
        task = tm.set_active_task("Chrome brauzerida sayt ochish")
        self.assertEqual(task.status, "active")
        self.assertIn("chrome", task.entities)

        tm.update_task_progress(action="navigate", result="page_loaded", new_entities=["youtube"])
        self.assertEqual(task.last_action, "navigate")
        self.assertIn("youtube", task.entities)

        tm.complete_task()
        self.assertIsNone(tm.get_active_task())

    # 19. Conflict resolution with superseded_by
    def test_19_conflict_resolution_superseded(self):
        old_item = MemoryItem(key="mavzu", content="qora tema", confidence=1.0)
        new_item = MemoryItem(key="mavzu", content="oq tema", confidence=1.0)

        resolved = MemoryPolicy.resolve_conflict(new_item, [old_item])
        self.assertEqual(len(resolved), 1)
        self.assertEqual(old_item.superseded_by, new_item.id)
        self.assertFalse(old_item.is_active())

    # 20. Inactive items excluded from retrieval
    def test_20_inactive_items_excluded_from_retrieval(self):
        active_item = MemoryItem(key="shahar", content="Toshkent")
        inactive_item = MemoryItem(key="shahar", content="Samarqand", superseded_by="other_id")

        results = MemoryRetriever.retrieve("Toshkent yoki Samarqand", [active_item, inactive_item])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "Toshkent")

    # 21. Memory failure resilience in ContextEngine
    def test_21_context_engine_resilience(self):
        bad_memory = MagicMock()
        bad_memory.get_conversations.side_effect = RuntimeError("Storage corrupted")
        bad_memory.get_knowledge.side_effect = RuntimeError("Database locked")

        engine = ContextEngine(memory=bad_memory)
        req = engine.assemble("Salom Misa")
        self.assertEqual(req.message, "Salom Misa")
        self.assertIn("prompt", req.system_context)

    # 22. Memory clearing
    def test_22_memory_clearing(self):
        self.memory.save_knowledge("k1", "v1")
        self.memory.save_knowledge("k2", "v2")
        self.assertEqual(len(self.memory.get_knowledge()), 2)

        self.memory.clear_knowledge()
        self.assertEqual(len(self.memory.get_knowledge()), 0)
        self.assertEqual(len(self.memory.get_memory_items()), 0)

    # 23. Memory single delete
    def test_23_memory_single_delete(self):
        self.memory.save_knowledge("muhim_fakt", "qiymat")
        self.assertIsNotNone(self.memory.get_knowledge("muhim_fakt"))

        ok = self.memory.delete_knowledge("muhim_fakt")
        self.assertTrue(ok)
        self.assertIsNone(self.memory.get_knowledge("muhim_fakt"))

    # 24. Backward compatibility with AgentMemory
    def test_24_backward_compatibility(self):
        self.memory.save_knowledge("dasturchi_tili", "Python")
        k = self.memory.get_knowledge("dasturchi_tili")
        self.assertIsInstance(k, dict)
        self.assertIn("value", k)
        self.assertIn("saved_at", k)
        self.assertIn("access_count", k)
        self.assertEqual(k["value"], "Python")

        summary = self.memory.get_knowledge_summary()
        self.assertIn("dasturchi_tili: Python", summary)

    # 25. ContextEngine integration and anti-injection headers
    def test_25_context_engine_integration_and_anti_injection(self):
        self.memory.save_knowledge("user_name", "Aziz")
        self.memory.save_knowledge("sevimli_klub", "Real Madrid")

        tm = TaskContextManager()
        tm.set_active_task("Klub yangiliklarini ko'rish", entities=["real madrid"])

        engine = ContextEngine(memory=self.memory, task_manager=tm)
        req = engine.assemble("Shunga doir yangiliklarni ko'rsat", user_name="Aziz")

        prompt = req.system_context["prompt"]
        self.assertIn("DATA ONLY", prompt)
        self.assertIn("FAOL VAZIFA KONTEKSTI", prompt)
        self.assertIn("sevimli_klub", req.memory["knowledge"])
        self.assertEqual(req.metadata["user_name"], "Aziz")

    # 26. MemoryExtractor autonomous regex patterns
    def test_26_memory_extractor_patterns(self):
        from core.intelligence.memory_extractor import MemoryExtractor

        facts = MemoryExtractor.extract_from_text("Salom, mening ismim Bobur va men Toshkentda yashayman.")
        keys = {f["key"]: f["content"] for f in facts}
        self.assertIn("foydalanuvchi_ismi", keys)
        self.assertEqual(keys["foydalanuvchi_ismi"], "Bobur")
        self.assertIn("foydalanuvchi_shahri", keys)

        # Note extraction
        notes = MemoryExtractor.extract_from_text("Buni eslab qol: docker container porti 9000")
        self.assertTrue(len(notes) > 0)
        self.assertTrue(any("docker container" in n["content"].lower() for n in notes))

    # 27. MemoryExtractor autonomous integration with AgentMemory
    def test_27_memory_extractor_autonomous_save(self):
        self.memory.add_conversation("Men backend dasturchisiman va mening loyiham Mikasa v9", "Tushundim, do'stim!")
        knowledge = self.memory.get_knowledge()
        self.assertTrue("foydalanuvchi_kasbi" in knowledge or "faol_loyiha" in knowledge)


if __name__ == "__main__":
    unittest.main()
