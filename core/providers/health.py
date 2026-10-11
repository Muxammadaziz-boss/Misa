# ========== core/providers/health.py ==========
# Misa AI 9.0.0 — Provider Health Monitoring & Cooldown Management

import time
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from core.providers.base import ProviderHealth
from core.providers.errors import (
    ProviderError,
    RateLimitError,
    AuthenticationError,
    TimeoutError,
    ServerNetworkError,
    QuotaExceededError,
)

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    LLM Provayderlar salomatligi va cooldown (sovutish) holatini nazorat qiluvchi markaz.
    Avtomatik ravishda:
    - Kechikish (latency) ni hisoblaydi
    - Ketma-ket xatoliklarni kuzatadi
    - 429 / Timeout / Server xatolarida eksponentsial sovutish (cooldown) belgilaydi
    - Cooldown muddati o'tgach, provayderni avtomatik tiklaydi (auto-heal)
    """

    def __init__(self):
        self._states: Dict[str, ProviderHealth] = {}
        self._default_cooldown: float = 60.0  # soniya
        self._max_cooldown: float = 600.0     # 10 daqiqa

    def _get_or_create(self, provider: str) -> ProviderHealth:
        p = provider.lower()
        if p not in self._states:
            self._states[p] = ProviderHealth(provider=p)
        return self._states[p]

    def record_success(self, provider: str, latency_ms: float = 0.0) -> ProviderHealth:
        """Muvaffaqiyatli so'rovni qayd etish."""
        state = self._get_or_create(provider)
        now_iso = datetime.now().isoformat()

        state.success_count += 1
        state.consecutive_failures = 0
        state.last_success = now_iso
        state.cooldown_until = None

        # Kechikishni hisoblash (Exponential Moving Average: 70% eski, 30% yangi)
        if state.latency_ms <= 0:
            state.latency_ms = max(0.0, latency_ms)
        else:
            state.latency_ms = (state.latency_ms * 0.7) + (max(0.0, latency_ms) * 0.3)

        if state.latency_ms > 4000.0:
            state.status = "degraded"
        else:
            state.status = "healthy"

        logger.debug(f"[HealthMonitor] {provider} muvaffaqiyat: {round(latency_ms, 1)}ms (holat={state.status})")
        return state

    def record_failure(self, provider: str, error: Exception, latency_ms: float = 0.0) -> ProviderHealth:
        """Xatolikni qayd etish va zarur bo'lsa cooldown belgilash."""
        state = self._get_or_create(provider)
        now_ts = time.time()
        now_iso = datetime.now().isoformat()

        state.failure_count += 1
        state.consecutive_failures += 1
        state.last_failure = now_iso
        if latency_ms > 0:
            state.latency_ms = max(state.latency_ms, latency_ms)

        # Xatolik turiga qarab cooldown hisoblash
        cooldown_sec = 0.0

        if isinstance(error, RateLimitError):
            state.rate_limit_count += 1
            # 429 xatosi: eksponentsial sovutish (masalan 60s, 120s, 240s)
            factor = min(4, state.consecutive_failures)
            cooldown_sec = getattr(error, "retry_after_seconds", self._default_cooldown) * factor
            cooldown_sec = min(self._max_cooldown, max(self._default_cooldown, cooldown_sec))
            state.status = "cooling_down"

        elif isinstance(error, QuotaExceededError):
            state.rate_limit_count += 1
            cooldown_sec = 1800.0  # 30 daqiqa
            state.status = "cooling_down"

        elif isinstance(error, AuthenticationError):
            # Kalit noto'g'ri bo'lsa butunlay o'chirish/unavailable qilish
            state.status = "unavailable"
            cooldown_sec = 3600.0

        elif isinstance(error, TimeoutError):
            if state.consecutive_failures >= 2:
                cooldown_sec = 30.0 * state.consecutive_failures
                state.status = "cooling_down"
            else:
                state.status = "degraded"

        elif isinstance(error, ServerNetworkError):
            cooldown_sec = 20.0 * min(3, state.consecutive_failures)
            state.status = "cooling_down"

        else:
            if state.consecutive_failures >= 3:
                cooldown_sec = 30.0
                state.status = "cooling_down"
            else:
                state.status = "degraded"

        if cooldown_sec > 0:
            state.cooldown_until = now_ts + cooldown_sec
            logger.warning(
                f"[HealthMonitor] {provider} {error.__class__.__name__} sababli "
                f"{round(cooldown_sec, 1)} soniyaga sovutishga qo'yildi (status={state.status})."
            )

        return state

    def is_cooling_down(self, provider: str) -> bool:
        """Provayder ayni paytda cooldown holatidami?"""
        state = self._get_or_create(provider)
        if not state.cooldown_until:
            return False

        now = time.time()
        if now < state.cooldown_until:
            return True

        # Cooldown muddati o'tgan bo'lsa, avtomatik qayta tiklash
        state.cooldown_until = None
        state.status = "healthy"
        logger.info(f"[HealthMonitor] {provider} cooldown muddati tugadi, qayta tiklandi.")
        return False

    def is_healthy_or_usable(self, provider: str) -> bool:
        """Provayder so'rov qabul qila oladimi?"""
        if self.is_cooling_down(provider):
            return False
        state = self._get_or_create(provider)
        return state.status in ("healthy", "degraded")

    def get_health(self, provider: str) -> ProviderHealth:
        """Bitta provayderning joriy salomatlik holati."""
        self.is_cooling_down(provider)  # Auto-refresh cooldown if expired
        return self._get_or_create(provider)

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Barcha provayderlar salomatlik xaritasini olish."""
        result = {}
        for p in list(self._states.keys()):
            self.is_cooling_down(p)
            result[p] = self._states[p].to_dict()
        return result

    def reset(self, provider: Optional[str] = None):
        """Barcha yoki bitta provayder holatini tozalash."""
        if provider:
            self._states.pop(provider.lower(), None)
        else:
            self._states.clear()


_global_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = HealthMonitor()
    return _global_health_monitor
