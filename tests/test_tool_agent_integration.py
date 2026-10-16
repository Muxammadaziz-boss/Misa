# ========== test_tool_agent_integration.py ==========
# Phase 32 — AgentLoop & Tool System 2.0 Integration Tests
# Capability-driven execution, Idempotency Guard, Builtin Tool Coverage & Observability

import os
import sys
import time
import unittest
from unittest.mock import MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.intelligence.types import (
    AgentPlan,
    AgentState,
    PlanStatus,
    PlanStep,
    RiskLevel,
    StepStatus,
    VerificationStatus,
    VerificationResult,
)
from core.intelligence.agent_loop import AgentLoop
from core.intelligence.permission import PermissionEngine
from core.intelligence.verifier import AgentVerifier
from core.intelligence.task_context import TaskContextManager
from core.tools.contract import ToolContract2, ToolErrorCode, ToolHealth, ToolResult
from core.agent_tools import Tool, ToolRegistry, get_tool_registry


class TestToolAgentIntegration(unittest.TestCase):
    """AgentLoop va Tool System 2.0 integratsion testlari"""

    def setUp(self):
        self.registry = ToolRegistry()
        self.perm_engine = PermissionEngine()
        self.task_mgr = TaskContextManager()
        self.loop = AgentLoop(
            tool_registry=self.registry,
            permission_engine=self.perm_engine,
            task_context_manager=self.task_mgr
        )

    def test_builtin_tools_contract_coverage(self):
        """Barcha 29 ta o'rnatilgan vosita ToolContract2 talablariga 100% javob berishi"""
        global_registry = get_tool_registry()
        tools = global_registry.list_names()

        self.assertGreaterEqual(len(tools), 25, "O'rnatilgan vositalar soni kamida 25 ta bo'lishi kerak")

        for name in tools:
            tool = global_registry.get(name)
            self.assertIsNotNone(tool, f"Vosita topilmadi: {name}")
            self.assertIsInstance(tool, ToolContract2, f"Vosita ToolContract2 bo'lishi shart: {name}")

            # Majburiy atributlar
            self.assertEqual(tool.version, "2.0.0", f"Versiya 2.0.0 bo'lishi kerak: {name}")
            self.assertEqual(tool.health, ToolHealth.AVAILABLE, f"Salomatlik AVAILABLE bo'lishi kerak: {name}")
            self.assertIsInstance(tool.risk_level, RiskLevel, f"RiskLevel enum bo'lishi kerak: {name}")
            self.assertGreater(tool.timeout, 0.0, f"Timeout musbat bo'lishi kerak: {name}")
            self.assertIsInstance(tool.idempotent, bool, f"idempotent bool bo'lishi kerak: {name}")
            self.assertIsInstance(tool.destructive, bool, f"destructive bool bo'lishi kerak: {name}")
            self.assertTrue(len(tool.capabilities) > 0, f"Kamida bitta qobiliyat bo'lishi kerak: {name}")
            self.assertIsInstance(tool.aliases, list, f"Aliases list bo'lishi kerak: {name}")

    def test_builtin_capability_dispatch_calculation(self):
        """Haqiqiy registrdan 'calculation' qobiliyati orqali hisoblashni bajarish"""
        global_registry = get_tool_registry()
        calc_tools = global_registry.find_by_capability("calculation")
        self.assertTrue(len(calc_tools) > 0)

        # Qobiliyat nomi orqali to'g'ridan-to'g'ri chaqirish
        res = global_registry.call("calculation", expression="15 + 27")
        self.assertIsInstance(res, ToolResult)
        self.assertTrue(res.success)
        # Natija 42
        res_val = str(res.data)
        self.assertIn("42", res_val)

    def test_agent_executes_step_with_capability_name(self):
        """AgentLoop rejasida vosita nomi o'rniga qobiliyat ('text_processor') berilganda ham to'g'ri tanlanib bajarilishi"""
        def process_text(text):
            return {"success": True, "result": f"Processed: {text}"}

        custom_tool = Tool(
            name="my_text_processor",
            description="Processes text",
            parameters={"text": {"type": "string", "required": True}},
            function=process_text,
            capabilities=["text_processor", "formatter"],
            aliases=["text_cleaner"],
        )
        self.registry.register(custom_tool)

        plan = AgentPlan(
            plan_id="plan_cap_1",
            goal="Matnni qayta ishlash",
            steps=[
                PlanStep(
                    step_id="step_1",
                    order=1,
                    intent="Matnni tozalash",
                    tool="text_processor",  # Qobiliyat nomi ko'rsatilgan!
                    parameters={"text": "antigravity intelligence"},
                    expected_result="Processed: antigravity intelligence"
                )
            ]
        )

        from core.intelligence.observability import ContextTrace
        trace = ContextTrace(request_id="cap_req", trace_id="cap_trace_1", query="Matnni qayta ishlash")
        response = self.loop.execute_plan(plan, trace=trace)
        self.assertTrue(response.success)
        self.assertEqual(plan.status, PlanStatus.COMPLETED)
        self.assertEqual(plan.steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(plan.steps[0].observed_result, "Processed: antigravity intelligence")

        # Observability trace da tanlanish bosqichlari mavjudligini tekshirish
        trace_stages = [s.stage for s in trace.stages]
        self.assertIn("TOOL_DISCOVERED", trace_stages)
        self.assertIn("TOOL_SELECTED", trace_stages)

    def test_agent_blocks_retry_for_destructive_tool(self):
        """Xatolikka uchragan destruktiv (destructive=True) amal uchun AgentLoop qayta urinishni (retry) bloklashi"""
        fail_count = {"count": 0}

        def destructive_action():
            fail_count["count"] += 1
            return {"success": False, "error": "Disk partition failure"}

        dest_tool = Tool(
            name="disk_formatter",
            description="Formats disk",
            parameters={},
            function=destructive_action,
            risk_level=RiskLevel.LOW,
            destructive=True,
            idempotent=False,
        )
        self.registry.register(dest_tool)

        from core.tools.security_policy import get_security_policy
        token = get_security_policy().token_manager.create_token("disk_formatter", {})

        plan = AgentPlan(
            plan_id="plan_dest_1",
            goal="Format disk",
            steps=[
                PlanStep(
                    step_id="step_1",
                    order=1,
                    intent="Format",
                    tool="disk_formatter",
                    parameters={"_confirmation_token": token},
                    risk_level=RiskLevel.LOW,
                    max_retries=3  # 3 ta ruxsat berilgan bo'lsa ham!
                )
            ]
        )

        response = self.loop.execute_plan(plan)
        self.assertFalse(response.success)
        self.assertEqual(plan.status, PlanStatus.FAILED)
        self.assertIn("qayta urinish bloklandi", response.content.lower())
        # Qayta urinish bloklanganligi sababli funksiya faqat 1 marta chaqirilgan bo'lishi kerak
        self.assertEqual(fail_count["count"], 1)

    def test_agent_allows_retry_for_idempotent_tool(self):
        """Xavfsiz va idempotent (idempotent=True) amal xato bersa, AgentLoop qayta urinib muvaffaqiyatga erishishi"""
        attempts = {"count": 0}

        def flaky_lookup():
            attempts["count"] += 1
            if attempts["count"] == 1:
                return {"success": False, "error": "Network timeout"}
            return {"success": True, "result": "Data found on retry"}

        safe_tool = Tool(
            name="network_lookup",
            description="Reads network",
            parameters={},
            function=flaky_lookup,
            idempotent=True,
            destructive=False,
        )
        self.registry.register(safe_tool)

        plan = AgentPlan(
            plan_id="plan_retry_1",
            goal="Lookup data",
            steps=[
                PlanStep(
                    step_id="step_1",
                    order=1,
                    intent="Lookup",
                    tool="network_lookup",
                    parameters={},
                    max_retries=2
                )
            ]
        )

        response = self.loop.execute_plan(plan)
        self.assertTrue(response.success)
        self.assertEqual(plan.status, PlanStatus.COMPLETED)
        self.assertEqual(attempts["count"], 2)
        self.assertEqual(plan.steps[0].observed_result, "Data found on retry")

    def test_agent_step_parameter_validation_failure(self):
        """Asbob uchun kerakli majburiy parametr berilmaganda validatsiya qat'iy to'xtatishi"""
        tool = Tool(
            name="email_sender",
            description="Sends email",
            parameters={
                "recipient": {"type": "string", "required": True},
                "body": {"type": "string", "required": True},
            },
            function=lambda recipient, body: {"success": True, "result": "Sent"},
        )
        self.registry.register(tool)

        plan = AgentPlan(
            plan_id="plan_val_1",
            goal="Send email",
            steps=[
                PlanStep(
                    step_id="step_1",
                    order=1,
                    intent="Send",
                    tool="email_sender",
                    parameters={"recipient": "user@example.com"},  # body missing!
                    max_retries=0
                )
            ]
        )

        response = self.loop.execute_plan(plan)
        self.assertFalse(response.success)
        self.assertEqual(plan.status, PlanStatus.FAILED)
        self.assertIn("majburiy parametr yetishmayapti", str(plan.steps[0].error).lower())

    def test_agent_step_timeout_enforcement(self):
        """AgentLoop da asbob timeout ga uchraganda loop to'xtab qolmasligi va xato qayd etilishi"""
        def hanging_action():
            time.sleep(1.0)
            return {"success": True}

        hanging_tool = Tool(
            name="hanging_task",
            description="Hangs",
            parameters={},
            function=hanging_action,
            timeout=0.1,  # 100ms
        )
        self.registry.register(hanging_tool)

        plan = AgentPlan(
            plan_id="plan_timeout_1",
            goal="Hanging execution",
            steps=[
                PlanStep(
                    step_id="step_1",
                    order=1,
                    intent="Hang",
                    tool="hanging_task",
                    parameters={},
                    max_retries=0
                )
            ]
        )

        t0 = time.time()
        response = self.loop.execute_plan(plan)
        dur = time.time() - t0

        self.assertFalse(response.success)
        self.assertLess(dur, 0.8, "AgentLoop timeout tufayli 0.8 soniyadan kam vaqtda tugashi kerak")
        self.assertIn("vaqt chegarasida", str(plan.steps[0].error).lower())

    def test_agent_fallback_tool_switching(self):
        """Asosiy asbob ishlamay qolganda, AgentLoop avtomatik mos fallback vositaga o'tishi"""
        def broken_fetch():
            return {"success": False, "error": "Primary API down"}

        def working_backup_fetch():
            return {"success": True, "result": "Backup data content"}

        # 2 ta bir xil qobiliyatga ega asbob
        tool1 = Tool(
            name="fetch_primary",
            description="Primary fetch",
            parameters={},
            function=broken_fetch,
            capabilities=["data_fetch"],
            risk_level=RiskLevel.LOW,
        )
        tool2 = Tool(
            name="fetch_backup",
            description="Backup fetch",
            parameters={},
            function=working_backup_fetch,
            capabilities=["data_fetch"],
            risk_level=RiskLevel.LOW,
        )
        self.registry.register(tool1)
        self.registry.register(tool2)

        plan = AgentPlan(
            plan_id="plan_fallback_1",
            goal="Fetch data safely",
            steps=[
                PlanStep(
                    step_id="step_1",
                    order=1,
                    intent="Fetch",
                    tool="fetch_primary",
                    parameters={},
                    max_retries=1
                )
            ]
        )

        response = self.loop.execute_plan(plan)
        self.assertTrue(response.success)
        self.assertEqual(plan.status, PlanStatus.COMPLETED)
        self.assertEqual(plan.steps[0].observed_result, "Backup data content")

    def test_multi_step_sequential_agent_flow(self):
        """Ko'p qadamli rejada asboblar ketma-ket muvaffaqiyatli bajarilishi"""
        def calc_func(expression):
            return {"success": True, "result": str(eval(expression))}

        def format_func(text):
            return {"success": True, "result": text.upper()}

        t1 = Tool(name="calc_step", description="Calc", parameters={"expression": {"type": "string", "required": True}}, function=calc_func)
        t2 = Tool(name="format_step", description="Format", parameters={"text": {"type": "string", "required": True}}, function=format_func)
        self.registry.register(t1)
        self.registry.register(t2)

        plan = AgentPlan(
            plan_id="plan_multi_1",
            goal="Calculate and format",
            steps=[
                PlanStep(step_id="s1", order=1, intent="Calc", tool="calc_step", parameters={"expression": "50 * 2"}),
                PlanStep(step_id="s2", order=2, intent="Format", tool="format_step", parameters={"text": "misa tool system 2.0"}),
            ]
        )

        response = self.loop.execute_plan(plan)
        self.assertTrue(response.success)
        self.assertEqual(plan.status, PlanStatus.COMPLETED)
        self.assertEqual(plan.steps[0].observed_result, "100")
        self.assertEqual(plan.steps[1].observed_result, "MISA TOOL SYSTEM 2.0")


if __name__ == "__main__":
    unittest.main()
