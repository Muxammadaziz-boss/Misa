# ========== core/multi_agent/registry.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Central Registry
# Manages agent configurations, typed registration, persistence, and discovery

import os
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Set, Any

from core.common_paths import get_data_path
from core.multi_agent.schema import AgentDefinition, AgentStatus
from core.multi_agent.initial_agents import get_initial_specialist_agents

logger = logging.getLogger("misa.multi_agent.registry")


class AgentRegistry:
    """
    Centralized Multi-Agent Registry for MISA.
    Stores and manages runtime agent definitions with thread safety and persistent storage.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._storage_path = storage_path or get_data_path("multi_agent_registry.json")
        self._agents: Dict[str, AgentDefinition] = {}
        self._load_or_initialize()

    def _load_or_initialize(self) -> None:
        """Load agents from storage file or initialize with 15 initial specialists."""
        with self._lock:
            loaded_from_disk = False
            if os.path.isfile(self._storage_path):
                try:
                    with open(self._storage_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list) and data:
                        for item in data:
                            try:
                                agent = AgentDefinition.from_dict(item)
                                self._agents[agent.agent_id] = agent
                            except Exception as ex:
                                logger.warning(f"Error parsing agent record from disk: {ex}")
                        loaded_from_disk = len(self._agents) > 0
                except Exception as e:
                    logger.error(f"Failed to load agent registry from {self._storage_path}: {e}")

            # Ensure built-in specialists are present
            initial_agents = get_initial_specialist_agents()
            updated = False
            for init_agent in initial_agents:
                if init_agent.agent_id not in self._agents:
                    self._agents[init_agent.agent_id] = init_agent
                    updated = True
                else:
                    # Maintain built-in flag
                    self._agents[init_agent.agent_id].is_builtin = True

            if not loaded_from_disk or updated:
                self._save_to_disk()

            logger.info(f"AgentRegistry initialized with {len(self._agents)} agents.")

    def _save_to_disk(self) -> None:
        """Persist registry to disk."""
        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            data = [agent.to_dict() for agent in self._agents.values()]
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to persist agent registry to {self._storage_path}: {e}")

    # ========================================================
    # CRUD Operations
    # ========================================================

    def register_agent(self, agent: AgentDefinition) -> AgentDefinition:
        """Register or update an agent definition with validation."""
        with self._lock:
            agent.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._agents[agent.agent_id] = agent
            self._save_to_disk()
            logger.info(f"Registered agent: {agent.agent_id} ({agent.name})")
            return agent

    def get_agent(self, agent_id: str) -> Optional[AgentDefinition]:
        """Fetch agent definition by ID."""
        with self._lock:
            return self._agents.get(str(agent_id).strip().lower())

    def list_agents(
        self,
        department: Optional[str] = None,
        status: Optional[AgentStatus] = None,
        only_active: bool = False
    ) -> List[AgentDefinition]:
        """List all agents with optional filtering."""
        with self._lock:
            results = list(self._agents.values())
            if department:
                dep_lower = department.strip().lower()
                results = [a for a in results if a.department.lower() == dep_lower]
            if status:
                results = [a for a in results if a.status == status]
            if only_active:
                results = [a for a in results if a.status in (AgentStatus.ACTIVE, AgentStatus.IDLE)]
            return results

    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> AgentDefinition:
        """Update fields of an existing agent with validation."""
        with self._lock:
            aid = str(agent_id).strip().lower()
            if aid not in self._agents:
                raise KeyError(f"Agent with ID '{agent_id}' does not exist.")

            current = self._agents[aid].to_dict()
            # Do not allow modifying agent_id or is_builtin via updates
            updates.pop("agent_id", None)
            updates.pop("is_builtin", None)

            # Deep update for nested structures
            for key in ["model_preference", "permission_profile", "context_policy", "memory_policy", "execution_limits"]:
                if key in updates and isinstance(updates[key], dict) and isinstance(current.get(key), dict):
                    current[key].update(updates[key])
                    updates.pop(key)

            current.update(updates)
            current["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Version bump if instructed or default minor bump
            if "version" not in updates and "status" not in updates:
                try:
                    parts = current["version"].split(".")
                    parts[-1] = str(int(parts[-1]) + 1)
                    current["version"] = ".".join(parts)
                except Exception:
                    pass

            updated_agent = AgentDefinition.from_dict(current)
            self._agents[aid] = updated_agent
            self._save_to_disk()
            logger.info(f"Updated agent: {aid} (v{updated_agent.version})")
            return updated_agent

    def delete_agent(self, agent_id: str) -> bool:
        """Delete a user-created agent safely. Built-in agents cannot be deleted."""
        with self._lock:
            aid = str(agent_id).strip().lower()
            if aid not in self._agents:
                return False
            agent = self._agents[aid]
            if agent.is_builtin:
                raise PermissionError(f"Cannot delete built-in system agent '{agent_id}'. You can disable it instead.")

            del self._agents[aid]
            self._save_to_disk()
            logger.info(f"Deleted user agent: {aid}")
            return True

    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent (sets status to ACTIVE)."""
        with self._lock:
            aid = str(agent_id).strip().lower()
            if aid not in self._agents:
                return False
            self._agents[aid].status = AgentStatus.ACTIVE
            self._agents[aid].updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._save_to_disk()
            return True

    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent (sets status to DISABLED)."""
        with self._lock:
            aid = str(agent_id).strip().lower()
            if aid not in self._agents:
                return False
            if aid == "misa-main":
                raise PermissionError("Cannot disable primary orchestrator 'misa-main'.")
            self._agents[aid].status = AgentStatus.DISABLED
            self._agents[aid].updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            self._save_to_disk()
            return True

    # ========================================================
    # Discovery & Query
    # ========================================================

    def find_agents_by_capability(self, capability: str) -> List[AgentDefinition]:
        """Find active agents capable of handling a given capability."""
        with self._lock:
            cap_lower = capability.strip().lower()
            return [
                a for a in self._agents.values()
                if a.status in (AgentStatus.ACTIVE, AgentStatus.IDLE)
                and any(cap_lower in c.lower() for c in a.capabilities)
            ]

    def find_agents_by_tool(self, tool_name: str) -> List[AgentDefinition]:
        """Find active agents that have access to a specific tool."""
        with self._lock:
            t_lower = tool_name.strip().lower()
            return [
                a for a in self._agents.values()
                if a.status in (AgentStatus.ACTIVE, AgentStatus.IDLE)
                and any(t_lower == t.lower() for t in a.available_tools)
            ]

    def find_agents_by_department(self, department: str) -> List[AgentDefinition]:
        """Find agents by department."""
        return self.list_agents(department=department)

    def get_all_capabilities(self) -> Set[str]:
        """Get the union of all registered agent capabilities."""
        with self._lock:
            caps: Set[str] = set()
            for a in self._agents.values():
                caps.update(a.capabilities)
            return caps

    def get_all_departments(self) -> List[str]:
        """Get unique departments in sorted order."""
        with self._lock:
            deps = {a.department for a in self._agents.values()}
            return sorted(list(deps))

    # ========================================================
    # Import / Export
    # ========================================================

    def export_agent_json(self, agent_id: str) -> str:
        """Export an agent configuration as formatted JSON."""
        with self._lock:
            agent = self.get_agent(agent_id)
            if not agent:
                raise KeyError(f"Agent '{agent_id}' not found.")
            return json.dumps(agent.to_dict(), indent=2, ensure_ascii=False)

    def import_agent_json(self, json_str: str, overwrite: bool = False) -> AgentDefinition:
        """Import an agent configuration from JSON string."""
        with self._lock:
            data = json.loads(json_str)
            agent = AgentDefinition.from_dict(data)
            if agent.agent_id in self._agents and not overwrite:
                raise ValueError(f"Agent '{agent.agent_id}' already exists and overwrite=False.")
            return self.register_agent(agent)

    def export_all_agents(self) -> List[Dict[str, Any]]:
        """Export all agents as a list of dictionaries."""
        with self._lock:
            return [a.to_dict() for a in self._agents.values()]

    def import_all_agents(self, agents_data: List[Dict[str, Any]], overwrite: bool = False) -> int:
        """Import a batch of agents from dictionary list."""
        with self._lock:
            count = 0
            for item in agents_data:
                try:
                    agent = AgentDefinition.from_dict(item)
                    if agent.agent_id in self._agents and not overwrite:
                        continue
                    self._agents[agent.agent_id] = agent
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to import agent item: {e}")
            if count > 0:
                self._save_to_disk()
            return count


# Singleton
_registry_instance: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_agent_registry(storage_path: Optional[str] = None) -> AgentRegistry:
    global _registry_instance
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = AgentRegistry(storage_path=storage_path)
        return _registry_instance
