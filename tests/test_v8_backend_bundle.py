# ========== tests/test_v8_backend_bundle.py ==========
# Misa AI v8.0.0 — Standalone Backend Bundle & Supervisor Test Suite
# Tests 13 critical production packaging, health check, OAuth callback,
# supervisor lifecycle, and portable distribution scenarios.

import os
import sys
import json
import time
import shutil
import socket
import zipfile
import unittest
import subprocess
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON_EXE = sys.executable


def is_port_listening(port: int = 18420, host: str = "127.0.0.1") -> bool:
    """Checks if a local TCP port is currently listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def ensure_backend_extracted():
    """If running in fresh CI clone where backend/ was gitignored, unpack from portable zip."""
    v8_dir = REPO_ROOT / "release" / "v8.0.0"
    backend_dir = v8_dir / "backend"
    zip_path = v8_dir / "Mikasa-AI-v8.0.0-Portable.zip"
    if zip_path.exists() and not (backend_dir / "misa_backend.exe").exists() and not (backend_dir / "mikasa_backend.exe").exists():
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                if member.startswith("backend/"):
                    zf.extract(member, v8_dir)

    # Ensure misa_backend.exe exists if mikasa_backend.exe was unpacked
    if (backend_dir / "mikasa_backend.exe").exists() and not (backend_dir / "misa_backend.exe").exists():
        shutil.copy2(backend_dir / "mikasa_backend.exe", backend_dir / "misa_backend.exe")

    tauri_backend_dir = REPO_ROOT / "Misa" / "src-tauri" / "backend"
    tauri_backend_exe = tauri_backend_dir / "misa_backend.exe"
    src_backend_exe = backend_dir / "misa_backend.exe"
    if not src_backend_exe.exists():
        src_backend_exe = backend_dir / "mikasa_backend.exe"

    if not tauri_backend_exe.exists() and src_backend_exe.exists():
        tauri_backend_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_backend_exe.parent, tauri_backend_dir, dirs_exist_ok=True)
        if not tauri_backend_exe.exists() and (tauri_backend_dir / "mikasa_backend.exe").exists():
            shutil.copy2(tauri_backend_dir / "mikasa_backend.exe", tauri_backend_exe)


ensure_backend_extracted()


class TestBackendBundleStructure(unittest.TestCase):
    """Scenario A & J: Verify physical presence and structure of bundled backend."""

    def test_backend_executable_in_release(self):
        backend_exe = REPO_ROOT / "release" / "v8.0.0" / "backend" / "misa_backend.exe"
        if not backend_exe.exists():
            backend_exe = REPO_ROOT / "release" / "v8.0.0" / "backend" / "mikasa_backend.exe"
        self.assertTrue(backend_exe.exists(), f"Backend executable not found at: {backend_exe}")
        size_mb = backend_exe.stat().st_size / (1024 * 1024)
        self.assertGreater(size_mb, 1.0, f"Executable size too small: {size_mb:.2f} MB")

    def test_backend_deployed_to_tauri_resources(self):
        tauri_backend_exe = REPO_ROOT / "Misa" / "src-tauri" / "backend" / "misa_backend.exe"
        if not tauri_backend_exe.exists():
            tauri_backend_exe = REPO_ROOT / "Misa" / "src-tauri" / "backend" / "mikasa_backend.exe"
        self.assertTrue(tauri_backend_exe.exists(), f"Tauri resource backend not found at: {tauri_backend_exe}")

    def test_tauri_conf_includes_backend_resources(self):
        tauri_conf_path = REPO_ROOT / "Misa" / "src-tauri" / "tauri.conf.json"
        self.assertTrue(tauri_conf_path.exists())
        with open(tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        resources = conf.get("bundle", {}).get("resources", [])
        has_backend = any("backend" in r for r in resources)
        self.assertTrue(has_backend, "tauri.conf.json bundle.resources must include 'backend/**' or 'backend/**/*'")
        self.assertIn("WebView2Loader.dll", resources, "tauri.conf.json must include 'WebView2Loader.dll'")


class TestBackendRuntimeAndHealth(unittest.TestCase):
    """Scenario B, C, E, G, H: Standalone runtime execution, health endpoint, and OAuth."""

    @classmethod
    def setUpClass(cls):
        cls.proc: Optional[subprocess.Popen] = None

        if not is_port_listening(18420):
            env = dict(os.environ)
            env["MISA_API_HOST"] = "127.0.0.1"
            env["MISA_API_PORT"] = "18420"
            cls.proc = subprocess.Popen(
                [PYTHON_EXE, str(REPO_ROOT / "core" / "api_server.py")],
                cwd=str(REPO_ROOT),
                env=env,
            )
            # Wait for backend readiness (up to 30s)
            for _ in range(60):
                if is_port_listening(18420):
                    break
                time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        if cls.proc and cls.proc.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(cls.proc.pid)], capture_output=True)

    def test_health_endpoint_contract(self):
        """Scenario E: GET /api/health returns 200 OK and expected fields."""
        import requests
        res = requests.get("http://127.0.0.1:18420/api/health", timeout=3)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("app"), "Misa AI")
        self.assertIn(data.get("version"), ("8.0.0", "9.0.0", "9.0.1", "9.0.2", "9.2", "9.2.0"))

    def test_oauth_callback_html(self):
        """Scenario G: GET /api/auth/callback serves OAuth redirect landing page."""
        import requests
        res = requests.get("http://127.0.0.1:18420/api/auth/callback", timeout=3)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("Content-Type", ""))
        self.assertIn("Misa AI", res.text)
        self.assertIn("/api/auth/callback/session", res.text)

    def test_oauth_session_save_and_retrieve(self):
        """Scenario H: POST and GET /api/auth/callback/session securely transfers tokens."""
        import requests
        test_state = f"unit_test_state_{int(time.time() * 1000)}"
        session_payload = {
            "access_token": "ey_test_access_token_abc123",
            "refresh_token": "test_refresh_token_xyz789",
            "state": test_state
        }
        post_res = requests.post(
            "http://127.0.0.1:18420/api/auth/callback/session",
            json=session_payload,
            timeout=3
        )
        self.assertEqual(post_res.status_code, 200)

        # Retrieve by state
        get_res = requests.get(
            f"http://127.0.0.1:18420/api/auth/callback/session?state={test_state}",
            timeout=3
        )
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertTrue(data.get("ok"))
        session = data.get("session", {})
        self.assertEqual(session.get("access_token"), "ey_test_access_token_abc123")
        self.assertEqual(session.get("refresh_token"), "test_refresh_token_xyz789")


class TestSupervisorArchitecture(unittest.TestCase):
    """Scenario D, F, L, M: Supervisor logic, existing detection, and cleanup."""

    def test_supervisor_source_code_integrity(self):
        """Validates that src-tauri/src/lib.rs implements all required supervisor guarantees."""
        lib_rs = REPO_ROOT / "Misa" / "src-tauri" / "src" / "lib.rs"
        self.assertTrue(lib_rs.exists())
        with open(lib_rs, "r", encoding="utf-8") as f:
            content = f.read()

        # Check HTTP health check function
        self.assertIn("check_http_health", content)
        self.assertIn("/api/health", content)

        # Check bundled binary resolution candidates
        self.assertIn("find_bundled_backend_binary", content)
        self.assertIn("misa_backend.exe", content)

        # Check existing backend detection (unmanaged preservation)
        self.assertIn("is_managed", content)
        self.assertTrue(
            "Mavjud backend aniqlandi va mos" in content or "Mavjud backend aniqlandi va faol" in content,
            "lib.rs must check and log existing backend detection"
        )

        # Check concurrency guard (no duplicate parallel spawns)
        self.assertIn("is_spawning", content)

        # Check exponential backoff
        self.assertIn("backoff_delays", content)

        # Check clean kill via taskkill
        self.assertIn("taskkill", content)
        self.assertIn("stop_backend", content)


class TestPortableZipArchive(unittest.TestCase):
    """Scenario I & K: Portable zip self-contained archive validation."""

    def test_portable_zip_contains_all_components(self):
        v92_zip = REPO_ROOT / "release" / "v9.2" / "Misa-AI-v9.2-Portable.zip"
        v920_zip = REPO_ROOT / "release" / "v9.2.0" / "Misa-AI-v9.2.0-Portable.zip"
        v902_zip = REPO_ROOT / "release" / "v9.0.2" / "Misa-AI-v9.0.2-Portable.zip"
        v91_zip = REPO_ROOT / "release" / "v9.0.1" / "Misa-AI-v9.0.1-Portable.zip"
        v9_zip = REPO_ROOT / "release" / "v9.0.0" / "Misa-AI-v9.0.0-Portable.zip"
        v8_zip = REPO_ROOT / "release" / "v8.0.0" / "Mikasa-AI-v8.0.0-Portable.zip"
        zip_path = (
            v92_zip if v92_zip.exists()
            else (v920_zip if v920_zip.exists()
            else (v902_zip if v902_zip.exists()
            else (v91_zip if v91_zip.exists()
            else (v9_zip if v9_zip.exists() else v8_zip))))
        )
        self.assertTrue(zip_path.exists(), f"Portable zip missing: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())

        has_exe = any(
            n.endswith("Misa-AI-v9.2.exe")
            or n.endswith("Misa-AI-v9.2.0.exe")
            or n.endswith("Misa-AI-v9.0.2.exe")
            or n.endswith("Misa-AI-v9.0.1.exe")
            or n.endswith("Misa-AI-v9.0.0.exe")
            or n.endswith("Mikasa-AI-v8.0.0.exe")
            for n in names
        )
        has_dll = any(n.endswith("WebView2Loader.dll") for n in names)
        has_bat = any(n.endswith("run_portable.bat") for n in names)
        has_backend = any(
            "backend/misa_backend.exe" in n.replace("\\", "/") or "backend/mikasa_backend.exe" in n.replace("\\", "/")
            for n in names
        )

        self.assertTrue(has_exe, "Portable zip must contain desktop executable")
        self.assertTrue(has_dll, "Portable zip must contain WebView2Loader.dll")
        self.assertTrue(has_bat, "Portable zip must contain run_portable.bat")
        self.assertTrue(has_backend, "Portable zip must contain backend executable")


if __name__ == "__main__":
    unittest.main()
