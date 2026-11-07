import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_theme_switch_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\ThemeSwitch.tsx")
    assert os.path.isfile(path), f"ThemeSwitch.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "ThemeSwitch" in c
    assert "misa-theme-switch-track" in c
    assert "misa-theme-switch-thumb" in c
    assert "misa-theme-switch-stars" in c
    assert "misa-theme-switch-clouds" in c
    assert "role=\"switch\"" in c or "role='switch'" in c
    assert "aria-label" in c


def test_globals_css_has_theme_switch_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert ".misa-theme-switch-track" in c
    assert ".misa-theme-switch-thumb" in c
    assert ".misa-theme-switch-stars" in c
    assert ".misa-theme-switch-clouds" in c
    assert "theme-light" in c
    assert "prefers-reduced-motion" in c


def test_theme_switch_integrated_in_account_page():
    acc_path = os.path.join(BASE_DIR, r"Misa\src\pages\AccountPage.tsx")
    assert os.path.isfile(acc_path), f"AccountPage.tsx not found at {acc_path}"
    with open(acc_path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "ThemeSwitch" in c
