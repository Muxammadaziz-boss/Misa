import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_neumorphic_card_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\NeumorphicCard.tsx")
    assert os.path.isfile(path), f"NeumorphicCard.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "NeumorphicCard" in c
    assert "misa-neumorphic-card" in c
    assert "elevated" in c
    assert "interactive" in c
    assert "selected" in c
    assert "compact" in c
    assert "stat" in c
    assert "glass" in c
    # Subcomponents
    assert "NeumorphicCardHeader" in c
    assert "NeumorphicCardTitle" in c
    assert "NeumorphicCardBody" in c
    assert "NeumorphicCardFooter" in c
    # Accessibility & keyboard navigation
    assert "tabIndex" in c or "role=" in c
    assert "onKeyDown" in c or "onClick" in c
    assert "aria-pressed" in c


def test_globals_css_has_neumorphic_card_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert ".misa-neumorphic-card" in c
    assert ".misa-neumorphic-card--elevated" in c
    assert ".misa-neumorphic-card--interactive" in c
    assert ".misa-neumorphic-card--selected" in c
    assert ".misa-neumorphic-card--compact" in c
    assert ".misa-neumorphic-card--stat" in c
    assert ".misa-neumorphic-card--glass" in c

    # Structural elements
    assert ".misa-neumorphic-card__header" in c
    assert ".misa-neumorphic-card__title" in c
    assert ".misa-neumorphic-card__stat-value" in c
    assert ".misa-neumorphic-card__stat-trend" in c

    # Dual-direction shadows
    assert "8px 8px 20px" in c or "box-shadow" in c
    # Purple accent reference
    assert "147, 3, 197" in c or "9303C5" in c or "192, 76, 253" in c
    # Motion preference
    assert "prefers-reduced-motion" in c


def test_neumorphic_card_integrated_in_memory_page():
    mem_path = os.path.join(BASE_DIR, r"Misa\src\pages\MemoryPage.tsx")
    assert os.path.isfile(mem_path), f"MemoryPage.tsx not found at {mem_path}"
    with open(mem_path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "NeumorphicCard" in c
    assert 'variant="stat"' in c
    assert 'variant="interactive"' in c


def test_neumorphic_card_integrated_in_account_page():
    acc_path = os.path.join(BASE_DIR, r"Misa\src\pages\AccountPage.tsx")
    assert os.path.isfile(acc_path), f"AccountPage.tsx not found at {acc_path}"
    with open(acc_path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "NeumorphicCard" in c
    assert 'variant="interactive"' in c


def test_design_tokens_conformance():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    # Dark gradient container
    assert "#171D29" in c or "#171d29" in c
    assert "#101520" in c or "#101520" in c
    # Soft dual shadows
    assert "rgba(0, 0, 0," in c
    assert "rgba(45, 53, 70," in c
    # Accent illumination
    assert "rgba(192, 76, 253," in c
