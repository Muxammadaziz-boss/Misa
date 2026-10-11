# ========== config.py ==========
# Loyiha konfiguratsiyasi va sozlamalari

import os
import json
import logging
import tempfile
from pathlib import Path


class Config:
    """Loyiha konfiguratsiyasi klassi"""

    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.config_file = self.project_dir / "data" / "config.json"
        self.logs_dir = self.project_dir / "logs"

        # Loglarni yaratish
        self.logs_dir.mkdir(exist_ok=True)

        # Standart konfiguratsiya
        self.default_config = {
            "app": {"version": "9.0.1", "name": "Misa AI", "debug": False},
            "audio": {
                "sample_rate": 16000,
                "duration": 5,
                "channels": 1,
                "tts_voice_male": "uz-UZ-SardorNeural",
                "tts_voice_female": "uz-UZ-MadinaNeural",
                "tts_rate": 200,
                "vad_enabled": True,
                "vad_threshold": 0.015,
                "silence_duration": 1.2,
            },
            "gui": {
                "theme": "dark",
                "color_scheme": "blue",
                "compact_mode": False,
                "window_size": "1100x800",
                "compact_window_size": "960x700",
                "font_family": "Segoe UI",
                "font_size": 12,
            },
            "paths": {
                "commands_file": "commands.json",
                "history_file": "buyruqlar_tarixi.txt",
                "reminders_file": "eslatmalar.txt",
                "temp_dir": tempfile.gettempdir(),
            },
            "api": {
                "openrouter_model": "openai/gpt-3.5-turbo",
                "speech_language": "uz-UZ",
                "timeout": 15,
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_name": "misa.log",
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5,
            },
        }

        # Konfiguratsiyani yuklash
        self.config = self.load_config()

        # Logging sozlash
        self.setup_logging()

    def load_config(self):
        """Konfiguratsiyani fayldan yuklash"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)

                # Standart va yuklangan konfiguratsiyani birlashtirish
                config = self.default_config.copy()
                self._deep_update(config, loaded_config)

                # Dinamik temp_dir: har doim amaldagi tizim temp katalogini ta'minlash
                if "paths" in config:
                    saved_temp = config["paths"].get("temp_dir", "")
                    if not saved_temp or not os.path.exists(saved_temp):
                        config["paths"]["temp_dir"] = tempfile.gettempdir()

                return config
            except Exception as e:
                print(f"Konfiguratsiyani yuklashda xatolik: {e}")
                return self.default_config.copy()
        else:
            # Standart konfiguratsiyani saqlash
            self.save_config(self.default_config)
            return self.default_config.copy()

    def save_config(self, config=None):
        """Konfiguratsiyani faylga saqlash"""
        if config is None:
            config = self.config

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Konfiguratsiyani saqlashda xatolik: {e}")
            return False

    def _deep_update(self, base_dict, update_dict):
        """Ichma-ich lug'atlarni yangilash"""
        for key, value in update_dict.items():
            if (
                key in base_dict
                and isinstance(base_dict[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def get(self, key_path, default=None):
        """Konfiguratsiya qiymatini olish (masalan: 'app.version')"""
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path, value):
        """Konfiguratsiya qiymatini o'rnatish"""
        keys = key_path.split(".")
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        self.save_config()

    def setup_logging(self):
        """Logging tizimini sozlash"""
        root_logger = logging.getLogger()
        log_config = self.get("logging")
        root_logger.setLevel(getattr(logging, log_config.get("level", "INFO")))

        if not root_logger.handlers:
            try:
                from core.logger import SensitiveDataFilter
                sens_filter = SensitiveDataFilter()
            except ImportError:
                sens_filter = None

            log_file = self.logs_dir / log_config.get("file_name", "misa.log")
            formatter = logging.Formatter(log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=log_config.get("max_file_size", 10 * 1024 * 1024),
                backupCount=log_config.get("backup_count", 5),
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            if sens_filter:
                file_handler.addFilter(sens_filter)

            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            if sens_filter:
                console_handler.addFilter(sens_filter)

            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

        # Kutubxona loglarini o'chirish
        logging.getLogger("absl").setLevel(logging.ERROR)
        logging.getLogger("google.auth").setLevel(logging.ERROR)
        logging.getLogger("google.auth.transport.requests").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("matplotlib").setLevel(logging.WARNING)

    # get_user_file_path() va get_voice_file_path() olib tashlandi
    # (user.name va user.voice_type endi config.json da saqlanadi)

    def get_commands_file_path(self):
        """Buyruqlar fayli yo'li"""
        return self.project_dir / self.get("paths.commands_file")

    def get_history_file_path(self):
        """Tarix fayli yo'li"""
        return self.project_dir / self.get("paths.history_file")

    def get_reminders_file_path(self):
        """Eslatmalar fayli yo'li"""
        return self.project_dir / self.get("paths.reminders_file")


# Global konfiguratsiya obyekti
config = Config()


# Qulaylik funksiyalari
def get_config(key_path, default=None):
    """Konfiguratsiya qiymatini olish"""
    return config.get(key_path, default)


def set_config(key_path, value):
    """Konfiguratsiya qiymatini o'rnatish"""
    config.set(key_path, value)


def get_logger(name=None):
    """Logger olish"""
    return logging.getLogger(name or __name__)
