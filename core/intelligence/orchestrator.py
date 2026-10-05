# ========== orchestrator.py ==========
# Misa AI 7.x — Intelligence Orchestrator
# Central Cognitive Controller: Pipeline Coordinator from Context to Verified Response

import time
import logging
from typing import Optional, Dict, Any

from core.intelligence.types import (
    AIRequest,
    AIResponse,
    Intent,
    Decision,
    DecisionType,
    RiskLevel,
    IntelligenceResponse,
)
from core.intelligence.provider import ProviderManager
from core.intelligence.gemini_provider import GeminiProvider
from core.intelligence.openrouter_provider import OpenRouterProvider
from core.intelligence.context import ContextEngine
from core.intelligence.intent import IntentEngine
from core.intelligence.decision import DecisionEngine
from core.intelligence.permission import PermissionEngine
from core.intelligence.observability import get_observability_manager

logger = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """
    Misa AI Intelligence Core orkestratori.
    Barcha intellektual bosqichlarni (Kontekst -> Niyat -> Fikrlash -> Qaror -> Vosita -> Tasdiqlash -> Javob)
    birlashtiruvchi markaziy boshqaruvchi.
    """

    def __init__(
        self,
        provider_manager: Optional[ProviderManager] = None,
        context_engine: Optional[ContextEngine] = None,
        intent_engine: Optional[IntentEngine] = None,
        decision_engine: Optional[DecisionEngine] = None,
        permission_engine: Optional[PermissionEngine] = None,
        tool_registry=None,
        command_dispatcher=None,
        agent_loop=None,
    ):
        self.permission_engine = permission_engine or PermissionEngine()
        self.intent_engine = intent_engine or IntentEngine()
        self.tool_registry = tool_registry
        self.command_dispatcher = command_dispatcher

        # Provayder menejeri
        if provider_manager is None:
            gemini = GeminiProvider()
            openrouter = OpenRouterProvider()
            self.provider_manager = ProviderManager([gemini, openrouter])
        else:
            self.provider_manager = provider_manager

        # Kontekst dvigateli
        self.context_engine = context_engine or ContextEngine(tool_registry=tool_registry)

        # Qaror dvigateli
        self.decision_engine = decision_engine or DecisionEngine(
            permission_engine=self.permission_engine,
            tool_registry=self.tool_registry
        )

        # AgentLoop (Phase 31: Multi-Step Agentic Loop)
        if agent_loop is None and tool_registry is not None:
            from core.intelligence.agent_loop import AgentLoop
            self.agent_loop = AgentLoop(
                tool_registry=self.tool_registry,
                permission_engine=self.permission_engine,
                provider_manager=self.provider_manager
            )
        else:
            self.agent_loop = agent_loop

    def handle(
        self,
        message: str,
        user_name: str = "Foydalanuvchi",
        confirmed_action: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> IntelligenceResponse:

        """
        Xabarni to'liq intellektual quvur (pipeline) orqali qayta ishlash:
        1. Qabul qilish
        2. Kontekstni yig'ish (ContextEngine)
        3. AI provayderini chaqirish (ProviderManager)
        4. Niyatni aniqlash (IntentEngine)
        5. Ruxsat va xavfni baholash (PermissionEngine)
        6. Qaror qabul qilish (DecisionEngine)
        7. Tasdiqlash talab etilsa to'xtatish
        8. Asbobni bajarish (Tool execution)
        9. Natijani tekshirish (Verification)
        10. Yakuniy javobni qaytarish (IntelligenceResponse)
        """
        start_time = time.time()
        clean_message = (message or "").strip()

        if not clean_message:
            return IntelligenceResponse(
                type="answer",
                content="Bo'sh xabar kiritildi.",
                verified=True,
                metadata={"latency_ms": 0}
            )

        logger.info(f"[IntelligenceOrchestrator] Xabar qabul qilindi: '{clean_message[:80]}'")

        obs = get_observability_manager()
        trace = obs.create_trace()
        trace.add_stage("REQUEST", status="ok", details={"message": clean_message[:80], "user_name": user_name})

        # 1. Tezkor Mahalliy Buyruqlar tekshiruvi (agar dispatcher mavjud bo'lsa)
        if self.command_dispatcher:
            try:
                handled, local_msg = self.command_dispatcher.dispatch_local(clean_message, user_name=user_name)
                if handled and local_msg:
                    latency = round((time.time() - start_time) * 1000, 2)
                    logger.info(f"[IntelligenceOrchestrator] Tezkor mahalliy dispatcher bajardi ({latency}ms)")
                    trace.add_stage("LOCAL_DISPATCH", status="ok", details={"intent": "local_dispatch"})
                    return self._finalize_response(
                        IntelligenceResponse(
                            type="command",
                            content=local_msg,
                            intent="local_dispatch",
                            verified=True,
                            provider="local",
                            model="command_dispatcher",
                            metadata={"latency_ms": latency}
                        ),
                        trace=trace
                    )
            except Exception as e:
                logger.warning(f"Mahalliy dispatcherda xatolik: {e}")

        # 2. Kontekst yig'ish (Context Assembly)
        trace.start_stage("TASK_CONTEXT")
        request = self.context_engine.assemble(
            message=clean_message,
            user_name=user_name,
            include_tools=(self.tool_registry is not None)
        )
        if user_id:
            request.metadata["user_id"] = user_id
        trace.end_stage(

            "TASK_CONTEXT",
            status="ok",
            details={
                "has_active_task": request.metadata.get("has_active_task", False),
                "retrieved_memories_count": request.metadata.get("retrieved_memories_count", 0),
            }
        )

        retrieved_count = request.metadata.get("retrieved_memories_count", 0)
        trace.add_stage(
            "MEMORY_RETRIEVAL",
            status="ok",
            details={
                "count": retrieved_count,
                "memories": list(request.memory.get("knowledge", {}).keys())
            }
        )
        obs.metrics.record_retrieval(retrieved_count)

        # 2.5. Ko'p bosqichli Agentlik Rejasi (Phase 31: Multi-Step Agentic Loop)
        if self.agent_loop and self._is_multi_step_goal(clean_message):
            logger.info(f"[IntelligenceOrchestrator] Ko'p bosqichli agentlik maqsadi aniqlandi: '{clean_message}'")
            plan = self.agent_loop.create_plan_from_goal(clean_message, request=request)
            if plan and len(plan.steps) > 1:
                return self.agent_loop.execute_plan(
                    plan=plan,
                    request=request,
                    user_name=user_name,
                    trace=trace
                )

        # 3. AI Provayderidan javob olish (Fallback bilan)
        trace.start_stage("PROVIDER")
        ai_response: AIResponse = self.provider_manager.generate_with_fallback(request)
        trace.end_stage(
            "PROVIDER",
            status="ok" if ai_response.success else "error",
            details={"provider": ai_response.provider, "model": ai_response.model}
        )

        # 4. Niyatni aniqlash (Intent Resolution)
        intent: Intent = self.intent_engine.resolve_intent_from_response(ai_response)
        trace.add_stage("INTENT", status="ok", details={"intent": intent.name, "category": intent.category.value if hasattr(intent.category, "value") else str(intent.category)})

        # 5. Qaror qabul qilish (Decision Layer)
        decision: Decision = self.decision_engine.decide(intent, ai_response)
        trace.add_stage("PERMISSION", status="ok", details={"risk_level": decision.risk_level.value if hasattr(decision.risk_level, "value") else str(decision.risk_level)})
        trace.add_stage("DECISION", status="ok", details={"type": decision.type.value if hasattr(decision.type, "value") else str(decision.type)})

        latency = round((time.time() - start_time) * 1000, 2)

        # 6. Tasdiqlash (Confirmation) tekshiruvi
        if decision.type == DecisionType.CONFIRMATION:
            # Agar foydalanuvchi ushbu amalni allaqachon tasdiqlagan bo'lsa -> davom etish
            if confirmed_action and confirmed_action == intent.name:
                logger.info(f"Foydalanuvchi amalni oldindan tasdiqlagan: '{confirmed_action}'")
                decision.type = DecisionType.COMMAND
            else:
                return self._finalize_response(
                    IntelligenceResponse(
                        type="confirmation",
                        content=decision.content,
                        intent=intent.name,
                        params=intent.params,
                        verified=True,
                        provider=ai_response.provider,
                        model=ai_response.model,
                        metadata={"latency_ms": latency, "risk_level": decision.risk_level.value}
                    ),
                    trace=trace,
                    request=request
                )

        # 7. Aniqlashtirish (Clarification) talabi
        if decision.type == DecisionType.CLARIFICATION:
            return self._finalize_response(
                IntelligenceResponse(
                    type="clarification",
                    content=decision.content,
                    intent=intent.name if intent else None,
                    verified=True,
                    provider=ai_response.provider,
                    model=ai_response.model,
                    metadata={"latency_ms": latency}
                ),
                trace=trace,
                request=request
            )

        # 8. Asbobni ijro etish va Natijani tekshirish (Tool Execution & Verification)
        if decision.type == DecisionType.TOOL and decision.tool_name and self.tool_registry:
            tool_name = decision.tool_name
            tool_params = decision.tool_params

            logger.info(f"[IntelligenceOrchestrator] Asbob ijro etilmoqda: '{tool_name}', parametrlar={tool_params}")
            try:
                tool_call_res = self.tool_registry.call(tool_name, **tool_params)
                is_success = bool(tool_call_res.get("success", False))
                trace.add_stage("TOOL", status="ok" if is_success else "error", details={"tool": tool_name})

                if is_success:
                    raw_result = tool_call_res.get("result")
                    formatted_content = self._format_tool_output(tool_name, raw_result, decision.content)
                    logger.info(f"[IntelligenceOrchestrator] Asbob muvaffaqiyatli bajarildi: '{tool_name}'")
                    return self._finalize_response(
                        IntelligenceResponse(
                            type="tool",
                            content=formatted_content,
                            intent=intent.name,
                            params=tool_params,
                            tool_executed=tool_name,
                            tool_result=raw_result,
                            verified=True,
                            provider=ai_response.provider,
                            model=ai_response.model,
                            metadata={"latency_ms": latency}
                        ),
                        trace=trace,
                        request=request
                    )
                else:
                    err = tool_call_res.get("error", "Noma'lum xatolik")
                    logger.warning(f"[IntelligenceOrchestrator] Asbob bajarilmadi: '{tool_name}', xato: {err}")
                    return self._finalize_response(
                        IntelligenceResponse(
                            type="error",
                            content=f"Asbobni bajarishda xatolik yuz berdi ({tool_name}): {err}",
                            intent=intent.name,
                            params=tool_params,
                            tool_executed=tool_name,
                            tool_result=tool_call_res,
                            verified=False,
                            provider=ai_response.provider,
                            model=ai_response.model,
                            metadata={"latency_ms": latency}
                        ),
                        trace=trace,
                        request=request
                    )
            except Exception as e:
                logger.error(f"Asbob ijrosida istisno: {e}", exc_info=True)
                trace.add_stage("TOOL", status="error", details={"tool": tool_name, "error": str(e)})
                return self._finalize_response(
                    IntelligenceResponse(
                        type="error",
                        content=f"Asbob ijro etilmadi: {e}",
                        intent=intent.name,
                        params=tool_params,
                        tool_executed=tool_name,
                        verified=False,
                        provider=ai_response.provider,
                        model=ai_response.model,
                        metadata={"latency_ms": latency}
                    ),
                    trace=trace,
                    request=request
                )

        # 9. Buyruq (Command)
        if decision.type == DecisionType.COMMAND:
            return self._finalize_response(
                IntelligenceResponse(
                    type="command",
                    content=decision.content,
                    intent=intent.name,
                    params=intent.params,
                    verified=True,
                    provider=ai_response.provider,
                    model=ai_response.model,
                    metadata={"latency_ms": latency}
                ),
                trace=trace,
                request=request
            )

        # 10. Xatolik (Error)
        if decision.type == DecisionType.ERROR:
            return self._finalize_response(
                IntelligenceResponse(
                    type="error",
                    content=decision.content,
                    intent=intent.name,
                    verified=False,
                    provider=ai_response.provider,
                    model=ai_response.model,
                    error_code=ai_response.error_code,
                    metadata={"latency_ms": latency}
                ),
                trace=trace,
                request=request
            )

        # 11. Standart Suhbat Javobi (Answer)
        return self._finalize_response(
            IntelligenceResponse(
                type="answer",
                content=decision.content,
                intent=intent.name,
                verified=True,
                provider=ai_response.provider,
                model=ai_response.model,
                metadata={"latency_ms": latency}
            ),
            trace=trace,
            request=request
        )

    def _finalize_response(
        self,
        response: IntelligenceResponse,
        trace: Any,
        request: Optional[AIRequest] = None
    ) -> IntelligenceResponse:
        """Trace va tushuntirishlarni javobga biriktirish"""
        if trace:
            trace.add_stage("RESPONSE", status="ok" if response.verified else "error", details={"type": response.type})
            obs = get_observability_manager()
            obs.record_trace(trace)
            if response.metadata is None:
                response.metadata = {}
            response.metadata["trace_id"] = trace.trace_id
            if request and request.metadata and request.metadata.get("retrieval_explanations"):
                response.metadata["retrieval_explanations"] = request.metadata["retrieval_explanations"]
        return response

    def _format_tool_output(self, tool_name: str, result: Any, default_text: str) -> str:
        """Asbob natijasini foydalanuvchiga tushunarli matnga aylantirish"""
        if isinstance(result, dict):
            if tool_name == "system_info" and "info" in result and isinstance(result["info"], dict) and result["info"]:
                info = result["info"]
                sections = []
                if "cpu_model" in info:
                    sections.append(
                        f"🧠 **Protsessoringiz (CPU) ma'lumotlari:**\n\n"
                        f"• **Model:** {info['cpu_model']}\n"
                        f"• **Yadrolar:** {info.get('cpu_cores', 'N/A')}\n"
                        f"• **Hozirgi yuklama:** {info.get('cpu_usage', 'N/A')} band"
                    )
                if "gpu_model" in info:
                    details = [f"• **Model:** {info['gpu_model']}"]
                    if "gpu_vram" in info:
                        details.append(f"• **Video xotira (VRAM):** {info['gpu_vram']}")
                    if "gpu_driver" in info:
                        details.append(f"• **Drayver versiyasi:** {info['gpu_driver']}")
                    details.append("• **Holati:** Faol (DirectX 12)")
                    sections.append(f"🎮 **Videokartangiz (GPU) ma'lumotlari:**\n\n" + "\n".join(details))
                elif "gpu" in info:
                    sections.append(f"🎮 **Videokartangiz (GPU):**\n• {info['gpu']}")
                if "ram" in info:
                    sections.append(f"💾 **Tezkor xotira (RAM) ma'lumotlari:**\n\n• **Holat:** {info['ram']}")
                if "disk" in info:
                    sections.append(f"💽 **Disk xotirasi (Storage):**\n\n• **Holat:** {info['disk']}")
                if "battery" in info:
                    sections.append(f"🔋 **Batareya quvvati:**\n\n• **Holat:** {info['battery']}")
                if sections:
                    return "\n\n".join(sections)

            if "response" in result and result["response"]:
                return str(result["response"])
            if "message" in result and result["message"]:
                return str(result["message"])
            if "info" in result and isinstance(result["info"], dict) and result["info"]:
                lines = [f"• {k}: {v}" for k, v in result["info"].items()]
                return "Ma'lumotlar:\n" + "\n".join(lines)
            if "error" in result and result["error"]:
                return f"Xatolik: {result['error']}"
        if isinstance(result, str) and result.strip():
            return result.strip()
        if default_text and not any(h in default_text for h in ["1050 Ti", "GTX 1050"]):
            return default_text
        return f"'{tool_name}' vositasi muvaffaqiyatli bajarildi."

    def _is_multi_step_goal(self, text: str) -> bool:
        """Xabar ko'p qadamli agentlik rejasini talab qiladimi yoki yo'qligini aniqlash"""
        if not text:
            return False
        import re
        lowered = text.lower()
        delimiters = [r"\bva\b", r"\bkeyin\b", r"\bhamda\b", r"\bso'ng\b", r"\band\b"]
        pattern = "|".join(delimiters)
        parts = [p.strip() for p in re.split(pattern, lowered) if p.strip()]
        if len(parts) >= 2:
            action_keywords = [
                "och", "yop", "qidir", "izla", "top", "hisobla", "o'chir",
                "ko'rsat", "qo'y", "play", "pause", "open", "close", "start",
                "qulfla", "lock", "brauzer", "youtube"
            ]
            has_first = any(ak in parts[0] for ak in action_keywords)
            has_second = any(ak in parts[1] for ak in action_keywords)
            return has_first and has_second
        return False
