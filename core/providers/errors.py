# ========== core/providers/errors.py ==========
# Misa AI 9.0.0 — Unified Provider Error Classification System

class ProviderError(Exception):
    """Barcha LLM provayder xatolarining asosiy klassi."""
    def __init__(self, message: str, provider: str = "unknown", model: str = "unknown", status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self):
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "provider": self.provider,
            "model": self.model,
            "status_code": self.status_code,
            "details": self.details,
        }


class AuthenticationError(ProviderError):
    """API kaliti yetishmayapti yoki yaroqsiz (HTTP 401, 403)."""
    pass


class RateLimitError(ProviderError):
    """So'rovlar yoki tokenlar kvotasi to'ldi (HTTP 429)."""
    def __init__(self, message: str, provider: str = "unknown", model: str = "unknown", retry_after_seconds: float = 60.0, **kwargs):
        super().__init__(message, provider=provider, model=model, status_code=429, **kwargs)
        self.retry_after_seconds = retry_after_seconds


class QuotaExceededError(ProviderError):
    """Oylik yoki kunlik qat'iy kvota tugagan."""
    pass


class TimeoutError(ProviderError):
    """Provayder belgilangan vaqt ichida javob bermadi."""
    def __init__(self, message: str, provider: str = "unknown", model: str = "unknown", timeout_seconds: float = 15.0, **kwargs):
        super().__init__(message, provider=provider, model=model, status_code=408, **kwargs)
        self.timeout_seconds = timeout_seconds


class ServerNetworkError(ProviderError):
    """Tarmoq xatosi, server ishlamayapti yoki 5xx xatolik (HTTP 500, 502, 503, 504)."""
    pass


class ModelUnavailableError(ProviderError):
    """So'ralgan model mavjud emas, eskirgan (deprecated) yoki o'chirilgan (HTTP 404)."""
    pass


class MalformedResponseError(ProviderError):
    """Provayder javobi buzilgan yoki kutilgan JSON formatga to'g'ri kelmaydi."""
    pass


class ProviderDisabledError(ProviderError):
    """Provayder administrator yoki konfiguratsiya tomonidan o'chirilgan."""
    pass
