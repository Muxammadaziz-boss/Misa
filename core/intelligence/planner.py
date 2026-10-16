# ========== planner.py ==========
# Misa AI 7.x — Planning & Reasoning 2.0 Engine
# Goal Decomposition, Dependency Graphs, Execution Ordering, Plan Optimization & Versioned Replanning

import re
import uuid
import json
import logging
import datetime
from collections import deque, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from core.intelligence.types import (
    RiskLevel,
    PlanStatus,
    StepStatus,
    VerificationStatus,
    PlanStep,
    AgentPlan,
    StepResult,
    AIRequest,
    AIResponse,
)
from core.intelligence.permission import PermissionEngine
from core.tools.contract import ToolContract2, ToolErrorCode, ToolHealth
from core.tools.validator import ParameterValidator

logger = logging.getLogger(__name__)


# ========================================================
# 1. GOAL DECOMPOSER
# ========================================================

class GoalDecomposer:
    """
    Foydalanuvchi maqsadini tahlil qilish va qismlarga ajratish (Decomposition).
    Oddiy maqsadlarni 1 ta minimal qadamda saqlaydi (over-planning dan qochish).
    Murakkab maqsadlarni esa bog'liq va ketma-ket qadamlarga ajratadi.
    """

    SIMPLE_MATH_PATTERNS = [
        re.compile(r"^\s*(\d+[\s\+\-\*\/\(\)\.\^\%]+\d+)\s*(ni\s+)?(hisobla|chiqar|qancha|top)?\s*$", re.IGNORECASE),
        re.compile(r"^(hisobla|calc|calculate)\s*:?\s*[\d\+\-\*\/\(\)\.\s]+$", re.IGNORECASE),
    ]

    TIME_PATTERNS = [
        re.compile(r"^(hozirgi\s+)?(soat|vaqt|bugungi sana|sana|bugun qaysi kun)\s*(necha|qanday|qanaqa)?\s*$", re.IGNORECASE),
    ]

    SINGLE_TOOL_SHORTCUTS: Dict[str, Tuple[str, str, Dict[str, Any]]] = {
        # pattern_substring: (tool_name, capability, default_params)
        "youtube": ("open_youtube", "browser_navigation", {}),
        "yutub": ("open_youtube", "browser_navigation", {}),
        "brave": ("open_brave", "browser_navigation", {}),
        "chrome": ("open_chrome", "browser_navigation", {}),
        "telegram": ("open_telegram", "app_launch", {}),
        "tg": ("open_telegram", "app_launch", {}),
        "vscode": ("open_code", "app_launch", {}),
        "vs code": ("open_code", "app_launch", {}),
        "discord": ("open_discord", "app_launch", {}),
        "qulfla": ("lock", "system_power", {}),
        "lock": ("lock", "system_power", {}),
        "oynani yop": ("close_window", "window_management", {}),
        "notepad": ("focus_window", "window_management", {"title": "Notepad"}),
        "bloknot": ("focus_window", "window_management", {"title": "Notepad"}),
        "kalkulyator": ("calculator", "calculation", {"expression": "0"}),
        "calculator": ("calculator", "calculation", {"expression": "0"}),
        "screen_click": ("screen_click", "gui_automation", {}),
        "keyboard_type": ("keyboard_type", "gui_automation", {}),
        "screen_analyze": ("screen_analyze", "screen_vision", {}),
    }

    def __init__(
        self,
        tool_registry=None,
        provider_manager=None,
        permission_engine: Optional[PermissionEngine] = None
    ):
        self.tool_registry = tool_registry
        self.provider_manager = provider_manager
        self.permission_engine = permission_engine or PermissionEngine()

    def is_simple_goal(self, goal: str) -> bool:
        """
        Maqsad oddiy (yagona amal) ekanligini aniqlash.
        Oddiy maqsadlar uchun murakkab reja yoki LLM kerak emas.
        """
        if not goal or not goal.strip():
            return True

        clean = goal.strip().lower()
        words = clean.split()
        conjunctions = ["va", "keyin", "so'ng", "hamda", "agar", "lekin", "ammo", "and", "then", "after"]

        # Ko'p bosqichli GUI amallari hech qachon 'oddiy' (single-step) hisoblanmaydi
        if any(kw in clean for kw in ["ochib", "och va", "hisoblash", "yozish", "deb yoz", "matn yoz", "hisobla va"]):
            return False

        # Matematik ifodalar
        for pat in self.SIMPLE_MATH_PATTERNS:
            if pat.match(clean):
                return True

        # Vaqt/sana
        for pat in self.TIME_PATTERNS:
            if pat.match(clean):
                return True

        # Shortcuts for specific applications or actions
        for key in self.SINGLE_TOOL_SHORTCUTS:
            if key in clean and len(words) <= 5 and not any(f" {c} " in f" {clean} " for c in conjunctions):
                return True

        if any(w in clean for w in ["valyuta", "kurs", "dollar", "ob-havo", "harorat"]) and len(words) <= 4 and not any(f" {c} " in f" {clean} " for c in conjunctions):
            return True

        return False

    def decompose(
        self,
        goal: str,
        plan_id: Optional[str] = None,
        request: Optional[AIRequest] = None,
        provider_manager: Optional[Any] = None,
        max_steps: int = 8
    ) -> AgentPlan:
        """
        Maqsadni to'liq Planning Model 2.0 rejasiga aylantirish.
        """
        clean_goal = (goal or "").strip()
        plan_id = plan_id or f"plan_{str(uuid.uuid4())[:8]}"

        # 1. Oddiy maqsadlar uchun yagona qadamli reja
        if self.is_simple_goal(clean_goal):
            step = self._build_single_step(clean_goal, step_order=1)
            plan = AgentPlan(
                plan_id=plan_id,
                goal=clean_goal,
                intent=clean_goal,
                desired_outcome=f"{clean_goal} amali muvaffaqiyatli bajarildi",
                steps=[step],
                dependencies={},
                execution_order=[step.step_id],
                required_capabilities=[step.required_capability],
                risk_level=step.risk_level,
                status=PlanStatus.PENDING,
                created_at=datetime.datetime.now().isoformat(),
                max_steps=max_steps,
                metadata={"planner": "deterministic_simple", "complexity": "simple"}
            )
            return plan

        # 2. Mahalliy deterministik tahlil (Bog'lovchilar va qoliplar orqali)
        local_steps = self._decompose_locally(clean_goal)
        if local_steps:
            dep_graph = DependencyGraph()
            deps = dep_graph.build_graph(local_steps)
            order = dep_graph.compute_execution_order(local_steps, deps)

            plan = AgentPlan(
                plan_id=plan_id,
                goal=clean_goal,
                intent=clean_goal,
                desired_outcome=f"'{clean_goal}' maqsadidagi barcha bog'liq bosqichlar to'liq bajarildi",
                steps=local_steps,
                dependencies=deps,
                execution_order=order,
                status=PlanStatus.PENDING,
                created_at=datetime.datetime.now().isoformat(),
                max_steps=max_steps,
                metadata={"planner": "local_decomposition", "complexity": "multi_step"}
            )
            return plan

        # 3. LLM orqali rejalashtirish (agar mavjud bo'lsa)
        pm = provider_manager or self.provider_manager
        if pm and request:
            llm_steps = self._generate_plan_via_llm(clean_goal, request, pm, max_steps)
            if llm_steps:
                dep_graph = DependencyGraph()
                deps = dep_graph.build_graph(llm_steps)
                order = dep_graph.compute_execution_order(llm_steps, deps)
                plan = AgentPlan(
                    plan_id=plan_id,
                    goal=clean_goal,
                    intent=clean_goal,
                    desired_outcome=f"'{clean_goal}' bo'yicha sun'iy intellekt rejasi",
                    steps=llm_steps,
                    dependencies=deps,
                    execution_order=order,
                    status=PlanStatus.PENDING,
                    created_at=datetime.datetime.now().isoformat(),
                    max_steps=max_steps,
                    metadata={"planner": "llm_structured", "complexity": "complex"}
                )
                return plan

        # 4. Zaxira (Fallback) yagona qadamli reja
        fallback_step = self._build_single_step(clean_goal, step_order=1)
        return AgentPlan(
            plan_id=plan_id,
            goal=clean_goal,
            intent=clean_goal,
            desired_outcome=f"{clean_goal} amali bajarilishi",
            steps=[fallback_step],
            dependencies={},
            execution_order=[fallback_step.step_id],
            required_capabilities=[fallback_step.required_capability],
            risk_level=fallback_step.risk_level,
            status=PlanStatus.PENDING,
            created_at=datetime.datetime.now().isoformat(),
            max_steps=max_steps,
            metadata={"planner": "single_step_fallback", "complexity": "fallback"}
        )

    def _build_single_step(self, text: str, step_order: int = 1) -> PlanStep:
        """Yagona matndan to'liq mos qadam shakllantirish"""
        tool, capability, params = self._infer_capability_and_params(text)
        risk, _, _ = self.permission_engine.evaluate(tool, params)

        return PlanStep(
            step_id=f"step_{step_order}",
            order=step_order,
            intent=tool,
            description=f"{text} amalini bajarish",
            purpose=f"Foydalanuvchining '{text}' so'rovini qondirish",
            dependencies=[],
            required_capability=capability,
            tool=tool,
            parameters=params,
            expected_result=f"{tool} amali muvaffaqiyatli bajarilishi",
            risk_level=risk,
            status=StepStatus.PENDING,
            max_retries=1
        )

    def _infer_capability_and_params(self, text: str) -> Tuple[str, str, Dict[str, Any]]:
        """Matndan (tool_name, capability, params) uchligini ajratish"""
        low = text.lower().strip()

        # Qisqa buyruqlar
        for key, (tool, cap, def_params) in self.SINGLE_TOOL_SHORTCUTS.items():
            if key in low:
                return tool, cap, dict(def_params)

        # Matematik hisoblash
        if any(w in low for w in ["hisobla", "kopaytir", "ko'paytir", "bo'l", "qo'sh", "ayir", "calc", "calculate"]) or any(p.match(low) for p in self.SIMPLE_MATH_PATTERNS):
            expr = re.sub(r"[^\d\+\-\*\/\(\)\.\s]", "", low).strip()
            return "calculator", "calculation", {"expression": expr or "0"}

        # Ob-havo
        if any(w in low for w in ["ob-havo", "obhavo", "havo", "harorat", "weather"]):
            city = "Toshkent"
            m = re.search(r"(\w+)(da|dagi|ning)?\s+(ob-havo|havo)", low)
            if m:
                found = m.group(1).capitalize()
                if found.lower() not in ["qanday", "bugungi", "ertangi", "iltimos"]:
                    city = found
            return "weather", "weather", {"city": city}

        # Valyuta
        if any(w in low for w in ["valyuta", "kurs", "dollar", "so'm", "som", "rubl", "yevro", "currency"]):
            return "currency", "currency", {"from_currency": "USD", "to_currency": "UZS"}

        # Vaqt / sana
        if any(w in low for w in ["vaqt", "soat", "sana", "time", "date"]):
            return "datetime", "datetime", {}

        # Tizim ma'lumotlari
        if any(w in low for w in ["tizim", "kompyuter", "protsessor", "ram", "xotira", "disk", "gpu", "cpu", "specs"]):
            return "system_info", "system_information", {}

        # GUI amallari
        if any(w in low for w in ["bos", "click", "bosing", "sichqoncha"]):
            mx = re.search(r"x\s*=\s*(\d+)", low)
            my = re.search(r"y\s*=\s*(\d+)", low)
            px = int(mx.group(1)) if mx else 100
            py = int(my.group(1)) if my else 100
            return "screen_click", "gui_automation", {"x": px, "y": py}

        if any(w in low for w in ["yoz", "matn kirit", "type"]):
            m = re.search(r"['\"](.*?)['\"]", text)
            txt = m.group(1) if m else text
            return "keyboard_type", "gui_automation", {"text": txt}

        if any(w in low for w in ["ekranni ko'r", "ekranni tahlil", "screen_analyze", "ekranda nima"]):
            return "screen_analyze", "screen_vision", {"question": text}

        # Standart qidiruv
        query = low.replace("qidir", "").replace("izla", "").replace("top", "").strip()
        return "search", "web_search", {"query": query or low}

    def _decompose_locally(self, text: str) -> Optional[List[PlanStep]]:
        """
        Murakkab maqsadlarni tahliliy qoliplar va bog'lovchilar orqali ajratish.
        """
        low = text.lower().strip()

        # Qolib A: Notepad'ga matn yozish workflow
        if any(w in low for w in ["notepad", "bloknot"]) and any(w in low for w in ["yoz", "matn", "ochib"]):
            m = re.search(r"(?:^|\s)[\x22\x27]([^\x22\x27]+)[\x22\x27]", text)
            target_text = m.group(1) if m else "Salom Dunyo"
            if not m and "deb" in low:
                parts = text.split("deb")
                if len(parts) > 1:
                    target_text = parts[0].split()[-1] if parts[0].split() else "Salom Dunyo"

            s1 = PlanStep(
                step_id="step_1",
                order=1,
                intent="focus_window",
                description="Notepad ilovasini ochish va fokuslash",
                purpose="Matn kiritish uchun Notepad oynasini aktiv holatga keltirish",
                dependencies=[],
                required_capability="window_management",
                tool="focus_window",
                parameters={"title": "Notepad"},
                precondition="Windows GUI tayyor",
                postcondition="Notepad oynasi faol va fokusda",
                expected_result="Notepad oynasi faollashdi",
                risk_level=RiskLevel.LOW
            )
            s2 = PlanStep(
                step_id="step_2",
                order=2,
                intent="keyboard_type",
                description=f"Notepad oynasiga '{target_text}' matnini kiritish",
                purpose=f"Foydalanuvchi so'ragan '{target_text}' matnini yozish",
                dependencies=["step_1"],
                required_capability="gui_automation",
                tool="keyboard_type",
                parameters={"text": target_text, "target_window": "Notepad"},
                precondition="Notepad oynasi aktiv va fokusda",
                postcondition="Matn kiritildi",
                expected_result=f"'{target_text}' matni Notepad ichiga yozildi",
                risk_level=RiskLevel.HIGH
            )
            s3 = PlanStep(
                step_id="step_3",
                order=3,
                intent="screen_analyze",
                description="Notepad ichidagi kiritilgan matnni tekshirish",
                purpose="Kiritilgan matnning to'g'riligini verifikatsiya qilish",
                dependencies=["step_2"],
                required_capability="screen_vision",
                tool="screen_analyze",
                parameters={"question": "Notepadda kiritilgan matn mavjudmi?"},
                precondition="Klaviatura kiritish amali yakunlandi",
                postcondition="Kiritilgan matn verifikatsiya qilindi",
                expected_result="Notepadda matn mavjudligi tasdiqlandi",
                risk_level=RiskLevel.LOW
            )
            return [s1, s2, s3]

        # Qolib B: Calculator'ni ochib hisoblash workflow
        if any(w in low for w in ["calculator", "kalkulyator"]) and any(w in low for w in ["ochib", "hisobla", "hisoblash"]):
            expr = "7"
            m = re.search(r"(\d+[\s\+\-\*\/\(\)\.\^\%]+\d+)", low)
            if m:
                expr = m.group(1).strip()
            else:
                m_single = re.search(r"(\d+)\s*(ni|chiqar|hisobla)", low)
                if m_single:
                    expr = m_single.group(1).strip()

            s1 = PlanStep(
                step_id="step_1",
                order=1,
                intent="focus_window",
                description="Calculator ilovasini ochish va fokuslash",
                purpose="Hisoblash amali uchun Calculator oynasini tayyorlash",
                dependencies=[],
                required_capability="window_management",
                tool="focus_window",
                parameters={"title": "Calculator"},
                precondition="Windows GUI tayyor",
                postcondition="Calculator faol va fokusda",
                expected_result="Calculator oynasi ochildi",
                risk_level=RiskLevel.LOW
            )
            s2 = PlanStep(
                step_id="step_2",
                order=2,
                intent="calculator",
                description=f"Kalkulyator yordamida '{expr}' ifodasini hisoblash",
                purpose=f"Ifodani aniq hisoblash: {expr}",
                dependencies=["step_1"],
                required_capability="calculation",
                tool="calculator",
                parameters={"expression": expr},
                precondition="Calculator oynasi faol",
                postcondition="Hisoblash natijasi olindi",
                expected_result=f"{expr} hisoblandi",
                risk_level=RiskLevel.LOW
            )
            s3 = PlanStep(
                step_id="step_3",
                order=3,
                intent="screen_analyze",
                description="Kalkulyator natijasini tekshirish",
                purpose="Hisoblash natijasini verifikatsiya qilish",
                dependencies=["step_2"],
                required_capability="screen_vision",
                tool="screen_analyze",
                parameters={"question": f"Kalkulyatorda {expr} natijasi bormi?"},
                precondition="Hisoblash bajarildi",
                postcondition="Hisob to'g'riligi tasdiqlandi",
                expected_result="Hisoblash natijasi tasdiqlandi",
                risk_level=RiskLevel.LOW
            )
            return [s1, s2, s3]

        # Qolib 1: "X tekshir va shunga/natijaga qarab tavsiya ber" (Data-dependent pipeline)
        if any(p in low for p in ["shunga qarab", "natijaga qarab", "tavsiya ber", "maslahat ber", "nima qilishimni ayt"]):
            # Boshlang'ich qism
            if "ob-havo" in low or "havo" in low:
                s1 = PlanStep(
                    step_id="step_1",
                    order=1,
                    intent="weather",
                    description="Ob-havo ma'lumotlarini olish",
                    purpose="Tavsiya berish uchun joriy ob-havoni aniqlash",
                    dependencies=[],
                    required_capability="weather",
                    tool="weather",
                    parameters={"city": "Toshkent"},
                    expected_result="Ob-havo holati va harorat",
                    risk_level=RiskLevel.LOW
                )
                s2 = PlanStep(
                    step_id="step_2",
                    order=2,
                    intent="analyze_weather",
                    description="Olingan ob-havo sharoitlarini tahlil qilish",
                    purpose="Ob-havo omillarini foydalanuvchi rejalariga ta'sirini baholash",
                    dependencies=["step_1"],
                    required_capability="analysis",
                    tool="weather",
                    parameters={"city": "Toshkent"},
                    expected_result="Ob-havo tahlili",
                    risk_level=RiskLevel.LOW
                )
                s3 = PlanStep(
                    step_id="step_3",
                    order=3,
                    intent="generate_recommendation",
                    description="Foydalanuvchi uchun xulosaviy tavsiya ishlab chiqish",
                    purpose="Tahlil natijasi asosida aniq harakatlar rejasini taqdim etish",
                    dependencies=["step_2"],
                    required_capability="recommendation",
                    tool="search",
                    parameters={"query": "ob-havo tavsiyasi"},
                    expected_result="Foydalanuvchi uchun tavsiya",
                    risk_level=RiskLevel.LOW
                )
                return [s1, s2, s3]

        # Qolib 2: "Kompyuterni tekshir, muammoni aniqlab, yechim ber" (Diagnostics pipeline)
        if "kompyuter" in low and any(p in low for p in ["tekshir", "muammo", "yechim", "diagnostika"]):
            s1 = PlanStep(
                step_id="step_1",
                order=1,
                intent="system_info",
                description="Tizim holati va parametrlarini to'plash",
                purpose="Apparat va dasturiy ta'minot ko'rsatkichlarini olish",
                dependencies=[],
                required_capability="system_information",
                tool="system_info",
                parameters={},
                expected_result="CPU, RAM, Disk va OS ko'rsatkichlari",
                risk_level=RiskLevel.LOW
            )
            s2 = PlanStep(
                step_id="step_2",
                order=2,
                intent="analyze_system_health",
                description="Tizim ko'rsatkichlaridagi anomaliyalarni tahlil qilish",
                purpose="Potentsial yuklama va nosozliklarni aniqlash",
                dependencies=["step_1"],
                required_capability="analysis",
                tool="system_info",
                parameters={},
                expected_result="Nosozliklar va anomaliyalar ro'yxati",
                risk_level=RiskLevel.LOW
            )
            s3 = PlanStep(
                step_id="step_3",
                order=3,
                intent="recommend_solution",
                description="Xavfsiz optimallashtirish yoki yechim berish",
                purpose="Tizim faoliyatini yaxshilash choralarini tavsiya etish",
                dependencies=["step_2"],
                required_capability="recommendation",
                tool="system_info",
                parameters={},
                expected_result="Optimallashtirish tavsiyalari",
                risk_level=RiskLevel.LOW
            )
            return [s1, s2, s3]

        # Qolib 3: Bog'lovchilar orqali ajratish ("A va B", "A keyin B", "A hamda B")
        delimiters = [r"\bva\b", r"\bkeyin\b", r"\bhamda\b", r"\bso'ng\b", r"\band\b"]
        parts = [p.strip() for p in re.split("|".join(delimiters), low) if p.strip()]

        if len(parts) > 1:
            steps: List[PlanStep] = []
            for idx, part in enumerate(parts, 1):
                tool, cap, params = self._infer_capability_and_params(part)
                risk, _, _ = self.permission_engine.evaluate(tool, params)

                # Agar "keyin" / "so'ng" kabi ketma-ketlik so'zlari bo'lsa, oldingi qadamga bog'laymiz
                deps = [f"step_{idx - 1}"] if (idx > 1 and any(k in low for k in ["keyin", "so'ng", "then"])) else []

                steps.append(PlanStep(
                    step_id=f"step_{idx}",
                    order=idx,
                    intent=tool,
                    description=f"{part} amalini bajarish",
                    purpose=f"Rejaning #{idx}-bosqichi: {part}",
                    dependencies=deps,
                    required_capability=cap,
                    tool=tool,
                    parameters=params,
                    expected_result=f"{part} amali muvaffaqiyatli bajarilishi",
                    risk_level=risk,
                    status=StepStatus.PENDING
                ))
            return steps

        return None

    def _generate_plan_via_llm(
        self,
        goal: str,
        request: AIRequest,
        provider_manager: Any,
        max_steps: int
    ) -> Optional[List[PlanStep]]:
        """LLM orqali qat'iy JSON formatdagi strukturaviy reja olish"""
        prompt = f"""Siz Misa AI Aqlli Rejalashtiruvchisiz.
Foydalanuvchi maqsadi uchun bog'liqliklari (dependencies) bilan minimal reja tuzing.

Mavjud qobiliyatlar:
- calculation, weather, currency, datetime, system_information, web_search, file_read, file_write, app_check, browser_navigation

Qoidalar:
1. Reja maksimal {max_steps} qadamdan iborat bo'lsin.
2. Qadamlar orasidagi bog'liqliklarni (dependencies) aniq ko'rsating.
3. FAQAT JSON formatida javob bering:
{{
  "steps": [
    {{
      "step_id": "step_1",
      "intent": "weather",
      "description": "Ob-havoni tekshirish",
      "required_capability": "weather",
      "tool": "weather",
      "dependencies": [],
      "parameters": {{"city": "Toshkent"}},
      "expected_result": "Ob-havo ma'lumoti"
    }}
  ]
}}
"""
        req = AIRequest(
            message=f"Maqsad: '{goal}'",
            system_context={"system_instruction": prompt},
            memory=request.memory,
            conversation=[]
        )
        try:
            resp: AIResponse = provider_manager.generate_with_fallback(req)
            if not resp or not resp.content:
                return None
            m = re.search(r"\{.*\}", resp.content.strip(), re.DOTALL)
            if not m:
                return None
            data = json.loads(m.group(0))
            raw_steps = data.get("steps", [])
            if not isinstance(raw_steps, list) or not raw_steps:
                return None

            steps: List[PlanStep] = []
            for idx, s in enumerate(raw_steps[:max_steps], 1):
                tool = str(s.get("tool") or s.get("intent", "search")).strip()
                cap = str(s.get("required_capability", tool)).strip()
                params = dict(s.get("parameters", {}) or {})
                risk, _, _ = self.permission_engine.evaluate(tool, params)
                s_id = str(s.get("step_id") or f"step_{idx}")
                deps = list(s.get("dependencies", []) or [])

                steps.append(PlanStep(
                    step_id=s_id,
                    order=idx,
                    intent=str(s.get("intent", tool)),
                    description=str(s.get("description", tool)),
                    purpose=str(s.get("purpose", "")),
                    dependencies=deps,
                    required_capability=cap,
                    tool=tool,
                    parameters=params,
                    expected_result=str(s.get("expected_result", "")),
                    risk_level=risk
                ))
            return steps
        except Exception as e:
            logger.debug(f"[GoalDecomposer] LLM plan exception: {e}")
            return None


# ========================================================
# 2. DEPENDENCY GRAPH & TOPOLOGICAL EXECUTION ORDER
# ========================================================

class DependencyGraph:
    """
    Qadamlar bog'liqlik grafigi (Directed Acyclic Graph - DAG).
    - Bog'liqliklar to'g'riligini tekshiradi.
    - Tsiklik bog'liqliklarni (Circular Dependency: A -> B -> C -> A) aniqlaydi va rad etadi.
    - Topologik saralash orqali xavfsiz va deterministik execution_order hisoblaydi.
    - Mustaqil (parallel/izolyatsiyalangan) qadamlarni aniqlaydi.
    """

    @staticmethod
    def build_graph(steps: List[PlanStep]) -> Dict[str, List[str]]:
        """Qadamlardan bog'liqlik xaritasini hosil qilish (step_id -> list of prereqs)"""
        graph: Dict[str, List[str]] = {}
        for s in steps:
            graph[s.step_id] = list(s.dependencies or [])
        return graph

    @staticmethod
    def validate_dependencies_exist(steps: List[PlanStep], dependencies: Dict[str, List[str]]) -> Tuple[bool, Optional[str]]:
        """Barcha bog'liqliklar mavjud qadamlarga ishora qilayotganini tekshirish"""
        valid_ids = {s.step_id for s in steps}
        for s_id, deps in dependencies.items():
            for dep in deps:
                if dep not in valid_ids:
                    return False, f"PLAN_MISSING_DEPENDENCY: Qadam '{s_id}' mavjud bo'lmagan qadamga ('{dep}') bog'langan"
        return True, None

    @staticmethod
    def detect_cycles(steps: List[PlanStep], dependencies: Dict[str, List[str]]) -> Optional[List[str]]:
        """
        Tsiklik bog'liqlikni aniqlash (DFS orqali).
        Agar tsikl aniqlansa, tsikl yo'lini ro'yxat ko'rinishida qaytaradi (masalan: ['s1', 's2', 's3', 's1']).
        Tsikl bo'lmasa, None qaytaradi.
        """
        all_nodes = [s.step_id for s in steps]
        # 0 = unvisited (white), 1 = visiting (gray), 2 = visited (black)
        visited: Dict[str, int] = {node: 0 for node in all_nodes}
        parent: Dict[str, Optional[str]] = {node: None for node in all_nodes}
        cycle_path: List[str] = []

        def dfs(u: str) -> bool:
            visited[u] = 1  # visiting
            # u qadami kimlarga bog'langan bo'lsa, u lar u dan oldin kelishi kerak
            # Demak yo'nalish: dep -> u (dep bajarilgach u bajariladi)
            # Yoki tahlil grafigi: agar v -> u qaramlik bo'lsa
            for v in dependencies.get(u, []):
                if v not in visited:
                    continue
                if visited[v] == 1:
                    # Tsikl topildi!
                    cycle_path.append(u)
                    curr = u
                    while curr != v and curr is not None:
                        curr = parent.get(curr)
                        if curr:
                            cycle_path.append(curr)
                    cycle_path.append(v)
                    cycle_path.reverse()
                    return True
                elif visited[v] == 0:
                    parent[v] = u
                    if dfs(v):
                        return True
            visited[u] = 2  # visited
            return False

        for node in all_nodes:
            if visited[node] == 0:
                if dfs(node):
                    return cycle_path if cycle_path else ["cycle_detected"]

        return []

    @staticmethod
    def compute_execution_order(steps: List[PlanStep], dependencies: Dict[str, List[str]]) -> List[str]:
        """
        Topologik saralash (Kahn algoritmi).
        Bog'liqliklar bo'yicha oldin bajarilishi shart bo'lgan qadamlar birinchi bo'lib chiqadi.
        """
        all_ids = [s.step_id for s in steps]
        in_degree: Dict[str, int] = {s_id: 0 for s_id in all_ids}
        dependents: Dict[str, List[str]] = defaultdict(list)

        for s_id, deps in dependencies.items():
            in_degree[s_id] = len(deps)
            for dep in deps:
                dependents[dep].append(s_id)

        # In-degree 0 bo'lgan qadamlar (hech kimga bog'liq bo'lmaganlar)
        queue = deque([s_id for s_id in all_ids if in_degree[s_id] == 0])
        order: List[str] = []

        while queue:
            curr = queue.popleft()
            order.append(curr)

            for dependent in dependents[curr]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Agar barcha qadamlar kirmagan bo'lsa (tsikl yoki to'liq bo'lmagan bog'liqlik),
        # qolganlarini asl tartibda qo'shamiz
        if len(order) < len(all_ids):
            for s_id in all_ids:
                if s_id not in order:
                    order.append(s_id)

        return order


# ========================================================
# 3. PLAN OPTIMIZER
# ========================================================

class PlanOptimizer:
    """
    Rejani optimallashtirish dvigateli.
    - Bir xil (dublikat) qadamlarni o'chiradi.
    - Xotirada / TaskContext da mavjud bo'lgan yangi va verifikatsiya qilingan natijalardan qayta foydalanadi.
    - Ortiqcha va keraksiz asbob chaqiruvlarini yo'q qiladi.
    """

    def __init__(self, task_context_manager: Optional[Any] = None):
        self.task_context_manager = task_context_manager

    def optimize(
        self_or_plan,
        plan_or_context=None,
        context: Optional[Any] = None,
        task_context_manager: Optional[Any] = None
    ):
        if isinstance(self_or_plan, AgentPlan):
            return PlanOptimizer.optimize_plan(
                self_or_plan,
                context=plan_or_context,
                task_context_manager=context or task_context_manager
            )
        else:
            mgr = task_context_manager or getattr(self_or_plan, "task_context_manager", None)
            plan = plan_or_context
            opt_plan, notes = PlanOptimizer.optimize_plan(
                plan,
                context=context,
                task_context_manager=mgr
            )
            if notes:
                opt_plan.metadata["optimized"] = True
                opt_plan.metadata["optimization_notes"] = notes
            return opt_plan

    @staticmethod
    def optimize_plan(
        plan: AgentPlan,
        context: Optional[Any] = None,
        task_context_manager: Optional[Any] = None
    ) -> Tuple[AgentPlan, List[str]]:
        """
        Rejani tahlil qilish va keraksiz amallardan tozalash.
        Qaytaradi: (optimized_plan, list_of_optimization_notes)
        """
        notes: List[str] = []
        if not plan.steps:
            return plan, notes

        optimized_steps: List[PlanStep] = []
        seen_actions: Dict[str, str] = {}  # action_key -> step_id

        # TaskContext dagi avvalgi muvaffaqiyatli amallar
        context_actions: Dict[str, Any] = {}
        if task_context_manager:
            try:
                active_task = task_context_manager.get_active_task()
                if active_task and hasattr(active_task, "action_history"):
                    for act in active_task.action_history:
                        if getattr(act, "action", None) and getattr(act, "result", None):
                            context_actions[str(act.action).lower()] = act.result
            except Exception as e:
                logger.debug(f"[PlanOptimizer] Context retrieval note: {e}")

        for step in plan.steps:
            # 1. Kontekstda mavjud bo'lgan yangi natijalardan foydalanish
            step_action = (step.tool or step.required_capability).lower()
            if step_action in context_actions and not step.parameters:
                cached_res = context_actions[step_action]
                step.observed_result = cached_res
                step.status = StepStatus.COMPLETED
                notes.append(f"Qadam #{step.order} ({step.tool}): mavjud kontekstdan natija qayta ishlatildi (keraksiz chaqiruv olib tashlandi)")
                optimized_steps.append(step)
                continue

            # 2. Dublikat qadamlarni yo'qotish (bir xil asbob va bir xil parametrlar)
            param_key = json.dumps(step.parameters, sort_keys=True)
            action_key = f"{step.tool}_{param_key}"

            if action_key in seen_actions and len(plan.steps) >= 2:
                prev_id = seen_actions[action_key]
                notes.append(f"Dublikat qadam #{step.order} ({step.tool}) o'chirildi; natija '{prev_id}' qadamidan olinadi")
                # Qaramliklarni prev_id ga yo'naltirish
                for other_step in plan.steps:
                    if step.step_id in other_step.dependencies:
                        other_step.dependencies = [
                            prev_id if d == step.step_id else d for d in other_step.dependencies
                        ]
                continue

            seen_actions[action_key] = step.step_id
            optimized_steps.append(step)

        # Qadamlar tartibini qayta raqamlash
        for idx, s in enumerate(optimized_steps, 1):
            s.order = idx

        plan.steps = optimized_steps
        # Yangi bog'liqliklar va tartibni qayta hisoblash
        dep_graph = DependencyGraph()
        plan.dependencies = dep_graph.build_graph(optimized_steps)
        plan.execution_order = dep_graph.compute_execution_order(optimized_steps, plan.dependencies)
        plan.calculate_plan_risk()

        return plan, notes


# ========================================================
# 4. PLAN VALIDATOR
# ========================================================

class PlanValidator:
    """
    Rejaning xavfsizlik, bog'liqlik va strukturaviy qoidalariga muvofiqligini qat'iy tekshirish.
    """

    MAX_STEPS = 8
    DANGEROUS_PATTERNS = ["__import__", "eval", "exec", "os.system", "subprocess", "shutil.rmtree"]

    def __init__(self, tool_registry: Optional[Any] = None, max_steps: int = 8):
        self.tool_registry = tool_registry
        self.max_steps = max_steps

    def validate(
        self_or_plan,
        plan_or_reg=None,
        tool_registry: Optional[Any] = None,
        max_steps: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        if isinstance(self_or_plan, AgentPlan):
            is_valid, err_code, err_msg = PlanValidator.validate_details(
                self_or_plan,
                tool_registry=plan_or_reg,
                max_steps=max_steps or PlanValidator.MAX_STEPS
            )
        else:
            reg = tool_registry or getattr(self_or_plan, "tool_registry", None)
            limit = max_steps or getattr(self_or_plan, "max_steps", PlanValidator.MAX_STEPS)
            is_valid, err_code, err_msg = PlanValidator.validate_details(
                plan_or_reg,
                tool_registry=reg,
                max_steps=limit
            )

        if not is_valid:
            return False, f"{err_code}: {err_msg}" if err_code else err_msg
        return True, None

    @staticmethod
    def validate_details(
        plan: AgentPlan,
        tool_registry: Optional[Any] = None,
        max_steps: int = 8
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Qaytaradi: (is_valid, error_code, error_message)
        """
        if not plan or not plan.steps:
            return False, "AGENT_PLAN_INVALID", "Rejada birorta ham qadam mavjud emas"

        # 1. Limit tekshiruvi
        if len(plan.steps) > max_steps:
            return (
                False,
                "AGENT_PLAN_INVALID",
                f"Qadamlar soni ruxsat etilgan limitdan oshib ketdi ({len(plan.steps)} > {max_steps})"
            )

        # 2. Bog'liqliklar mavjudligini tekshirish
        dep_graph = DependencyGraph()
        deps = plan.dependencies or dep_graph.build_graph(plan.steps)
        deps_exist, dep_err = dep_graph.validate_dependencies_exist(plan.steps, deps)
        if not deps_exist:
            return False, "PLAN_MISSING_DEPENDENCY", dep_err

        # 3. Tsiklik bog'liqlik tekshiruvi (Circular Dependencies)
        cycle = dep_graph.detect_cycles(plan.steps, deps)
        if cycle:
            return (
                False,
                "PLAN_CIRCULAR_DEPENDENCY",
                f"Rejada tsiklik bog'liqlik (Circular Dependency) aniqlandi: {' -> '.join(cycle)}"
            )

        # 4. Qadamlar va parametrlar xavfsizligi
        for step in plan.steps:
            tool_name = (step.tool or "").strip()
            if not tool_name:
                return False, "AGENT_PLAN_INVALID", f"Qadam #{step.order} da asbob nomi ko'rsatilmagan"

            # Kod inyeksiyasi tekshiruvi
            if any(p in tool_name.lower() for p in PlanValidator.DANGEROUS_PATTERNS):
                return False, "AGENT_PLAN_INVALID", f"Asbob nomida noqonuniy kod aniqlandi: '{tool_name}'"

            if not isinstance(step.parameters, dict):
                return False, "AGENT_PLAN_INVALID", f"Qadam #{step.order} parametrlari lug'at bo'lishi shart"

            param_str = json.dumps(step.parameters).lower()
            if any(p in param_str for p in PlanValidator.DANGEROUS_PATTERNS):
                # Faqat kod yozuvchi / sandbox vositalar ruxsat etiladi
                if step.tool not in ("file_write", "sandbox_execute_python", "sandbox"):
                    return False, "AGENT_PLAN_INVALID", f"Qadam #{step.order} parametrlarida ruxsatsiz xavfli kod inyeksiyasi aniqlandi"

            # Asbob mavjudligi tekshiruvi (agar registry berilgan bo'lsa)
            if tool_registry:
                has_tool = bool(tool_registry.get(tool_name))
                has_cap = bool(hasattr(tool_registry, "find_by_capability") and tool_registry.find_by_capability(tool_name))
                is_standard = tool_name in ["open_telegram", "open_chrome", "open_youtube", "open_code", "open_discord", "open_brave", "lock", "search", "close_window", "close_chrome"]
                if not (has_tool or has_cap or is_standard):
                    return False, "CAPABILITY_UNAVAILABLE", f"Noma'lum yoki mavjud bo'lmagan qobiliyat/asbob: '{tool_name}'"

        return True, None, None


# ========================================================
# 5. REPLANNING ENGINE
# ========================================================

class ReplanningEngine:
    """
    Qayta rejalashtirish (Replanning) dvigateli.
    Vaqtinchalik yoki doimiy to'siqlar yuzaga kelganda rejani xavfsiz moslashtiradi:
    - Tool nosozligida fallback qobiliyat/asbobni tanlash.
    - Yangi ma'lumotlar paydo bo'lganda keraksiz qadamlarni olib tashlash.
    - Reja versiyasini yangilash (v1 -> v2) va tarixni saqlash.
    - Qat'iy chegaralar: MAX_REPLANS = 2, Security-blocked holatlarida replan man etiladi.
    """

    MAX_REPLANS = 2

    def __init__(
        self,
        tool_registry: Optional[Any] = None,
        provider_manager: Optional[Any] = None,
        max_replans: int = 2
    ):
        self.tool_registry = tool_registry
        self.provider_manager = provider_manager
        self.max_replans = max_replans

    def evaluate_and_replan(
        self,
        plan: AgentPlan,
        failed_step: PlanStep,
        failure_reason: Optional[str] = None,
        step_result: Optional[StepResult] = None,
        tool_registry: Optional[Any] = None,
        context: Optional[Any] = None,
        request: Optional[Any] = None,
        max_replans: Optional[int] = None
    ) -> Tuple[bool, str]:
        reg = tool_registry or self.tool_registry
        limit = max_replans or getattr(self, "max_replans", ReplanningEngine.MAX_REPLANS)
        did_replan, _, reason = ReplanningEngine.evaluate_and_replan_static(
            plan=plan,
            failed_step=failed_step,
            step_result=step_result,
            failure_reason=failure_reason,
            tool_registry=reg,
            context=context,
            max_replans=limit
        )
        return did_replan, reason

    @staticmethod
    def evaluate_and_replan_static(
        plan: AgentPlan,
        failed_step: PlanStep,
        step_result: Optional[StepResult] = None,
        failure_reason: Optional[str] = None,
        tool_registry: Optional[Any] = None,
        context: Optional[Any] = None,
        max_replans: int = 2
    ) -> Tuple[bool, Optional[AgentPlan], str]:
        """
        Qaytaradi: (did_replan, new_plan_or_none, reason_explanation)
        """
        effective_max = min(plan.max_replans, max_replans)
        # 1. Replan limitini tekshirish (cheksiz tsiklning oldini olish)
        if plan.replan_count >= effective_max:
            msg = f"Qayta rejalashtirish limiti tugadi ({plan.replan_count}/{effective_max})"
            logger.warning(f"[ReplanningEngine] {msg}")
            return False, None, msg

        error_text = str((step_result.error if step_result and step_result.error else failure_reason) or "").lower()

        # 2. Xavfsizlik bo'yicha to'xtash (SECURITY_BLOCKED da replan qilinmaydi!)
        if "security_blocked" in error_text or ("xavfsizlik" in error_text and "chegarasi buzildi" in error_text):
            msg = "Xavfsizlik chegarasi buzilganligi sababli qayta rejalashtirish qat'iyan man etiladi (SECURITY_BLOCKED)"
            logger.error(f"[ReplanningEngine] {msg}")
            return False, None, msg

        # 3. Ruxsat rad etilganda (PERMISSION_DENIED da aylanib o'tilmaydi!)
        if "permission_denied" in error_text or "confirmation_required" in error_text:
            msg = "Foydalanuvchi tasdig'i yoki ruxsat talab etilganligi sababli avtomatik replan qilinmaydi"
            logger.warning(f"[ReplanningEngine] {msg}")
            return False, None, msg

        # 4. Fallback qobiliyat orqali qayta rejalashtirish (TOOL_UNAVAILABLE, TIMEOUT, EXECUTION_ERROR)
        if tool_registry and hasattr(tool_registry, "select_tool"):
            try:
                # Muqobil asbob topish
                lookup_caps = [failed_step.required_capability] if failed_step.required_capability else []
                t_obj = tool_registry.get(failed_step.tool)
                if t_obj and hasattr(t_obj, "capabilities"):
                    lookup_caps.extend([c for c in t_obj.capabilities if c != t_obj.name.lower()])
                if not lookup_caps:
                    lookup_caps = [failed_step.tool]

                fallback_found: Optional[ToolContract2] = None
                for cap in lookup_caps:
                    sel = tool_registry.select_tool(cap, candidate_params=failed_step.parameters)
                    if sel and sel.fallback_tool and sel.fallback_tool.name != failed_step.tool:
                        fallback_found = sel.fallback_tool
                        break
                    elif sel and sel.tool and sel.tool.name != failed_step.tool and sel.tool.health in (ToolHealth.AVAILABLE, ToolHealth.DEGRADED):
                        fallback_found = sel.tool
                        break

                if fallback_found:
                    old_tool = failed_step.tool
                    reason = f"Birlamchi asbob '{old_tool}' ishlamay qoldi; mos zaxira asbob '{fallback_found.name}' tanlandi."
                    
                    # Yangi versiya yaratish
                    plan.create_next_version(reason=reason, changed_steps=[failed_step.step_id])
                    failed_step.tool = fallback_found.name
                    failed_step.required_capability = fallback_found.capabilities[0] if fallback_found.capabilities else failed_step.required_capability
                    failed_step.status = StepStatus.PENDING
                    failed_step.retry_count = 0
                    failed_step.error = None
                    failed_step.failure_reason = f"Switched from {old_tool}"

                    logger.info(f"[ReplanningEngine] Reja v{plan.plan_version} ga yangilandi: {reason}")
                    return True, plan, reason

            except Exception as ex:
                logger.error(f"[ReplanningEngine] Fallback qidirishda xatolik: {ex}")

        # 5. Moslashuvchan qisqartirish (Opportunistic pruning)
        # Agar qadam qisman bajarilgan va qolgan qadamlar keraksiz bo'lsa
        if failed_step.observed_result and "no_issues_found" in str(failed_step.observed_result).lower():
            redundant_steps = [s.step_id for s in plan.steps if s.order > failed_step.order and "fix" in s.intent.lower()]
            if redundant_steps:
                reason = f"Tizimda muammo topilmaganligi sababli ortiqcha {len(redundant_steps)} ta qadam olib tashlandi."
                plan.create_next_version(reason=reason, changed_steps=redundant_steps)
                plan.steps = [s for s in plan.steps if s.step_id not in redundant_steps]
                return True, plan, reason

        return False, None, "Qayta rejalashtirish uchun mos alternativ yechim topilmadi"
