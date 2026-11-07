import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_glass_context_menu_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\GlassContextMenu.tsx")
    assert os.path.isfile(path), f"GlassContextMenu.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert "GlassContextMenu" in c
    assert "GlassMenuItem" in c
    assert "GlassMenuGroup" in c
    assert "misa-glass-menu" in c
    assert "misa-glass-menu-item" in c
    assert "misa-glass-menu-separator" in c
    assert "destructive" in c


def test_globals_css_has_glass_menu_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert ".misa-glass-menu" in c
    assert ".misa-glass-menu-item" in c
    assert ".misa-glass-menu-separator" in c
    assert ".misa-glass-menu-item--destructive" in c
    assert "prefers-reduced-motion" in c


def test_context_menu_uses_glass_menu_classes():
    cm_path = os.path.join(BASE_DIR, r"Misa\src\components\ContextMenu.tsx")
    assert os.path.isfile(cm_path), f"ContextMenu.tsx not found at {cm_path}"
    with open(cm_path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "misa-glass-menu" in c
