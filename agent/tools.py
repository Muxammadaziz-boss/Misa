# ========== agent/tools.py ==========
# Phase 46 — Real Windows Tool Handlers & Security

import os
import time
import socket
import platform
import logging
import subprocess
import dataclasses
from typing import Dict, Any, List, Optional, Callable, Tuple
from pathlib import Path
from tempfile import gettempdir

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger('agent.tools')

# --- Xavfsizlik bo'limi (Security section) ---

class PathSecurityValidator:
    """Path security validator to prevent path traversal and access to sensitive files/directories."""
    
    BLOCKED_PATTERNS = ["..", "\\\\"]
    # Blocked Windows device names
    for _d in ["CON", "NUL", "PRN"]:
        BLOCKED_PATTERNS.append(_d)
    for _i in range(1, 10):
        BLOCKED_PATTERNS.extend([f"COM{_i}", f"LPT{_i}"])
        
    BLOCKED_DIRECTORIES = {
        r"c:\windows",
        r"c:\windows\system32",
        r"appdata\local",
        r"appdata\roaming",
        r".ssh",
        r".gnupg",
        r"google\chrome\user data",
        r"mozilla\firefox\profiles"
    }
    
    CREDENTIAL_FILES = {
        ".env", "id_rsa", "id_ed25519", "credentials", "passwords.txt", 
        "*.key", "*.pem"
    }

    @staticmethod
    def get_default_sandbox() -> str:
        return os.path.expanduser("~/MisaSandbox")

    @classmethod
    def validate_path(cls, path: str, allowed_dirs: List[str] = None) -> Tuple[bool, str, str]:
        if allowed_dirs is None:
            allowed_dirs = [cls.get_default_sandbox()]
            
        if not path:
            return False, "", "EMPTY_PATH"
            
        # 1. Check patterns
        if ".." in path:
            return False, "", "PATH_TRAVERSAL"
        if "\\\\" in path or path.startswith("//") or path.startswith(r"\\"):
            return False, "", "UNC_PATH_BLOCKED"
            
        # Device names
        basename = os.path.basename(path).upper()
        name_no_ext = os.path.splitext(basename)[0]
        if name_no_ext in ["CON", "NUL", "PRN"] or (len(name_no_ext) == 4 and name_no_ext.startswith("COM") and name_no_ext[3].isdigit()) or (len(name_no_ext) == 4 and name_no_ext.startswith("LPT") and name_no_ext[3].isdigit()):
            return False, "", "DEVICE_NAME_BLOCKED"

        # 2. Resolve absolute
        try:
            resolved_path = os.path.abspath(os.path.expanduser(path))
            resolved_path = os.path.realpath(resolved_path) # resolve symlinks
        except Exception as e:
            return False, "", f"PATH_RESOLUTION_ERROR: {str(e)}"
            
        # 3. Blocked dirs
        path_lower = resolved_path.lower()
        for b_dir in cls.BLOCKED_DIRECTORIES:
            if b_dir in path_lower:
                return False, "", "SENSITIVE_DIRECTORY"
                
        # 4. Credential files
        fname_lower = os.path.basename(resolved_path).lower()
        for c_file in cls.CREDENTIAL_FILES:
            if c_file.startswith("*."):
                if fname_lower.endswith(c_file[1:]):
                    return False, "", "CREDENTIAL_FILE"
            elif fname_lower == c_file:
                return False, "", "CREDENTIAL_FILE"
                
        # 5. Allowed dirs (Sandbox)
        is_allowed = False
        for allowed in allowed_dirs:
            try:
                allowed_abs = os.path.realpath(os.path.abspath(os.path.expanduser(allowed)))
                common = os.path.commonpath([resolved_path, allowed_abs])
                if common == allowed_abs:
                    is_allowed = True
                    break
            except Exception:
                pass
                
        if not is_allowed:
            return False, "", "PATH_OUTSIDE_SANDBOX"
            
        return True, resolved_path, "OK"

# App security
ALLOWED_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "wordpad": "write.exe",
    "snipping_tool": "SnippingTool.exe",
    "task_manager": "taskmgr.exe",
    "chrome": "chrome.exe",
    "browser": "chrome.exe"
}

PROTECTED_PROCESSES = {
    "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", 
    "smss.exe", "winlogon.exe", "system", "svchost.exe", 
    "dwm.exe", "explorer.exe", "registry", "fontdrvhost.exe", 
    "conhost.exe", "runtimebroker.exe"
}

# --- Asosiy strukturalar (Core structures) ---

@dataclasses.dataclass
class AgentToolHandler:
    tool_id: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    timeout: float = 10.0
    max_result_bytes: int = 65536
    risk_level: str = "LOW"
    requires_confirmation: bool = False

class AgentToolRegistry:
    _instance = None
    
    def __init__(self):
        self._tools: Dict[str, AgentToolHandler] = {}
        self._register_defaults()
        
    @classmethod
    def get_default_instance(cls) -> 'AgentToolRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def register(self, handler: AgentToolHandler):
        self._tools[handler.tool_id] = handler
        
    def get(self, tool_id: str) -> Optional[AgentToolHandler]:
        return self._tools.get(tool_id)
        
    def list_tools(self) -> List[str]:
        return list(self._tools.keys())
        
    def execute(self, tool_id: str, params: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        handler = self.get(tool_id)
        if not handler:
            return {"ok": False, "error": f"Tool not found: {tool_id}", "duration_ms": 0}
            
        start_time = time.time()
        try:
            result = handler.handler(params)
            duration = int((time.time() - start_time) * 1000)
            return {"ok": True, "data": result, "duration_ms": duration}
        except Exception as e:
            logger.exception(f"Error executing tool {tool_id}")
            duration = int((time.time() - start_time) * 1000)
            return {"ok": False, "error": str(e), "duration_ms": duration}

    def _register_defaults(self):
        tools = [
            ("system.status", handle_system_status, 10.0, "LOW", False),
            ("system.info", handle_system_info, 10.0, "LOW", False),
            ("system.screenshot", handle_system_screenshot, 15.0, "LOW", False),
            ("app.list", handle_app_list, 10.0, "LOW", False),
            ("app.launch", handle_app_launch, 10.0, "MEDIUM", False),
            ("app.close", handle_app_close, 10.0, "MEDIUM", True),
            ("file.list", handle_file_list, 10.0, "LOW", False),
            ("file.read", handle_file_read, 10.0, "MEDIUM", False),
            ("file.write", handle_file_write, 15.0, "HIGH", True),
            ("file.delete", handle_file_delete, 10.0, "HIGH", True),
            ("network.info", handle_network_info, 10.0, "LOW", False),
            ("power.restart", handle_power_restart, 10.0, "HIGH", True),
            ("power.shutdown", handle_power_shutdown, 10.0, "HIGH", True),
            ("power.sleep", handle_power_sleep, 10.0, "HIGH", True),
            ("power.wake", handle_power_wake, 5.0, "LOW", False),
        ]
        for t_id, func, timeout, risk, req_conf in tools:
            self.register(AgentToolHandler(
                tool_id=t_id,
                handler=func,
                timeout=timeout,
                risk_level=risk,
                requires_confirmation=req_conf
            ))

# --- Vositalar (Tool Handlers) ---

def handle_system_status(params: Dict[str, Any]) -> Dict[str, Any]:
    cpu_pct = 0.0
    ram_pct = 0.0
    ram_used = 0
    uptime = 0
    
    if psutil:
        try:
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            ram_pct = mem.percent
            ram_used = mem.used // (1024 * 1024)
            uptime = int(time.time() - psutil.boot_time())
        except Exception:
            pass
            
    return {
        "status": "online",
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "uptime_seconds": uptime,
        "cpu_percent": cpu_pct,
        "ram_percent": ram_pct,
        "ram_used_mb": ram_used,
        "timestamp": int(time.time()),
        "agent_version": "9.0.0"
    }

def handle_system_info(params: Dict[str, Any]) -> Dict[str, Any]:
    cpu_count = os.cpu_count() or 1
    cpu_pct = 0.0
    ram_used = 0
    ram_total = 0
    disk_total = 0
    disk_free = 0
    disk_used_pct = 0.0
    
    if psutil:
        try:
            cpu_pct = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            ram_used = mem.used // (1024**3)
            ram_total = mem.total // (1024**3)
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            disk_total = disk.total // (1024**3)
            disk_free = disk.free // (1024**3)
            disk_used_pct = disk.percent
        except Exception:
            pass

    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": cpu_count,
        "cpu_percent": cpu_pct,
        "ram_used_gb": ram_used,
        "ram_total_gb": ram_total,
        "disk_total_gb": disk_total,
        "disk_free_gb": disk_free,
        "disk_used_percent": disk_used_pct
    }

def handle_system_screenshot(params: Dict[str, Any]) -> Dict[str, Any]:
    sandbox = PathSecurityValidator.get_default_sandbox()
    screenshot_dir = os.path.join(sandbox, ".screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    
    # cleanup old
    now = time.time()
    for f in os.listdir(screenshot_dir):
        fp = os.path.join(screenshot_dir, f)
        if os.path.isfile(fp):
            if now - os.path.getmtime(fp) > 3600:
                try:
                    os.remove(fp)
                except:
                    pass

    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if img.width > 1920 or img.height > 1080:
            img.thumbnail((1920, 1080))
            
        fname = f"screenshot_{int(time.time())}.png"
        fpath = os.path.join(screenshot_dir, fname)
        img.save(fpath, "PNG", optimize=True)
        fsize = os.path.getsize(fpath)
        
        if fsize > 2 * 1024 * 1024:
            img = img.convert("RGB")
            fname = f"screenshot_{int(time.time())}.jpg"
            fpath = os.path.join(screenshot_dir, fname)
            img.save(fpath, "JPEG", quality=60)
            fsize = os.path.getsize(fpath)
            
        return {
            "captured": True,
            "format": "png" if fpath.endswith("png") else "jpg",
            "width": img.width,
            "height": img.height,
            "file_size_bytes": fsize,
            "file_path": fpath,
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.warning(f"Screenshot failed: {e}")
        return {
            "captured": False,
            "mock": False,
            "error": str(e)
        }

def handle_app_list(params: Dict[str, Any]) -> Dict[str, Any]:
    if not psutil:
        return {"total_apps": 0, "apps": [], "error": "psutil not available"}
        
    apps = []
    try:
        for p in psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = p.info
                name = str(pinfo.get('name', '')).lower()
                if not name or name in PROTECTED_PROCESSES:
                    continue
                apps.append({
                    "name": pinfo.get('name'),
                    "pid": pinfo.get('pid'),
                    "cpu_percent": pinfo.get('cpu_percent', 0.0),
                    "memory_percent": pinfo.get('memory_percent', 0.0)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception:
        pass
        
    apps = apps[:30]
    return {"total_apps": len(apps), "apps": apps}

def handle_app_launch(params: Dict[str, Any]) -> Dict[str, Any]:
    app_name = params.get("app_name", "").lower()
    if not app_name:
        return {"success": False, "error": "MISSING_APP_NAME"}
        
    exe_name = ALLOWED_APPS.get(app_name)
    if not exe_name:
        return {"success": False, "error": f"APP_NOT_ALLOWED: {app_name}"}
        
    try:
        p = subprocess.Popen([exe_name], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "app_name": app_name, "executable": exe_name, "pid": p.pid, "status": "launched"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_app_close(params: Dict[str, Any]) -> Dict[str, Any]:
    app_name = params.get("app_name")
    pid = params.get("pid")
    
    if not app_name and not pid:
        return {"success": False, "error": "MISSING_APP_NAME_OR_PID"}
        
    if not psutil:
        return {"success": False, "error": "psutil not available"}
        
    try:
        target_p = None
        if pid:
            target_p = psutil.Process(int(pid))
        elif app_name:
            for p in psutil.process_iter(['name', 'pid']):
                if str(p.info.get('name', '')).lower() == app_name.lower():
                    target_p = p
                    break
                    
        if not target_p:
            return {"success": False, "error": "PROCESS_NOT_FOUND"}
            
        p_name = target_p.name().lower()
        if p_name in PROTECTED_PROCESSES:
            return {"success": False, "error": "CANNOT_CLOSE_PROTECTED_PROCESS"}
            
        target_p.terminate()
        return {"success": True, "app_name": target_p.name(), "pid": target_p.pid, "status": "terminated"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_file_list(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path", "")
    if not path:
        path = PathSecurityValidator.get_default_sandbox()
        
    is_valid, resolved, err = PathSecurityValidator.validate_path(path)
    if not is_valid:
        return {"success": False, "error": err}
        
    if not os.path.isdir(resolved):
        return {"success": False, "error": "NOT_A_DIRECTORY"}
        
    items = []
    try:
        entries = os.listdir(resolved)
        for e in entries[:50]:
            ep = os.path.join(resolved, e)
            stat = os.stat(ep)
            items.append({
                "name": e,
                "is_dir": os.path.isdir(ep),
                "size": stat.st_size,
                "modified_at": stat.st_mtime
            })
        return {"success": True, "directory": resolved, "items": items}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_file_read(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path")
    if not path:
        return {"success": False, "error": "MISSING_PATH"}
        
    is_valid, resolved, err = PathSecurityValidator.validate_path(path)
    if not is_valid:
        return {"success": False, "error": err}
        
    if not os.path.isfile(resolved):
        return {"success": False, "error": "FILE_NOT_FOUND"}
        
    try:
        size = os.path.getsize(resolved)
        if size > 65536:
            return {"success": False, "error": "FILE_TOO_LARGE"}
            
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        return {"success": True, "path": resolved, "content": content, "bytes_read": len(content.encode('utf-8')), "encoding": "utf-8"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_file_write(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path")
    content = params.get("content", "")
    if not path:
        return {"success": False, "error": "MISSING_PATH"}
        
    is_valid, resolved, err = PathSecurityValidator.validate_path(path)
    if not is_valid:
        return {"success": False, "error": err}
        
    content_bytes = content.encode('utf-8')
    if len(content_bytes) > 262144:
        return {"success": False, "error": "CONTENT_TOO_LARGE"}
        
    try:
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        tmp_path = resolved + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, resolved)
        return {"success": True, "path": resolved, "bytes_written": len(content_bytes)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_file_delete(params: Dict[str, Any]) -> Dict[str, Any]:
    path = params.get("path")
    if not path:
        return {"success": False, "error": "MISSING_PATH"}
        
    is_valid, resolved, err = PathSecurityValidator.validate_path(path)
    if not is_valid:
        return {"success": False, "error": err}
        
    if not os.path.isfile(resolved):
        return {"success": False, "error": "FILE_NOT_FOUND_OR_IS_DIR"}
        
    try:
        os.remove(resolved)
        return {"success": True, "path": resolved, "deleted": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_network_info(params: Dict[str, Any]) -> Dict[str, Any]:
    hn = socket.gethostname()
    ip = socket.gethostbyname(hn)
    
    interfaces = []
    if psutil and hasattr(psutil, 'net_if_addrs'):
        try:
            if_addrs = psutil.net_if_addrs()
            for name, addrs in if_addrs.items():
                interfaces.append({
                    "name": name,
                    "addresses": [a.address for a in addrs if hasattr(a, 'address')]
                })
        except Exception:
            pass
            
    return {
        "hostname": hn,
        "local_ip": ip,
        "interfaces": interfaces,
        "status": "connected"
    }

def handle_power_restart(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        subprocess.Popen(['shutdown.exe', '/r', '/t', '5'], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "action": "restart", "delay_seconds": 5, "message": "Restart initiated"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_power_shutdown(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        subprocess.Popen(['shutdown.exe', '/s', '/t', '5'], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "action": "shutdown", "delay_seconds": 5, "message": "Shutdown initiated"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_power_sleep(params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        subprocess.Popen(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'], shell=False, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "action": "sleep", "message": "Sleep initiated"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def handle_power_wake(params: Dict[str, Any]) -> Dict[str, Any]:
    mac = params.get("mac_address")
    if not mac:
        return {"success": False, "error": "MISSING_MAC_ADDRESS"}
        
    try:
        from core.v8.wol import create_magic_packet
        packet = create_magic_packet(mac)
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(packet, ('<broadcast>', 9))
            
        return {"success": True, "action": "wake", "mac_address": mac, "message": "Magic packet sent"}
    except ImportError:
        return {"success": False, "error": "WOL module not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}
