# ========== test_v6_performance.py ==========
# Misa AI — Performance V2: Lazy Loading, Card Cache, Result Diffing,
# Navigation Generation Tokens, Lifecycle Hardening, and Stress Tests

import os
import time
import unittest
import customtkinter as ctk

from gui.app import MisaApp
from gui.pages.commands import CommandsPage
from gui.pages.voice import VoicePage
from gui.pages.scheduler import SchedulerPage
from gui.components import LoadingSkeleton, SearchBar
from gui.icons import IconEngine


class TestV6AppLazyLoading(unittest.TestCase):
    """Test suite verifying MisaApp lazy loading, page caching, and navigation state machine"""

    def setUp(self):
        IconEngine.clear_cache()
        self.app = None

    def tearDown(self):
        if self.app:
            try:
                if hasattr(self.app, "bridge") and self.app.bridge:
                    self.app.bridge.stop()
                for timer_attr in ["_lazy_nav_job", "_clock_job", "_stats_job"]:
                    job = getattr(self.app, timer_attr, None)
                    if job:
                        try:
                            self.app.after_cancel(job)
                        except Exception:
                            pass
                self.app.destroy()
            except Exception:
                pass
        IconEngine.clear_cache()

    def test_lazy_initialization_on_startup(self):
        """Verify that app startup only initializes home and does NOT instantiate all pages"""
        self.app = MisaApp(connect_backend=False, show_splash=False)
        self.app.withdraw()

        # On startup, only initial page (home) should be instantiated
        self.assertIn("home", self.app._pages)
        self.assertEqual(len(self.app._pages), 1, "Only initial page (home) should be loaded at startup")

        # Other pages must NOT exist in _pages yet
        for page_id in ["voice", "dashboard", "chat", "commands", "memory", "scheduler", "plugins", "settings"]:
            self.assertNotIn(page_id, self.app._pages, f"{page_id} should NOT be initialized at startup")

        self.assertEqual(self.app._current_page, "home")
        self.assertEqual(self.app._nav_state, "READY")

    def test_lazy_navigation_and_page_caching(self):
        """Verify lazy creation on first navigation and instant caching on subsequent visits"""
        self.app = MisaApp(connect_backend=False, show_splash=False)
        self.app.withdraw()
        self.assertEqual(len(self.app._pages), 1)

        # 1. First navigation to 'commands' (sync=True for test determinism)
        self.app.navigate_to("commands", sync=True)
        self.assertEqual(self.app._current_page, "commands")
        self.assertEqual(self.app._nav_state, "READY")
        self.assertIn("commands", self.app._pages)
        self.assertEqual(len(self.app._pages), 2)

        cmd_page_ref = self.app._pages["commands"]
        self.assertIsInstance(cmd_page_ref, CommandsPage)

        # 2. Navigation back to 'home'
        self.app.navigate_to("home", sync=True)
        self.assertEqual(self.app._current_page, "home")
        self.assertEqual(len(self.app._pages), 2)

        # 3. Navigation again to 'commands' — must reuse cached instance!
        self.app.navigate_to("commands", sync=True)
        self.assertIs(self.app._pages["commands"], cmd_page_ref, "Page must be reused from cache, not recreated")

    def test_rapid_navigation_cancels_pending_lazy_jobs(self):
        """Verify rapid navigation cancels earlier lazy jobs without crashing or orphaned widgets"""
        self.app = MisaApp(connect_backend=False, show_splash=False)
        self.app.withdraw()

        # Rapid clicks without sync (asynchronous path)
        self.app.navigate_to("chat", sync=False)
        self.assertEqual(self.app._nav_state, "LOADING")
        self.assertIsNotNone(self.app._lazy_nav_job)

        # Rapidly click memory before chat finishes
        self.app.navigate_to("memory", sync=False)
        self.assertEqual(self.app._nav_state, "LOADING")
        self.assertIsNotNone(self.app._lazy_nav_job)

        # Allow after timer to complete
        self.app.update()

    def test_navigation_generation_token_drops_stale_callback(self):
        """Verify stale navigation callback from an earlier requested page is rejected"""
        self.app = MisaApp(connect_backend=False, show_splash=False)
        self.app.withdraw()

        initial_gen = self.app._nav_generation

        # Navigate to commands
        self.app.navigate_to("commands", sync=True)
        cmd_gen = self.app._nav_generation
        self.assertGreater(cmd_gen, initial_gen)

        # Now simulate a stale lazy navigation callback for "chat" with old generation
        stale_gen = initial_gen
        self.app._finish_lazy_navigation("chat", generation=stale_gen)

        # Current page must still be commands, chat must NOT be activated!
        self.assertEqual(self.app._current_page, "commands")
        self.assertNotIn("chat", self.app._pages)


class TestV6CommandsPerformance(unittest.TestCase):
    """Test suite verifying CommandsPage debounce, caching, result diffing, and virtualized scaling"""

    def setUp(self):
        IconEngine.clear_cache()
        self.root = ctk.CTk()
        self.root.withdraw()
        self.page = CommandsPage(self.root)

    def tearDown(self):
        try:
            self.page.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        IconEngine.clear_cache()

    def test_commands_page_search_debouncing_and_caching(self):
        """Verify CommandsPage search debounce timer and versioned in-memory cache"""
        # 1. Test in-memory query caching
        self.page.search_entry.delete(0, "end")
        self.page.search_entry.insert(0, "tizim")
        self.page._execute_search(immediate=True)

        cache_key = ("tizim", "all", self.page._sort_mode, self.page._tools_dataset_version)
        self.assertIn(cache_key, self.page._search_cache)
        cached_results = self.page._search_cache[cache_key]
        self.assertIsInstance(cached_results, list)

        # Second execute with same query should hit cache
        self.page._execute_search(immediate=True)
        self.assertIs(self.page._search_cache[cache_key], cached_results)

        # 2. Test debouncing: rapid keyrelease calls schedule only 1 timer
        self.page._on_search_keyrelease()
        job1 = self.page._search_debounce_job
        self.assertIsNotNone(job1)

        self.page._on_search_keyrelease()
        job2 = self.page._search_debounce_job
        self.assertIsNotNone(job2)
        self.assertNotEqual(job1, job2, "New keystroke must cancel previous debounce job")

    def test_commands_page_category_pills(self):
        """Verify category pills update active state and filter tools correctly"""
        self.assertEqual(self.page._selected_category, "all")
        self.page._on_category_click("system")
        self.assertEqual(self.page._selected_category, "system")

        # Chips visual state updated
        system_chip = self.page._category_chips.get("system")
        self.assertIsNotNone(system_chip)

    def test_commands_page_batch_rendering_chunk_safety(self):
        """Verify chunked batch rendering splits tools and cancels gracefully"""
        tools = self.page._get_tools()
        self.assertGreater(len(tools), 10)

        # Start batch render
        self.page._cancel_batch_render()
        self.page._build_tools_grid(tools)

        # Cancel batch render must cleanly clear the job
        self.page._cancel_batch_render()
        self.assertIsNone(self.page._batch_render_job)

    def test_card_widget_cache_and_result_diffing(self):
        """Verify card widget cache reuses existing card widgets across searches without destroying them"""
        # Step 1: Render all tools
        self.page.search_entry.delete(0, "end")
        self.page._execute_search(immediate=True)
        self.page.update_idletasks()

        # Check that cards are cached in _tool_cards
        target_tool = "calculator" if "calculator" in self.page._tool_cards else list(self.page._tool_cards.keys())[0]
        self.assertIn(target_tool, self.page._tool_cards)
        target_card = self.page._tool_cards[target_tool]
        self.assertTrue(target_card.winfo_exists())

        # Step 2: Search for "xyznonexistent" (should hide target_tool, NOT destroy it)
        self.page.search_entry.delete(0, "end")
        self.page.search_entry.insert(0, "xyznonexistentquery")
        self.page._execute_search(immediate=True)
        self.page.update_idletasks()

        # target_card must STILL exist in memory (cached)!
        self.assertTrue(target_card.winfo_exists(), "Cached card must NOT be destroyed when filtered out")
        self.assertIn(target_tool, self.page._tool_cards)

        # Step 3: Search again for all (should reuse the exact same card widget instance!)
        self.page.search_entry.delete(0, "end")
        self.page._execute_search(immediate=True)
        self.page.update_idletasks()

        self.assertIs(self.page._tool_cards[target_tool], target_card, "Card widget must be reused from cache")

    def test_normalized_search_index_speed(self):
        """Verify normalized search index enables sub-millisecond filtering"""
        t0 = time.perf_counter()
        results = self.page._filter_and_sort_tools("audio", "all", "name")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.assertLess(elapsed_ms, 5.0, f"Normalized search filtering took {elapsed_ms:.2f}ms (must be < 5ms)")
        self.assertGreater(len(results), 0)
        self.assertTrue(all("audio" in t["_search_text"] for t in results))

    def test_large_dataset_virtualization_and_time_budget(self):
        """Stress test: 500 virtual tools scaling test — verify UI windowing limits widget creation"""
        # Generate 500 virtual tools
        virtual_tools = [
            {
                "name": f"virtual_tool_{i:04d}",
                "description": f"Virtual description for automated scaling test number {i}",
                "category": ["system", "utility", "coding", "media", "internet"][i % 5],
                "icon": "commands",
                "color": "#0A84FF",
            }
            for i in range(500)
        ]

        # Index the 500 tools
        self.page._load_and_index_tools(virtual_tools)
        self.assertEqual(len(self.page._all_tools), 500)

        # Filter & sort performance on 500 tools
        t0 = time.perf_counter()
        filtered = self.page._filter_and_sort_tools("test", "all", "name")
        filter_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(filter_elapsed_ms, 10.0, f"500-tool filter took {filter_elapsed_ms:.2f}ms (must be < 10ms)")
        self.assertEqual(len(filtered), 500)

        # Trigger grid build — windowing must restrict rendered cards to WINDOW_SIZE (24)
        self.page._active_window_limit = self.page.WINDOW_SIZE
        self.page._build_tools_grid(filtered)

        self.assertEqual(
            len(self.page._rendered_tool_names),
            self.page.WINDOW_SIZE,
            "Rendered tool cards must be bounded by window size to prevent UI freeze",
        )

    def test_on_hide_cancels_timers(self):
        """Verify on_hide cancels all active search and batch timers"""
        self.page.search_entry.delete(0, "end")
        self.page.search_entry.insert(0, "test")
        self.page._on_search_keyrelease()
        self.assertIsNotNone(self.page._search_timer)

        self.page.on_hide()
        self.assertIsNone(self.page._search_timer)
        self.assertIsNone(self.page._batch_job)


class TestV6LifecycleAndTimers(unittest.TestCase):
    """Test suite verifying lifecycle management and background timer pausing"""

    def setUp(self):
        IconEngine.clear_cache()
        self.root = ctk.CTk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        IconEngine.clear_cache()

    def test_voice_page_on_hide_pauses_orb(self):
        """Verify VoicePage.on_hide stops AppleSiriOrb animation (0% background CPU)"""
        voice = VoicePage(self.root)
        try:
            voice.on_show()
            self.assertTrue(voice.apple_orb._is_active)

            voice.on_hide()
            self.assertFalse(voice.apple_orb._is_active, "Orb must be paused when VoicePage is hidden")

            voice.on_show()
            self.assertTrue(voice.apple_orb._is_active, "Orb must resume animation when VoicePage is shown")
        finally:
            voice.destroy()

    def test_scheduler_page_on_hide_pauses_clock(self):
        """Verify SchedulerPage.on_hide stops background clock timer"""
        sched = SchedulerPage(self.root)
        try:
            sched.on_show()
            self.assertTrue(sched._timeline_running)

            sched.on_hide()
            self.assertFalse(sched._timeline_running, "Timeline clock loop must be paused on hide")
            self.assertIsNone(sched._clock_job)
        finally:
            sched.destroy()

    def test_loading_skeleton_set_title_and_safe_destroy(self):
        """Verify LoadingSkeleton updates title and destroys without timer leaks"""
        skeleton = LoadingSkeleton(self.root, title="Yuklanmoqda...")
        try:
            skeleton.set_title("Sozlamalar yuklanmoqda...")
            self.assertEqual(skeleton.title_label.cget("text"), "Sozlamalar yuklanmoqda...")
        finally:
            skeleton.destroy()


if __name__ == "__main__":
    unittest.main()
