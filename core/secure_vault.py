# ========== secure_vault.py ==========
# Xavfsiz Seh (Secure Vault)
# API tokenlar, parollar va maxfiy ma'lumotlarni shifrlash orqali saqlash

import os
import json
import logging
import base64
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography moduli topilmadi. pip install cryptography")

from core.common_paths import get_data_path, get_base_dir
BASE_DIR = get_base_dir()
VAULT_FILE = get_data_path("secure_vault.json")
KEY_FILE = get_data_path(".vault.key")


class SecureVault:
    """
    Maxfiy ma'lumotlarni xavfsiz saqlash.
    Fernet shifrlash + master parol.
    """

    def __init__(self, master_password: str = None):
        self._cipher = None
        self._unlocked = False
        self._vault_data: Dict[str, Any] = {}

        if master_password:
            self.unlock(master_password)

    def _generate_key(self, password: str, salt: bytes = None) -> tuple:
        """Paroldan shifrlash kaliti yaratish"""
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography moduli o'rnatilmagan")

        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    def _load_or_create_key(self) -> bytes:
        """Kalit faylini yuklash yoki yaratish"""
        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, "r") as f:
                    data = json.load(f)
                    salt = base64.b64decode(data["salt"])
                    return salt
            except Exception as e:
                logger.warning(f"Key fayl o'qish xatolik: {e}")

        salt = os.urandom(16)
        with open(KEY_FILE, "w") as f:
            json.dump({"salt": base64.b64encode(salt).decode()}, f, indent=2)

        return salt

    def unlock(self, master_password: str) -> bool:
        """Vault ni parol bilan ochish"""
        if not CRYPTO_AVAILABLE:
            return False

        try:
            salt = self._load_or_create_key()
            key, _ = self._generate_key(master_password, salt)
            self._cipher = Fernet(key)
            self._unlocked = True

            self._load_vault()
            return True

        except Exception as e:
            logger.error(f"Vault unlock xatolik: {e}")
            return False

    def lock(self):
        """Vault ni yopish"""
        self._cipher = None
        self._unlocked = False

    def is_unlocked(self) -> bool:
        """Vault ochilganmi?"""
        return self._unlocked

    def _load_vault(self):
        """Vault ma'lumotlarini yuklash"""
        if not os.path.exists(VAULT_FILE):
            self._vault_data = {"secrets": {}, "metadata": {}}
            return

        try:
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                encrypted = f.read()

            if encrypted.strip():
                decrypted = self._cipher.decrypt(encrypted.encode()).decode()
                self._vault_data = json.loads(decrypted)
            else:
                self._vault_data = {"secrets": {}, "metadata": {}}

        except Exception as e:
            logger.warning(f"Vault yuklash xatolik: {e}")
            self._vault_data = {"secrets": {}, "metadata": {}}

    def _save_vault(self):
        """Vault ma'lumotlarini saqlash"""
        if not self._unlocked:
            return

        os.makedirs(os.path.dirname(VAULT_FILE), exist_ok=True)

        try:
            encrypted = self._cipher.encrypt(
                json.dumps(self._vault_data, ensure_ascii=False).encode()
            )
            with open(VAULT_FILE, "w", encoding="utf-8") as f:
                f.write(encrypted.decode())

        except Exception as e:
            logger.error(f"Vault saqlash xatolik: {e}")

    def set_secret(self, key: str, value: str, category: str = "general") -> bool:
        """
        Maxfiy ma'lumot saqlash.

        Args:
            key: Kalit nomi (masalan: "github_token")
            value: Qiymat (masalan: "ghp_xxxxx")
            category: Kategoriya (api_key, password, token, general)

        Returns:
            bool: Muvaffaqiyatmi
        """
        if not self._unlocked:
            logger.warning("Vault yopiq — maxfiy ma'lumot saqlab bo'lmaydi")
            return False

        if "secrets" not in self._vault_data:
            self._vault_data["secrets"] = {}

        self._vault_data["secrets"][key] = {
            "value": value,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        self._save_vault()
        return True

    def get_secret(self, key: str) -> Optional[str]:
        """Maxfiy ma'lumotni olish"""
        if not self._unlocked:
            return None

        secrets = self._vault_data.get("secrets", {})
        if key in secrets:
            return secrets[key]["value"]

        return None

    def delete_secret(self, key: str) -> bool:
        """Maxfiy ma'lumotni o'chirish"""
        if not self._unlocked:
            return False

        if "secrets" in self._vault_data and key in self._vault_data["secrets"]:
            del self._vault_data["secrets"][key]
            self._save_vault()
            return True

        return False

    def list_secrets(self) -> Dict[str, Dict]:
        """Barcha maxfiy ma'lumotlarni ro'yxatini olish (qiymatsiz)"""
        if not self._unlocked:
            return {}

        secrets = self._vault_data.get("secrets", {})
        return {
            key: {
                "category": info["category"],
                "created_at": info["created_at"],
                "updated_at": info["updated_at"],
            }
            for key, info in secrets.items()
        }

    def has_secret(self, key: str) -> bool:
        """Kalit mavjudmi?"""
        if not self._unlocked:
            return False
        return key in self._vault_data.get("secrets", {})

    def get_by_category(self, category: str) -> Dict[str, str]:
        """Kategoriya bo'yicha maxfiy ma'lumotlarni olish"""
        if not self._unlocked:
            return {}

        secrets = self._vault_data.get("secrets", {})
        return {
            key: info["value"]
            for key, info in secrets.items()
            if info.get("category") == category
        }

    def setup_password(self, new_password: str) -> bool:
        """Yangi master parol o'rnatish"""
        if not CRYPTO_AVAILABLE:
            return False

        try:
            salt = os.urandom(16)
            key_data = {"salt": base64.b64encode(salt).decode()}

            with open(KEY_FILE, "w") as f:
                json.dump(key_data, f)

            return self.unlock(new_password)

        except Exception as e:
            logger.error(f"Password setup xatolik: {e}")
            return False


_vault_instance: Optional[SecureVault] = None


def get_vault() -> SecureVault:
    """Global vault instance"""
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = SecureVault()
    return _vault_instance


def unlock_vault(password: str) -> bool:
    """Vault ni ochish"""
    vault = get_vault()
    return vault.unlock(password)


def lock_vault():
    """Vault ni yopish"""
    get_vault().lock()


def get_secret(key: str) -> Optional[str]:
    """Maxfiy ma'lumot olish"""
    return get_vault().get_secret(key)


def set_secret(key: str, value: str, category: str = "general") -> bool:
    """Maxfiy ma'lumot saqlash"""
    return get_vault().set_secret(key, value, category)


def is_vault_unlocked() -> bool:
    """Vault ochilganmi?"""
    return get_vault().is_unlocked()
