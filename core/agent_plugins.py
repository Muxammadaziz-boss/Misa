# ========== agent_plugins.py ==========
# Plugin tizimi — JSON yoki Python fayl orqali yangi tool'lar qo'shish
# Proaktiv Agent — foydalanuvchiga taklif berish

import os
import json
import logging
import datetime
import importlib.util
import re

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Loyiha ildizi
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")


# ========================================================
# PLUGIN MANAGER — JSON va Python plugin'larni yuklash
# ========================================================

AVAILABLE_TEMPLATES = [
    {
        "name": "github_search",
        "description": "GitHub orqali dasturiy kodlar va repozitoriyalarni qidirish",
        "category": "Dasturlash",
        "type": "url",
        "url": "https://github.com/search?q={query}&type=repositories",
        "parameters": {"query": {"type": "string", "description": "Qidiruv so'rovi"}},
        "version": "1.2.0",
        "author": "Misa AI Team",
    },
    {
        "name": "wikipedia_lookup",
        "description": "Vikipediyadan ilmiy atamalar va maqolalarni qidirish",
        "category": "AI Bilim",
        "type": "url",
        "url": "https://uz.wikipedia.org/wiki/{topic}",
        "parameters": {"topic": {"type": "string", "description": "Mavzu yoki atama"}},
        "version": "1.1.0",
        "author": "Misa AI Team",
    },
    {
        "name": "telegram_sender",
        "description": "Telegram orqali matnli xabarnoma yoki eslatma yuborish",
        "category": "Muloqot",
        "type": "url",
        "url": "https://t.me/share/url?url={text}",
        "parameters": {"text": {"type": "string", "description": "Xabar matni"}},
        "version": "1.0.0",
        "author": "Community",
    },
    {
        "name": "open_my_website",
        "description": "Foydalanuvchi sevimli veb-saytini brauzerda ochish",
        "category": "Qidiruv",
        "type": "url",
        "url": "https://google.com/search?q={query}",
        "parameters": {"query": {"type": "string", "description": "Qidiruv so'zi"}},
        "version": "1.0.0",
        "author": "Misa AI Team",
    },
    {
        "name": "run_my_script",
        "description": "Windows CLI yoki maxsus Python skriptlarini chaqirish",
        "category": "Tizim",
        "type": "command",
        "command": "python -c \"print('Misa script executed:', '{arg1}')\"",
        "parameters": {"arg1": {"type": "string", "description": "Parametr qiymati"}},
        "version": "1.0.0",
        "author": "Misa AI Team",
    },
]


class PluginManager:
    """JSON va Python plugin'larni yuklash va tool registry ga qo'shish."""
    
    def __init__(self, plugins_dir: str = None):
        self.plugins_dir = plugins_dir or PLUGINS_DIR
        self._loaded = []
        self._disabled_file = os.path.join(BASE_DIR, "data", "disabled_plugins.json")
        self._disabled_names = set()
        self._load_disabled_state()
    
    def _load_disabled_state(self):
        """O'chirilgan plaginlar holatini yuklash"""
        if os.path.exists(self._disabled_file):
            try:
                with open(self._disabled_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._disabled_names = set(data.get("disabled", []))
            except Exception:
                self._disabled_names = set()

    def _save_disabled_state(self):
        """O'chirilgan plaginlar holatini saqlash"""
        try:
            os.makedirs(os.path.dirname(self._disabled_file), exist_ok=True)
            with open(self._disabled_file, "w", encoding="utf-8") as f:
                json.dump({"disabled": list(self._disabled_names)}, f, indent=2)
        except Exception as e:
            logger.warning(f"Disabled plugins holati saqlashda xatolik: {e}")

    def load_all(self, registry) -> int:
        """Barcha plugin'larni yuklash va registry ga qo'shish."""
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
            self._create_example_plugin()
            logger.debug(f"Plugins papkasi yaratildi: {self.plugins_dir}")
            return 0
        
        count = 0
        for fname in os.listdir(self.plugins_dir):
            fpath = os.path.join(self.plugins_dir, fname)
            
            # Agar fayl nomi _ bilan boshlansa, bu o'chirilgan
            if fname.startswith("_"):
                continue

            if fname.endswith(".json"):
                if self._load_json_plugin(fpath, registry):
                    count += 1
            elif fname.endswith(".py"):
                if self._load_python_plugin(fpath, registry):
                    count += 1
        
        logger.info(f"PluginManager: {count} ta plugin yuklandi")
        return count
    
    def _load_json_plugin(self, path: str, registry) -> bool:
        """JSON plugin yuklash"""
        from core.agent_tools import Tool
        import webbrowser
        from urllib.parse import quote_plus
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            name = config.get("name", "")
            if not name:
                logger.warning(f"Plugin nomsiz: {path}")
                return False
            
            # Agar disabled bo'lsa ro'yxatdan o'tkazmaymiz
            if name in self._disabled_names:
                return False

            desc = config.get("description", "Custom tool")
            params = config.get("parameters", {})
            plugin_type = config.get("type", "url")
            category = config.get("category", "custom")
            
            if plugin_type == "url":
                url_template = config.get("url", "")
                
                def url_runner(url_tpl=url_template, **kwargs):
                    url = url_tpl
                    for key, value in kwargs.items():
                        url = url.replace(f"{{{key}}}", quote_plus(str(value)))
                    webbrowser.open(url)
                    return {"message": f"Ochildi: {url}", "url": url}
                
                tool = Tool(name=name, description=desc, parameters=params,
                           function=url_runner, category=category)
            
            elif plugin_type == "command":
                import subprocess
                import shlex
                cmd_template = config.get("command", "")
                
                def cmd_runner(cmd_tpl=cmd_template, **kwargs):
                    try:
                        args = shlex.split(cmd_tpl)
                        resolved_args = []
                        for token in args:
                            resolved_token = token
                            for key, value in kwargs.items():
                                resolved_token = resolved_token.replace(f"{{{key}}}", str(value))
                            resolved_args.append(resolved_token)
                        result = subprocess.run(resolved_args, shell=False, capture_output=True, text=True, timeout=10)
                        return {"message": (result.stdout or result.stderr)[:500], "returncode": result.returncode}
                    except Exception as err:
                        return {"error": str(err), "returncode": -1}
                
                tool = Tool(name=name, description=desc, parameters=params,
                           function=cmd_runner, category=category)
            else:
                logger.warning(f"Noma'lum plugin turi: {plugin_type}")
                return False
            
            registry.register(tool)
            self._loaded.append(name)
            logger.info(f"JSON plugin yuklandi: {name}")
            return True
            
        except Exception as e:
            logger.error(f"JSON plugin xatolik ({path}): {e}")
            return False
    
    def _load_python_plugin(self, path: str, registry) -> bool:
        """Python plugin yuklash"""
        from core.agent_tools import Tool
        
        try:
            fname = os.path.basename(path)
            real_path = os.path.realpath(path)
            real_plugins = os.path.realpath(self.plugins_dir)
            if not real_path.startswith(real_plugins):
                logger.error(f"Plugin plugins/ papkasidan tashqarida: {path}")
                return False
            
            spec = importlib.util.spec_from_file_location("plugin", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            name = getattr(module, "TOOL_NAME", "")
            if not name:
                logger.warning(f"Python plugin TOOL_NAME yo'q: {path}")
                return False

            if name in self._disabled_names:
                return False
            
            desc = getattr(module, "TOOL_DESCRIPTION", "Custom Python tool")
            params = getattr(module, "TOOL_PARAMS", {})
            category = getattr(module, "TOOL_CATEGORY", "custom")
            run_func = getattr(module, "run", None)
            
            if not run_func:
                logger.warning(f"Python plugin run() yo'q: {path}")
                return False
            
            tool = Tool(name=name, description=desc, parameters=params,
                       function=run_func, category=category)
            registry.register(tool)
            self._loaded.append(name)
            logger.info(f"Python plugin yuklandi: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Python plugin xatolik ({path}): {e}")
            return False
    
    def _create_example_plugin(self):
        """Namuna plugin yaratish"""
        example = {
            "name": "github_search",
            "description": "GitHub da kod qidirish",
            "category": "Dasturlash",
            "type": "url",
            "url": "https://github.com/search?q={query}&type=repositories",
            "parameters": {
                "query": {"type": "string", "description": "Qidiruv so'rovi"}
            },
            "version": "1.0.0"
        }
        path = os.path.join(self.plugins_dir, "example_github.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(example, f, ensure_ascii=False, indent=2)

    def get_all_plugins(self, registry=None) -> tuple:
        """5 ta holat (installed, available, disabled, error, updates) bo'yicha barcha plaginlar va statistikani qaytarish"""
        plugins = []
        custom_names = set()

        # 1. Custom plugins papkasini tekshirish
        if os.path.exists(self.plugins_dir):
            for fname in os.listdir(self.plugins_dir):
                fpath = os.path.join(self.plugins_dir, fname)
                if not os.path.isfile(fpath):
                    continue

                if not (fname.endswith(".json") or fname.endswith(".py")):
                    continue

                is_file_disabled = fname.startswith("_")
                clean_fname = fname.lstrip("_")
                base_name, ext = os.path.splitext(clean_fname)
                p_type = "json" if ext == ".json" else "python"

                if ext == ".json":
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        p_name = data.get("name", base_name)
                        p_desc = data.get("description", "Custom JSON plugin")
                        p_cat = data.get("category", "Foydalanuvchi")
                        p_params = data.get("parameters", {})
                        p_ver = data.get("version", "1.0.0")

                        # Updates tekshirish
                        has_update = False
                        for tpl in AVAILABLE_TEMPLATES:
                            if tpl["name"] == p_name and tpl.get("version", "1.0.0") > p_ver:
                                has_update = True
                                break

                        if is_file_disabled or p_name in self._disabled_names:
                            status = "disabled"
                        elif has_update:
                            status = "updates"
                        else:
                            status = "installed"

                        custom_names.add(p_name)
                        plugins.append({
                            "id": p_name,
                            "name": p_name,
                            "description": p_desc,
                            "category": p_cat,
                            "parameters": p_params,
                            "version": p_ver,
                            "type": p_type,
                            "status": status,
                            "enabled": status not in ["disabled", "error"],
                            "has_update": has_update,
                            "file_name": fname,
                        })
                    except Exception as e:
                        # Malformed JSON -> error status
                        custom_names.add(base_name)
                        plugins.append({
                            "id": base_name,
                            "name": base_name,
                            "description": f"Xatolik: {fname} faylini o'qib bo'lmadi",
                            "category": "Xatolik",
                            "parameters": {},
                            "version": "1.0.0",
                            "type": p_type,
                            "status": "error",
                            "error": str(e),
                            "enabled": False,
                            "file_name": fname,
                        })

                elif ext == ".py":
                    p_name = base_name
                    is_dis = is_file_disabled or p_name in self._disabled_names
                    custom_names.add(p_name)
                    plugins.append({
                        "id": p_name,
                        "name": p_name,
                        "description": "Custom Python plugin",
                        "category": "Dasturlash",
                        "parameters": {},
                        "version": "1.0.0",
                        "type": "python",
                        "status": "disabled" if is_dis else "installed",
                        "enabled": not is_dis,
                        "file_name": fname,
                    })

        # 2. Builtin tools ro'yxatini kiritish
        if registry:
            category_map = {
                "web_search": "Qidiruv", "calculator": "Hisoblash", "system_control": "Tizim",
                "music": "Multimedia", "weather": "Qidiruv", "reminder": "Rejalashtirish",
                "file_manager": "Fayllar", "knowledge": "Xotira", "datetime": "Tizim",
                "scheduler": "Rejalashtirish", "rag": "AI Bilim", "currency": "Hisoblash",
                "translator": "AI Bilim", "screenshot": "Multimedia", "file_write": "Fayllar",
                "app_check": "Tizim", "ask_user": "Muloqot", "screen_click": "Avtomatlashtirish",
                "keyboard_type": "Avtomatlashtirish", "keyboard_shortcut": "Avtomatlashtirish",
                "clipboard": "Tizim", "process_manager": "Tizim", "audio_control": "Tizim",
                "system_info": "Tizim", "window_manager": "Tizim", "notification": "Tizim",
                "vector_search": "AI Bilim", "sandbox": "Xavfsizlik", "secret_vault": "Xavfsizlik"
            }
            for t in registry.list_tools():
                t_name = t.get("name", "")
                if t_name not in custom_names:
                    is_dis = t_name in self._disabled_names
                    plugins.append({
                        "id": t_name,
                        "name": t_name,
                        "description": t.get("description", ""),
                        "category": category_map.get(t_name, "Tizim"),
                        "parameters": t.get("parameters", {}),
                        "version": t.get("version", "2.0.0"),
                        "capabilities": t.get("capabilities", []),
                        "required_parameters": t.get("required_parameters", []),
                        "risk_level": t.get("risk_level", "low"),
                        "timeout": t.get("timeout", 10.0),
                        "idempotent": t.get("idempotent", True),
                        "destructive": t.get("destructive", False),
                        "aliases": t.get("aliases", []),
                        "health": t.get("health", "available"),
                        "metrics": t.get("metrics", {}),
                        "type": "builtin",
                        "status": "disabled" if is_dis else "installed",
                        "enabled": not is_dis,
                    })

        # 3. Available (mavjud) shablonlar
        installed_and_dis = {p["name"] for p in plugins}
        for tpl in AVAILABLE_TEMPLATES:
            if tpl["name"] not in installed_and_dis:
                plugins.append({
                    "id": tpl["name"],
                    "name": tpl["name"],
                    "description": tpl["description"],
                    "category": tpl["category"],
                    "parameters": tpl.get("parameters", {}),
                    "version": tpl.get("version", "1.0.0"),
                    "type": tpl.get("type", "url"),
                    "status": "available",
                    "enabled": False,
                    "author": tpl.get("author", "Misa AI Team"),
                })

        # Statistika hisoblash
        stats = {
            "total": len(plugins),
            "installed": sum(1 for p in plugins if p["status"] == "installed"),
            "available": sum(1 for p in plugins if p["status"] == "available"),
            "disabled": sum(1 for p in plugins if p["status"] == "disabled"),
            "error": sum(1 for p in plugins if p["status"] == "error"),
            "updates": sum(1 for p in plugins if p["status"] == "updates"),
        }

        return plugins, stats

    def toggle(self, name: str, enabled: bool, registry=None) -> bool:
        """Plaginni yoqish / o'chirish"""
        if enabled:
            self._disabled_names.discard(name)
        else:
            self._disabled_names.add(name)
        self._save_disabled_state()

        # Custom fayl bo'lsa nomini almashtirish
        if os.path.exists(self.plugins_dir):
            for fname in os.listdir(self.plugins_dir):
                clean_name = fname.lstrip("_")
                base_name, _ = os.path.splitext(clean_name)
                if base_name == name or clean_name == name:
                    old_path = os.path.join(self.plugins_dir, fname)
                    if enabled and fname.startswith("_"):
                        new_path = os.path.join(self.plugins_dir, fname[1:])
                        try:
                            os.rename(old_path, new_path)
                        except Exception:
                            pass
                    elif not enabled and not fname.startswith("_"):
                        new_path = os.path.join(self.plugins_dir, f"_{fname}")
                        try:
                            os.rename(old_path, new_path)
                        except Exception:
                            pass
                    break

        # Registry dan o'chirish yoki qayta yuklash
        if registry:
            if not enabled:
                registry.unregister(name)
            else:
                # Qayta yuklashga urinish
                self.load_all(registry)

        return True

    def install(self, name: str, custom_data: dict = None, registry=None) -> bool:
        """Plagin o'rnatish"""
        # Xavfsizlik: faqat xavfsiz identifikator nomlari qabul qilinadi
        if not name or not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            logger.warning(f"Xavfsizlik: Noto'g'ri yoki xavfli plagin nomi rad etildi: '{name}'")
            return False

        os.makedirs(self.plugins_dir, exist_ok=True)
        real_plugins = os.path.realpath(self.plugins_dir)
        target_path = os.path.realpath(os.path.join(self.plugins_dir, f"{name}.json"))
        if not target_path.startswith(real_plugins):
            logger.error(f"Xavfsizlik: Path traversal urinishi rad etildi: '{name}'")
            return False

        if custom_data:
            data = custom_data
        else:
            # Shablonlardan qidirish
            data = None
            for tpl in AVAILABLE_TEMPLATES:
                if tpl["name"] == name:
                    data = dict(tpl)
                    break
            if not data:
                return False

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._disabled_names.discard(name)
        self._save_disabled_state()

        if registry:
            self._load_json_plugin(target_path, registry)
        return True

    def uninstall(self, name: str, registry=None) -> bool:
        """Plaginni butunlay o'chirish"""
        if not name or not re.match(r"^[a-zA-Z0-9_\-]+$", name):
            logger.warning(f"Xavfsizlik: Noto'g'ri yoki xavfli plagin nomi rad etildi: '{name}'")
            return False

        deleted = False
        if os.path.exists(self.plugins_dir):
            for fname in os.listdir(self.plugins_dir):
                f_clean = fname.lstrip("_")
                base_name, _ = os.path.splitext(f_clean)
                if base_name == name or f_clean == name:
                    fpath = os.path.join(self.plugins_dir, fname)
                    try:
                        os.remove(fpath)
                        deleted = True
                    except Exception:
                        pass

        self._disabled_names.discard(name)
        self._save_disabled_state()

        if registry:
            registry.unregister(name)

        return deleted

    def update(self, name: str, registry=None) -> bool:
        """Plaginni yangilash"""
        for tpl in AVAILABLE_TEMPLATES:
            if tpl["name"] == name:
                return self.install(name, tpl, registry)
        return False

    @property
    def loaded_plugins(self) -> list:
        return self._loaded.copy()


# ========================================================
# PROACTIVE AGENT — O'zi taklif berish
# ========================================================

class ProactiveAgent:
    """Foydalanuvchiga proaktiv takliflar berish.
    
    - Har kuni birinchi "salom" da ob-havo va eslatmalar xabar qilish
    - Foydalanuvchi odatlariga qarab taklif berish
    - Uzoq vaqt jimlik bo'lsa taklif berish
    """
    
    def __init__(self, memory=None):
        self.memory = memory
        self._last_greeting = None
        self._suggestions_today = 0
        self._max_suggestions_per_day = 3
    
    def get_greeting_suggestions(self) -> list:
        """Salom aytganda takliflar.
        
        Returns:
            List of suggestion strings
        """
        now = datetime.datetime.now()
        suggestions = []
        
        # Bugun birinchi marta bo'lsa
        if self._last_greeting is None or self._last_greeting.date() != now.date():
            self._last_greeting = now
            self._suggestions_today = 0  # Yangi kun — counter reset
            
            # Vaqtga qarab salomlash
            hour = now.hour
            if hour < 6:
                suggestions.append("Erta turibsiz! Yaxshi uyqu oling.")
            elif hour < 12:
                suggestions.append("Xayrli tong! Bugun qanday rejalar bor?")
            elif hour < 18:
                suggestions.append("Xayrli kun! Biror narsa yordam beraymi?")
            else:
                suggestions.append("Xayrli kech! Bugun qanday o'tdi?")
            
            # Eslatmalar bormi?
            try:
                from core.agent_scheduler import get_scheduler
                scheduler = get_scheduler()
                active = scheduler.active_count
                if active > 0:
                    suggestions.append(f"📋 {active} ta rejalashtirilgan vazifangiz bor.")
            except Exception:
                pass
            
            # Foydalanuvchi bilimi bormi?
            if self.memory:
                knowledge = self.memory.get_knowledge()
                if knowledge:
                    # Eng oxirgi saqlangan bilim
                    recent = sorted(knowledge.items(), 
                                   key=lambda x: x[1].get("saved_at", ""), reverse=True)
                    if recent:
                        key, data = recent[0]
                        suggestions.append(f"💡 Eslatma: {key} = {data['value']}")
        
        return suggestions
    
    def get_idle_suggestion(self, idle_seconds: int = 300) -> str:
        """Uzoq vaqt jimlik bo'lganda taklif.
        
        Args:
            idle_seconds: Necha soniya jim turgan
        Returns:
            Taklif matni yoki bo'sh string
        """
        if self._suggestions_today >= self._max_suggestions_per_day:
            return ""
        
        now = datetime.datetime.now()
        hour = now.hour
        
        suggestions = [
            "Biror narsa qidirib beraymi?",
            "Musiqaga nima deraysiz? 🎵",
            "Hisob-kitob kerakmi? 🧮",
        ]
        
        if 12 <= hour <= 13:
            return "Tushlik vaqti! Dam oling. 🍽️"
        
        if idle_seconds > 600:
            self._suggestions_today += 1
            import random
            return random.choice(suggestions)
        
        return ""
    
    def get_context_suggestion(self, last_command: str) -> str:
        """Oxirgi buyruqqa asoslangan taklif.
        
        Args:
            last_command: Oxirgi bajarilgan buyruq
        Returns:
            Taklif matni
        """
        # Markov chain ga o'xshash — buyruqdan keyin nima taklif qilish
        suggestions_map = {
            "open_youtube": "YouTube'dan musiqa qidirib beraymi? 🎵",
            "weather": "Ob-havo ma'lumotini eslatib qo'yaymi? ⏰",
            "calculator": "Yana hisob-kitob kerakmi? 🧮",
            "open_telegram": "Telegramda kimga yozmoqchisiz?",
            "music_search": "Boshqa qo'shiq qidiraylikmi? 🎶",
        }
        
        return suggestions_map.get(last_command, "")


# Global singleton
_plugin_manager = None
_proactive_agent = None

def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager

def get_proactive_agent(memory=None) -> ProactiveAgent:
    global _proactive_agent
    if _proactive_agent is None:
        _proactive_agent = ProactiveAgent(memory)
    return _proactive_agent
