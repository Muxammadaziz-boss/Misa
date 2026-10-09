# ========== sandbox.py ==========
# Xavfsiz Sinov Maydoni (Sandbox)
# Kodni izolatsiyalangan muhitda bajarish

import os
import sys
import tempfile
import subprocess
import logging
import shutil
import ast
import re
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Loyiha ildizi
SANDBOX_DIR = os.path.join(BASE_DIR, "sandbox_workspace")


class Sandbox:
    """
    Izolatsiyalangan kod bajarish muhiti.
    Xavfli operatsiyalardan himoyalangan.
    """

    ALLOWED_MODULES = {
        "math",
        "random",
        "datetime",
        "json",
        "re",
        "collections",
        "itertools",
        "functools",
        "operator",
        "string",
        "textwrap",
        "heapq",
        "bisect",
        "array",
        "copy",
        "pprint",
    }

    BLOCKED_PATTERNS = [
        r"import\s+os\s*(?!as)",
        r"from\s+os\s+import",
        r"import\s+sys\s*(?!as)",
        r"from\s+sys\s+import",
        r"import\s+subprocess",
        r"from\s+subprocess\s+import",
        r"import\s+socket",
        r"from\s+socket\s+import",
        r"import\s+urllib",
        r"from\s+urllib\s+import",
        r"import\s+requests",
        r"from\s+requests\s+import",
        r"import\s+http",
        r"from\s+http\s+import",
        r"open\s*\(",
        r"file\s*\(",
        r"os\.system",
        r"os\.popen",
        r"subprocess\.call",
        r"subprocess\.run",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"compile\s*\(",
        r"getattr\s*\(",
        r"setattr\s*\(",
        r"del\s+",
        r"reload\s*\(",
    ]

    BLOCKED_FUNCTIONS = {
        "exit",
        "quit",
        "breakpoint",
        "help",
        "input",
        "raw_input",
    }

    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or SANDBOX_DIR
        self._ensure_workspace()

    def _ensure_workspace(self):
        """Ishchi papkani yaratish"""
        try:
            os.makedirs(self.workspace_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Workspace yaratish xatolik: {e}")
            self.workspace_dir = tempfile.mkdtemp(prefix="misa_sandbox_")

    def validate_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Kodni xavfsizlik jihatidan tekshirish.
        Xavfli patternlar bo'lsa, False qaytaradi.
        """
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Xavfli pattern topildi: {pattern}"

        try:
            tree = ast.parse(code)
            forbidden_modules = {
                "os", "sys", "subprocess", "socket", "urllib", "requests", "http",
                "shutil", "ctypes", "pty", "posix", "nt", "importlib", "pickle", "marshal"
            }
            forbidden_names = self.BLOCKED_FUNCTIONS | {
                "__builtins__", "eval", "exec", "compile", "open", "getattr", "setattr", "delattr", "__import__"
            }
            forbidden_attrs = {
                "__class__", "__subclasses__", "__bases__", "__globals__", "__builtins__",
                "__code__", "__mro__", "__import__", "__loader__", "__spec__"
            }

            for node in ast.walk(tree):
                # 1. Block dangerous names and builtins
                if isinstance(node, ast.Name) and node.id in forbidden_names:
                    return False, f"Xavfli funksiya yoki identifikator: {node.id}"
                
                # 2. Block dunder attribute escape chains
                if isinstance(node, ast.Attribute) and node.attr in forbidden_attrs:
                    return False, f"Xavfli dunder atribut orqali xavfsizlikni buzish: {node.attr}"

                # 3. Block unauthorized imports via AST
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod_root = alias.name.split(".")[0]
                        if mod_root in forbidden_modules or (self.ALLOWED_MODULES and mod_root not in self.ALLOWED_MODULES):
                            return False, f"Ruxsat etilmagan modul importi: {alias.name}"

                if isinstance(node, ast.ImportFrom):
                    mod_root = (node.module or "").split(".")[0]
                    if mod_root in forbidden_modules or (self.ALLOWED_MODULES and mod_root not in self.ALLOWED_MODULES):
                        return False, f"Ruxsat etilmagan modul importi: {node.module}"

        except SyntaxError as e:
            return False, f"Syntax xatolik: {e}"

        return True, None

    def execute_python(
        self, code: str, timeout: int = 10, validate: bool = True
    ) -> Dict[str, Any]:
        """
        Python kodni izolatsiyalangan muhitda bajarish.

        Args:
            code: Bajariladigan Python kodi
            timeout: Maksimal bajarish vaqti (soniyada)
            validate: Kodni tekshirish (default True)

        Returns:
            Dict[str, Any]: natija yoki xatolik
        """
        if validate:
            is_safe, error = self.validate_code(code)
            if not is_safe:
                return {
                    "status": "error",
                    "error": f"Kod xavfli deb topildi: {error}",
                    "blocked": True,
                }

        temp_file = None
        result_file = os.path.join(self.workspace_dir, f"result_{os.getpid()}.txt")

        try:
            temp_fd, temp_file = tempfile.mkstemp(
                suffix=".py", dir=self.workspace_dir, text=True
            )

            wrapped_code = self._wrap_code(code)
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(wrapped_code)

            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.workspace_dir,
                env=self._get_safe_env(),
            )

            output = result.stdout.strip()
            error = result.stderr.strip()

            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": error or "Noma'lum xatolik",
                    "returncode": result.returncode,
                }

            return {"status": "success", "output": output, "execution_time": None}

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": f"Kod {timeout} soniyada tugamadi (cheklangan vaqt)",
                "timeout": True,
            }
        except Exception as e:
            logger.error(f"Sandbox execute xatolik: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def _wrap_code(self, code: str) -> str:
        """Kodni natija olish uchun wrap qilish"""
        return f"""
import sys
import io
import traceback

_output = io.StringIO()
_error = io.StringIO()

sys.stdout = _output
sys.stderr = _error

try:
{self._indent_code(code, 1)}
except Exception as e:
    print(f"ERROR: {{type(e).__name__}}: {{e}}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
finally:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print(_output.getvalue())
"""

    def _indent_code(self, code: str, spaces: int) -> str:
        """Kodni indent qilish"""
        indent = " " * (4 * spaces)
        return "\n".join(
            indent + line if line.strip() else line for line in code.split("\n")
        )

    def _get_safe_env(self) -> Dict[str, str]:
        """Xavfsiz muhit o'zgaruvchilari"""
        env = os.environ.copy()
        safe_keys = {"PATH", "TEMP", "TMP", "HOME", "USER", "SYSTEMROOT", "COMSPEC"}
        python_safe = {"PYTHONPATH", "PYTHONHOME", "PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING"}
        return {
            k: v
            for k, v in env.items()
            if k.upper() in safe_keys | python_safe
        }

    def execute_bash(self, command: str, timeout: int = 5) -> Dict[str, Any]:
        """
        Cheklangan bash buyrug'ini bajarish.
        Faqat xavfsiz buyruqlar ruxsat etilgan.
        """
        allowed_commands = {
            "echo",
            "pwd",
            "ls",
            "dir",
            "cat",
            "type",
            "head",
            "tail",
            "wc",
            "grep",
            "find",
            "date",
        }

        parts = command.strip().split()
        if not parts:
            return {"status": "error", "error": "Buyruq bo'sh"}

        base_cmd = os.path.basename(parts[0]).lower()
        if base_cmd not in allowed_commands:
            return {
                "status": "error",
                "error": f"Ruxsat etilmagan buyruq: {base_cmd}",
                "allowed": list(allowed_commands),
            }

        # Xavfsizlik: pipe, redirect va zanjir operatorlarini bloklash
        dangerous_chars = {'|', '&', ';', '>', '<', '`', '$', '(', ')'}
        if any(c in command for c in dangerous_chars):
            return {
                "status": "error",
                "error": "Xavfli belgilar topildi (pipe, redirect, zanjir)",
            }

        try:
            result = subprocess.run(
                parts,
                shell=False,  # Xavfsiz: shell injection oldini olish
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.workspace_dir,
            )

            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": f"Buyruq {timeout} soniyada tugamadi",
                "timeout": True,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def cleanup(self):
        """Workspace ni tozalash"""
        try:
            if os.path.exists(self.workspace_dir):
                for item in os.listdir(self.workspace_dir):
                    path = os.path.join(self.workspace_dir, item)
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                        elif os.path.isdir(path):
                            shutil.rmtree(path)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Cleanup xatolik: {e}")


_sandbox_instance: Optional[Sandbox] = None


def get_sandbox() -> Sandbox:
    """Global sandbox instance"""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = Sandbox()
    return _sandbox_instance


def execute_safe(code: str, timeout: int = 10) -> Dict[str, Any]:
    """Qulay funksiya — sandbox orqali kod bajarish"""
    return get_sandbox().execute_python(code, timeout)
