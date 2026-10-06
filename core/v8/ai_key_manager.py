# ========== core/v8/ai_key_manager.py ==========
# Misa AI v9.0.0 — Database AI Key Management & Auto-Activation
# Handles dynamic AI key storage in Supabase / Cloud, multi-key rotation,
# user-account auto-sync, and fallback priority.

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_FILE = REPO_ROOT / "data" / "ai_keys_cache.json"

DEFAULT_GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-pro-latest",
]


class AIKeyManager:
    """Markazlashgan dinamik AI kalitlari boshqaruvchisi.
    Kalitlarni Supabase bazasida, bulut backendda va mahalliy keshda saqlaydi hamda
    foydalanuvchi akkaunti bilan kirganda avtomatik faollashtiradi.
    """

    _instance: Optional["AIKeyManager"] = None

    def __init__(self):
        self._system_keys: Dict[str, List[str]] = {
            "gemini": [],
            "openrouter": [],
            "groq": [],
            "cerebras": [],
            "nvidia": [],
        }
        self._user_keys: Dict[str, Dict[str, str]] = {}  # user_id -> {provider: key}
        self._active_models: Dict[str, str] = {
            "gemini": "gemini-2.0-flash",
            "groq": "llama-3.3-70b-versatile",
            "cerebras": "llama-3.3-70b",
            "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
            "nvidia": "meta/llama-3.3-70b-instruct",
        }
        self._key_cooldowns: Dict[str, float] = {}  # key -> cooldown_until_timestamp
        self._last_sync_time: float = 0
        self._load_cache()

    @classmethod
    def get_instance(cls) -> "AIKeyManager":
        if cls._instance is None:
            cls._instance = AIKeyManager()
        return cls._instance

    def _load_cache(self):
        """Mahalliy keshdan saqlangan kalitlarni yuklash"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for prov in ("gemini", "openrouter", "groq", "cerebras", "nvidia"):
                        keys = data.get(prov, [])
                        if isinstance(keys, list):
                            self._system_keys[prov] = [str(k).strip() for k in keys if k and str(k).strip()]
                        elif isinstance(keys, str) and keys.strip():
                            self._system_keys[prov] = [keys.strip()]
                    if data.get("active_models"):
                        self._active_models.update(data["active_models"])
        except Exception as e:
            logger.warning(f"AI kalitlari keshini yuklashda xatolik: {e}")

    def _save_cache(self):
        """Kalitlarni xavfsiz mahalliy keshga saqlash"""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "gemini": self._system_keys.get("gemini", []),
                "openrouter": self._system_keys.get("openrouter", []),
                "groq": self._system_keys.get("groq", []),
                "cerebras": self._system_keys.get("cerebras", []),
                "nvidia": self._system_keys.get("nvidia", []),
                "active_models": self._active_models,
                "updated_at": time.time(),
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"AI kalitlari keshini saqlashda xatolik: {e}")

    def register_system_key(self, provider: str, key: str, prepend: bool = True):
        """Tizim kalitini xotiraga va keshga qo'shish"""
        k = (key or "").strip()
        if not k or len(k) < 8:
            return
        prov = provider.lower()
        if prov not in self._system_keys:
            self._system_keys[prov] = []
        if k in self._system_keys[prov]:
            self._system_keys[prov].remove(k)
        if prepend:
            self._system_keys[prov].insert(0, k)
        else:
            self._system_keys[prov].append(k)
        self._save_cache()

    def set_user_key(self, user_id: str, provider: str, key: str):
        """Foydalanuvchining shaxsiy API kalitini saqlash"""
        if not user_id:
            return
        prov = provider.lower()
        if user_id not in self._user_keys:
            self._user_keys[user_id] = {}
        if key and key.strip():
            self._user_keys[user_id][prov] = key.strip()
        else:
            self._user_keys[user_id].pop(prov, None)

    def mark_key_failed(self, key: str, cooldown_seconds: float = 120.0):
        """Kvotasi to'lgan yoki xato bergan kalitni vaqtincha cooldown ga qo'yish"""
        if not key:
            return
        self._key_cooldowns[key] = time.time() + cooldown_seconds
        logger.warning(f"AI kaliti vaqtinchalik sovutishga olindi: {key[:8]}... ({cooldown_seconds}s)")

    def get_active_key(self, provider: str, user_id: Optional[str] = None) -> str:
        """Istalgan provayder uchun deterministik ustuvorlikda faol API kalitini olish:
        1. User shaxsiy kaliti
        2. Tizim kalitlari (cooldown dagi kalitlarni o'tkazib yuborish)
        3. Environment (MISA_<PROV>_API_KEY, <PROV>_API_KEY)
        4. Maxsus taxalluslar (masalan GEMINI -> GOOGLE_API_KEY)
        5. data/config.json
        """
        p = provider.lower()
        now = time.time()

        # 1. User shaxsiy kaliti
        if user_id and user_id in self._user_keys:
            ukey = self._user_keys[user_id].get(p)
            if ukey and now >= self._key_cooldowns.get(ukey, 0):
                return ukey

        # 2. Tizim kalitlari
        for k in self._system_keys.get(p, []):
            if k and now >= self._key_cooldowns.get(k, 0):
                return k

        # 3. Environment o'zgaruvchilari
        misa_env = os.getenv(f"MISA_{p.upper()}_API_KEY", "").strip()
        if misa_env and now >= self._key_cooldowns.get(misa_env, 0):
            return misa_env

        std_env = os.getenv(f"{p.upper()}_API_KEY", "").strip()
        if std_env and now >= self._key_cooldowns.get(std_env, 0):
            return std_env

        # 4. Maxsus taxalluslar
        if p == "gemini":
            g_env = os.getenv("GOOGLE_API_KEY", "").strip()
            if g_env and now >= self._key_cooldowns.get(g_env, 0):
                return g_env

        # 5. data/config.json
        try:
            cfg_path = REPO_ROOT / "data" / "config.json"
            if cfg_path.exists():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    ck = (
                        cfg.get(f"{p}_api_key")
                        or cfg.get("ai", {}).get(f"{p}_api_key")
                        or cfg.get("providers", {}).get(p, {}).get("api_key")
                    )
                    if p == "gemini" and not ck:
                        ck = cfg.get("google_api_key") or cfg.get("ai", {}).get("gemini_api_key")
                    if ck and str(ck).strip() and now >= self._key_cooldowns.get(str(ck).strip(), 0):
                        return str(ck).strip()
        except Exception:
            pass

        # Cooldown da bo'lsa ham oxirgi chora sifatida ro'yxatdagisini qaytarish
        if self._system_keys.get(p):
            return self._system_keys[p][0]

        return misa_env or std_env or ""

    def get_active_gemini_key(self, user_id: Optional[str] = None) -> str:
        """Deterministik ustuvorlik tartibida faol Gemini API kalitini olish"""
        return self.get_active_key("gemini", user_id=user_id)

    def get_active_openrouter_key(self, user_id: Optional[str] = None) -> str:
        """OpenRouter API kalitini olish"""
        return self.get_active_key("openrouter", user_id=user_id)

    def get_active_groq_key(self, user_id: Optional[str] = None) -> str:
        """Groq API kalitini olish"""
        return self.get_active_key("groq", user_id=user_id)

    def get_active_cerebras_key(self, user_id: Optional[str] = None) -> str:
        """Cerebras API kalitini olish"""
        return self.get_active_key("cerebras", user_id=user_id)

    def get_active_nvidia_key(self, user_id: Optional[str] = None) -> str:
        """NVIDIA NIM API kalitini olish"""
        return self.get_active_key("nvidia", user_id=user_id)

    def sync_from_user_session(self, user_id: str, metadata: Dict[str, Any]):
        """Foydalanuvchi akkaunti bilan tizimga kirganda ma'lumotlarni avtomatik sinxronlash"""
        if not metadata:
            return
        # Foydalanuvchi metadata ichida kalit bormi?
        for prov in ("gemini", "groq", "cerebras", "openrouter", "nvidia"):
            k = (
                metadata.get(f"{prov}_api_key")
                or metadata.get(f"custom_{prov}_key")
            )
            if prov == "gemini" and not k:
                k = metadata.get("google_api_key") or metadata.get("ai_key")
            if k and str(k).strip():
                self.set_user_key(user_id, prov, str(k).strip())
                logger.info(f"Foydalanuvchi {user_id} uchun shaxsiy {prov} kaliti yuklandi.")

        custom_model = metadata.get("preferred_model") or metadata.get("ai_model")
        if custom_model:
            self._active_models["gemini"] = str(custom_model).strip()

    def sync_from_cloud(self, cloud_url: Optional[str] = None, auth_token: Optional[str] = None) -> bool:
        """Railway bulut serveri yoki Supabase dan eng so'nggi faol AI kalitlarini yuklab olish"""
        import requests
        base_cloud = (cloud_url or os.getenv("MISA_CLOUD_URL") or "https://misa.up.railway.app").rstrip("/")
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # 1. Bulut backenddan so'rash
        try:
            res = requests.get(f"{base_cloud}/api/ai/config", headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()
                if data.get("ok"):
                    active_keys = data.get("active_keys", {})
                    for prov, key in active_keys.items():
                        if key and not key.endswith("..."):
                            self.register_system_key(prov, key)
                    self._last_sync_time = time.time()
                    logger.info("Bulut backenddan AI kalitlari muvaffaqiyatli sinxronlandi.")
                    return True
        except Exception as e:
            logger.debug(f"Bulut backenddan AI kalitlarini olishda xatolik: {e}")

        # 2. Supabase PostgREST orqali so'rash
        supa_url = (os.getenv("SUPABASE_URL") or "https://vdcssmzguxfknqkfxbed.supabase.co").rstrip("/")
        anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
        if supa_url and anon_key:
            try:
                supa_headers = {
                    "apikey": anon_key,
                    "Authorization": f"Bearer {auth_token or anon_key}"
                }
                resp = requests.get(f"{supa_url}/rest/v1/system_ai_keys?is_active=eq.true&select=*&order=priority.asc", headers=supa_headers, timeout=4)
                if resp.status_code == 200:
                    records = resp.json()
                    for r in records:
                        prov = r.get("provider", "gemini").lower()
                        k = r.get("api_key", "").strip()
                        if k:
                            self.register_system_key(prov, k)
                    self._last_sync_time = time.time()
                    return True
            except Exception as e:
                logger.debug(f"Supabase PostgREST orqali AI kalitlarini olishda xatolik: {e}")

        return False

    def set_preferred_model(self, model: str, provider: str = "gemini"):
        """Afzal ko'rilgan AI modelini sozlash"""
        if model and str(model).strip():
            self._active_models[provider.lower()] = str(model).strip()
            self._save_cache()

    def get_preferred_model(self, provider: str = "gemini") -> str:
        """Joriy afzal ko'rilgan AI modelini olish"""
        return self._active_models.get(provider.lower(), "gemini-2.0-flash")

    def get_status_summary(self) -> Dict[str, Any]:
        """Tizim va UI uchun kalitlar holatini xavfsiz qaytarish (kalitlar maskalangan)"""
        active_gemini = self.get_active_gemini_key()
        has_gemini = bool(active_gemini)
        masked_gemini = (active_gemini[:8] + "..." + active_gemini[-4:]) if has_gemini and len(active_gemini) > 12 else ""

        providers_status = {}
        for prov in ("gemini", "groq", "cerebras", "openrouter", "nvidia"):
            k = self.get_active_key(prov)
            has_k = bool(k)
            masked_k = (k[:4] + "..." + k[-4:]) if has_k and len(k) > 8 else ""
            providers_status[prov] = {
                "configured": has_k,
                "masked_key": masked_k,
                "preferred_model": self.get_preferred_model(prov),
                "system_keys_count": len(self._system_keys.get(prov, [])),
            }

        any_configured = any(p["configured"] for p in providers_status.values())

        return {
            "gemini_configured": has_gemini,
            "groq_configured": bool(self.get_active_groq_key()),
            "cerebras_configured": bool(self.get_active_cerebras_key()),
            "openrouter_configured": bool(self.get_active_openrouter_key()),
            "nvidia_configured": bool(self.get_active_nvidia_key()),
            "masked_key": masked_gemini,
            "system_keys_count": len(self._system_keys.get("gemini", [])),
            "preferred_model": self.get_preferred_model("gemini"),
            "supported_models": DEFAULT_GEMINI_MODELS,
            "last_sync": self._last_sync_time,
            "status": "ready" if any_configured else "missing_key",
            "providers": providers_status,
        }


def get_ai_key_manager() -> AIKeyManager:
    return AIKeyManager.get_instance()
