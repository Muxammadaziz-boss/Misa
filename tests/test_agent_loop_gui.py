"""
tests/test_agent_loop_gui.py
Tests for Agent Loop: Plan -> Act -> Observe -> Verify
with GUI controller capabilities, Notepad/Calculator workflows, loop detection,
and local-by-default vision privacy.
"""

import unittest
from unittest.mock import patch, MagicMock

from core.intelligence.types import (
    RiskLevel,
    PlanStatus,
    StepStatus,
    VerificationStatus,
    PlanStep,
    AgentPlan,
    StepResult,
    VerificationResult,
)
from core.intelligence.verifier import AgentVerifier
from core.intelligence.planner import GoalDecomposer
from core.intelligence.agent_loop import AgentLoop
from core.ai_engine import ekran_tahlil
from core.agent_tools import _screen_analyze


class TestAgentLoopGUI(unittest.TestCase):

    def setUp(self):
        self.verifier = AgentVerifier()
        self.decomposer = GoalDecomposer()

    def test_notepad_workflow_decomposition(self):
        """Notepad workflow rejasini tuzish va precondition/postcondition tekshiruvi"""
        goal = "Notepad'ga 'Misa AI ishlamoqda' matnini yozish"
        plan = self.decomposer.decompose(goal)

        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan.steps), 3)

        step1, step2, step3 = plan.steps[0], plan.steps[1], plan.steps[2]

        # Step 1: focus_window (Notepad)
        self.assertEqual(step1.tool, "focus_window")
        self.assertEqual(step1.parameters.get("title"), "Notepad")
        self.assertTrue(bool(step1.precondition))
        self.assertTrue(bool(step1.postcondition))

        # Step 2: keyboard_type
        self.assertEqual(step2.tool, "keyboard_type")
        self.assertEqual(step2.parameters.get("text"), "Misa AI ishlamoqda")
        self.assertEqual(step2.parameters.get("target_window"), "Notepad")
        self.assertIn("step_1", step2.dependencies)

        # Step 3: screen_analyze
        self.assertEqual(step3.tool, "screen_analyze")
        self.assertIn("step_2", step3.dependencies)

    def test_calculator_workflow_decomposition(self):
        """Calculator workflow rejasini tuzish va hisoblash qadami"""
        goal = "Calculator'ni ochib 7 ni hisoblash"
        plan = self.decomposer.decompose(goal)

        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan.steps), 3)

        step1, step2, step3 = plan.steps[0], plan.steps[1], plan.steps[2]

        self.assertEqual(step1.tool, "focus_window")
        self.assertEqual(step1.parameters.get("title"), "Calculator")

        self.assertEqual(step2.tool, "calculator")
        self.assertEqual(step2.parameters.get("expression"), "7")
        self.assertIn("step_1", step2.dependencies)

        self.assertEqual(step3.tool, "screen_analyze")
        self.assertIn("step_2", step3.dependencies)

    def test_verifier_gui_oracles(self):
        """AgentVerifier GUI amallari uchun deterministik orakullari"""
        # 1. Keyboard type
        step_kb = PlanStep(step_id="s1", order=1, intent="keyboard_type", tool="keyboard_type")
        res_kb_ok = StepResult(
            step_id="s1",
            tool="keyboard_type",
            success=True,
            raw_result={"typed": True, "postcondition_verified": True, "text": "Salom"}
        )
        ver_kb = self.verifier.verify_step(step_kb, res_kb_ok)
        self.assertEqual(ver_kb.status, VerificationStatus.SUCCESS)

        # 2. Screen click
        step_click = PlanStep(step_id="s2", order=2, intent="screen_click", tool="screen_click")
        res_click_ok = StepResult(
            step_id="s2",
            tool="screen_click",
            success=True,
            raw_result={"clicked": True, "x": 150, "y": 250}
        )
        ver_click = self.verifier.verify_step(step_click, res_click_ok)
        self.assertEqual(ver_click.status, VerificationStatus.SUCCESS)

        # 3. Screen analyze
        step_screen = PlanStep(step_id="s3", order=3, intent="screen_analyze", tool="screen_analyze")
        res_screen_ok = StepResult(
            step_id="s3",
            tool="screen_analyze",
            success=True,
            raw_result={"message": "Notepad oynasi faol", "local_analysis": True}
        )
        ver_screen = self.verifier.verify_step(step_screen, res_screen_ok)
        self.assertEqual(ver_screen.status, VerificationStatus.SUCCESS)

    def test_verifier_unknown_policy_retry_or_clarification(self):
        """UNKNOWN holatida darhol davom etmay, retry yoki clarification so'rashi kerak"""
        step = PlanStep(step_id="s1", order=1, intent="custom_tool", tool="custom_tool", max_retries=1, retry_count=0)
        unknown_ver = VerificationResult(verified=True, status=VerificationStatus.UNKNOWN, reason="No oracle")

        # 1-marta (retry mavjud): re-observe / retry
        can_cont_1, reason_1 = self.verifier.should_continue(unknown_ver, step)
        self.assertFalse(can_cont_1)
        self.assertEqual(reason_1, "UNKNOWN_STATUS_RETRY_OBSERVATION")

        # Retry tugagan: foydalanuvchidan tasdiq / clarification so'rash
        step.retry_count = 1
        can_cont_2, reason_2 = self.verifier.should_continue(unknown_ver, step)
        self.assertFalse(can_cont_2)
        self.assertEqual(reason_2, "UNKNOWN_STATUS_REQUIRES_CLARIFICATION")

    def test_agent_loop_loop_detection(self):
        """AgentLoop bir xil amallar ketma-ket 3 marta takrorlansa siklni aniqlashi va to'xtatishi kerak"""
        loop = AgentLoop(verifier=self.verifier)

        # 4 ta bir xil qadamdan iborat reja
        steps = [
            PlanStep(step_id=f"step_{i}", order=i, intent="weather", tool="weather", parameters={"city": "Toshkent"})
            for i in range(1, 5)
        ]
        plan = AgentPlan(
            plan_id="plan_loop_test",
            goal="Loop test",
            steps=steps,
            execution_order=[f"step_{i}" for i in range(1, 5)]
        )

        with patch.object(loop, "_act_execute_step") as mock_act:
            mock_act.return_value = StepResult(
                step_id="step_x",
                tool="weather",
                success=True,
                raw_result="Harorat 25C"
            )
            resp = loop.execute_plan(plan)

        self.assertFalse(resp.success)
        self.assertEqual(resp.error_code, "AGENT_LOOP_DETECTED")
        self.assertEqual(plan.status, PlanStatus.FAILED)

    def test_local_vision_privacy_by_default(self):
        """ekran_tahlil va screen_analyze default holatda lokal maxfiy rejimda ishlashi va cloud ga yubormasligi kerak"""
        with patch("core.gui.controller.WindowsGUIController.get_active_window") as mock_active:
            mock_active.return_value = MagicMock(title="Calculator", process_name="CalculatorApp.exe")

            # 1. Default (allow_cloud=False)
            res_local = ekran_tahlil()
            self.assertIn("Lokal ekran tahlili", res_local)
            self.assertIn("Calculator", res_local)
            self.assertIn("aniq foydalanuvchi tasdig'i talab etiladi", res_local)

            # 2. Tool chaqiruvi orqali
            tool_res = _screen_analyze(question="Ekranda nima bor?", allow_cloud=False)
            self.assertTrue(tool_res.get("local_analysis"))
            self.assertFalse(tool_res.get("cloud_allowed"))


if __name__ == "__main__":
    unittest.main()
