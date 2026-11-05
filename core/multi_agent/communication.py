# ========== core/multi_agent/communication.py ==========
# Misa AI 9.0.0 — Native Multi-Agent Structured Communication Protocol
# Handles inter-agent messaging, routing, correlation, history, and message validation

import time
import uuid
import logging
import threading
from typing import Dict, List, Optional, Callable, Any, Set
from collections import defaultdict

from core.multi_agent.schema import AgentMessage, MessageType

logger = logging.getLogger("misa.multi_agent.communication")


class MessageBroker:
    """
    Centralized In-Memory Message Broker for Multi-Agent Communication.
    Routes messages between agents, maintains correlation chains, and enforces message schemas.
    """

    def __init__(self, max_history: int = 1000):
        self._lock = threading.RLock()
        self._max_history = max_history
        self._messages: List[AgentMessage] = []
        self._listeners: Dict[str, List[Callable[[AgentMessage], None]]] = defaultdict(list)
        self._global_listeners: List[Callable[[AgentMessage], None]] = []

    def send_message(self, message: AgentMessage) -> AgentMessage:
        """
        Validates, records, and routes an AgentMessage to its recipient or global listeners.
        """
        with self._lock:
            # Set defaults if missing
            if not message.message_id:
                message.message_id = f"msg_{uuid.uuid4().hex[:12]}"
            if not message.timestamp:
                message.timestamp = time.time()
            if not message.correlation_id:
                message.correlation_id = message.task_id or message.message_id

            # Store in history (bounded)
            self._messages.append(message)
            if len(self._messages) > self._max_history:
                self._messages = self._messages[-self._max_history:]

            # Dispatch to recipient specific listeners
            recipient = str(message.recipient_agent).strip().lower()
            rec_listeners = list(self._listeners.get(recipient, []))

            # Dispatch to global listeners
            glob_listeners = list(self._global_listeners)

        # Notify outside lock to prevent deadlocks
        for cb in rec_listeners:
            try:
                cb(message)
            except Exception as e:
                logger.error(f"Error in recipient message callback ({recipient}): {e}")

        for gcb in glob_listeners:
            try:
                gcb(message)
            except Exception as e:
                logger.error(f"Error in global message callback: {e}")

        logger.debug(
            f"Message {message.message_id} [{message.message_type.value}]: "
            f"{message.sender_agent} -> {message.recipient_agent}"
        )
        return message

    def subscribe(self, agent_id: str, callback: Callable[[AgentMessage], None]) -> None:
        """Subscribe to messages addressed to a specific agent."""
        with self._lock:
            aid = str(agent_id).strip().lower()
            if callback not in self._listeners[aid]:
                self._listeners[aid].append(callback)

    def unsubscribe(self, agent_id: str, callback: Callable[[AgentMessage], None]) -> None:
        """Unsubscribe from messages."""
        with self._lock:
            aid = str(agent_id).strip().lower()
            if callback in self._listeners[aid]:
                self._listeners[aid].remove(callback)

    def subscribe_global(self, callback: Callable[[AgentMessage], None]) -> None:
        """Subscribe to all messages traversing the broker."""
        with self._lock:
            if callback not in self._global_listeners:
                self._global_listeners.append(callback)

    def unsubscribe_global(self, callback: Callable[[AgentMessage], None]) -> None:
        with self._lock:
            if callback in self._global_listeners:
                self._global_listeners.remove(callback)

    # ========================================================
    # Query & Tracing
    # ========================================================

    def get_messages(
        self,
        conversation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentMessage]:
        """Query historical messages with filtering."""
        with self._lock:
            results = self._messages
            if conversation_id:
                results = [m for m in results if m.conversation_id == conversation_id]
            if task_id:
                results = [m for m in results if m.task_id == task_id]
            if correlation_id:
                results = [m for m in results if m.correlation_id == correlation_id]
            return results[-limit:]

    def clear_history(self) -> None:
        with self._lock:
            self._messages.clear()


# Singleton
_broker_instance: Optional[MessageBroker] = None
_broker_lock = threading.Lock()


def get_message_broker() -> MessageBroker:
    global _broker_instance
    with _broker_lock:
        if _broker_instance is None:
            _broker_instance = MessageBroker()
        return _broker_instance
