# ========== test_v6_icon_engine.py ==========
# Misa AI v6.0.0 — Vector Icon Engine Professional Quality & Visual QA Tests

import os
import unittest
from PIL import Image, ImageDraw
import customtkinter as ctk

from gui.icons import (
    VectorIconEngine,
    get_vector_icon,
    compute_canvas_stroke,
    LOGICAL_GRID,
    SUPERSAMPLE_FACTOR,
    CANVAS_SIZE,
)


class TestVectorIconEngine(unittest.TestCase):
    """Production Vector Icon Engine unit and visual regression tests"""

    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()
        VectorIconEngine.clear_cache()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        VectorIconEngine.clear_cache()

    def test_constants_and_grid(self):
        self.assertEqual(LOGICAL_GRID, 24)
        self.assertEqual(SUPERSAMPLE_FACTOR, 4)
        self.assertEqual(CANVAS_SIZE, 96)
        self.assertGreaterEqual(len(VectorIconEngine.REGISTRY), 26)

    def test_compute_canvas_stroke(self):
        s16 = compute_canvas_stroke(16)
        s18 = compute_canvas_stroke(18)
        s20 = compute_canvas_stroke(20)
        s24 = compute_canvas_stroke(24)
        s32 = compute_canvas_stroke(32)

        # 16px -> 1.5px on target -> 1.5 * (96/16) = 9px on canvas
        self.assertEqual(s16, 9)
        # 24px -> 2.0px on target -> 2.0 * (96/24) = 8px on canvas
        self.assertEqual(s24, 8)
        # 32px -> 2.5px on target -> 2.5 * (96/32) = 7.5 -> 8px on canvas
        self.assertEqual(s32, 8)
        self.assertTrue(s16 >= 2 and s24 >= 2 and s32 >= 2)

    def test_all_26_canonical_icons_render(self):
        sizes = [16, 18, 20, 22, 24, 28, 32]
        for name in VectorIconEngine.REGISTRY:
            for sz in sizes:
                with self.subTest(icon=name, size=sz):
                    ctk_img = VectorIconEngine.get_image(name, size=sz)
                    self.assertIsNotNone(ctk_img)
                    self.assertEqual(ctk_img.cget("size"), (sz, sz))

                    light_img, dark_img = VectorIconEngine.get_pil_images(name, size=sz)
                    self.assertEqual(light_img.size, (sz, sz))
                    self.assertEqual(dark_img.size, (sz, sz))
                    self.assertEqual(light_img.mode, "RGBA")
                    self.assertEqual(dark_img.mode, "RGBA")

                    # Check that image is not blank (has visible pixels in alpha channel)
                    alpha_dark = dark_img.split()[3]
                    bbox = alpha_dark.getbbox()
                    self.assertIsNotNone(bbox, f"Icon {name} at size {sz} rendered completely transparent!")
                    # Bounding box should stay within canvas dimensions
                    self.assertTrue(bbox[0] >= 0 and bbox[1] >= 0)
                    self.assertTrue(bbox[2] <= sz and bbox[3] <= sz)

    def test_two_tier_caching_and_identity(self):
        # 1. CTkImage cache identity
        img1 = VectorIconEngine.get_image("dashboard", size=24, color_dark="#FFFFFF")
        img2 = VectorIconEngine.get_image("dashboard", size=24, color_dark="#FFFFFF")
        self.assertIs(img1, img2, "CTkImage should be reused directly from _CTK_CACHE")

        # 2. PIL Cache population
        key = ("dashboard", 24, "#FFFFFF", "#0F172A")
        self.assertIn(key, VectorIconEngine._PIL_CACHE)
        self.assertIn(key, VectorIconEngine._CTK_CACHE)

        # 3. Cache clearing
        VectorIconEngine.clear_cache()
        self.assertEqual(len(VectorIconEngine._PIL_CACHE), 0)
        self.assertEqual(len(VectorIconEngine._CTK_CACHE), 0)

    def test_semantic_aliases_and_legacy_fallbacks(self):
        test_cases = [
            ("✦", "sparkles"),
            ("★", "sparkles"),
            ("●", "circle"),
            ("•", "circle"),
            ("⚙", "settings"),
            ("⚙️", "settings"),
            ("🔍", "search"),
            ("💬", "chat"),
            ("mic", "mic"),
            ("microphone", "mic"),
            ("home", "dashboard"),
            ("trash-2", "trash"),
            ("delete", "trash"),
            ("x", "close"),
            ("check", "check"),
            ("plus", "plus"),
            ("add", "plus"),
            ("copy", "copy"),
            ("sparkles", "sparkles"),
            ("ai", "sparkles"),
            ("robot", "sparkles"),
            ("folder", "folder"),
            ("open", "folder"),
            ("eye", "eye"),
            ("view", "eye"),
            ("play", "play"),
            ("pause", "pause"),
            ("stop", "stop"),
            ("info", "info"),
            ("unknown_symbol_xyz", "sparkles"),
            (None, "sparkles"),
        ]
        for input_name, expected_resolved in test_cases:
            resolved = VectorIconEngine.resolve_icon_name(input_name)
            self.assertEqual(resolved, expected_resolved, f"Failed resolving {input_name}")
            # Verify get_vector_icon succeeds
            img = get_vector_icon(input_name, size=20)
            self.assertIsNotNone(img)

    def test_generate_visual_contact_sheet(self):
        """Generates a comprehensive high-resolution visual showcase PNG"""
        icons = list(sorted(VectorIconEngine.REGISTRY))
        sizes = [16, 20, 24, 32]
        header_h = 60
        row_h = 44

        # Columns: Icon Name (180px), 4 Dark Cards (50px each), Divider (25px), 4 Light Cards (50px each)
        total_w = 180 + len(sizes) * 50 + 25 + len(sizes) * 50 + 30
        total_h = header_h + len(icons) * row_h + 20

        sheet = Image.new("RGBA", (total_w, total_h), "#0F172A")
        draw = ImageDraw.Draw(sheet)

        # Draw Title
        draw.text((20, 14), "MISA AI — VECTOR ICON SYSTEM (CANONICAL 26)", fill="#F8FAFC")
        draw.text((20, 34), "Left: Dark Theme (#F8FAFC on #1E293B) | Right: Light Theme (#0F172A on #F1F5F9)", fill="#94A3B8")

        y = header_h
        for idx, icon_name in enumerate(icons):
            # Draw row background
            bg_color = "#162032" if (idx % 2 == 0) else "#0F172A"
            draw.rectangle([10, y, total_w - 10, y + row_h - 4], fill=bg_color)

            # Icon label
            draw.text((20, y + 14), icon_name, fill="#E2E8F0")

            # Dark theme cards
            x = 180
            for sz in sizes:
                card_bg = "#1E293B"
                draw.rounded_rectangle([x, y + 4, x + 40, y + 36], radius=4, fill=card_bg)
                _, dark_p = VectorIconEngine.get_pil_images(icon_name, size=sz, color_dark="#F8FAFC")
                offset = (40 - sz) // 2
                sheet.paste(dark_p, (x + offset, y + 4 + offset), dark_p)
                x += 50

            # Divider
            x += 8
            draw.line([x, y + 6, x, y + 34], fill="#334155", width=1)
            x += 16

            # Light theme cards
            for sz in sizes:
                card_bg = "#F1F5F9"
                draw.rounded_rectangle([x, y + 4, x + 40, y + 36], radius=4, fill=card_bg)
                light_p, _ = VectorIconEngine.get_pil_images(icon_name, size=sz, color_light="#0F172A")
                offset = (40 - sz) // 2
                sheet.paste(light_p, (x + offset, y + 4 + offset), light_p)
                x += 50

            y += row_h

        # Save to tests/icon_showcase.png
        out_path = os.path.join(os.path.dirname(__file__), "icon_showcase.png")
        sheet.save(out_path)
        self.assertTrue(os.path.exists(out_path))

        # Also copy to artifact dir for report embedding if configured in environment
        artifact_dir = os.environ.get("ANTIGRAVITY_ARTIFACT_DIR", "")
        if artifact_dir and os.path.isdir(artifact_dir):
            artifact_img = os.path.join(artifact_dir, "icon_showcase.png")
            sheet.save(artifact_img)
            print(f"\n[QA] Copied showcase to artifact: {artifact_img}")

        print(f"\n[QA] Generated icon showcase: {out_path}")


if __name__ == "__main__":
    unittest.main()
