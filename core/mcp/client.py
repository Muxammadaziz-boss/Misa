# ========== core/mcp/client.py ==========
# Misa AI v9.0 — Universal Model Context Protocol (MCP) Client
# Standart MCP (JSON-RPC 2.0) protokoli bo'yicha HTTP va Stdio serverlar bilan aloqa

import os
import json
import logging
import threading
import subprocess
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MCPClient:
    """Universal Model Context Protocol (MCP) mijozi (HTTP va STDIO qo'llab-quvvatlaydi)."""

    def __init__(
        self,
        server_id: str,
        transport: str = "http",
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 60,
    ):
        self.server_id = server_id
        self.transport = (transport or "http").lower()
        self.url = url
        self.headers = headers or {}
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.timeout = timeout
        self._request_id = 1
        self._proc: Optional[subprocess.Popen] = None
        self._proc_lock = threading.RLock()
        self._is_initialized = False

    def _next_id(self) -> int:
        req_id = self._request_id
        self._request_id += 1
        return req_id

    def _send_http_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """HTTP transport orqali JSON-RPC 2.0 so'rovi yuborish"""
        if not self.url:
            raise ValueError(f"MCP server '{self.server_id}' uchun URL ko'rsatilmagan")

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }

        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.headers,
        }

        try:
            call_timeout = 5 if method == "tools/list" else self.timeout
            resp = requests.post(
                self.url,
                headers=req_headers,
                json=payload,
                timeout=call_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                err = data["error"]
                err_msg = err.get("message") if isinstance(err, dict) else str(err)
                logger.error(f"[MCPClient:{self.server_id}] RPC xatolik: {err_msg}")
                return {"error": err_msg}
            return data.get("result", {})
        except requests.exceptions.RequestException as e:
            logger.error(f"[MCPClient:{self.server_id}] HTTP so'rov xatoligi: {e}")
            return {"error": f"Ulanish xatosi: {str(e)}"}
        except Exception as e:
            logger.error(f"[MCPClient:{self.server_id}] Kutilmagan xatolik: {e}")
            return {"error": str(e)}

    def _ensure_stdio_proc(self) -> Optional[subprocess.Popen]:
        """STDIO jarayonini ishga tushirish yoki qayta tiklash"""
        with self._proc_lock:
            if self._proc is not None and self._proc.poll() is None:
                return self._proc

            if not self.command:
                logger.error(f"[MCPClient:{self.server_id}] Stdio transport uchun command ko'rsatilmagan")
                return None

            proc_env = os.environ.copy()
            if self.env:
                proc_env.update(self.env)

            cmd_list = [self.command] + self.args
            try:
                self._proc = subprocess.Popen(
                    cmd_list,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    env=proc_env,
                    bufsize=1,
                )
                self._is_initialized = False

                # MCP Standart Handshake (initialize)
                init_id = self._next_id()
                init_payload = {
                    "jsonrpc": "2.0",
                    "id": init_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "Misa AI", "version": "9.4.0"},
                    },
                }
                self._proc.stdin.write(json.dumps(init_payload) + "\n")
                self._proc.stdin.flush()

                # Javobni o'qish (handshake)
                line = self._proc.stdout.readline()
                if line:
                    # Initsializatsiya bildirishnomasi
                    notify_payload = {
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                    }
                    self._proc.stdin.write(json.dumps(notify_payload) + "\n")
                    self._proc.stdin.flush()
                    self._is_initialized = True
                    logger.info(f"[MCPClient:{self.server_id}] Stdio MCP server muvaffaqiyatli ishga tushirildi: {' '.join(cmd_list)}")

                return self._proc
            except Exception as e:
                logger.error(f"[MCPClient:{self.server_id}] Stdio jarayonini ishga tushirishda xato: {e}")
                self._proc = None
                return None

    def _send_stdio_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """STDIO orqali JSON-RPC 2.0 xabarini uzatish va javobni kutish"""
        with self._proc_lock:
            proc = self._ensure_stdio_proc()
            if not proc or proc.poll() is not None:
                return {"error": "Stdio MCP jarayoni ishlamayapti"}

            req_id = self._next_id()
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params or {},
            }

            try:
                msg_str = json.dumps(payload) + "\n"
                proc.stdin.write(msg_str)
                proc.stdin.flush()

                # Bir qator JSON-RPC javobini o'qish
                resp_line = proc.stdout.readline()
                if not resp_line:
                    return {"error": "Stdio serverdan bo'sh javob qaytdi"}

                data = json.loads(resp_line.strip())
                if "error" in data:
                    err = data["error"]
                    err_msg = err.get("message") if isinstance(err, dict) else str(err)
                    return {"error": err_msg}
                return data.get("result", {})
            except Exception as e:
                logger.error(f"[MCPClient:{self.server_id}] Stdio RPC xatosi ({method}): {e}")
                return {"error": str(e)}

    def list_tools(self) -> List[Dict[str, Any]]:
        """MCP serveridagi barcha mavjud vositalarni (tools) olish"""
        if self.transport == "http":
            res = self._send_http_rpc("tools/list")
            if isinstance(res, dict) and "tools" in res:
                return res["tools"]
            return []
        elif self.transport == "stdio":
            res = self._send_stdio_rpc("tools/list")
            if isinstance(res, dict) and "tools" in res:
                return res["tools"]
            return []
        return []

    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Muayyan MCP vositasini chaqirish va natijani olish"""
        args = arguments or {}
        if self.transport == "http":
            res = self._send_http_rpc("tools/call", {"name": tool_name, "arguments": args})
        elif self.transport == "stdio":
            res = self._send_stdio_rpc("tools/call", {"name": tool_name, "arguments": args})
        else:
            return {"ok": False, "error": f"Noma'lum transport: {self.transport}"}

        if "error" in res:
            return {"ok": False, "error": res["error"]}

        content_list = res.get("content", [])
        output_texts = []
        for item in content_list:
            if isinstance(item, dict):
                if "text" in item:
                    output_texts.append(item["text"])
                elif "data" in item:
                    output_texts.append(str(item["data"]))
            else:
                output_texts.append(str(item))

        combined_text = "\n".join(output_texts)
        try:
            parsed_json = json.loads(combined_text)
            return {"ok": True, "raw": combined_text, "data": parsed_json}
        except Exception:
            return {"ok": True, "raw": combined_text, "data": combined_text}

    def close(self):
        """Mijoz jarayonini xavfsiz to'xtatish"""
        with self._proc_lock:
            if self._proc is not None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=2)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
                self._proc = None
                self._is_initialized = False

    def ping(self) -> bool:
        """Server ishlayotganini tekshirish"""
        try:
            tools = self.list_tools()
            return len(tools) >= 0
        except Exception:
            return False
