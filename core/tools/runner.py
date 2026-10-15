# ========== runner.py ==========
# Misa AI 7.x — Safe Tool Execution Runner & Pipeline
# Timeout Enforcement, Health Tracking, Permission Integration & Normalization

import time
import logging
import concurrent.futures
from typing import Any, Callable, Dict, Optional

from core.intelligence.observability import redact_sensitive_data
from core.intelligence.permission import PermissionEngine
from core.intelligence.types import RiskLevel
from core.tools.contract import ToolContract2, ToolErrorCode, ToolHealth, ToolResult
from core.tools.validator import ParameterValidator

from core.tools.security_policy import AuthoritativeSecurityPolicy, get_security_policy

logger = logging.getLogger(__name__)


class SafeToolRunner:
    """
    Asboblarni xavfsiz, belgilangan vaqt chegarasi (timeout) va ruxsatlar bilan bajarish dvigateli.
    Noma'lum yoki nosoz asboblar tizimni to'xtatib qo'yishining oldini oladi.
    """

    def __init__(
        self,
        permission_engine: Optional[PermissionEngine] = None,
        security_policy: Optional[AuthoritativeSecurityPolicy] = None
    ):
        self.permission_engine = permission_engine or PermissionEngine()
        self.security_policy = security_policy or get_security_policy()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="tool_worker")

    def execute_tool(
        self,
        tool: ToolContract2,
        params: Dict[str, Any],
        trace: Optional[Any] = None,
        bypass_permission: bool = False,
        confirmation_token: Optional[str] = None
    ) -> ToolResult:
        """
        To'liq zanjir bo'yicha asbobni ishga tushirish:
        VALIDATE -> PERMISSION -> TIMEOUT RUN -> NORMALIZE -> HEALTH UPDATE
        """
        start_time = time.time()
        tool_name = tool.name

        clean_input_params = dict(params) if isinstance(params, dict) else (params or {})
        if not confirmation_token and isinstance(clean_input_params, dict):
            confirmation_token = clean_input_params.pop("_confirmation_token", None) or clean_input_params.pop("confirmation_token", None)
        elif isinstance(clean_input_params, dict):
            clean_input_params.pop("_confirmation_token", None)
            clean_input_params.pop("confirmation_token", None)

        safe_params = redact_sensitive_data(clean_input_params)

        # 1. Salomatlik holatini tekshirish
        if tool.health == ToolHealth.DISABLED:
            dur = (time.time() - start_time) * 1000.0
            if trace:
                trace.add_stage("TOOL_BLOCKED", status="disabled", details={"tool": tool_name, "reason": "Tool is DISABLED"})
            return ToolResult(
                success=False,
                code=ToolErrorCode.TOOL_UNAVAILABLE,
                error=f"Asbob '{tool_name}' ma'muriy ravishda o'chirilgan (DISABLED)",
                duration_ms=dur,
                tool=tool_name,
                version=tool.version
            )

        if tool.health == ToolHealth.UNAVAILABLE:
            dur = (time.time() - start_time) * 1000.0
            if trace:
                trace.add_stage("TOOL_BLOCKED", status="unavailable", details={"tool": tool_name, "reason": "Tool is UNAVAILABLE"})
            return ToolResult(
                success=False,
                code=ToolErrorCode.TOOL_UNAVAILABLE,
                error=f"Asbob '{tool_name}' ayni paytda ishlamayapti (UNAVAILABLE)",
                duration_ms=dur,
                tool=tool_name,
                version=tool.version
            )

        # 2. Parametrlarni qat'iy tekshirish (VALIDATE)
        is_valid, err_msg, err_code, clean_params = ParameterValidator.validate(tool, clean_input_params, strict=True)
        if clean_params and isinstance(clean_params, dict):
            clean_params.pop("_confirmation_token", None)
            clean_params.pop("confirmation_token", None)
        if not is_valid:
            dur = (time.time() - start_time) * 1000.0
            logger.warning(f"[SafeToolRunner] Validatsiya xatoligi: '{tool_name}' - {err_msg}")
            if trace:
                trace.add_stage("TOOL_VALIDATION_FAILED", status="validation_error", details={
                    "tool": tool_name,
                    "error": err_msg,
                    "params": safe_params
                })
            return ToolResult(
                success=False,
                code=err_code or ToolErrorCode.VALIDATION_ERROR,
                error=err_msg,
                duration_ms=dur,
                tool=tool_name,
                version=tool.version
            )

        # 3. Vakolatli xavfsizlik va tasdiqlash siyosati (AUTHORITATIVE SECURITY POLICY)
        if not bypass_permission:
            decision = self.security_policy.evaluate(
                tool_name=tool_name,
                tool_obj=tool,
                params=clean_params,
                confirmation_token=confirmation_token
            )
            if decision.requires_confirmation and not decision.allowed:
                dur = (time.time() - start_time) * 1000.0
                risk_str = decision.risk_level.value if hasattr(decision.risk_level, "value") else str(decision.risk_level)
                logger.info(f"[SafeToolRunner] '{tool_name}' uchun tasdiqlash talab etiladi ({risk_str} risk): {decision.reason}")
                if trace:
                    trace.add_stage("TOOL_PERMISSION_CHECKED", status="requires_confirmation", details={
                        "tool": tool_name,
                        "risk": risk_str,
                        "prompt": decision.prompt,
                        "challenge_token": decision.challenge_token
                    })
                return ToolResult(
                    success=False,
                    code=ToolErrorCode.PERMISSION_DENIED,
                    message=decision.prompt or f"'{tool_name}' amalini bajarish uchun tasdiqlash talab etiladi",
                    error="CONFIRMATION_REQUIRED",
                    duration_ms=dur,
                    tool=tool_name,
                    version=tool.version,
                    metadata={
                        "requires_confirmation": True,
                        "prompt": decision.prompt,
                        "risk_level": risk_str,
                        "challenge_token": decision.challenge_token,
                        "action_class": decision.action_class.value if hasattr(decision.action_class, "value") else str(decision.action_class)
                    }
                )

        if trace:
            trace.add_stage("TOOL_STARTED", status="ok", details={"tool": tool_name, "params": redact_sensitive_data(clean_params)})

        # 4. Vaqt chegarasi (TIMEOUT) bilan ijro etish
        timeout = tool.timeout if tool.timeout and tool.timeout > 0 else 10.0
        try:
            future = self._executor.submit(tool.function, **clean_params)
            raw_result = future.result(timeout=timeout)
            dur = (time.time() - start_time) * 1000.0

            # Natijani normalizatsiya qilish (NORMALIZE)
            if isinstance(raw_result, ToolResult):
                norm_result = raw_result
                norm_result.duration_ms = dur
                norm_result.tool = tool_name
            elif isinstance(raw_result, dict):
                norm_result = ToolResult.from_legacy_dict(raw_result, tool_name=tool_name, duration_ms=dur)
            else:
                norm_result = ToolResult(
                    success=True,
                    data=raw_result,
                    message=str(raw_result)[:200],
                    duration_ms=dur,
                    tool=tool_name,
                    version=tool.version
                )

            # Salomatlikni yangilash
            if norm_result.success:
                tool.mark_success(dur)
                if trace:
                    trace.add_stage("TOOL_COMPLETED", status="ok", details={
                        "tool": tool_name,
                        "duration_ms": dur,
                        "success": True
                    })
            else:
                tool.mark_failure(norm_result.error or "Tool returned failure", dur)
                if trace:
                    trace.add_stage("TOOL_FAILED", status="error", details={
                        "tool": tool_name,
                        "error": norm_result.error,
                        "duration_ms": dur
                    })

            return norm_result

        except concurrent.futures.TimeoutError:
            dur = (time.time() - start_time) * 1000.0
            tool.mark_failure(f"Timeout {timeout}s", dur)
            logger.error(f"[SafeToolRunner] Asbob '{tool_name}' vaqt chegarasidan oshdi ({timeout}s)")
            if trace:
                trace.add_stage("TOOL_TIMEOUT", status="timeout", details={"tool": tool_name, "timeout": timeout, "duration_ms": dur})
            return ToolResult(
                success=False,
                code=ToolErrorCode.TIMEOUT,
                error=f"Asbob '{tool_name}' belgilangan vaqt chegarasida ({timeout} soniya) javob bermadi",
                duration_ms=dur,
                tool=tool_name,
                version=tool.version
            )

        except Exception as exc:
            dur = (time.time() - start_time) * 1000.0
            tool.mark_failure(str(exc), dur)
            logger.error(f"[SafeToolRunner] Asbob '{tool_name}' ijrosida istisno: {exc}")
            if trace:
                trace.add_stage("TOOL_FAILED", status="execution_error", details={"tool": tool_name, "error": str(exc), "duration_ms": dur})
            return ToolResult(
                success=False,
                code=ToolErrorCode.EXECUTION_ERROR,
                error=f"Asbob '{tool_name}' ijrosida xatolik: {str(exc)}",
                duration_ms=dur,
                tool=tool_name,
                version=tool.version
            )


# Global singleton
_tool_runner: Optional[SafeToolRunner] = None


def get_tool_runner() -> SafeToolRunner:
    global _tool_runner
    if _tool_runner is None:
        _tool_runner = SafeToolRunner()
    return _tool_runner
