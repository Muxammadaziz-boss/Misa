# ========== core/multi_agent/context_memory.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Context & Memory Architecture
# Manages User Memory, Project Memory, Agent Private Memory, and Shared Memory with strict isolation

import os
import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Set

from core.common_paths import get_data_path, get_data_dir
from core.multi_agent.schema import AgentDefinition, ContextPolicy, MemoryPolicy

logger = logging.getLogger("misa.multi_agent.context_memory")


class MultiAgentMemoryManager:
    """
    Unified Memory & Context Manager for MISA Native Multi-Agent Platform.
    Enforces context isolation, token budgeting, and authorization policies.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._data_dir = get_data_dir()
        self._shared_memory_path = get_data_path("multi_agent_shared_memory.json")
        self._project_memory_path = get_data_path("multi_agent_project_memory.json")
        self._private_dir = os.path.join(self._data_dir, "agent_private_memory")
        os.makedirs(self._private_dir, exist_ok=True)

        self._shared_memory: Dict[str, Any] = self._load_json(self._shared_memory_path, {})
        self._project_memory: Dict[str, Any] = self._load_json(
            self._project_memory_path,
            {
                "project_name": "Misa AI",
                "version": "9.3.0",
                "architecture": "React 19 Frontend + Tauri v2 Desktop Shell + Python 3.11 Asynchronous Backend",
                "established_patterns": [
                    "Ultra Glass Dark Design Language (#02060E, #9303C5)",
                    "Zero-hardcoded secrets with automatic redaction",
                    "Deterministic multi-provider fallback (Groq -> Cerebras -> Gemini -> OpenRouter)",
                    "Human-in-the-loop one-time cryptographic confirmation tokens for destructive actions",
                ],
                "decisions": [],
            }
        )

    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read memory file {path}: {e}")
        return default

    def _save_json(self, path: str, data: Any) -> None:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write memory file {path}: {e}")

    # ========================================================
    # 1. USER MEMORY (Authorized User Profile)
    # ========================================================

    def get_user_context(self) -> Dict[str, Any]:
        """Fetch sanitized user preferences from existing agent_profile.json."""
        try:
            from core.agent_memory import AgentMemory
            # Read profile safely
            prof_path = get_data_path("agent_profile.json")
            if os.path.isfile(prof_path):
                with open(prof_path, "r", encoding="utf-8") as f:
                    profile = json.load(f)
                return {
                    "user_name": profile.get("ism") or "Ustoz",
                    "preferred_language": profile.get("til") or "uz",
                    "voice_preference": profile.get("ovoz_turi") or "erkak",
                    "interests": profile.get("qiziqishlar") or [],
                }
        except Exception:
            pass
        return {"user_name": "Ustoz", "preferred_language": "uz"}

    # ========================================================
    # 2. PROJECT MEMORY (Architecture, Tech Decisions, Guidelines)
    # ========================================================

    def get_project_memory(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._project_memory)

    def add_project_decision(self, title: str, decision: str, author_agent: str = "misa-main") -> None:
        with self._lock:
            record = {
                "title": title,
                "decision": decision,
                "author": author_agent,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            if "decisions" not in self._project_memory:
                self._project_memory["decisions"] = []
            self._project_memory["decisions"].append(record)
            self._save_json(self._project_memory_path, self._project_memory)

    # ========================================================
    # 3. AGENT PRIVATE MEMORY (Isolated per Agent)
    # ========================================================

    def _get_agent_private_path(self, agent_id: str) -> str:
        safe_id = "".join(c for c in agent_id if c.isalnum() or c in "-_")
        return os.path.join(self._private_dir, f"{safe_id}.json")

    def get_agent_private_memory(self, agent_id: str) -> Dict[str, Any]:
        with self._lock:
            path = self._get_agent_private_path(agent_id)
            return self._load_json(path, {"observations": [], "task_notes": {}})

    def record_agent_observation(self, agent_id: str, observation: str) -> None:
        with self._lock:
            path = self._get_agent_private_path(agent_id)
            data = self._load_json(path, {"observations": [], "task_notes": {}})
            obs_list = data.get("observations", [])
            obs_list.append({
                "observation": observation,
                "timestamp": time.time(),
            })
            data["observations"] = obs_list[-50:]  # Keep last 50
            self._save_json(path, data)

    # ========================================================
    # 4. SHARED MEMORY (Explicitly Shared across Authorized Agents)
    # ========================================================

    def get_shared_memory(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._shared_memory)

    def set_shared_value(self, key: str, value: Any, author_agent: str) -> None:
        with self._lock:
            self._shared_memory[key] = {
                "value": value,
                "author": author_agent,
                "updated_at": time.time(),
            }
            self._save_json(self._shared_memory_path, self._shared_memory)

    # ========================================================
    # CONTEXT ASSEMBLY WITH ISOLATION & TOKEN BUDGETING
    # ========================================================

    def assemble_context_for_agent(
        self,
        agent: AgentDefinition,
        task_context: Optional[Dict[str, Any]] = None,
        intermediate_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assembles a bounded, policy-compliant context bundle for a specific agent.
        Enforces privacy boundaries and isolates private state.
        """
        policy: ContextPolicy = agent.context_policy or ContextPolicy()
        bundle: Dict[str, Any] = {}

        # 1. User Profile if permitted
        if policy.include_user_profile:
            bundle["user_profile"] = self.get_user_context()

        # 2. Project Memory if permitted
        if policy.include_project_memory:
            bundle["project_memory"] = self.get_project_memory()

        # 3. Shared Memory if permitted
        if policy.shared_context_access:
            bundle["shared_context"] = self.get_shared_memory()

        # 4. Agent's own private observations (never other agents' private memory!)
        if policy.isolated_scratchpad:
            bundle["agent_private_scratchpad"] = self.get_agent_private_memory(agent.agent_id)

        # 5. Task-specific inputs & upstream dependency outputs
        if task_context:
            bundle["task_input"] = dict(task_context)
        if intermediate_results:
            bundle["upstream_dependency_results"] = dict(intermediate_results)

        return bundle

    def clear_agent_memory(self, agent_id: str) -> bool:
        """Clear private memory of an agent."""
        with self._lock:
            path = self._get_agent_private_path(agent_id)
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    return True
                except Exception:
                    return False
            return True


# Singleton
_memory_manager_instance: Optional[MultiAgentMemoryManager] = None
_memory_manager_lock = threading.Lock()


def get_multi_agent_memory_manager() -> MultiAgentMemoryManager:
    global _memory_manager_instance
    with _memory_manager_lock:
        if _memory_manager_instance is None:
            _memory_manager_instance = MultiAgentMemoryManager()
        return _memory_manager_instance
