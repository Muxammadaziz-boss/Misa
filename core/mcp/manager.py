# ========== core/mcp/manager.py ==========
# Misa AI v9.0 — Universal Model Context Protocol (MCP) Manager
# Barcha tashqi va ichki MCP serverlarni dinamik boshqarish, ro'yxatdan o'tkazish va nazorat qilish

import os
import json
import logging
from typing import Dict, Any, List, Optional
from core.mcp.client import MCPClient

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCP_CONFIG_PATH = os.path.join(BASE_DIR, "data", "mcp_servers.json")


class MCPManager:
    """Misa MCP boshqaruvchisi — barcha MCP serverlarni konfiguratsiya va monitoring qilish."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MCPManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        self.config_path = config_path or MCP_CONFIG_PATH
        self._servers: Dict[str, Dict[str, Any]] = {}
        self._clients: Dict[str, MCPClient] = {}
        self._cached_tools: Dict[str, List[Dict[str, Any]]] = {}
        self.load_config()
        self._initialized = True

    def load_config(self) -> None:
        """data/mcp_servers.json faylidan serverlarni o'qish"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._servers = data.get("servers", {})
                    logger.info(f"[MCPManager] {len(self._servers)} ta MCP server yuklandi")
            except Exception as e:
                logger.error(f"[MCPManager] Konfiguratsiyani o'qishda xatolik: {e}")
                self._servers = {}
        else:
            self._servers = {}

        self._refresh_clients()

    def save_config(self) -> bool:
        """data/mcp_servers.json fayliga serverlarni saqlash"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            payload = {
                "$schema": "mcp_servers_registry_v1",
                "version": "1.0.0",
                "description": "Misa AI Universal Model Context Protocol (MCP) Server Configuration Registry",
                "servers": self._servers,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"[MCPManager] Konfiguratsiyani saqlashda xatolik: {e}")
            return False

    def _refresh_clients(self) -> None:
        """Mavjud serverlar uchun MCPClient obyektlarini yangilash"""
        self._clients = {}
        for s_id, cfg in self._servers.items():
            if cfg.get("enabled", True):
                self._clients[s_id] = MCPClient(
                    server_id=s_id,
                    transport=cfg.get("transport", "http"),
                    url=cfg.get("url"),
                    headers=cfg.get("headers", {}),
                    command=cfg.get("command"),
                    args=cfg.get("args", []),
                    env=cfg.get("env", {}),
                    timeout=cfg.get("timeout", 60),
                )

    def get_servers(self) -> Dict[str, Dict[str, Any]]:
        """Barcha ro'yxatdan o'tgan serverlar lug'atini olish"""
        return self._servers

    def list_servers(self) -> List[Dict[str, Any]]:
        """Barcha ro'yxatdan o'tgan serverlar ro'yxatini olish"""
        return list(self._servers.values())

    def register_server(self, server_id: str, config: Dict[str, Any]) -> bool:
        """Yangi MCP server qo'shish yoki mavjudini yangilash (Kelajakdagi MCP lar uchun ochiq o'rin)"""
        clean_id = server_id.lower().strip()
        self._servers[clean_id] = {
            "id": clean_id,
            "name": config.get("name", clean_id),
            "description": config.get("description", ""),
            "transport": config.get("transport", "http"),
            "url": config.get("url"),
            "headers": config.get("headers", {}),
            "command": config.get("command"),
            "args": config.get("args", []),
            "env": config.get("env", {}),
            "enabled": config.get("enabled", True),
            "timeout": config.get("timeout", 60),
            "category": config.get("category", "Umumiy"),
        }
        saved = self.save_config()
        self._refresh_clients()
        return saved

    def remove_server(self, server_id: str) -> bool:
        """Serverni ro'yxatdan o'chirish"""
        clean_id = server_id.lower().strip()
        if clean_id in self._servers:
            del self._servers[clean_id]
            self.save_config()
            self._refresh_clients()
            return True
        return False

    def toggle_server(self, server_id: str, enabled: Optional[bool] = None) -> bool:
        """Serverni yoqish yoki o'chirish"""
        clean_id = server_id.lower().strip()
        if clean_id in self._servers:
            curr = self._servers[clean_id].get("enabled", True)
            self._servers[clean_id]["enabled"] = (not curr) if enabled is None else bool(enabled)
            self.save_config()
            self._refresh_clients()
            return True
        return False

    def get_client(self, server_id: str) -> Optional[MCPClient]:
        """Muayyan server mijozi (client) ni olish"""
        return self._clients.get(server_id.lower().strip())

    def get_all_tools(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Barcha faol MCP serverlaridagi barcha vositalarni olish"""
        all_tools = []
        for s_id, client in self._clients.items():
            if not force_refresh and s_id in self._cached_tools:
                tools = self._cached_tools[s_id]
            else:
                try:
                    tools = client.list_tools()
                    self._cached_tools[s_id] = tools
                except Exception as e:
                    logger.warning(f"[MCPManager] '{s_id}' serveridan tool list olishda xatolik: {e}")
                    tools = []

            for t in tools:
                augmented = dict(t)
                augmented["server_id"] = s_id
                augmented["server_name"] = self._servers.get(s_id, {}).get("name", s_id)
                augmented["misa_qualified_name"] = f"mcp_{s_id}_{t.get('name')}"
                all_tools.append(augmented)
        return all_tools

    def call_tool(self, server_id: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Kerakli serverdagi toolni chaqirish"""
        client = self.get_client(server_id)
        if not client:
            return {"ok": False, "error": f"MCP server '{server_id}' topilmadi yoki o'chirilgan"}
        return client.call_tool(tool_name, arguments)


def get_mcp_manager() -> MCPManager:
    """Singleton MCPManager instansiyasini olish"""
    return MCPManager()
