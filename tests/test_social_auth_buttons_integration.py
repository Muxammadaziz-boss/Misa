import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_social_auth_buttons_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\SocialAuthButtons.tsx")
    assert os.path.isfile(path), f"SocialAuthButtons.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "export const SocialAuthButtons" in content
    assert "misa-social-circle-btn" in content
    assert "misa-social-circle-google" in content
    assert "misa-social-circle-github" in content
    assert "misa-social-circle-telegram" in content
    assert "Continue with Google" in content
    assert "Continue with GitHub" in content
    assert "Continue with Telegram" in content


def test_globals_css_has_social_circle_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".misa-social-circle-btn" in content
    assert "border-radius: 50%" in content
    assert ".misa-social-circle-tooltip" in content
    assert ".misa-social-circle-google" in content
    assert ".misa-social-circle-github" in content
    assert ".misa-social-circle-telegram" in content
    assert "scale(1.08)" in content or "scale(1.0" in content
    assert "prefers-reduced-motion" in content


def test_auth_page_uses_social_auth_buttons():
    path = os.path.join(BASE_DIR, r"Misa\src\pages\AuthPage.tsx")
    assert os.path.isfile(path), f"AuthPage.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SocialAuthButtons" in content
    assert "handleOAuthSignIn" in content
    assert "handleOpenTelegramLogin" in content
