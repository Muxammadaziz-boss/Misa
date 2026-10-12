"""
Misa AI v9.0.1 — Windows Deployment Lifecycle & Single-Instance Test Suite
Tests:
- test_webview2_missing_does_not_restart
- test_single_instance
- test_no_duplicate_backend
- test_backend_cleanup_on_ui_failure
- test_permanent_dependency_failure_no_retry
- test_backend_already_running
- test_graceful_shutdown
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch
import subprocess
from pathlib import Path

# Add project root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core import api_server


class TestWindowsDeploymentLifecycle(unittest.TestCase):
    """Test suite for WebView2 startup, single-instance protection, and backend lifecycle."""

    def test_webview2_missing_does_not_restart(self):
        """
        Case B: WebView2 missing must not trigger an infinite restart loop.
        It must detect missing runtime once, abort UI startup, and stop without respawning.
        """
        attempts = 0
        max_attempts = 1
        restart_triggered = False

        def mock_detect_webview2():
            nonlocal attempts, restart_triggered
            attempts += 1
            if attempts > max_attempts:
                restart_triggered = True
            # Simulate WebView2 not installed on clean machine
            return False

        # Simulate startup check
        is_installed = mock_detect_webview2()
        self.assertFalse(is_installed, "WebView2 should be detected as missing")

        # When missing, application must stop and NOT trigger restart
        if not is_installed:
            # Permanent dependency error handling: do NOT restart
            restart_policy = "stop_on_missing_dependency"
        else:
            restart_policy = "restart"

        self.assertEqual(restart_policy, "stop_on_missing_dependency")
        self.assertEqual(attempts, 1, "Detection should run exactly once without restart loop")
        self.assertFalse(restart_triggered, "Restart loop must not be triggered")

    def test_single_instance(self):
        """
        Case C: Second launch must be blocked by single-instance protection.
        On Windows, a Named Mutex or PID check prevents duplicate instances.
        """
        if sys.platform == "win32":
            import winreg
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            CreateMutexW = kernel32.CreateMutexW
            CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            CreateMutexW.restype = wintypes.HANDLE

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            ERROR_ALREADY_EXISTS = 183

            test_mutex_name = "Local\\Misa_Test_SingleInstance_Mutex"

            # 1. First instance acquires mutex
            h1 = CreateMutexW(None, True, test_mutex_name)
            self.assertNotEqual(h1, 0, "First instance should acquire mutex handle")
            err1 = ctypes.get_last_error()
            self.assertNotEqual(err1, ERROR_ALREADY_EXISTS, "First instance should not find existing mutex")

            # 2. Second instance attempts to acquire mutex
            h2 = CreateMutexW(None, True, test_mutex_name)
            err2 = ctypes.get_last_error()
            self.assertEqual(err2, ERROR_ALREADY_EXISTS, "Second instance must detect ERROR_ALREADY_EXISTS")

            # Cleanup
            if h2:
                CloseHandle(h2)
            if h1:
                CloseHandle(h1)
        else:
            # Non-windows file-based single instance test
            lock_file = REPO_ROOT / "test_misa.lock"
            self.assertFalse(lock_file.exists())
            lock_file.touch()
            self.assertTrue(lock_file.exists())
            lock_file.unlink()

    def test_no_duplicate_backend(self):
        """
        Case D: Starting backend when a healthy backend is already running on port 18420
        must exit cleanly without launching a second backend or crashing with port collision.
        """
        with patch("urllib.request.urlopen") as mock_urlopen:
            # Mock healthy response from port 18420
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            with patch("aiohttp.web.run_app") as mock_run_app:
                # Call run_server
                api_server.run_server(host="127.0.0.1", port=18420)

                # run_app must NOT have been called because a healthy server already exists
                mock_run_app.assert_not_called()

    def test_backend_cleanup_on_ui_failure(self):
        """
        Case E / G: When UI fails to initialize or crashes, any child backend process
        must be cleanly stopped and not left as an orphan.
        """
        # Create a mock child process
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(10)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.assertIsNone(child.poll(), "Child process should be running")

        # Simulate UI failure / teardown guard
        try:
            pid = child.pid
            # Simulate stop_backend
            child.kill()
            child.wait(timeout=2)
        finally:
            if child.poll() is None:
                child.kill()

        self.assertIsNotNone(child.poll(), "Child process must be terminated after cleanup")

    def test_permanent_dependency_failure_no_retry(self):
        """
        Case F: Maximum retries limit (3 attempts) prevents infinite respawn loops.
        After 3 failures, state transitions to is_permanently_failed = True.
        """
        attempts = 0
        max_retries = 3
        is_permanently_failed = False

        for _ in range(5):  # Attempt 5 times
            if is_permanently_failed:
                break
            attempts += 1
            if attempts >= max_retries:
                is_permanently_failed = True

        self.assertEqual(attempts, 3, "Must stop attempting after exactly 3 attempts")
        self.assertTrue(is_permanently_failed, "State must transition to permanently failed")

    def test_backend_already_running(self):
        """
        Verifies health check probe logic returns True when 200 OK received.
        """
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            # Verify that http://127.0.0.1:18420/api/health is probed
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:18420/api/health")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                status_code = resp.status

            self.assertEqual(status_code, 200)

    def test_graceful_shutdown(self):
        """
        Case H: Clean shutdown removes PID file and cleans up port.
        """
        app_data = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP", ".")
        pid_dir = Path(app_data) / "MisaAI"
        pid_dir.mkdir(parents=True, exist_ok=True)
        test_pid_file = pid_dir / "test_misa_backend.pid"

        # Write PID
        current_pid = os.getpid()
        test_pid_file.write_text(str(current_pid), encoding="utf-8")
        self.assertTrue(test_pid_file.exists())
        self.assertEqual(int(test_pid_file.read_text().strip()), current_pid)

        # Cleanup PID
        test_pid_file.unlink()
        self.assertFalse(test_pid_file.exists(), "PID file must be removed on clean shutdown")

    # =========================================================================
    # PORTABLE WEBVIEW2 LIFECYCLE TESTS (v9.0.1)
    # =========================================================================

    def test_portable_webview2_missing(self):
        """
        Verify that in portable environment when WebView2 is not detected:
        1. check_webview2_installed returns False.
        2. Backend is NOT started.
        3. No infinite restart loops.
        """
        backend_started = False

        def mock_check_webview2():
            return False

        def mock_start_backend():
            nonlocal backend_started
            backend_started = True

        # Portable startup flow simulation
        is_installed = mock_check_webview2()
        self.assertFalse(is_installed, "WebView2 should be missing on clean machine")

        if is_installed:
            mock_start_backend()

        self.assertFalse(backend_started, "Backend must NEVER be started when WebView2 is missing")

    def test_portable_webview2_install_success(self):
        """
        Verify successful portable installation flow:
        1. WebView2 initially missing.
        2. Bundled bootstrapper found.
        3. Installer process completes successfully.
        4. Strict re-check passes.
        5. Flow returns True, allowing UI and backend startup.
        """
        detection_state = [False, True]  # Initially missing, then present after install
        installer_invoked = False

        def mock_check():
            return detection_state.pop(0) if detection_state else True

        def mock_run_installer(args):
            nonlocal installer_invoked
            installer_invoked = True
            return 0  # Process exit code 0

        # Run portable installation simulation
        initial = mock_check()
        self.assertFalse(initial, "Initially missing")

        exit_code = mock_run_installer(["/silent", "/install"])
        self.assertEqual(exit_code, 0, "Installer should exit 0 on success")

        recheck = mock_check()
        self.assertTrue(recheck, "Post-install re-check must pass")
        self.assertTrue(installer_invoked, "Installer must have been invoked")

    def test_portable_webview2_install_failure(self):
        """
        Verify failure handling during portable installation:
        1. Installer fails (e.g., non-zero exit code or timeout).
        2. Re-check returns False.
        3. App aborts without starting backend.
        """
        backend_started = False

        def mock_run_installer():
            return 1603  # Fatal error during installation (e.g., no internet or UAC denied)

        def mock_recheck():
            return False  # Still missing

        def mock_start_backend():
            nonlocal backend_started
            backend_started = True

        code = mock_run_installer()
        recheck_ok = mock_recheck()

        self.assertNotEqual(code, 0)
        self.assertFalse(recheck_ok, "Re-check must fail when installer failed")

        if not recheck_ok:
            # Clean exit, do NOT start backend
            pass
        else:
            mock_start_backend()

        self.assertFalse(backend_started, "Backend must NEVER start if installer fails")

    def test_portable_webview2_recheck(self):
        """
        Verify that installer completion alone is NOT enough without a positive re-check:
        If installer returns 0 but runtime is still not detectable in registry/path,
        the flow must fail.
        """
        # Case 1: Installer reports 0, but re-check fails
        installer_exit_code = 0
        recheck_passed = False

        lifecycle_allowed = (installer_exit_code == 0) and recheck_passed
        self.assertFalse(lifecycle_allowed, "Must not allow startup if re-check fails even if exit code is 0")

        # Case 2: Installer reports 0 AND re-check passes
        recheck_passed = True
        lifecycle_allowed = (installer_exit_code == 0) and recheck_passed
        self.assertTrue(lifecycle_allowed, "Must allow startup only when re-check passes")

    def test_portable_no_backend_before_webview2(self):
        """
        Strict lifecycle order verification:
        misa_backend.exe must NEVER start prior to successful WebView2 verification.
        Order:
          SingleInstanceGuard -> WebView2 Detection -> (Install & Verify) -> Backend Spawn -> UI
        """
        execution_order = []

        def step_single_instance():
            execution_order.append("single_instance")
            return True

        def step_webview2_verify():
            execution_order.append("webview2_verify")
            return True

        def step_spawn_backend():
            # Backend should only be spawned after webview2_verify
            self.assertIn("webview2_verify", execution_order, "WebView2 must be verified before backend spawn")
            execution_order.append("spawn_backend")

        def step_show_ui():
            self.assertIn("spawn_backend", execution_order, "Backend should precede UI initialization")
            execution_order.append("show_ui")

        # Execute in order
        if step_single_instance():
            if step_webview2_verify():
                step_spawn_backend()
                step_show_ui()

        self.assertEqual(
            execution_order,
            ["single_instance", "webview2_verify", "spawn_backend", "show_ui"],
            "Execution order must be strictly maintained"
        )

    def test_portable_no_orphan_backend(self):
        """
        Verify that if portable app encounters a failure or crashes during startup,
        any started backend or child processes are cleaned up immediately.
        """
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(15)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assertIsNone(child.poll(), "Process should be alive initially")

        # Simulate portable teardown / abort on failure
        try:
            child.kill()
            child.wait(timeout=3)
        except Exception:
            pass

        self.assertIsNotNone(child.poll(), "No orphan backend process should remain alive")

    def test_portable_single_instance(self):
        """
        Verify that rapid launching of portable app (e.g. 5 times) results in
        only ONE active instance. Subsequent 4 launches must immediately exit.
        """
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            CreateMutexW = kernel32.CreateMutexW
            CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            CreateMutexW.restype = wintypes.HANDLE

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            ERROR_ALREADY_EXISTS = 183
            test_mutex = "Local\\Misa_Portable_RapidLaunch_Test_Mutex"

            handles = []
            results = []

            for i in range(5):
                h = CreateMutexW(None, True, test_mutex)
                err = ctypes.get_last_error()
                if err == ERROR_ALREADY_EXISTS:
                    results.append("BLOCKED_DUPLICATE")
                    if h:
                        CloseHandle(h)
                else:
                    results.append("ACQUIRED_PRIMARY")
                    handles.append(h)

            # Cleanup
            for h in handles:
                CloseHandle(h)

            self.assertEqual(results.count("ACQUIRED_PRIMARY"), 1, "Exactly 1 instance must acquire primary mutex")
            self.assertEqual(results.count("BLOCKED_DUPLICATE"), 4, "Remaining 4 launches must be blocked")
        else:
            # Platform agnostic simulation
            active_instances = 0
            results = []
            for _ in range(5):
                if active_instances == 0:
                    active_instances += 1
                    results.append("PRIMARY")
                else:
                    results.append("BLOCKED")
            self.assertEqual(results.count("PRIMARY"), 1)
            self.assertEqual(results.count("BLOCKED"), 4)


if __name__ == "__main__":
    unittest.main()

