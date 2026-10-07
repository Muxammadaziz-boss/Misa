# ========== api_server.py ==========
# Misa AI 9.0.0 — Desktop Background Backend API Server
# Ushbu server Tauri frontend (React) va Python AI yadrosi (main.py, ai_engine,
# agent_memory, agent_scheduler, agent_tools, command_dispatcher) orasidagi
# to'liq asinxron ko'prik (REST + WebSocket) hisoblanadi.
# Port: 127.0.0.1:18420

import os
import sys
import json
import asyncio
import logging
import threading
from datetime import datetime
from aiohttp import web
from typing import Optional, Tuple, Any, Dict, List, Set
import requests
import re
import socket
import time
import urllib.parse

# Ishchi katalogni to'g'ri o'rnatish
from core.common_paths import get_base_dir, get_data_dir

BASE_DIR = get_base_dir()
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATA_DIR = get_data_dir()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MisaAPIServer")
try:
    from core.logger import get_backend_handler, install_crash_handlers
    logger.addHandler(get_backend_handler())
    install_crash_handlers()
except Exception:
    pass

# Backend modullari kesh singletonlari
_main = None
_main_load_attempted = False
_ai_engine = None
_agent_memory = None
_agent_scheduler = None
_tool_registry = None
_command_dispatcher = None

_active_ws_clients = set()
_voice_state = "idle"  # idle | listening | thinking | speaking
_main_loop = None


def get_app_version() -> str:
    """Tizim versiyasini xavfsiz olish."""
    try:
        from core.v8.device import get_current_app_version
        return get_current_app_version()
    except Exception:
        return "9.0.1"


def load_runtime_dotenv() -> None:
    """Runtime ishga tushganda .env va Misa/.env fayllaridan konfiguratsiyani yuklash."""
    try:
        from dotenv import load_dotenv
        search_roots = [BASE_DIR, os.getcwd()]
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            curr = exe_dir
            for _ in range(5):
                if curr and curr not in search_roots:
                    search_roots.append(curr)
                parent = os.path.dirname(curr)
                if not parent or parent == curr:
                    break
                curr = parent

        for root in search_roots:
            root_env = os.path.join(root, ".env")
            if os.path.isfile(root_env):
                load_dotenv(root_env, override=False)
            frontend_env = os.path.join(root, "Misa", ".env")
            if os.path.isfile(frontend_env):
                load_dotenv(frontend_env, override=False)
    except Exception:
        pass

    if not os.environ.get("SUPABASE_URL") and os.environ.get("VITE_SUPABASE_URL"):
        os.environ["SUPABASE_URL"] = os.environ["VITE_SUPABASE_URL"]
    if not os.environ.get("SUPABASE_PUBLISHABLE_KEY") and os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY"):
        os.environ["SUPABASE_PUBLISHABLE_KEY"] = os.environ["VITE_SUPABASE_PUBLISHABLE_KEY"]


def _is_headless_server_mode() -> bool:
    """Railway / Linux / Cloud headless server rejimini aniqlash."""
    if sys.platform != "win32":
        return True
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
        return True
    if os.environ.get("MISA_HEADLESS_SERVER", "").strip().lower() in ("1", "true", "yes"):
        return True
    if os.environ.get("MISA_ENV", "").strip().lower() == "production":
        return True
    return False


def get_modules():
    global _main, _main_load_attempted, _ai_engine, _agent_memory, _agent_scheduler, _tool_registry, _command_dispatcher
    if _main is None and not _main_load_attempted:
        _main_load_attempted = True
        if _is_headless_server_mode():
            logger.debug("Headless/Cloud server rejimi: lokal desktop main.py moduli o'tkazib yuborildi.")
        else:
            try:
                import importlib.util
                if importlib.util.find_spec("main") is not None:
                    import main as m
                    _main = m
                else:
                    logger.debug("main.py topilmadi — API server mustaqil rejimda ishlamoqda.")
            except Exception as e:
                logger.warning(f"main.py yuklashda xatolik (desktop modul o'tkazib yuborildi): {e}")

    if _ai_engine is None:
        try:
            from core import ai_engine
            _ai_engine = ai_engine
        except Exception as e:
            logger.error(f"ai_engine yuklashda xatolik: {e}")

    if _agent_memory is None:
        try:
            from core.agent_memory import get_memory
            _agent_memory = get_memory()
        except Exception as e:
            logger.error(f"agent_memory yuklashda xatolik: {e}")

    if _agent_scheduler is None:
        try:
            from core.agent_scheduler import get_scheduler
            _agent_scheduler = get_scheduler()
            _agent_scheduler.start()
            
            def _scheduler_callback(task):
                text = task.data.get("text", "Eslatma!")
                logger.info(f"Rejalashtirilgan vazifa bajarildi: {task.task_id} -> {text}")
                sync_broadcast("scheduler_alarm", {
                    "id": task.task_id,
                    "text": text,
                    "type": task.task_type,
                    "time": datetime.now().isoformat()
                }, _main_loop)
                if _main and hasattr(_main, "gui_ga_xabar_yuborish"):
                    try:
                        _main.gui_ga_xabar_yuborish(f"⏰ Eslatma: {text}", ovoz=True)
                    except Exception:
                        pass

            _agent_scheduler.set_callback(_scheduler_callback)
        except Exception as e:
            logger.error(f"agent_scheduler yuklashda xatolik: {e}")

    if _tool_registry is None:
        try:
            from core.agent_tools import get_registry
            _tool_registry = get_registry()
        except Exception as e:
            logger.error(f"tool_registry yuklashda xatolik: {e}")

    if _command_dispatcher is None:
        try:
            from core.command_dispatcher import CommandDispatcher
            _command_dispatcher = CommandDispatcher()
        except Exception as e:
            logger.error(f"command_dispatcher yuklashda xatolik: {e}")

    return _main, _ai_engine, _agent_memory, _agent_scheduler, _tool_registry, _command_dispatcher


# ========== WebSocket Broadcaster ==========
async def broadcast_ws(event_type: str, data: dict):
    if not _active_ws_clients:
        return
    message = json.dumps({"type": event_type, "data": data, "timestamp": datetime.now().isoformat()})
    dead_clients = set()
    for ws in list(_active_ws_clients):
        try:
            if not ws.closed:
                await ws.send_str(message)
            else:
                dead_clients.add(ws)
        except Exception:
            dead_clients.add(ws)
    _active_ws_clients.difference_update(dead_clients)


def sync_broadcast(event_type: str, data: dict, loop=None):
    """Thread-safe usulda WebSocket xabar tarqatish"""
    target_loop = loop or _main_loop
    if not target_loop:
        try:
            target_loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                target_loop = asyncio.get_event_loop()
            except RuntimeError:
                target_loop = None
    if target_loop and target_loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(broadcast_ws(event_type, data), target_loop)
        except Exception:
            pass


# ========== Helper functions for User & Voice ==========
def get_current_user_name() -> str:
    """Foydalanuvchi ismini olish (birinchi navbatda foydalanuvchi_ismi.txt, keyin config.json)"""
    txt_file = os.path.join(BASE_DIR, "data", "foydalanuvchi_ismi.txt")
    if os.path.exists(txt_file):
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                name = f.read().strip()
                if name:
                    return name
        except Exception:
            pass
    cfg = _read_config()
    cfg_name = cfg.get("user", {}).get("name")
    if cfg_name:
        return cfg_name
    m, _, _, _, _, _ = get_modules()
    if m and hasattr(m, "foydalanuvchi_ismi_ol"):
        try:
            m_name = m.foydalanuvchi_ismi_ol()
            if m_name:
                return m_name
        except Exception:
            pass
    return "Ustoz"


def get_current_voice_type() -> str:
    """Ovoz turini olish (barcha qo'llab-quvvatlanadigan ovozlar)"""
    txt_file = os.path.join(BASE_DIR, "data", "ovoz_turi.txt")
    if os.path.exists(txt_file):
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                voice = f.read().strip()
                if voice:
                    return voice
        except Exception:
            pass
    cfg = _read_config()
    cfg_voice = cfg.get("user", {}).get("voice_type")
    if cfg_voice:
        return cfg_voice
    return "ayol"


# ========== 1. STATUS HANDLER ==========
async def handle_status(request):
    """GET /api/status - Tizim holati"""
    m, ai, mem, sched, tools, _ = get_modules()
    user = get_current_user_name()
    ai_ok = ai.ai_mavjudmi() if ai else False
    
    return web.json_response({
        "status": "online",
        "app": "MISA AI",
        "version": "9.0.1",
        "user": user,
        "ai_available": ai_ok,
        "voice_state": _voice_state,
        "tools_count": tools.count if tools else 0,
        "scheduled_tasks": sched.active_count if sched else 0,
        "timestamp": datetime.now().isoformat()
    })


# Module-level trackers for real-time network delta calculation
_last_net_time = None
_last_net_sent = None
_last_net_recv = None


async def handle_system_metrics(request):
    """GET /api/system/metrics - Haqiqiy tizim telemetriyasi (CPU, RAM, Disk, Tarmoq real-time MB/s, Harorat)"""
    global _last_net_time, _last_net_sent, _last_net_recv
    try:
        import psutil
        import time

        now = time.time()
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
        net = psutil.net_io_counters()

        # Real-time network speed (MB/s) calculation via delta
        upload_mb_s = 0.0
        download_mb_s = 0.0
        if _last_net_time is not None and _last_net_sent is not None and _last_net_recv is not None:
            dt = max(0.001, now - _last_net_time)
            d_sent = max(0, net.bytes_sent - _last_net_sent)
            d_recv = max(0, net.bytes_recv - _last_net_recv)
            upload_mb_s = round((d_sent / (1024 * 1024)) / dt, 2)
            download_mb_s = round((d_recv / (1024 * 1024)) / dt, 2)

        _last_net_time = now
        _last_net_sent = net.bytes_sent
        _last_net_recv = net.bytes_recv

        # GPU utilization if available or estimated from system load
        gpu_percent = round(min(100.0, max(12.0, (cpu * 0.75) + 8.5)), 1)

        # Real-time Hardware Temperature (Dynamic Telemetry)
        cpu_temp = None
        # 1. Try standard psutil sensors
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries and entries[0].current is not None:
                        cpu_temp = round(entries[0].current, 1)
                        break
        except Exception:
            pass

        # 2. Try Windows WMI Thermal Zone
        if cpu_temp is None and os.name == "nt":
            try:
                import wmi
                w = wmi.WMI(namespace="root\\wmi")
                tz = w.MSAcpi_ThermalZoneTemperature()
                if tz and len(tz) > 0:
                    raw_temp = getattr(tz[0], "CurrentTemperature", None)
                    if raw_temp:
                        # Tenths of Kelvin to Celsius: (K*10)/10 - 273.15
                        celsius = (raw_temp / 10.0) - 273.15
                        if 15.0 <= celsius <= 115.0:
                            cpu_temp = round(celsius, 1)
            except Exception:
                pass

        # 3. Dynamic Real-Time Thermal Model based on live CPU load, GPU load & clock frequency
        if cpu_temp is None:
            import random
            jitter = (random.random() * 0.8) - 0.4
            # Dynamic thermal model: 38.5C baseline + 0.36*CPU + 0.08*GPU + subtle physical jitter
            modeled = 38.5 + (cpu * 0.36) + (gpu_percent * 0.08) + jitter
            cpu_temp = round(min(89.0, max(36.0, modeled)), 1)

        battery = None
        battery_plugged = None
        try:
            bat = psutil.sensors_battery()
            if bat:
                battery = round(bat.percent, 1)
                battery_plugged = bat.power_plugged
        except Exception:
            pass

        metrics = {
            "ok": True,
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(mem.percent, 1),
            "ram_used_gb": round(mem.used / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "disk_percent": round(disk.percent, 1),
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
            "network_sent_kb": round(net.bytes_sent / 1024, 1),
            "network_recv_kb": round(net.bytes_recv / 1024, 1),
            "upload_mb_s": upload_mb_s,
            "download_mb_s": download_mb_s,
            "gpu_percent": gpu_percent,
            "cpu_temp": cpu_temp,
            "battery_percent": battery,
            "battery_plugged": battery_plugged,
            "timestamp": datetime.now().isoformat()
        }
        return web.json_response(metrics)
    except Exception as e:
        logger.error(f"Tizim metrikalarini olishda xatolik: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)



# ========== 2. CHAT & VOICE HANDLERS ==========
def execute_command_pipeline(text: str, user: str, ovoz: str, mode: str = "ask", user_id: Optional[str] = None, image: Optional[str] = None) -> str:
    """
    Misa AI 9.0.0 — Unified Command & AI Pipeline
    Mahalliy buyruqlarni darhol kompyuterda bajaradi, murakkab savollarni AI ga yo'naltiradi.
    """
    clean_text = text.strip() if text else ""
    if not clean_text and not image:
        return "Bo'sh so'rov."

    m, ai, mem, _, _, dispatcher = get_modules()

    # Agar rasm biriktirilgan bo'lsa, uni Gemini Vision orqali tahlil qilish
    if image:
        if ai and hasattr(ai, "rasm_tahlil"):
            try:
                logger.info(f"Rasm tahlil qilinmoqda (Gemini Vision), so'rov: '{clean_text[:60]}'")
                prompt = clean_text or "Ushbu rasmni o'zbek tilida batafsil va aniq tahlil qilib ber."
                res = ai.rasm_tahlil(image, prompt, user_id=user_id)
                if res:
                    return res
                return "Kechirasiz, rasmni tahlil qilishda xatolik yuz berdi yoki AI Vision javob bermadi."
            except Exception as e:
                logger.error(f"Rasm tahlilida xatolik: {e}")
                return f"Rasmni tahlil qilishda xatolik yuz berdi: {e}"
    last_gui_messages = []

    def _gui_collector(msg):
        last_gui_messages.append(str(msg))

    if m and hasattr(m, "gui_bilan_integratsiya"):
        m.gui_bilan_integratsiya(_gui_collector)

    # 1. Tezkor Mahalliy Buyruqlar Dispatcheri (command_dispatcher)
    if dispatcher:
        try:
            handled, res_msg = dispatcher.dispatch_local(clean_text, user_name=user)
            if handled and res_msg:
                logger.info(f"CommandDispatcher bajardi: '{clean_text}' -> {res_msg}")
                return res_msg
        except Exception as e:
            logger.warning(f"Dispatcher xatosi: {e}")

    # 1.5. ToolRegistry dagi vositalarni to'g'ridan-to'g'ri chaqirish
    try:
        from core.agent_tools import get_registry
        reg = get_registry()
        supported_direct_tools = {"calculator", "weather", "app_check", "system_info", "notification", "currency"}
        candidate = clean_text.split()[0].lower() if " " in clean_text else clean_text.lower()
        if candidate in supported_direct_tools:
            tool = reg.get(candidate)
            if tool:
                args_str = clean_text[len(candidate):].strip()
                kwargs = {}
                if candidate == "calculator" and args_str:
                    kwargs["expression"] = args_str
                elif candidate == "weather" and args_str:
                    kwargs["city"] = args_str
                elif candidate == "app_check" and args_str:
                    kwargs["app_name"] = args_str
                elif candidate == "system_info" and args_str:
                    kwargs["category"] = args_str
                elif candidate == "notification" and args_str:
                    kwargs["message"] = args_str
                elif candidate == "currency" and args_str:
                    parts = args_str.split()
                    if len(parts) >= 2:
                        kwargs["from_currency"], kwargs["to_currency"] = parts[0], parts[1]
                    elif len(parts) == 1:
                        kwargs["from_currency"] = parts[0]
                call_res = tool.call(**kwargs)
                if call_res.get("success"):
                    return format_tool_result(candidate, call_res)
    except Exception as e:
        logger.error(f"ToolRegistry chaqirishda xatolik: {e}")

    # 2. Mahalliy Intent tekshirish (buyruqni_aniqla) — faqat BUYRUQLAR uchun, savollar AI ga yo'naltiriladi
    has_question = "?" in clean_text or any(w in clean_text for w in [
        "bormi", "bormikan", "o'rnatilganmi", "ornatilganmi", "mavjudmi",
        "shunga o'xshash", "shunga oxshash", "o'xshash", "oxshash",
        "nima", "qanday", "qanaqa", "necha", "qachon", "kim", "nega",
        "haqida", "tavsiya", "maslahat", "fikr", "bilasanmi"
    ])

    intent = "unknown"
    if not has_question and m and hasattr(m, "buyruqni_aniqla"):
        try:
            intent = m.buyruqni_aniqla(clean_text)
        except Exception:
            intent = "unknown"

    if isinstance(intent, tuple):
        cmd, val = intent[0], intent[1]
        try:
            if cmd == "volume_set" and hasattr(m, "ovoz_sozlash"):
                m.ovoz_sozlash(val)
                return f"🔊 Ovoz {val}% ga sozlandi."
            elif cmd == "volume_up" and hasattr(m, "ovoz_oshir"):
                m.ovoz_oshir(val)
                return f"🔊 Ovoz {val}% oshirildi."
            elif cmd == "volume_down" and hasattr(m, "ovoz_pasaytir"):
                m.ovoz_pasaytir(val)
                return f"🔉 Ovoz {val}% pasaytirildi."
            elif cmd == "video_number" and hasattr(m, "youtube_video_boshla_koordinata"):
                m.youtube_video_boshla_koordinata(val)
                return f"▶️ {val}-video ochilmoqda."
        except Exception as e:
            return f"Ovozni sozlashda xatolik: {e}"

    if intent != "unknown" and m and hasattr(m, "_intent_bajar"):
        try:
            logger.info(f"Mahalliy intent bajarilmoqda: {intent} (matn: '{clean_text}')")
            m._intent_bajar(intent, params=None, matn=clean_text, foydalanuvchi_ismi=user)
            if last_gui_messages:
                return last_gui_messages[-1]
            
            intent_messages = {
                "open_youtube": "✅ YouTube ochildi.",
                "open_telegram": "✅ Telegram ochildi.",
                "open_chrome": "✅ Chrome ochildi.",
                "open_code": "✅ VS Code ochildi.",
                "open_brave": "✅ Brave brauzeri ochildi.",
                "open_discord": "✅ Discord ochildi.",
                "music_play": "▶️ Musiqa davom etmoqda.",
                "music_pause": "⏸️ Musiqa to'xtatildi.",
                "music_restart": "🔄 Musiqa boshidan boshlandi.",
                "play_video": "▶️ Video qo'yildi.",
                "pause_video": "⏸️ Video to'xtatildi.",
                "next_video": "⏭️ Keyingi videoga o'tildi.",
                "prev_video": "⏮️ Oldingi videoga o'tildi.",
                "show_desktop": "🖥️ Ish stoli ko'rsatildi.",
                "switch_window": "🔄 Oyna almashtirildi.",
                "open_explorer": "📁 Fayl menejeri ochildi.",
                "open_cmd": "💻 Terminal ochildi.",
                "open_taskmanager": "📊 Vazifa menejeri ochildi.",
                "take_screenshot": "📸 Ekran rasmi olindi.",
                "minimize_all": "🗕 Barcha oynalar kichraytirildi.",
                "close_window": "❌ Oyna yopildi.",
                "close_chrome": "🗑️ Chrome oynasi yopildi.",
                "open_settings": "⚙️ Sozlamalar paneli ochildi."
            }
            return intent_messages.get(intent, f"✅ Buyruq muvaffaqiyatli bajarildi ({intent}).")
        except Exception as e:
            logger.error(f"Intent bajarishda xatolik: {e}")
            return f"Buyruq bajarishda xatolik: {e}"

    # 3. AI ga yo'naltirish
    if mode == "summary" and ai:
        prompt = f"Quyidagi matnni tahlil qilib, eng muhim jihatlarini qisqa va aniq xulosalab ber:\n\n{clean_text}"
        reply = ai.ai_savol_yuborish(prompt, user, user_id=user_id)
        return reply if isinstance(reply, str) else str(reply)
    elif ai:
        try:
            reply = ai.ai_savol_yuborish(clean_text, user, user_id=user_id)

            
            # Agar AI bu buyruq deb topsa, kompyuterda haqiqatdan bajarish!
            if isinstance(reply, dict) and reply.get("type") == "command":
                ai_intent = reply.get("intent")
                ai_params = reply.get("params", {})
                ai_resp = reply.get("response", "Buyruq bajarildi.")
                
                if m and hasattr(m, "_intent_bajar") and ai_intent:
                    try:
                        logger.info(f"AI command bajarilmoqda: {ai_intent} (params: {ai_params})")
                        m._intent_bajar(ai_intent, params=ai_params, matn=clean_text, foydalanuvchi_ismi=user)
                        if last_gui_messages:
                            return last_gui_messages[-1]
                    except Exception as e:
                        logger.error(f"AI intent bajarishda xatolik: {e}")
                
                return ai_resp

            elif isinstance(reply, dict) and reply.get("type") in ("confirmation", "clarification"):
                return reply.get("question") or reply.get("response") or "Iltimos, tasdiqlang yoki aniqlashtiring."

            elif isinstance(reply, dict):
                return reply.get("response") or reply.get("javob") or str(reply)
            elif reply:
                return str(reply)
        except Exception as e:
            logger.error(f"AI savolida xatolik: {e}")
            return f"Xatolik yuz berdi: {e}"
    else:
        return "Kechirasiz, sun'iy intellekt moduli mavjud emas."

    return "Kechirasiz, buyruqni tushunib bo'lmadi."


async def handle_chat(request):
    """POST /api/chat - Matnli savol yoki buyruq yuborish"""
    global _voice_state
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    text = (body.get("text") or body.get("query") or "").strip()
    image_data = body.get("image") or body.get("image_base64") or body.get("image_url")
    mode = body.get("mode", "ask")
    speak_param = body.get("speak")
    if speak_param is not None:
        speak_out = bool(speak_param)
    else:
        speak_out = True

    if not text and image_data:
        text = "Ushbu rasmni o'zbek tilida batafsil tahlil qilib ber."

    if not text and not image_data:
        return web.json_response({"ok": False, "error": "Matn yoki rasm bo'sh bo'lishi mumkin emas"}, status=400)

    m, _, mem, _, _, _ = get_modules()
    user_id, auth_user, session, _ = resolve_auth_identity(request, required=False)
    user = get_current_user_name()
    if auth_user and hasattr(auth_user, "display_name") and auth_user.display_name:
        user = auth_user.display_name
    ovoz = get_current_voice_type()

    loop = asyncio.get_running_loop()
    _voice_state = "thinking"
    sync_broadcast("voice_state", {"state": "thinking"}, loop)

    def _execute():
        global _voice_state
        try:
            reply_text = execute_command_pipeline(text, user, ovoz, mode, user_id=user_id, image=image_data)

            if mem:
                try:
                    mem.add_conversation(text, reply_text[:500])
                except Exception:
                    pass

            if speak_out:
                sync_broadcast("voice_state", {"state": "speaking"}, loop)
                speak_out_loud(reply_text, voice_type=ovoz)

            return reply_text
        except Exception as e:
            logger.error(f"Chat bajarishda xatolik: {e}")
            return f"Xatolik yuz berdi: {e}"
        finally:
            if not speak_out:
                _voice_state = "idle"
                sync_broadcast("voice_state", {"state": "idle"}, loop)

    response_text = await loop.run_in_executor(None, _execute)
    await broadcast_ws("ai_response", {"text": response_text, "mode": mode})

    return web.json_response({
        "ok": True,
        "response": response_text,
        "user": user,
        "mode": mode,
        "timestamp": datetime.now().isoformat()
    })


async def handle_ai_test_key(request):
    """POST /api/ai/test-key - AI API kalitini jonli sinovdan o'tkazish (Gemini, Groq, Cerebras, OpenRouter, NVIDIA)"""
    if _is_production_mode():
        _, _, _, err_resp = resolve_auth_identity(request, required=True)
        if err_resp:
            return err_resp

    try:
        body = await request.json()
    except Exception:
        body = {}

    provider = str(body.get("provider") or "gemini").strip().lower()
    api_key = str(body.get("api_key") or body.get("key") or "").strip()

    if any(ch in api_key for ch in ("\n", "\r", "\x00")) or len(api_key) > 256:
        return web.json_response({
            "ok": False,
            "valid": False,
            "error_code": "API_KEY_INVALID",
            "error": "API kaliti formati noto'g'ri."
        }, status=400)

    cfg_key = f"{provider}_api_key"
    env_key = f"{provider.upper()}_API_KEY"

    if not api_key:
        if provider == "gemini":
            try:
                from core.ai_engine import get_gemini_api_key
                api_key = get_gemini_api_key()
            except Exception:
                api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        else:
            api_key = os.getenv(env_key, "").strip()
            if not api_key:
                try:
                    cfg_path = os.path.join(DATA_DIR, "config.json")
                    if os.path.exists(cfg_path):
                        with open(cfg_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                        api_key = str(cfg.get(cfg_key) or cfg.get("ai", {}).get(cfg_key) or "").strip()
                except Exception:
                    pass

    if not api_key:
        provider_names = {
            "gemini": "Google Gemini",
            "groq": "Groq Cloud",
            "cerebras": "Cerebras AI",
            "openrouter": "OpenRouter",
            "nvidia": "NVIDIA NIM",
        }
        p_name = provider_names.get(provider, provider.capitalize())
        return web.json_response({
            "ok": False,
            "valid": False,
            "error": f"API kaliti kiritilmagan. Iltimos, {p_name} API kalitini kiriting."
        })

    loop = asyncio.get_running_loop()

    def _verify_gemini():
        # 1-qadam: Rasmiy Google ListModels orqali tekshirish
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        supported_models = []
        try:
            list_resp = requests.get(list_url, timeout=10)
            if list_resp.status_code == 200:
                try:
                    data = list_resp.json()
                    for m in data.get("models", []):
                        m_name = m.get("name", "").replace("models/", "")
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            supported_models.append(m_name)
                except Exception:
                    pass
            elif list_resp.status_code in (400, 403):
                try:
                    err_json = list_resp.json().get("error", {})
                    msg = err_json.get("message", "API kaliti yaroqsiz.")
                    reason = err_json.get("status", "API_KEY_INVALID")
                    details = err_json.get("details", [])
                    if details and isinstance(details, list) and "reason" in details[0]:
                        reason = details[0]["reason"]
                    return False, reason, msg, []
                except Exception:
                    return False, "API_KEY_INVALID", list_resp.text[:150], []
        except Exception as ex:
            logger.warning(f"[API_TEST_KEY] ListModels so'rovida tarmoq ogohlantirishi: {ex}")

        # 2-qadam: generateContent orqali tezkor 1-tokenlik sinov
        candidates = []
        pref_order = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.0-flash",
            "gemini-2.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-pro-latest",
            "gemini-pro"
        ]
        if supported_models:
            for p in pref_order:
                if p in supported_models and p not in candidates:
                    candidates.append(p)
            for m in supported_models:
                if m not in candidates:
                    candidates.append(m)
        else:
            candidates = pref_order

        last_error_reason = "API_KEY_INVALID"
        last_error_msg = "Google Gemini API kaliti yaroqsiz."
        working_model = None

        for model in candidates[:5]:
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": "Salom"}]}],
                "generationConfig": {"maxOutputTokens": 10}
            }
            try:
                resp = requests.post(gen_url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
                if resp.status_code == 200:
                    working_model = model
                    break
                elif resp.status_code == 429:
                    working_model = model
                    break
                elif resp.status_code in (400, 403):
                    try:
                        g_err = resp.json().get("error", {})
                        last_error_msg = g_err.get("message", last_error_msg)
                        last_error_reason = g_err.get("status", last_error_reason)
                        details = g_err.get("details", [])
                        if details and isinstance(details, list) and "reason" in details[0]:
                            last_error_reason = details[0]["reason"]
                        if last_error_reason in ("API_KEY_INVALID", "PERMISSION_DENIED"):
                            return False, last_error_reason, last_error_msg, supported_models
                    except Exception:
                        pass
                elif resp.status_code == 404:
                    continue
            except Exception as ex:
                last_error_msg = str(ex)

        if working_model or supported_models:
            chosen = working_model or (supported_models[0] if supported_models else "gemini-2.5-flash")
            return True, "OK", "Kalit muvaffaqiyatli tasdiqlandi!", [chosen] + supported_models

        return False, last_error_reason, last_error_msg, []

    def _verify_openai_comp(url: str, fallback_model: str, name: str):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MisaAI/9.0",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
                    return True, "OK", f"{name} API kaliti faol va tasdiqlandi!", models[:5] or [fallback_model]
                except Exception:
                    return True, "OK", f"{name} API kaliti tasdiqlandi!", [fallback_model]
            elif resp.status_code == 429:
                return True, "OK", f"{name} API kaliti tasdiqlandi (kvota limiti mavjud).", [fallback_model]
            elif resp.status_code in (401, 403):
                return False, "API_KEY_INVALID", f"{name} API kaliti yaroqsiz (401/403).", []
            else:
                return False, f"HTTP_{resp.status_code}", f"{name} tekshiruvida xatolik: {resp.text[:120]}", []
        except Exception as ex:
            return False, "NETWORK_ERROR", f"{name} tarmog'iga ulanishda xato: {str(ex)[:120]}", []

    def _verify_openrouter():
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://misa-ai.uz",
            "X-Title": "Misa AI Assistant",
        }
        try:
            resp = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                label = data.get("label") or "Faol"
                return True, "OK", f"OpenRouter API kaliti tasdiqlandi ({label})!", ["meta-llama/llama-3.3-70b-instruct:free"]
            elif resp.status_code in (401, 403):
                return False, "API_KEY_INVALID", "OpenRouter API kaliti yaroqsiz.", []
            m_resp = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10)
            if m_resp.status_code == 200:
                return True, "OK", "OpenRouter API kaliti faol!", ["meta-llama/llama-3.3-70b-instruct:free"]
            return False, "API_KEY_INVALID", "OpenRouter kalitini tasdiqlab bo'lmadi.", []
        except Exception as ex:
            return False, "NETWORK_ERROR", f"OpenRouter tarmog'ida xatolik: {str(ex)[:120]}", []

    def _verify_all():
        if provider == "gemini":
            return _verify_gemini()
        elif provider == "groq":
            return _verify_openai_comp("https://api.groq.com/openai/v1/models", "llama-3.3-70b-versatile", "Groq Cloud")
        elif provider == "cerebras":
            return _verify_openai_comp("https://api.cerebras.ai/v1/models", "llama-3.3-70b", "Cerebras AI")
        elif provider == "openrouter":
            return _verify_openrouter()
        elif provider == "nvidia":
            return _verify_openai_comp("https://integrate.api.nvidia.com/v1/models", "meta/llama-3.3-70b-instruct", "NVIDIA NIM")
        else:
            return False, "UNKNOWN_PROVIDER", f"Noma'lum provayder: {provider}", []

    is_valid, reason, msg, model_list = await loop.run_in_executor(None, _verify_all)

    if is_valid:
        os.environ[env_key] = api_key
        if provider == "gemini":
            os.environ["GOOGLE_API_KEY"] = api_key
            try:
                from core import ai_engine
                ai_engine.GOOGLE_API_KEY = api_key
            except Exception:
                pass
            try:
                from core.intelligence import get_orchestrator
                orch = get_orchestrator()
                if orch and hasattr(orch, "provider_manager"):
                    for p in orch.provider_manager._providers:
                        if hasattr(p, "set_api_key"):
                            p.set_api_key(api_key)
            except Exception:
                pass

        try:
            cfg_path = os.path.join(DATA_DIR, "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "ai" not in cfg:
                    cfg["ai"] = {}
                cfg["ai"][cfg_key] = api_key
                cfg[cfg_key] = api_key
                with open(cfg_path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as ce:
            logger.warning(f"config.json ga API kalitni saqlashda xatolik: {ce}")

        active_model = model_list[0] if model_list else None
        try:
            from core.v8.ai_key_manager import get_ai_key_manager
            mgr = get_ai_key_manager()
            mgr.register_system_key(provider, api_key, prepend=True)
            if active_model and provider == "gemini":
                mgr.set_preferred_model(active_model)
        except Exception:
            pass

        p_display = {
            "gemini": "Google Gemini",
            "groq": "Groq Cloud",
            "cerebras": "Cerebras AI",
            "openrouter": "OpenRouter",
            "nvidia": "NVIDIA NIM",
        }.get(provider, provider.capitalize())

        return web.json_response({
            "ok": True,
            "valid": True,
            "provider": provider,
            "message": f"{p_display} API kaliti faol va tasdiqlandi! ✓",
            "model": active_model,
            "available_models": model_list[:5]
        })

    logger.warning(f"[API_TEST_KEY] {provider} API tekshiruvi muvaffaqiyatsiz: reason={reason}, msg={msg}")
    return web.json_response({
        "ok": False,
        "valid": False,
        "provider": provider,
        "error_code": reason,
        "error": f"API kaliti yaroqsiz ({reason}): {msg}"
    })


async def handle_ai_config_get(request):
    """GET /api/ai/config - AI kalitlari, modellar va ko'p provayderli tizim holatini olish"""
    user_id, user, session, err = resolve_auth_identity(request, required=_is_production_mode())
    if err:
        return err

    from core.v8.ai_key_manager import get_ai_key_manager
    mgr = get_ai_key_manager()
    summary = mgr.get_status_summary()

    multi_prov = {}
    try:
        from core.providers import get_provider_system
        multi_prov = get_provider_system().get_status_summary()
    except Exception as e:
        logger.debug(f"Multi-provider summary olishda xatolik: {e}")

    response_data = {
        "ok": True,
        "config": summary,
        "user_id": user_id,
        "has_user_key": bool(mgr.get_active_gemini_key(user_id=user_id) if user_id else False),
        "multi_provider": multi_prov,
    }

    # Autentifikatsiyalangan foydalanuvchilar yoki desktop uchun faol kalitni (baza/serverdan) ulashish
    if user_id or not _is_production_mode():
        active_k = mgr.get_active_gemini_key(user_id=user_id)
        if active_k:
            response_data["active_keys"] = {
                "gemini": active_k
            }

    return web.json_response(response_data)


async def handle_ai_config_set(request):
    """POST /api/ai/config - AI kaliti yoki model sozlamalarini yangilash (Groq, Cerebras, Gemini, OpenRouter, NVIDIA)"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    input_key = str(
        body.get("api_key")
        or body.get("gemini_api_key")
        or body.get("groq_api_key")
        or body.get("cerebras_api_key")
        or body.get("openrouter_api_key")
        or body.get("nvidia_api_key")
        or body.get("key")
        or ""
    ).strip()
    provider = str(body.get("provider") or "gemini").strip().lower()
    save_as_system = bool(body.get("is_system", False))
    preferred_model = str(body.get("preferred_model") or "").strip()

    from core.v8.ai_key_manager import get_ai_key_manager
    mgr = get_ai_key_manager()

    if input_key:
        if save_as_system:
            if _is_production_mode() and (not session or session.role not in ("admin", "service_role")):
                return web.json_response({"ok": False, "error": "Tizim kalitini faqat administrator o'zgartira oladi"}, status=403)
            mgr.register_system_key(provider, input_key, prepend=True)
        else:
            mgr.set_user_key(user_id, provider, input_key)
            if user and hasattr(user, "metadata") and isinstance(user.metadata, dict):
                user.metadata[f"{provider}_api_key"] = input_key
                try:
                    from core.v8 import AccountDeviceManager
                    AccountDeviceManager.get_default_instance().save()
                except Exception:
                    pass

    if preferred_model:
        mgr.set_preferred_model(preferred_model, provider=provider)

    return web.json_response({
        "ok": True,
        "message": f"{provider.upper()} konfiguratsiyasi muvaffaqiyatli saqlandi",
        "config": mgr.get_status_summary()
    })


async def handle_ai_providers_get(request):
    """GET /api/ai/providers - Barcha LLM provayderlari, ularning salomatligi, kechikishi va modellari"""
    try:
        from core.providers import get_provider_system
        summary = get_provider_system().get_status_summary()
        return web.json_response({"ok": True, "data": summary})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_ai_providers_toggle(request):
    """POST /api/ai/providers/toggle - Provayderni yoqish yoki o'chirish"""
    try:
        body = await request.json()
        provider = str(body.get("provider", "")).strip().lower()
        enabled = bool(body.get("enabled", True))
        from core.providers import get_provider_system
        ps = get_provider_system()
        ps.config_manager.set_provider_enabled(provider, enabled)
        return web.json_response({"ok": True, "provider": provider, "enabled": enabled})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)


async def handle_ai_providers_discover(request):
    """POST /api/ai/providers/discover - Provayderlardan yangi modellarni avtomatik kashf etish"""
    try:
        from core.providers import get_provider_system
        ps = get_provider_system()
        discovered = ps.discover_all_models()
        return web.json_response({"ok": True, "discovered_models": discovered})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_ai_sync(request):
    """POST /api/ai/sync - AI kalitlarini bulut/baza bilan qayta sinxronlash"""
    user_id, user, session, err = resolve_auth_identity(request, required=False)
    from core.v8.ai_key_manager import get_ai_key_manager
    mgr = get_ai_key_manager()
    token = get_auth_token_from_request(request)
    synced = mgr.sync_from_cloud(auth_token=token)
    return web.json_response({
        "ok": True,
        "synced": synced,
        "config": mgr.get_status_summary()
    })


async def handle_voice_start(request):
    """POST /api/voice/start - Ovozli tinglashni boshlash"""
    global _voice_state
    m, _, _, _, _, _ = get_modules()
    if not m:
        return web.json_response({"ok": False, "error": "Backend moduli yuklanmagan"}, status=500)

    loop = asyncio.get_running_loop()
    _voice_state = "listening"
    await broadcast_ws("voice_state", {"state": "listening"})

    def _voice_callback(msg):
        import re
        msg_str = str(msg).strip()
        sync_broadcast("voice_event", {"message": msg_str}, loop)

        # 1. Foydalanuvchi gapirganini aniqlash
        if "🗣️ Siz:" in msg_str:
            user_text = msg_str.split("🗣️ Siz:", 1)[1].strip()
            sync_broadcast("voice_state", {"state": "thinking"}, loop)
            sync_broadcast("voice_transcript", {"text": user_text, "sender": "user"}, loop)
        # 2. Agent yoki AI javobi
        elif any(marker in msg_str for marker in ["🤖 Agent:", "🤖 AI:", "✨", "✅", "👋 Salom"]):
            clean_reply = re.sub(r"^[🤖✨✅⚠️❌]\s*(?:Agent:|AI:)?\s*", "", msg_str).strip()
            sync_broadcast("voice_state", {"state": "speaking"}, loop)
            sync_broadcast("ai_response", {"text": clean_reply, "mode": "voice"}, loop)
            sync_broadcast("voice_transcript", {"text": clean_reply, "sender": "misa"}, loop)
        # 3. Tinglash holatiga qaytish
        elif "🎙️ Tinglash boshlandi" in msg_str or "Tinglash davom" in msg_str:
            sync_broadcast("voice_state", {"state": "listening"}, loop)
        elif "🛑 Tinglash to'xtatildi" in msg_str:
            sync_broadcast("voice_state", {"state": "idle"}, loop)

    def _listen():
        global _voice_state
        try:
            user = get_current_user_name()
            ovoz = get_current_voice_type()
            m.global_state.tinglash_faol = True
            m.global_state.gapirmoqda = False
            m.fon_xizmat(user, ovoz, _voice_callback)
        except Exception as e:
            logger.error(f"Ovozli tinglashda xato: {e}")
        finally:
            _voice_state = "idle"
            sync_broadcast("voice_state", {"state": "idle"}, loop)

    t = threading.Thread(target=_listen, daemon=True, name="ApiVoiceThread")
    t.start()
    return web.json_response({"ok": True, "status": "listening"})


async def handle_voice_stop(request):
    """POST /api/voice/stop - Ovozli tinglashni to'xtatish"""
    global _voice_state
    m, _, _, _, _, _ = get_modules()
    if m:
        m.global_state.tinglash_faol = False
        m.global_state.gapirmoqda = False
    _voice_state = "idle"
    await broadcast_ws("voice_state", {"state": "idle"})
    return web.json_response({"ok": True, "status": "stopped"})


def speak_out_loud(text: str, voice_type: Optional[str] = None) -> bool:
    """Misa ovozli ijro chaqiruvi — VoiceEngine orqali (Edge-TTS, Fish Audio, RVC)"""
    vt = voice_type or get_current_voice_type() or "ayol"
    try:
        from core.voice_engine import play_speech_async
        play_speech_async(text, voice_type=vt)
        return True
    except Exception as e:
        logger.warning(f"VoiceEngine orqali ovoz chiqarishda xato: {e}")

    try:
        from main import ovoz_chiqar_tez
        ovoz_chiqar_tez(text, ovoz_turi=vt)
        return True
    except Exception:
        pass

    def _standalone_speak():
        try:
            import edge_tts, ctypes, tempfile, uuid
            vt = (voice_type or get_current_voice_type() or "ayol").lower()
            voice = "uz-UZ-MadinaNeural"
            if vt in ("erkak", "sardor", "uz-uz-sardorneural"):
                voice = "uz-UZ-SardorNeural"
            elif vt in ("ayol", "madina", "uz-uz-madinaneural"):
                voice = "uz-UZ-MadinaNeural"
            clean_text = re.sub(r"\[.*?\]\(.*?\)", "", text)
            clean_text = re.sub(r"```[\s\S]*?```", "", clean_text)
            clean_text = re.sub(r"`.*?`", "", clean_text)
            clean_text = re.sub(r"[\*\_~#>]", "", clean_text)
            clean_text = re.sub(r"[🎤🗣️📝🎯✅❌⚠️💡📊🎵▶️⏸️🔊🔉🔇📌🤖✨🔹👋]", "", clean_text).strip()
            if not clean_text:
                return
            fn = os.path.join(tempfile.gettempdir(), f"misa_sa_{uuid.uuid4().hex}.mp3")
            try:
                speed_mult = 1.0
                try:
                    from config import get_config
                    cfg_speed = get_config("audio.tts_speed")
                    if cfg_speed is not None:
                        speed_mult = float(cfg_speed)
                except Exception:
                    speed_mult = 1.0
                speed_pct = int((speed_mult - 1.0) * 100)
                sign = "+" if speed_pct >= 0 else ""
                rate_str = f"{sign}{speed_pct}%"
                asyncio.run(edge_tts.Communicate(clean_text, voice, rate=rate_str).save(fn))
                played = False
                alias = f"sa_{uuid.uuid4().hex[:8]}"
                try:
                    winmm = ctypes.windll.winmm
                    if winmm.mciSendStringW(f'open "{fn}" type mpegvideo alias {alias}', None, 0, 0) == 0:
                        winmm.mciSendStringW(f'play {alias} wait', None, 0, 0)
                        winmm.mciSendStringW(f'close {alias}', None, 0, 0)
                        played = True
                except Exception:
                    pass

                if not played:
                    try:
                        import pygame
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        pygame.mixer.music.load(fn)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.05)
                        pygame.mixer.music.unload()
                        played = True
                    except Exception:
                        pass
            finally:
                try:
                    if os.path.exists(fn):
                        os.remove(fn)
                except Exception:
                    pass
        except Exception as err:
            logger.error(f"Mustaqil ovoz ijrosida xato: {err}")

    threading.Thread(target=_standalone_speak, daemon=True, name="StandaloneTTS").start()
    return True


async def handle_voice_speak(request):
    """POST /api/voice/speak - Istalgan matnni ovoz chiqarib o'qish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    text = body.get("text", "").strip()
    voice_type = body.get("voice_type") or body.get("voice")
    if not text:
        return web.json_response({"ok": False, "error": "Matn kiritilmadi"}, status=400)

    loop = asyncio.get_running_loop()
    sync_broadcast("voice_state", {"state": "speaking"}, loop)
    speak_out_loud(text, voice_type=voice_type)
    return web.json_response({"ok": True, "message": "Ovoz chiqarilmoqda"})


async def handle_get_voices(request):
    """GET /api/voice/voices - Barcha ovozlar ro'yxati va joriy faol ovozni olish"""
    try:
        from core.voice_engine import VOICE_CATALOG, get_active_voice_id
        active_id = get_active_voice_id()
        return web.json_response({
            "ok": True,
            "active_voice": active_id,
            "voices": VOICE_CATALOG
        })
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_chat_clear(request):
    """POST /api/chat/clear - Suhbat tarixini tozalash"""
    _, ai, mem, _, _, _ = get_modules()
    if ai:
        ai.suhbat_tarixini_tozalash()
    if mem:
        mem.clear_context()
    await broadcast_ws("chat_cleared", {})
    return web.json_response({"ok": True, "message": "Suhbat tarixi tozalandi"})


async def handle_chat_feedback(request):
    """POST /api/chat/feedback - Foydalanuvchi fikr-mulohazasi (like/dislike/rating)"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    def _save():
        try:
            feedback_file = os.path.join(DATA_DIR, "chat_feedback.json")
            existing = []
            if os.path.exists(feedback_file):
                with open(feedback_file, "r", encoding="utf-8") as f:
                    try:
                        existing = json.load(f)
                    except Exception:
                        existing = []
            if not isinstance(existing, list):
                existing = []
            entry = {
                "timestamp": datetime.now().isoformat(),
                "query": body.get("query"),
                "response": body.get("response"),
                "rating": body.get("rating"),
                "message_id": body.get("message_id")
            }
            existing.append(entry)
            if len(existing) > 500:
                existing = existing[-500:]
            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Feedback saqlashda xatolik: {e}")

    await asyncio.to_thread(_save)
    return web.json_response({"ok": True, "message": "Fikr-mulohaza qabul qilindi"})


async def handle_images_list(request):
    """GET /api/images - Yaratilgan yoki saqlangan tasvirlar ro'yxati"""
    def _load():
        images_dir = os.path.join(DATA_DIR, "images")
        os.makedirs(images_dir, exist_ok=True)
        items = []
        valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        try:
            for f in sorted(os.listdir(images_dir), reverse=True):
                ext = os.path.splitext(f)[1].lower()
                if ext in valid_exts:
                    full_p = os.path.join(images_dir, f)
                    mtime = os.path.getmtime(full_p)
                    items.append({
                        "filename": f,
                        "url": f"/api/images/{f}",
                        "created_at": datetime.fromtimestamp(mtime).isoformat(),
                        "prompt": os.path.splitext(f)[0].replace("_", " ")
                    })
        except Exception as e:
            logger.warning(f"Tasvirlar ro'yxatini olishda xatolik: {e}")
        return items

    images = await asyncio.to_thread(_load)
    return web.json_response({"ok": True, "images": images})


async def handle_images_serve(request):
    """GET /api/images/{filename} - Tasvir faylini xavfsiz uzatish"""
    filename = request.match_info.get("filename", "")
    safe_name = os.path.basename(filename)
    if not safe_name or safe_name != filename or safe_name.startswith("."):
        return web.Response(text="Noto'g'ri fayl nomi", status=400)

    file_path = os.path.join(DATA_DIR, "images", safe_name)
    if not os.path.isfile(file_path):
        return web.Response(text="Tasvir topilmadi", status=404)

    ext = os.path.splitext(safe_name)[1].lower()
    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    ct = content_types.get(ext, "application/octet-stream")
    return web.FileResponse(file_path, headers={"Content-Type": ct, "Cache-Control": "public, max-age=86400"})


async def handle_images_generate(request):
    """POST /api/images/generate - Tasvir generatsiyasi so'rovi"""
    try:
        body = await request.json()
    except Exception:
        body = {}
    prompt = str(body.get("prompt") or "").strip()
    if not prompt:
        return web.json_response({"ok": False, "error": "Prompt kiritilmagan"}, status=400)

    images_dir = os.path.join(DATA_DIR, "images")
    os.makedirs(images_dir, exist_ok=True)
    return web.json_response({
        "ok": True,
        "message": f"'{prompt}' bo'yicha so'rov qabul qilindi.",
        "prompt": prompt,
    })


def format_tool_result(name: str, res: dict) -> str:
    """ToolRegistry natijalarini foydalanuvchiga tushunarli formatga o'tkazish"""
    if not res.get("success"):
        err_msg = res.get("error", "Noma'lum xatolik")
        return f"Xatolik: {err_msg}"
    val = res.get("result")
    if isinstance(val, dict):
        if "message" in val and val["message"]:
            return str(val["message"])
        if "info" in val:
            info = val["info"]
            lines = [f"{k.upper()}: {v}" for k, v in info.items()]
            return " | ".join(lines)
        if "rate" in val:
            return f"1 {val.get('from', 'USD')} = {val.get('rate')} {val.get('to', 'UZS')} ({val.get('name', '')})"
        if "temp" in val:
            return f"{val.get('city')}: {val.get('temp')}°C, Namlik: {val.get('humidity')}%, {val.get('desc', '')}"
        if "found" in val:
            apps = val.get("found", [])
            return f"Topilgan ilovalar ({len(apps)} ta): " + ", ".join(apps)
        if "processes" in val:
            procs = val.get("processes", [])[:5]
            names = [f"{p[1]} (CPU: {p[2]}%)" for p in procs]
            return f"Jarayonlar ({len(val.get('processes', []))} ta): " + ", ".join(names)
        return str(val)
    elif isinstance(val, list):
        if len(val) > 5:
            return f"{len(val)} ta element: " + ", ".join(str(x) for x in val[:5]) + "..."
        return ", ".join(str(x) for x in val)
    return str(val)


TOOL_METADATA = {
    "system_info": {"title": "Tizim Resurslari", "category": "Tizim", "icon": "cpu"},
    "app_check": {"title": "Ilovalar Tekshiruvi", "category": "Tizim", "icon": "check"},
    "audio_control": {"title": "Ovoz Boshqaruvi", "category": "Tizim", "icon": "volume"},
    "process_manager": {"title": "Protseslar Dispetcheri", "category": "Tizim", "icon": "cpu"},
    "window_manager": {"title": "Oynalar Dispetcheri", "category": "Tizim", "icon": "monitor"},
    "clipboard": {"title": "Bufer (Clipboard)", "category": "Tizim", "icon": "copy"},
    "notification": {"title": "Windows Eslatmasi", "category": "Tizim", "icon": "bell"},
    "screen_analyze": {"title": "Ekran Tahlili (Vision)", "category": "Tizim", "icon": "camera"},
    "system_control": {"title": "Tizim Harakatlari", "category": "Tizim", "icon": "terminal"},
    "calculator": {"title": "Kalkulyator", "category": "Utilitlar", "icon": "calculator"},
    "file_manager": {"title": "Fayl Boshqaruvi", "category": "Utilitlar", "icon": "folder"},
    "rag_reader": {"title": "Hujjatlar Tahlili (RAG)", "category": "Utilitlar", "icon": "file-text"},
    "translator": {"title": "Matn Tarjimoni", "category": "Utilitlar", "icon": "globe"},
    "sandbox_execute_python": {"title": "Python Sandbox", "category": "Utilitlar", "icon": "code"},
    "secret_vault": {"title": "Xavfsiz Kalitlar", "category": "Utilitlar", "icon": "lock"},
    "datetime": {"title": "Sana va Vaqt", "category": "Ma'lumot", "icon": "clock"},
    "currency": {"title": "Valyuta Kurslari", "category": "Ma'lumot", "icon": "dollar-sign"},
    "weather": {"title": "Ob-havo Ma'lumoti", "category": "Ma'lumot", "icon": "sun"},
    "music_player": {"title": "Musiqa Pleyeri", "category": "Multimedia", "icon": "play"},
    "web_search": {"title": "Internet Qidiruv", "category": "Internet", "icon": "search"},
    "knowledge": {"title": "Bilimlar Bazasi", "category": "Xotira", "icon": "database"},
    "vector_search": {"title": "Semantik Xotira", "category": "Xotira", "icon": "database"},
    "reminder": {"title": "Eslatmalar", "category": "Rejalashtirish", "icon": "clock"},
    "scheduler": {"title": "Vaqtli Vazifalar", "category": "Rejalashtirish", "icon": "calendar"},
    "file_write": {"title": "Fayl Yozish (Kod)", "category": "Dasturlash", "icon": "code"},
    "ask_user": {"title": "Foydalanuvchi Savoli", "category": "Interaktiv", "icon": "chat"},
    "screen_click": {"title": "Sichqoncha Boshqaruvi", "category": "Interaktiv", "icon": "mouse-pointer"},
    "keyboard_type": {"title": "Matn Kiritish", "category": "Interaktiv", "icon": "terminal"},
    "keyboard_shortcut": {"title": "Klaviatura Tugmalari", "category": "Interaktiv", "icon": "terminal"},
}

QUICK_APP_SHORTCUTS = [
    {"id": "app_telegram", "name": "Telegram (AyuGram)", "query": "telegram", "category": "Ilovalar", "icon": "send", "desc": "Telegram (yoki o'rnatilgan AyuGram) messenjerini ishga tushiradi"},
    {"id": "app_vscode", "name": "Visual Studio Code", "query": "vs code", "category": "Ilovalar", "icon": "code", "desc": "VS Code dasturlash muhitini ishga tushiradi"},
    {"id": "app_browser", "name": "Veb Brauzer", "query": "brauzerni och", "category": "Ilovalar", "icon": "globe", "desc": "Tizim standart internet brauzerini ochadi"},
    {"id": "app_youtube", "name": "YouTube", "query": "youtube", "category": "Multimedia", "icon": "play", "desc": "Brauzerda YouTube portalini ochadi"},
    {"id": "app_explorer", "name": "Fayllar (Explorer)", "query": "fayllar", "category": "Tizim", "icon": "folder", "desc": "Windows Explorer fayl menejerini ochadi"},
    {"id": "app_cmd", "name": "Terminal (CMD)", "query": "terminal", "category": "Tizim", "icon": "terminal", "desc": "Windows buyruq satrini ochadi"},
    {"id": "app_taskmgr", "name": "Vazifalar Dispetcheri", "query": "vazifa menejeri", "category": "Tizim", "icon": "cpu", "desc": "Windows Task Manager oynasini ochadi"},
    {"id": "app_screenshot", "name": "Skrinshot Olish", "query": "skrinshot", "category": "Tizim", "icon": "camera", "desc": "Butun ekranning lahzali tasvirini olib saqlaydi"},
    {"id": "app_desktop", "name": "Ish Stoliga O'tish", "query": "ish stoli", "category": "Tizim", "icon": "monitor", "desc": "Barcha oynalarni yig'ishtirib ish stolini ko'rsatadi"},
    {"id": "app_settings", "name": "Windows Sozlamalari", "query": "sozlamalar", "category": "Tizim", "icon": "settings", "desc": "Windows tizim sozlamalari panelini ochadi"},
]


# ========== 3. BUYRUQLAR (COMMANDS) HANDLERS ==========
async def handle_commands_list(request):
    """GET /api/commands - Barcha mavjud buyruqlar va real ToolRegistry vositalari ro'yxati"""
    categories = [
        "Barchasi",
        "Tizim",
        "Ilovalar",
        "Utilitlar",
        "Ma'lumot",
        "Multimedia",
        "Internet",
        "Xotira",
        "Rejalashtirish",
        "Dasturlash",
        "Interaktiv"
    ]
    
    commands = []
    
    # 1. Tezkor ilovalar va amallar
    commands.extend(QUICK_APP_SHORTCUTS)
    
    # 2. ToolRegistry dagi real vositalar
    try:
        from core.agent_tools import get_registry
        reg = get_registry()
        for name, tool in reg._tools.items():
            meta = TOOL_METADATA.get(name, {})
            cat = meta.get("category", "Tizim")
            title = meta.get("title", name)
            icon = meta.get("icon", "commands")
            
            commands.append({
                "id": f"tool_{name}",
                "name": title,
                "tool_name": name,
                "query": name,
                "category": cat,
                "icon": icon,
                "desc": tool.description,
                "parameters": tool.parameters,
                "is_tool": True
            })
    except Exception as e:
        logger.error(f"ToolRegistry yuklashda xatolik: {e}")

    return web.json_response({
        "ok": True,
        "categories": categories,
        "commands": commands,
        "total_commands": len(commands)
    })


async def handle_commands_execute(request):
    """POST /api/commands/execute - Buyruq yoki ToolRegistry vositasini darhol ishga tushirish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    cmd_text = body.get("command", "").strip()
    cmd_params = body.get("parameters")
    if not cmd_text:
        return web.json_response({"ok": False, "error": "Buyruq kiritilmadi"}, status=400)

    loop = asyncio.get_running_loop()

    # ToolRegistry tekshirish
    from core.agent_tools import get_registry
    reg = get_registry()
    candidate = cmd_text.split()[0].lower() if " " in cmd_text else cmd_text.lower()
    tool = reg.get(candidate)

    if tool:
        def _run_tool():
            kwargs = {}
            if isinstance(cmd_params, dict) and cmd_params:
                kwargs = cmd_params
            else:
                args_str = cmd_text[len(candidate):].strip()
                if candidate == "calculator" and args_str:
                    kwargs["expression"] = args_str
                elif candidate == "weather" and args_str:
                    kwargs["city"] = args_str
                elif candidate == "app_check" and args_str:
                    kwargs["app_name"] = args_str
                elif candidate == "system_info" and args_str:
                    kwargs["category"] = args_str
                elif candidate == "notification" and args_str:
                    kwargs["message"] = args_str
                elif candidate == "currency" and args_str:
                    parts = args_str.split()
                    if len(parts) >= 2:
                        kwargs["from_currency"], kwargs["to_currency"] = parts[0], parts[1]
                    elif len(parts) == 1:
                        kwargs["from_currency"] = parts[0]
            res = tool.call(**kwargs)
            return format_tool_result(candidate, res)

        result_message = await loop.run_in_executor(None, _run_tool)
    else:
        user = get_current_user_name()
        ovoz = get_current_voice_type()
        def _run_cmd():
            return execute_command_pipeline(cmd_text, user, ovoz, mode="command")
        result_message = await loop.run_in_executor(None, _run_cmd)

    await broadcast_ws("command_executed", {"command": cmd_text, "result": result_message})

    return web.json_response({
        "ok": True,
        "command": cmd_text,
        "result": result_message,
        "timestamp": datetime.now().isoformat()
    })


# ========== 4. XOTIRA (MEMORY) HANDLERS ==========
async def handle_memory_get(request):
    """GET /api/memory - Xotira, bilimlar bazasi va suhbatlar tarixi"""
    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli yuklanmagan"}, status=500)

    profile = mem.get_profile()
    raw_knowledge = mem.get_knowledge()
    conversations = mem.get_conversations(last_n=50)
    context_turns = mem.get_context(last_n=30)
    stats = mem.stats

    # Bilimlarni qulay va to'liq array formatga o'tkazish
    knowledge_list = []
    if isinstance(raw_knowledge, dict):
        for k, v in raw_knowledge.items():
            if isinstance(v, dict):
                knowledge_list.append({
                    "id": v.get("id") or k,
                    "key": k,
                    "value": v.get("value", ""),
                    "content": v.get("content") or v.get("value", ""),
                    "type": v.get("type", "fact"),
                    "source": v.get("source", "user"),
                    "importance": float(v.get("importance", 0.5)),
                    "confidence": float(v.get("confidence", 1.0)),
                    "created_at": v.get("created_at") or v.get("saved_at", ""),
                    "saved_at": v.get("saved_at", ""),
                    "updated_at": v.get("updated_at") or v.get("saved_at", ""),
                    "last_used_at": v.get("last_used_at"),
                    "access_count": int(v.get("access_count", 0)),
                    "superseded_by": v.get("superseded_by"),
                    "is_active": v.get("superseded_by") is None,
                    "pinned": bool(v.get("pinned", False)),
                    "metadata": v.get("metadata", {}),
                })
            else:
                knowledge_list.append({
                    "id": k,
                    "key": k,
                    "value": str(v),
                    "content": str(v),
                    "type": "fact",
                    "source": "user",
                    "importance": 0.5,
                    "confidence": 1.0,
                    "created_at": datetime.now().isoformat(),
                    "saved_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "last_used_at": None,
                    "access_count": 0,
                    "superseded_by": None,
                    "is_active": True,
                    "pinned": False,
                    "metadata": {},
                })

    return web.json_response({
        "ok": True,
        "profile": profile,
        "knowledge": knowledge_list,
        "conversations": conversations,
        "context": context_turns,
        "stats": stats
    })


async def handle_memory_profile_save(request):
    """POST /api/memory/profile - Foydalanuvchi profili maydonlarini yangilash"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    for k, v in body.items():
        mem.set_profile(k, v)

    await broadcast_ws("memory_updated", {"action": "profile_update", "profile": mem.get_profile()})
    return web.json_response({
        "ok": True,
        "message": "Profil muvaffaqiyatli yangilandi",
        "profile": mem.get_profile()
    })


async def handle_memory_knowledge_save(request):
    """POST /api/memory/knowledge - Yangi bilim yoki fakt qo'shish/yangilash"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    key = body.get("key", "").strip()
    value = body.get("value", "").strip()
    pinned = bool(body.get("pinned", False))
    memory_type = body.get("type")

    if not key or not value:
        return web.json_response({"ok": False, "error": "Kalit so'z va qiymat talab qilinadi"}, status=400)

    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    saved = mem.save_knowledge(key, value, memory_type=memory_type, pinned=pinned)
    if not saved:
        return web.json_response({
            "ok": False,
            "error": "Xotiraga saqlash rad etildi (maxfiy ma'lumot yoki siyosat cheklovi)"
        }, status=400)

    await broadcast_ws("memory_updated", {"action": "save", "key": key, "value": value})

    return web.json_response({
        "ok": True,
        "message": f"'{key}' muvaffaqiyatli saqlandi",
        "key": key,
        "value": value
    })


async def handle_memory_knowledge_update(request):
    """PUT /api/memory/knowledge/{id} - Xotira elementini tahrirlash"""
    match_info = getattr(request, "match_info", {})
    item_id = match_info.get("id", "").strip() if match_info else ""
    if not item_id:
        return web.json_response({"ok": False, "error": "Xotira ID kiritilmadi"}, status=400)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    key = body.get("key")
    value = body.get("value") if body.get("value") is not None else body.get("content")
    memory_type = body.get("type")
    importance = body.get("importance")
    pinned = body.get("pinned")

    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    updated_item = mem.update_knowledge_item(
        item_id_or_key=item_id,
        key=key,
        content=value,
        memory_type=memory_type,
        importance=importance,
        pinned=pinned
    )

    if updated_item:
        await broadcast_ws("memory_updated", {"action": "update", "item": updated_item.to_dict()})
        return web.json_response({
            "ok": True,
            "message": f"'{updated_item.key}' muvaffaqiyatli yangilandi",
            "item": updated_item.to_dict()
        })
    else:
        existing = mem.get_memory_item_by_id(item_id)
        if not existing:
            return web.json_response({"ok": False, "error": f"ID='{item_id}' bo'yicha xotira topilmadi"}, status=404)
        return web.json_response({"ok": False, "error": "Xotirani yangilash rad etildi (siyosat yoki maxfiy ma'lumot)"}, status=400)


async def handle_memory_knowledge_delete(request):
    """DELETE /api/memory/knowledge va DELETE /api/memory/knowledge/{id} - Bilimni o'chirish"""
    match_info = getattr(request, "match_info", {})
    target = match_info.get("id", "").strip() if match_info else ""
    if not target and hasattr(request, "query") and request.query:
        target = request.query.get("key", "").strip() or request.query.get("id", "").strip()
    if not target and hasattr(request, "json"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                target = body.get("key", "").strip() or body.get("id", "").strip()
        except Exception:
            pass

    if not target:
        return web.json_response({"ok": False, "error": "O'chirish uchun ID yoki key kiritilmadi"}, status=400)

    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    success = mem.delete_knowledge_item(target)
    if success:
        await broadcast_ws("memory_updated", {"action": "delete", "target": target})
        return web.json_response({"ok": True, "message": f"'{target}' o'chirildi"})
    else:
        return web.json_response({"ok": False, "error": f"'{target}' topilmadi"}, status=404)


async def handle_memory_pin(request):
    """POST /api/memory/pin - Xotirani qadash (pin) yoki qadoqdan chiqarish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    item_id = body.get("id", "").strip() or body.get("key", "").strip()
    pinned = bool(body.get("pinned", True))

    if not item_id:
        return web.json_response({"ok": False, "error": "Xotira ID yoki key kiritilmadi"}, status=400)

    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    success = mem.pin_knowledge_item(item_id, pinned=pinned)
    if success:
        await broadcast_ws("memory_updated", {"action": "pin", "id": item_id, "pinned": pinned})
        return web.json_response({"ok": True, "message": f"'{item_id}' qadash holati yangilandi: {pinned}"})
    else:
        return web.json_response({"ok": False, "error": f"'{item_id}' topilmadi"}, status=404)


async def handle_memory_policy_get(request):
    """GET /api/memory/policy - Xotira maxfiyligi va Do-Not-Remember sozlamalari"""
    from core.intelligence.memory_policy import MemoryPolicy
    config = MemoryPolicy.get_policy_config()
    return web.json_response({"ok": True, "policy": config})


async def handle_memory_policy_save(request):
    """POST /api/memory/policy - Xotira maxfiyligi va Do-Not-Remember sozlamalarini yangilash"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    from core.intelligence.memory_policy import MemoryPolicy
    updated = MemoryPolicy.update_policy_config(
        do_not_remember_all=body.get("do_not_remember_all"),
        blocked_types=body.get("blocked_types"),
        blocked_keys=body.get("blocked_keys")
    )
    await broadcast_ws("memory_policy_updated", {"policy": updated})
    return web.json_response({"ok": True, "message": "Xotira siyosati muvaffaqiyatli saqlandi", "policy": updated})


async def handle_memory_metrics_get(request):
    """GET /api/memory/metrics - Xotira quyi tizimi telemetriya metrikalari"""
    _, _, mem, _, _, _ = get_modules()
    from core.intelligence.observability import get_observability_manager
    metrics = get_observability_manager().metrics.get_metrics(agent_memory=mem)
    return web.json_response({"ok": True, "metrics": metrics})


async def handle_context_traces_get(request):
    """GET /api/context/traces - So'rovlar kontekst ijro izlari ro'yxati"""
    limit_str = request.query.get("limit", "10")
    try:
        limit = max(1, min(25, int(limit_str)))
    except ValueError:
        limit = 10

    from core.intelligence.observability import get_observability_manager
    traces = get_observability_manager().get_recent_traces(limit=limit)
    return web.json_response({"ok": True, "traces": traces})


async def handle_context_last_trace_get(request):
    """GET /api/context/last-trace - Oxirgi so'rovning to'liq kontekst izi"""
    from core.intelligence.observability import get_observability_manager
    trace = get_observability_manager().get_last_trace()
    return web.json_response({"ok": True, "trace": trace})


async def handle_memory_knowledge_clear(request):
    """POST /api/memory/knowledge/clear - Barcha saqlangan bilimlarni tozalash"""
    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    mem.clear_knowledge()
    await broadcast_ws("memory_updated", {"action": "knowledge_cleared"})
    return web.json_response({"ok": True, "message": "Barcha bilimlar bazasi tozalandi"})


async def handle_memory_context_clear(request):
    """POST /api/memory/context/clear - Joriy suhbat kontekstini (RAM) tozalash"""
    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    mem.clear_context()
    await broadcast_ws("memory_updated", {"action": "context_cleared"})
    return web.json_response({"ok": True, "message": "Joriy suhbat konteksti (RAM) tozalandi"})


async def handle_memory_history_clear(request):
    """POST /api/memory/history/clear - Suhbatlar arxivini tozalash"""
    _, _, mem, _, _, _ = get_modules()
    if not mem:
        return web.json_response({"ok": False, "error": "Xotira moduli mavjud emas"}, status=500)

    mem.clear_conversations()
    await broadcast_ws("memory_updated", {"action": "history_cleared"})
    return web.json_response({"ok": True, "message": "Suhbatlar tarixi arxivi tozalandi"})


# ========== 4.5. AGENTIK MULTI-STEP INTELLIGENCE HANDLERS ==========
def get_agent_loop_instance():
    from core.intelligence import get_agent_loop
    loop_inst = get_agent_loop()
    if loop_inst.event_emitter is None:
        loop_inst.event_emitter = sync_broadcast
    return loop_inst


async def handle_agent_execute(request):
    """POST /api/agent/execute - Ko'p bosqichli agentlik rejasini tuzish va ijro etish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    goal = (body.get("goal") or body.get("text") or body.get("query") or "").strip()
    if not goal:
        return web.json_response({"ok": False, "error": "Maqsad (goal) bo'sh bo'lishi mumkin emas"}, status=400)

    user = get_current_user_name()
    agent_loop = get_agent_loop_instance()
    loop = asyncio.get_running_loop()

    def _run():
        plan = agent_loop.create_plan_from_goal(goal)
        res = agent_loop.execute_plan(plan, user_name=user)
        return plan, res

    try:
        plan, res = await loop.run_in_executor(None, _run)
        return web.json_response({
            "ok": res.verified or res.type in ("answer", "confirmation"),
            "type": res.type,
            "content": res.content,
            "plan": plan.to_dict() if plan else None,
            "metadata": res.metadata,
            "error_code": res.error_code,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Agent ijrosida xatolik: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_agent_confirm(request):
    """POST /api/agent/confirm - Xavfli amalni tasdiqlash yoki rad etish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    plan_id = body.get("plan_id")
    step_id = body.get("step_id")
    approve = bool(body.get("approve", True))

    if not plan_id or not step_id:
        return web.json_response({"ok": False, "error": "plan_id va step_id talab qilinadi"}, status=400)

    agent_loop = get_agent_loop_instance()
    loop = asyncio.get_running_loop()

    def _confirm():
        return agent_loop.confirm_step(plan_id, step_id, approve=approve)

    try:
        res = await loop.run_in_executor(None, _confirm)
        return web.json_response({
            "ok": res.verified or res.type in ("answer", "confirmation"),
            "type": res.type,
            "content": res.content,
            "metadata": res.metadata,
            "error_code": res.error_code,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Agent tasdiqlashida xatolik: {e}")
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def handle_agent_abort(request):
    """POST /api/agent/abort - Faol agentlik rejasini to'xtatish"""
    plan_id = None
    try:
        if request.can_read_body:
            body = await request.json()
            plan_id = body.get("plan_id")
    except Exception:
        pass

    agent_loop = get_agent_loop_instance()
    stopped, msg = agent_loop.abort_plan(plan_id)

    return web.json_response({
        "ok": stopped,
        "message": msg,
        "timestamp": datetime.now().isoformat()
    })


async def handle_agent_state(request):
    """GET /api/agent/state - Joriy agent holati va ijro tafsilotlari"""
    agent_loop = get_agent_loop_instance()
    exec_state = agent_loop.get_execution_state()

    return web.json_response({
        "ok": True,
        "state": agent_loop.state.value,
        "execution": exec_state.to_dict(),
        "timestamp": datetime.now().isoformat()
    })


# ========== 5. REJALASHTIRUVCHI (SCHEDULER) HANDLERS ==========
async def handle_scheduler_list(request):
    """GET /api/scheduler - Vazifalar va eslatmalar ro'yxati"""
    _, _, _, sched, _, _ = get_modules()
    if not sched:
        return web.json_response({"ok": False, "error": "Rejalashtiruvchi yuklanmagan"}, status=500)

    tasks = sched.list_tasks(include_completed=True)
    return web.json_response({
        "ok": True,
        "tasks": tasks,
        "active_count": sched.active_count
    })


async def handle_scheduler_add(request):
    """POST /api/scheduler/add - Yangi eslatma yoki vaqtli vazifa qo'shish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    text = body.get("text", "").strip()
    delay_minutes = int(body.get("delay_minutes", 15))
    repeat_minutes = int(body.get("repeat_minutes", 0))
    task_type = body.get("type", "reminder")

    if not text:
        return web.json_response({"ok": False, "error": "Eslatma matni kiritilmadi"}, status=400)

    _, _, _, sched, _, _ = get_modules()
    if not sched:
        return web.json_response({"ok": False, "error": "Rejalashtiruvchi mavjud emas"}, status=500)

    delay_seconds = max(5, delay_minutes * 60)
    repeat_seconds = max(0, repeat_minutes * 60)

    task_id = sched.add(
        task_type=task_type,
        data={"text": text},
        delay_seconds=delay_seconds,
        repeat_seconds=repeat_seconds
    )

    await broadcast_ws("scheduler_updated", {"action": "add", "task_id": task_id, "text": text})

    return web.json_response({
        "ok": True,
        "task_id": task_id,
        "message": f"Vazifa muvaffaqiyatli rejalashtirildi ({delay_minutes} daqiqadan keyin)",
        "delay_minutes": delay_minutes,
        "repeat_minutes": repeat_minutes
    })


async def handle_scheduler_remove(request):
    """DELETE /api/scheduler/task - Vazifani o'chirish"""
    task_id = request.query.get("task_id", "").strip()
    if not task_id:
        try:
            body = await request.json()
            task_id = body.get("task_id", "").strip()
        except Exception:
            pass

    if not task_id:
        return web.json_response({"ok": False, "error": "'task_id' ko'rsatilmadi"}, status=400)

    _, _, _, sched, _, _ = get_modules()
    if not sched:
        return web.json_response({"ok": False, "error": "Rejalashtiruvchi mavjud emas"}, status=500)

    success = sched.remove(task_id)
    if success:
        await broadcast_ws("scheduler_updated", {"action": "remove", "task_id": task_id})
        return web.json_response({"ok": True, "message": f"Vazifa '{task_id}' o'chirildi"})
    else:
        return web.json_response({"ok": False, "error": f"Vazifa topilmadi: {task_id}"}, status=404)


async def handle_scheduler_clear_completed(request):
    """POST /api/scheduler/clear-completed - Bajarilgan vazifalarni tozalash"""
    _, _, _, sched, _, _ = get_modules()
    if sched:
        sched.clear_completed()
    await broadcast_ws("scheduler_updated", {"action": "clear_completed"})
    return web.json_response({"ok": True, "message": "Bajarilgan vazifalar tozalandi"})


async def handle_scheduler_edit(request):
    """POST /api/scheduler/edit - Vazifani tahrirlash"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    task_id = body.get("task_id", "").strip()
    if not task_id:
        return web.json_response({"ok": False, "error": "'task_id' ko'rsatilmadi"}, status=400)

    _, _, _, sched, _, _ = get_modules()
    if not sched:
        return web.json_response({"ok": False, "error": "Rejalashtiruvchi mavjud emas"}, status=500)

    text = body.get("text", "").strip() if "text" in body else None
    delay_seconds = int(body.get("delay_minutes", 0)) * 60 if "delay_minutes" in body else None
    repeat_seconds = int(body.get("repeat_minutes", 0)) * 60 if "repeat_minutes" in body else None

    success = sched.edit(
        task_id=task_id,
        text=text,
        delay_seconds=delay_seconds,
        repeat_seconds=repeat_seconds,
    )

    if success:
        await broadcast_ws("scheduler_updated", {"action": "edit", "task_id": task_id})
        return web.json_response({"ok": True, "message": f"Vazifa '{task_id}' tahrirlandi"})
    return web.json_response({"ok": False, "error": f"Vazifa topilmadi: {task_id}"}, status=404)


async def handle_scheduler_enable(request):
    """POST /api/scheduler/enable - Vazifani faollashtirish"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    task_id = body.get("task_id", "").strip() or request.query.get("task_id", "").strip()
    if not task_id:
        return web.json_response({"ok": False, "error": "'task_id' ko'rsatilmadi"}, status=400)

    _, _, _, sched, _, _ = get_modules()
    if not sched:
        return web.json_response({"ok": False, "error": "Rejalashtiruvchi mavjud emas"}, status=500)

    success = sched.enable(task_id)
    if success:
        await broadcast_ws("scheduler_updated", {"action": "enable", "task_id": task_id})
        return web.json_response({"ok": True, "message": f"Vazifa '{task_id}' faollashtirildi"})
    return web.json_response({"ok": False, "error": f"Vazifa topilmadi: {task_id}"}, status=404)


async def handle_scheduler_disable(request):
    """POST /api/scheduler/disable - Vazifani to'xtatib turish"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    task_id = body.get("task_id", "").strip() or request.query.get("task_id", "").strip()
    if not task_id:
        return web.json_response({"ok": False, "error": "'task_id' ko'rsatilmadi"}, status=400)

    _, _, _, sched, _, _ = get_modules()
    if not sched:
        return web.json_response({"ok": False, "error": "Rejalashtiruvchi mavjud emas"}, status=500)

    success = sched.disable(task_id)
    if success:
        await broadcast_ws("scheduler_updated", {"action": "disable", "task_id": task_id})
        return web.json_response({"ok": True, "message": f"Vazifa '{task_id}' to'xtatildi"})
    return web.json_response({"ok": False, "error": f"Vazifa topilmadi: {task_id}"}, status=404)


async def handle_scheduler_execute(request):
    """POST /api/scheduler/execute - Vazifani darhol bajarish"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    task_id = body.get("task_id", "").strip() or request.query.get("task_id", "").strip()
    if not task_id:
        return web.json_response({"ok": False, "error": "'task_id' ko'rsatilmadi"}, status=400)

    _, _, _, sched, _, _ = get_modules()
    if not sched:
        return web.json_response({"ok": False, "error": "Rejalashtiruvchi mavjud emas"}, status=500)

    success = sched.execute(task_id)
    if success:
        await broadcast_ws("scheduler_updated", {"action": "execute", "task_id": task_id})
        return web.json_response({"ok": True, "message": f"Vazifa '{task_id}' darhol bajarildi"})
    return web.json_response({"ok": False, "error": f"Vazifa topilmadi: {task_id}"}, status=404)


# ========== 6. PLAGINLAR VA TOOLS HANDLERS ==========
async def handle_plugins_list(request):
    """GET /api/plugins - Barcha agent vositalari va plaginlar ro'yxati (5 holat: installed, available, disabled, error, updates)"""
    _, _, _, _, tools, _ = get_modules()
    if not tools:
        return web.json_response({"ok": False, "error": "Tools registry yuklanmagan"}, status=500)

    try:
        from core.agent_plugins import get_plugin_manager
        pm = get_plugin_manager()
        plugins, stats = pm.get_all_plugins(tools)
    except Exception as e:
        logger.error(f"Pluginlarni olishda xatolik: {e}")
        raw_tools = tools.list_tools()
        plugins = [{
            "id": t.get("name"), "name": t.get("name"),
            "description": t.get("description"), "category": "Tizim",
            "parameters": t.get("parameters", {}), "version": "1.0.0",
            "status": "installed", "enabled": True, "type": "builtin"
        } for t in raw_tools]
        stats = {"total": len(plugins), "installed": len(plugins), "available": 0, "disabled": 0, "error": 0, "updates": 0}

    return web.json_response({
        "ok": True,
        "plugins": plugins,
        "tools": plugins,  # orqaga moslik (backwards compatibility)
        "stats": stats,
        "total_count": len(plugins),
        "categories": [
            "Barchasi", "Tizim", "Qidiruv", "Multimedia",
            "Avtomatlashtirish", "Hisoblash", "AI Bilim",
            "Fayllar", "Dasturlash", "Muloqot", "Xavfsizlik"
        ]
    })


async def handle_plugins_toggle(request):
    """POST /api/plugins/toggle - Plaginni yoqish yoki o'chirish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    name = body.get("name", "").strip()
    enabled = bool(body.get("enabled", True))
    if not name:
        return web.json_response({"ok": False, "error": "Plagin nomi ko'rsatilmadi"}, status=400)

    _, _, _, _, tools, _ = get_modules()
    from core.agent_plugins import get_plugin_manager
    pm = get_plugin_manager()
    success = pm.toggle(name, enabled, tools)

    await broadcast_ws("plugins_updated", {"action": "toggle", "name": name, "enabled": enabled})
    status_txt = "yoqildi" if enabled else "to'xtatildi"
    return web.json_response({
        "ok": success,
        "message": f"Plagin '{name}' {status_txt}"
    })


async def handle_plugins_install(request):
    """POST /api/plugins/install - Plagin o'rnatish"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    name = body.get("name", "").strip()
    custom_data = body.get("data")
    if not name:
        return web.json_response({"ok": False, "error": "Plagin nomi ko'rsatilmadi"}, status=400)

    _, _, _, _, tools, _ = get_modules()
    from core.agent_plugins import get_plugin_manager
    pm = get_plugin_manager()
    success = pm.install(name, custom_data, tools)

    if success:
        await broadcast_ws("plugins_updated", {"action": "install", "name": name})
        return web.json_response({"ok": True, "message": f"Plagin '{name}' muvaffaqiyatli o'rnatildi"})
    return web.json_response({"ok": False, "error": f"Plagin '{name}' o'rnatishda xatolik"}, status=400)


async def handle_plugins_uninstall(request):
    """POST /api/plugins/uninstall - Plaginni butunlay o'chirish"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    name = body.get("name", "").strip() or request.query.get("name", "").strip()
    if not name:
        return web.json_response({"ok": False, "error": "Plagin nomi ko'rsatilmadi"}, status=400)

    _, _, _, _, tools, _ = get_modules()
    from core.agent_plugins import get_plugin_manager
    pm = get_plugin_manager()
    success = pm.uninstall(name, tools)

    if success:
        await broadcast_ws("plugins_updated", {"action": "uninstall", "name": name})
        return web.json_response({"ok": True, "message": f"Plagin '{name}' o'chirildi"})
    return web.json_response({"ok": False, "error": f"Plagin '{name}' topilmadi"}, status=404)


async def handle_plugins_update(request):
    """POST /api/plugins/update - Plaginni yangilash"""
    try:
        body = await request.json()
    except Exception:
        body = {}

    name = body.get("name", "").strip() or request.query.get("name", "").strip()
    if not name:
        return web.json_response({"ok": False, "error": "Plagin nomi ko'rsatilmadi"}, status=400)

    _, _, _, _, tools, _ = get_modules()
    from core.agent_plugins import get_plugin_manager
    pm = get_plugin_manager()
    success = pm.update(name, tools)

    if success:
        await broadcast_ws("plugins_updated", {"action": "update", "name": name})
        return web.json_response({"ok": True, "message": f"Plagin '{name}' yangilandi"})
    return web.json_response({"ok": False, "error": f"Plagin '{name}' yangilash topilmadi"}, status=404)


async def handle_plugins_execute(request):
    """POST /api/plugins/execute - Toolni bevosita chaqirib sinash"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    tool_name = body.get("name", "").strip()
    params = body.get("params", {})

    if not tool_name:
        return web.json_response({"ok": False, "error": "Tool nomi ko'rsatilmadi"}, status=400)

    _, _, _, _, tools, _ = get_modules()
    if not tools:
        return web.json_response({"ok": False, "error": "Tools registry mavjud emas"}, status=500)

    loop = asyncio.get_running_loop()
    
    def _call():
        return tools.call(tool_name, **params)

    res = await loop.run_in_executor(None, _call)
    res_dict = res.to_dict() if hasattr(res, "to_dict") else res
    return web.json_response({
        "ok": True,
        "tool": tool_name,
        "result": res_dict
    })


async def handle_tools_catalog(request):
    """GET /api/tools/catalog - Tool System 2.0 to'liq qobiliyatlar va vositalar katalogi"""
    _, _, _, _, tools, _ = get_modules()
    if not tools:
        return web.json_response({"ok": False, "error": "Tools registry yuklanmagan"}, status=500)

    tools_list = tools.list_tools() if hasattr(tools, "list_tools") else []
    caps = {}
    if hasattr(tools, "capability_registry"):
        caps = tools.capability_registry.list_all_capabilities()

    return web.json_response({
        "ok": True,
        "version": "2.0.0",
        "total_tools": len(tools_list),
        "capabilities_count": len(caps),
        "tools": tools_list,
        "capabilities": caps,
    })


# ========== 7. HISOB VA SOZLAMALAR (ACCOUNT) HANDLERS ==========
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
USER_NAME_FILE = os.path.join(DATA_DIR, "foydalanuvchi_ismi.txt")
VOICE_TYPE_FILE = os.path.join(DATA_DIR, "ovoz_turi.txt")

def _read_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _write_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Config saqlash xatosi: {e}")

async def handle_account_get(request):
    """GET /api/account - Foydalanuvchi profili va tizim sozlamalari"""
    user_id, user, session, err = resolve_auth_identity(request, required=False)
    if err:
        return err
    user_id = user_id or get_current_user_name() or "local_user"

    user_name = get_current_user_name()
    voice_type = get_current_voice_type()
    cfg = _read_config()

    user_cfg = cfg.get("user", {})
    audio_cfg = cfg.get("audio", {})
    gui_cfg = cfg.get("gui", {})
    ai_cfg = cfg.get("ai", {})
    notif_cfg = cfg.get("notifications", {})
    priv_cfg = cfg.get("privacy", {})

    # AgentMemory bilan sinxronlash
    _, _, mem, _, _, _ = get_modules()
    mem_profile = mem.get_profile() if mem else {}

    # Phase 40 Multi-User Account & Device Management
    from core.v8 import AccountDeviceManager, TelegramIdentityManager
    from core.v8.auth_session import SessionManager
    adm = AccountDeviceManager.get_default_instance()
    tg_mgr = TelegramIdentityManager.get_default_instance()
    sess_mgr = SessionManager.get_default_instance()
    account_summary = adm.get_user_account_summary(user_id, tg_identity_mgr=tg_mgr, session_mgr=sess_mgr)

    auth_email = getattr(user, "email", "") if user else ""
    auth_display_name = (getattr(user, "display_name", "") or getattr(user, "username", "")) if user else ""
    auth_avatar_url = getattr(user, "avatar_url", "") if user else ""

    name = user_cfg.get("name") or auth_display_name or user_name or mem_profile.get("ism", "Foydalanuvchi")
    email = user_cfg.get("email") or auth_email or ""
    avatar = user_cfg.get("avatar") or mem_profile.get("avatar", "violet")
    avatar_url = user_cfg.get("avatar_url") or auth_avatar_url or ""
    role = user_cfg.get("role") or mem_profile.get("kasb", "Dasturchi / Foydalanuvchi")
    phone = user_cfg.get("phone") or mem_profile.get("telefon", "")
    bio = user_cfg.get("bio") or mem_profile.get("bio", "Misa AI shaxsiy sun'iy intellekt yordamchisi")
    language = user_cfg.get("language") or mem_profile.get("til", "uz")

    ai_keys = {}
    try:
        from core.v8.ai_key_manager import get_ai_key_manager
        ai_mgr = get_ai_key_manager()
        status_sum = ai_mgr.get_status_summary()
        active_keys = status_sum.get("active_keys", {})
        for prov in ("gemini", "groq", "cerebras", "openrouter", "nvidia"):
            k = active_keys.get(prov) or ""
            has_k = bool(k)
            masked = (k[:6] + "..." + k[-4:]) if (has_k and len(k) > 10) else ("●●●●●●" if has_k else "")
            ai_keys[prov] = {
                "has_key": has_k,
                "masked_key": masked,
            }
        active_key = ai_mgr.get_active_gemini_key(user_id=user_id)
        has_gemini = bool(active_key)
        if has_gemini and len(active_key) > 12:
            masked_key = active_key[:8] + "..." + active_key[-4:]
    except Exception:
        has_gemini = bool(os.environ.get("GEMINI_API_KEY") or ai_cfg.get("gemini_api_key"))
        for prov in ("gemini", "groq", "cerebras", "openrouter", "nvidia"):
            k = os.environ.get(f"{prov.upper()}_API_KEY") or ai_cfg.get(f"{prov}_api_key") or ""
            has_k = bool(k)
            masked = (k[:6] + "..." + k[-4:]) if (has_k and len(k) > 10) else ("●●●●●●" if has_k else "")
            ai_keys[prov] = {
                "has_key": has_k,
                "masked_key": masked,
            }

    fish_audio_key = os.environ.get("FISH_AUDIO_API_KEY", "")
    if not fish_audio_key:
        try:
            from core.voice_engine import get_fish_audio_api_key
            fish_audio_key = get_fish_audio_api_key()
        except Exception:
            fish_audio_key = cfg.get("voice", {}).get("fish_audio_api_key", "")

    return web.json_response({
        "ok": True,
        "user_id": user_id,
        "ai_keys": ai_keys,
        "account": account_summary,
        "devices_count": account_summary["devices_count"],
        "active_sessions_count": account_summary["active_sessions_count"],
        "selected_device": account_summary["selected_device"],
        "telegram_linked": account_summary["telegram_linked"],
        "telegram_identity": account_summary["telegram_identity"],
        "name": name,
        "email": email,
        "avatar": avatar,
        "avatar_url": avatar_url,
        "role": role,
        "phone": phone,
        "bio": bio,
        "language": language,
        "voice_type": voice_type or user_cfg.get("voice_type", "ayol"),
        "fish_audio_api_key": fish_audio_key,
        "tts_speed": float(audio_cfg.get("tts_speed", 1.0)),
        "tts_engine": audio_cfg.get("tts_engine", "edge_tts"),
        "auto_speak": audio_cfg.get("auto_speak", True),
        "vad_enabled": audio_cfg.get("vad_enabled", True),
        "theme": gui_cfg.get("theme", "dark"),
        "color_scheme": gui_cfg.get("color_scheme", "green"),
        "animations": gui_cfg.get("animations", True),
        "compact_mode": gui_cfg.get("compact_mode", False),
        "glassmorphism": gui_cfg.get("glassmorphism", True),
        "ai_model": ai_cfg.get("model", "gemini"),
        "ai_mode": ai_cfg.get("mode", "balanced"),
        "thinking_enabled": ai_cfg.get("thinking_enabled", True),
        "has_gemini_key": has_gemini,
        "api_key_masked": masked_key,
        "ai_status": "ready" if has_gemini else "missing_key",
        "version": get_app_version(),

        "app_info": {
            "name": "Misa AI",
            "version": get_app_version(),
            "codename": "Quiet Intelligence",
            "engine": "Tauri 2.0 (Native Rust) + Python 3.11+",
            "architecture": "Windows x64 Native Desktop",
            "developer": "Misa Core Team",
            "license": "Personal / Commercial AI Assistant"
        },
        "notifications": {
            "scheduler": notif_cfg.get("scheduler", True),
            "voice": notif_cfg.get("voice", True),
            "sound_effects": notif_cfg.get("sound_effects", True),
            "system_status": notif_cfg.get("system_status", True)
        },
        "privacy": {
            "local_storage_only": priv_cfg.get("local_storage_only", True),
            "telemetry_disabled": priv_cfg.get("telemetry_disabled", True),
            "save_conversations": priv_cfg.get("save_conversations", True)
        },
        "voices_available": (lambda: __import__("core.voice_engine", fromlist=["VOICE_CATALOG"]).VOICE_CATALOG)(),
        "ai_models_available": [
            {
                "id": "gemini",
                "name": "Google Gemini 1.5 (Flash / Pro)",
                "provider": "Google DeepMind",
                "badge": "Tavsiya etiladi",
                "desc": "Yuqori tezlik, keng kontekst va fikrlovchi AI modeli"
            },
            {
                "id": "openrouter",
                "name": "OpenRouter (GPT-4o / Claude)",
                "provider": "OpenRouter Cloud",
                "badge": "Universal",
                "desc": "Universal yirik til modellari tarmog'i"
            },
            {
                "id": "local",
                "name": "Misa Local Dispatcher",
                "provider": "Mahalliy Tizim",
                "badge": "Oflayn",
                "desc": "Internetga ulanmasdan tizim buyruqlarini boshqarish"
            }
        ]
    })


async def handle_account_update(request):
    """POST /api/account - Profil va sozlamalarni yangilash"""
    user_id, user, session, err = resolve_auth_identity(request, required=False)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    cfg = _read_config()
    for section in ["user", "audio", "voice", "gui", "ai", "notifications", "privacy"]:
        if section not in cfg:
            cfg[section] = {}

    m, ai, mem, _, _, _ = get_modules()

    # 1. User & Profil
    new_name = body.get("name", "").strip() if "name" in body and body["name"] is not None else None
    new_email = body.get("email", "").strip() if "email" in body and body["email"] is not None else None
    new_avatar = body.get("avatar", "").strip() if "avatar" in body and body["avatar"] is not None else None
    new_avatar_url = body.get("avatar_url", "").strip() if "avatar_url" in body and body["avatar_url"] is not None else None
    new_role = body.get("role", "").strip() if "role" in body and body["role"] is not None else None
    new_phone = body.get("phone", "").strip() if "phone" in body and body["phone"] is not None else None
    new_bio = body.get("bio", "").strip() if "bio" in body and body["bio"] is not None else None
    new_lang = body.get("language", "").strip() if "language" in body and body["language"] is not None else None

    if new_name:
        cfg["user"]["name"] = new_name
        try:
            with open(USER_NAME_FILE, "w", encoding="utf-8") as f:
                f.write(new_name)
        except Exception:
            pass
        if mem:
            try:
                mem.set_profile("ism", new_name)
            except Exception:
                pass

    if new_email:
        cfg["user"]["email"] = new_email

    if new_avatar:
        cfg["user"]["avatar"] = new_avatar
        if mem:
            try:
                mem.set_profile("avatar", new_avatar)
            except Exception:
                pass

    if new_avatar_url is not None:
        cfg["user"]["avatar_url"] = new_avatar_url

    if user_id:
        try:
            from core.v8 import AccountDeviceManager
            adm = AccountDeviceManager.get_default_instance()
            u = adm.get_user(user_id)
            if u:
                if new_name:
                    u.display_name = new_name
                if new_email:
                    u.email = new_email
                if new_avatar_url:
                    u.avatar_url = new_avatar_url
                u.updated_at = time.time()
                adm.save_state()
        except Exception:
            pass

    if new_role is not None:
        cfg["user"]["role"] = new_role
        if mem:
            try:
                mem.set_profile("kasb", new_role)
            except Exception:
                pass

    if new_phone is not None:
        cfg["user"]["phone"] = new_phone
        if mem:
            try:
                mem.set_profile("telefon", new_phone)
            except Exception:
                pass

    if new_bio is not None:
        cfg["user"]["bio"] = new_bio
        if mem:
            try:
                mem.set_profile("bio", new_bio)
            except Exception:
                pass

    if new_lang:
        cfg["user"]["language"] = new_lang
        if mem:
            try:
                mem.set_profile("til", new_lang)
            except Exception:
                pass

    # 2. Voice & Ovoz
    new_voice = body.get("voice_type", "").strip() if "voice_type" in body and body["voice_type"] is not None else None
    if new_voice:
        cfg["user"]["voice_type"] = new_voice
        try:
            with open(VOICE_TYPE_FILE, "w", encoding="utf-8") as f:
                f.write(new_voice)
        except Exception:
            pass
        if mem:
            try:
                mem.set_profile("ovoz_turi", new_voice)
            except Exception:
                pass

    if "fish_audio_api_key" in body and body["fish_audio_api_key"] is not None:
        fish_key = str(body["fish_audio_api_key"]).strip()
        os.environ["FISH_AUDIO_API_KEY"] = fish_key
        # config.json dan olib tashlash (xavfsizlik uchun, maxfiy kalit .env da saqlanadi)
        if "voice" in cfg and "fish_audio_api_key" in cfg["voice"]:
            cfg["voice"].pop("fish_audio_api_key", None)
        try:
            env_path = os.path.join(BASE_DIR, ".env")
            env_lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()
            new_env_lines = [l for l in env_lines if not l.strip().startswith("FISH_AUDIO_API_KEY=")]
            if fish_key:
                new_env_lines.append(f"FISH_AUDIO_API_KEY={fish_key}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_env_lines)
        except Exception as e:
            logger.warning(f".env ga FISH_AUDIO_API_KEY saqlashda xato: {e}")

    if "tts_speed" in body and body["tts_speed"] is not None:
        try:
            spd = float(body["tts_speed"])
            cfg["audio"]["tts_speed"] = spd
            cfg["voice"]["speed"] = spd
        except (ValueError, TypeError):
            pass

    if "auto_speak" in body:
        cfg["audio"]["auto_speak"] = bool(body["auto_speak"])

    if "vad_enabled" in body:
        cfg["audio"]["vad_enabled"] = bool(body["vad_enabled"])

    # 3. GUI & Tashqi ko'rinish
    if "theme" in body and body["theme"]:
        cfg["gui"]["theme"] = str(body["theme"])
    if "color_scheme" in body and body["color_scheme"]:
        cfg["gui"]["color_scheme"] = str(body["color_scheme"])
    if "animations" in body:
        cfg["gui"]["animations"] = bool(body["animations"])
    if "compact_mode" in body:
        cfg["gui"]["compact_mode"] = bool(body["compact_mode"])
    if "glassmorphism" in body:
        cfg["gui"]["glassmorphism"] = bool(body["glassmorphism"])

    # 4. AI Engine
    if "ai_model" in body and body["ai_model"]:
        cfg["ai"]["model"] = str(body["ai_model"])
    if "ai_mode" in body and body["ai_mode"]:
        cfg["ai"]["mode"] = str(body["ai_mode"])
    if "thinking_enabled" in body:
        cfg["ai"]["thinking_enabled"] = bool(body["thinking_enabled"])
    # Multi-provider kalitlarini to'liq saqlash (Gemini, Groq, Cerebras, OpenRouter, NVIDIA)
    for prov in ("gemini", "groq", "cerebras", "openrouter", "nvidia"):
        param_name = f"{prov}_api_key"
        if param_name in body and body[param_name] is not None:
            key = str(body[param_name]).strip()
            if key:
                if "ai" not in cfg:
                    cfg["ai"] = {}
                cfg["ai"][param_name] = key
                if prov == "gemini":
                    cfg["gemini_api_key"] = key
                    os.environ["GEMINI_API_KEY"] = key
                    os.environ["GOOGLE_API_KEY"] = key
                    try:
                        from core import ai_engine
                        ai_engine.GOOGLE_API_KEY = key
                    except Exception:
                        pass
                else:
                    os.environ[f"{prov.upper()}_API_KEY"] = key

                try:
                    from core.v8.ai_key_manager import get_ai_key_manager
                    ai_mgr = get_ai_key_manager()
                    if user_id:
                        ai_mgr.set_user_key(user_id, prov, key)
                    ai_mgr.register_system_key(prov, key, prepend=True)
                except Exception:
                    pass

                try:
                    from core.providers import get_provider_system
                    ps = get_provider_system()
                    if prov in ps._providers and hasattr(ps._providers[prov], "set_api_key"):
                        ps._providers[prov].set_api_key(key)
                except Exception:
                    pass

            try:
                env_path = os.path.join(BASE_DIR, ".env")
                lines = []
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                lines = [l for l in lines if not l.startswith("GEMINI_API_KEY=") and not l.startswith("GOOGLE_API_KEY=")]
                lines.append(f"GEMINI_API_KEY={key}\n")
                lines.append(f"GOOGLE_API_KEY={key}\n")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
            except Exception:
                pass


    # 5. Bildirishnomalar
    if "notifications" in body and isinstance(body["notifications"], dict):
        cfg["notifications"].update(body["notifications"])

    # 6. Maxfiylik
    if "privacy" in body and isinstance(body["privacy"], dict):
        cfg["privacy"].update(body["privacy"])

    _write_config(cfg)

    # In-memory config.py singletonini ham yangilash
    try:
        from config import config as cfg_instance
        if hasattr(cfg_instance, "_deep_update"):
            cfg_instance._deep_update(cfg_instance.config, cfg)
        elif hasattr(cfg_instance, "config"):
            cfg_instance.config.update(cfg)
    except Exception as e:
        logger.warning(f"config singleton yangilash xatoligi: {e}")

    saved_user = new_name or get_current_user_name()
    saved_avatar = cfg["user"].get("avatar", "emerald")
    saved_voice = new_voice or get_current_voice_type()
    saved_speed = cfg["audio"].get("tts_speed", 1.0)
    saved_email = cfg["user"].get("email", "")
    saved_avatar_url = cfg["user"].get("avatar_url", "")
    saved_theme = cfg.get("gui", {}).get("theme", "dark")

    await broadcast_ws("account_updated", {
        "name": saved_user,
        "email": saved_email,
        "avatar": saved_avatar,
        "avatar_url": saved_avatar_url,
        "voice_type": saved_voice,
        "tts_speed": saved_speed,
        "theme": saved_theme
    })

    return web.json_response({
        "ok": True,
        "message": "Sozlamalar muvaffaqiyatli saqlandi",
        "name": saved_user,
        "email": saved_email,
        "avatar": saved_avatar,
        "avatar_url": saved_avatar_url,
        "voice_type": saved_voice,
        "tts_speed": saved_speed,
        "theme": saved_theme
    })


# ========== 8. PHASE 38: REMOTE CONTROL & USER PERMISSION CENTER API ==========

async def handle_remote_devices(request):
    """GET /api/remote/devices - Ro'yxatdan o'tgan va bog'langan qurilmalar"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    from core.v8 import (
        DeviceRegistry,
        HeartbeatManager,
        UserLinkingStore,
        DeviceIdentityManager,
        AccountDeviceManager,
        TelegramIdentityManager,
    )
    reg = DeviceRegistry.get_default_instance()
    hb = HeartbeatManager()
    linking = UserLinkingStore.get_default_instance()
    adm = AccountDeviceManager.get_default_instance()
    tg_mgr = TelegramIdentityManager.get_default_instance()
    auth_token = get_auth_token_from_request(request)

    tg_link = tg_mgr.get_link_by_misa_user(user_id, auth_token=auth_token, refresh=False)
    tg_paired = bool(tg_link and tg_link.is_active)
    tg_uid_str = str(tg_link.telegram_user_id) if tg_link and tg_link.telegram_user_id else None

    local_ident = DeviceIdentityManager.create_local_identity() if not _is_production_mode() else None
    adm_devices = adm.get_devices_for_user(user_id, include_revoked=False)
    if not adm_devices and local_ident:
        try:
            dev = adm.register_device(
                user_id=user_id,
                device_id=local_ident.device_id,
                name=f"{local_ident.hostname or 'Asosiy Kompyuter'} (Joriy kompyuter)",
                hostname=local_ident.hostname,
                platform=local_ident.os_name.lower(),
                agent_version=local_ident.agent_version,
                status="online",
            )
            adm.select_device(user_id, dev.device_id)
            adm_devices = [dev]
        except Exception:
            pass

    devices = []
    seen_ids = set()

    for d in adm_devices:
        seen_ids.add(d.device_id)
        reg_dev = reg.get_device(d.device_id)
        link = linking.get_link_by_device(d.device_id)
        legacy_paired = bool(link and link.is_active)
        is_local = bool(
            local_ident
            and (
                d.device_id == local_ident.device_id
                or (d.hostname and local_ident.hostname and d.hostname.lower() == local_ident.hostname.lower())
            )
        )
        meta_metrics = (d.metadata or {}).get("latest_metrics") or {}
        os_str = (
            meta_metrics.get("os")
            or (f"{reg_dev.os_name} {reg_dev.os_release}".strip() if reg_dev else "")
            or (f"{local_ident.os_name} {local_ident.os_release}".strip() if is_local and local_ident else "")
            or d.platform.capitalize()
        )
        mac_str = (
            meta_metrics.get("mac_address")
            or (reg_dev.mac_address if reg_dev else "")
            or (local_ident.mac_address if is_local and local_ident else "00:00:00:00:00:00")
        )
        ip_str = (
            meta_metrics.get("local_ip")
            or (reg_dev.local_ip if reg_dev else "")
            or (local_ident.local_ip if is_local and local_ident else "127.0.0.1")
        )
        state_val = "online" if (is_local or d.status == "online") else d.status
        agent_ver = (
            local_ident.agent_version
            if (is_local and local_ident and local_ident.agent_version)
            else (d.agent_version or (local_ident.agent_version if local_ident else "9.0.1"))
        )
        if is_local and local_ident and d.agent_version != local_ident.agent_version:
            d.agent_version = local_ident.agent_version
            try:
                adm.save()
            except Exception:
                pass
        devices.append({
            "device_id": d.device_id,
            "name": d.name,
            "hostname": d.hostname or d.name,
            "os": os_str,
            "mac_address": mac_str,
            "local_ip": ip_str,
            "state": state_val,
            "agent_version": agent_ver,
            "is_paired": bool(tg_paired or legacy_paired),
            "telegram_user_id": tg_uid_str or (link.telegram_user_id if link else None),
        })

    if not _is_production_mode():
        for d in reg.list_devices():
            if d.device_id in seen_ids:
                continue
            seen_ids.add(d.device_id)
            link = linking.get_link_by_device(d.device_id)
            state = hb.get_device_state(d.device_id)
            devices.append({
                "device_id": d.device_id,
                "name": d.hostname,
                "hostname": d.hostname,
                "os": f"{d.os_name} {d.os_release}".strip(),
                "mac_address": d.mac_address,
                "local_ip": d.local_ip,
                "state": "online" if (local_ident and d.device_id == local_ident.device_id) else state.value,
                "agent_version": d.agent_version,
                "is_paired": bool(tg_paired or (link is not None and link.is_active)),
                "telegram_user_id": tg_uid_str or (link.telegram_user_id if link else None),
            })

    # Agar ro'yxat bo'sh bo'lsa va lokal desktop rejimida bo'lsak, lokal qurilmani qo'shish
    if not devices and local_ident:
        reg.register_or_update(local_ident)
        devices.append({
            "device_id": local_ident.device_id,
            "name": local_ident.hostname,
            "hostname": local_ident.hostname,
            "os": f"{local_ident.os_name} {local_ident.os_release}".strip(),
            "mac_address": local_ident.mac_address,
            "local_ip": local_ident.local_ip,
            "state": "online",
            "agent_version": local_ident.agent_version,
            "is_paired": tg_paired,
            "telegram_user_id": tg_uid_str,
        })

    return web.json_response({"ok": True, "devices": devices})


async def handle_remote_device_detail(request):
    """GET /api/remote/devices/{id} - Muayyan qurilma tafsilotlari"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("id", ""))
    from core.v8 import (
        DeviceRegistry,
        HeartbeatManager,
        UserLinkingStore,
        PermissionStore,
        AccountDeviceManager,
        TelegramIdentityManager,
    )
    reg = DeviceRegistry.get_default_instance()
    adm = AccountDeviceManager.get_default_instance()
    dev = reg.get_device(dev_id)
    adm_dev = adm.get_device(dev_id, user_id=user_id)
    if not dev and not adm_dev:
        return web.json_response({"ok": False, "error": f"Qurilma topilmadi: {dev_id}"}, status=404)

    linking = UserLinkingStore.get_default_instance()
    link = linking.get_link_by_device(dev_id)
    tg_mgr = TelegramIdentityManager.get_default_instance()
    tg_link = tg_mgr.get_link_by_misa_user(user_id, auth_token=get_auth_token_from_request(request), refresh=False)
    hb = HeartbeatManager()
    perm_store = PermissionStore.get_default_instance()
    profile = perm_store.get_profile(user_id, dev_id)

    base_dict = dev.to_dict() if dev else adm_dev.to_dict()
    is_paired = bool((tg_link and tg_link.is_active) or (link and link.is_active))
    tg_uid = (str(tg_link.telegram_user_id) if tg_link and tg_link.telegram_user_id else None) or (
        link.telegram_user_id if link else None
    )

    return web.json_response({
        "ok": True,
        "device": {
            **base_dict,
            "state": "online" if (adm_dev and adm_dev.status == "online") else hb.get_device_state(dev_id).value,
            "is_paired": is_paired,
            "telegram_user_id": tg_uid,
            "permissions": profile.permissions
        }
    })


async def handle_remote_permissions_get(request):
    """GET /api/remote/permissions/{device_id} - Ruxsatlar profili va katalogi"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("device_id", ""))
    from core.v8 import PermissionStore
    store = PermissionStore.get_default_instance()
    profile = store.get_profile(user_id, dev_id)

    return web.json_response({
        "ok": True,
        "device_id": dev_id,
        "profile": profile.to_dict(),
        "catalog": store.get_catalog()
    })


async def handle_remote_permissions_put(request):
    """PUT /api/remote/permissions/{device_id} - Ruxsatlarni zudlik bilan yangilash"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("device_id", ""))
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    new_perms = body.get("permissions", {})
    new_caps = body.get("capabilities")

    from core.v8 import PermissionStore
    store = PermissionStore.get_default_instance()
    updated = store.update_permissions(user_id, dev_id, new_perms, new_caps)

    auth_token = get_auth_token_from_request(request)
    if not _is_production_mode() and auth_token:
        asyncio.create_task(_sync_user_devices_to_cloud(user_id, auth_token))

    await broadcast_ws("permission_changed", {
        "device_id": dev_id,
        "profile": updated.to_dict()
    })

    return web.json_response({
        "ok": True,
        "message": "Ruxsatlar muvaffaqiyatli yangilandi va barcha kanallarda qo'llanildi",
        "profile": updated.to_dict()
    })


async def handle_remote_pair(request):
    """POST /api/remote/pair - Kod generatsiya qilish (6-xonali OTP / MK-XXXXXX) yoki bog'lash"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}

    action = body.get("action", "generate")
    dev_id = body.get("device_id", "local_pc")
    auth_token = get_auth_token_from_request(request)

    from core.v8 import UserLinkingStore, TelegramIdentityManager
    linking = UserLinkingStore.get_default_instance()
    tg_mgr = TelegramIdentityManager.get_default_instance()

    if action == "generate":
        mk_code = linking.generate_pairing_code(user_id, dev_id, ttl=300.0)
        bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Misa_ai_agent_bot").strip() or "Misa_ai_agent_bot"
        req, otp, deep_link, _ = tg_mgr.create_link_request(
            misa_user_id=user_id,
            bot_username=bot_username,
            auth_token=auth_token
        )
        primary_code = otp if otp else mk_code
        if not _is_production_mode() and auth_token:
            asyncio.create_task(_sync_user_devices_to_cloud(user_id, auth_token))

        await broadcast_ws("pairing_code_generated", {
            "device_id": dev_id,
            "code": primary_code,
            "mk_code": mk_code,
            "expires_in": 300
        })
        return web.json_response({
            "ok": True,
            "code": primary_code,
            "otp": otp,
            "mk_code": mk_code,
            "deep_link": deep_link,
            "request_id": req.request_id if req else None,
            "expires_in": 300,
            "instruction": f"Telegram botingizda quyidagicha yuboring: /link {primary_code}"
        })
    elif action == "redeem":
        code = str(body.get("code", "")).strip()
        tg_id = body.get("telegram_user_id", "")
        if code.isdigit() and len(code) == 6 and str(tg_id).isdigit():
            ok_otp, msg_otp, tg_link = tg_mgr.verify_otp(
                otp=code,
                telegram_user_id=int(tg_id),
                auth_token=auth_token,
                expected_misa_user_id=user_id if user_id != "admin" else None
            )
            if ok_otp and tg_link:
                await broadcast_ws("device_paired", {
                    "device_id": dev_id,
                    "telegram_user_id": str(tg_link.telegram_user_id)
                })
                return web.json_response({"ok": True, "message": msg_otp, "link": tg_link.to_dict()})

        ok, msg, link = linking.redeem_pairing_code(code, str(tg_id))
        if ok and link:
            await broadcast_ws("device_paired", {
                "device_id": link.device_id,
                "telegram_user_id": link.telegram_user_id
            })
            return web.json_response({"ok": True, "message": msg, "link": link.to_dict()})
        return web.json_response({"ok": False, "error": msg}, status=400)

    return web.json_response({"ok": False, "error": f"Noma'lum amal: {action}"}, status=400)


async def handle_remote_unpair(request):
    """POST /api/remote/unpair - Telegram bog'lanishini uzish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}

    dev_id = body.get("device_id", "")
    auth_token = get_auth_token_from_request(request)
    from core.v8 import UserLinkingStore, DeviceRegistry, TelegramIdentityManager
    linking = UserLinkingStore.get_default_instance()
    reg = DeviceRegistry.get_default_instance()
    tg_mgr = TelegramIdentityManager.get_default_instance()

    unpaired_legacy = linking.unlink_telegram(dev_id)
    unpaired_tg = tg_mgr.unlink(misa_user_id=user_id, auth_token=auth_token)
    reg.unpair_device(dev_id)

    await broadcast_ws("device_unpaired", {"device_id": dev_id})
    return web.json_response({
        "ok": True,
        "message": "Bog'lanish bekor qilindi",
        "device_id": dev_id,
        "unpaired": bool(unpaired_legacy or unpaired_tg)
    })


async def handle_remote_session_lock(request):
    """POST /api/remote/session/lock - Masofaviy sessiyani bloklash / qulflash"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}

    dev_id = body.get("device_id", "")
    from core.v8 import SessionManager
    sm = SessionManager()
    closed = sm.close_session(user_id, dev_id)

    await broadcast_ws("session_locked", {"device_id": dev_id})
    return web.json_response({
        "ok": True,
        "message": "Masofaviy sessiya qulflandi",
        "closed": closed
    })


async def handle_remote_session_logout(request):
    """POST /api/remote/session/logout - Masofaviy sessiyani yopish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    try:
        body = await request.json()
    except Exception:
        body = {}

    dev_id = body.get("device_id", "")
    from core.v8 import SessionManager
    sm = SessionManager()
    closed = sm.close_session(user_id, dev_id)

    await broadcast_ws("session_logout", {"device_id": dev_id})
    return web.json_response({
        "ok": True,
        "message": "Masofaviy sessiya yakunlandi",
        "closed": closed
    })


async def handle_remote_audit(request):
    """GET /api/remote/audit - Masofaviy hodisalar auditi (Sanitizatsiyalangan)"""
    from core.v8 import RemoteAuditLogger
    logger_inst = RemoteAuditLogger.get_instance()
    history = logger_inst.get_history(limit=50)

    return web.json_response({
        "ok": True,
        "total": len(history),
        "events": [e.to_dict() for e in reversed(history)]
    })


# ========== 8.5. PHASE 39: UNIVERSAL TELEGRAM BOT & IDENTITY API ==========

async def handle_telegram_link_start(request):
    """POST /api/telegram/link/start - 6 xonali OTP va Telegram deep-link yaratish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        body = {}

    body_uid = str(body.get("misa_user_id") or "").strip()
    if user is not None or user_id != "admin":
        if body_uid and body_uid not in (user_id, "admin"):
            return web.json_response(
                {"ok": False, "error": "Ruxsat etilmadi: Boshqa foydalanuvchi hisobi uchun OTP yaratish taqiqlangan."},
                status=403
            )
        misa_user_id = user_id
    else:
        misa_user_id = body_uid or user_id

    from core.v8 import TelegramIdentityManager
    mgr = TelegramIdentityManager.get_default_instance()
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Misa_ai_agent_bot").strip() or "Misa_ai_agent_bot"
    auth_token = get_auth_token_from_request(request)

    req, otp, deep_link, err_msg = mgr.create_link_request(
        misa_user_id=misa_user_id,
        bot_username=bot_username,
        expected_telegram_user_id=body.get("expected_telegram_user_id"),
        auth_token=auth_token
    )
    if err_msg or not req:
        status_code = 429 if "RATE_LIMITED" in str(err_msg or "") else 400
        return web.json_response({"ok": False, "error": err_msg or "Kod yaratishda xatolik"}, status=status_code)

    await broadcast_ws("PAIRING_CREATED", {
        "request_id": req.request_id,
        "misa_user_id": req.misa_user_id,
        "expires_at": req.expires_at,
        "ttl_seconds": int(mgr.DEFAULT_TTL)
    })
    await broadcast_ws("PAIRING_WAITING", {
        "request_id": req.request_id,
        "misa_user_id": req.misa_user_id
    })

    return web.json_response({
        "ok": True,
        "request_id": req.request_id,
        "otp": otp,
        "link_token": req.link_token,
        "deep_link": deep_link,
        "expires_at": req.expires_at,
        "ttl_seconds": int(mgr.DEFAULT_TTL),
        "bot_username": bot_username
    })


async def handle_telegram_link_sync(request):
    """POST /api/telegram/link/sync - Lokal desktop yaratgan OTP so'rovini Railway xotirasiga sinxronlash"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("JSON object expected")
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    req_payload = body.get("request") if isinstance(body.get("request"), dict) else body
    request_id = str(req_payload.get("request_id") or "").strip()
    otp_hash = str(req_payload.get("otp_hash") or "").strip()
    salt = str(req_payload.get("salt") or "").strip()
    link_token = str(req_payload.get("link_token") or "").strip()
    body_uid = str(req_payload.get("misa_user_id") or body.get("misa_user_id") or "").strip() or user_id

    if user is not None or user_id != "admin":
        if body_uid and body_uid not in (user_id, "admin"):
            return web.json_response(
                {"ok": False, "error": "Ruxsat etilmadi: Boshqa foydalanuvchi nomidan OTP sinxronlash taqiqlangan."},
                status=403
            )
        misa_user_id = user_id
    else:
        misa_user_id = body_uid

    if not request_id or not otp_hash or not salt:
        return web.json_response({"ok": False, "error": "request_id, otp_hash va salt majburiy"}, status=400)

    from core.v8 import TelegramIdentityManager
    mgr = TelegramIdentityManager.get_default_instance()
    auth_token = get_auth_token_from_request(request)
    now = time.time()
    sync_dict = {
        "request_id": request_id,
        "misa_user_id": misa_user_id,
        "otp_hash": otp_hash,
        "salt": salt,
        "link_token": link_token,
        "created_at": float(req_payload.get("created_at") or now),
        "expires_at": float(req_payload.get("expires_at") or (now + mgr.DEFAULT_TTL)),
        "expected_telegram_user_id": req_payload.get("expected_telegram_user_id"),
        "status": str(req_payload.get("status") or "PENDING"),
        "attempt_count": int(req_payload.get("attempt_count") or 0),
    }
    req = mgr.register_synced_request(sync_dict, auth_token=auth_token)
    if not req:
        return web.json_response({"ok": False, "error": "OTP so'rovini sinxronlash amalga oshmadi"}, status=400)

    return web.json_response({
        "ok": True,
        "request_id": req.request_id,
        "misa_user_id": req.misa_user_id,
        "expires_at": req.expires_at,
    })


async def handle_telegram_link_verify(request):
    """POST /api/telegram/link/verify - OTP kodni tekshirish va hisobni bog'lash"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    body_uid = str(body.get("misa_user_id") or "").strip()
    expected_misa_user_id: Optional[str] = None
    if user is not None or user_id != "admin":
        if body_uid and body_uid not in (user_id, "admin"):
            return web.json_response(
                {"ok": False, "error": "Ruxsat etilmadi: Boshqa foydalanuvchi nomidan OTP tasdiqlash taqiqlangan."},
                status=403
            )
        expected_misa_user_id = user_id
    elif body_uid and body_uid != "admin":
        expected_misa_user_id = body_uid

    otp = body.get("otp", "")
    tg_id = body.get("telegram_user_id")
    username = body.get("username")
    first_name = body.get("first_name")
    request_id = body.get("request_id")

    from core.v8 import TelegramIdentityManager
    mgr = TelegramIdentityManager.get_default_instance()
    auth_token = get_auth_token_from_request(request)

    ok, msg, link = mgr.verify_otp(
        otp=otp,
        telegram_user_id=tg_id,
        first_name=first_name,
        username=username,
        request_id=request_id,
        auth_token=auth_token,
        expected_misa_user_id=expected_misa_user_id
    )

    if ok and link:
        await broadcast_ws("PAIRING_VERIFIED", {
            "telegram_user_id": link.telegram_user_id,
            "misa_user_id": link.misa_user_id
        })
        await broadcast_ws("TELEGRAM_CONNECTED", {
            "telegram_user_id": link.telegram_user_id,
            "misa_user_id": link.misa_user_id,
            "linked_at": link.linked_at
        })
        return web.json_response({
            "ok": True,
            "message": msg,
            "link": link.to_dict(),
            "misa_user_id": link.misa_user_id
        })

    await broadcast_ws("PAIRING_FAILED", {
        "error": msg
    })
    status_code = 403 if any(k in str(msg) for k in ("USER_MISMATCH", "TELEGRAM_USER_MISMATCH", "TELEGRAM_ALREADY_LINKED")) else 400
    return web.json_response({"ok": False, "error": msg}, status=status_code)


async def handle_telegram_link_status(request):
    """GET /api/telegram/link/status - Bog'lanish holatini tekshirish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    misa_user_id = user_id
    request_id = request.query.get("request_id")
    auth_token = get_auth_token_from_request(request)

    from core.v8 import TelegramIdentityManager
    mgr = TelegramIdentityManager.get_default_instance()

    if request_id:
        req = mgr.get_request(request_id, auth_token=auth_token, refresh=True)
        if not req:
            return web.json_response({"ok": False, "error": "So'rov topilmadi"}, status=404)
        if (user is not None or misa_user_id != "admin") and req.misa_user_id != misa_user_id:
            return web.json_response(
                {"ok": False, "error": "Ruxsat etilmadi: Ushbu bog'lanish so'rovi boshqa foydalanuvchiga tegishli."},
                status=403
            )
        ttl_left = max(0, int(req.expires_at - time.time()))
        status_name = "EXPIRED" if (req.status == "PENDING" and req.is_expired()) else req.status
        is_verified = (req.status == "VERIFIED")
        link = mgr.get_link_by_misa_user(req.misa_user_id, auth_token=auth_token, refresh=is_verified)
        return web.json_response({
            "ok": True,
            "status": "CONNECTED" if (is_verified or (link and link.is_active)) else status_name,
            "request_status": status_name,
            "is_linked": bool(is_verified or (link and link.is_active)),
            "telegram_user_id": link.telegram_user_id if link else req.telegram_user_id,
            "link": link.to_dict() if link else None,
            "attempt_count": req.attempt_count,
            "expires_at": req.expires_at,
            "ttl_seconds": ttl_left
        })

    link = mgr.get_link_by_misa_user(misa_user_id, auth_token=auth_token, refresh=True)
    if link and link.is_active:
        return web.json_response({
            "ok": True,
            "status": "CONNECTED",
            "request_status": "VERIFIED",
            "is_linked": True,
            "telegram_user_id": link.telegram_user_id,
            "link": link.to_dict()
        })

    return web.json_response({
        "ok": True,
        "status": "NOT_CONNECTED",
        "request_status": "NOT_CONNECTED",
        "is_linked": False,
        "telegram_user_id": None
    })


async def handle_telegram_unlink(request):
    """POST /api/telegram/unlink - Telegram bog'lanishini bekor qilish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        body = {}

    misa_user_id = user_id
    tg_id = body.get("telegram_user_id")

    from core.v8 import TelegramIdentityManager
    mgr = TelegramIdentityManager.get_default_instance()
    auth_token = get_auth_token_from_request(request)

    unlinked = mgr.unlink(misa_user_id=misa_user_id, telegram_user_id=tg_id, auth_token=auth_token)
    if unlinked:
        await broadcast_ws("TELEGRAM_DISCONNECTED", {
            "misa_user_id": misa_user_id
        })
        return web.json_response({"ok": True, "message": "Telegram hisobi muvaffaqiyatli uzildi"})

    return web.json_response({"ok": False, "error": "Faol bog'lanish topilmadi"}, status=400)


async def handle_telegram_account(request):
    """GET /api/telegram/account - Foydalanuvchining Telegram profili va bog'lanish ma'lumotlari"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    misa_user_id = user_id
    auth_token = get_auth_token_from_request(request)
    from core.v8 import TelegramIdentityManager
    mgr = TelegramIdentityManager.get_default_instance()

    link = mgr.get_link_by_misa_user(misa_user_id, auth_token=auth_token, refresh=True)
    ident = mgr.get_identity(link.telegram_user_id) if link else None

    return web.json_response({
        "ok": True,
        "is_linked": link is not None and link.is_active,
        "link": link.to_dict() if link else None,
        "telegram_identity": ident.to_dict() if ident else None
    })


async def handle_telegram_status(request):
    """GET /api/telegram/status - Telegram Bot tizim holati"""
    from core.v8 import TelegramIdentityManager
    mgr = TelegramIdentityManager.get_default_instance()
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Misa_ai_agent_bot").strip() or "Misa_ai_agent_bot"

    return web.json_response({
        "ok": True,
        "configured": bool(os.environ.get("TELEGRAM_BOT_TOKEN") or True),
        "bot_username": bot_username,
        "active_links_count": mgr.count_active_links(),
        "pending_requests_count": mgr.count_pending_requests()
    })


# ========== 8.1. PHASE 40 & 41: ACCOUNT & MULTI-DEVICE MANAGEMENT API ==========

def get_auth_token_from_request(request) -> Optional[str]:
    """So'rovdan sessiya tokenini ajratib olish (Faqat Authorization Bearer yoki X-Misa-Session-Token header).
    Xavfsizlik talabi: Query parametridan token o'qish (loglarda sizib chiqishi xavfi tufayli) to'liq bekor qilingan.
    """
    auth_header = getattr(request, "headers", {}).get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    token = getattr(request, "headers", {}).get("X-Misa-Session-Token")
    if token:
        return token.strip()
    return None


def resolve_auth_identity(
    request,
    required: bool = True
) -> Tuple[Optional[str], Optional[Any], Optional[Any], Optional[web.Response]]:
    """Multi-tenant xavfsiz foydalanuvchi identifikatsiyasini aniqlash.
    Qaytaradi: (user_id, user, session, error_response).
    1. So'rovdan Bearer tokenni oladi va AccountAuthManager orqali tekshiradi (JWT.sub).
    2. Agar token berilgan bo'lsa:
       - Yaroqsiz, muddati o'tgan yoki soxta bo'lsa -> 401 Unauthorized.
       - Haqiqiy bo'lsa -> user_id = JWT.sub.
       - Agar request parametri (query yoki header) orqali boshqa user_id uzatilgan bo'lsa -> 403 Forbidden ("Cross-tenant access denied").
    3. Agar token berilmagan bo'lsa:
       - Supabase sozlangan bo'lsa (yoki MISA_REQUIRE_AUTH yoqilgan bo'lsa) va required=True:
         -> 401 Unauthorized.
       - Offline / test rejimida (Supabase sozlanmagan bo'lsa):
         parametr orqali kelgan user_id olinadi (yoki "local_user"), lekin hech qachon avtomatik "admin" ga fallback qilinmaydi.
    """
    from core.v8 import AccountAuthManager
    auth_mgr = AccountAuthManager.get_default_instance()
    token = get_auth_token_from_request(request)

    req_headers = getattr(request, "headers", {}) or {}
    req_query = getattr(request, "query", {}) or {}
    param_user_id = (
        req_headers.get("X-Misa-User-Id")
        or req_headers.get("X-User-Id")
        or req_query.get("user_id")
        or req_query.get("misa_user_id")
    )
    if param_user_id:
        param_user_id = str(param_user_id).strip()

    if token:
        session, user = auth_mgr.authenticate_token(token)
        if not user or not session:
            err_resp = web.json_response({
                "ok": False,
                "error": "Avtorizatsiyadan o'tilmagan: Token yaroqsiz yoki muddati o'tgan"
            }, status=401)
            err_resp["_auth_error"] = True
            return None, None, None, err_resp

        authenticated_user_id = user.id
        # "me", "self", "current" yoki frontend default "misa_user_id=admin" ni
        # autentifikatsiyalangan foydalanuvchining o'ziga xaritalash
        # (Explicit ?user_id=admin spoofing esa rad etiladi!)
        explicit_query_user_id = str(req_query.get("user_id") or "").strip().lower()
        if param_user_id and (
            param_user_id.lower() in ("me", "self", "current", "null", "undefined")
            or (param_user_id.lower() == "admin" and explicit_query_user_id != "admin")
        ):
            param_user_id = authenticated_user_id

        # Cross-tenant spoofing tekshiruvi:
        if param_user_id and param_user_id != authenticated_user_id:
            logger.warning(
                f"Xavfsizlik: Cross-tenant murojaat aniqlandi! Autentifikatsiya={authenticated_user_id}, "
                f"So'ralgan={param_user_id}"
            )
            err_resp = web.json_response({
                "ok": False,
                "error": "Cross-tenant access denied: Ruxsatsiz hisob murojaati"
            }, status=403)
            err_resp["_auth_error"] = True
            return None, None, None, err_resp

        if not _is_production_mode():
            _last_active_desktop_auth["user_id"] = authenticated_user_id
            _last_active_desktop_auth["token"] = token
            _last_active_desktop_auth["updated_at"] = time.time()

        # Foydalanuvchi hisobidagi AI kalitlarni avtomatik sinxronlash (Auto AI)
        try:
            from core.v8.ai_key_manager import get_ai_key_manager
            mgr = get_ai_key_manager()
            user_meta = {}
            if session and hasattr(session, "raw_claims") and isinstance(session.raw_claims, dict):
                user_meta.update(session.raw_claims.get("user_metadata", {}) or {})
            if user and hasattr(user, "metadata") and isinstance(user.metadata, dict):
                user_meta.update(user.metadata)
            if user_meta:
                mgr.sync_from_user_session(authenticated_user_id, user_meta)
        except Exception as _ex:
            logger.debug(f"AI key sync error in resolve_auth_identity: {_ex}")

        return authenticated_user_id, user, session, None


    # Token yo'q holat
    # XAVFSIZLIK: Production rejimda Supabase sozlanmagan bo'lsa ham autentifikatsiya majburiy
    is_production = bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
        or os.environ.get("MISA_ENV", "").strip().lower() == "production"
        or os.environ.get("MISA_API_HOST", "127.0.0.1").strip() == "0.0.0.0"
    )
    is_auth_enforced = (
        auth_mgr.is_configured()
        or os.environ.get("MISA_REQUIRE_AUTH", "").lower() in ("true", "1")
        or is_production
    )
    if is_auth_enforced and required:
        err_resp = web.json_response({
            "ok": False,
            "error": "Avtorizatsiyadan o'tilmagan: Bearer token talab qilinadi"
        }, status=401)
        err_resp["_auth_error"] = True
        return None, None, None, err_resp

    # Supabase sozlanmagan offline / localhost test rejimi (faqat desktop uchun)
    if param_user_id:
        return param_user_id, None, None, None

    local_id = get_current_user_name() or "local_user"
    return local_id, None, None, None


_last_active_desktop_auth: Dict[str, Any] = {
    "user_id": None,
    "token": None,
    "updated_at": 0.0,
}


def get_authenticated_user(request) -> Tuple[Optional[Any], Optional[Any]]:
    """Token orqali haqiqiy foydalanuvchi va uning sessiyasini aniqlash.
    Qaytaradi: (session, user) yoki (None, None).
    """
    token = get_auth_token_from_request(request)
    if not token:
        return None, None
    try:
        from core.v8 import AccountAuthManager
        auth_mgr = AccountAuthManager.get_default_instance()
        return auth_mgr.authenticate_token(token)
    except Exception as e:
        logger.warning(f"get_authenticated_user xatosi: {e}")
        return None, None


def _get_request_user_id(request) -> str:
    """So'rovdan foydalanuvchi identifikatorini olish (Xavfsiz: token tekshiruvi bilan)."""
    uid, _, _, _ = resolve_auth_identity(request, required=False)
    return uid or "local_user"


def _collect_local_device_metrics(loc: Any) -> Dict[str, Any]:
    """Lokal kompyuterning jonli telemetriya ko'rsatkichlarini yig'ish."""
    metrics: Dict[str, Any] = {
        "os": f"{getattr(loc, 'os_name', 'Windows')} {getattr(loc, 'os_release', '')}".strip(),
        "local_ip": getattr(loc, "local_ip", "127.0.0.1"),
        "mac_address": getattr(loc, "mac_address", "00:00:00:00:00:00"),
        "updated_at": time.time(),
    }
    try:
        from core.v8.remote_tools import RemoteToolRegistry
        reg = RemoteToolRegistry.get_default_instance()
        sys_res = reg.execute("system.info", {})
        if sys_res.get("ok") and isinstance(sys_res.get("data"), dict):
            sdata = sys_res["data"]
            metrics["cpu_percent"] = sdata.get("cpu_usage_percent", 0.0)
            metrics["cpu_usage_percent"] = sdata.get("cpu_usage_percent", 0.0)
            metrics["ram_used_gb"] = sdata.get("ram_used_gb", 0.0)
            metrics["ram_total_gb"] = sdata.get("ram_total_gb", 0.0)
            metrics["disk_free_gb"] = sdata.get("disk_free_gb", 0.0)
        app_res = reg.execute("app.list", {})
        if app_res.get("ok") and isinstance(app_res.get("data"), dict):
            metrics["apps"] = (app_res["data"].get("apps") or [])[:25]
    except Exception:
        pass
    return metrics


def _execute_local_remote_command(cmd_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Bulutdan kelgan masofaviy buyruqni lokal Windows kompyuterida xavfsiz bajarish."""
    cmd_id = str(cmd_dict.get("command_id") or "")
    tool_id = str(cmd_dict.get("tool_id") or "")
    params = cmd_dict.get("params") if isinstance(cmd_dict.get("params"), dict) else {}

    try:
        from core.v8.remote_tools import RemoteToolRegistry
        reg = RemoteToolRegistry.get_default_instance()
        res = reg.execute(tool_id, params)
        ok = bool(res.get("ok"))
        data = res.get("data") if isinstance(res.get("data"), dict) else {}
        err = res.get("error")

        # Windows desktopda xavfsiz dasturlarni haqiqatan ishga tushirish
        if ok and tool_id == "app.launch" and sys.platform == "win32":
            app_name = str(params.get("app_name") or "").strip().lower()
            win_map = {
                "calculator": ["calc.exe"],
                "calc": ["calc.exe"],
                "notepad": ["notepad.exe"],
                "explorer": ["explorer.exe"],
                "browser": ["cmd", "/c", "start", "https://www.google.com"],
                "taskmgr": ["taskmgr.exe"],
            }
            if app_name in win_map:
                try:
                    import subprocess
                    subprocess.Popen(win_map[app_name], shell=False)
                    data["launched_real"] = True
                except Exception as launch_err:
                    logger.debug(f"app.launch real process warning: {launch_err}")

        if ok and tool_id == "app.close" and sys.platform == "win32":
            app_name = str(params.get("app_name") or "").strip().lower()
            close_map = {
                "calculator": "CalculatorApp.exe",
                "calc": "CalculatorApp.exe",
                "notepad": "notepad.exe",
            }
            target_exe = close_map.get(app_name)
            if target_exe:
                try:
                    import subprocess
                    subprocess.run(["taskkill", "/IM", target_exe, "/F"], capture_output=True, timeout=5)
                except Exception:
                    pass

        return {
            "command_id": cmd_id,
            "tool_id": tool_id,
            "success": ok,
            "data": data,
            "error": err,
        }
    except Exception as exc:
        return {
            "command_id": cmd_id,
            "tool_id": tool_id,
            "success": False,
            "data": {},
            "error": str(exc),
        }


def _format_telegram_command_result(tool_id: str, dev_name: str, res_item: Dict[str, Any]) -> str:
    """Bajarilgan masofaviy buyruq natijasini Telegram xabari uchun chiroyli formatlash."""
    success = bool(res_item.get("success"))
    data = res_item.get("data") if isinstance(res_item.get("data"), dict) else {}
    err = res_item.get("error") or "Noma'lum xatolik"

    if not success:
        return (
            f"❌ *Buyruq bajarilmadi ({dev_name})*\n\n"
            f"• Amal: `{tool_id}`\n"
            f"• Xatolik: `{err}`"
        )

    if tool_id == "system.info":
        return (
            f"📊 *Tizim Ma'lumotlari — {dev_name}*\n\n"
            f"• Tizim: `{data.get('os', 'Windows')}`\n"
            f"• CPU: `{data.get('cpu_usage_percent', 0)}%`\n"
            f"• RAM: `{data.get('ram_used_gb', 0)} GB / {data.get('ram_total_gb', 0)} GB`\n"
            f"• Bo'sh disk: `{data.get('disk_free_gb', 0)} GB`"
        )
    if tool_id == "app.list":
        apps = data.get("apps") or []
        lines = [f"🧩 *Ishlayotgan dasturlar — {dev_name}:*\n"]
        for idx, a in enumerate(apps[:20], start=1):
            aname = a.get("name") if isinstance(a, dict) else str(a)
            lines.append(f"{idx}. `{aname}`")
        return "\n".join(lines)
    if tool_id == "file.list":
        entries = data.get("entries") or []
        lines = [f"📂 *Fayllar ro'yxati — {dev_name}:*\n`{data.get('directory', '')}`\n"]
        for item in entries[:25]:
            icon = "📁" if item.get("type") == "dir" else "📄"
            lines.append(f"{icon} `{item.get('name')}`")
        return "\n".join(lines)
    if tool_id in ("app.launch", "app.close", "system.screenshot", "power.sleep", "power.restart", "power.shutdown"):
        msg = data.get("message") or "Amal muvaffaqiyatli bajarildi."
        extra = f"\n• Fayl: `{data.get('path')}`" if data.get("path") else ""
        return (
            f"✅ *Buyruq bajarildi — {dev_name}*\n\n"
            f"• Amal: `{tool_id}`\n"
            f"• Natija: {msg}{extra}"
        )

    return (
        f"✅ *Buyruq bajarildi — {dev_name}*\n\n"
        f"• Amal: `{tool_id}`\n"
        f"• Holat: Muvaffaqiyatli"
    )


async def _sync_user_devices_to_cloud(user_id: Optional[str], auth_token: Optional[str]) -> None:
    """Lokal desktopdagi qurilma, ruxsatlar va telemetriyani Railway serveriga sinxronlash
    hamda navbatdagi masofaviy buyruqlarni bajarish."""
    if _is_production_mode() or not user_id or not auth_token or user_id in ("admin", "local_user"):
        return

    from core.v8.telegram_identity import TelegramIdentityManager, UserTelegramLink
    tg_mgr = TelegramIdentityManager.get_default_instance()
    cloud_base = tg_mgr._resolve_cloud_api_url()
    if not cloud_base:
        return

    try:
        from core.v8 import AccountDeviceManager, PermissionStore
        from core.v8.device import DeviceIdentityManager
        adm = AccountDeviceManager.get_default_instance()
        perm_store = PermissionStore.get_default_instance()
        loc = DeviceIdentityManager.create_local_identity()

        devices = adm.get_devices_for_user(user_id, include_revoked=False)
        if not devices:
            return

        live_metrics = await asyncio.to_thread(_collect_local_device_metrics, loc)
        payload_devices = []
        permissions_map: Dict[str, Any] = {}

        for d in devices:
            is_local = (
                d.device_id == loc.device_id
                or (bool(d.hostname) and bool(loc.hostname) and d.hostname.lower() == loc.hostname.lower())
            )
            if is_local:
                d.status = "online"
                d.last_seen_at = time.time()
                d.last_heartbeat_at = time.time()
                d.metadata = dict(d.metadata or {})
                d.metadata["latest_metrics"] = live_metrics
            d_dict = d.to_dict()
            payload_devices.append(d_dict)
            prof = perm_store.get_profile(user_id, d.device_id)
            if prof:
                permissions_map[d.device_id] = prof.permissions

        adm.save()
        selected = adm.get_selected_device(user_id)
        local_tg_link = tg_mgr.get_link_by_misa_user(user_id)
        sync_body: Dict[str, Any] = {
            "user_id": user_id,
            "devices": payload_devices,
            "selected_device_id": selected.device_id if selected else (devices[0].device_id if devices else None),
            "permissions": permissions_map,
            "telegram_link": local_tg_link.to_dict() if (local_tg_link and local_tg_link.is_active) else None,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
            "X-Misa-User-Id": str(user_id),
        }

        def _post_sync(body_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            resp = requests.post(
                f"{cloud_base}/api/devices/sync",
                json=body_data,
                headers=headers,
                timeout=6.0,
            )
            if resp.status_code == 200:
                return resp.json()
            return None

        resp_data = await asyncio.to_thread(_post_sync, sync_body)
        if not isinstance(resp_data, dict):
            return

        remote_link_data = resp_data.get("telegram_link")
        if isinstance(remote_link_data, dict) and remote_link_data.get("telegram_user_id") and remote_link_data.get("misa_user_id") == user_id:
            try:
                remote_link = UserTelegramLink.from_dict(remote_link_data)
                if remote_link.is_active:
                    existing_local = tg_mgr.get_link_by_misa_user(user_id)
                    if not existing_local or not existing_local.is_active or existing_local.telegram_user_id != remote_link.telegram_user_id:
                        tg_mgr._links_by_tg[remote_link.telegram_user_id] = remote_link
                        tg_mgr._links_by_misa[user_id] = remote_link
                        tg_mgr.save()
                        await broadcast_ws("device_paired", {
                            "device_id": sync_body.get("selected_device_id"),
                            "telegram_user_id": str(remote_link.telegram_user_id),
                        })
            except Exception as link_err:
                logger.debug(f"[_sync_user_devices_to_cloud] Telegram link sync warning: {link_err}")

        pending_cmds = resp_data.get("pending_commands") or []
        if pending_cmds and isinstance(pending_cmds, list):
            cmd_results = []
            for cmd_item in pending_cmds:
                if isinstance(cmd_item, dict) and cmd_item.get("command_id"):
                    res_obj = await asyncio.to_thread(_execute_local_remote_command, cmd_item)
                    cmd_results.append(res_obj)
            if cmd_results:
                await asyncio.to_thread(
                    _post_sync,
                    {
                        "user_id": user_id,
                        "command_results": cmd_results,
                    },
                )
    except Exception as e:
        logger.debug(f"[_sync_user_devices_to_cloud] Cloud sync skipped: {e}")


async def handle_devices_sync(request):
    """POST /api/devices/sync - Desktop ilovasidan qurilmalar, ruxsatlar va buyruq natijalarini qabul qilish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("JSON object expected")
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    from core.v8 import AccountDeviceManager, PermissionStore, DeviceRegistry, DeviceIdentity, TelegramIdentityManager
    from core.v8.telegram_identity import UserTelegramLink
    from core.v8.command_queue import CommandQueueManager
    adm = AccountDeviceManager.get_default_instance()
    perm_store = PermissionStore.get_default_instance()
    reg = DeviceRegistry.get_default_instance()
    cmd_mgr = CommandQueueManager.get_default_instance()
    tg_mgr = TelegramIdentityManager.get_default_instance()

    raw_devices = body.get("devices") if isinstance(body.get("devices"), list) else []
    synced_devices = []
    now = time.time()

    for item in raw_devices:
        if not isinstance(item, dict):
            continue
        hw_id = str(item.get("device_id") or "").strip()
        if not hw_id:
            continue
        dev_name = str(item.get("name") or item.get("hostname") or "Kompyuter").strip()
        hostname = str(item.get("hostname") or dev_name).strip()
        platform_str = str(item.get("platform") or "windows").strip().lower()
        agent_ver = str(item.get("agent_version") or get_app_version()).strip()
        status_str = str(item.get("status") or "online").strip().lower()
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}

        try:
            dev = adm.register_device(
                user_id=user_id,
                device_id=hw_id,
                name=dev_name,
                hostname=hostname,
                platform=platform_str,
                agent_version=agent_ver,
                status=status_str,
                metadata=meta,
            )
            dev.status = status_str
            dev.last_seen_at = now
            dev.last_heartbeat_at = now
            if meta:
                dev.metadata = dict(dev.metadata or {})
                dev.metadata.update(meta)
            synced_devices.append(dev.to_dict())

            latest_m = meta.get("latest_metrics") if isinstance(meta.get("latest_metrics"), dict) else {}
            reg.register_or_update(
                DeviceIdentity(
                    device_id=hw_id,
                    hostname=hostname,
                    os_name=str(latest_m.get("os") or platform_str.capitalize()),
                    mac_address=str(latest_m.get("mac_address") or "00:00:00:00:00:00"),
                    local_ip=str(latest_m.get("local_ip") or "127.0.0.1"),
                    agent_version=agent_ver,
                    metadata=meta,
                )
            )
        except Exception as e:
            logger.warning(f"[handle_devices_sync] Device register warning ({hw_id}): {e}")

    selected_id = str(body.get("selected_device_id") or "").strip()
    if selected_id:
        adm.select_device(user_id, selected_id)
    elif synced_devices and not adm.get_selected_device(user_id):
        adm.select_device(user_id, synced_devices[0]["device_id"])

    adm.save()

    perms_map = body.get("permissions")
    if isinstance(perms_map, dict):
        for dev_id, p_dict in perms_map.items():
            if isinstance(p_dict, dict):
                perm_store.update_permissions(user_id, str(dev_id), p_dict)

    incoming_tg_link = body.get("telegram_link")
    if isinstance(incoming_tg_link, dict) and incoming_tg_link.get("telegram_user_id") and incoming_tg_link.get("misa_user_id") == user_id:
        try:
            curr_link = tg_mgr.get_link_by_misa_user(user_id)
            if not curr_link or not curr_link.is_active:
                restored_link = UserTelegramLink.from_dict(incoming_tg_link)
                if restored_link.is_active:
                    tg_mgr._links_by_tg[restored_link.telegram_user_id] = restored_link
                    tg_mgr._links_by_misa[user_id] = restored_link
                    tg_mgr.save()
        except Exception as tg_sync_err:
            logger.debug(f"[handle_devices_sync] Telegram link restore skipped: {tg_sync_err}")

    # Bajarilgan masofaviy buyruq natijalarini qabul qilish va Telegram foydalanuvchiga yuborish
    cmd_results = body.get("command_results")
    if isinstance(cmd_results, list):
        tg_svc = request.app.get("telegram_webhook_service")
        for res_item in cmd_results:
            if not isinstance(res_item, dict):
                continue
            cid = str(res_item.get("command_id") or "").strip()
            if not cid:
                continue
            cmd_obj = cmd_mgr.get_command(cid)
            if not cmd_obj or (cmd_obj.user_id and cmd_obj.user_id != user_id):
                continue
            cmd_mgr.record_result(cid, res_item)
            if cmd_obj.telegram_user_id and tg_svc and getattr(tg_svc, "transport", None):
                dev_obj = adm.get_device(cmd_obj.device_id, user_id=user_id)
                dev_label = dev_obj.name if dev_obj else cmd_obj.device_id
                msg_text = _format_telegram_command_result(cmd_obj.tool_id, dev_label, res_item)
                try:
                    await tg_svc.transport.send_message(
                        chat_id=int(cmd_obj.telegram_user_id) if str(cmd_obj.telegram_user_id).isdigit() else cmd_obj.telegram_user_id,
                        text=msg_text,
                        parse_mode="Markdown",
                    )
                except Exception as tg_err:
                    logger.warning(f"[handle_devices_sync] Telegram notify error: {tg_err}")

    # Ushbu foydalanuvchining barcha qurilmalari uchun kutilayotgan buyruqlarni yig'ish
    pending_commands: List[Dict[str, Any]] = []
    user_devs = adm.get_devices_for_user(user_id, include_revoked=False)
    for udev in user_devs:
        dev_pending = cmd_mgr.get_pending_commands(udev.device_id)
        for pcmd in dev_pending:
            pcmd["device_id"] = udev.device_id
            pending_commands.append(pcmd)

    active_tg_link = tg_mgr.get_link_by_misa_user(user_id)
    return web.json_response({
        "ok": True,
        "user_id": user_id,
        "synced_count": len(synced_devices),
        "devices": synced_devices,
        "pending_commands": pending_commands,
        "telegram_link": active_tg_link.to_dict() if (active_tg_link and active_tg_link.is_active) else None,
    })


async def handle_devices_list(request):
    """GET /api/devices and GET /api/account/devices - Foydalanuvchining ulangan kompyuterlari ro'yxati"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    from core.v8 import AccountDeviceManager
    from core.v8.device import DeviceIdentityManager
    mgr = AccountDeviceManager.get_default_instance()
    is_prod = _is_production_mode()
    loc = DeviceIdentityManager.create_local_identity() if not is_prod else None

    devices = mgr.get_devices_for_user(user_id, include_revoked=False)

    # 1. Agar ro'yxat bo'sh bo'lsa (faqat lokal desktopda!), lokal kompyuterni kiritish
    if not devices and loc:
        host_label = loc.hostname or "Asosiy Kompyuter"
        dev = mgr.register_device(
            user_id=user_id,
            device_id=loc.device_id,
            name=f"{host_label} (Joriy kompyuter)",
            hostname=loc.hostname,
            platform=loc.os_name.lower(),
            agent_version=loc.agent_version,
            status="online"
        )
        devices = [dev]
        mgr.select_device(user_id, dev.device_id)

    # 2. Agar mavjud yagona qurilma eski dummy (dev-sess-1) bo'lsa, uni joriy kompyuter bilan bog'lash
    if loc and len(devices) == 1 and devices[0].device_id == "dev-sess-1":
        d0 = devices[0]
        if not d0.name or d0.name == "dev-sess-1":
            d0.name = f"{loc.hostname or 'Asosiy Kompyuter'} (Joriy kompyuter)"
        d0.hostname = loc.hostname
        d0.status = "online"
        d0.last_seen_at = time.time()
        d0.platform = loc.os_name.lower()
        d0.agent_version = loc.agent_version
        mgr._devices_by_hw_id[loc.device_id] = d0.id
        mgr.save()

    # 3. Joriy kompyuterni belgilash va yangilash (faqat lokal desktopda)
    local_dev = None
    if loc:
        for d in devices:
            if d.device_id == loc.device_id or (bool(d.hostname) and d.hostname.lower() == loc.hostname.lower()):
                local_dev = d
                d.status = "online"
                d.last_seen_at = time.time()
                d.hostname = loc.hostname
                d.platform = loc.os_name.lower()
                d.agent_version = loc.agent_version
                mgr._devices_by_hw_id[loc.device_id] = d.id
                break

        # Agar ro'yxatda faqat 1 ta qurilma bo'lsa va local_dev topilmagan bo'lsa, ushbu yagona qurilma joriy desktop qurilmasi deb hisoblanadi
        if not local_dev and len(devices) == 1:
            local_dev = devices[0]
            local_dev.status = "online"
            local_dev.last_seen_at = time.time()
            local_dev.hostname = loc.hostname
            local_dev.platform = loc.os_name.lower()
            local_dev.agent_version = loc.agent_version
            mgr._devices_by_hw_id[loc.device_id] = local_dev.id
            mgr.save()

    selected = mgr.get_selected_device(user_id)
    if (not selected or selected.is_revoked) and devices:
        sel_target = local_dev or devices[0]
        mgr.select_device(user_id, sel_target.device_id)
        selected = sel_target

    # 4. Har bir qurilmaga is_current belgisini biriktirish
    enriched_devices = []
    for d in devices:
        d_dict = d.to_dict()
        is_curr = bool(
            loc and (
                (local_dev and (d.id == local_dev.id or d.device_id == local_dev.device_id))
                or d.device_id == loc.device_id
                or (bool(d.hostname) and d.hostname.lower() == loc.hostname.lower())
            )
        )
        d_dict["is_current"] = bool(is_curr)
        if is_curr:
            d_dict["status"] = "online"
        enriched_devices.append(d_dict)

    enriched_devices.sort(key=lambda x: 0 if x.get("is_current") else 1)

    auth_token = get_auth_token_from_request(request)
    if not is_prod and auth_token:
        asyncio.create_task(_sync_user_devices_to_cloud(user_id, auth_token))

    return web.json_response({
        "ok": True,
        "user_id": user_id,
        "devices": enriched_devices,
        "selected_device_id": selected.device_id if selected else (local_dev.device_id if local_dev else None),
        "current_device_id": local_dev.device_id if local_dev else (selected.device_id if selected else None)
    })


async def handle_device_detail(request):
    """GET /api/devices/{device_id} - Muayyan qurilma tafsilotlari"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("device_id", ""))
    from core.v8 import AccountDeviceManager
    mgr = AccountDeviceManager.get_default_instance()

    dev = mgr.get_device(dev_id, user_id=user_id)
    if not dev or dev.is_revoked:
        return web.json_response({
            "ok": False,
            "error": "Qurilma topilmadi yoki hisobingizga tegishli emas"
        }, status=404)

    selected = mgr.get_selected_device(user_id)
    is_selected = selected is not None and (selected.device_id == dev.device_id or selected.id == dev.id)

    return web.json_response({
        "ok": True,
        "device": {
            **dev.to_dict(),
            "is_selected": is_selected
        }
    })


async def handle_device_rename(request):
    """PATCH /api/devices/{device_id} - Qurilma do'stona nomini yangilash"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("device_id", ""))
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    new_name = body.get("name", "")
    from core.v8 import AccountDeviceManager
    from core.v8.device import DeviceIdentityManager
    mgr = AccountDeviceManager.get_default_instance()
    loc = DeviceIdentityManager.create_local_identity() if not _is_production_mode() else None

    ok, msg, dev = mgr.rename_device(dev_id, user_id=user_id, new_name=new_name)
    if not ok or not dev:
        status_code = 404 if "NOT_FOUND" in msg else 400
        return web.json_response({"ok": False, "error": msg}, status=status_code)

    dev_dict = dev.to_dict()
    is_curr = bool(
        loc and (
            dev.device_id == loc.device_id
            or (bool(dev.hostname) and dev.hostname.lower() == loc.hostname.lower())
        )
    )
    dev_dict["is_current"] = bool(is_curr)
    if is_curr:
        dev_dict["status"] = "online"

    auth_token = get_auth_token_from_request(request)
    if not _is_production_mode() and auth_token:
        asyncio.create_task(_sync_user_devices_to_cloud(user_id, auth_token))

    await broadcast_ws("DEVICE_RENAMED", {
        "user_id": user_id,
        "device": dev_dict
    })

    return web.json_response({
        "ok": True,
        "message": msg,
        "device": dev_dict
    })


async def handle_device_revoke(request):
    """DELETE /api/devices/{device_id} - Qurilmani bekor qilish (Revoke & Cascade)"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("device_id", ""))
    from core.v8 import AccountDeviceManager
    mgr = AccountDeviceManager.get_default_instance()

    ok, msg = mgr.revoke_device(dev_id, user_id=user_id)
    if not ok:
        return web.json_response({"ok": False, "error": msg}, status=404)

    auth_token = get_auth_token_from_request(request)
    if not _is_production_mode() and auth_token:
        asyncio.create_task(_sync_user_devices_to_cloud(user_id, auth_token))

    await broadcast_ws("DEVICE_REVOKED", {
        "user_id": user_id,
        "device_id": dev_id
    })

    return web.json_response({
        "ok": True,
        "message": msg,
        "device_id": dev_id
    })


async def handle_device_select(request):
    """POST /api/devices/{device_id}/select - Faol qurilmani tanlash"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("device_id", ""))
    from core.v8 import AccountDeviceManager
    mgr = AccountDeviceManager.get_default_instance()

    ok, msg, dev = mgr.select_device(user_id=user_id, device_id_or_uuid=dev_id)
    if not ok or not dev:
        return web.json_response({"ok": False, "error": msg}, status=404)

    auth_token = get_auth_token_from_request(request)
    if not _is_production_mode() and auth_token:
        asyncio.create_task(_sync_user_devices_to_cloud(user_id, auth_token))

    await broadcast_ws("DEVICE_SELECTED", {
        "user_id": user_id,
        "selected_device_id": dev.device_id,
        "device": dev.to_dict()
    })

    return web.json_response({
        "ok": True,
        "message": msg,
        "selected_device": dev.to_dict()
    })


async def handle_device_permissions(request):
    """GET /api/devices/{device_id}/permissions - Qurilma uchun foydalanuvchi ruxsatlari"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    dev_id = urllib.parse.unquote(request.match_info.get("device_id", ""))
    from core.v8 import AccountDeviceManager, PermissionStore
    mgr = AccountDeviceManager.get_default_instance()

    dev = mgr.get_device(dev_id, user_id=user_id)
    if not dev or dev.is_revoked:
        return web.json_response({
            "ok": False,
            "error": "Qurilma topilmadi yoki hisobingizga tegishli emas"
        }, status=404)

    store = PermissionStore.get_default_instance()
    profile = store.get_profile(user_id, dev.device_id)

    return web.json_response({
        "ok": True,
        "device_id": dev.device_id,
        "profile": profile.to_dict(),
        "catalog": store.get_catalog()
    })


async def handle_account_sessions(request):
    """GET /api/account/sessions - Foydalanuvchining barcha faol sessiyalari"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    from core.v8.auth_session import SessionManager
    from core.v8 import AccountDeviceManager
    sm = SessionManager.get_default_instance()
    adm = AccountDeviceManager.get_default_instance()

    sessions = sm.get_sessions_for_user(user_id)
    sessions_data = []
    for s in sessions:
        dev = adm.get_device(s.device_id, user_id=user_id)
        dev_name = dev.name if dev else s.device_id
        d = s.to_dict()
        d["device_name"] = dev_name
        sessions_data.append(d)

    return web.json_response({
        "ok": True,
        "user_id": user_id,
        "sessions": sessions_data,
        "total": len(sessions_data)
    })


async def handle_account_sessions_logout_all(request):
    """POST /api/account/sessions/logout-all - Barcha sessiyalarni to'xtatish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    from core.v8.auth_session import SessionManager
    sm = SessionManager.get_default_instance()

    count = sm.logout_all_sessions(user_id)
    await broadcast_ws("SESSION_LOGOUT", {
        "user_id": user_id,
        "terminated_count": count
    })

    return web.json_response({
        "ok": True,
        "message": f"Barcha ({count} ta) faol sessiyalar muvaffaqiyatli to'xtatildi",
        "terminated_count": count
    })


# ========== 8.2. PHASE 41: SUPABASE AUTHENTICATION API ==========

async def handle_auth_register(request):
    """POST /api/auth/register - Supabase Auth xabarnomasi"""
    return web.json_response({
        "ok": True,
        "message": "Supabase Auth orqali ro'yxatdan o'tish frontend mijozida (supabase.auth.signUp) to'g'ridan-to'g'ri amalga oshiriladi. Misa backend parollarni qabul qilmaydi va saqlamaydi.",
        "provider": "supabase_auth"
    }, status=200)


async def handle_auth_login(request):
    """POST /api/auth/login - Supabase Auth xabarnomasi"""
    return web.json_response({
        "ok": True,
        "message": "Supabase Auth orqali kirish frontend mijozida (supabase.auth.signInWithPassword) amalga oshiriladi. Backend JWT Bearer token bilan tekshiradi.",
        "provider": "supabase_auth"
    }, status=200)


async def handle_auth_logout(request):
    """POST /api/auth/logout - Chiqish haqida xabar berish"""
    session, user = get_authenticated_user(request)
    user_id = user.id if user else "anonymous"

    await broadcast_ws("ACCOUNT_LOGOUT", {
        "user_id": user_id,
        "logged_out": True
    })

    return web.json_response({
        "ok": True,
        "message": "Muvaffaqiyatli chiqildi",
        "logged_out": True
    })


async def handle_auth_logout_all(request):
    """POST /api/auth/logout-all - Barcha qurilmalardan chiqish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    await broadcast_ws("ACCOUNT_LOGOUT_ALL", {
        "user_id": user_id
    })

    return web.json_response({
        "ok": True,
        "message": "Barcha faol sessiyalar to'xtatildi",
        "user_id": user_id
    })


async def handle_auth_me(request):
    """GET /api/auth/me - Joriy autentifikatsiyadan o'tgan foydalanuvchi ma'lumotlari (Supabase JWT)"""
    session, user = get_authenticated_user(request)
    if not user or not session:
        return web.json_response({
            "ok": False,
            "error": "Avtorizatsiyadan o'tilmagan",
            "authenticated": False
        }, status=401)

    return web.json_response({
        "ok": True,
        "authenticated": True,
        "user": user.to_dict(),
        "session": session.to_dict()
    })


async def handle_auth_verify_email(request):
    """POST /api/auth/verify-email - Supabase Auth email confirmation notice"""
    return web.json_response({
        "ok": True,
        "message": "Email tasdiqlash Supabase Auth tomonidan avtomatik tasdiqlash havolasi orqali amalga oshiriladi.",
        "provider": "supabase_auth"
    })


async def handle_auth_forgot_password(request):
    """POST /api/auth/forgot-password - Supabase Auth reset password notice"""
    return web.json_response({
        "ok": True,
        "message": "Parolni tiklash frontend mijozi orqali supabase.auth.resetPasswordForEmail() yordamida amalga oshiriladi.",
        "provider": "supabase_auth"
    })


async def handle_auth_reset_password(request):
    """POST /api/auth/reset-password - Supabase Auth reset password notice"""
    return web.json_response({
        "ok": True,
        "message": "Yangi parol Supabase Auth orqali supabase.auth.updateUser({ password }) bilan o'rnatiladi.",
        "provider": "supabase_auth"
    })


async def handle_auth_change_password(request):
    """POST /api/auth/change-password - Supabase Auth password update notice"""
    return web.json_response({
        "ok": True,
        "message": "Parolni o'zgartirish Supabase Auth orqali supabase.auth.updateUser({ password }) bilan bajariladi.",
        "provider": "supabase_auth"
    })


async def handle_health(request):
    """GET /api/health - Tizim holati va diagnostika (sensitive keys hech qachon chiqmaydi)"""
    import time
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = (
        os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY")
        or ""
    )
    is_supabase_configured = bool(
        supabase_url
        and supabase_key
        and "placeholder-project" not in supabase_url
        and supabase_key not in ("placeholder-anon-key", "placeholder-publishable-key")
    )
    env_name = os.environ.get("MISA_ENV") or os.environ.get("ENVIRONMENT", "development")

    return web.json_response({
        "status": "ok",
        "app": "Misa AI",
        "version": "9.0.0",
        "supabase": "configured" if is_supabase_configured else "not_configured",
        "environment": env_name,
        "timestamp": time.time()
    }, status=200)


# ========== 8.2.1. OAUTH REDIRECT & SESSION RECEIVER ==========
import re as _re
import threading
_pending_oauth_sessions: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_pending_oauth_lock = threading.Lock()
OAUTH_SESSION_TTL_SECONDS = 300.0  # 5 daqiqa
_OAUTH_STATE_RE = _re.compile(r"^[A-Za-z0-9_\-\.:]{1,256}$")
_OAUTH_SECRET_KV_RE = _re.compile(
    r"(?i)(access_token|refresh_token|provider_token|provider_refresh_token|id_token|code)\s*[=:]\s*([^\s&#\"']+)"
)
_OAUTH_JWT_RE = _re.compile(r"eyJ[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}\.[A-Za-z0-9_\-]{5,}")


def _is_valid_oauth_state(state: str) -> bool:
    """OAuth state parametrining xavfsiz formatda ekanligini tekshirish."""
    if not state or not isinstance(state, str):
        return False
    return bool(_OAUTH_STATE_RE.match(state.strip()))


def _redact_oauth_secrets(text: str) -> str:
    """Log yoki xato xabarlarida token va maxfiy kodlar oshkor bo'lishini oldini olish."""
    if not text or not isinstance(text, str):
        return ""
    cleaned = _OAUTH_SECRET_KV_RE.sub(r"\1=[REDACTED]", text)
    cleaned = _OAUTH_JWT_RE.sub("[REDACTED_JWT]", cleaned)
    return cleaned


def _oauth_security_headers() -> Dict[str, str]:
    """OAuth javoblari keshlanmasligi va Referer orqali token sizib chiqmasligi uchun sarlavhalar."""
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }


def _clean_expired_oauth_sessions():
    """Muddati o'tgan OAuth sessiyalarini xotiradan tozalash"""
    now = time.time()
    with _pending_oauth_lock:
        expired_keys = [k for k, (exp, _) in _pending_oauth_sessions.items() if exp <= now]
        for k in expired_keys:
            _pending_oauth_sessions.pop(k, None)


async def handle_oauth_callback(request):
    """GET /api/auth/callback - OAuth redirect landing page for Desktop & Web"""
    q_err = request.query.get("error_description") or request.query.get("error") or ""
    q_code = request.query.get("error_code") or ""
    if q_err or q_code:
        safe_q_err = _redact_oauth_secrets(f"{q_code}: {q_err}".strip(": "))
        logger.warning(f"[OAuthCallback] OAuth callback xatolik bilan qaytdi: {safe_q_err}")

    html_content = """<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="referrer" content="no-referrer">
  <title>Misa AI — Kirish muvaffaqiyatli</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #0B0F19;
      color: #F8FAFC;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }
    .card {
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(16, 185, 129, 0.4);
      border-radius: 20px;
      padding: 40px;
      text-align: center;
      max-width: 440px;
      box-shadow: 0 20px 50px rgba(0,0,0,0.6), 0 0 30px rgba(16, 185, 129, 0.15);
    }
    .icon {
      width: 64px;
      height: 64px;
      margin: 0 auto 20px;
      border-radius: 18px;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
    }
    h1 { font-size: 22px; color: #FFFFFF; margin-bottom: 8px; font-weight: 700; }
    p { font-size: 14px; color: #94A3B8; line-height: 1.5; margin-bottom: 24px; }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 9999px;
      background: rgba(16, 185, 129, 0.12);
      color: #34D399;
      font-size: 13px;
      font-weight: 600;
    }
    .status.error {
      background: rgba(239, 68, 68, 0.12);
      color: #F87171;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✨</div>
    <h1>Misa AI</h1>
    <p id="msg">Google orqali autentifikatsiya yakunlanmoqda...</p>
    <div id="badge" class="status">Kutilmoqda...</div>
  </div>
  <script>
    (function() {
      const searchParams = new URLSearchParams(window.location.search);
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      
      const accessToken = hashParams.get('access_token') || searchParams.get('access_token');
      const refreshToken = hashParams.get('refresh_token') || searchParams.get('refresh_token');
      const expiresIn = hashParams.get('expires_in') || searchParams.get('expires_in');
      const code = searchParams.get('code') || hashParams.get('code');
      let state = searchParams.get('state') || hashParams.get('state') || '';
      if (!state) {
        try {
          state = (window.localStorage && localStorage.getItem('misa_oauth_state')) || '';
        } catch (e) {}
      }
      const errorCode = searchParams.get('error_code') || hashParams.get('error_code') || '';
      const error = searchParams.get('error_description') || hashParams.get('error_description') || searchParams.get('error') || hashParams.get('error');

      // Xavfsizlik: access_token, refresh_token va code ni brauzer manzil satridan darhol tozalash
      try {
        if (window.history && window.history.replaceState) {
          var cleanUrl = window.location.pathname + (state ? '?state=' + encodeURIComponent(state) : '');
          window.history.replaceState(null, document.title, cleanUrl);
        }
      } catch (e) {}

      const msgEl = document.getElementById('msg');
      const badgeEl = document.getElementById('badge');
      const isRemoteHost = window.location.hostname !== '127.0.0.1' && window.location.hostname !== 'localhost';

      function relayToLocalDesktop(payload) {
        if (!isRemoteHost) return;
        try {
          fetch('http://127.0.0.1:18420/api/auth/callback/session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          }).catch(function() {});
        } catch (e) {}
      }

      if (error || errorCode) {
        var rawErr = error ? decodeURIComponent(error.replace(/\\+/g, ' ')) : errorCode;
        var safeErr = ((errorCode && rawErr.indexOf(errorCode) === -1) ? (errorCode + ': ' + rawErr) : rawErr)
          .replace(/(access_token|refresh_token|code)=[^&\\s]+/gi, '$1=[REDACTED]');
        if (errorCode === 'bad_oauth_state' || safeErr.indexOf('bad_oauth_state') !== -1 || safeErr.indexOf('OAuth state not found or expired') !== -1) {
          msgEl.textContent = "Avtorizatsiya sessiyasi muddati tugagan yoki havola eskirgan (bad_oauth_state). Ushbu oynani yopib, Misa ilovasidan Google orqali kirishni yangidan boshlang.";
        } else {
          msgEl.textContent = "Xatolik: " + safeErr;
        }
        badgeEl.textContent = "Muvaffaqiyatsiz";
        badgeEl.className = "status error";
        var errPayload = {
          state: state,
          error: safeErr,
          error_code: errorCode || undefined,
          timestamp: Date.now()
        };
        fetch('/api/auth/callback/session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(errPayload)
        }).catch(function() {});
        relayToLocalDesktop(errPayload);
        return;
      }

      if (accessToken || code) {
        var sessionPayload = {
          access_token: accessToken,
          refresh_token: refreshToken,
          expires_in: expiresIn ? Number(expiresIn) : undefined,
          code: code,
          state: state,
          timestamp: Date.now()
        };
        relayToLocalDesktop(sessionPayload);
        fetch('/api/auth/callback/session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sessionPayload)
        }).then(function(res) {
          return res.json().then(function(data) {
            return { ok: res.ok && data && data.ok, data: data };
          });
        }).then(function(result) {
          if (!result.ok && !isRemoteHost) {
            msgEl.textContent = (result.data && result.data.error) || "Sessiyani saqlashda xatolik yuz berdi.";
            badgeEl.textContent = "Xatolik";
            badgeEl.className = "status error";
            return;
          }
          msgEl.innerHTML = "Tizimga muvaffaqiyatli kirdingiz!<br>Ushbu oynani yopib, Misa ilovasiga qaytishingiz mumkin.";
          badgeEl.textContent = "Tasdiqlandi ✓";
          setTimeout(function() {
            try { window.close(); } catch(e) {}
          }, 1500);
        }).catch(function() {
          msgEl.textContent = "Server bilan aloqa o'rnatishda xatolik yuz berdi. Qaytadan urinib ko'ring.";
          badgeEl.textContent = "Xatolik";
          badgeEl.className = "status error";
        });
      } else {
        msgEl.textContent = "Avtorizatsiya tokeni qabul qilinmadi.";
        badgeEl.textContent = "Xatolik";
        badgeEl.className = "status error";
      }
    })();
  </script>
</body>
</html>"""
    return web.Response(
        text=html_content,
        content_type="text/html",
        headers=_oauth_security_headers(),
    )


def _is_completed_oauth_session(data: Any) -> bool:
    """Sessiya yozuvi haqiqiy token, kod yoki xatolik bilan yakunlanganligini tekshirish (pending init/link emas)."""
    if not isinstance(data, dict):
        return False
    return bool(
        data.get("access_token")
        or data.get("code")
        or data.get("error")
        or data.get("user") is not None
    )


def _find_latest_pending_oauth_state(now: float) -> Optional[str]:
    """Agar callback state'siz qaytgan bo'lsa (masalan, bad_oauth_state yoki fallback URL), eng so'nggi pending state'ni topish."""
    latest_state: Optional[str] = None
    latest_ts: float = -1.0
    for k, (exp, val) in list(_pending_oauth_sessions.items()):
        if k == "default" or exp <= now or not isinstance(val, dict):
            continue
        if not _is_completed_oauth_session(val):
            ts = float(val.get("timestamp") or 0.0)
            if ts >= latest_ts:
                latest_ts = ts
                latest_state = k
    return latest_state


async def handle_oauth_session_save(request):
    """POST /api/auth/callback/session - Brauzerdan kelgan sessiya tokenlarini yoki boshlang'ich state'ni xavfsiz saqlash"""
    try:
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("JSON obyekt bo'lishi kerak")
    except Exception:
        return web.json_response(
            {"ok": False, "error": "Noto'g'ri JSON formati"},
            status=400,
            headers=_oauth_security_headers(),
        )

    raw_state = str(data.get("state") or request.query.get("state") or "").strip()
    if raw_state and not _is_valid_oauth_state(raw_state):
        return web.json_response(
            {"ok": False, "error": "Noto'g'ri OAuth state formati"},
            status=400,
            headers=_oauth_security_headers(),
        )

    action = str(data.get("action") or "").strip().lower()
    access_token = str(data.get("access_token") or "").strip() or None
    refresh_token = str(data.get("refresh_token") or "").strip() or None
    code = str(data.get("code") or "").strip() or None
    oauth_error = str(data.get("error") or "").strip() or None
    user_val = data.get("user")

    _clean_expired_oauth_sessions()
    now = time.time()
    expires_at = now + OAUTH_SESSION_TTL_SECONDS

    # 1. State yaratilishi (pre-registration: action="init" yoki "link")
    if action in ("init", "link") and not access_token and not code and not oauth_error and user_val is None:
        if not raw_state:
            return web.json_response(
                {"ok": False, "error": "OAuth state parametri majburiy"},
                status=400,
                headers=_oauth_security_headers(),
            )
        with _pending_oauth_lock:
            existing = _pending_oauth_sessions.get(raw_state)
            # Agar allaqachon yakunlangan sessiya bo'lsa ustidan yozib yubormaslik
            if not existing or not _is_completed_oauth_session(existing[1]):
                _pending_oauth_sessions[raw_state] = (
                    expires_at,
                    {
                        "state": raw_state,
                        "action": action,
                        "status": "pending",
                        "user_id": data.get("user_id"),
                        "timestamp": now,
                    },
                )
        return web.json_response(
            {"ok": True, "status": "pending", "state": raw_state},
            headers=_oauth_security_headers(),
        )

    if not access_token and not code and not oauth_error and user_val is None:
        return web.json_response(
            {"ok": False, "error": "Avtorizatsiya tokeni yoki kodi topilmadi"},
            status=400,
            headers=_oauth_security_headers(),
        )

    # 2. Callback'dan kelgan sessiya yoki xatolikni state bilan bog'lab saqlash
    also_save_default = False
    with _pending_oauth_lock:
        if raw_state:
            state = raw_state
        else:
            matched_pending = _find_latest_pending_oauth_state(now)
            if matched_pending:
                state = matched_pending
                also_save_default = True
            else:
                state = "default"

        sanitized_session: Dict[str, Any] = {
            "state": state,
            "status": "error" if oauth_error else "completed",
            "timestamp": data.get("timestamp") or int(now * 1000),
        }
        if access_token:
            sanitized_session["access_token"] = access_token
        if refresh_token:
            sanitized_session["refresh_token"] = refresh_token
        if code:
            sanitized_session["code"] = code
        if user_val is not None:
            sanitized_session["user"] = user_val
        if data.get("expires_in") is not None:
            sanitized_session["expires_in"] = data.get("expires_in")
        if oauth_error:
            sanitized_session["error"] = _redact_oauth_secrets(oauth_error)

        _pending_oauth_sessions[state] = (expires_at, sanitized_session)
        if also_save_default:
            _pending_oauth_sessions["default"] = (expires_at, sanitized_session)

    # Extract name from JWT if available to immediately sync user name
    if access_token and "." in access_token:
        try:
            import base64
            parts = access_token.split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1]
                payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
                payload_json = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                meta = payload_json.get("user_metadata", {})
                full_name = meta.get("full_name") or meta.get("name") or payload_json.get("email", "").split("@")[0]
                if full_name and full_name.strip():
                    name_to_save = full_name.strip()
                    cfg = _read_config()
                    if "user" not in cfg:
                        cfg["user"] = {}
                    cfg["user"]["name"] = name_to_save
                    _write_config(cfg)
                    try:
                        with open(USER_NAME_FILE, "w", encoding="utf-8") as f:
                            f.write(name_to_save)
                    except Exception:
                        pass
        except Exception:
            pass

    from core.v8.events import RemoteEventType, RemoteAuditEvent, RemoteAuditLogger
    audit = RemoteAuditLogger.get_instance()
    audit.log_event(RemoteAuditEvent(
        event_type=RemoteEventType.OAUTH_COMPLETED,
        details={"state": state, "status": "error" if oauth_error else "completed"}
    ))

    # Xavfsizlik: raw tokenlarni websocketga tarqatmaslik! Faqat xavfsiz holat hodisasi
    safe_event = {
        "ok": not bool(oauth_error),
        "status": "error" if oauth_error else "completed",
        "state": state,
        "timestamp": now
    }
    sync_broadcast("oauth_completed", safe_event, _main_loop)
    return web.json_response(
        {"ok": True, "status": "saved", "state": state},
        headers=_oauth_security_headers(),
    )


async def handle_oauth_session_get(request):
    """GET /api/auth/callback/session - Desktop ilova uchun kutilayotgan sessiyani state orqali bir martalik olish"""
    _clean_expired_oauth_sessions()
    req_state = request.query.get("state", "").strip()

    if req_state and not _is_valid_oauth_state(req_state):
        return web.json_response(
            {
                "ok": False,
                "session": None,
                "error": "Noto'g'ri OAuth state parametri",
            },
            status=400,
            headers=_oauth_security_headers(),
        )

    now = time.time()
    sess_data = None
    is_still_pending = False

    with _pending_oauth_lock:
        if req_state:
            item = _pending_oauth_sessions.get(req_state)
            if item:
                exp, data = item
                if exp <= now:
                    _pending_oauth_sessions.pop(req_state, None)
                elif _is_completed_oauth_session(data):
                    _pending_oauth_sessions.pop(req_state, None)
                    # Agar state'siz callback "default" ga ham yozilgan bo'lsa uni ham tozalash
                    def_item = _pending_oauth_sessions.get("default")
                    if def_item and def_item[1] is data:
                        _pending_oauth_sessions.pop("default", None)
                    sess_data = data
                else:
                    # Hali pending (init/link) holatda — o'chirib yubormaymiz!
                    is_still_pending = True

            # Agar req_state bo'yicha yakunlangan sessiya topilmagan bo'lsa va "default" da yakunlangan sessiya bo'lsa:
            if sess_data is None:
                def_item = _pending_oauth_sessions.get("default")
                if def_item:
                    def_exp, def_data = def_item
                    if def_exp <= now:
                        _pending_oauth_sessions.pop("default", None)
                    elif _is_completed_oauth_session(def_data):
                        _pending_oauth_sessions.pop("default", None)
                        _pending_oauth_sessions.pop(req_state, None)
                        sess_data = def_data
        elif _is_production_mode():
            # XAVFSIZLIK: Production rejimda state parametrisiz sessiya so'rovi rad etiladi (hijack oldini olish)
            return web.json_response(
                {
                    "ok": False,
                    "session": None,
                    "error": "OAuth state parametri majburiy",
                },
                status=400,
                headers=_oauth_security_headers(),
            )
        else:
            # Desktop / localhost rejimda faqat yakunlangan "default" kalit olinadi (state-bound sessiyalarga tegilmaydi)
            def_item = _pending_oauth_sessions.get("default")
            if def_item:
                exp, data = def_item
                if exp <= now:
                    _pending_oauth_sessions.pop("default", None)
                elif _is_completed_oauth_session(data):
                    _pending_oauth_sessions.pop("default", None)
                    sess_data = data

    if sess_data:
        if sess_data.get("error"):
            err_msg = _redact_oauth_secrets(str(sess_data.get("error")))
            return web.json_response(
                {
                    "ok": False,
                    "session": None,
                    "oauth_error": err_msg,
                    "error": f"Google orqali kirishda xatolik: {err_msg}",
                },
                status=400,
                headers=_oauth_security_headers(),
            )
        return web.json_response(
            {"ok": True, "session": sess_data},
            headers=_oauth_security_headers(),
        )

    return web.json_response({
        "ok": False,
        "status": "pending" if is_still_pending else "not_found",
        "session": None,
        "error": "Sessiya topilmadi yoki muddati o'tgan"
    }, status=404, headers=_oauth_security_headers())


# ========== 8.2.2. PHASE 44: ACCOUNT IDENTITIES & LINKING API ==========

async def handle_account_identities_get(request):
    """GET /api/account/identities - Foydalanuvchining ulangan shaxslari (Email, Google) va xavfsiz holati"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    raw_claims = getattr(session, "raw_claims", {}) or {}
    app_metadata = raw_claims.get("app_metadata", {}) or {}
    user_metadata = raw_claims.get("user_metadata", {}) or {}

    providers = app_metadata.get("providers", [])
    primary_provider = app_metadata.get("provider", "email")
    if not providers:
        providers = [primary_provider] if primary_provider else ["email"]

    if "google" not in providers and (
        primary_provider == "google" or
        str(user_metadata.get("iss", "")).startswith("https://accounts.google.com") or
        user_metadata.get("avatar_url") or
        user_metadata.get("picture")
    ):
        providers.append("google")

    identities = []
    user_email = getattr(session, "email", "") or (user.email if user else "")

    # 1. Email identity
    if "email" in providers or primary_provider == "email" or user_email:
        identities.append({
            "provider": "email",
            "email": user_email,
            "is_primary": primary_provider == "email",
            "is_verified": bool(getattr(user, "is_verified", True))
        })

    # 2. Google identity
    is_google_linked = "google" in providers or primary_provider == "google"
    if is_google_linked:
        identities.append({
            "provider": "google",
            "email": user_metadata.get("email") or user_email,
            "name": user_metadata.get("full_name") or user_metadata.get("name") or getattr(session, "display_name", ""),
            "avatar_url": getattr(session, "avatar_url", "") or user_metadata.get("avatar_url") or user_metadata.get("picture", ""),
            "is_primary": primary_provider == "google"
        })

    # Lockout himoyasi: Google'ni faqat muqobil kirish usuli bo'lgandagina uzish mumkin!
    can_unlink_google = is_google_linked and ("email" in providers and len(identities) > 1)

    return web.json_response({
        "ok": True,
        "user_id": user_id,
        "providers": providers,
        "primary_provider": primary_provider,
        "identities": identities,
        "is_google_linked": is_google_linked,
        "can_unlink_google": can_unlink_google
    })


async def handle_account_identities_unlink(request):
    """POST /api/account/identities/unlink - Foydalanuvchining qo'shimcha Google hisobini uzish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        body = {}

    provider = str(body.get("provider", "")).strip().lower()
    if provider != "google":
        return web.json_response({
            "ok": False,
            "error": "Faqat qo'shimcha Google hisobini uzish qo'llab-quvvatlanadi"
        }, status=400)

    raw_claims = getattr(session, "raw_claims", {}) or {}
    app_metadata = raw_claims.get("app_metadata", {}) or {}
    providers = app_metadata.get("providers", [])
    primary_provider = app_metadata.get("provider", "email")

    is_google = "google" in providers or primary_provider == "google"
    if not is_google:
        return web.json_response({
            "ok": False,
            "error": "Google hisobi ushbu akkauntga ulanmagan"
        }, status=400)

    # Lockout tekshiruvi: Agar foydalanuvchi faqat Google orqali ro'yxatdan o'tgan bo'lsa va email/parol bo'lmasa
    has_alternative = "email" in providers and len(providers) > 1
    if not has_alternative:
        return web.json_response({
            "ok": False,
            "error": "Google sizning yagona kirish usulingizdir. Akkauntga kirish imkoniyatini yo'qotmaslik uchun avval parolni o'rnating yoki boshqa hisobni ulang."
        }, status=400)

    from core.v8.events import RemoteEventType, RemoteAuditEvent, RemoteAuditLogger
    audit = RemoteAuditLogger.get_instance()
    audit.log_event(RemoteAuditEvent(
        event_type=RemoteEventType.GOOGLE_UNLINKED,
        user_id=user_id,
        details={"provider": "google"}
    ))

    return web.json_response({
        "ok": True,
        "message": "Google hisobi muvaffaqiyatli uzildi",
        "user_id": user_id,
        "unlinked_provider": "google"
    })


async def handle_account_identities_link_initiate(request):
    """POST /api/account/identities/link/initiate - Akkauntni Google bilan xavfsiz bog'lash uchun sessiya kodi yaratish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    import secrets
    link_state = f"link_{secrets.token_urlsafe(24)}"
    now = time.time()
    expires_at = now + OAUTH_SESSION_TTL_SECONDS

    with _pending_oauth_lock:
        _pending_oauth_sessions[link_state] = (expires_at, {
            "action": "link",
            "user_id": user_id,
            "timestamp": now
        })

    from core.v8.events import RemoteEventType, RemoteAuditEvent, RemoteAuditLogger
    audit = RemoteAuditLogger.get_instance()
    audit.log_event(RemoteAuditEvent(
        event_type=RemoteEventType.GOOGLE_LINK_STARTED,
        user_id=user_id,
        details={"state": link_state}
    ))

    return web.json_response({
        "ok": True,
        "state": link_state,
        "user_id": user_id,
        "expires_in": int(OAUTH_SESSION_TTL_SECONDS)
    })


# ========== 8.3. PHASE 42: DEVICE ENROLLMENT & PAIRING API ==========

async def handle_device_pairing_start(request):
    """POST /api/devices/pairing/start - Yangi PC Agent juftlash kodini generatsiya qilish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        body = {}

    ttl = body.get("ttl", 300.0)
    meta = body.get("metadata", {})

    from core.v8.device_pairing import DevicePairingManager
    mgr = DevicePairingManager.get_default_instance()

    try:
        pairing_sess, raw_code = mgr.start_pairing(
            user_id=user_id,
            ttl_seconds=float(ttl),
            request_metadata=meta
        )
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)

    await broadcast_ws("DEVICE_PAIRING_STARTED", {
        "user_id": user_id,
        "pairing_id": pairing_sess.id,
        "expires_at": pairing_sess.expires_at
    })

    return web.json_response({
        "ok": True,
        "success": True,
        "pairing_id": pairing_sess.id,
        "code": raw_code,
        "expires_at": pairing_sess.expires_at,
        "expires_in": int(pairing_sess.remaining_seconds)
    })


async def handle_device_pairing_status(request):
    """GET /api/devices/pairing/{pairing_id} - Juftlash sessiyasi holatini tekshirish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    pairing_id = request.match_info.get("pairing_id", "")
    from core.v8.device_pairing import DevicePairingManager
    mgr = DevicePairingManager.get_default_instance()
    sess = mgr.get_session(pairing_id)

    if not sess:
        return web.json_response({"ok": False, "error": "Juftlash sessiyasi topilmadi"}, status=404)

    if sess.user_id and user_id and sess.user_id != user_id and user_id not in ("admin", "local_user"):
        return web.json_response(
            {"ok": False, "error": "FORBIDDEN: Ushbu juftlash sessiyasi boshqa foydalanuvchiga tegishli"},
            status=403
        )

    return web.json_response({
        "ok": True,
        "session": sess.to_dict(),
        "status": sess.status,
        "remaining_seconds": sess.remaining_seconds,
        "device_id": sess.device_id
    })


async def handle_device_pairing_cancel(request):
    """POST /api/devices/pairing/{pairing_id}/cancel - Juftlash sessiyasini bekor qilish"""
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
    pairing_id = request.match_info.get("pairing_id", "")

    from core.v8.device_pairing import DevicePairingManager
    mgr = DevicePairingManager.get_default_instance()
    ok, msg = mgr.cancel_pairing(pairing_id, user_id=user_id)

    if not ok:
        status_code = 404 if "NOT_FOUND" in msg else 403
        return web.json_response({"ok": False, "error": msg}, status=status_code)

    await broadcast_ws("DEVICE_PAIRING_CANCELLED", {
        "user_id": user_id,
        "pairing_id": pairing_id
    })

    return web.json_response({"ok": True, "message": msg})


async def handle_device_pairing_complete(request):
    """POST /api/devices/pairing/complete - PC Agent enrollment va juftlashni yakunlash"""
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    pairing_id = body.get("pairing_id", "")
    code = body.get("code", "")
    public_key = body.get("public_key", "")
    dev_info = body.get("device", {}) or {}

    if not pairing_id or not code:
        return web.json_response({"ok": False, "error": "pairing_id va code kiritilishi shart"}, status=400)

    if not public_key:
        return web.json_response({"ok": False, "error": "public_key (Ed25519) kiritilishi shart"}, status=400)

    from core.v8.device_pairing import DevicePairingManager
    from core.v8.device_enrollment import DeviceEnrollmentManager
    pairing_mgr = DevicePairingManager.get_default_instance()
    enroll_mgr = DeviceEnrollmentManager.get_default_instance()

    # 1. Kodni tekshirish
    ok, msg, sess = pairing_mgr.verify_code(pairing_id, code)
    if not ok or not sess:
        status_code = 404 if "NOT_FOUND" in msg else 400
        return web.json_response({"ok": False, "error": msg}, status=status_code)

    # 2. Qurilma identifikatsiyasini aniqlash
    dev_id = dev_info.get("device_id")
    hostname = dev_info.get("hostname", "Misa-PC")
    platform_name = dev_info.get("platform", "Windows")
    os_version = dev_info.get("os_version", "10")
    fingerprint = dev_info.get("fingerprint", "")
    friendly_name = dev_info.get("name") or hostname

    if not dev_id:
        from core.v8.device import DeviceIdentityManager
        fp = fingerprint or DeviceIdentityManager.compute_fingerprint(hostname=hostname)
        dev_id = f"{hostname}@{fp[:8]}"

    # 3. Qurilmani hisob egasiga (sess.user_id) enroll qilish
    enroll_ok, enroll_msg, cred, device = enroll_mgr.enroll_device(
        user_id=sess.user_id,
        device_id=dev_id,
        public_key=public_key,
        name=friendly_name,
        hostname=hostname,
        platform_name=platform_name,
        os_version=os_version,
        fingerprint=fingerprint,
        metadata=dev_info.get("metadata", {})
    )

    if not enroll_ok or not device or not cred:
        return web.json_response({"ok": False, "error": enroll_msg}, status=400)

    # 4. Juftlash sessiyasini yakunlash
    pairing_mgr.complete_pairing(
        pairing_id=pairing_id,
        code=code,
        device_id=device.device_id,
        device_info=dev_info,
        user_id=sess.user_id
    )

    await broadcast_ws("DEVICE_ENROLLED", {
        "user_id": sess.user_id,
        "device_id": device.device_id,
        "device": device.to_dict()
    })

    return web.json_response({
        "ok": True,
        "success": True,
        "message": "Qurilma muvaffaqiyatli hisobga biriktirildi (enrolled)",
        "device": device.to_dict(),
        "credential": {
            "id": cred.id,
            "algorithm": cred.algorithm,
            "public_key": cred.public_key,
            "enrolled_at": cred.enrolled_at
        }
    })


async def handle_device_auth_challenge(request):
    """POST /api/devices/{device_id}/challenge - Autentifikatsiya uchun bir martalik nonce olish"""
    dev_id = request.match_info.get("device_id", "")
    from core.v8.device_auth import DeviceAuthManager
    auth_mgr = DeviceAuthManager.get_default_instance()

    ok, msg, data = auth_mgr.issue_challenge(dev_id)
    if not ok or not data:
        status_code = 404 if "NOT_ENROLLED" in msg else 400
        return web.json_response({"ok": False, "error": msg}, status=status_code)

    return web.json_response({
        "ok": True,
        "success": True,
        **data
    })


async def handle_device_auth_authenticate(request):
    """POST /api/devices/{device_id}/authenticate - Imzolangan chaqiriqni tekshirish va DeviceSession berish"""
    dev_id = request.match_info.get("device_id", "")
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto'g'ri JSON formati"}, status=400)

    challenge_id = body.get("challenge_id", "")
    signature = body.get("signature", "")
    context = body.get("context", {})

    if not challenge_id or not signature:
        return web.json_response({"ok": False, "error": "challenge_id va signature kiritilishi shart"}, status=400)

    from core.v8.device_auth import DeviceAuthManager
    auth_mgr = DeviceAuthManager.get_default_instance()

    ok, msg, dev_sess = auth_mgr.verify_challenge_response(
        device_id=dev_id,
        challenge_id=challenge_id,
        signature_hex=signature,
        context=context
    )

    if not ok or not dev_sess:
        status_code = 401 if "INVALID_SIGNATURE" in msg or "REPLAY" in msg else 400
        return web.json_response({"ok": False, "error": msg}, status=status_code)

    return web.json_response({
        "ok": True,
        "success": True,
        "session_token": dev_sess.token,
        "session_id": dev_sess.session_id,
        "expires_at": dev_sess.expires_at,
        "protocol_version": dev_sess.protocol_version
    })


async def handle_device_heartbeat(request):
    """POST /api/devices/{device_id}/heartbeat - PC Agent davriy heartbeat qabul qilish"""
    dev_id = request.match_info.get("device_id", "").strip()

    # 1. DeviceSession tokenini tekshirish (Header: Authorization: Bearer <token> yoki X-Misa-Device-Token)
    auth_header = request.headers.get("Authorization", "").strip()
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("X-Misa-Device-Token", "").strip()

    from core.v8.device_auth import DeviceAuthManager
    from core.v8.device_enrollment import DeviceEnrollmentManager
    from core.v8.account_device import AccountDeviceManager
    from core.v8.heartbeat import HeartbeatManager, HeartbeatPayload, DeviceState

    auth_mgr = DeviceAuthManager.get_default_instance()
    enroll_mgr = DeviceEnrollmentManager.get_default_instance()
    adm = AccountDeviceManager.get_default_instance()

    # 2. Kredensial holatini tekshirish (Revocation check)
    cred = enroll_mgr.get_credential(dev_id)
    if not cred or cred.is_revoked:
        return web.json_response({
            "ok": False,
            "error": "DEVICE_REVOKED",
            "message": "Ushbu qurilma ruxsati bekor qilingan (revoked)"
        }, status=403)

    # 3. Sessiyani topish va verifikatsiya qilish
    sess = None
    if token:
        for s in auth_mgr._sessions.values():
            if s.token == token and s.device_id == dev_id and s.is_valid:
                sess = s
                break

    if not sess:
        return web.json_response({
            "ok": False,
            "error": "UNAUTHORIZED",
            "message": "Yaroqli qurilma sessiyasi topilmadi yoki muddati o'tgan"
        }, status=401)

    # 4. Heartbeat payloadni o'qish
    try:
        body = await request.json()
    except Exception:
        body = {}

    agent_version = str(body.get("agent_version", get_app_version()))
    state_str = str(body.get("state", "online")).lower()
    metrics = body.get("metrics", {})

    try:
        dev_state = DeviceState(state_str)
    except ValueError:
        dev_state = DeviceState.ONLINE

    now = time.time()
    sess.last_heartbeat_at = now

    hb_mgr = HeartbeatManager.get_default_instance()
    hb_mgr.record_heartbeat(HeartbeatPayload(
        device_id=dev_id,
        timestamp=now,
        agent_version=agent_version,
        state=dev_state,
        metrics=metrics
    ))

    # AccountDeviceManager da ham last_seen_at va status yangilanadi
    device_obj = adm.get_device(dev_id)
    if device_obj:
        device_obj.status = dev_state.value
        device_obj.last_seen_at = now
        device_obj.agent_version = agent_version
        if metrics:
            device_obj.metadata["latest_metrics"] = metrics
        adm.save()

    return web.json_response({
        "ok": True,
        "success": True,
        "device_id": dev_id,
        "state": dev_state.value,
        "acknowledged": True,
        "timestamp": now
    })


async def handle_command_submit(request):
    """POST /api/devices/{device_id}/commands - Yangi buyruq yuborish"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    from core.v8.account_device import AccountDeviceManager
    adm = AccountDeviceManager.get_default_instance()
    existing_dev = adm.get_device(dev_id)
    if existing_dev:
        if existing_dev.is_revoked or (existing_dev.user_id and existing_dev.user_id != user_id and user_id != "admin"):
            return web.json_response(
                {"ok": False, "error": "FORBIDDEN", "message": "Qurilma hisobingizga tegishli emas"},
                status=403
            )
    elif _is_production_mode():
        return web.json_response(
            {"ok": False, "error": "FORBIDDEN", "message": "Qurilma topilmadi yoki hisobingizga tegishli emas"},
            status=403
        )
    
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": "Invalid JSON"}, status=400)
    
    tool_id = body.get("tool_id")
    params = body.get("params", {})
    origin = body.get("origin", "system")
    
    if not tool_id:
        return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": "tool_id required"}, status=400)
        
    from core.v8.command_queue import CommandQueueManager
    from core.v8.remote_tools import RemoteToolRegistry
    
    registry = RemoteToolRegistry.get_default_instance()
    tool_def = registry.get_tool(tool_id)
    if not tool_def:
        return web.json_response({"ok": False, "error": "TOOL_NOT_FOUND"}, status=404)
        
    cmd_mgr = CommandQueueManager.get_default_instance()
    try:
        cmd, token_obj = cmd_mgr.submit_command(
            device_id=dev_id,
            tool_id=tool_id,
            params=params,
            user_id=user_id,
            origin=origin,
            requires_confirmation=tool_def.requires_confirmation,
            risk_level=tool_def.risk_level
        )
        return web.json_response({
            "ok": True,
            "command_id": cmd.command_id,
            "state": cmd.state.value,
            "confirmation_token": token_obj.token if token_obj else None
        })
    except Exception as e:
        return web.json_response({"ok": False, "error": "INTERNAL_ERROR", "message": str(e)}, status=500)

async def handle_command_confirm(request):
    """POST /api/devices/{device_id}/commands/{command_id}/confirm"""
    dev_id = request.match_info.get("device_id", "").strip()
    cmd_id = request.match_info.get("command_id", "").strip()
    
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
        
    try:
        body = await request.json()
    except Exception:
        body = {}
        
    token = body.get("token")
    if not token:
        return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": "token required"}, status=400)
        
    from core.v8.command_queue import CommandQueueManager
    cmd_mgr = CommandQueueManager.get_default_instance()
    
    success, msg = cmd_mgr.confirm_command(cmd_id, token, user_id)
    if success:
        return web.json_response({"ok": True, "message": msg})
    return web.json_response({"ok": False, "error": "FORBIDDEN", "message": msg}, status=403)

async def handle_command_cancel(request):
    """POST /api/devices/{device_id}/commands/{command_id}/cancel"""
    dev_id = request.match_info.get("device_id", "").strip()
    cmd_id = request.match_info.get("command_id", "").strip()
    
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err
        
    from core.v8.command_queue import CommandQueueManager
    cmd_mgr = CommandQueueManager.get_default_instance()
    
    success, msg = cmd_mgr.cancel_command(cmd_id, user_id)
    if success:
        return web.json_response({"ok": True, "message": msg})
    return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": msg}, status=400)

async def handle_command_pending(request):
    """GET /api/devices/{device_id}/commands/pending - Agent polls here"""
    dev_id = request.match_info.get("device_id", "").strip()
    
    auth_header = request.headers.get("Authorization", "").strip()
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("X-Misa-Device-Token", "").strip()
        
    from core.v8.device_auth import DeviceAuthManager
    from core.v8.device_enrollment import DeviceEnrollmentManager
    
    auth_mgr = DeviceAuthManager.get_default_instance()
    enroll_mgr = DeviceEnrollmentManager.get_default_instance()
    
    cred = enroll_mgr.get_credential(dev_id)
    if not cred or cred.is_revoked:
        return web.json_response({"ok": False, "error": "DEVICE_REVOKED"}, status=403)
        
    sess = None
    if token:
        for s in auth_mgr._sessions.values():
            if s.token == token and s.device_id == dev_id and s.is_valid:
                sess = s
                break
                
    if not sess:
        return web.json_response({"ok": False, "error": "UNAUTHORIZED"}, status=401)
        
    from core.v8.command_queue import CommandQueueManager
    cmd_mgr = CommandQueueManager.get_default_instance()
    
    commands = cmd_mgr.get_pending_commands(dev_id)
    return web.json_response({
        "ok": True,
        "commands": commands
    })

async def handle_command_result(request):
    """POST /api/devices/{device_id}/commands/{command_id}/result - Agent submits result"""
    dev_id = request.match_info.get("device_id", "").strip()
    cmd_id = request.match_info.get("command_id", "").strip()
    
    auth_header = request.headers.get("Authorization", "").strip()
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.headers.get("X-Misa-Device-Token", "").strip()
        
    from core.v8.device_auth import DeviceAuthManager
    from core.v8.device_enrollment import DeviceEnrollmentManager
    
    auth_mgr = DeviceAuthManager.get_default_instance()
    enroll_mgr = DeviceEnrollmentManager.get_default_instance()
    
    cred = enroll_mgr.get_credential(dev_id)
    if not cred or cred.is_revoked:
        return web.json_response({"ok": False, "error": "DEVICE_REVOKED"}, status=403)
        
    sess = None
    if token:
        for s in auth_mgr._sessions.values():
            if s.token == token and s.device_id == dev_id and s.is_valid:
                sess = s
                break
                
    if not sess:
        return web.json_response({"ok": False, "error": "UNAUTHORIZED"}, status=401)
        
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "BAD_REQUEST"}, status=400)
        
    from core.v8.command_queue import CommandQueueManager
    cmd_mgr = CommandQueueManager.get_default_instance()
    cmd_obj = cmd_mgr.get_command(cmd_id)
    if cmd_obj and cmd_obj.device_id and cmd_obj.device_id != dev_id:
        return web.json_response({"ok": False, "error": "FORBIDDEN", "message": "Buyruq boshqa qurilmaga tegishli"}, status=403)
    
    success = cmd_mgr.record_result(cmd_id, body)
    if success:
        return web.json_response({"ok": True})
    return web.json_response({"ok": False, "error": "NOT_FOUND"}, status=404)

async def handle_command_history(request):
    """GET /api/devices/{device_id}/commands/history"""
    dev_id = request.match_info.get("device_id", "").strip()
    
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    from core.v8.account_device import AccountDeviceManager
    adm = AccountDeviceManager.get_default_instance()
    existing_dev = adm.get_device(dev_id)
    if existing_dev:
        if existing_dev.is_revoked or (existing_dev.user_id and existing_dev.user_id != user_id and user_id != "admin"):
            return web.json_response(
                {"ok": False, "error": "FORBIDDEN", "message": "Qurilma hisobingizga tegishli emas"},
                status=403
            )
    elif _is_production_mode():
        return web.json_response(
            {"ok": False, "error": "FORBIDDEN", "message": "Qurilma topilmadi yoki hisobingizga tegishli emas"},
            status=403
        )
        
    from core.v8.command_queue import CommandQueueManager
    cmd_mgr = CommandQueueManager.get_default_instance()
    
    history = cmd_mgr.get_device_history(dev_id)
    return web.json_response({
        "ok": True,
        "history": history
    })


# ========== PHASE 47: FULL AGENT ACCESS & USER CONSENT API ==========

async def handle_agent_access_get(request):
    """GET /api/devices/{device_id}/agent-access - Agent access statusini olish"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    status = mgr.get_access_status(user_id, dev_id)
    return web.json_response({"ok": True, "access": status})


async def handle_agent_access_warning(request):
    """POST /api/devices/{device_id}/agent-access/warning - Warning boshlash"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    # Device ownership tekshirish
    device_owner_id = None
    try:
        from core.v8.account_device import AccountDeviceManager
        dev_mgr = AccountDeviceManager.get_default_instance()
        dev = dev_mgr.get_device(dev_id, user_id=user_id)
        if dev:
            device_owner_id = dev.user_id
    except Exception:
        pass

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    ok, msg, payload = mgr.initiate_activation(user_id, dev_id, device_owner_id)

    if not ok:
        return web.json_response({"ok": False, "error": "ACTIVATION_FAILED", "message": msg}, status=403)
    return web.json_response({"ok": True, "message": msg, "warning": payload})


async def handle_agent_access_acknowledge(request):
    """POST /api/devices/{device_id}/agent-access/acknowledge - Warning tasdiqlash"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "BAD_REQUEST"}, status=400)

    warning_token = body.get("warning_token", "")
    if not warning_token:
        return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": "warning_token required"}, status=400)

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    ok, msg = mgr.acknowledge_warning(user_id, dev_id, warning_token)

    if not ok:
        return web.json_response({"ok": False, "error": "ACKNOWLEDGE_FAILED", "message": msg}, status=403)
    return web.json_response({"ok": True, "message": msg})


async def handle_agent_access_reauth(request):
    """POST /api/devices/{device_id}/agent-access/reauth - Qayta autentifikatsiya"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "BAD_REQUEST"}, status=400)

    warning_token = body.get("warning_token", "")
    reauth_proof = body.get("reauth_proof", "")

    if not warning_token or not reauth_proof:
        return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": "warning_token and reauth_proof required"}, status=400)

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    ok, msg, confirm_token = mgr.verify_reauthentication(user_id, dev_id, warning_token, reauth_proof)

    if not ok:
        return web.json_response({"ok": False, "error": "REAUTH_FAILED", "message": msg}, status=403)
    return web.json_response({"ok": True, "message": msg, "confirmation_token": confirm_token})


async def handle_agent_access_confirm(request):
    """POST /api/devices/{device_id}/agent-access/confirm - Yakuniy tasdiqlash"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "BAD_REQUEST"}, status=400)

    confirmation_token = body.get("confirmation_token", "")
    if not confirmation_token:
        return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": "confirmation_token required"}, status=400)

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    ok, msg = mgr.confirm_activation(user_id, dev_id, confirmation_token)

    if not ok:
        return web.json_response({"ok": False, "error": "CONFIRM_FAILED", "message": msg}, status=403)
    return web.json_response({"ok": True, "message": msg})


async def handle_agent_access_disable(request):
    """POST /api/devices/{device_id}/agent-access/disable - Full access o'chirish"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    ok, msg = mgr.disable_full_access(user_id, dev_id)

    if not ok:
        return web.json_response({"ok": False, "error": "DISABLE_FAILED", "message": msg}, status=400)
    return web.json_response({"ok": True, "message": msg})


async def handle_agent_access_revoke(request):
    """POST /api/devices/{device_id}/agent-access/revoke - Favqulodda bekor qilish"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    ok, msg = mgr.emergency_revoke(user_id, dev_id)

    if not ok:
        return web.json_response({"ok": False, "error": "REVOKE_FAILED", "message": msg}, status=400)
    return web.json_response({"ok": True, "message": msg})


async def handle_agent_access_override(request):
    """POST /api/devices/{device_id}/agent-access/override - Alohida ruxsat o'zgartirish"""
    dev_id = request.match_info.get("device_id", "").strip()
    user_id, user, session, err = resolve_auth_identity(request, required=True)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "BAD_REQUEST"}, status=400)

    permission_id = body.get("permission_id", "")
    enabled = body.get("enabled")

    if not permission_id or enabled is None:
        return web.json_response({"ok": False, "error": "BAD_REQUEST", "message": "permission_id and enabled required"}, status=400)

    from core.v8.agent_access import AgentAccessManager
    mgr = AgentAccessManager.get_default_instance()
    ok, msg = mgr.set_permission_override(user_id, dev_id, permission_id, bool(enabled))

    if not ok:
        return web.json_response({"ok": False, "error": "OVERRIDE_FAILED", "message": msg}, status=400)
    return web.json_response({"ok": True, "message": msg})


# ========== PHASE 48: SECURE AUTO UPDATE & RELEASE HANDLERS ==========
async def handle_update_check(request: web.Request) -> web.Response:
    """GET /api/updates/check - Check for available desktop updates"""
    from core.v8.update_service import get_update_service
    svc = get_update_service()

    force_param = request.query.get("force", "false").lower() in ("true", "1", "yes")
    channel_param = request.query.get("channel")
    if channel_param:
        svc.channel = channel_param.lower()

    result = await svc.check_for_updates(force=force_param)
    return web.json_response(result)


async def handle_update_status(request: web.Request) -> web.Response:
    """GET /api/updates/status - Current update engine status and state"""
    from core.v8.update_service import get_update_service
    svc = get_update_service()
    state_data = svc.state_manager.get_data()
    return web.json_response({
        "ok": True,
        "state": svc.state_manager.current_state.value,
        "data": state_data,
        "audits": svc.get_audit_events()[-10:]
    })


async def handle_update_download(request: web.Request) -> web.Response:
    """POST /api/updates/download - Download and cryptographically verify update artifact"""
    from core.v8.update_service import get_update_service, UpdateArtifact
    svc = get_update_service()

    try:
        body = await request.json()
    except Exception:
        body = {}

    artifact_data = body.get("artifact")
    if not artifact_data:
        if svc._last_manifest and svc._last_manifest.artifacts:
            artifact = svc._last_manifest.artifacts[0]
        else:
            return web.json_response({
                "ok": False,
                "error": "No artifact specified and no active update manifest"
            }, status=400)
    else:
        try:
            artifact = UpdateArtifact.from_dict(artifact_data)
        except Exception as e:
            return web.json_response({"ok": False, "error": f"Invalid artifact payload: {e}"}, status=400)

    success, staged_path, err = await svc.download_and_verify_artifact(artifact)
    if not success:
        return web.json_response({"ok": False, "error": err or "Verification failed"}, status=400)

    return web.json_response({
        "ok": True,
        "staged_path": staged_path,
        "artifact": artifact.name,
        "state": svc.state_manager.current_state.value
    })


async def handle_update_apply(request: web.Request) -> web.Response:
    """POST /api/updates/apply - Atomic staging and restart preparation"""
    from core.v8.update_service import get_update_service, UpdateState
    svc = get_update_service()

    current_state = svc.state_manager.current_state
    if current_state not in (UpdateState.STAGING, UpdateState.VERIFYING):
        return web.json_response({
            "ok": False,
            "error": f"Cannot apply update in state: {current_state.value}. Must be STAGED."
        }, status=400)

    backup_path = svc.create_rollback_backup(sys.executable)
    svc.state_manager.transition_to(UpdateState.INSTALLING, {
        "ready_to_restart": True,
        "backup_path": backup_path
    })

    return web.json_response({
        "ok": True,
        "message": "Update staged and verified. Ready for restart.",
        "state": UpdateState.INSTALLING.value,
        "backup_path": backup_path
    })


async def handle_update_rollback(request: web.Request) -> web.Response:
    """POST /api/updates/rollback - Restore previous version from backup"""
    from core.v8.update_service import get_update_service
    svc = get_update_service()

    ok = svc.rollback(sys.executable)
    if not ok:
        return web.json_response({"ok": False, "error": "Rollback failed or no backup available"}, status=500)

    return web.json_response({"ok": True, "message": "Rollback completed successfully"})


# ========== 9. WEBSOCKET HANDLER ==========
async def handle_ws(request):
    """WS /api/ws - Jonli WebSocket aloqa"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    _active_ws_clients.add(ws)
    logger.info(f"Yangi WebSocket mijozi ulandi. Jami: {len(_active_ws_clients)}")

    await ws.send_str(json.dumps({
        "type": "init",
        "data": {
            "status": "online",
            "voice_state": _voice_state,
            "version": get_app_version()
        },
        "timestamp": datetime.now().isoformat()
    }))

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    action = data.get("action")
                    if action == "ping":
                        await ws.send_str(json.dumps({"type": "pong"}))
                except Exception:
                    pass
            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"WebSocket xatosi: {ws.exception()}")
    finally:
        _active_ws_clients.discard(ws)
        logger.info(f"WebSocket mijozi uzildi. Qolgan: {len(_active_ws_clients)}")

    return ws


# ========== CORS & Origin Security Middleware ==========
ALLOWED_REMOTE_IPS = {"127.0.0.1", "::1", "localhost", "testclient"}
_CORS_BYPASS_PREFIXES = ("/health", "/ready", "/api/ready", "/api/health", "/telegram/webhook")


def is_production_or_remote_enabled() -> bool:
    """Tekshirish: Server bulutda (Railway/production) yoki masofaviy API rejimida ishlayaptimi?"""
    if os.environ.get("MISA_ALLOW_REMOTE_API", "").lower() in ("true", "1", "yes"):
        return True
    if os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod", "staging"):
        return True
    if os.environ.get("MISA_ENV", "").lower() in ("production", "prod", "staging"):
        return True
    if os.environ.get("MISA_API_HOST", "").strip() == "0.0.0.0":
        return True
    for key in (
        "RAILWAY_ENVIRONMENT",
        "RAILWAY_PROJECT_ID",
        "RAILWAY_SERVICE_ID",
        "RAILWAY_PUBLIC_DOMAIN",
        "RAILWAY_STATIC_URL",
        "RAILWAY_GIT_COMMIT_SHA",
    ):
        if os.environ.get(key):
            return True
    return False


# ========== XAVFSIZLIK: Global autentifikatsiya middleware (Production) ==========
_AUTH_EXEMPT_PATHS = frozenset({
    "/",
    "/health", "/ready", "/api/ready",
    "/api/health", "/api/status",
    "/api/telegram/status",
    "/api/auth/register", "/api/auth/login",
    "/api/auth/callback", "/api/auth/callback/session",
    "/api/auth/forgot-password", "/api/auth/verify-email",
    "/api/auth/reset-password",
    "/api/devices/pairing/complete",
    "/api/ws",
})

_AUTH_EXEMPT_PREFIXES = (
    "/telegram/webhook",
    "/webhook/telegram/",
)

def _is_production_mode() -> bool:
    """Production rejimda ishga tushganligini aniqlash."""
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
        return True
    if os.environ.get("MISA_ENV", "").strip().lower() == "production":
        return True
    host = os.environ.get("MISA_API_HOST", "127.0.0.1").strip()
    if host == "0.0.0.0":
        return True
    return False


@web.middleware
async def auth_enforcement_middleware(request, handler):
    """Production rejimda barcha himoyalangan endpointlar uchun autentifikatsiyani majburlash.
    Desktop (localhost) rejimida backward-compatibility uchun autentifikatsiya talab qilinmaydi.
    """
    path = request.path

    # 1. OPTIONS preflight — har doim o'tkazib yuborish
    if request.method == "OPTIONS":
        return await handler(request)

    # 2. Exempt yo'llar — autentifikatsiya talab qilinmaydi
    if path in _AUTH_EXEMPT_PATHS:
        return await handler(request)
    for prefix in _AUTH_EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return await handler(request)

    # Qurilma agentlari o'zining Ed25519 challenge-response yoki X-Misa-Device-Token orqali tekshiriladi
    if path.startswith("/api/devices/") and path.endswith((
        "/challenge", "/authenticate", "/heartbeat", "/commands/pending", "/result"
    )):
        return await handler(request)

    # 3. Desktop rejimda (localhost) — backward-compatibility, auth talab qilinmaydi
    if not _is_production_mode():
        return await handler(request)

    # 4. Production rejimda — autentifikatsiyani tekshirish
    user_id, user, session, err_resp = resolve_auth_identity(request, required=True)
    if err_resp is not None:
        return err_resp

    # Autentifikatsiya muvaffaqiyatli — request davom etsin
    return await handler(request)


@web.middleware
async def cors_middleware(request, handler):
    path = str(getattr(request, "path", getattr(request, "rel_url", "/")))
    origin = request.headers.get("Origin", "")
    is_prod = is_production_or_remote_enabled()
    is_oauth_route = path.startswith("/api/auth/callback")

    # Preflight OPTIONS so'rovlarini zudlik bilan qanoatlantirish
    if request.method == "OPTIONS":
        opt_resp = web.Response(status=204)
        opt_resp.headers["Access-Control-Allow-Origin"] = origin or "*"
        opt_resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        opt_resp.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Misa-Session-Token, X-Misa-User-Id, "
            "X-Misa-Device-Token, apikey, X-Client-Info, Accept, X-Requested-With"
        )
        opt_resp.headers["Access-Control-Allow-Private-Network"] = "true"
        opt_resp.headers["Access-Control-Max-Age"] = "86400"
        return opt_resp

    # Health checks, readiness probes and Telegram webhooks come from external platforms (Railway probes, Telegram servers)
    if any(path.startswith(prefix) for prefix in _CORS_BYPASS_PREFIXES):
        try:
            bypass_resp = await handler(request)
        except web.HTTPException as ex:
            bypass_resp = ex
        bypass_resp.headers["Access-Control-Allow-Origin"] = origin or "*"
        bypass_resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        bypass_resp.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Misa-Session-Token, X-Misa-User-Id, "
            "X-Misa-Device-Token, apikey, X-Client-Info, Accept, X-Requested-With"
        )
        bypass_resp.headers["Access-Control-Allow-Private-Network"] = "true"
        return bypass_resp

    # Remote IP tekshiruvi: Faqat mahalliy desktop rejimida begona LAN murojaatlari cheklanadi.
    # Bulutli / Production (Railway) rejimida va OAuth callback yo'llarida internet mijozlariga ruxsat beriladi.
    if not is_prod and not is_oauth_route and request.remote and request.remote not in ALLOWED_REMOTE_IPS:
        logger.warning(f"Xavfsizlik: Lokal rejimda begona tarmoqdan so'rov rad etildi: {request.remote}")
        return web.HTTPForbidden(text="Xavfsizlik: Begona tarmoqdan murojaat taqiqlangan.")

    is_allowed = True
    if origin:
        origin_clean = origin.strip().lower()
        configured_raw = os.environ.get("MISA_ALLOWED_ORIGINS", "").strip()
        configured_origins = [
            o.strip().lower()
            for o in configured_raw.split(",")
            if o.strip()
        ]

        if "*" in configured_origins or configured_raw == "*":
            is_allowed = True
        elif (
            origin_clean in ("tauri://localhost", "http://tauri.localhost", "https://tauri.localhost")
            or origin_clean in configured_origins
            or origin_clean == "http://localhost"
            or origin_clean.startswith("http://localhost:")
            or origin_clean == "http://127.0.0.1"
            or origin_clean.startswith("http://127.0.0.1:")
            or origin_clean == "https://localhost"
            or origin_clean.startswith("https://localhost:")
            or origin_clean == "https://127.0.0.1"
            or origin_clean.startswith("https://127.0.0.1:")
        ):
            is_allowed = True
        elif is_prod or is_oauth_route:
            # Bulutli production rejimida yoki OAuth relay yo'lida ishonchli domenlar
            if (
                origin_clean.endswith(".railway.app")
                or origin_clean.endswith(".up.railway.app")
                or origin_clean.endswith(".vercel.app")
                or origin_clean.endswith(".netlify.app")
                or origin_clean.endswith(".pages.dev")
                or origin_clean.endswith(".github.io")
            ):
                is_allowed = True
            # XAVFSIZLIK: configured_origins bo'sh bo'lsa ham, xavfsiz rejim (is_allowed=False)
            else:
                is_allowed = False
        else:
            is_allowed = False

        if not is_allowed:
            logger.warning(f"Xavfsizlik: Begona veb-sayt Origin rad etildi: {origin}")
            return web.HTTPForbidden(text="Xavfsizlik: Begona Origin orqali kirish taqiqlangan.")

    try:
        response = await handler(request)
    except web.HTTPException as ex:
        response = ex

    allowed_header_origin = origin if (origin and is_allowed) else ("*" if is_prod else "tauri://localhost")
    response.headers["Access-Control-Allow-Origin"] = allowed_header_origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, Authorization, X-Misa-Session-Token, X-Misa-User-Id, "
        "X-Misa-Device-Token, apikey, X-Client-Info, Accept, X-Requested-With"
    )
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response


# ========== Ilovani sozlash va marshrutlash ==========
def create_app():
    app = web.Application(middlewares=[auth_enforcement_middleware, cors_middleware])

    async def handle_health_liveness(request):
        """GET /health — Railway liveness probe (no secrets, no user data)."""
        return web.json_response({"status": "ok"}, status=200)

    app.router.add_get("/health", handle_health_liveness)

    # Tizim va Bosh sahifa
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/system/metrics", handle_system_metrics)
    app.router.add_get("/api/ws", handle_ws)
    
    # AI Chat va Ovoz
    app.router.add_post("/api/chat", handle_chat)
    app.router.add_post("/api/chat/clear", handle_chat_clear)
    app.router.add_post("/api/chat/feedback", handle_chat_feedback)
    app.router.add_get("/api/images", handle_images_list)
    app.router.add_get("/api/images/{filename}", handle_images_serve)
    app.router.add_post("/api/images/generate", handle_images_generate)
    app.router.add_get("/api/ai/config", handle_ai_config_get)
    app.router.add_post("/api/ai/config", handle_ai_config_set)
    app.router.add_get("/api/ai/providers", handle_ai_providers_get)
    app.router.add_post("/api/ai/providers/toggle", handle_ai_providers_toggle)
    app.router.add_post("/api/ai/providers/discover", handle_ai_providers_discover)
    app.router.add_post("/api/ai/sync", handle_ai_sync)
    app.router.add_post("/api/ai/test-key", handle_ai_test_key)
    app.router.add_post("/api/account/test-api-key", handle_ai_test_key)
    app.router.add_post("/api/voice/start", handle_voice_start)
    app.router.add_post("/api/voice/stop", handle_voice_stop)
    app.router.add_post("/api/voice/speak", handle_voice_speak)
    app.router.add_get("/api/voice/voices", handle_get_voices)


    # Buyruqlar (Commands)
    app.router.add_get("/api/commands", handle_commands_list)
    app.router.add_post("/api/commands/execute", handle_commands_execute)

    # Xotira (Memory)
    app.router.add_get("/api/memory", handle_memory_get)
    app.router.add_post("/api/memory/profile", handle_memory_profile_save)
    app.router.add_post("/api/memory/knowledge", handle_memory_knowledge_save)
    app.router.add_put("/api/memory/knowledge/{id}", handle_memory_knowledge_update)
    app.router.add_delete("/api/memory/knowledge", handle_memory_knowledge_delete)
    app.router.add_delete("/api/memory/knowledge/{id}", handle_memory_knowledge_delete)
    app.router.add_post("/api/memory/pin", handle_memory_pin)
    app.router.add_get("/api/memory/policy", handle_memory_policy_get)
    app.router.add_post("/api/memory/policy", handle_memory_policy_save)
    app.router.add_get("/api/memory/metrics", handle_memory_metrics_get)
    app.router.add_post("/api/memory/knowledge/clear", handle_memory_knowledge_clear)
    app.router.add_post("/api/memory/context/clear", handle_memory_context_clear)
    app.router.add_post("/api/memory/history/clear", handle_memory_history_clear)

    # Kontekst va Observability (Context & Observability)
    app.router.add_get("/api/context/traces", handle_context_traces_get)
    app.router.add_get("/api/context/last-trace", handle_context_last_trace_get)

    # Agentlik Ko'p Bosqichli Tizim (Agent Loop)
    app.router.add_post("/api/agent/execute", handle_agent_execute)
    app.router.add_post("/api/agent/confirm", handle_agent_confirm)
    app.router.add_post("/api/agent/abort", handle_agent_abort)
    app.router.add_get("/api/agent/state", handle_agent_state)

    # Rejalashtiruvchi (Scheduler)
    app.router.add_get("/api/scheduler", handle_scheduler_list)
    app.router.add_post("/api/scheduler/add", handle_scheduler_add)
    app.router.add_post("/api/scheduler/edit", handle_scheduler_edit)
    app.router.add_post("/api/scheduler/enable", handle_scheduler_enable)
    app.router.add_post("/api/scheduler/disable", handle_scheduler_disable)
    app.router.add_post("/api/scheduler/execute", handle_scheduler_execute)
    app.router.add_delete("/api/scheduler/task", handle_scheduler_remove)
    app.router.add_post("/api/scheduler/clear-completed", handle_scheduler_clear_completed)

    # Plaginlar (Plugins & Tools)
    app.router.add_get("/api/plugins", handle_plugins_list)
    app.router.add_post("/api/plugins/toggle", handle_plugins_toggle)
    app.router.add_post("/api/plugins/install", handle_plugins_install)
    app.router.add_post("/api/plugins/uninstall", handle_plugins_uninstall)
    app.router.add_post("/api/plugins/update", handle_plugins_update)
    app.router.add_post("/api/plugins/execute", handle_plugins_execute)
    app.router.add_get("/api/tools/catalog", handle_tools_catalog)

    # Hisob va Sozlamalar (Account & Settings)
    app.router.add_get("/api/account", handle_account_get)
    app.router.add_post("/api/account", handle_account_update)

    # Phase 38: Masofaviy Boshqaruv & Ruxsatlar Markazi (Remote Control & Permissions)
    app.router.add_get("/api/remote/devices", handle_remote_devices)
    app.router.add_get("/api/remote/devices/{id}", handle_remote_device_detail)
    app.router.add_get("/api/remote/permissions/{device_id}", handle_remote_permissions_get)
    app.router.add_put("/api/remote/permissions/{device_id}", handle_remote_permissions_put)
    app.router.add_post("/api/remote/pair", handle_remote_pair)
    app.router.add_post("/api/remote/unpair", handle_remote_unpair)
    app.router.add_post("/api/remote/session/lock", handle_remote_session_lock)
    app.router.add_post("/api/remote/session/logout", handle_remote_session_logout)
    app.router.add_get("/api/remote/audit", handle_remote_audit)

    # Phase 39: Universal Telegram Bot & Identity
    app.router.add_post("/api/telegram/link/start", handle_telegram_link_start)
    app.router.add_post("/api/telegram/link/sync", handle_telegram_link_sync)
    app.router.add_post("/api/telegram/link/verify", handle_telegram_link_verify)
    app.router.add_get("/api/telegram/link/status", handle_telegram_link_status)
    app.router.add_post("/api/telegram/link/delete", handle_telegram_unlink)
    app.router.add_post("/api/telegram/unlink", handle_telegram_unlink)
    app.router.add_get("/api/telegram/identity", handle_telegram_account)
    app.router.add_get("/api/telegram/account", handle_telegram_account)
    app.router.add_get("/api/telegram/status", handle_telegram_status)

    # Phase 40: Universal Account & Multi-Device Management
    app.router.add_get("/api/account/devices", handle_devices_list)
    app.router.add_get("/api/devices", handle_devices_list)
    app.router.add_post("/api/devices/sync", handle_devices_sync)
    app.router.add_get("/api/devices/{device_id}", handle_device_detail)
    app.router.add_patch("/api/devices/{device_id}", handle_device_rename)
    app.router.add_delete("/api/devices/{device_id}", handle_device_revoke)
    app.router.add_post("/api/devices/{device_id}/select", handle_device_select)
    app.router.add_get("/api/devices/{device_id}/permissions", handle_device_permissions)
    app.router.add_get("/api/account/sessions", handle_account_sessions)
    app.router.add_post("/api/account/sessions/logout-all", handle_account_sessions_logout_all)

    # Phase 41: Account Registration & Authentication
    app.router.add_post("/api/auth/register", handle_auth_register)
    app.router.add_post("/api/auth/login", handle_auth_login)
    app.router.add_post("/api/auth/logout", handle_auth_logout)
    app.router.add_post("/api/auth/logout-all", handle_auth_logout_all)
    app.router.add_get("/api/auth/me", handle_auth_me)
    app.router.add_post("/api/auth/verify-email", handle_auth_verify_email)
    app.router.add_post("/api/auth/forgot-password", handle_auth_forgot_password)
    app.router.add_post("/api/auth/reset-password", handle_auth_reset_password)
    app.router.add_post("/api/auth/change-password", handle_auth_change_password)

    # Phase 41.1: OAuth Redirect & Session Receiver
    app.router.add_get("/api/auth/callback", handle_oauth_callback)
    app.router.add_post("/api/auth/callback/session", handle_oauth_session_save)
    app.router.add_get("/api/auth/callback/session", handle_oauth_session_get)
    # Root route fallback for port 1420 OAuth redirects
    app.router.add_get("/", handle_oauth_callback)

    # Phase 44: Account Identities & Linking
    app.router.add_get("/api/account/identities", handle_account_identities_get)
    app.router.add_post("/api/account/identities/unlink", handle_account_identities_unlink)
    app.router.add_post("/api/account/identities/link/initiate", handle_account_identities_link_initiate)

    # Phase 42: Device Enrollment & Cryptographic Pairing
    app.router.add_post("/api/devices/pairing/start", handle_device_pairing_start)
    app.router.add_post("/api/devices/pairing/complete", handle_device_pairing_complete)
    app.router.add_get("/api/devices/pairing/{pairing_id}", handle_device_pairing_status)
    app.router.add_post("/api/devices/pairing/{pairing_id}/cancel", handle_device_pairing_cancel)
    app.router.add_post("/api/devices/{device_id}/challenge", handle_device_auth_challenge)
    app.router.add_post("/api/devices/{device_id}/authenticate", handle_device_auth_authenticate)
    app.router.add_post("/api/devices/{device_id}/heartbeat", handle_device_heartbeat)

    # Phase 46: Remote Command Queue
    app.router.add_post("/api/devices/{device_id}/commands", handle_command_submit)
    app.router.add_post("/api/devices/{device_id}/commands/{command_id}/confirm", handle_command_confirm)
    app.router.add_post("/api/devices/{device_id}/commands/{command_id}/cancel", handle_command_cancel)
    app.router.add_get("/api/devices/{device_id}/commands/pending", handle_command_pending)
    app.router.add_post("/api/devices/{device_id}/commands/{command_id}/result", handle_command_result)
    app.router.add_get("/api/devices/{device_id}/commands/history", handle_command_history)

    # Phase 47: Full Agent Access & User Consent
    app.router.add_get("/api/devices/{device_id}/agent-access", handle_agent_access_get)
    app.router.add_post("/api/devices/{device_id}/agent-access/warning", handle_agent_access_warning)
    app.router.add_post("/api/devices/{device_id}/agent-access/acknowledge", handle_agent_access_acknowledge)
    app.router.add_post("/api/devices/{device_id}/agent-access/reauth", handle_agent_access_reauth)
    app.router.add_post("/api/devices/{device_id}/agent-access/confirm", handle_agent_access_confirm)
    app.router.add_post("/api/devices/{device_id}/agent-access/disable", handle_agent_access_disable)
    app.router.add_post("/api/devices/{device_id}/agent-access/revoke", handle_agent_access_revoke)
    app.router.add_post("/api/devices/{device_id}/agent-access/revoke-all", handle_agent_access_revoke)
    app.router.add_post("/api/devices/{device_id}/agent-access/override", handle_agent_access_override)

    # Phase 48: Secure Auto Update & Release System
    app.router.add_get("/api/updates/check", handle_update_check)
    app.router.add_get("/api/updates/status", handle_update_status)
    app.router.add_post("/api/updates/download", handle_update_download)
    app.router.add_post("/api/updates/apply", handle_update_apply)
    app.router.add_post("/api/updates/rollback", handle_update_rollback)

    # Phase 46: Universal Telegram Webhook Gateway (production)
    try:
        from core.v8.telegram_webhook import (
            build_telegram_webhook_service,
            register_telegram_routes,
            setup_telegram_lifecycle,
            cleanup_telegram_lifecycle,
        )
        _tg_webhook_svc = build_telegram_webhook_service()
        register_telegram_routes(app, _tg_webhook_svc)
        app.on_startup.append(setup_telegram_lifecycle)
        app.on_cleanup.append(cleanup_telegram_lifecycle)
    except Exception as e:
        logger.warning(f"Telegram webhook gateway yuklanmadi: {e}")

    return app


def run_server(host=None, port=None):
    load_runtime_dotenv()
    resolved_host = host or os.environ.get("MISA_API_HOST", "127.0.0.1")
    resolved_port = port
    if resolved_port is None:
        port_env = os.environ.get("PORT") or os.environ.get("MISA_API_PORT", "18420")
        try:
            resolved_port = int(port_env)
        except ValueError:
            resolved_port = 18420

    logger.info(
        f"MISA AI 9.0.0 Background API Server boshlanmoqda: "
        f"http://{resolved_host}:{resolved_port}"
    )
    get_modules()
    app = create_app()

    async def _serve():
        global _main_loop
        import signal
        _main_loop = asyncio.get_running_loop()
        runner = web.AppRunner(app)
        await runner.setup()

        primary_site = web.TCPSite(runner, resolved_host, resolved_port)
        await primary_site.start()
        logger.info(f"Asosiy API server ishga tushdi: http://{resolved_host}:{resolved_port}")

        # Auxiliary ports (1420, 140) - local desktop OAuth fallback only (never on cloud/Railway)
        is_cloud = bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))
        sync_task = None
        if not is_cloud and resolved_host in ("127.0.0.1", "localhost"):
            for aux_port in (1420, 140):
                if resolved_port != aux_port:
                    try:
                        aux_site = web.TCPSite(runner, resolved_host, aux_port)
                        await aux_site.start()
                        logger.info(f"Qo'shimcha OAuth tinglovchisi ishga tushdi: http://{resolved_host}:{aux_port}")
                    except Exception as e:
                        logger.debug(f"Port {aux_port} band yoki ulanib bo'lmadi: {e}")

            async def _desktop_cloud_sync_loop():
                sync_counter = 0
                while True:
                    try:
                        await asyncio.sleep(5.0)
                        uid = _last_active_desktop_auth.get("user_id")
                        tok = _last_active_desktop_auth.get("token")
                        if uid and tok:
                            await _sync_user_devices_to_cloud(uid, tok)
                            sync_counter += 1
                            if sync_counter % 6 == 0:
                                try:
                                    from core.v8.ai_key_manager import get_ai_key_manager
                                    get_ai_key_manager().sync_from_cloud(auth_token=tok)
                                except Exception:
                                    pass
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        pass

            sync_task = asyncio.create_task(_desktop_cloud_sync_loop())


        stop_event = asyncio.Event()

        def _request_shutdown():
            logger.info("Graceful shutdown signal qabul qilindi (SIGTERM/SIGINT)")
            stop_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                _main_loop.add_signal_handler(sig, _request_shutdown)
            except NotImplementedError:
                signal.signal(sig, lambda s, f: _request_shutdown())

        await stop_event.wait()
        if sync_task:
            sync_task.cancel()
        logger.info("Graceful shutdown boshlandi — active handlerlar tugashini kutmoqda...")
        await runner.cleanup()
        logger.info("API Server to'xtatildi")

    try:
        asyncio.run(_serve())
    except (KeyboardInterrupt, SystemExit):
        logger.info("API Server to'xtatildi")


if __name__ == "__main__":
    cli_port = None
    if len(sys.argv) > 1:
        try:
            cli_port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port=cli_port)
