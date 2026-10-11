# ========== logger.py ==========
# Misa AI 8.0.0 — Production Logging Subsystem [Phase 22]
# Provides structured rotating logs:
#   - logs/misa.log  (General application events, AI engine, memory, tools)
#   - logs/backend.log (API server requests, WebSocket, supervisor lifecycle)
#   - logs/crash.log   (Unhandled exceptions, thread failures, fatal errors)
# Includes automatic sensitive data sanitization (API keys, tokens, credentials).

import os
import sys
import re
import logging
import traceback
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Windows terminalida UnicodeEncodeError (charmap / emoji) oldini olish
if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

MISA_LOG_PATH = os.path.join(LOGS_DIR, "misa.log")
BACKEND_LOG_PATH = os.path.join(LOGS_DIR, "backend.log")
CRASH_LOG_PATH = os.path.join(LOGS_DIR, "crash.log")

# Regex patterns for sensitive data
SENSITIVE_PATTERNS = [
    # Google API keys (AIza...)
    (re.compile(r"AIza[0-9A-Za-z_-]{35}"), "AIza***MASKED_KEY***"),
    # OpenAI/Anthropic/OpenRouter keys (sk-...)
    (re.compile(r"sk-[a-zA-Z0-9_-]{20,}"), "sk-***MASKED_KEY***"),
    # Supabase new keys (sb_secret_..., sb_publishable_...)
    (re.compile(r"sb_secret_[a-zA-Z0-9_-]{20,}"), "sb_secret_***MASKED***"),
    (re.compile(r"sb_publishable_[a-zA-Z0-9_-]{20,}"), "sb_publishable_***MASKED***"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{15,}", re.IGNORECASE), r"\1***MASKED_TOKEN***"),
    # Private keys
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC )?PRIVATE KEY-----"), "***MASKED_PRIVATE_KEY***"),
    # JSON password / token / secret / api_key / refresh_token fields
    (re.compile(r'("(?:password|api_key|token|secret|access_token|refresh_token|session_token|service_role|private_key)"\s*:\s*)"[^"]+"', re.IGNORECASE), r'\1"***MASKED***"'),
]


class SensitiveDataFilter(logging.Filter):
    """Log xabarlaridagi maxfiy kalit va ma'lumotlarni avtomatik yashiruvchi filtr"""
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pattern, repl in SENSITIVE_PATTERNS:
                msg = pattern.sub(repl, msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


def sanitize_text(text: str) -> str:
    """Ixtiyoriy matndan maxfiy ma'lumotlarni tozalash"""
    if not isinstance(text, str):
        return text
    res = text
    for pattern, repl in SENSITIVE_PATTERNS:
        res = pattern.sub(repl, res)
    return res


def get_misa_handler(max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5) -> RotatingFileHandler:
    """logs/misa.log uchun rotating fayl handler"""
    handler = RotatingFileHandler(MISA_LOG_PATH, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.addFilter(SensitiveDataFilter())
    return handler


def get_backend_handler(max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5) -> RotatingFileHandler:
    """logs/backend.log uchun rotating fayl handler"""
    handler = RotatingFileHandler(BACKEND_LOG_PATH, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.addFilter(SensitiveDataFilter())
    return handler


def log_crash(exc_type, exc_value, exc_traceback, context: str = "Kutilmagan xatolik"):
    """Crash haqida to'liq diagnostika ma'lumotlarini logs/crash.log ga xavfsiz yozish"""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        raw_tb = "".join(tb_lines)
        clean_tb = sanitize_text(raw_tb)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        entry = (
            f"\n{'=' * 70}\n"
            f"CRASH REPORT — {timestamp}\n"
            f"Context: {context}\n"
            f"Exception: {exc_type.__name__ if exc_type else 'Unknown'}: {sanitize_text(str(exc_value))}\n"
            f"Thread: {threading.current_thread().name}\n"
            f"{'-' * 70}\n"
            f"{clean_tb}"
            f"{'=' * 70}\n"
        )
        with open(CRASH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
            f.flush()
    except Exception as e:
        print(f"Crash log yozishda xatolik: {e}", file=sys.stderr)


def install_crash_handlers():
    """Global crash ushlagichlarni (sys.excepthook va threading.excepthook) o'rnatish"""
    original_sys_excepthook = sys.excepthook

    def _sys_excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            original_sys_excepthook(exc_type, exc_value, exc_traceback)
            return
        log_crash(exc_type, exc_value, exc_traceback, context="Asosiy oqim (Main Thread)")
        original_sys_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _sys_excepthook

    if hasattr(threading, "excepthook"):
        def _threading_excepthook(args):
            log_crash(args.exc_type, args.exc_value, args.exc_traceback, context=f"Thread '{args.thread.name}'")
        threading.excepthook = _threading_excepthook
