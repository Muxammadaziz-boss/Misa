# ========== ai_engine.py ==========
# AI integratsiyasi — Gemini va OpenRouter qo'llab-quvvatlaydi
# Avval Gemini, keyin OpenRouter ga fallback

import os
import json
import logging
import requests
import time
import io
import base64
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


load_dotenv()



# ========== Sozlamalar ==========
GOOGLE_API_KEY = (
    os.getenv("MISA_GEMINI_API_KEY", "").strip()
    or os.getenv("GOOGLE_API_KEY", "").strip()
    or os.getenv("GEMINI_API_KEY", "").strip()
)
OPENROUTER_API_KEY = (
    os.getenv("MISA_OPENROUTER_API_KEY", "").strip()
    or os.getenv("OPENROUTER_API_KEY", "").strip()
)
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")


def get_gemini_api_key(user_id: Optional[str] = None) -> str:
    """Dinamik Google Gemini API kalitini olish (AIKeyManager, environment yoki config.json orqali)"""
    global GOOGLE_API_KEY
    try:
        from core.v8.ai_key_manager import get_ai_key_manager
        m_key = get_ai_key_manager().get_active_gemini_key(user_id=user_id)
        if m_key:
            return m_key
    except Exception:
        pass

    key = (
        os.getenv("MISA_GEMINI_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    if key:
        GOOGLE_API_KEY = key
        return key

    if GOOGLE_API_KEY and str(GOOGLE_API_KEY).strip():
        return str(GOOGLE_API_KEY).strip()
    try:
        cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                k = (
                    cfg.get("gemini_api_key")
                    or cfg.get("google_api_key")
                    or cfg.get("ai", {}).get("gemini_api_key")
                    or cfg.get("ai", {}).get("api_key")
                )
                if k and str(k).strip():
                    GOOGLE_API_KEY = str(k).strip()
                    return GOOGLE_API_KEY
    except Exception:
        pass
    return ""

# ========== Suhbat xotirasi ==========
suhbat_tarixi_gemini = []  # Gemini formati
suhbat_tarixi_openrouter = []  # OpenRouter formati
MAX_TARIX = 10

# ========== Mavjud buyruqlar ro'yxati ==========
MAVJUD_BUYRUQLAR = {
    "open_youtube": "YouTube ochish",
    "youtube_first_video": "YouTube dan birinchi videoni ochish",
    "music_search": "Musiqa qidirish",
    "open_telegram": "Telegram ochish",
    "open_code": "VS Code ochish",
    "open_chrome": "Chrome ochish",
    "open_brave": "Brave ochish",
    "open_discord": "Discord ochish",
    "weather": "Ob-havo haqida ma'lumot",
    "search": "Google da qidirish",
    "time": "Hozirgi vaqtni aytish",
    "date": "Bugungi sanani aytish",
    "reminder": "Eslatma qo'shish",
    "reminders": "Eslatmalarni ko'rish",
    "delete_reminder": "Eslatmani o'chirish",
    "play_video": "YouTube VIDEONI ijro etish / davom ettirish (faqat VIDEO uchun!)",
    "pause_video": "YouTube VIDEONI to'xtatish / pauza (faqat VIDEO uchun!)",
    "music_play": "MUSIQANI ijro etish / davom ettirish (Yandex Music, musiqa uchun)",
    "music_pause": "MUSIQANI to'xtatish / pauza qilish (Yandex Music, musiqa uchun)",
    "music_restart": "MUSIQANI boshidan boshlash (Yandex Music)",
    "volume_set": "Ovozni ma'lum darajaga qo'yish (0-100)",
    "volume_up": "Ovozni oshirish",
    "volume_down": "Ovozni pasaytirish",
    "volume_mute": "Ovozni o'chirish (mute)",
    "volume_unmute": "Ovozni yoqish (unmute)",
    "next_video": "Keyingi videoga o'tish (YouTube)",
    "prev_video": "Oldingi videoga qaytish (YouTube)",
    "close_chrome": "Chrome oynasini / tabini yopish",
    "show_desktop": "Ish stolini ko'rsatish (Win+D)",
    "switch_window": "Boshqa oynaga o'tish (Alt+Tab)",
    "open_explorer": "Fayl menejer / papkalarni ochish (Win+E)",
    "open_cmd": "Buyruq satri / CMD / terminal ochish",
    "open_taskmanager": "Vazifa menejeri / Task Manager ochish",
    "close_window": "Hozirgi oynani yopish (Alt+F4)",
    "task_view": "Barcha oynalarni ko'rish (Win+Tab)",
    "open_settings": "Windows sozlamalarni ochish (Win+I)",
    "take_screenshot": "Ekran rasmini olish (screenshot)",
    "open_run": "Ishga tushirish oynasi (Win+R)",
    "minimize_all": "Barcha oynalarni kichraytirish",
    "greet": "Salomlashish",
    "shutdown": "Kompyuterni o'chirish",
    "restart": "Kompyuterni qayta yuklash",
    "lock": "Ekranni qulflash",
    "chat_mode": "AI bilan suhbat rejimi",
}

# ========== Tizim prompti ==========
SYSTEM_PROMPT = f"""Sen — "Yordamchi AI", foydalanuvchining yaqin do'sti va aqlli kompyuter yordamchisi.
Sen robot emas — sen YAQIN ODAM kabi gaplash. Iliq, samimiy va hazilkash bo'l.

MUHIM QOIDALAR:
1. Har doim O'ZBEK tilida javob ber.
2. Javoblarni QISQA va TABIIY qil (1-3 gap, xuddi do'stingga gapirgandek).
3. Do'stona, iliq va samimiy bo'l — foydalanuvchi seni yaqin odam deb his qilsin.
4. CHALA SO'ZLARNI TUSHUN: Nutq tanish ba'zan so'zlarni chala eshitadi.
   Masalan: "maslahat uchun ra" = "maslahat uchun rahmat"
   "kompyuter o'ch" = "kompyuterni o'chir"
   "farg'onada hav" = "farg'onada havo qanday"
   Sen AQLLI bo'l — chala gapni o'zing to'ldirib tushun!
5. Xato yozilgan yoki noto'g'ri eshitilgan so'zlarni ham tushunishga harakat qil.
6. HECH QACHON inglizcha fikrlash jarayonini (reasoning, 'The user is asking...', 'I should...') VA ICHKI QOIDALARNI (aniqlik foizlari, mezonlar, prompt ko'rsatmalari) foydalanuvchiga matn qilib ko'rsatma! Faqat toza va samimiy o'zbekcha yakuniy javob ber.
7. INTERNETDAN QIDIRUV VA 70% ANQLIK MEZONI:
   Foydalanuvchi so'ragan har qanday ma'lumot, yangilik, narx, ob-havo, atama yoki fakt bo'yicha erkin internetdan izlashing mumkin.
   Taqdim etilayotgan har qanday ma'lumotning ishonchliligi va to'g'riligi kamida 70% bo'lishi SHART!
   Agar biror ma'lumotning aniqligi yoki ishonchliligi 70% dan past bo'lsa, shubhali bo'lsa yoki tasdiqlanmagan mish-mish bo'lsa, uni mutlaq haqiqat deb taqdim etma! Foydalanuvchiga buni ochiq bildir yoki faqat tekshirilgan qismini ko'rsat.

VAZIFANG:
Foydalanuvchi biron narsa aytganda, sen ikki xil javob bera olasan:

A) BUYRUQ — agar foydalanuvchi kompyuterda biror ish qilmoqchi bo'lsa:
Javobni faqat JSON formatda ber:
{{"type": "command", "intent": "<buyruq_nomi>", "params": {{}}, "response": "<qisqa javob>"}}

Mavjud buyruqlar:
{json.dumps(MAVJUD_BUYRUQLAR, ensure_ascii=False, indent=2)}

Ovoz buyruqlari uchun params:
- volume_set: {{"level": 50}}
- volume_up: {{"amount": 10}}
- volume_down: {{"amount": 10}}
- weather: {{"city": "shahar nomi"}} (masalan: "Toshkent", "Farg'ona", "Samarqand")

MUHIM — MUSIQA va VIDEO farqi:
- "musiqani to'xtat/pauza" = music_pause (Yandex Music)
- "videoni to'xtat" yoki "to'xtat" (video kontekstida) = pause_video (YouTube)
- "musiqani qo'y/davom ettir" = music_play
- "videoni qo'y/davom ettir" = play_video
- "musiqani boshidan boshla" = music_restart
- Agar kontekst noaniq bo'lsa, music_pause/music_play ishlatilsin (musiqa ko'proq ishlatiladi)

MUHIM — OYNA YOPISH farqi:
- "chrome yop" / "brauzerni yop" / "sahifani yop" / "tabni yop" = close_chrome (faqat Chrome)
- "oynani yop" / "oynani yopish" / "yopib yubor" = close_window (Alt+F4, hozirgi oynani yopadi)
- Agar "chrome" yoki "brauzer" yoki "tab" yoki "sahifa" aytilsa = close_chrome
- Agar umumiy "oynani yop" aytilsa = close_window

B) SUHBAT — agar foydalanuvchi savol bersa yoki gaplashmoqchi bo'lsa:
{{"type": "answer", "response": "<javob matni>"}}

MISOLLAR:
"YouTube och" -> {{"type": "command", "intent": "open_youtube", "params": {{}}, "response": "YouTube ochildi"}}
"Ovozni 50 foiz qil" -> {{"type": "command", "intent": "volume_set", "params": {{"level": 50}}, "response": "Ovoz 50 foizga qo'yildi"}}
"Farg'onada havo qanday?" -> {{"type": "command", "intent": "weather", "params": {{"city": "Farg'ona"}}, "response": "Farg'ona ob-havosi tekshirilmoqda"}}
"musiqani to'xtat" -> {{"type": "command", "intent": "music_pause", "params": {{}}, "response": "Musiqa to'xtatildi"}}
"musiqani qo'y" -> {{"type": "command", "intent": "music_play", "params": {{}}, "response": "Musiqa davom etmoqda"}}
"videoni to'xtat" -> {{"type": "command", "intent": "pause_video", "params": {{}}, "response": "Video to'xtatildi"}}
"Python nima?" -> {{"type": "answer", "response": "Python — mashhur dasturlash tili."}}

FAQAT JSON QAYTARING. BOSHQA HECH NARSA YOZMANG.
"""


def ai_savol_yuborish(matn, foydalanuvchi_ismi="Foydalanuvchi", user_id: Optional[str] = None):
    """AI ga savol yuborish — Misa Intelligence Core orqali
    (Context -> Intent -> Reasoning -> Decision -> Tool -> Verification -> Response)
    Har qanday nosozlikda an'anaviy to'g'ridan-to'g'ri fallback saqlanadi.
    """
    try:
        from core.intelligence import get_orchestrator, CompatibilityAdapter
        orchestrator = get_orchestrator()
        intel_resp = orchestrator.handle(matn, user_name=foydalanuvchi_ismi, user_id=user_id)
        if intel_resp:
            legacy_dict = CompatibilityAdapter.to_legacy_ai_engine_dict(intel_resp)
            if legacy_dict:
                return legacy_dict
    except Exception as e:
        logging.warning(f"Intelligence Orchestrator orqali chaqirishda xatolik: {e}, an'anaviy oqimga o'tilmoqda...")

    
    enriched_prompt = SYSTEM_PROMPT
    
    # 1. Foydalanuvchi ismi
    enriched_prompt += f"\n\nJoriy foydalanuvchi ismi: {foydalanuvchi_ismi}."
    
    # 2. Kompyuter va dasturlar konteksti (Real-time Windows Inventory & Specs)
    try:
        from core.app_detector import get_app_detector
        detector = get_app_detector()
        specs = detector.get_realtime_system_specs()
        inventory = detector.get_realtime_inventory_summary()
        enriched_prompt += f"\n\nKOMPYUTER VA ILOVALAR HOLATI (REAL-TIME WINDOWS INVENTORY):\n{specs}\n\nAniqlangan dasturlar holati:\n{inventory}\n"
    except Exception as e:
        logging.warning(f"AI kontekstiga dasturlar va tizim ma'lumotlarini yuklashda xatolik: {e}")

    # 3. AgentMemory dan bilimlar va so'nggi suhbat tarixi
    try:
        from core.agent_memory import get_memory
        memory = get_memory()
        
        # Bilimlar
        knowledge = memory.get_knowledge()
        if knowledge:
            bilimlar = "\n".join(f"- {k}: {v.get('value', v)}" for k, v in list(knowledge.items())[:10])
            enriched_prompt += f"\n\nFOYDALANUVCHI HAQIDA BILIMLAR:\n{bilimlar}\n"
            
        # So'nggi suhbat tarixi
        conversations = memory.get_conversations(last_n=6)
        if conversations:
            tarix_lines = []
            for c in conversations:
                u = c.get("user", "").strip()
                a = c.get("agent", "").strip()
                if u and a:
                    tarix_lines.append(f"Foydalanuvchi: {u}")
                    tarix_lines.append(f"Misa: {a}")
            if tarix_lines:
                enriched_prompt += f"\nSO'NGGI SUHBAT TARIXI (Kontekst uchun):\n" + "\n".join(tarix_lines) + "\n"
    except Exception:
        pass

    enriched_prompt += """
\nMUHIM MANTIQ VA FIKRLASH QOIDALARI:
- Agar foydalanuvchi 'shunga o'xshash', 'boshqa', 'u', 'yana' kabi so'zlarni ishlatsa, avvalgi suhbat mavzusi va kompyuterdagi mavjud dasturlar holatini bog'lab, chuqur mantiqiy, do'stona va foydali maslahat ber!
- Masalan: Agar foydalanuvchi Telegram haqida so'ragan bo'lsa va keyin 'shunga o'xshash bormi?' desa, unga Telegramga o'xshash messenjerlar (WhatsApp, Discord, Signal) haqida ma'lumot ber, kompyuteridagi holatini ayt va qulay yechimlarni taklif qil.
- Doimo foydalanuvchiga chin dildan yordam beradigan, mantiqan o'ylaydigan sun'iy intellekt bo'l!
"""
    
    # 1-urinish: Google Gemini
    if get_gemini_api_key(user_id=user_id):
        javob = _gemini_yuborish(matn, enriched_prompt, user_id=user_id)
        if javob is not None:
            return javob
        logging.warning("Gemini ishlamadi, OpenRouter ga o'tilmoqda...")
    
    # 2-urinish: OpenRouter
    if OPENROUTER_API_KEY:
        javob = _openrouter_yuborish(matn, enriched_prompt)
        if javob is not None:
            return javob
    
    logging.error("Hech qaysi AI provider ishlamadi")
    return None


def _gemini_yuborish(matn, system_prompt=None, user_id=None):

    """Google Gemini API orqali so'rov — Google Search Grounding va Thinking Mode bilan"""
    prompt = system_prompt or SYSTEM_PROMPT
    GEMINI_MODELS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-pro",
        "gemini-pro-latest",
    ]

    
    suhbat_tarixi_gemini.append({"role": "user", "parts": [{"text": matn}]})
    while len(suhbat_tarixi_gemini) > MAX_TARIX:
        suhbat_tarixi_gemini.pop(0)
    
    for model in GEMINI_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            
            gen_config = {"maxOutputTokens": 2048, "temperature": 0.4}
            
            request_body = {
                "system_instruction": {"parts": [{"text": prompt}]},
                "contents": suhbat_tarixi_gemini,
                "generationConfig": gen_config,
                # Google Search Grounding — real-time ma'lumot olish
                "tools": [{"google_search": {}}]
            }
            
            active_gemini_key = get_gemini_api_key(user_id=user_id)
            if not active_gemini_key:
                logging.warning("Gemini API kaliti topilmadi")
                break

            response = requests.post(
                f"{url}?key={active_gemini_key}",
                headers={"Content-Type": "application/json"},
                json=request_body,
                timeout=15
            )
            
            if response.status_code == 429:
                logging.warning(f"Gemini {model} kvota tugagan (429), keyingi model...")
                try:
                    from core.v8.ai_key_manager import get_ai_key_manager
                    get_ai_key_manager().mark_key_failed(active_gemini_key, cooldown_seconds=60.0)
                except Exception:
                    pass
                continue
            
            if response.status_code != 200:
                logging.error(f"Gemini {model} xato: {response.status_code}")
                # Agar grounding qo'llab-quvvatlanmasa, tools siz urinish
                if response.status_code == 400:
                    del request_body["tools"]
                    response = requests.post(
                        f"{url}?key={active_gemini_key}",
                        headers={"Content-Type": "application/json"},
                        json=request_body,
                        timeout=15
                    )
                    if response.status_code != 200:
                        continue

                else:
                    continue
            
            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                logging.warning(f"Gemini ({model}): candidates ro'yxati bo'sh")
                continue
            cand0 = candidates[0]
            parts = cand0.get("content", {}).get("parts", [])
            ai_text = ""
            for part in parts:
                # Agar modelning ichki o'ylash (thought) qismi bo'lsa, uni o'tkazib yuboramiz
                if part.get("thought", False):
                    continue
                if "text" in part:
                    ai_text += part["text"]
            ai_text = ai_text.strip()
            if not ai_text:
                continue
            
            # Grounding metadata bormi tekshirish
            grounding = cand0.get("groundingMetadata", {})
            if grounding:
                logging.debug(f"Gemini ({model}): Google Search Grounding ishlatildi")
            
            logging.debug(f"Gemini ({model}) javobi: {ai_text}")
            
            suhbat_tarixi_gemini.append({"role": "model", "parts": [{"text": ai_text}]})
            return _javob_tahlil(ai_text)
            
        except Exception as e:
            logging.error(f"Gemini {model} xatolik: {e}")
            continue
    
    # Barcha modellar ishlamadi
    if suhbat_tarixi_gemini:
        suhbat_tarixi_gemini.pop()
    return None


def _openrouter_yuborish(matn, system_prompt=None):
    """OpenRouter API orqali so'rov"""
    prompt = system_prompt or SYSTEM_PROMPT
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    suhbat_tarixi_openrouter.append({"role": "user", "content": matn})
    while len(suhbat_tarixi_openrouter) > MAX_TARIX:
        suhbat_tarixi_openrouter.pop(0)
    
    messages = [{"role": "system", "content": prompt}] + suhbat_tarixi_openrouter
    
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://yordamchi-ai.uz",
                "X-Title": "Yordamchi AI"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.3,
            },
            timeout=15
        )
        
        if response.status_code != 200:
            logging.error(f"OpenRouter xato: {response.status_code}")
            suhbat_tarixi_openrouter.pop()
            return None
        
        data = response.json()
        ai_text = data["choices"][0]["message"]["content"].strip()
        logging.debug(f"OpenRouter javobi: {ai_text}")
        
        suhbat_tarixi_openrouter.append({"role": "assistant", "content": ai_text})
        return _javob_tahlil(ai_text)
        
    except Exception as e:
        logging.error(f"OpenRouter xatolik: {e}")
        if suhbat_tarixi_openrouter:
            suhbat_tarixi_openrouter.pop()
        return None


def _javob_tahlil(ai_text):
    """AI javobini tahlil qilish (mustahkam himoya va tiklash bilan)"""
    from core.intelligence.text_cleaner import extract_clean_response_text
    javob = _json_ajratish(ai_text)

    if javob and isinstance(javob, dict):
        logging.info(f"AI natija: type={javob.get('type')}, intent={javob.get('intent', '-')}")
        if "response" in javob:
            javob["response"] = extract_clean_response_text(javob["response"])
        return javob
    else:
        # Har qanday uzilib qolgan yoki xom JSON dan toza inson matnini ajratib olish
        clean_resp = extract_clean_response_text(ai_text)
        if clean_resp:
            return {"type": "answer", "response": clean_resp}

        logging.warning(f"Foydali matn topilmadi: {ai_text[:100]}")
        return {"type": "answer", "response": "Kechirasiz, javobni tayyorlashda xatolik bo'ldi. Qaytadan urinib ko'ring."}


def _json_ajratish(matn):
    """AI javobidan JSON ni ajratib olish (ichma-ich {} va strict=False ni qo'llab-quvvatlaydi)"""
    matn = matn.strip()

    # To'g'ridan-to'g'ri JSON
    if matn.startswith("{"):
        try:
            return json.loads(matn, strict=False)
        except json.JSONDecodeError:
            pass

    # ```json ... ```
    if "```json" in matn:
        try:
            return json.loads(matn.split("```json")[1].split("```")[0].strip(), strict=False)
        except (IndexError, json.JSONDecodeError):
            pass

    # ``` ... ```
    if "```" in matn:
        try:
            return json.loads(matn.split("```")[1].split("```")[0].strip(), strict=False)
        except (IndexError, json.JSONDecodeError):
            pass

    # Ichma-ich {} ni qo'llab-quvvatlovchi qidiruv
    start = matn.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(matn)):
            if matn[i] == "{":
                depth += 1
            elif matn[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(matn[start:i+1], strict=False)
                    except json.JSONDecodeError:
                        break

    return None


def ai_mavjudmi():
    """AI tizimi ishga tayyor ekanligini tekshirish (ko'p provayderli tizim bilan)"""
    try:
        from core.providers import get_provider_system
        if get_provider_system().is_any_available():
            return True
    except Exception:
        pass
    return bool(get_gemini_api_key()) or bool(OPENROUTER_API_KEY)


def suhbat_tarixini_tozalash():
    """Suhbat tarixini tozalash"""
    global suhbat_tarixi_gemini, suhbat_tarixi_openrouter
    suhbat_tarixi_gemini = []
    suhbat_tarixi_openrouter = []
    logging.debug("Suhbat tarixi tozalandi")


# ========== Ekran tahlili (AI Vision) ==========
def _capture_screen_pil():
    """Ekrandan ishonchli screenshot olish (pyautogui va Windows GDI BitBlt fallback)"""
    try:
        import pyautogui
        return pyautogui.screenshot()
    except Exception as e:
        logging.warning(f"pyautogui screenshot ololmadi: {e}, GDI BitBlt orqali olishga urinilmoqda...")
    
    # Windows GDI BitBlt fallback (non-interactive / background / DWM sesiyalar uchun 100% ishlaydi)
    try:
        import ctypes
        from ctypes import wintypes
        from PIL import Image

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        if w <= 0 or h <= 0:
            w, h = 1920, 1080

        hdesktop = user32.GetDesktopWindow()
        desktop_dc = user32.GetWindowDC(hdesktop)
        img_dc = gdi32.CreateCompatibleDC(desktop_dc)
        mem_bitmap = gdi32.CreateCompatibleBitmap(desktop_dc, w, h)
        old_bmp = gdi32.SelectObject(img_dc, mem_bitmap)

        SRCCOPY = 0x00CC0020
        gdi32.BitBlt(img_dc, 0, 0, w, h, desktop_dc, 0, 0, SRCCOPY)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ('biSize', wintypes.DWORD),
                ('biWidth', wintypes.LONG),
                ('biHeight', wintypes.LONG),
                ('biPlanes', wintypes.WORD),
                ('biBitCount', wintypes.WORD),
                ('biCompression', wintypes.DWORD),
                ('biSizeImage', wintypes.DWORD),
                ('biXPelsPerMeter', wintypes.LONG),
                ('biYPelsPerMeter', wintypes.LONG),
                ('biClrUsed', wintypes.DWORD),
                ('biClrImportant', wintypes.DWORD)
            ]

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down DIB
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buffer_len = w * h * 4
        buf = ctypes.create_string_buffer(buffer_len)
        DIB_RGB_COLORS = 0
        gdi32.GetDIBits(desktop_dc, mem_bitmap, 0, h, buf, ctypes.byref(bmi), DIB_RGB_COLORS)

        # Tozalash
        gdi32.SelectObject(img_dc, old_bmp)
        gdi32.DeleteObject(mem_bitmap)
        gdi32.DeleteDC(img_dc)
        user32.ReleaseDC(hdesktop, desktop_dc)

        img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1)
        return img.convert('RGB')
    except Exception as gdi_err:
        logging.error(f"GDI screenshot olishda ham xatolik: {gdi_err}")
        return None


def ekran_tahlil(savol="Ekranda nima ko'rinmoqda? Qisqacha tushuntir.", user_id=None):
    """Ekran screenshot olib, AI Vision orqali tahlil qilish"""
    try:
        screenshot = _capture_screen_pil()
        if not screenshot:
            logging.error("Ekran tahlili: screenshot olinmadi")
            return "Ekran tasvirini olib bo'lmadi (ekran ruxsati yoki oyna holati cheklangan)."
        
        # Rasmni kichiklashtirish (API uchun tez va arzon)
        screenshot = screenshot.resize((1024, max(1, int(1024 * screenshot.height / screenshot.width))))
        
        # Base64 ga o'girish
        buffer = io.BytesIO()
        screenshot.save(buffer, format="JPEG", quality=75)
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        logging.info(f"Screenshot olindi: {len(img_base64)} bytes (base64)")
        
        # Gemini Vision API ga yuborish
        if get_gemini_api_key(user_id=user_id):
            result = _gemini_vision(img_base64, savol, user_id=user_id)
            if result:
                return result
        
        # OpenRouter Vision fallback
        if OPENROUTER_API_KEY:
            result = _openrouter_vision(img_base64, savol)
            if result:
                return result
        
        logging.error("Ekran tahlili: hech qaysi AI provider ishlamadi")
        return "Ekran tahlili uchun AI Vision xizmati javob bermadi."
        
    except Exception as e:
        logging.error(f"Ekran tahlili xatolik: {e}")
        return f"Ekran tahlilida xatolik yuz berdi: {e}"


def ekran_element_top(element_nomi):
    """Ekranda ma'lum bir elementni topib, koordinatalarini qaytarish"""
    savol = f"""Ekrandagi '{element_nomi}' tugmasi yoki elementini top.
Javobni FAQAT shu formatda ber (boshqa hech narsa yozma):
{{"topildi": true, "x": <piksel_x>, "y": <piksel_y>, "tavsif": "<element haqida qisqacha>"}}
Agar topilmasa:
{{"topildi": false, "tavsif": "<nima uchun topilmadi>"}}

MUHIM: x va y — bu elementning MARKAZI piksel koordinatalari (screenshot 1024px kenglikda).
Haqiqiy ekran o'lchamiga moslashtirish kerak emas, men o'zim qilaman."""
    
    result = ekran_tahlil(savol)
    if not result:
        return None
    
    try:
        import pyautogui
        # AI javobidan JSON ni olish
        json_data = _json_ajratish(result)
        if json_data and json_data.get("topildi"):
            # Koordinatalarni haqiqiy ekran o'lchamiga moslashtirish
            screen_w, screen_h = pyautogui.size()
            scale_x = screen_w / 1024
            scale_y = screen_h / (1024 * screen_h / screen_w)
            
            real_x = int(json_data["x"] * scale_x)
            real_y = int(json_data["y"] * scale_y)
            
            logging.debug(f"Element topildi: '{element_nomi}' → ({real_x}, {real_y})")
            return {"topildi": True, "x": real_x, "y": real_y, "tavsif": json_data.get("tavsif", "")}
        else:
            logging.debug(f"Element topilmadi: '{element_nomi}'")
            return {"topildi": False, "tavsif": json_data.get("tavsif", "") if json_data else result}
    except Exception as e:
        logging.error(f"Element topish xatolik: {e}")
        return {"topildi": False, "tavsif": str(e)}


def buyruq_tekshir(nima_qilindi, kutilgan_natija):
    """Buyruq bajarilganidan keyin ekranni tekshirish — muvaffaqiyatli bo'ldimi?
    
    Args:
        nima_qilindi: Nima buyruq bajarildi (masalan: "Yandex Music play tugmasi bosildi")
        kutilgan_natija: Nima natija kutilmoqda (masalan: "Musiqa ijro etilmoqda, play/pause tugma ko'rinadi")
    
    Returns:
        dict: {"muvaffaqiyat": True/False, "tavsif": "...", "keyingi_qadam": "..."}
    """
    savol = f"""Men hozir buyruq bajardim: "{nima_qilindi}"
Kutilgan natija: "{kutilgan_natija}"

Ekranni ko'rib, buyruq MUVAFFAQIYATLI bajarilganini tekshir.
Javobni FAQAT shu formatda ber (boshqa hech narsa yozma):
{{"muvaffaqiyat": true/false, "tavsif": "<hozir ekranda nima ko'rinmoqda>", "keyingi_qadam": "<agar muvaffaqiyatsiz bo'lsa, nima qilish kerak>"}}"""
    
    result = ekran_tahlil(savol)
    if not result:
        return {"muvaffaqiyat": False, "tavsif": "Ekran tahlili ishlamadi", "keyingi_qadam": "qayta urinish"}
    
    try:
        json_data = _json_ajratish(result)
        if json_data:
            logging.debug(f"Tekshiruv natijasi: {json_data.get('muvaffaqiyat', False)} — {json_data.get('tavsif', '')[:80]}")
            return json_data
        else:
            # JSON bo'lmasa, matndan tahlil
            muvaffaqiyat = any(s in result.lower() for s in ["muvaffaqiyat", "success", "true", "ijro", "playing", "play"])
            return {"muvaffaqiyat": muvaffaqiyat, "tavsif": result[:200], "keyingi_qadam": ""}
    except Exception as e:
        logging.error(f"Tekshiruv xatolik: {e}")
        return {"muvaffaqiyat": False, "tavsif": str(e), "keyingi_qadam": "qayta urinish"}


def rasm_tahlil(img_data_or_path: str, savol: str = "Ushbu rasmni o'zbek tilida batafsil va aniq tahlil qilib ber.", user_id: Optional[str] = None) -> Optional[str]:
    """Ixtiyoriy rasm fayli yoki Base64 ma'lumotini Gemini Vision orqali tahlil qilish."""
    if not img_data_or_path:
        return None

    img_b64 = ""
    # 1. Fayl yo'li bo'lsa o'qish
    if len(img_data_or_path) < 1000 and os.path.isfile(img_data_or_path):
        try:
            with open(img_data_or_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logging.error(f"Rasm faylini o'qishda xatolik ({img_data_or_path}): {e}")
            return None
    else:
        img_b64 = img_data_or_path

    # 2. Gemini Vision orqali tahlil
    result = _gemini_vision(img_b64, savol, user_id=user_id)
    if result:
        return result

    # 3. OpenRouter Vision zaxirasi
    if OPENROUTER_API_KEY:
        res_open = _openrouter_vision(img_b64, savol)
        if res_open:
            return res_open

    return None


def _gemini_vision(img_base64: str, savol: str, user_id: Optional[str] = None) -> Optional[str]:
    """Gemini Vision API ga rasm yuborish (Gemini 3.8 Flash & 2.5 Flash)"""
    key = get_gemini_api_key(user_id=user_id)
    if not key:
        logging.warning("Gemini Vision: API kaliti topilmadi")
        return None

    VISION_MODELS = [
        "gemini-flash-lite-latest",
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]

    # Agar "data:image/...;base64," prefix bilan kelsa, tozalaymiz
    if "," in img_base64 and img_base64.startswith("data:"):
        img_base64 = img_base64.split(",", 1)[1]
    img_base64 = img_base64.strip()

    for model in VISION_MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            gen_config = {"maxOutputTokens": 1024, "temperature": 0.2}

            response = requests.post(
                f"{url}?key={key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [
                            {"text": savol or "Ushbu rasmni o'zbek tilida batafsil va aniq tushuntirib ber."},
                            {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
                        ]
                    }],
                    "generationConfig": gen_config
                },
                timeout=35
            )

            if response.status_code == 429:
                logging.warning(f"Vision {model} kvota tugagan (429), keyingi...")
                continue

            if response.status_code != 200:
                logging.error(f"Vision {model} xato: {response.status_code} - {response.text[:120]}")
                continue

            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                continue
            ai_text = parts[0]["text"].strip()
            logging.info(f"Vision ({model}) muvaffaqiyatli tahlil qildi: {ai_text[:80]}")
            return ai_text

        except Exception as e:
            logging.error(f"Vision {model} xatolik: {e}")
            continue

    return None
    
    return None


def _openrouter_vision(img_base64, savol):
    """OpenRouter Vision API ga rasm yuborish"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": savol},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                    ]
                }],
                "max_tokens": 512,
                "temperature": 0.2,
            },
            timeout=20
        )
        
        if response.status_code != 200:
            logging.error(f"OpenRouter Vision xato: {response.status_code}")
            return None
        
        data = response.json()
        ai_text = data["choices"][0]["message"]["content"].strip()
        logging.debug(f"OpenRouter Vision javobi: {ai_text[:100]}")
        return ai_text
        
    except Exception as e:
        logging.error(f"OpenRouter Vision xatolik: {e}")
        return None


# ========================================================
# AGENT AI CALL — Agent planner uchun maxsus funksiya
# ========================================================

def agent_ai_call(prompt: str, system_prompt: str, history: list = None) -> str:
    """Agent planner uchun AI chaqirish.
    
    Oddiy ai_savol_yuborish dan farqi:
    - Custom system prompt qabul qiladi
    - Raw text qaytaradi (JSON parse qilmaydi — planner o'zi qiladi)
    - Suhbat tarixini oladi
    
    Args:
        prompt: Foydalanuvchi matni + kontekst
        system_prompt: Agent system prompt (tool'lar bilan)
        history: Suhbat tarixi (ixtiyoriy)
    
    Returns:
        AI javobi (raw text)
    """
    # 1. Multi-Provider Router orqali urinish (Groq Llama 3.3 70B, Cerebras, Gemini, OpenRouter)
    try:
        from core.providers import get_provider_system
        from core.intelligence.types import AIRequest
        ps = get_provider_system()
        if ps.is_any_available():
            conv = []
            if history:
                for msg in history[-10:]:
                    role = msg.get("role", "user")
                    c = msg.get("content", "")
                    if c:
                        conv.append({"role": role, "content": c})
            req = AIRequest(
                message=prompt,
                system_context={"prompt": system_prompt},
                conversation=conv,
                metadata={"requires_tool": True, "task": "tool_calling"}
            )
            resp = ps.generate(req)
            if resp and resp.success and (resp.raw_text or resp.content):
                return resp.raw_text or resp.content
    except Exception as e:
        logging.warning(f"Agent Multi-Provider chaqirishda xatolik: {e}")

    # Gemini orqali an'anaviy urinish
    try:
        result = _agent_gemini_call(prompt, system_prompt, history)
        if result:
            return result
    except Exception as e:
        logging.warning(f"Agent Gemini xatolik: {e}")
    
    # OpenRouter fallback
    try:
        result = _agent_openrouter_call(prompt, system_prompt, history)
        if result:
            return result
    except Exception as e:
        logging.warning(f"Agent OpenRouter xatolik: {e}")
    
    return ""


def _agent_gemini_call(prompt: str, system_prompt: str, history: list = None) -> str:
    """Agent uchun Gemini API — suhbat tarixi bilan"""
    GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    
    # History ni Gemini formatiga aylantirish
    gemini_contents = []
    if history:
        for msg in history[-10:]:  # Oxirgi 10 ta xabar
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            if content:
                gemini_contents.append({"role": role, "parts": [{"text": content}]})
    
    # Oxirgi prompt qo'shish
    gemini_contents.append({"role": "user", "parts": [{"text": prompt}]})
    
    for i, model in enumerate(GEMINI_MODELS):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            
            gen_config = {"maxOutputTokens": 1024, "temperature": 0.3}
            if "2.5" in model:
                gen_config["thinkingConfig"] = {"thinkingBudget": 0}
            
            # Birinchi model uchun 10s, keyingilar 8s
            timeout = 10 if i == 0 else 8
            
            request_body = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": gemini_contents,
                "generationConfig": gen_config,
            }
            
            response = requests.post(
                f"{url}?key={GOOGLE_API_KEY}",
                headers={"Content-Type": "application/json"},
                json=request_body,
                timeout=timeout
            )
            
            if response.status_code == 429:
                continue
            if response.status_code != 200:
                continue
            
            data = response.json()
            candidates = data.get("candidates") or []
            if not candidates:
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            ai_text = ""
            for part in parts:
                if "text" in part:
                    ai_text += part["text"]
            
            return ai_text.strip()
        except Exception as e:
            logging.error(f"Agent Gemini {model} xatolik: {e}")
            continue
    
    return ""


def _agent_openrouter_call(prompt: str, system_prompt: str, history: list = None) -> str:
    """Agent uchun OpenRouter API — suhbat tarixi bilan"""
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    # History ni OpenRouter formatiga aylantirish
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history[-10:]:  # Oxirgi 10 ta xabar
            role = msg.get("role", "user")
            if role == "model":
                role = "assistant"
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.3,
            },
            timeout=10  # Fallback — tezroq
        )
        
        if response.status_code != 200:
            return ""
        
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logging.error(f"Agent OpenRouter xatolik: {e}")
        return ""

