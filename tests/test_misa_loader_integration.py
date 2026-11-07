import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_misa_loader_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\MisaLoader.tsx")
    assert os.path.isfile(path), f"MisaLoader.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "MisaLoader" in c
    assert "main" in c
    assert "inline" in c
    assert "small" in c
    assert "medium" in c
    assert "large" in c
    # Accessibility
    assert "role=\"status\"" in c or 'role="status"' in c
    assert "aria-live=\"polite\"" in c or 'aria-live="polite"' in c
    assert "aria-hidden" in c
    assert "misa-sr-only" in c or "sr-only" in c


def test_globals_css_has_loader_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert ".misa-main-loader" in c
    assert ".misa-main-loader-core" in c
    assert ".misa-inline-loader" in c
    assert ".misa-inline-spinner" in c
    assert ".misa-loader-text" in c
    assert ".misa-loader-letter" in c

    assert "@keyframes misaShadowRotate" in c
    assert "@keyframes misaInlineSpin" in c
    assert "@keyframes misaLetterShimmer" in c
    assert "prefers-reduced-motion" in c


def test_loader_design_tokens():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    # Misa palette colors in loader section
    loader_section = c[c.find(".misa-main-loader"):]
    assert "#9303C5" in loader_section or "147, 3, 197" in loader_section
    assert "#C77DFF" in loader_section or "199, 125, 255" in loader_section or "#C04CFD" in loader_section
    assert "inset" in loader_section


def test_loader_integrated_in_app():
    path = os.path.join(BASE_DIR, r"Misa\src\App.tsx")
    assert os.path.isfile(path), f"App.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "MisaLoader" in c
    assert 'variant="main"' in c


def test_loader_integrated_in_chat():
    path = os.path.join(BASE_DIR, r"Misa\src\pages\ChatPage.tsx")
    assert os.path.isfile(path), f"ChatPage.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "MisaLoader" in c
    assert 'variant="inline"' in c


def test_loader_integrated_in_memory():
    path = os.path.join(BASE_DIR, r"Misa\src\pages\MemoryPage.tsx")
    assert os.path.isfile(path), f"MemoryPage.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "MisaLoader" in c
