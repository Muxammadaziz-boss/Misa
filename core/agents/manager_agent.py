# ========== manager_agent.py ==========
# Multi-Agent: ManagerAgent
# Asosiy agent — vazifalarni sub-agentlarga bo'lib beradi

import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from .base_agent import BaseAgent
from .coder_agent import CoderAgent
from .research_agent import ResearchAgent
from .system_agent import SystemAgent
from core.tools.security_policy import get_security_policy

logger = logging.getLogger(__name__)


class Task:
    """Vazifa — sub-agentga beriladigan ish birligi"""

    def __init__(self, description: str, assigned_to: Optional[str] = None):
        self.description = description
        self.assigned_to = assigned_to
        self.status = "pending"
        self.result = None


class ManagerAgent(BaseAgent):
    """
    ManagerAgent — asosiy koordinator.
    Kelgan vazifalarni tahlil qiladi va to'g'ri sub-agentga yo'naltiradi.
    Human-in-the-Loop va cheksiz tsikllardan himoya (OWASP LLM06 / MISA-ROOT-006, MISA-ROOT-013) bilan ta'minlangan.
    """

    MAX_RECURSION_DEPTH = 10

    def __init__(self, ai_call_func: Callable):
        super().__init__(
            name="ManagerAgent",
            specialty="Vazifa taqsimlash va koordinatsiya",
            ai_call_func=ai_call_func,
        )

        self._sub_agents: Dict[str, BaseAgent] = {}
        self._tasks: List[Task] = []
        self._active_plan: Optional[Dict[str, Any]] = None
        self._step_listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._recursion_depth = 0
        self._security_policy = get_security_policy()
        self._init_sub_agents(ai_call_func)

    def _init_sub_agents(self, ai_call_func: Callable):
        """Sub-agentlarni ishga tushirish"""
        try:
            self._sub_agents["coder"] = CoderAgent(ai_call_func)
            self._sub_agents["research"] = ResearchAgent(ai_call_func)
            self._sub_agents["system"] = SystemAgent(ai_call_func)
            logger.info("Sub-agents initialized: coder, research, system")
        except Exception as e:
            logger.error(f"Sub-agents init xatolik: {e}")

    def _build_system_prompt(self) -> str:
        return """Sen ManagerAgent — Misa AI'ning asosiy koordinatorisan.

Senning vazifang:
1. Kelgan vazifalarni tahlil qilish
2. Ularni to'g'ri sub-agentlarga yo'naltirish
3. Natijalarni birlashtirish

Mavjud sub-agentlar:
- CoderAgent: kod tahlili va yozish
- ResearchAgent: web qidiruv va tadqiqot
- SystemAgent: kompyuter tizimi (RAM, CPU, disk, optimallashtirish) monitoringi

Qoidalaring:
- Har bir vazifa uchun eng mos agentni tanla
- murakkab vazifalarni kichik qismlarga bo'l
- Natijalarni foydalanuvchiga tushunarli qil

Muloqot tili: O'zbekcha (Asalim uchun)
"""

    def can_handle(self, task: str) -> bool:
        """Barcha vazifalarni Manager qabul qiladi"""
        return True

    def add_step_listener(self, listener: Callable[[Dict[str, Any]], None]):
        """Agent rejasidagi qadamlar o'zgarishini kuzatish uchun listener qo'shish"""
        if listener not in self._step_listeners:
            self._step_listeners.append(listener)

    def _notify_step(self, step_event: Dict[str, Any]):
        """Qadam hodisasini barcha kuzatuvchilarga uzatish"""
        for listener in self._step_listeners:
            try:
                listener(step_event)
            except Exception as e:
                logger.debug(f"Step listener xatosi: {e}")

    def plan(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Vazifa bo'yicha shaffof ijro rejasini (Plan) tuzish (MISA-ROOT-013).
        Qora quti o'rniga foydalanuvchiga har bir qadamni ko'rsatish imkonini beradi.
        """
        context = context or {}
        task_lower = task.lower()
        steps = []

        coder_keywords = ["code", "python", "javascript", "fayl", "file", "yoz", "debug"]
        research_keywords = ["qidir", "search", "web", "internet", "youtube", "github"]
        system_keywords = ["tizim", "sistema", "ram", "cpu", "xotira", "tozala", "temp", "monitoring", "nagruzka"]

        if any(k in task_lower for k in coder_keywords):
            assigned = "coder"
            intent = "Kod tahlili yoki fayl amallari"
        elif any(k in task_lower for k in research_keywords):
            assigned = "research"
            intent = "Internetdan ma'lumot qidirish"
        elif any(k in task_lower for k in system_keywords):
            assigned = "system"
            intent = "Tizim diagnostikasi va resurslar tahlili"
        else:
            assigned = "direct"
            intent = "To'g'ridan-to'g'ri AI orqali hal etish"

        # Xavfsizlik siyosatini baholash
        decision = self._security_policy.evaluate(task, params=context)

        step_item = {
            "step_id": "step_1",
            "order": 1,
            "intent": intent,
            "tool": f"manager_{assigned}",
            "description": task,
            "parameters": context,
            "risk_level": "high" if decision.requires_confirmation else "low",
            "status": "waiting_confirmation" if decision.requires_confirmation else "pending",
            "requires_confirmation": decision.requires_confirmation,
            "prompt": decision.prompt if decision.requires_confirmation else None,
            "challenge_token": decision.challenge_token if decision.requires_confirmation else None,
        }
        steps.append(step_item)

        plan_data = {
            "plan_id": f"plan_{len(self._tasks) + 1}",
            "goal": task,
            "status": "waiting_confirmation" if decision.requires_confirmation else "running",
            "risk_level": "high" if decision.requires_confirmation else "low",
            "steps": steps,
            "current_step_index": 0,
            "max_steps": len(steps)
        }
        self._active_plan = plan_data
        self._notify_step({"type": "plan_created", "plan": plan_data})
        return plan_data

    def execute(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Vazifani bajarish — sub-agentlarga yo'naltirish (HITL va Rekursiya nazorati bilan)"""
        context = context or {}

        if self._recursion_depth >= self.MAX_RECURSION_DEPTH:
            logger.error(f"ManagerAgent: Maksimal rekursiya chegarasiga yetildi ({self.MAX_RECURSION_DEPTH})")
            return {
                "status": "error",
                "error": f"Maksimal rekursiya chegarasiga yetildi ({self.MAX_RECURSION_DEPTH}). Cheksiz tsikl to'xtatildi.",
                "recursion_limit_hit": True
            }

        self._recursion_depth += 1
        try:
            # 1. Human-in-the-Loop xavfsizlik tekshiruvi (MISA-ROOT-006)
            confirmation_token = context.get("confirmation_token")
            eval_params = {k: v for k, v in context.items() if k != "confirmation_token"}
            decision = self._security_policy.evaluate(
                tool_name=task,
                params=eval_params,
                confirmation_token=confirmation_token
            )

            if decision.requires_confirmation and not decision.allowed:
                logger.warning(f"ManagerAgent: Destruktiv amal tasdiqlash talab qiladi ({decision.reason})")
                return {
                    "status": "requires_confirmation",
                    "requires_confirmation": True,
                    "prompt": decision.prompt or f"'{task}' amalini bajarishni tasdiqlaysizmi?",
                    "challenge_token": decision.challenge_token,
                    "risk_level": str(decision.risk_level),
                    "reason": decision.reason,
                    "task": task
                }

            # 2. Shaffof reja (Plan) yaratish (MISA-ROOT-013)
            current_plan = self.plan(task, context)

            coder_keywords = ["code", "python", "javascript", "fayl", "file", "yoz", "debug"]
            research_keywords = ["qidir", "search", "web", "internet", "youtube", "github"]
            system_keywords = ["tizim", "sistema", "ram", "cpu", "xotira", "tozala", "temp", "monitoring", "nagruzka"]

            task_lower = task.lower()

            if any(k in task_lower for k in coder_keywords):
                return self._delegate_to_agent("coder", task, context)

            if any(k in task_lower for k in research_keywords):
                return self._delegate_to_agent("research", task, context)

            if any(k in task_lower for k in system_keywords):
                return self._delegate_to_agent("system", task, context)

            return self._direct_execute(task, context)

        finally:
            self._recursion_depth = max(0, self._recursion_depth - 1)

    def _delegate_to_agent(
        self, agent_name: str, task: str, context: Dict
    ) -> Dict[str, Any]:
        """Sub-agentga vazifa berish"""
        agent = self._sub_agents.get(agent_name)

        if not agent:
            return {"status": "error", "error": f"{agent_name} topilmadi"}

        if not agent.can_handle(task):
            return {
                "status": "error",
                "error": f"{agent_name} bu vazifani bajara olmaydi",
                "suggestion": "Boshqa agentga yo'naltiring",
            }

        task_record = Task(description=task, assigned_to=agent_name)
        self._tasks.append(task_record)

        self._notify_step({
            "type": "step_update",
            "step_id": "step_1",
            "status": "running",
            "delegated_to": agent_name
        })

        try:
            result = agent.run(task, context)
            task_record.result = result
            task_record.status = "completed"

            self._notify_step({
                "type": "step_update",
                "step_id": "step_1",
                "status": "completed",
                "delegated_to": agent_name,
                "result_summary": str(result)[:200] if result else "OK"
            })

            return {
                "status": "success",
                "delegated_to": agent_name,
                "result": result,
                "task_id": len(self._tasks) - 1,
                "plan": self._active_plan
            }

        except Exception as e:
            task_record.status = "failed"
            logger.error(f"Agent delegation xatolik: {e}")
            self._notify_step({
                "type": "step_update",
                "step_id": "step_1",
                "status": "failed",
                "delegated_to": agent_name,
                "error": str(e)
            })
            return {"status": "error", "error": str(e), "delegated_to": agent_name}

    def _direct_execute(self, task: str, context: Dict) -> Dict[str, Any]:
        """To'g'ridan-to'g'ri bajarish — AI orqali"""
        try:
            self._notify_step({
                "type": "step_update",
                "step_id": "step_1",
                "status": "running",
                "delegated_to": "direct_ai"
            })
            result = self.ai_call_func(task, context)
            self._notify_step({
                "type": "step_update",
                "step_id": "step_1",
                "status": "completed",
                "delegated_to": "direct_ai"
            })
            return {"status": "success", "direct": True, "result": result, "plan": self._active_plan}
        except Exception as e:
            logger.error(f"Direct execute xatolik: {e}")
            self._notify_step({
                "type": "step_update",
                "step_id": "step_1",
                "status": "failed",
                "delegated_to": "direct_ai",
                "error": str(e)
            })
            return {"status": "error", "error": str(e)}

    def get_sub_agents(self) -> List[str]:
        """Mavjud sub-agentlar ro'yxati"""
        return list(self._sub_agents.keys())

    def get_sub_agent_stats(self) -> Dict[str, Dict]:
        """Barcha sub-agentlar statistikasi"""
        return {name: agent.get_stats() for name, agent in self._sub_agents.items()}

    def get_tasks(self) -> List[Dict]:
        """Bajarilgan vazifalar ro'yxati"""
        return [
            {
                "description": t.description,
                "assigned_to": t.assigned_to,
                "status": t.status,
            }
            for t in self._tasks[-20:]
        ]
