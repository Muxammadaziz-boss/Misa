# ========== agent/lifecycle.py ==========
# Phase 45 — Windows PC Agent Lifecycle & Reconnection Manager
# Orchestrates enrollment, authentication, heartbeat, exponential backoff, and graceful shutdown

import asyncio
import logging
from typing import List

from core.v8.events import RemoteEventType
from agent.audit import AgentAuditLogger
from agent.config import AgentConfig
from agent.identity import AgentIdentityManager
from agent.crypto import AgentCrypto
from agent.transport import SecureTransport
from agent.enrollment import AgentEnrollment
from agent.auth import AgentAuth
from agent.heartbeat import AgentHeartbeat, AgentState
from agent.recovery import CrashRecoveryManager
from agent.executor import RemoteCommandExecutor, CommandPoller

logger = logging.getLogger("misa.agent.lifecycle")

BACKOFF_STEPS: List[float] = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 60.0]


def calculate_backoff(attempt: int) -> float:
    """Eksponensial kutish vaqtini hisoblash (1s, 2s, 4s, 8s, 16s, 30s, max 60s)"""
    if attempt < 0:
        return BACKOFF_STEPS[0]
    if attempt < len(BACKOFF_STEPS):
        return BACKOFF_STEPS[attempt]
    return 60.0


class AgentLifecycleManager:
    """
    Agentning to'liq hayot siklini boshqaruvchi markaziy menejer.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._audit = AgentAuditLogger.get_instance()

        # Komponentlar
        self.identity_mgr = AgentIdentityManager(config.vault_dir)
        self.identity = self.identity_mgr.get_or_create_identity(config.device_name)
        self.device_id = self.identity.device_id

        self.crypto = AgentCrypto(self.device_id, config.vault_dir)
        self.recovery = CrashRecoveryManager(config.vault_dir)
        self.transport = SecureTransport(
            backend_url=config.backend_url,
            ca_cert_path=config.ca_cert_path,
            device_id=self.device_id
        )
        self.enrollment = AgentEnrollment(self.transport, self.crypto, self.device_id)
        self.auth = AgentAuth(self.transport, self.crypto, self.device_id)
        self.heartbeat = AgentHeartbeat(
            transport=self.transport,
            device_id=self.device_id,
            interval_seconds=config.heartbeat_interval_seconds,
            agent_version=config.agent_version
        )
        self.executor = RemoteCommandExecutor(audit_logger=self._audit)
        self.poller = CommandPoller(
            transport=self.transport,
            device_id=self.device_id,
            executor=self.executor,
            poll_interval=self.config.poll_interval_seconds,
            audit_logger=self._audit
        )

        self._shutdown_event = asyncio.Event()
        self._is_running: bool = False
        self._reconnect_attempts: int = 0

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def start(self) -> bool:
        """
        Agentni xavfsiz ishga tushirish.
        1. Crash recovery tekshiruvi.
        2. Kredensial mavjudligini tekshirish (agar bo'lmasa, enrollment talab qilinadi).
        3. Autentifikatsiya va heartbeat ishga tushirish.
        4. Reconnect nazorati.
        """
        self._audit.log_event(
            event_type=RemoteEventType.AGENT_STARTED,
            device_id=self.device_id,
            details={
                "version": self.config.agent_version,
                "platform": self.identity.platform,
                "backend_url": self.config.backend_url
            }
        )

        # 1. Crash recovery tekshiruvi
        is_recovered = self.recovery.on_startup(self.device_id)
        if is_recovered:
            logger.info("[Lifecycle] Avvalgi nosozlikdan so'ng holat tiklandi")

        self._is_running = True
        self._shutdown_event.clear()

        # 2. Autentifikatsiya va ulanish
        auth_ok = await self._authenticate_and_connect()
        if not auth_ok:
            logger.warning("[Lifecycle] Dastlabki autentifikatsiya amalga oshmadi, qayta ulanish sikliga o'tiladi")

        return True

    async def _authenticate_and_connect(self) -> bool:
        """Autentifikatsiya o'tish, heartbeat va command pollerni boshlash"""
        self.heartbeat.state = AgentState.CONNECTING
        ok, msg, _ = await self.auth.authenticate()
        if ok:
            self._reconnect_attempts = 0
            self.heartbeat.state = AgentState.ONLINE
            self.heartbeat.start()
            await self.poller.start()
            logger.info("[Lifecycle] Agent ONLINE holatga o'tdi va command poller faollashtirildi")
            return True
        else:
            await self.poller.stop()
            logger.warning(f"[Lifecycle] Autentifikatsiya xatosi: {msg}")
            return False

    async def restart(self) -> bool:
        """Agentni xavfsiz to'xtatib, qayta ulanish (Restart)."""
        logger.info("[Lifecycle] Agent restart boshlandi...")
        await self.poller.stop()
        await self.heartbeat.stop()
        return await self._authenticate_and_connect()

    async def run_forever(self):
        """Asosiy sikl: to'xtatish signali kelgunga qadar yoki qayta ulanishni boshqarish"""
        while self._is_running and not self._shutdown_event.is_set():
            if self.heartbeat.state == AgentState.REVOKED:
                logger.critical("[Lifecycle] Qurilma bekor qilingan (REVOKED). Agent to'xtatilmoqda.")
                await self.poller.stop()
                break

            # Agar aloqa uzilgan yoki degradatsiyalangan bo'lsa, qayta ulanish
            if self.heartbeat.state in (AgentState.CONNECTING, AgentState.DEGRADED, AgentState.INITIALIZING):
                await self.poller.stop()
                delay = calculate_backoff(self._reconnect_attempts)
                self._audit.log_event(
                    event_type=RemoteEventType.RECONNECT_STARTED,
                    device_id=self.device_id,
                    details={
                        "attempt": self._reconnect_attempts,
                        "delay_seconds": delay
                    }
                )
                logger.info(f"[Lifecycle] {delay}s dan so'ng qayta ulanishga urinish (#{self._reconnect_attempts})")

                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=delay)
                    break  # Agar shutdown bo'lsa chiqish
                except asyncio.TimeoutError:
                    pass

                self._reconnect_attempts += 1
                success = await self._authenticate_and_connect()
                if success:
                    self._audit.log_event(
                        event_type=RemoteEventType.RECONNECT_SUCCESS,
                        device_id=self.device_id,
                        details={"attempts": self._reconnect_attempts}
                    )
                else:
                    self._audit.log_event(
                        event_type=RemoteEventType.RECONNECT_FAILED,
                        device_id=self.device_id,
                        details={"attempt": self._reconnect_attempts}
                    )

            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=2.0)
                break
            except asyncio.TimeoutError:
                pass

        await self.shutdown()

    async def shutdown(self):
        """Xavfsiz va toza to'xtatish (Graceful Shutdown)"""
        if not self._is_running:
            return

        logger.info("[Lifecycle] Graceful shutdown boshlandi...")
        self._audit.log_event(
            event_type=RemoteEventType.AGENT_STOPPING,
            device_id=self.device_id,
            details={"action": "graceful_shutdown"}
        )

        self._shutdown_event.set()
        self._is_running = False

        # 1. Command poller to'xtatish (yangi buyruqlar qabul qilinmaydi)
        try:
            await self.poller.stop()
        except Exception as e:
            logger.warning(f"[Lifecycle] Poller to'xtatishda xatolik: {e}")

        # 2. Heartbeat to'xtatish
        try:
            await self.heartbeat.stop()
        except Exception as e:
            logger.warning(f"[Lifecycle] Heartbeat to'xtatishda xatolik: {e}")

        # 3. Transport sessiyasini yopish
        try:
            await self.transport.close()
        except Exception as e:
            logger.warning(f"[Lifecycle] Transport yopishda xatolik: {e}")

        # 4. Xotiradagi maxfiy kalitlarni tozalash (Memory wiping)
        try:
            self.crypto.clean_memory()
        except Exception as e:
            logger.warning(f"[Lifecycle] Crypto xotirasini tozalashda xatolik: {e}")

        # 5. Crash recovery bayrog'ini toza yopish (clean_exit=True)
        try:
            self.recovery.on_clean_shutdown(self.device_id)
        except Exception as e:
            logger.warning(f"[Lifecycle] Recovery clean shutdown belgilashda xatolik: {e}")

        self._audit.log_event(
            event_type=RemoteEventType.AGENT_STOPPED,
            device_id=self.device_id,
            details={"status": "clean_exit"}
        )
        logger.info("[Lifecycle] Agent muvaffaqiyatli to'xtatildi")
