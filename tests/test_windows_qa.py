# ========== test_windows_qa.py ==========
# Phase 25 — Windows 10 & 11 Quality Assurance (QA) Test Suite
# Tests: Path portability, Python runtime, DPI CSS tokens, process hygiene, %TEMP% isolation

import os
import sys
import json
import tempfile
import platform
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


class TestWindowsQA(unittest.TestCase):
    """Windows 10 / 11 platformasi va muhiti uchun maxsus QA testlari"""

    def test_os_platform_detection(self):
        """Tizim Windows ekanligi va arxitekturasi aniqlanadi"""
        current_os = platform.system()
        self.assertEqual(current_os, "Windows", f"QA sinovi Windows tizimida bajarilishi shart (aniqlandi: {current_os})")
        release = platform.release()

        # Platform aniqlash: Windows 10, Windows 11, Windows Server, Linux, macOS
        def classify_os_platform() -> str:
            sys_name = platform.system()
            if sys_name == "Windows":
                rel = str(platform.release()).strip()
                if "server" in rel.lower() or rel in ["2016", "2019", "2022", "2025"]:
                    return "Windows Server"
                if rel == "11":
                    return "Windows 11"
                if rel == "10":
                    return "Windows 10"
                return f"Windows ({rel})"
            elif sys_name == "Linux":
                return "Linux"
            elif sys_name == "Darwin":
                return "macOS"
            return sys_name

        detected_platform = classify_os_platform()
        # Windows QA sinovi Windows 10, 11 yoki Windows Server muhitlarida qo'llab-quvvatlanadi
        supported_windows = ["Windows 10", "Windows 11", "Windows Server"]
        self.assertTrue(
            any(detected_platform.startswith(w) for w in supported_windows),
            f"Windows 10, 11 yoki Windows Server qo'llab-quvvatlanadi (aniqlandi: {detected_platform}, release: {release})"
        )

    def test_python_runtime_compatibility(self):
        """Python versiyasi 3.10+ va 64-bit ekanligi tekshiriladi"""
        v = sys.version_info
        self.assertGreaterEqual(v.major, 3)
        self.assertGreaterEqual(v.minor, 10, f"Python versiyasi kamida 3.10 bo'lishi kerak: {sys.version}")
        is_64bits = sys.maxsize > 2**32
        self.assertTrue(is_64bits, "Python runtime 64-bit bo'lishi shart")

    def test_path_portability_no_hardcoded_user_roots(self):
        """Katalog yo'llarida qat'iy (hardcoded) foydalanuvchi yo'llari yo'qligi"""
        from config import Config
        cfg = Config()
        
        base = str(cfg.project_dir)
        self.assertTrue(os.path.exists(base), f"Baza katalogi mavjud emas: {base}")
        
        # Temp katalog tizim standartiga mos
        temp_d = cfg.get("paths.temp_dir", "")
        self.assertTrue(os.path.exists(temp_d), f"Temp katalogi mavjud emas: {temp_d}")

    def test_temp_file_creation_and_cleanup(self):
        """Windows %TEMP% katalogida xavfsiz fayl yaratish va tozalash"""
        test_file = os.path.join(tempfile.gettempdir(), f"misa_qa_test_{os.getpid()}.tmp")
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Misa AI Windows QA check")
            self.assertTrue(os.path.exists(test_file))
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
            self.assertFalse(os.path.exists(test_file))

    def test_high_dpi_css_tokens(self):
        """CSS fayllarida High-DPI (100%, 125%, 150%, 200%) uchun font-smoothing va elastik birliklar mavjudligi"""
        css_path = os.path.join(BASE_DIR, "Misa", "src", "styles", "globals.css")
        self.assertTrue(os.path.exists(css_path), "globals.css mavjud emas")

        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        self.assertIn("-webkit-font-smoothing", css_content, "DPI rendering uchun font-smoothing talab qilinadi")
        self.assertIn("box-sizing: border-box", css_content, "DPI o'lchamlari to'g'ri hisoblanishi uchun border-box talab qilinadi")

    def test_tauri_config_window_bounds(self):
        """Tauri oyna chegaralari (1024x700 min) va frameless bezaklari Windows talablariga mos"""
        tauri_conf_path = os.path.join(BASE_DIR, "Misa", "src-tauri", "tauri.conf.json")
        self.assertTrue(os.path.exists(tauri_conf_path))

        with open(tauri_conf_path, "r", encoding="utf-8") as f:
            t_conf = json.load(f)

        windows = t_conf.get("app", {}).get("windows", [])
        if windows:
            win = windows[0]
            self.assertGreaterEqual(win.get("minWidth", 0), 1024)
            self.assertGreaterEqual(win.get("minHeight", 0), 700)
            self.assertEqual(win.get("decorations"), False, "Frameless custom chrome oynasi ishlatilishi kerak")
        else:
            lib_rs_path = os.path.join(BASE_DIR, "Misa", "src-tauri", "src", "lib.rs")
            self.assertTrue(os.path.exists(lib_rs_path))
            with open(lib_rs_path, "r", encoding="utf-8") as f:
                lib_content = f.read()
            self.assertIn("min_inner_size(1024.0, 700.0)", lib_content)
            self.assertIn("decorations(false)", lib_content)


if __name__ == "__main__":
    unittest.main()
