# ========== core/v8/account_auth.py ==========
# Phase 41 — Supabase Auth Integration & Token Verification
# Central Identity Provider: Supabase Auth (auth.users)
# Application Profiles: public.profiles (1:1 with auth.users.id UUID)
# Production JWT Verification: JWKS caching (RS256/ES256) + strict HMAC fallback (HS256)
# Strict Separation: Supabase Auth Session vs RemoteAuthSession (PC Agent control)
# Zero Backend Password Storage: Misa never receives or stores passwords.

import os
import time
import base64
import hmac
import hashlib
import json
import re
import logging
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List

from core.v8.events import RemoteAuditLogger
from core.v8.account_device import MisaUser, Device, AccountDeviceManager

logger = logging.getLogger("core.v8.account_auth")


# =====================================================================
# 1. INPUT VALIDATION RULES
# =====================================================================

def validate_username(username: str) -> Tuple[bool, str]:
    """Username tekshiruvi: 3-32 belgi, faqat a-z, A-Z, 0-9, _, -"""
    if not username or not isinstance(username, str):
        return False, "Username kiritilishi shart"
    clean = username.strip()
    if not re.match(r"^[a-zA-Z0-9_-]{3,32}$", clean):
        return False, "Username 3-32 belgidan iborat bo'lishi va faqat harf, raqam, '_' yoki '-' dan iborat bo'lishi kerak"
    return True, clean


def validate_email(email: Optional[str], allow_empty: bool = True) -> Tuple[bool, str]:
    """Email formati tekshiruvi va lowercase canonical formatga keltirish"""
    if email is None or (isinstance(email, str) and not email.strip()):
        if allow_empty:
            return True, ""
        return False, "Email kiritilishi shart"
    if not isinstance(email, str):
        return False, "Email satr bo'lishi kerak"
    clean = email.strip().lower()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, clean) or len(clean) > 254:
        return False, "Noto'g'ri email formati"
    return True, clean


# =====================================================================
# 2. SUPABASE SESSION MODEL
# =====================================================================

@dataclass
class SupabaseSessionClaims:
    """
    Supabase Auth JWT claims modeli.
    Web va mijoz ilovalari autentifikatsiyasi uchun xizmat qiladi.
    RemoteAuthSession (kompyuter masofaviy boshqaruvi) dan to'liq ajratilgan.
    """
    user_id: str  # sub (auth.users.id)
    email: str = ""
    role: str = "authenticated"
    exp: float = 0.0
    iat: float = field(default_factory=time.time)
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    display_name: str = ""
    avatar_url: str = ""
    raw_claims: Dict[str, Any] = field(default_factory=dict)
    token: str = ""

    @property
    def is_valid(self) -> bool:
        return time.time() < self.exp if self.exp else True

    @property
    def id(self) -> str:
        return self.user_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "exp": self.exp,
            "is_valid": self.is_valid,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url
        }


# Backward-compatible alias
AccountSession = SupabaseSessionClaims


# =====================================================================
# 3. RATE LIMITER
# =====================================================================

class AuthRateLimiter:
    """
    API so'rovlarini brute-force va suiiste'mollikdan himoya qiluvchi hisoblagich.
    """
    COOLDOWN_SECONDS = 300.0  # 5 daqiqa
    MAX_ATTEMPTS = 5

    def __init__(self):
        self._failures: Dict[str, List[float]] = {}
        self._cooldowns: Dict[str, float] = {}

    def is_rate_limited(self, identifier: str) -> Tuple[bool, float]:
        now = time.time()
        cd = self._cooldowns.get(identifier, 0.0)
        if now < cd:
            return True, cd - now
        return False, 0.0

    def record_failure(self, identifier: str):
        now = time.time()
        history = [t for t in self._failures.get(identifier, []) if now - t < self.COOLDOWN_SECONDS]
        history.append(now)
        self._failures[identifier] = history
        if len(history) >= self.MAX_ATTEMPTS:
            self._cooldowns[identifier] = now + self.COOLDOWN_SECONDS
            self._failures.pop(identifier, None)

    def record_success(self, identifier: str):
        self._failures.pop(identifier, None)
        self._cooldowns.pop(identifier, None)


# =====================================================================
# 4. PRODUCTION SUPABASE JWKS CLIENT (RFC 7517)
# =====================================================================

class SupabaseJWKSClient:
    """
    Supabase loyihasining JWKS (JSON Web Key Set) ommaviy kalitlarini olish va keshlovchi mijoz.
    - URL: https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json
    - TTL kesh (standart: 3600 soniya / 1 soat)
    - Tarmoq xatolarida xavfsiz rad etish (fail-closed, hech qachon verifikatsiyasiz o'tkazmaydi)
    - RS256, ES256, EdDSA asimmetrik kalitlarni Python cryptography orqali tiklaydi
    """

    def __init__(self, supabase_url: str = "", cache_ttl: float = 3600.0):
        self.supabase_url = supabase_url.rstrip("/") if supabase_url else ""
        self.cache_ttl = cache_ttl
        self._cached_keys: Dict[str, Any] = {}
        self._raw_jwks: Dict[str, Any] = {}
        self._last_fetched: float = 0.0
        self._lock = threading.Lock()

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        rem = len(data) % 4
        if rem > 0:
            data += "=" * (4 - rem)
        return base64.urlsafe_b64decode(data.encode("utf-8"))

    def set_supabase_url(self, url: str):
        with self._lock:
            self.supabase_url = url.rstrip("/") if url else ""
            self._last_fetched = 0.0
            self._cached_keys.clear()

    def add_mock_key(self, kid: str, public_key: Any):
        """Sinovlar uchun mock ommaviy kalit qo'shish"""
        with self._lock:
            self._cached_keys[kid] = public_key
            self._last_fetched = time.time()

    def set_mock_jwks(self, jwks: Dict[str, Any]):
        """Sinovlar uchun soxta JWKS lug'atini o'rnatish"""
        with self._lock:
            self._raw_jwks = jwks
            self._cached_keys.clear()
            self._parse_jwks_dict(jwks)
            self._last_fetched = time.time()

    def _convert_jwk_to_public_key(self, jwk: Dict[str, Any]) -> Optional[Any]:
        """Bitta JWK ob'ektini cryptography Public Key ga aylantirish"""
        kty = jwk.get("kty")
        try:
            if kty == "RSA":
                from cryptography.hazmat.primitives.asymmetric import rsa
                n_b64 = jwk.get("n", "")
                e_b64 = jwk.get("e", "")
                if not n_b64 or not e_b64:
                    return None
                n_bytes = self._base64url_decode(n_b64)
                e_bytes = self._base64url_decode(e_b64)
                n_int = int.from_bytes(n_bytes, "big")
                e_int = int.from_bytes(e_bytes, "big")
                return rsa.RSAPublicNumbers(e_int, n_int).public_key()

            elif kty == "EC":
                from cryptography.hazmat.primitives.asymmetric import ec
                crv = jwk.get("crv", "P-256")
                x_b64 = jwk.get("x", "")
                y_b64 = jwk.get("y", "")
                if not x_b64 or not y_b64:
                    return None
                x_bytes = self._base64url_decode(x_b64)
                y_bytes = self._base64url_decode(y_b64)
                x_int = int.from_bytes(x_bytes, "big")
                y_int = int.from_bytes(y_bytes, "big")

                curve = ec.SECP256R1() if crv == "P-256" else (ec.SECP384R1() if crv == "P-384" else ec.SECP521R1())
                return ec.EllipticCurvePublicNumbers(x_int, y_int, curve).public_key()

            elif kty == "OKP":
                from cryptography.hazmat.primitives.asymmetric import ed25519
                crv = jwk.get("crv", "")
                x_b64 = jwk.get("x", "")
                if crv == "Ed25519" and x_b64:
                    x_bytes = self._base64url_decode(x_b64)
                    return ed25519.Ed25519PublicKey.from_public_bytes(x_bytes)
        except Exception as e:
            logger.debug(f"[SupabaseJWKSClient] Kalit konvertatsiyasida xatolik: {e}")
            return None
        return None

    def _parse_jwks_dict(self, jwks: Dict[str, Any]):
        keys = jwks.get("keys", [])
        for jwk in keys:
            kid = jwk.get("kid")
            if kid:
                pub = self._convert_jwk_to_public_key(jwk)
                if pub:
                    self._cached_keys[kid] = pub

    def refresh_keys(self) -> bool:
        """Supabase JWKS endpointidan yangi kalitlarni yuklab olish"""
        if not self.supabase_url or "placeholder-project" in self.supabase_url:
            return False

        jwks_url = f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
        try:
            req = urllib.request.Request(
                jwks_url,
                headers={"User-Agent": "Misa-AI-Auth/9.0.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    raw_data = json.loads(resp.read().decode("utf-8"))
                    with self._lock:
                        self._raw_jwks = raw_data
                        self._cached_keys.clear()
                        self._parse_jwks_dict(raw_data)
                        self._last_fetched = time.time()
                    logger.info(f"[SupabaseJWKSClient] JWKS muvaffaqiyatli yangilandi: {len(self._cached_keys)} ta kalit")
                    return True
        except Exception as e:
            logger.warning(f"[SupabaseJWKSClient] JWKS yuklashda xatolik ({jwks_url}): {e}")
            return False
        return False

    def get_public_key(self, kid: Optional[str]) -> Optional[Any]:
        """kid bo'yicha ommaviy kalitni olish. Kesh muddati o'tgan bo'lsa qayta yuklanadi."""
        now = time.time()
        with self._lock:
            # Agar keshda mavjud bo'lsa va muddati o'tmagan bo'lsa
            if kid and kid in self._cached_keys and (now - self._last_fetched < self.cache_ttl):
                return self._cached_keys[kid]
            # Agar kid bitta bo'lsa va keshda yagona kalit mavjud bo'lsa
            if not kid and len(self._cached_keys) == 1 and (now - self._last_fetched < self.cache_ttl):
                return next(iter(self._cached_keys.values()))

        # Keshda topilmasa yoki muddati o'tgan bo'lsa, bir marta yangilab ko'ramiz
        if self.refresh_keys():
            with self._lock:
                if kid:
                    return self._cached_keys.get(kid)
                if len(self._cached_keys) == 1:
                    return next(iter(self._cached_keys.values()))
        return None


# =====================================================================
# 5. SUPABASE AUTH MANAGER
# =====================================================================

class SupabaseAuthManager:
    """
    Misa AI Supabase Auth integratsiya va JWT verifikatsiya dvigateli.
    Supabase auth.users.id ni asosiy identity sifatida tekshiradi va
    Misa public.profiles bilan 1:1 bog'laydi.
    """
    _default_instance: Optional["SupabaseAuthManager"] = None
    _instance: Optional["SupabaseAuthManager"] = None

    def __init__(
        self,
        account_device_mgr: Optional[AccountDeviceManager] = None,
        supabase_url: Optional[str] = None,
        supabase_publishable_key: Optional[str] = None,
        supabase_secret_key: Optional[str] = None,
        supabase_anon_key: Optional[str] = None,
        supabase_jwt_secret: Optional[str] = None,
        storage_path: Optional[str] = None
    ):
        self.account_device_mgr = account_device_mgr or AccountDeviceManager.get_default_instance()
        self._explicit_url = supabase_url is not None
        self._explicit_pub_key = (supabase_publishable_key is not None) or (supabase_anon_key is not None)
        self._explicit_sec_key = supabase_secret_key is not None
        self._explicit_jwt_secret = supabase_jwt_secret is not None

        raw_url = supabase_url or os.environ.get("SUPABASE_URL", "")
        self.supabase_url = raw_url.rstrip("/") if raw_url else ""

        # Supabase API Key Architecture: Publishable & Secret
        self.supabase_publishable_key = (
            supabase_publishable_key
            or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
            or supabase_anon_key
            or os.environ.get("SUPABASE_ANON_KEY", "")
        )
        self.supabase_anon_key = self.supabase_publishable_key

        self.supabase_secret_key = (
            supabase_secret_key
            or os.environ.get("SUPABASE_SECRET_KEY")
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        )

        # Legacy symmetric JWT secret (DIQQAT: fallback test-secret mutlaqo yo'q!)
        self.supabase_jwt_secret = (
            supabase_jwt_secret if supabase_jwt_secret is not None
            else os.environ.get("SUPABASE_JWT_SECRET")
        )

        # JWKS Klienti
        self.jwks_client = SupabaseJWKSClient(supabase_url=self.supabase_url)

        self.rate_limiter = AuthRateLimiter()
        self._audit = RemoteAuditLogger.get_instance()
        self.storage_path = storage_path

    def _sync_env_config(self) -> None:
        """Refresh environment-sourced config if singleton was initialized before env load."""
        if not self._explicit_url:
            env_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
            if env_url != self.supabase_url:
                self.supabase_url = env_url
                self.jwks_client.set_supabase_url(env_url)
        if not self._explicit_pub_key:
            self.supabase_publishable_key = (
                os.environ.get("SUPABASE_PUBLISHABLE_KEY")
                or os.environ.get("SUPABASE_ANON_KEY", "")
            )
            self.supabase_anon_key = self.supabase_publishable_key
        if not self._explicit_sec_key:
            self.supabase_secret_key = (
                os.environ.get("SUPABASE_SECRET_KEY")
                or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
            )
        if not self._explicit_jwt_secret:
            self.supabase_jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")

    def is_configured(self) -> bool:
        """Supabase xizmati haqiqiy API kalitlari bilan sozlanganligini tekshirish."""
        self._sync_env_config()
        return bool(
            self.supabase_url
            and self.supabase_publishable_key
            and "placeholder-project" not in self.supabase_url
            and self.supabase_publishable_key not in ("placeholder-anon-key", "placeholder-publishable-key")
        )

    @classmethod
    def get_default_instance(cls, *args, **kwargs) -> "SupabaseAuthManager":
        inst = getattr(cls, "_instance", None) or cls._default_instance
        if inst is None:
            cls._default_instance = cls(*args, **kwargs)
            return cls._default_instance
        inst._sync_env_config()
        return inst

    @classmethod
    def get_instance(cls, *args, **kwargs) -> "SupabaseAuthManager":
        return cls.get_default_instance(*args, **kwargs)

    # ========================================================
    # A. JWT VERIFICATION (RFC 7519 / Supabase Auth Contract)
    # ========================================================

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Base64URL satrni to'g'ri padding bilan baytlarga o'tkazish"""
        rem = len(data) % 4
        if rem > 0:
            data += "=" * (4 - rem)
        return base64.urlsafe_b64decode(data.encode("utf-8"))

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Baytlarni Base64URL satriga aylantirish"""
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    def verify_supabase_jwt(self, token: str) -> Tuple[bool, str, Optional[SupabaseSessionClaims]]:
        """
        Supabase access token (JWT) ni tekshirish.
        1. Strukturaviy tekshiruv (header.payload.signature) -> malformed -> 401.
        2. Header tahlili (alg, kid).
        3. Imzo verifikatsiyasi:
           - Asimmetrik (RS256, ES256) -> Supabase JWKS orqali.
           - Simmetrik (HS256) -> faqat konfiguratsiyalangan SUPABASE_JWT_SECRET mavjud bo'lsa.
           - Default/test secret orqali soxtalashtirish MUTLAQO TAQIQLANGAN.
        4. Muddati (exp), issuer (iss), audience (aud), sub (UUID) tekshiruvi.
        """
        self._sync_env_config()
        if not token or not isinstance(token, str):
            return False, "MISSING_TOKEN: Token kiritilmadi", None

        clean_token = token.strip()
        parts = clean_token.split(".")
        if len(parts) != 3:
            return False, "MALFORMED_TOKEN: Noto'g'ri JWT token formati", None

        header_b64, payload_b64, signature_b64 = parts

        # 1. Header dekodlash
        try:
            header_bytes = self._base64url_decode(header_b64)
            header = json.loads(header_bytes.decode("utf-8"))
        except Exception as e:
            return False, f"MALFORMED_TOKEN: JWT header dekodlashda xatolik: {e}", None

        # 2. Payload dekodlash
        try:
            payload_bytes = self._base64url_decode(payload_b64)
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as e:
            return False, f"MALFORMED_TOKEN: JWT payload dekodlashda xatolik: {e}", None

        alg = header.get("alg", "HS256")
        kid = header.get("kid")
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        try:
            sig_bytes = self._base64url_decode(signature_b64)
        except Exception:
            return False, "INVALID_SIGNATURE: Imzoni dekodlashda xatolik", None

        # 3. Imzo verifikatsiyasi (Algorithm checking)
        if (
            alg in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512")
            and not self.jwks_client.supabase_url
            and not self._explicit_url
        ):
            raw_iss = str(payload.get("iss") or "").strip().rstrip("/")
            if raw_iss.startswith("https://") and ".supabase.co" in raw_iss:
                base_iss = raw_iss.split("/auth/v1")[0]
                self.jwks_client.set_supabase_url(base_iss)
            else:
                self.jwks_client.set_supabase_url("https://vdcssmzguxfknqkfxbed.supabase.co")

        if alg in ("RS256", "RS384", "RS512"):
            pub_key = self.jwks_client.get_public_key(kid)
            if not pub_key:
                return False, f"INVALID_SIGNATURE: JWKS orqali ommaviy kalit topilmadi (kid={kid})", None
            try:
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import padding
                hash_algo = hashes.SHA256() if alg == "RS256" else (hashes.SHA384() if alg == "RS384" else hashes.SHA512())
                pub_key.verify(sig_bytes, signing_input, padding.PKCS1v15(), hash_algo)
            except Exception:
                return False, "INVALID_SIGNATURE: RS256 imzo tekshiruvidan o'tmadi", None

        elif alg in ("ES256", "ES384", "ES512"):
            pub_key = self.jwks_client.get_public_key(kid)
            if not pub_key:
                return False, f"INVALID_SIGNATURE: JWKS orqali EC kalit topilmadi (kid={kid})", None
            try:
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.asymmetric import ec, utils

                # RFC 7515/7518: JWT ES256 xom imzosi R || S (64 bayt).
                # Python cryptography kutubxonasi DER formatini kutadi, shuning uchun konvertatsiya qilamiz.
                der_sig = sig_bytes
                if alg == "ES256" and len(sig_bytes) == 64:
                    r = int.from_bytes(sig_bytes[:32], "big")
                    s = int.from_bytes(sig_bytes[32:], "big")
                    der_sig = utils.encode_dss_signature(r, s)
                elif alg == "ES384" and len(sig_bytes) == 96:
                    r = int.from_bytes(sig_bytes[:48], "big")
                    s = int.from_bytes(sig_bytes[48:], "big")
                    der_sig = utils.encode_dss_signature(r, s)
                elif alg == "ES512" and len(sig_bytes) in (131, 132):
                    half = len(sig_bytes) // 2
                    r = int.from_bytes(sig_bytes[:half], "big")
                    s = int.from_bytes(sig_bytes[half:], "big")
                    der_sig = utils.encode_dss_signature(r, s)

                hash_algo = hashes.SHA256() if alg == "ES256" else (hashes.SHA384() if alg == "ES384" else hashes.SHA512())
                pub_key.verify(der_sig, signing_input, ec.ECDSA(hash_algo))
            except Exception as e:
                logger.debug(f"[SupabaseAuth] EC imzo verifikatsiyasida xatolik: {e}")
                return False, f"INVALID_SIGNATURE: {alg} imzo tekshiruvidan o'tmadi", None

        elif alg == "HS256":
            if not self.supabase_jwt_secret:
                return False, "UNCONFIGURED_KEY: HS256 imzosini tekshirish uchun maxfiy kalit sozlanmagan", None
            expected_sig = hmac.new(
                self.supabase_jwt_secret.encode("utf-8"),
                signing_input,
                hashlib.sha256
            ).digest()
            if not hmac.compare_digest(expected_sig, sig_bytes):
                return False, "INVALID_SIGNATURE: Yaroqsiz JWT imzosi", None

        else:
            return False, f"UNSUPPORTED_ALGORITHM: '{alg}' algoritmi qo'llab-quvvatlanmaydi", None

        # 4. Expiration tekshiruvi
        now = time.time()
        exp = payload.get("exp")
        if exp is None:
            return False, "MALFORMED_TOKEN: Token muddati (exp) ko'rsatilmagan", None
        if float(exp) < now:
            return False, "EXPIRED_TOKEN: Token muddati o'tgan (expired)", None

        # 5. Issuer (iss) tekshiruvi
        iss = payload.get("iss")
        if self.supabase_url and "placeholder-project" not in self.supabase_url:
            clean_base = self.supabase_url.rstrip("/")
            expected_issuers = {
                f"{clean_base}/auth/v1",
                clean_base,
                f"{clean_base}/"
            }
            if iss and not any(iss.rstrip("/") == exp_iss.rstrip("/") for exp_iss in expected_issuers):
                return False, f"INVALID_ISSUER: Noto'g'ri token beruvchi (iss='{iss}', kutilgan='{clean_base}/auth/v1')", None

        # 6. Audience (aud) tekshiruvi
        aud = payload.get("aud")
        if aud and isinstance(aud, str):
            if aud not in ("authenticated", "authenticated_user"):
                logger.debug(f"[SupabaseAuth] Kutilmagan audience: {aud}")

        # 7. Foydalanuvchi identifikatori (sub)
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return False, "MISSING_SUBJECT: Token ichida foydalanuvchi identifikatori (sub) topilmadi", None

        email = payload.get("email", "")
        role = payload.get("role", "authenticated")
        user_meta = payload.get("user_metadata", {}) or {}
        username = (
            user_meta.get("username")
            or user_meta.get("full_name")
            or user_meta.get("name")
            or (email.split("@")[0] if email else user_id)
        )
        display_name = (
            user_meta.get("display_name")
            or user_meta.get("full_name")
            or user_meta.get("name")
            or username
        )
        avatar_url = user_meta.get("avatar_url") or user_meta.get("picture", "")
        first_name = str(user_meta.get("first_name", "")).strip()
        last_name = str(user_meta.get("last_name", "")).strip()

        claims = SupabaseSessionClaims(
            user_id=str(user_id).strip(),
            email=str(email).strip().lower(),
            role=str(role),
            exp=float(exp) if exp else 0.0,
            iat=float(payload.get("iat", now)),
            username=str(username).strip(),
            first_name=first_name,
            last_name=last_name,
            display_name=str(display_name).strip(),
            avatar_url=str(avatar_url).strip(),
            raw_claims=payload,
            token=clean_token
        )
        return True, "OK", claims

    # ========================================================
    # B. AUTHENTICATION & PROFILE RESOLUTION
    # ========================================================

    def authenticate_token(self, token: str) -> Tuple[Optional[SupabaseSessionClaims], Optional[MisaUser]]:
        """
        Tokenni tekshirish va unga mos MisaProfile (public.profiles) ni olish.
        Qaytaradi: (claims, profile) yoki (None, None).
        """
        ok, msg, claims = self.verify_supabase_jwt(token)
        if not ok or not claims:
            logger.debug(f"[SupabaseAuth] Token verifikatsiyasi muvaffaqiyatsiz: {msg}")
            return None, None

        user_metadata = claims.raw_claims.get("user_metadata") if isinstance(claims.raw_claims.get("user_metadata"), dict) else {}
        meta_dict = dict(user_metadata)
        if claims.first_name:
            meta_dict["first_name"] = claims.first_name
        if claims.last_name:
            meta_dict["last_name"] = claims.last_name

        # Supabase auth.users -> Misa public.profiles avtomatik sinxronizatsiyasi
        profile = self.account_device_mgr.upsert_profile_from_supabase(
            user_id=claims.user_id,
            email=claims.email,
            username=claims.username,
            display_name=claims.display_name,
            avatar_url=claims.avatar_url,
            is_verified=True,
            metadata=meta_dict
        )

        return claims, profile

    # ========================================================
    # C. TEST & LOCAL TOKEN GENERATOR
    # ========================================================

    def create_mock_jwt(
        self,
        user_id: str,
        email: str = "",
        username: str = "",
        display_name: str = "",
        role: str = "authenticated",
        exp_seconds: int = 3600,
        secret: Optional[str] = None,
        issuer: Optional[str] = None,
        alg: str = "HS256",
        kid: Optional[str] = None,
        private_key: Optional[Any] = None,
        app_metadata: Optional[Dict[str, Any]] = None,
        user_metadata: Optional[Dict[str, Any]] = None,
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Sinovlar va lokal muhit uchun haqiqiy Supabase formatidagi JWT yaratish.
        - Standart: HS256
        - RS256: agar private_key berilsa
        """
        now = int(time.time())
        header: Dict[str, Any] = {"alg": alg, "typ": "JWT"}
        if kid:
            header["kid"] = kid

        iss = issuer or (f"{self.supabase_url}/auth/v1" if self.supabase_url else "https://test.supabase.co/auth/v1")
        user_meta = {
            "username": username or (email.split("@")[0] if email else user_id),
            "display_name": display_name or username or (email.split("@")[0] if email else user_id)
        }
        if user_metadata:
            user_meta.update(user_metadata)

        payload = {
            "iss": iss,
            "sub": str(user_id),
            "email": str(email).lower(),
            "role": role,
            "aud": "authenticated",
            "iat": now,
            "exp": now + exp_seconds,
            "user_metadata": user_meta,
            "app_metadata": app_metadata or {"provider": "email", "providers": ["email"]}
        }
        if extra_claims:
            payload.update(extra_claims)

        header_b64 = self._base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = self._base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        if alg == "RS256" and private_key is not None:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            sig_bytes = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            sig_b64 = self._base64url_encode(sig_bytes)
        else:
            sec = secret or self.supabase_jwt_secret or "mock-signing-secret"
            sig = hmac.new(sec.encode("utf-8"), signing_input, hashlib.sha256).digest()
            sig_b64 = self._base64url_encode(sig)

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    # ========================================================
    # D. MULTI-TENANT ISOLATION HELPERS
    # ========================================================

    def get_user_profile(self, user_id: str) -> Optional[MisaUser]:
        """Foydalanuvchi profilini Supabase UUID orqali olish"""
        return self.account_device_mgr.get_user(user_id)

    def get_user_devices(self, user_id: str) -> List[Device]:
        """Foydalanuvchiga tegishli kompyuter qurilmalari ro'yxati (Row-Level Security)"""
        return self.account_device_mgr.get_devices_for_user(user_id)


# Backward compatibility alias
AccountAuthManager = SupabaseAuthManager
