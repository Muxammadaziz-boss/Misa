import os

BASE_DIR = r"D:\Ishchi stoli\Misa\yordamchi_9.0.0"

def test_reaction_bar_component_exists():
    path = os.path.join(BASE_DIR, r"Misa\src\components\ReactionBar.tsx")
    assert os.path.isfile(path), f"ReactionBar.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "export const ReactionBar" in c
    assert "REACTION_ITEMS" in c
    assert "misa-reaction-bar" in c
    assert "misa-reaction-btn" in c
    assert "misa-reaction-tooltip" in c
    assert "misa-reaction-emoji" in c

    # Check 5 reactions
    assert "👍" in c  # Like
    assert "👏🏻" in c  # Cheer
    assert "🎉" in c  # Celebrate
    assert "✨" in c  # Appreciate
    assert "🙂" in c  # Smile

    # Check tooltips
    assert "Like" in c
    assert "Cheer" in c
    assert "Celebrate" in c
    assert "Appreciate" in c
    assert "Smile" in c


def test_globals_css_has_reaction_bar_styles():
    path = os.path.join(BASE_DIR, r"Misa\src\styles\globals.css")
    assert os.path.isfile(path), f"globals.css not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    assert ".misa-reaction-bar" in c
    assert ".misa-reaction-btn" in c
    assert ".misa-reaction-tooltip" in c
    assert "is-selected" in c
    assert "translateY(-6px)" in c or "translateY(-5px)" in c or "translateY(-8px)" in c
    assert "scale(1.18)" in c or "scale(1.1" in c or "scale(1.2" in c
    assert "prefers-reduced-motion" in c


def test_chat_page_uses_reaction_bar():
    path = os.path.join(BASE_DIR, r"Misa\src\pages\ChatPage.tsx")
    assert os.path.isfile(path), f"ChatPage.tsx not found at {path}"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    assert "ReactionBar" in c
    assert "handleReaction" in c
