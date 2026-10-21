# ========== core/tools/stitch_tool.py ==========
# Misa AI v9.0 — Stitch UI/UX Designer & Template Generator
# Google Stitch MCP orqali matndan tayyor andoza va frontend veb ekranlar yaratish

import os
import json
import logging
from typing import Dict, Any, Optional
from core.mcp.manager import get_mcp_manager

logger = logging.getLogger(__name__)


def stitch_ui_designer(
    prompt: str,
    project_title: Optional[str] = None,
    save_to_desktop: bool = True
) -> str:
    """
    Google Stitch orqali matndan to'liq andoza, UI dizayn va Tailwind CSS veb-sahifa yaratish.
    
    Args:
        prompt: Yaratilishi kerak bo'lgan andoza tavsifi (masalan: "Fintech mobil ilovasi uchun qorong'u rejimdagi dashboard")
        project_title: Loyiha nomi (agar berilmasa, avtomatik nomlanadi)
        save_to_desktop: Yaratilgan HTML kodni Ish stoliga saqlash
    """
    mcp = get_mcp_manager()
    client = mcp.get_client("stitch")
    if not client:
        return "❌ Google Stitch MCP serveri ulanmagan yoki 'data/mcp_servers.json' da faollashtirilmagan."

    clean_prompt = prompt.strip()
    if not clean_prompt:
        return "❌ Andoza tavsifi bo'sh bo'lishi mumkin emas."

    # 1. Loyihani aniqlash yoki yaratish
    proj_name = None
    try:
        projects_res = client.call_tool("list_projects", {})
        if projects_res.get("ok"):
            data = projects_res.get("data", {})
            projs = data.get("projects", []) if isinstance(data, dict) else []
            if projs and isinstance(projs, list):
                # Birinchi mos loyihani olish
                proj_name = projs[0].get("name")
    except Exception as e:
        logger.warning(f"Loyiha qidirishda ogohlantirish: {e}")

    if not proj_name:
        title = project_title or f"Misa Stitch Project ({clean_prompt[:25]})"
        create_res = client.call_tool("create_project", {"title": title})
        if create_res.get("ok"):
            p_data = create_res.get("data", {})
            proj_name = p_data.get("name") if isinstance(p_data, dict) else None

    if not proj_name:
        return "❌ Stitch'da loyiha yaratib bo'lmadi. API kalitini tekshiring."

    # 2. Matndan yangi andoza (screen) generatsiya qilish
    gen_res = client.call_tool(
        "generate_screen_from_text",
        {
            "projectId": proj_name,
            "prompt": clean_prompt,
        }
    )

    if not gen_res.get("ok"):
        return f"❌ Stitch orqali andoza yaratishda xatolik: {gen_res.get('error')}"

    screen_data = gen_res.get("data", {})
    screen_id = screen_data.get("name") if isinstance(screen_data, dict) else None
    html_code = screen_data.get("htmlCode", "") if isinstance(screen_data, dict) else ""
    screenshot_url = ""
    if isinstance(screen_data, dict) and "thumbnailScreenshot" in screen_data:
        screenshot_url = screen_data["thumbnailScreenshot"].get("downloadUrl", "")

    # 3. Agar kod mavjud bo'lsa, faylga saqlash
    saved_path_msg = ""
    if save_to_desktop and html_code:
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            safe_name = "".join(c if c.isalnum() else "_" for c in clean_prompt[:25]).strip("_")
            file_name = f"Stitch_Template_{safe_name}.html"
            out_path = os.path.join(desktop, file_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html_code)
            saved_path_msg = f"\n📁 **HTML fayl Ish stoliga saqlandi:** `{out_path}`"
        except Exception as e:
            logger.warning(f"Faylni saqlashda xatolik: {e}")

    preview_msg = f"\n🖼️ **Ko'rish havolasi (Screenshot):** [Rasmni ochish]({screenshot_url})" if screenshot_url else ""

    return (
        f"🎨 **Google Stitch andozasi muvaffaqiyatli yaratildi!**\n\n"
        f"• **Loyiha:** `{proj_name}`\n"
        f"• **Andoza kodi:** `{screen_id or 'Yangi ekran'}`\n"
        f"• **Tavsif:** {clean_prompt}\n"
        f"{preview_msg}"
        f"{saved_path_msg}\n\n"
        f"💡 Endi siz ushbu andozani to'g'ridan-to'g'ri loyihangizda ishlatishingiz yoki tahrirlashingiz mumkin."
    )
