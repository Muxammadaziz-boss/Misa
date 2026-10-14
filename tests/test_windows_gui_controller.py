# ========== tests/test_windows_gui_controller.py ==========
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.gui.controller import WindowsGUIController, WindowTarget, get_gui_controller


class TestWindowsGUIController(unittest.TestCase):
    def setUp(self):
        self.ctrl = WindowsGUIController()
        self.ctrl._is_window_alive = MagicMock(return_value=True)
        self.mock_target = WindowTarget(
            hwnd=1001,
            title="Untitled - Notepad",
            class_name="Notepad",
            pid=5555,
            rect=(100, 100, 900, 700),  # width=800, height=600
            is_elevated=False,
            is_focused=True,
        )

    def test_01_window_target_bounds_and_containment(self):
        target = self.mock_target
        self.assertEqual(target.width, 800)
        self.assertEqual(target.height, 600)

        # Ichidagi koordinatalar
        self.assertTrue(target.contains_point(200, 300))
        self.assertTrue(target.contains_point(100, 100))
        self.assertTrue(target.contains_point(900, 700))

        # Tashqarisidagi koordinatalar
        self.assertFalse(target.contains_point(50, 50))
        self.assertFalse(target.contains_point(950, 500))
        self.assertFalse(target.contains_point(400, 800))

    def test_02_safe_click_coordinate_bounds_validation(self):
        # 1. Manfiy yoki nol koordinata
        res1 = self.ctrl.safe_click(0, 0)
        self.assertFalse(res1["success"])
        self.assertEqual(res1["error"], "INVALID_COORDINATES")

        # 2. Oyna chegarasidan tashqaridagi nuqta rad etiladi
        with patch.object(self.ctrl, "verify_target_focus", return_value=(True, "VERIFIED")):
            res2 = self.ctrl.safe_click(950, 500, target=self.mock_target)
            self.assertFalse(res2["success"])
            self.assertEqual(res2["error"], "COORDINATES_OUTSIDE_TARGET_WINDOW")

        # 3. Oyna ichidagi to'g'ri nuqta bajariladi
        with patch.object(self.ctrl, "verify_target_focus", return_value=(True, "VERIFIED")), \
             patch("pyautogui.click") as mock_click, \
             patch("pyautogui.size", return_value=(1920, 1080)):
            res3 = self.ctrl.safe_click(300, 300, target=self.mock_target)
            self.assertTrue(res3["success"])
            self.assertEqual(res3["x"], 300)
            self.assertEqual(res3["y"], 300)
            self.assertTrue(res3["postcondition_verified"])
            mock_click.assert_called_once_with(300, 300)

    def test_03_safe_type_focus_and_target_verification(self):
        # 1. Target berilmagan bo'lsa rad etiladi
        res1 = self.ctrl.safe_type("Salom", target=None)
        self.assertFalse(res1["success"])
        self.assertEqual(res1["error"], "MISSING_TARGET_WINDOW")

        # 2. Target oyna fokusda bo'lmasa rad etiladi
        with patch.object(self.ctrl, "verify_target_focus", return_value=(False, "TARGET_WINDOW_NOT_FOCUSED")):
            res2 = self.ctrl.safe_type("Salom", target=self.mock_target)
            self.assertFalse(res2["success"])
            self.assertEqual(res2["error"], "PRECONDITION_FAILED: TARGET_WINDOW_NOT_FOCUSED")

        # 3. UAC yoki Elevated oyna bo'lsa rad etiladi
        elevated_target = WindowTarget(
            hwnd=1002,
            title="Administrator: Command Prompt",
            class_name="ConsoleWindowClass",
            pid=7777,
            rect=(50, 50, 600, 400),
            is_elevated=True,
            is_focused=True,
        )
        res3 = self.ctrl.safe_type("dir", target=elevated_target)
        self.assertFalse(res3["success"])
        self.assertIn("ELEVATED_WINDOW_OR_UAC_RESTRICTION", res3["error"])

        # 4. Fokuslangan to'g'ri oynaga xavfsiz yozish
        with patch.object(self.ctrl, "verify_target_focus", return_value=(True, "VERIFIED")), \
             patch("pyautogui.typewrite") as mock_typewrite:
            res4 = self.ctrl.safe_type("Misa AI Test", target=self.mock_target, interval=0.0)
            self.assertTrue(res4["success"])
            self.assertEqual(res4["typed_length"], 12)
            self.assertEqual(res4["target_window"], self.mock_target.title)
            self.assertTrue(res4["postcondition_verified"])

    def test_04_abort_signal_suppresses_further_input(self):
        self.ctrl.abort()
        self.assertTrue(self.ctrl.is_aborted)

        # Abort holatida click rad etiladi
        res_click = self.ctrl.safe_click(200, 200, target=self.mock_target)
        self.assertFalse(res_click["success"])
        self.assertEqual(res_click["error"], "ACTION_ABORTED")

        # Abort holatida type rad etiladi
        res_type = self.ctrl.safe_type("Hello", target=self.mock_target)
        self.assertFalse(res_type["success"])
        self.assertEqual(res_type["error"], "ACTION_ABORTED")

        # Reset abort
        self.ctrl.reset_abort()
        self.assertFalse(self.ctrl.is_aborted)

    def test_05_notepad_automation_workflow(self):
        """Notepad workflow: ochish -> fokuslash -> matn kiritish -> tekshirish -> yopish"""
        notepad_target = WindowTarget(
            hwnd=2001,
            title="Untitled - Notepad",
            class_name="Notepad",
            pid=9999,
            rect=(150, 150, 850, 650),
            is_elevated=False,
            is_focused=True,
        )

        with patch.object(self.ctrl, "find_window", return_value=notepad_target), \
             patch.object(self.ctrl, "focus_window", return_value=True), \
             patch.object(self.ctrl, "verify_target_focus", return_value=(True, "VERIFIED")), \
             patch("pyautogui.typewrite") as mock_type, \
             patch.object(self.ctrl, "close_window", return_value={"success": True, "closed": True}):

            # 1. Qidirish va topish
            found = self.ctrl.find_window("Notepad")
            self.assertIsNotNone(found)
            self.assertEqual(found.title, "Untitled - Notepad")

            # 2. Fokuslash
            focused = self.ctrl.focus_window(found)
            self.assertTrue(focused)

            # 3. Xavfsiz matn kiritish
            test_content = "Salom Misa AI v9.0.1"
            type_res = self.ctrl.safe_type(test_content, target=found, interval=0.0)
            self.assertTrue(type_res["success"])
            self.assertEqual(type_res["typed_length"], len(test_content))
            self.assertTrue(type_res["postcondition_verified"])

            # 4. Yopish
            close_res = self.ctrl.close_window(found)
            self.assertTrue(close_res["success"])
            self.assertTrue(close_res["closed"])

    def test_06_calculator_automation_workflow(self):
        """Calculator workflow: ochish -> fokuslash -> hisoblash kiritish -> tekshirish -> yopish"""
        calc_target = WindowTarget(
            hwnd=3001,
            title="Calculator",
            class_name="ApplicationFrameWindow",
            pid=8888,
            rect=(200, 200, 600, 700),
            is_elevated=False,
            is_focused=True,
        )

        with patch.object(self.ctrl, "find_window", return_value=calc_target), \
             patch.object(self.ctrl, "focus_window", return_value=True), \
             patch.object(self.ctrl, "verify_target_focus", return_value=(True, "VERIFIED")), \
             patch.object(self.ctrl, "safe_click", return_value={"success": True, "action": "click", "postcondition_verified": True}), \
             patch.object(self.ctrl, "safe_type", return_value={"success": True, "typed_length": 3, "postcondition_verified": True}), \
             patch.object(self.ctrl, "close_window", return_value={"success": True, "closed": True}):

            # 1. Qidirish
            calc = self.ctrl.find_window("Calculator")
            self.assertIsNotNone(calc)

            # 2. Fokuslash
            self.assertTrue(self.ctrl.focus_window(calc))

            # 3. '7' tugmasini bosish (Masalan markaziga click)
            click_res = self.ctrl.safe_click(300, 350, target=calc)
            self.assertTrue(click_res["success"])
            self.assertTrue(click_res["postcondition_verified"])

            # 4. Hisoblash ifodasini xavfsiz yozish
            type_res = self.ctrl.safe_type("+5=", target=calc)
            self.assertTrue(type_res["success"])
            self.assertTrue(type_res["postcondition_verified"])

            # 5. Yopish
            close_res = self.ctrl.close_window(calc)
            self.assertTrue(close_res["success"])


if __name__ == "__main__":
    unittest.main()
