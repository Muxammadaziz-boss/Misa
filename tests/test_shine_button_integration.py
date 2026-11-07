import os
import re

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_shine_button_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\ShineButton.tsx")
    assert os.path.isfile(path), f"ShineButton.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "export const ShineButton" in content
    assert "misa-shine-btn" in content
    assert "misa-shine-icon" in content
    assert "misa-shine-label" in content


def test_globals_css_has_shine_button_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".misa-shine-btn" in content
    assert "border-radius: 9999px" in content
    assert "misaShineTravel" in content
    assert "@keyframes misaShineTravel" in content
    assert ".misa-shine-icon" in content
    assert "translateX(4px)" in content
    assert "scale(1.04)" in content or "scale(1.03)" in content or "scale(1.05)" in content
    assert "prefers-reduced-motion" in content


def test_button_component_supports_shine():
    path = os.path.join(BASE_DIR, r"Misa\src\components\Button.tsx")
    assert os.path.isfile(path), f"Button.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "misa-shine-btn" in content
    assert "misa-shine-icon" in content


def test_auth_page_uses_shine_buttons():
    path = os.path.join(BASE_DIR, r"Misa\src\pages\AuthPage.tsx")
    assert os.path.isfile(path), f"AuthPage.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "misa-shine-btn" in content


def test_chat_page_uses_shine_button_for_new_chat():
    path = os.path.join(BASE_DIR, r"Misa\src\pages\ChatPage.tsx")
    assert os.path.isfile(path), f"ChatPage.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "misa-shine-btn" in content
