# ========== contract.py ==========
# Misa AI 7.x — Tool Contract 2.0 & Normalized Data Structures
# Standardized Tool Metadata, Health, Error Codes & ToolResult

import time
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from core.intelligence.types import RiskLevel


class ToolHealth(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    DISABLED = "disabled"


class ToolErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INVALID_RESULT = "INVALID_RESULT"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass
class ToolResult:
    """
    Standartlashtirilgan Tool natijasi.
    Barcha vositalar (o'rnatilgan va plaginlar) shu formatda natija qaytaradi.
    Eski kodlar uchun dict kabi murojaat qilish imkoniyati saqlanadi.
    """
    success: bool
    code: Optional[ToolErrorCode] = None
    message: str = ""
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    tool: str = ""
    version: str = "2.0.0"
    trace_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def result(self) -> Any:
        return self.data

    def to_dict(self) -> Dict[str, Any]:
        """Observability va API uchun maxfiy ma'lumotlari tozalangan dict"""
        from core.intelligence.observability import redact_sensitive_data

        raw = {
            "success": self.success,
            "code": self.code.value if isinstance(self.code, ToolErrorCode) else (str(self.code) if self.code else None),
            "message": self.message,
            "data": self.data,
            "result": self.data,  # Backward compatibility for legacy {"result": ...}
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "tool": self.tool,
            "version": self.version,
            "trace_id": self.trace_id,
            "metadata": self.metadata,
        }
        return redact_sensitive_data(raw)

    # Legacy dict interface compatibility (__getitem__, get, __contains__)
    def __getitem__(self, item: str) -> Any:
        d = self.to_dict()
        if item in d:
            return d[item]
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        return self.to_dict().get(item, default)

    def __contains__(self, item: str) -> bool:
        return item in self.to_dict()

    @classmethod
    def from_legacy_dict(cls, data: Dict[str, Any], tool_name: str = "", duration_ms: float = 0.0) -> "ToolResult":
        """Eski dict formatidagi natijani ToolResult ga aylantirish"""
        if not isinstance(data, dict):
            return cls(
                success=True,
                data=data,
                message=str(data)[:200],
                tool=tool_name,
                duration_ms=duration_ms
            )

        success = bool(data.get("success", True if "error" not in data else False))
        error = data.get("error")
        code = None
        if not success or error:
            code = ToolErrorCode.EXECUTION_ERROR

        message = data.get("message", "")
        # Extract payload
        if "result" in data:
            extra = {k: v for k, v in data.items() if k not in ("success", "error", "message", "result")}
            if isinstance(data["result"], dict):
                result_data = {**data["result"], **extra} if extra else data["result"]
            elif extra:
                result_data = {"result": data["result"], **extra}
            else:
                result_data = data["result"]
        else:
            result_data = {k: v for k, v in data.items() if k not in ("success", "error", "message")}
        if not result_data and "message" in data:
            result_data = {"message": message}

        return cls(
            success=success,
            code=code,
            message=str(message),
            data=result_data,
            error=str(error) if error else None,
            duration_ms=duration_ms,
            tool=tool_name
        )


@dataclass
class ToolContract2:
    """
    Tool Contract 2.0.
    Misa AI dagi barcha instrumentlar uchun kengaytirilgan kontrakt.
    Mavjud `Tool` bilan to'liq orqaga mos.
    """
    name: str
    description: str
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    function: Optional[Callable] = None
    category: str = "general"
    version: str = "2.0.0"
    capabilities: List[str] = field(default_factory=list)
    required_parameters: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    timeout: float = 10.0
    idempotent: bool = True
    destructive: bool = False
    requires_confirmation: bool = False
    aliases: List[str] = field(default_factory=list)
    health: ToolHealth = ToolHealth.AVAILABLE
    
    # Ishlash statistikasi va telemetriya
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    last_duration_ms: float = 0.0
    last_executed: Optional[str] = None
    last_error: Optional[str] = None

    def __post_init__(self):
        # Agar required_parameters ko'rsatilmagan bo'lsa, parameters dict ichidan avtomatik aniqlash
        if not self.required_parameters and self.parameters:
            self.required_parameters = [
                k for k, v in self.parameters.items()
                if isinstance(v, dict) and v.get("required") is True
            ]
        # Agar capabilities bo'sh bo'lsa, vosita nomidan boshlang'ich qobiliyat hosil qilish
        if not self.capabilities:
            self.capabilities = [self.name.lower().replace("-", "_")]

        # Ensure risk_level is enum
        if isinstance(self.risk_level, str):
            try:
                self.risk_level = RiskLevel(self.risk_level.lower())
            except ValueError:
                self.risk_level = RiskLevel.LOW

        # Ensure health is enum
        if isinstance(self.health, str):
            try:
                self.health = ToolHealth(self.health.lower())
            except ValueError:
                self.health = ToolHealth.AVAILABLE

    def to_dict(self) -> Dict[str, Any]:
        """AI prompt va API katalogi uchun tavsif"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "capabilities": list(self.capabilities),
            "parameters": {
                k: {
                    "type": v.get("type", "string") if isinstance(v, dict) else "string",
                    "description": v.get("description", "") if isinstance(v, dict) else "",
                    "required": v.get("required", False) if isinstance(v, dict) else False,
                }
                for k, v in self.parameters.items()
            },
            "required_parameters": list(self.required_parameters),
            "risk_level": self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level),
            "timeout": self.timeout,
            "idempotent": self.idempotent,
            "destructive": self.destructive,
            "requires_confirmation": self.requires_confirmation,
            "aliases": list(self.aliases),
            "health": self.health.value if isinstance(self.health, ToolHealth) else str(self.health),
            "metrics": {
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "last_duration_ms": round(self.last_duration_ms, 2),
                "last_executed": self.last_executed,
            }
        }

    def mark_success(self, duration_ms: float):
        """Muvaffaqiyatli bajarilishni qayd qilish"""
        self.success_count += 1
        self.consecutive_failures = 0
        self.last_duration_ms = duration_ms
        self.last_executed = datetime.datetime.now().isoformat()
        if self.health == ToolHealth.DEGRADED:
            # Tiklanish
            self.health = ToolHealth.AVAILABLE

    def mark_failure(self, error: str, duration_ms: float = 0.0):
        """Xatolikni qayd qilish va salomatlikni yangilash"""
        self.failure_count += 1
        self.consecutive_failures += 1
        self.last_duration_ms = duration_ms
        self.last_executed = datetime.datetime.now().isoformat()
        self.last_error = error
        if self.consecutive_failures >= 3 and self.health == ToolHealth.AVAILABLE:
            self.health = ToolHealth.DEGRADED

    def call(self, **kwargs) -> ToolResult:
        """
        Tool ni chaqirish (SafeToolRunner bilan birgalikda ishlatiladi).
        Standart chaqiruvda to'g'ridan-to'g'ri bajarish va ToolResult qaytarish.
        """
        from core.tools.runner import get_tool_runner
        return get_tool_runner().execute_tool(self, kwargs)
