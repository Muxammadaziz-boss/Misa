import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_expandable_button_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\ExpandableButton.tsx")
    assert os.path.isfile(path), f"ExpandableButton.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "export const ExpandableButton" in c
    assert "misa-expandable-btn" in c
    assert "misa-expandable-icon" in c
    assert "misa-expandable-text" in c
    assert "variant" in c
    assert "destructive" in c
    assert "loading" in c


def test_globals_css_has_expandable_button_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert ".misa-expandable-btn" in c
    assert ".misa-expandable-icon" in c
    assert ".misa-expandable-text" in c
    assert ".misa-expandable-btn--destructive" in c
    assert "prefers-reduced-motion" in c
    # Check width expansion on hover
    assert ":hover" in c


def test_expandable_button_used_in_pages():
    acc_path = os.path.join(BASE_DIR, r"Misa\src\pages\AccountPage.tsx")
    assert os.path.isfile(acc_path), f"AccountPage.tsx not found at {acc_path}"
    with open(acc_path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "ExpandableButton" in c
