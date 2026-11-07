import os
import re
import pytest

MISA_ROOT = r'D:\Ishchi stoli\Misa\yordamchi_9.0.0'

def test_copy_button_component_exists():
    path = os.path.join(MISA_ROOT, 'Misa', 'src', 'components', 'CopyButton.tsx')
    assert os.path.exists(path), "CopyButton.tsx must exist"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert "export const CopyButton" in content
    assert "navigator?.clipboard?.writeText" in content
    assert "document.execCommand" in content, "Must include fallback for restricted environments"
    assert "clearTimeout" in content, "Must clean up timers"
    assert "aria-live=\"polite\"" in content or "role=\"tooltip\"" in content

def test_globals_css_has_copy_button_styles():
    path = os.path.join(MISA_ROOT, 'Misa', 'src', 'styles', 'globals.css')
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf-8') as f:
        css = f.read()
    
    assert ".misa-copy-btn" in css
    assert ".misa-copy-tooltip" in css
    assert ".is-success" in css
    assert ".is-error" in css
    assert "--btn-size" in css
    assert "border-radius: 10px" in css

def test_chat_page_uses_copy_button():
    path = os.path.join(MISA_ROOT, 'Misa', 'src', 'pages', 'ChatPage.tsx')
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert "import { CopyButton }" in content
    assert "<CopyButton" in content

def test_markdown_view_uses_copy_button():
    path = os.path.join(MISA_ROOT, 'Misa', 'src', 'components', 'MarkdownView.tsx')
    assert os.path.exists(path)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert "import { CopyButton }" in content
    assert "<CopyButton" in content
