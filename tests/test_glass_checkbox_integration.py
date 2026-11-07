import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_glass_checkbox_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\GlassCheckbox.tsx")
    assert os.path.isfile(path), f"GlassCheckbox.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "GlassCheckbox" in c
    assert "misa-glass-checkbox-wrapper" in c
    assert "misa-glass-checkbox-box" in c
    assert "misa-glass-checkbox-check" in c
    assert "misa-glass-checkbox-input" in c
    assert "onChange" in c
    assert "disabled" in c
    assert "label" in c


def test_globals_css_has_glass_checkbox_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert ".misa-glass-checkbox-wrapper" in c
    assert ".misa-glass-checkbox-box" in c
    assert ".misa-glass-checkbox-check" in c
    assert "stroke-dashoffset" in c
    assert "prefers-reduced-motion" in c


def test_glass_checkbox_used_in_pages():
    acc_path = os.path.join(BASE_DIR, r"Misa\src\pages\AccountPage.tsx")
    assert os.path.isfile(acc_path), f"AccountPage.tsx not found at {acc_path}"
    with open(acc_path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "GlassCheckbox" in c
