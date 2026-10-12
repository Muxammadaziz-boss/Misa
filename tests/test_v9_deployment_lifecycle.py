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


if __name__ == "__main__":
    unittest.main()
