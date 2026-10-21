# ========== tests/smoke_test_rc.py ==========
# Misa AI 9.2 — Release Candidate Windows Smoke Test & Security Regression Suite
# To'liq avtomatlashtirilgan real Windows tekshiruvlari

import os
import sys
import time
import json
import asyncio
import logging
import subprocess
import urllib.request
import urllib.error
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("smoke_test_rc")

TEST_RESULTS: Dict[str, Any] = {
    "backend_handshake": False,
    "agent_lifecycle": False,
    "unconfirmed_gui_blocked": False,
    "notepad_sandbox_postcondition": False,
    "screenshot_error_handling": False,
    "security_tokenless_rejection": False,
    "security_replay_expiry": False,
    "security_destructive_power_blocked": False,
    "errors": []
}


def test_1_backend_handshake(port: int = 18420) -> bool:
    """1. Backend health/version handshake'ini tekshirish"""
    logger.info("=== STEP 1: Backend Health & Version Handshake ===")
    url = f"http://127.0.0.1:{port}/api/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Misa-SmokeTest/9.3.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            status_code = resp.getcode()
            body_bytes = resp.read()
            data = json.loads(body_bytes.decode("utf-8"))

        logger.info(f"Health response status={status_code}, data={data}")
        version = data.get("version")
        app = data.get("app")
        status = data.get("status") or (data.get("ok") and "ok")

        if status_code == 200 and version in ("9.3.0", "9.3", "9.2.0", "9.2") and app == "Misa AI":
            logger.info("✓ Backend handshake muvaffaqiyatli: Misa AI v9.3.0 (Healthy)")
            TEST_RESULTS["backend_handshake"] = True
            return True
        else:
            err = f"Backend handshake mos kelmadi: version={version}, app={app}, status={status}"
            logger.error(err)
            TEST_RESULTS["errors"].append(err)
            return False
    except Exception as e:
        err = f"Backend health endpointiga ulanib bo'lmadi ({url}): {e}"
        logger.error(err)
        TEST_RESULTS["errors"].append(err)
        return False


def test_2_agent_lifecycle() -> bool:
    """2. Remote agent lifecycle start/stop, duplicate poller himoyasi"""
    logger.info("=== STEP 2: Remote Agent Lifecycle & Poller/Executor ===")
    async def _run():
        from agent.executor import RemoteCommandExecutor, CommandPoller

        executor = RemoteCommandExecutor()
        mock_transport = AsyncMock()
        mock_transport.get.return_value = (200, [])
        mock_transport.post.return_value = (200, {"status": "ok"})

        poller = CommandPoller(
            transport=mock_transport,
            device_id="smoke-test-device-01",
            executor=executor,
            poll_interval=1.0
        )

        # 1. Start poller
        await poller.start()
        if not poller.is_running:
            raise RuntimeError("Poller start chaqirilgandan so'ng is_running True bo'lmadi")

        # 2. Duplicate start himoyasi
        task1 = poller._poll_task
        await poller.start()  # Takroriy chaqirish
        if poller._poll_task is not task1:
            raise RuntimeError("Duplicate poller start takroriy task yaratdi!")

        # 3. Stop poller
        await poller.stop()
        if poller.is_running or poller._poll_task is not None:
            raise RuntimeError("Poller stop chaqirilgandan so'ng to'xtamadi")

        logger.info("✓ Remote agent lifecycle start, duplicate start va stop to'g'ri ishladi")
        TEST_RESULTS["agent_lifecycle"] = True
        return True

    try:
        return asyncio.run(_run())
    except Exception as e:
        err = f"Agent lifecycle testida xatolik: {e}"
        logger.error(err)
        TEST_RESULTS["errors"].append(err)
        return False


def test_3_security_regression(port: int = 18420) -> bool:
    """3. Security regression: Local API himoyasi, replay/expiry va yuqori xavfli actionlar"""
    logger.info("=== STEP 3: Security Regression Verification ===")
    try:
        # A. Local API himoyasi: Ruxsatsiz yoki begona Origin bilan so'rov rad etilishi
        url = f"http://127.0.0.1:{port}/api/plugins/execute"
        body = json.dumps({"name": "calculator", "params": {"expression": "2+2"}}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://malicious-external-site.com"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                status = resp.getcode()
                raise RuntimeError(f"Ruxsatsiz so'rov 403 o'rniga {status} bilan qabul qilindi!")
        except urllib.error.HTTPError as he:
            if he.code == 403:
                logger.info("✓ Ruxsatsiz lokal API so'rovi to'g'ri 403 UNAUTHORIZED_LOCAL_CALLER bilan rad etildi")
                TEST_RESULTS["security_tokenless_rejection"] = True
            else:
                raise RuntimeError(f"Kutilmagan HTTP status kodi: {he.code}")

        # B. Replay va Expiry tekshiruvi
        from core.tools.security_policy import ConfirmationTokenManager, get_security_policy

        mgr = ConfirmationTokenManager(default_ttl_seconds=1.0)
        token = mgr.create_token(tool_name="test_tool", params={"key": "val"})

        # Birinchi marta: muvaffaqiyatli
        ok1, reason1 = mgr.verify_and_consume(token, "test_tool", {"key": "val"})
        if not ok1:
            raise RuntimeError(f"Yangi token tasdiqlanmadi: {reason1}")

        # Ikkinchi marta: TOKEN_ALREADY_USED
        ok2, reason2 = mgr.verify_and_consume(token, "test_tool", {"key": "val"})
        if ok2 or reason2 != "TOKEN_ALREADY_USED":
            raise RuntimeError(f"Replay attack ushlanmadi: ok={ok2}, reason={reason2}")

        # Expiry: qisqa TTL muddati tugashi
        exp_token = mgr.create_token(tool_name="test_tool", params={"key": "val"}, ttl=0.05)
        time.sleep(0.1)
        ok_exp, reason_exp = mgr.verify_and_consume(exp_token, "test_tool", {"key": "val"})
        if ok_exp or reason_exp != "TOKEN_EXPIRED":
            raise RuntimeError(f"Token muddati o'tishi ushlanmadi: ok={ok_exp}, reason={reason_exp}")

        logger.info("✓ Replay va Expiry qoidalari qat'iy ishladi (TOKEN_ALREADY_USED, TOKEN_EXPIRED)")
        TEST_RESULTS["security_replay_expiry"] = True

        # C. Power, file delete va keyboard/mouse actionlar confirmation'siz rad etilishi
        policy = get_security_policy()
        high_risk_actions = [
            ("system_shutdown", {}),
            ("delete_file", {"path": "C:\\fake_test_sandbox\\file.txt"}),
            ("keyboard_type", {"text": "hello"}),
            ("mouse_click", {"x": 100, "y": 100})
        ]

        for action_name, action_params in high_risk_actions:
            dec = policy.evaluate(tool_name=action_name, params=action_params, confirmation_token=None)
            if dec.allowed or not dec.requires_confirmation:
                raise RuntimeError(f"Yuqori xavfli amal '{action_name}' tasdiqsiz ruxsat etildi!")

        logger.info("✓ Power, file delete va input amallari tasdiqsiz qat'iy bloklandi")
        TEST_RESULTS["security_destructive_power_blocked"] = True
        return True
    except Exception as e:
        err = f"Security regression tekshiruvida xatolik: {e}"
        logger.error(err)
        TEST_RESULTS["errors"].append(err)
        return False


def test_4_unconfirmed_gui_action_blocked() -> bool:
    """4. Confirmation talab qiladigan GUI action confirmation'siz bloklanishi"""
    logger.info("=== STEP 4: Unconfirmed GUI Action Blocked ===")
    try:
        from core.tools.security_policy import get_security_policy

        policy = get_security_policy()
        # Tasdiqlanmagan GUI action chaqiruvi
        dec = policy.evaluate(tool_name="keyboard_type", params={"text": "unauthorized text"}, confirmation_token=None)
        if dec.allowed:
            raise RuntimeError("GUI action confirmation_token bo'lmaganda allowed=True qaytardi!")
        if not dec.requires_confirmation or not dec.challenge_token:
            raise RuntimeError("GUI action uchun challenge_token yaratilmadi!")

        logger.info(f"✓ GUI action confirmation'siz bloklandi (Challenge: {dec.challenge_token[:12]}...)")
        TEST_RESULTS["unconfirmed_gui_blocked"] = True
        return True
    except Exception as e:
        err = f"Unconfirmed GUI action testida xatolik: {e}"
        logger.error(err)
        TEST_RESULTS["errors"].append(err)
        return False


def test_5_real_windows_notepad_sandbox() -> bool:
    """
    5. Real Windows Notepad sandbox sinovi:
       - Oynani ochish
       - Fokuslash va tekshirish
       - Tasdiqlangan xavfsiz test matnini yozish
       - Postcondition tekshirish
       - Oynani xavfsiz yopish va tozalash
    """
    logger.info("=== STEP 5: Real Windows Notepad Sandbox Postcondition Test ===")
    proc = None
    try:
        from core.gui.controller import WindowsGUIController
        from core.tools.security_policy import get_security_policy

        controller = WindowsGUIController()
        policy = get_security_policy()

        # 1. Notepad sandbox jarayonini ochish
        logger.info("Notepad ochilmoqda...")
        proc = subprocess.Popen(["notepad.exe"])
        time.sleep(1.2)

        # 2. Notepad oynasini topish
        target = controller.find_window("Notepad") or controller.find_window("Блокнот")
        if not target:
            raise RuntimeError("Yangi ochilgan Notepad oynasi topilmadi!")

        logger.info(f"Notepad topildi: HWND=0x{target.hwnd:X}, Title='{target.title}', PID={target.pid}")

        # 3. Fokuslash
        focused = controller.focus_window(target, timeout=2.0)
        if not focused:
            raise RuntimeError("Notepad oynasiga fokus berib bo'lmadi!")

        # 4. Tasdiqlash tokenini olish (Avtorizatsiyalangan xavfsiz test oqimi)
        test_text = "Misa AI RC Test 9.2"
        token = policy.token_manager.create_token(tool_name="keyboard_type", params={"text": test_text})

        # Tokenni tekshirish
        policy_dec = policy.evaluate(tool_name="keyboard_type", params={"text": test_text}, confirmation_token=token)
        if not policy_dec.allowed:
            raise RuntimeError(f"To'g'ri token bilan ham keyboard_type rad etildi: {policy_dec.reason}")

        # 5. Xavfsiz matn kiritish
        logger.info(f"Notepad ga xavfsiz matn kiritilmoqda: '{test_text}'")
        res = controller.safe_type(text=test_text, target=target, interval=0.03)

        if not res.get("success"):
            raise RuntimeError(f"Matn kiritish muvaffaqiyatsiz bo'ldi: {res.get('error')}")

        if not res.get("postcondition_verified"):
            raise RuntimeError("Postcondition tekshiruvidan o'tmadi: oyna qulab tushgan yoki yo'qolgan!")

        logger.info("✓ Notepad matn kiritish va postcondition to'liq tasdiqlandi!")
        TEST_RESULTS["notepad_sandbox_postcondition"] = True
        return True

    except Exception as e:
        err = f"Notepad sandbox testida xatolik: {e}"
        logger.error(err)
        TEST_RESULTS["errors"].append(err)
        return False
    finally:
        # Har qanday holatda Notepad jarayonini xavfsiz tozalash
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
                logger.info("Notepad jarayoni xavfsiz yakunlandi ✓")
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


def test_6_screenshot_hardening() -> bool:
    """6. Screenshot xatosi bo'lsa noto'g'ri success/captured: true qaytmasligini tekshirish"""
    logger.info("=== STEP 6: Screenshot Error Handling Hardening ===")
    try:
        from agent.tools import handle_system_screenshot

        # Simulyatsiya: Screenshot funksiyasi xatolik berganda
        with patch("PIL.ImageGrab.grab", side_effect=PermissionError("Display access denied in mock test")):
            res = handle_system_screenshot({})

            # Noto'g'ri captured: True yoki success: True bo'lmasligi shart!
            if res.get("captured") is True or res.get("success") is True:
                raise RuntimeError(f"Screenshot xatolik yuz berganda noto'g'ri success qaytardi: {res}")

            if "Display access denied" not in res.get("error", ""):
                raise RuntimeError(f"Kutilgan xatolik xabari qaytmadi: {res}")

        logger.info("✓ Screenshot xatosi bo'lganda soxta 'captured: True' berilmasligi tasdiqlandi")
        TEST_RESULTS["screenshot_error_handling"] = True
        return True
    except Exception as e:
        err = f"Screenshot hardening testida xatolik: {e}"
        logger.error(err)
        TEST_RESULTS["errors"].append(err)
        return False


def run_all_smoke_tests():
    logger.info("=======================================================")
    logger.info("MISA AI 9.2 RELEASE CANDIDATE SMOKE TESTS BOSHLANDI")
    logger.info("=======================================================")

    # Background backend jarayoni tekshiruvi yoki vaqtincha ishga tushirish
    backend_proc = None
    port = 18420

    # Port listening tekshirish
    is_up = False
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.0)
        is_up = True
    except Exception:
        is_up = False

    if not is_up:
        logger.info(f"Port {port} da server aniqlanmadi. Backend subprocess ishga tushirilmoqda...")
        backend_proc = subprocess.Popen(
            [sys.executable, "core/api_server.py", str(port)],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Server kutish (maks 10 soniya)
        for _ in range(20):
            time.sleep(0.5)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.0)
                is_up = True
                break
            except Exception:
                pass

        if not is_up:
            logger.error("Backend serverni ishga tushirib bo'lmadi!")

    try:
        test_1_backend_handshake(port)
        test_2_agent_lifecycle()
        test_3_security_regression(port)
        test_4_unconfirmed_gui_action_blocked()
        test_5_real_windows_notepad_sandbox()
        test_6_screenshot_hardening()
    finally:
        if backend_proc:
            logger.info("Sinov backend jarayoni to'xtatilmoqda...")
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=3.0)
            except Exception:
                backend_proc.kill()
            logger.info("Sinov backend jarayoni to'xtatildi ✓")

    logger.info("=======================================================")
    logger.info("SMOKE TESTS YAKUNIY NATIJALARI:")
    for k, v in TEST_RESULTS.items():
        if k != "errors":
            status_symbol = "✓ PASS" if v else "✗ FAIL"
            logger.info(f"  {k:35}: {status_symbol}")

    if TEST_RESULTS["errors"]:
        logger.error(f"Xatoliklar ro'yxati ({len(TEST_RESULTS['errors'])} ta):")
        for err in TEST_RESULTS["errors"]:
            logger.error(f"  - {err}")
        return False
    else:
        logger.info("BARCHA 6 TA SMOKE & REGRESSION TESTLAR 100% MUVAFFAQIYATLI O'TDI!")
        logger.info("=======================================================")
        return True


if __name__ == "__main__":
    success = run_all_smoke_tests()
    if not success:
        sys.exit(1)
