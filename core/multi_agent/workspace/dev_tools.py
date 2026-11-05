# ========== core/multi_agent/workspace/dev_tools.py ==========
# Misa AI 9.0.0 — Native Project Understanding & Dev Engine
# Language detection, framework mapping, dependency parsing, API discovery, and test/build runners.

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.multi_agent.workspace.schema import ProjectMap, CommandExecutionRecord
from core.multi_agent.workspace.manager import WorkspaceManager, get_workspace_manager
from core.multi_agent.workspace.terminal_tools import TerminalEngine, get_terminal_engine

logger = logging.getLogger("misa.multi_agent.workspace.dev")

EXTENSION_LANG_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".rs": "Rust",
    ".go": "Go",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".sql": "SQL",
    ".md": "Markdown",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".bat": "Batch",
}


class ProjectUnderstandingEngine:
    """
    Analyzes project architectures, dependencies, frameworks, and coordinates builds and tests.
    """

    def __init__(
        self,
        manager: Optional[WorkspaceManager] = None,
        terminal: Optional[TerminalEngine] = None
    ):
        self.manager = manager or get_workspace_manager()
        self.terminal = terminal or get_terminal_engine()

    def analyze_project(self) -> ProjectMap:
        """Inspects workspace and compiles structured ProjectMap."""
        active_ws = self.manager.get_active_workspace()
        if not active_ws:
            raise RuntimeError("No active workspace configured.")

        root = active_ws.root_path
        lang_counts: Dict[str, int] = {}
        frameworks: List[str] = []
        entrypoints: List[str] = []
        important_modules: List[str] = []
        dependencies: Dict[str, str] = {}
        api_endpoints: List[str] = []
        test_framework = None
        build_system = None

        # 1. Walk files for languages and key markers
        for cur_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "target", "dist")]
            rel_dir = os.path.relpath(cur_root, root)

            for f in files:
                ext = os.path.splitext(f)[1].lower()
                lang = EXTENSION_LANG_MAP.get(ext)
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

                # Entrypoints detection
                if f in ("main.py", "app.py", "index.ts", "index.js", "main.tsx", "main.rs"):
                    entrypoints.append(os.path.normpath(os.path.join(rel_dir, f)))

                # Important module discovery
                if f == "__init__.py" and rel_dir != ".":
                    important_modules.append(os.path.normpath(rel_dir))

        # Determine primary language
        primary_lang = "unknown"
        if lang_counts:
            primary_lang = max(lang_counts.items(), key=lambda x: x[1])[0]

        # 2. Package.json analysis (Node/React/Tauri)
        pkg_json_path = os.path.join(root, "package.json")
        if not os.path.isfile(pkg_json_path) and os.path.isfile(os.path.join(root, "Misa", "package.json")):
            pkg_json_path = os.path.join(root, "Misa", "package.json")

        if os.path.isfile(pkg_json_path):
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    pkg_data = json.load(f)
                all_deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                for dep, ver in all_deps.items():
                    dependencies[dep] = str(ver)

                if "react" in all_deps:
                    frameworks.append("React")
                if "vite" in all_deps:
                    frameworks.append("Vite")
                    build_system = "Vite"
                if "@tauri-apps/api" in all_deps:
                    frameworks.append("Tauri v2")
                if "next" in all_deps:
                    frameworks.append("Next.js")
            except Exception:
                pass

        # 3. Python dependencies analysis
        req_txt_path = os.path.join(root, "requirements.txt")
        if os.path.isfile(req_txt_path):
            try:
                with open(req_txt_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        clean = line.strip()
                        if clean and not clean.startswith("#"):
                            parts = re.split(r"[=><~]", clean)
                            dependencies[parts[0].strip()] = parts[1].strip() if len(parts) > 1 else "latest"
                test_framework = "pytest"
            except Exception:
                pass

        # Check for Python frameworks in dependencies
        dep_keys = {k.lower() for k in dependencies.keys()}
        if "aiohttp" in dep_keys:
            frameworks.append("aiohttp")
        if "fastapi" in dep_keys:
            frameworks.append("FastAPI")
        if "flask" in dep_keys:
            frameworks.append("Flask")
        if "django" in dep_keys:
            frameworks.append("Django")

        # 4. Cargo.toml analysis (Rust)
        cargo_path = os.path.join(root, "Cargo.toml")
        if not os.path.isfile(cargo_path) and os.path.isfile(os.path.join(root, "Misa", "src-tauri", "Cargo.toml")):
            cargo_path = os.path.join(root, "Misa", "src-tauri", "Cargo.toml")

        if os.path.isfile(cargo_path):
            frameworks.append("Rust Cargo")
            if not build_system:
                build_system = "Cargo"

        # 5. API Endpoint discovery
        api_endpoints = self._discover_endpoints(root)

        return ProjectMap(
            root_path=root,
            primary_language=primary_lang,
            languages=lang_counts,
            frameworks=sorted(list(set(frameworks))),
            entrypoints=sorted(entrypoints),
            important_modules=sorted(list(set(important_modules)))[:30],
            api_endpoints=api_endpoints[:50],
            dependencies=dependencies,
            test_framework=test_framework or ("npm test" if "package.json" in str(pkg_json_path) else None),
            build_system=build_system or "Standard",
        )

    def _discover_endpoints(self, root: str) -> List[str]:
        """Scans source code for declared REST endpoints."""
        endpoints = []
        route_pattern = re.compile(r'app\.router\.add_(?:get|post|put|delete)\(["\']([^"\']+)["\']')
        fastapi_pattern = re.compile(r'@(?:app|router)\.(?:get|post|put|delete)\(["\']([^"\']+)["\']')

        for cur_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "target", "dist")]
            for f in files:
                if f.endswith(".py"):
                    full_p = os.path.join(cur_root, f)
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="replace") as fl:
                            text = fl.read()
                            for match in route_pattern.findall(text):
                                endpoints.append(match)
                            for match in fastapi_pattern.findall(text):
                                endpoints.append(match)
                    except Exception:
                        pass
        return sorted(list(set(endpoints)))

    def run_tests(self, custom_command: Optional[str] = None) -> CommandExecutionRecord:
        """Executes the project's test suite."""
        pmap = self.analyze_project()
        active_ws = self.manager.get_active_workspace()
        root = active_ws.root_path if active_ws else ""

        if custom_command:
            cmd = custom_command
        elif os.path.isfile(os.path.join(root, "pytest.ini")) or os.path.isfile(os.path.join(root, ".pytest_cache")):
            # Check for local venv python
            venv_py = os.path.join(root, ".venv", "Scripts", "python.exe")
            if os.path.isfile(venv_py):
                cmd = f'"{venv_py}" -m pytest -v'
            else:
                cmd = "pytest -v"
        elif "package.json" in pmap.dependencies or os.path.isfile(os.path.join(root, "package.json")):
            cmd = "npm test"
        else:
            cmd = "python -m unittest"

        logger.info(f"Running tests with command: {cmd}")
        return self.terminal.run_command(cmd, timeout_seconds=120.0, agent_id="test-architect")

    def run_build(self, custom_command: Optional[str] = None) -> CommandExecutionRecord:
        """Executes the project's build command."""
        active_ws = self.manager.get_active_workspace()
        root = active_ws.root_path if active_ws else ""

        if custom_command:
            cmd = custom_command
        elif os.path.isfile(os.path.join(root, "package.json")):
            cmd = "npm run build"
        elif os.path.isfile(os.path.join(root, "Misa", "package.json")):
            cmd = "npm --prefix Misa run build"
        elif os.path.isfile(os.path.join(root, "Cargo.toml")):
            cmd = "cargo build"
        else:
            cmd = "python setup.py build"

        logger.info(f"Running build with command: {cmd}")
        return self.terminal.run_command(cmd, timeout_seconds=180.0, agent_id="release-auditor")


# Singleton
_project_engine_instance: Optional[ProjectUnderstandingEngine] = None


def get_project_understanding_engine() -> ProjectUnderstandingEngine:
    global _project_engine_instance
    if _project_engine_instance is None:
        _project_engine_instance = ProjectUnderstandingEngine()
    return _project_engine_instance
