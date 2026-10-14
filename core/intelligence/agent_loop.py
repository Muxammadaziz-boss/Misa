# ========== agent_loop.py ==========
# Misa AI 7.x — Agentic Multi-Step Intelligence Loop
# PLAN → ACT → OBSERVE → VERIFY → CONTINUE → COMPLETE
# Deterministic, Bounded, Permission-Aware & Observability-Integrated

import re
import time
import json
import uuid
import logging
import datetime
from threading import RLock
from typing import Optional, Dict, Any, List, Tuple, Callable

from core.intelligence.types import (
    AgentState,
    PlanStatus,
    StepStatus,
    VerificationStatus,
    FailureCategory,
    RiskLevel,
    VerificationResult,
    StepResult,
    PlanStep,
    AgentPlan,
    AgentExecutionState,
    AIRequest,
    AIResponse,
    IntelligenceResponse,
)
from core.intelligence.verifier import AgentVerifier
from core.intelligence.permission import PermissionEngine
from core.intelligence.observability import (
    ContextTrace,
    get_observability_manager,
    redact_sensitive_data,
)
from core.intelligence.task_context import TaskContextManager, get_task_context_manager
from core.intelligence.planner import (
    GoalDecomposer,
    DependencyGraph,
    PlanOptimizer,
    PlanValidator,
    ReplanningEngine,
)

logger = logging.getLogger(__name__)


class AgentLoop:
    """
    Misa AI Agentik Ko'p Bosqichli Boshqaruv Dvigateli.
    PLAN → ACT → OBSERVE → VERIFY → CONTINUE siklini chegaralangan,
    xavfsiz, deterministik va to'liq kuzatiladigan tarzda boshqaradi.
    """

    # Qat'iy Xavfsizlik Chegaralari
    MAX_STEPS = 8
    MAX_RETRIES_PER_STEP = 1
    MAX_TOTAL_EXECUTION_TIME = 60.0  # soniya

    # Qayta urinish taqiqlangan (non-idempotent/destructive) amallar
    NON_IDEMPOTENT_ACTIONS = {
        "shutdown",
        "restart",
        "system_shutdown",
        "delete_all_reminders",
        "clear_memory",
        "delete_plugin",
        "destructive_file_op",
        "process_kill",
        "scheduler_remove",
        "send_message",
    }

    def __init__(
        self,
        tool_registry=None,
        permission_engine: Optional[PermissionEngine] = None,
        verifier: Optional[AgentVerifier] = None,
        provider_manager=None,
        task_context_manager: Optional[TaskContextManager] = None,
        event_emitter: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        self.tool_registry = tool_registry
        self.permission_engine = permission_engine or PermissionEngine()
        self.verifier = verifier or AgentVerifier(tool_registry=tool_registry)
        self.provider_manager = provider_manager
        self.task_context_manager = task_context_manager or get_task_context_manager()
        self.event_emitter = event_emitter

        # Planning & Reasoning 2.0 Subsystems
        self.goal_decomposer = GoalDecomposer(
            tool_registry=tool_registry,
            provider_manager=provider_manager,
            permission_engine=self.permission_engine,
        )
        self.dependency_graph = DependencyGraph()
        self.plan_optimizer = PlanOptimizer(
            task_context_manager=self.task_context_manager
        )
        self.plan_validator = PlanValidator(
            tool_registry=tool_registry,
            max_steps=self.MAX_STEPS
        )
        self.replanning_engine = ReplanningEngine(
            tool_registry=tool_registry,
            provider_manager=provider_manager,
            max_replans=2
        )

        self._lock = RLock()
        self._state: AgentState = AgentState.IDLE
        self._active_plan: Optional[AgentPlan] = None
        self._abort_requested: bool = False
        self._execution_state: AgentExecutionState = AgentExecutionState()
        self._paused_step_id: Optional[str] = None

    # ========================================================
    # STATE MACHINE MANAGEMENT
    # ========================================================

    @property
    def state(self) -> AgentState:
        with self._lock:
            return self._state

    def _transition_to(self, new_state: AgentState):
        """Holat o'tishini qat'iy tekshirish va xavfsiz o'zgartirish"""
        with self._lock:
            curr = self._state
            if curr == new_state:
                return

            valid_transitions = {
                AgentState.IDLE: {AgentState.PLANNING, AgentState.ABORTED},
                AgentState.PLANNING: {AgentState.VALIDATING, AgentState.FAILED, AgentState.ABORTED},
                AgentState.VALIDATING: {
                    AgentState.EXECUTING,
                    AgentState.WAITING_CONFIRMATION,
                    AgentState.FAILED,
                    AgentState.ABORTED
                },
                AgentState.EXECUTING: {
                    AgentState.OBSERVING,
                    AgentState.WAITING_CONFIRMATION,
                    AgentState.FAILED,
                    AgentState.ABORTED
                },
                AgentState.OBSERVING: {AgentState.VERIFYING, AgentState.FAILED, AgentState.ABORTED},
                AgentState.VERIFYING: {
                    AgentState.EXECUTING,
                    AgentState.WAITING_CONFIRMATION,
                    AgentState.COMPLETED,
                    AgentState.FAILED,
                    AgentState.ABORTED
                },
                AgentState.WAITING_CONFIRMATION: {
                    AgentState.EXECUTING,
                    AgentState.ABORTED,
                    AgentState.FAILED
                },
                AgentState.COMPLETED: {AgentState.IDLE, AgentState.PLANNING},
                AgentState.FAILED: {AgentState.IDLE, AgentState.PLANNING},
                AgentState.ABORTED: {AgentState.IDLE, AgentState.PLANNING},
            }

            allowed = valid_transitions.get(curr, set())
            if new_state not in allowed:
                err = f"Noqonuniy holat o'tishi: {curr} -> {new_state}"
                logger.error(err)
                raise ValueError(err)

            self._state = new_state
            self._execution_state.state = new_state
            logger.debug(f"[AgentLoop] Holat o'zgardi: {curr} -> {new_state}")

    def get_execution_state(self) -> AgentExecutionState:
        """Joriy ijro holatini olish"""
        with self._lock:
            return self._execution_state

    # ========================================================
    # PLAN GENERATION & PARSING
    # ========================================================

    def create_plan_from_goal(
        self,
        goal: str,
        request: Optional[AIRequest] = None
    ) -> AgentPlan:
        """
        Foydalanuvchi maqsadidan AgentPlan 2.0 yaratish.
        GoalDecomposer orqali tahlil qilinadi, PlanOptimizer orqali optimallashtiriladi,
        va DependencyGraph orqali ijro tartibi (execution_order) hisoblanadi.
        """
        clean_goal = (goal or "").strip()
        plan_id = f"plan_{str(uuid.uuid4())[:8]}"

        # 1. GoalDecomposer orqali rejalashtirish
        if hasattr(self, "goal_decomposer") and self.goal_decomposer:
            plan = self.goal_decomposer.decompose(clean_goal, request=request)
        else:
            # Zaxira dekompozitsiya
            local_steps = self._decompose_locally(clean_goal)
            if local_steps:
                plan = AgentPlan(
                    plan_id=plan_id,
                    goal=clean_goal,
                    steps=local_steps,
                    status=PlanStatus.PENDING,
                    created_at=datetime.datetime.now().isoformat(),
                    max_steps=self.MAX_STEPS,
                    metadata={"planner": "local_deterministic"}
                )
            elif self.provider_manager and request:
                ai_steps = self._generate_plan_via_llm(clean_goal, request)
                if ai_steps:
                    plan = AgentPlan(
                        plan_id=plan_id,
                        goal=clean_goal,
                        steps=ai_steps,
                        status=PlanStatus.PENDING,
                        created_at=datetime.datetime.now().isoformat(),
                        max_steps=self.MAX_STEPS,
                        metadata={"planner": "ai_provider"}
                    )
                else:
                    single_tool = self._infer_single_tool(clean_goal)
                    single_params = {"query": clean_goal} if single_tool == "search" else {}
                    plan = AgentPlan(
                        plan_id=plan_id,
                        goal=clean_goal,
                        steps=[
                            PlanStep(
                                step_id="step_1",
                                order=1,
                                intent=single_tool,
                                tool=single_tool,
                                parameters=single_params,
                                expected_result=f"{clean_goal} bajarilishi",
                                risk_level=self.permission_engine.evaluate(single_tool, single_params)[0]
                            )
                        ],
                        status=PlanStatus.PENDING,
                        created_at=datetime.datetime.now().isoformat(),
                        max_steps=self.MAX_STEPS,
                        metadata={"planner": "single_step_fallback"}
                    )
            else:
                single_tool = self._infer_single_tool(clean_goal)
                single_params = {"query": clean_goal} if single_tool == "search" else {}
                plan = AgentPlan(
                    plan_id=plan_id,
                    goal=clean_goal,
                    steps=[
                        PlanStep(
                            step_id="step_1",
                            order=1,
                            intent=single_tool,
                            tool=single_tool,
                            parameters=single_params,
                            expected_result=f"{clean_goal} bajarilishi",
                            risk_level=self.permission_engine.evaluate(single_tool, single_params)[0]
                        )
                    ],
                    status=PlanStatus.PENDING,
                    created_at=datetime.datetime.now().isoformat(),
                    max_steps=self.MAX_STEPS,
                    metadata={"planner": "single_step_fallback"}
                )

        # 2. PlanOptimizer orqali ortiqcha takrorlanishlarni tozalash
        if hasattr(self, "plan_optimizer") and self.plan_optimizer:
            plan = self.plan_optimizer.optimize(plan)

        # 3. DependencyGraph orqali ijro tartibini ta'minlash
        if hasattr(self, "dependency_graph") and self.dependency_graph:
            if not plan.execution_order or len(plan.execution_order) != len(plan.steps):
                dep_map = {s.step_id: list(s.dependencies) for s in plan.steps}
                plan.dependencies = dep_map
                order = self.dependency_graph.compute_execution_order(plan.steps, dep_map)
                plan.execution_order = order

        plan.risk_level = plan.calculate_plan_risk()
        return plan

    def _decompose_locally(self, text: str) -> Optional[List[PlanStep]]:
        """
        'A va B', 'A keyin B', 'A hamda B' kabi birikmalarni deterministik tahlil qilish.
        """
        lowered = text.lower()
        delimiters = [r"\bva\b", r"\bkeyin\b", r"\bhamda\b", r"\bso'ng\b", r"\band\b"]
        pattern = "|".join(delimiters)

        parts = [p.strip() for p in re.split(pattern, lowered) if p.strip()]
        if len(parts) <= 1:
            return None

        steps: List[PlanStep] = []
        for idx, part in enumerate(parts, 1):
            tool = self._infer_single_tool(part)
            if not tool:
                return None  # Noma'lum bo'lsa LLM ga qoldiramiz

            params: Dict[str, Any] = {}
            if tool == "search":
                params["query"] = part.replace("izla", "").replace("qidir", "").strip()
            elif tool == "calculator":
                expr = re.sub(r"[^\d\+\-\*\/\(\)\.\s]", "", part).strip()
                params["expression"] = expr or "0"
            elif tool == "weather":
                params["city"] = "Toshkent"
            elif tool == "currency":
                params["from_currency"] = "USD"
                params["to_currency"] = "UZS"

            risk, _, _ = self.permission_engine.evaluate(tool, params)
            steps.append(PlanStep(
                step_id=f"step_{idx}",
                order=idx,
                intent=tool,
                tool=tool,
                parameters=params,
                expected_result=f"{part} amali bajarilishi",
                risk_level=risk
            ))

        return steps if steps else None

    def _infer_single_tool(self, text: str) -> str:
        """Oddiy matn asosida asbobni aniqlash"""
        low = text.lower()
        if any(w in low for w in ["youtube", "yutub", "video"]):
            return "open_youtube"
        if "brave" in low:
            return "open_brave"
        if any(w in low for w in ["chrome", "brauzer"]):
            return "open_chrome"
        if any(w in low for w in ["telegram", "tg"]):
            return "open_telegram"
        if any(w in low for w in ["code", "vscode", "vs code"]):
            return "open_code"
        if any(w in low for w in ["discord"]):
            return "open_discord"
        if any(w in low for w in ["ob-havo", "harorat"]):
            return "weather"
        if any(w in low for w in ["valyuta", "kurs", "dollar", "so'm", "som"]):
            return "currency"
        if any(w in low for w in ["hisobla", "kopaytir", "bo'l", "qo'sh", "ayir"]):
            return "calculator"
        if any(w in low for w in ["yop", "chiq"]) and "chrome" in low:
            return "close_chrome"
        if any(w in low for w in ["yop", "oynani yop"]):
            return "close_window"
        if any(w in low for w in ["qidir", "izla", "google"]):
            return "search"
        if any(w in low for w in ["qulfla", "lock"]):
            return "lock"
        return "search"

    def _generate_plan_via_llm(self, goal: str, request: AIRequest) -> Optional[List[PlanStep]]:
        """LLM orqali qat'iy JSON formatdagi reja taklifini olish"""
        plan_system_prompt = f"""Siz Misa AI Agentik Rejalashtiruvchisiz.
Foydalanuvchi maqsadi uchun KICHIK, MINIMAL va KETMA-KET reja tuzing.

Mavjud asboblar:
- open_chrome, open_youtube, open_telegram, open_code, open_brave, open_discord
- close_chrome, close_window, lock
- calculator, weather, currency, system_info, search, app_check

QOIDALAR:
1. Reja maksimal 8 qadamdan iborat bo'lishi shart.
2. Hech qanday sun'iy qadamlar (kutish, tekshirish) qo'shmang.
3. FAQAT quyidagi JSON formatida javob bering, boshqa matn yozmang:
{{
  "goal": "{goal}",
  "steps": [
    {{
      "intent": "open_chrome",
      "tool": "open_chrome",
      "parameters": {{}},
      "expected_result": "Chrome ochildi"
    }}
  ]
}}
"""
        plan_req = AIRequest(
            message=f"Ushbu maqsad uchun qat'iy JSON reja tuz: '{goal}'",
            system_context={"system_instruction": plan_system_prompt},
            memory=request.memory,
            conversation=[]
        )

        try:
            resp: AIResponse = self.provider_manager.generate_with_fallback(plan_req)
            if not resp or not resp.content:
                return None

            raw_text = resp.content.strip()
            # JSON ajratish
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group(0))
            raw_steps = data.get("steps", [])
            if not isinstance(raw_steps, list) or not raw_steps:
                return None

            parsed_steps: List[PlanStep] = []
            for idx, s in enumerate(raw_steps[:self.MAX_STEPS], 1):
                tool = str(s.get("tool", "")).strip()
                params = s.get("parameters", {}) or {}
                risk, _, _ = self.permission_engine.evaluate(tool, params)
                parsed_steps.append(PlanStep(
                    step_id=f"step_{idx}",
                    order=idx,
                    intent=str(s.get("intent", tool)),
                    tool=tool,
                    parameters=params,
                    expected_result=str(s.get("expected_result", "")),
                    risk_level=risk
                ))
            return parsed_steps
        except Exception as e:
            logger.warning(f"[AgentLoop] LLM reja yaratishda xatolik: {e}")
            return None

    # ========================================================
    # PLAN VALIDATION
    # ========================================================

    def validate_plan(self, plan: AgentPlan) -> Tuple[bool, Optional[str]]:
        """
        Rejaning xavfsizlik va tuzilmaviy qoidalariga mosligini qat'iy tekshirish.
        PlanValidator orqali DAG (tsikllar, yetishmayotgan bog'liqliklar), limitlar,
        inyeksiya va asboblar mavjudligini tekshiradi.
        """
        if hasattr(self, "plan_validator") and self.plan_validator:
            return self.plan_validator.validate(plan)

        if not plan or not plan.steps:
            return False, "AGENT_PLAN_INVALID: Rejada birorta ham qadam mavjud emas"

        # 1. Maksimal qadamlar chegarasi
        if len(plan.steps) > self.MAX_STEPS:
            return False, f"AGENT_PLAN_INVALID: Qadamlar soni ruxsat etilgan limitdan oshib ketdi ({len(plan.steps)} > {self.MAX_STEPS})"

        dangerous_patterns = ["__import__", "eval", "exec", "os.system", "subprocess", "shutil.rmtree"]

        seen_steps = set()
        for step in plan.steps:
            tool_name = (step.tool or "").strip()
            if not tool_name:
                return False, f"AGENT_PLAN_INVALID: Qadam #{step.order} da asbob nomi ko'rsatilmagan"

            # 2. Xavfli inyeksiya tekshiruvi
            tool_low = tool_name.lower()
            if any(p in tool_low for p in dangerous_patterns):
                return False, f"AGENT_PLAN_INVALID: Asbob nomida noqonuniy kod aniqlandi: {tool_name}"

            # 3. Parametrlar tekshiruvi
            if not isinstance(step.parameters, dict):
                return False, f"AGENT_PLAN_INVALID: Qadam #{step.order} parametrlari lug'at (dict) bo'lishi shart"

            param_str = json.dumps(step.parameters).lower()
            if any(p in param_str for p in dangerous_patterns):
                return False, f"AGENT_PLAN_INVALID: Qadam #{step.order} parametrlarida xavfli kod aniqlandi"

            # 4. Asbob mavjudligi tekshiruvi (nomi, taxallusi yoki qobiliyati bo'yicha)
            is_valid_tool = False
            if self.tool_registry:
                if self.tool_registry.get(tool_name):
                    is_valid_tool = True
                elif hasattr(self.tool_registry, "find_by_capability") and self.tool_registry.find_by_capability(tool_name):
                    is_valid_tool = True
            elif tool_name in AgentVerifier.DETERMINISTIC_TOOLS:
                is_valid_tool = True
            elif tool_name in ["open_telegram", "open_chrome", "open_youtube", "open_code", "open_discord", "open_brave", "lock", "search"]:
                is_valid_tool = True

            if not is_valid_tool:
                return False, f"AGENT_PLAN_INVALID: Noma'lum yoki qo'llab-quvvatlanmaydigan asbob: '{tool_name}'"

            # 5. Tsiklik takrorlanish (circular execution)
            step_key = f"{step.tool}_{json.dumps(step.parameters, sort_keys=True)}"
            if step_key in seen_steps and len(plan.steps) > 4:
                return False, f"AGENT_PLAN_INVALID: Tsiklik takrorlanuvchi qadam aniqlandi: '{step.tool}'"
            seen_steps.add(step_key)

        return True, None

    # ========================================================
    # EXECUTION LOOP: PLAN → ACT → OBSERVE → VERIFY → CONTINUE
    # ========================================================

    def execute_plan(
        self,
        plan: AgentPlan,
        request: Optional[AIRequest] = None,
        user_name: str = "Foydalanuvchi",
        trace: Optional[ContextTrace] = None,
        resume_from_step: Optional[str] = None
    ) -> IntelligenceResponse:
        """
        Rejani ketma-ket xavfsiz ijro etish.
        Har bir qadam mustaqil tekshiriladi, kuzatiladi va verifikatsiya qilinadi.
        """
        with self._lock:
            # Concurrency: faqat 1 ta faol reja
            if self._state in (AgentState.EXECUTING, AgentState.OBSERVING, AgentState.VERIFYING):
                if not resume_from_step or (self._active_plan and self._active_plan.plan_id != plan.plan_id):
                    logger.warning("[AgentLoop] Boshqa reja faol bo'lgani sababli yangi reja rad etildi")
                    return IntelligenceResponse(
                        type="error",
                        content="Boshqa agentlik rejasi hozirda faol. Yangi reja boshlashdan avval uni kuting yoki to'xtating.",
                        error_code="AGENT_ALREADY_RUNNING",
                        verified=False
                    )

            self._active_plan = plan
            self._abort_requested = False
            if not resume_from_step:
                self._transition_to(AgentState.PLANNING)
            self._execution_state = AgentExecutionState(
                state=self._state,
                current_plan=plan,
                start_time=time.time(),
                trace_id=trace.trace_id if trace else None
            )

        start_time = time.time()
        obs = get_observability_manager()
        active_trace = trace or obs.create_trace()

        # 1. Reja yaratildi (Trace)
        if not resume_from_step:
            active_trace.add_stage(
                "PLAN_CREATED",
                status="ok",
                details={"plan_id": plan.plan_id, "goal": plan.goal, "steps_count": len(plan.steps)}
            )
            self._emit_event("agent_plan_created", {"plan_id": plan.plan_id, "goal": plan.goal, "steps_count": len(plan.steps)})

            # 2. Rejani tekshirish (VALIDATE)
            self._transition_to(AgentState.VALIDATING)
            is_valid, validation_err = self.validate_plan(plan)
            if not is_valid:
                self._transition_to(AgentState.FAILED)
                plan.status = PlanStatus.FAILED
                active_trace.add_stage("PLAN_VALIDATED", status="error", details={"error": validation_err})
                logger.error(f"[AgentLoop] Reja tekshiruvdan o'tmadi: {validation_err}")
                return IntelligenceResponse(
                    type="error",
                    content=f"Reja xavfsizlik tekshiruvidan o'tmadi: {validation_err}",
                    error_code="AGENT_PLAN_INVALID",
                    verified=False,
                    metadata={"plan_id": plan.plan_id}
                )

            active_trace.add_stage("PLAN_VALIDATED", status="ok", details={"plan_id": plan.plan_id})
            plan.status = PlanStatus.RUNNING

        # TaskContext bilan bog'lash
        if self.task_context_manager:
            self.task_context_manager.set_active_task(plan.goal)

        # Planning 2.0: Emit PLAN_OPTIMIZED trace if metadata indicates optimization
        if plan.metadata.get("optimized"):
            active_trace.add_stage(
                "PLAN_OPTIMIZED",
                status="ok",
                details={"plan_id": plan.plan_id, "steps_count": len(plan.steps)}
            )

        # 3. Qadamlarni ijro tartibi (execution_order) bo'yicha bajarish
        if not plan.execution_order:
            plan.execution_order = [s.step_id for s in plan.steps]

        steps_by_id = {s.step_id: s for s in plan.steps}

        start_order_idx = 0
        if resume_from_step and resume_from_step in plan.execution_order:
            start_order_idx = plan.execution_order.index(resume_from_step)

        recent_action_signatures: List[str] = []

        for exec_idx in range(start_order_idx, len(plan.execution_order)):
            step_id = plan.execution_order[exec_idx]
            step = steps_by_id.get(step_id)
            if not step:
                continue

            if step in plan.steps:
                plan.current_step_index = plan.steps.index(step)
            self._execution_state.active_step = step

            # A. Vaqt chegarasi (Timeout) tekshiruvi
            elapsed = time.time() - start_time
            if elapsed > self.MAX_TOTAL_EXECUTION_TIME:
                self._transition_to(AgentState.FAILED)
                plan.status = PlanStatus.FAILED
                err = f"Agentlik rejasining umumiy ijro vaqti limiti ({self.MAX_TOTAL_EXECUTION_TIME}s) tugadi"
                logger.warning(f"[AgentLoop] {err}")
                active_trace.add_stage("STEP_FAILED", status="timeout", details={"step_id": step.step_id, "elapsed": elapsed})
                return self._finalize_agent_response(
                    success=False,
                    message=f"{err}. Bajarilgan qadamlar saqlab qolindi.",
                    error_code="AGENT_TIMEOUT",
                    plan=plan,
                    trace=active_trace,
                    elapsed=elapsed
                )

            # B. Sikl (Loop) aniqlash tekshiruvi
            step_sig = f"{step.tool}:{json.dumps(step.parameters, sort_keys=True)}"
            recent_action_signatures.append(step_sig)
            if len(recent_action_signatures) >= 3 and all(s == step_sig for s in recent_action_signatures[-3:]):
                logger.warning(f"[AgentLoop] Sikl aniqlandi (Loop detected): '{step.tool}' 3 marta ketma-ket takrorlandi")
                self._transition_to(AgentState.FAILED)
                plan.status = PlanStatus.FAILED
                active_trace.add_stage("STEP_FAILED", status="loop_detected", details={"step_id": step.step_id, "tool": step.tool})
                return self._finalize_agent_response(
                    success=False,
                    message=f"Agent bir xil '{step.tool}' amalini ketma-ket takrorlab siklga tushgani aniqlandi va xavfsiz to'xtatildi.",
                    error_code="AGENT_LOOP_DETECTED",
                    plan=plan,
                    trace=active_trace,
                    elapsed=elapsed
                )

            # C. Bekor qilish (Abort) tekshiruvi
            if self._abort_requested:
                self._transition_to(AgentState.ABORTED)
                plan.status = PlanStatus.ABORTED
                active_trace.add_stage("PLAN_ABORTED", status="ok", details={"plan_id": plan.plan_id, "step_id": step.step_id})
                self._emit_event("agent_aborted", {"plan_id": plan.plan_id, "stopped_at_step": step.step_id})
                return self._finalize_agent_response(
                    success=False,
                    message="Agentlik rejasi foydalanuvchi tomonidan bekor qilindi.",
                    error_code="AGENT_ABORTED",
                    plan=plan,
                    trace=active_trace,
                    elapsed=elapsed
                )

            # C. Bog'liqliklar yechilishi (Dependency Resolution)
            step_deps = plan.get_dependencies(step.step_id)
            unresolved_dep = None
            for dep_id in step_deps:
                dep_step = steps_by_id.get(dep_id)
                if not dep_step or dep_step.status != StepStatus.COMPLETED:
                    unresolved_dep = dep_id
                    break
                else:
                    active_trace.add_stage(
                        "STEP_DEPENDENCY_RESOLVED",
                        status="ok",
                        details={"step_id": step.step_id, "resolved_dependency": dep_id}
                    )

            if unresolved_dep:
                logger.warning(f"[AgentLoop] Qadam #{step.order} ({step.step_id}) bog'liqlik sababli bloklandi: {unresolved_dep}")
                step.status = StepStatus.BLOCKED
                active_trace.add_stage(
                    "STEP_BLOCKED",
                    status="blocked",
                    details={"step_id": step.step_id, "blocked_by": unresolved_dep}
                )
                self._transition_to(AgentState.FAILED)
                plan.status = PlanStatus.FAILED
                return self._finalize_agent_response(
                    success=False,
                    message=f"Qadam #{step.order} ({step.tool}) bog'liq bo'lgan '{unresolved_dep}' muvaffaqiyatli yakunlanmagan.",
                    error_code="PLAN_DEPENDENCY_UNRESOLVED",
                    plan=plan,
                    trace=active_trace,
                    elapsed=time.time() - start_time
                )

            active_trace.add_stage("STEP_READY", status="ok", details={"step_id": step.step_id})

            # D. Ruxsat va Tasdiqlash (PERMISSION)
            risk_level, requires_confirmation, prompt_text = self.permission_engine.evaluate(step.tool, step.parameters)
            step.risk_level = risk_level

            # Agar tasdiqlash talab etilsa va u avval tasdiqlanmagan bo'lsa -> PAUSE
            if requires_confirmation and resume_from_step != step.step_id:
                with self._lock:
                    self._transition_to(AgentState.WAITING_CONFIRMATION)
                    plan.status = PlanStatus.PAUSED
                    step.status = StepStatus.WAITING_CONFIRMATION
                    self._paused_step_id = step.step_id

                active_trace.add_stage(
                    "PLAN_PAUSED",
                    status="ok",
                    details={"step_id": step.step_id, "tool": step.tool, "risk": risk_level.value}
                )
                self._emit_event("agent_confirmation_required", {
                    "plan_id": plan.plan_id,
                    "step_id": step.step_id,
                    "tool": step.tool,
                    "risk": risk_level.value,
                    "prompt": prompt_text or f"'{step.tool}' amalini bajarishni tasdiqlaysizmi?",
                })

                return IntelligenceResponse(
                    type="confirmation",
                    content=prompt_text or f"'{step.tool}' amalini tasdiqlash talab etiladi.",
                    intent=step.intent,
                    params=step.parameters,
                    verified=True,
                    metadata={
                        "confirmation_required": True,
                        "plan_id": plan.plan_id,
                        "step_id": step.step_id,
                        "risk": risk_level.value,
                        "current_step": step.order,
                        "total_steps": len(plan.steps)
                    }
                )

            # D. ACT: Asbobni bajarish
            self._transition_to(AgentState.EXECUTING)
            step.status = StepStatus.RUNNING
            active_trace.add_stage("STEP_STARTED", status="ok", details={"step_id": step.step_id, "tool": step.tool})
            self._emit_event("agent_step_started", {
                "plan_id": plan.plan_id,
                "step_id": step.step_id,
                "order": step.order,
                "tool": step.tool,
            })

            step_result = self._act_execute_step(step, trace=active_trace)

            # E. OBSERVE: Natijani qayd etish
            self._transition_to(AgentState.OBSERVING)
            step.observed_result = step_result.raw_result
            step.error = step_result.error

            # F. VERIFY: Natijani tekshirish
            self._transition_to(AgentState.VERIFYING)
            verification = self.verifier.verify_step(step, step_result)
            step.verification = verification

            active_trace.add_stage(
                "STEP_VERIFIED",
                status="ok" if verification.verified else "error",
                details={
                    "step_id": step.step_id,
                    "status": verification.status.value,
                    "reason": verification.reason
                }
            )
            self._emit_event("agent_verification", {
                "plan_id": plan.plan_id,
                "step_id": step.step_id,
                "verified": verification.verified,
                "status": verification.status.value,
                "reason": verification.reason,
            })

            can_continue, cont_reason = self.verifier.should_continue(verification, step)

            if can_continue:
                # Qadam muvaffaqiyatli yakunlandi
                step.status = StepStatus.COMPLETED
                self._execution_state.completed_steps.append(step)
                active_trace.add_stage("STEP_COMPLETED", status="ok", details={"step_id": step.step_id})
                self._emit_event("agent_step_completed", {
                    "plan_id": plan.plan_id,
                    "step_id": step.step_id,
                    "order": step.order,
                    "tool": step.tool,
                })

                if self.task_context_manager:
                    self.task_context_manager.update_task_progress(
                        action=step.tool,
                        result=str(step_result.raw_result)[:100] if step_result.raw_result else None
                    )
            else:
                # Qadam muvaffaqiyatsiz bo'ldi -> Qayta urinish (Retry) yoki To'xtatish
                logger.warning(f"[AgentLoop] Qadam #{step.order} muvaffaqiyatsiz: {cont_reason}")

                # Qayta urinish xavfsizligini tekshirish (Idempotency check via Tool Contract 2.0)
                from core.tools.contract import ToolContract2
                tool_obj = self.tool_registry.get(step.tool) if self.tool_registry else None
                is_non_idempotent = False
                if isinstance(tool_obj, ToolContract2):
                    is_non_idempotent = (not tool_obj.idempotent or bool(tool_obj.destructive))
                else:
                    is_non_idempotent = (step.tool in self.NON_IDEMPOTENT_ACTIONS)

                if is_non_idempotent:
                    logger.warning(f"[AgentLoop] Destruktiv yoki no-idempotent amal '{step.tool}' uchun qayta urinish bloklandi (AGENT_RETRY_BLOCKED)")
                    step.status = StepStatus.FAILED
                    self._execution_state.failed_steps.append(step)
                    self._transition_to(AgentState.FAILED)
                    plan.status = PlanStatus.FAILED
                    active_trace.add_stage("STEP_FAILED", status="blocked_retry", details={"tool": step.tool, "reason": "non_idempotent_or_destructive"})
                    self._emit_event("agent_step_failed", {"plan_id": plan.plan_id, "step_id": step.step_id, "error": "AGENT_RETRY_BLOCKED"})
                    return self._finalize_agent_response(
                        success=False,
                        message=f"Xavfli yoki no-idempotent amal '{step.tool}' bajarilmadi va xavfsizlik yuzasidan qayta urinish bloklandi: {cont_reason}",
                        error_code="AGENT_RETRY_BLOCKED",
                        plan=plan,
                        trace=active_trace,
                        elapsed=time.time() - start_time
                    )

                # Qayta urinish limiti (Retry policy bo'yicha bir xil asbob bilan qayta urinish)
                if step.retry_count < step.max_retries:
                    step.retry_count += 1
                    logger.info(f"[AgentLoop] Qadam #{step.order} uchun {step.retry_count}-qayta urinish...")
                    # 1 marta qayta urinib ko'ramiz
                    retry_res = self._act_execute_step(step, trace=active_trace)
                    retry_ver = self.verifier.verify_step(step, retry_res)
                    step.verification = retry_ver
                    retry_continue, _ = self.verifier.should_continue(retry_ver, step)
                    if retry_continue:
                        step.status = StepStatus.COMPLETED
                        step.observed_result = retry_res.raw_result
                        step.error = retry_res.error
                        self._execution_state.completed_steps.append(step)
                        active_trace.add_stage("STEP_COMPLETED", status="ok_after_retry", details={"step_id": step.step_id})
                        if self.task_context_manager:
                            self.task_context_manager.update_task_progress(
                                action=step.tool,
                                result=str(retry_res.raw_result)[:100] if retry_res.raw_result else None
                            )
                        continue

                # UNKNOWN holatida foydalanuvchidan tasdiq/aniqlik so'rash siyosati
                if "UNKNOWN_STATUS_REQUIRES_CLARIFICATION" in cont_reason:
                    with self._lock:
                        self._transition_to(AgentState.WAITING_CONFIRMATION)
                        plan.status = PlanStatus.PAUSED
                        step.status = StepStatus.WAITING_CONFIRMATION
                        self._paused_step_id = step.step_id

                    active_trace.add_stage(
                        "PLAN_PAUSED",
                        status="warning",
                        details={"step_id": step.step_id, "reason": cont_reason}
                    )
                    prompt_txt = f"Qadam #{step.order} ({step.tool}) bajarildi, ammo natija deterministik tasdiqlanmadi (UNKNOWN). Qadamni muvaffaqiyatli deb hisoblab davom etamizmi?"
                    self._emit_event("agent_confirmation_required", {
                        "plan_id": plan.plan_id,
                        "step_id": step.step_id,
                        "tool": step.tool,
                        "risk": step.risk_level.value,
                        "prompt": prompt_txt,
                    })
                    return IntelligenceResponse(
                        type="confirmation",
                        content=prompt_txt,
                        intent=step.intent,
                        params=step.parameters,
                        verified=False,
                        metadata={
                            "confirmation_required": True,
                            "clarification_required": True,
                            "plan_id": plan.plan_id,
                            "step_id": step.step_id,
                            "reason": cont_reason,
                            "current_step": step.order,
                            "total_steps": len(plan.steps)
                        }
                    )

                # Planning 2.0: Replanning Engine
                if getattr(step, "failure_category", None) != FailureCategory.SECURITY_BLOCKED and hasattr(self, "replanning_engine") and self.replanning_engine:
                    active_trace.add_stage(
                        "PLAN_REPLAN_REQUIRED",
                        status="warning",
                        details={"failed_step": step.step_id, "reason": cont_reason}
                    )
                    replanned, replan_msg = self.replanning_engine.evaluate_and_replan(
                        plan=plan,
                        failed_step=step,
                        failure_reason=cont_reason,
                        request=request
                    )
                    if replanned:
                        active_trace.add_stage(
                            "PLAN_REPLANNED",
                            status="ok",
                            details={"version": plan.plan_version, "reason": replan_msg}
                        )
                        active_trace.add_stage(
                            "PLAN_VERSION_CREATED",
                            status="ok",
                            details={"plan_id": plan.plan_id, "version": plan.plan_version}
                        )
                        self._emit_event("agent_plan_replanned", {
                            "plan_id": plan.plan_id,
                            "version": plan.plan_version,
                            "replan_count": plan.replan_count,
                            "reason": replan_msg,
                            "step_id": step.step_id,
                            "tool": step.tool,
                        })

                        # Qayta rejalashtirilgan qadamni bajarish
                        logger.info(f"[AgentLoop] Rejalashtirilgan yangi v{plan.plan_version} bo'yicha qadam qayta bajarilmoqda: {step.tool}")
                        replan_res = self._act_execute_step(step, trace=active_trace)
                        replan_ver = self.verifier.verify_step(step, replan_res)
                        step.verification = replan_ver
                        replan_continue, _ = self.verifier.should_continue(replan_ver, step)
                        if replan_continue:
                            step.status = StepStatus.COMPLETED
                            step.observed_result = replan_res.raw_result
                            step.error = replan_res.error
                            self._execution_state.completed_steps.append(step)
                            active_trace.add_stage("STEP_COMPLETED", status="ok_after_replan", details={"step_id": step.step_id})
                            if self.task_context_manager:
                                self.task_context_manager.update_task_progress(
                                    action=step.tool,
                                    result=str(replan_res.raw_result)[:100] if replan_res.raw_result else None
                                )
                            continue

                # Qayta urinish ham yordam bermasa -> To'xtatish
                step.status = StepStatus.FAILED
                self._execution_state.failed_steps.append(step)
                self._transition_to(AgentState.FAILED)
                plan.status = PlanStatus.FAILED
                active_trace.add_stage("STEP_FAILED", status="error", details={"step_id": step.step_id, "error": cont_reason})
                self._emit_event("agent_step_failed", {"plan_id": plan.plan_id, "step_id": step.step_id, "error": cont_reason})
                return self._finalize_agent_response(
                    success=False,
                    message=f"Rejaning #{step.order}-qadami ({step.tool}) bajarilmadi: {verification.reason}",
                    error_code="STEP_FAILED",
                    plan=plan,
                    trace=active_trace,
                    elapsed=time.time() - start_time
                )

        # 4. Reja to'liq yakunlandi (COMPLETE)
        self._transition_to(AgentState.COMPLETED)
        plan.status = PlanStatus.COMPLETED
        elapsed_total = time.time() - start_time
        self._execution_state.total_execution_time = elapsed_total

        active_trace.add_stage("PLAN_COMPLETED", status="ok", details={"plan_id": plan.plan_id, "duration_ms": elapsed_total * 1000})
        self._emit_event("agent_completed", {"plan_id": plan.plan_id, "steps_completed": len(plan.steps)})

        if self.task_context_manager:
            self.task_context_manager.complete_task()

        summary_msg = self._build_completion_summary(plan)
        return self._finalize_agent_response(
            success=True,
            message=summary_msg,
            plan=plan,
            trace=active_trace,
            elapsed=elapsed_total
        )

    # ========================================================
    # ACT EXECUTION HELPER
    # ========================================================

    def _act_execute_step(self, step: PlanStep, trace: Optional[Any] = None) -> StepResult:
        """Bitta asbobni chaqirish va StepResult qaytarish (Tool System 2.0 bilan)"""
        tool_name = step.tool
        params = step.parameters or {}
        step_start = time.time()

        # ToolRegistry orqali bajarish
        if self.tool_registry:
            try:
                # 1. To'g'ridan-to'g'ri nom yoki qobiliyat orqali topish
                tool_obj = self.tool_registry.get(tool_name)
                if not tool_obj and hasattr(self.tool_registry, "select_tool"):
                    ctx = None
                    if self.task_context_manager:
                        if hasattr(self.task_context_manager, "get_active_context"):
                            ctx = self.task_context_manager.get_active_context()
                        elif hasattr(self.task_context_manager, "get_active_task"):
                            ctx = self.task_context_manager.get_active_task()
                    sel = self.tool_registry.select_tool(
                        required_capability=tool_name,
                        context=ctx,
                        candidate_params=params
                    )
                    if sel and sel.tool:
                        tool_obj = sel.tool
                        if trace:
                            trace.add_stage("TOOL_DISCOVERED", status="ok", details={
                                "capability": tool_name,
                                "candidates": sel.candidate_tools
                            })
                            trace.add_stage("TOOL_SELECTED", status="ok", details={
                                "selected": tool_obj.name,
                                "score": sel.score,
                                "why": sel.explanation
                            })

                target_name = tool_obj.name if tool_obj else tool_name
                call_res = self.tool_registry.call(target_name, **params)

                dur = (time.time() - step_start) * 1000.0
                if bool(call_res.get("success", False)):
                    return StepResult(
                        step_id=step.step_id,
                        tool=tool_obj.name if tool_obj else tool_name,
                        parameters=redact_sensitive_data(params),
                        success=True,
                        raw_result=call_res.get("result") if "result" in call_res else call_res.get("data"),
                        duration_ms=dur,
                        timestamp=datetime.datetime.now().isoformat()
                    )
                else:
                    return StepResult(
                        step_id=step.step_id,
                        tool=tool_obj.name if tool_obj else tool_name,
                        parameters=redact_sensitive_data(params),
                        success=False,
                        error=call_res.get("error", "Noma'lum xatolik"),
                        raw_result=call_res.to_dict() if hasattr(call_res, "to_dict") else call_res,
                        duration_ms=dur,
                        timestamp=datetime.datetime.now().isoformat()
                    )
            except Exception as e:
                dur = (time.time() - step_start) * 1000.0
                return StepResult(
                    step_id=step.step_id,
                    tool=tool_name,
                    parameters=redact_sensitive_data(params),
                    success=False,
                    error=str(e),
                    duration_ms=dur,
                    timestamp=datetime.datetime.now().isoformat()
                )

        # ToolRegistry bo'lmaganda sinov yoki zaxira simulyatsiyasi
        dur = (time.time() - step_start) * 1000.0
        return StepResult(
            step_id=step.step_id,
            tool=tool_name,
            parameters=redact_sensitive_data(params),
            success=True,
            raw_result=f"{tool_name} bajarildi",
            duration_ms=dur,
            timestamp=datetime.datetime.now().isoformat()
        )

    # ========================================================
    # CONFIRMATION RESUME & USER ABORT
    # ========================================================

    def confirm_step(
        self,
        plan_id: str,
        step_id: str,
        approve: bool = True
    ) -> IntelligenceResponse:
        """Foydalanuvchi tasdiqlaganidan keyin pauza qilingan rejani davom ettirish"""
        with self._lock:
            if not self._active_plan or self._active_plan.plan_id != plan_id:
                return IntelligenceResponse(
                    type="error",
                    content="Faol reja topilmadi yoki reja ID si mos kelmadi.",
                    error_code="PLAN_NOT_FOUND",
                    verified=False
                )

            if not approve:
                logger.info(f"[AgentLoop] Foydalanuvchi qadam #{step_id} ni rad etdi")
                self.abort_plan(plan_id)
                return IntelligenceResponse(
                    type="answer",
                    content="Amal bekor qilindi va agentlik rejasi to'xtatildi.",
                    verified=True
                )

            logger.info(f"[AgentLoop] Foydalanuvchi qadam #{step_id} ni tasdiqladi, reja davom ettirilmoqda")
            active_trace = None
            if self._execution_state and self._execution_state.trace_id:
                active_trace = get_observability_manager().get_trace_obj(self._execution_state.trace_id)
            if not active_trace:
                active_trace = get_observability_manager().create_trace()
            active_trace.add_stage("PLAN_RESUMED", status="ok", details={"plan_id": plan_id, "step_id": step_id})

            self._paused_step_id = None
            return self.execute_plan(
                plan=self._active_plan,
                resume_from_step=step_id,
                trace=active_trace
            )

    def abort_plan(self, plan_id: Optional[str] = None) -> Tuple[bool, str]:
        """Faol rejani xavfsiz to'xtatish"""
        with self._lock:
            if not self._active_plan:
                return False, "Faol reja mavjud emas"

            if plan_id and self._active_plan.plan_id != plan_id:
                return False, "Reja ID si mos kelmadi"

            if self._active_plan.status in (PlanStatus.COMPLETED, PlanStatus.ABORTED, PlanStatus.FAILED):
                return False, f"Reja allaqachon yakunlangan ({self._active_plan.status.value})"

            self._abort_requested = True
            self._active_plan.status = PlanStatus.ABORTED
            self._transition_to(AgentState.ABORTED)
            try:
                from core.gui.controller import WindowsGUIController
                WindowsGUIController.request_abort()
            except Exception:
                pass
            logger.info(f"[AgentLoop] Reja #{self._active_plan.plan_id} bekor qilindi")
            return True, "Reja to'xtatildi"

    # ========================================================
    # HELPERS & EVENT EMITTING
    # ========================================================

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """WebSocket va frontend uchun hodisalarni yuborish"""
        if self.event_emitter:
            try:
                safe_data = redact_sensitive_data(data)
                self.event_emitter(event_type, safe_data)
            except Exception as e:
                logger.debug(f"[AgentLoop] Event emitter xatolik: {e}")

    def _build_completion_summary(self, plan: AgentPlan) -> str:
        """Reja yakunlanganda qisqa va tushunarli xulosaviy javob tuzish"""
        lines = [f"✅ Reja muvaffaqiyatli yakunlandi: '{plan.goal}'"]
        for s in plan.steps:
            obs = str(s.observed_result)[:60] if s.observed_result else ""
            lines.append(f"  • {s.tool}: muvaffaqiyatli {f'({obs})' if obs else ''}")
        return "\n".join(lines)

    def _finalize_agent_response(
        self,
        success: bool,
        message: str,
        plan: AgentPlan,
        trace: Optional[ContextTrace],
        elapsed: float,
        error_code: Optional[str] = None
    ) -> IntelligenceResponse:
        """Yakuniy javobni shakllantirish"""
        if trace:
            trace.finish(success=success)
            trace.duration_ms = round(elapsed * 1000.0, 2)

        return IntelligenceResponse(
            type="answer" if success else "error",
            content=message,
            intent="agent_plan",
            verified=success,
            provider="agent_loop",
            model="deterministic_loop",
            error_code=error_code,
            metadata={
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "total_steps": len(plan.steps),
                "completed_steps": len([s for s in plan.steps if s.status == StepStatus.COMPLETED]),
                "status": plan.status.value,
                "latency_ms": round(elapsed * 1000.0, 2),
                "trace_id": trace.trace_id if trace else None,
                "plan_version": getattr(plan, "plan_version", 1),
                "replan_count": getattr(plan, "replan_count", 0),
                "execution_order": getattr(plan, "execution_order", []),
                "dependencies": getattr(plan, "dependencies", {}),
                "replan_history": getattr(plan, "replan_history", []),
            }
        )


# Global Singleton AgentLoop
_agent_loop: Optional[AgentLoop] = None


def get_agent_loop() -> AgentLoop:
    """AgentLoop singletonini olish"""
    global _agent_loop
    if _agent_loop is None:
        from core.agent_tools import get_registry
        from core.intelligence.permission import PermissionEngine
        from core.intelligence.verifier import AgentVerifier

        registry = get_registry()
        perm = PermissionEngine()
        verifier = AgentVerifier(tool_registry=registry)

        _agent_loop = AgentLoop(
            tool_registry=registry,
            permission_engine=perm,
            verifier=verifier
        )
    return _agent_loop
