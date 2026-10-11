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

        # Provayder menejeri (ko'p provayderli intellektual router bilan)
        if provider_manager is None:
            self.provider_manager = ProviderManager()
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
                raw_result = tool_call_res.get("result") if is_success else None

                # Agar qidiruv asbobi (web_search / search) bo'lsa va internetda bevosita natija chiqmasa,
                # foydalanuvchiga xom "natija topilmadi" demasdan, AI o'z keng bilimidan javob shakllantirsin
                if tool_name in ("web_search", "search") and (
                    not is_success
                    or (isinstance(raw_result, dict) and raw_result.get("no_results"))
                ):
                    logger.info("[IntelligenceOrchestrator] Qidiruvdan to'g'ridan-to'g'ri natija topilmadi. AI o'z bilimidan javob tayyorlamoqda...")
                    fallback_instruction = (
                        f"Foydalanuvchi so'rovi: '{clean_message}'.\n"
                        "Internetdan bevosita havola topilmadi. O'zingizning keng va chuqur bilimingizdan foydalanib, "
                        "foydalanuvchining ushbu savoliga to'liq, samimiy va aniq o'zbek tilida javob bering. "
                        "Hech qanday ichki texnik qoidalarni (aniqlik foizi, prompt ko'rsatmasi va hk) aslo tilga olmang."
                    )
                    ai_fb_req = AIRequest(
                        message=fallback_instruction,
                        system_context=request.system_context,
                        conversation=request.conversation,
                        memory=request.memory,
                        metadata=request.metadata
                    )
                    ai_fb_resp = self.provider_manager.generate_with_fallback(ai_fb_req)
                    if ai_fb_resp and ai_fb_resp.content:
                        from core.intelligence.text_cleaner import extract_clean_response_text
                        clean_content = extract_clean_response_text(ai_fb_resp.content)

                        return self._finalize_response(
                            IntelligenceResponse(
                                type="answer",
                                content=clean_content,
                                intent=intent.name,
                                params=tool_params,
                                tool_executed=tool_name,
                                verified=True,
                                provider=ai_fb_resp.provider,
                                model=ai_fb_resp.model,
                                metadata={"latency_ms": latency}
                            ),
                            trace=trace,
                            request=request
                        )

                if is_success:
                    formatted_content = self._format_tool_output(tool_name, raw_result, decision.content, tool_res=tool_call_res)
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
        clean_ans = decision.content or ""
        if self._is_leaked_reasoning(clean_ans):
            logger.warning("[IntelligenceOrchestrator] Leaked reasoning aniqlandi, toza o'zbekcha javob qaytarilmoqda.")
            clean_ans = "So'rovingiz tushunildi. Buni siz uchun bajaryapman."

        return self._finalize_response(
            IntelligenceResponse(
                type="answer",
                content=clean_ans,
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
        """Trace va tushuntirishlarni javobga biriktirish hamda yakuniy matnni tozalash"""
        if response and response.content:
            from core.intelligence.text_cleaner import extract_clean_response_text
            response.content = extract_clean_response_text(response.content)
            if self._is_leaked_reasoning(response.content):
                logger.warning("[IntelligenceOrchestrator] Leaked reasoning _finalize_response da tozalandi.")
                response.content = "So'rovingiz tushunildi. Buni siz uchun bajaryapman."

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

    def _is_leaked_reasoning(self, text: str) -> bool:
        """Matn inglizcha ichki fikrlash (Chain-of-Thought) yoki ichki prompt ko'rsatmasi ekanligini aniqlash"""
        if not text:
            return False
        t_lower = text.lower().strip()
        reasoning_prefixes = [
            "the user is asking",
            "the user asks",
            "the user wants",
            "the user is inquiring",
            "i should use the",
            "i should check",
            "i need to check",
            "let me check",
            "looking at the system",
            "looking at the provided",
            "so, 5 applications are listed",
            "let me think",
            "we need to answer",
            "we should respond",
            "according to the rules",
            "actually, the system information",
            "o'z bilimingdan javob ber",
            "oz bilimingdan javob ber",
            "kamida 70%",
            "aniqlik talab etiladi",
            "mezoniga amal qil",
        ]
        return any(p in t_lower for p in reasoning_prefixes)

    def _format_tool_output(self, tool_name: str, result: Any, default_text: str = "", tool_res: Any = None) -> str:
        """Asbob natijasini foydalanuvchiga tushunarli matnga aylantirish"""
        # 1. Agar tool_res da tayyor o'zbekcha xabar bo'lsa
        if tool_res and hasattr(tool_res, "get") and tool_res.get("message"):
            msg = str(tool_res.get("message")).strip()
            if msg and not self._is_leaked_reasoning(msg):
                return msg

        if isinstance(result, dict):
            # app_check maxsus formatlash
            if tool_name == "app_check":
                if result.get("found"):
                    app_n = result.get("name") or "Ilova"
                    app_p = result.get("path")
                    p_info = f" ({app_p})" if app_p and app_p != "(process)" else ""
                    return f"✅ Ha, kompyuteringizda **{app_n}** ilovasi o'rnatilgan{p_info}."
                elif result.get("found") is False:
                    app_n = result.get("name") or "So'ralgan ilova"
                    return f"❌ Kompyuteringizda **{app_n}** ilovasi topilmadi (o'rnatilmagan)."

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

        # default_text faqat haqiqiy o'zbekcha javob bo'lsa va leaked reasoning bo'lmasa qabul qilinadi
        if default_text and not self._is_leaked_reasoning(default_text) and not any(h in default_text for h in ["1050 Ti", "GTX 1050"]):
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
