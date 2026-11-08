"""Tests to verify:
1. Removal of post-intro blocking loading screen in App.tsx
2. Persistent portable session restoration in backendService.ts and App.tsx
3. Portable launcher data folder and session preservation in package_release.cjs
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_no_blocking_auth_loader_after_intro():
    app_tsx = os.path.join(BASE_DIR, "Misa", "src", "App.tsx")
    with open(app_tsx, "r", encoding="utf-8") as f:
        code = f.read()

    # introActive should be an overlay, not a blocking early return that unmounts the app
    assert "{introActive && (" in code or "introActive && <MisaIntroSplash" in code
    # authChecking full-page loader should not block rendering
    assert "if (authChecking) {" not in code
    assert "Misa AI v9.4 ishga tushirilmoqda..." not in code


def test_portable_session_user_persistence():
    backend_service = os.path.join(BASE_DIR, "Misa", "src", "services", "backendService.ts")
    with open(backend_service, "r", encoding="utf-8") as f:
        code = f.read()

    # getCurrentAuthUser must check misa_user_data
    assert "misa_user_data" in code
    assert "localStorage.getItem(\"misa_user_data\")" in code


def test_portable_package_session_persistence():
    package_script = os.path.join(BASE_DIR, "Misa", "scripts", "package_release.cjs")
    with open(package_script, "r", encoding="utf-8") as f:
        code = f.read()

    # WEBVIEW2_USER_DATA_FOLDER must be configured for portable
    assert "WEBVIEW2_USER_DATA_FOLDER" in code
    assert "config.json" in code
