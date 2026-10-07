# ========== packaging/build_backend.py ==========
# Misa AI v9.0.0 — Standalone Backend Production Bundler
# Uses PyInstaller to bundle core/api_server.py into a self-contained
# production runtime (backend/misa_backend.exe + libraries).
# Excludes heavy ML/notebook dependencies (torch, matplotlib, jupyter)
# to achieve ~30MB footprint and sub-second startup.

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_backend")

def build():
    root_dir = Path(__file__).resolve().parent.parent
    os.chdir(root_dir)

    python_exe = sys.executable
    logger.info(f"Using Python executable: {python_exe}")
    logger.info(f"Project root: {root_dir}")

    build_dir = root_dir / "build" / "pyinstaller_backend"
    dist_dir = root_dir / "dist" / "backend_build"
    backend_target_name = "misa_backend"

    # Clean previous build artifacts
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
    if dist_dir.exists():
        shutil.rmtree(dist_dir, ignore_errors=True)

    cmd = [
        python_exe, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noconsole",
        "--onedir",
        f"--name={backend_target_name}",
        f"--workpath={build_dir}",
        f"--distpath={dist_dir}",
        "--add-data=core;core",
        "--add-data=data;data",
        "--add-data=main.py;.",
        "--hidden-import=main",
        "--hidden-import=edge_tts",
        "--hidden-import=sounddevice",
        "--hidden-import=soundfile",
        "--hidden-import=pygame",
        "--hidden-import=pycaw",
        "--hidden-import=ctypes",
        "--hidden-import=aiohttp",
        "--hidden-import=dotenv",
        "--hidden-import=cryptography",
        "--hidden-import=cryptography.hazmat.primitives.asymmetric.ed25519",
        "--hidden-import=psutil",
        "--hidden-import=requests",
        "--hidden-import=tzdata",
        "--hidden-import=core.v8.update_service",
        "--hidden-import=core.v8.account_auth",
        "--hidden-import=core.v8.device_auth",
        "--hidden-import=core.v8.device_enrollment",
        "--hidden-import=core.v8.account_device",
        "--hidden-import=core.v8.permission_center",
        "--hidden-import=core.v8.remote_orchestrator",
        "--hidden-import=core.v8.remote_tools",
        "--hidden-import=core.v8.command_queue",
        "--hidden-import=core.v8.auth_session",
        "--hidden-import=core.v8.events",
        "--hidden-import=core.v8.telegram_webhook",
        "--hidden-import=core.v8.telegram_identity",
        "--hidden-import=core.v8.universal_bot",
        "--hidden-import=core.v8.telegram_gateway",
        "--hidden-import=core.common_paths",
        "--hidden-import=core.providers",
        "--exclude-module=torch",
        "--exclude-module=torchaudio",
        "--exclude-module=torchvision",
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=ipython",
        "--exclude-module=ipykernel",
        "--exclude-module=jupyter",
        "--exclude-module=notebook",
        "--exclude-module=tkinter",
        "--exclude-module=customtkinter",
        "--exclude-module=pytest",
        "--exclude-module=flake8",
        "--exclude-module=grpc",
        "--exclude-module=grpcio",
        "--exclude-module=tensorboard",
        "core/api_server.py"
    ]

    logger.info("Starting PyInstaller backend compilation...")
    result = subprocess.run(cmd, cwd=root_dir)
    if result.returncode != 0:
        logger.error(f"PyInstaller failed with code {result.returncode}")
        sys.exit(result.returncode)

    built_dir = dist_dir / backend_target_name
    exe_file = built_dir / f"{backend_target_name}.exe"
    if not exe_file.exists():
        logger.error(f"Compiled executable not found at: {exe_file}")
        sys.exit(1)

    # Clean up unnecessary non-Windows speech recognition files
    sr_dir = built_dir / "_internal" / "speech_recognition"
    if sr_dir.exists():
        for junk in ["flac-linux-x86", "flac-linux-x86_64", "flac-mac", "pocketsphinx-data"]:
            junk_path = sr_dir / junk
            if junk_path.is_dir():
                shutil.rmtree(junk_path, ignore_errors=True)
            elif junk_path.exists():
                junk_path.unlink()

    logger.info(f"✔ Successfully compiled backend: {exe_file}")

    # Destination 1: Misa/src-tauri/backend/ (for Tauri bundle.resources)
    tauri_backend_dir = root_dir / "Misa" / "src-tauri" / "backend"
    if tauri_backend_dir.exists():
        shutil.rmtree(tauri_backend_dir, ignore_errors=True)
    shutil.copytree(built_dir, tauri_backend_dir)
    logger.info(f"✔ Deployed backend to Tauri resources: {tauri_backend_dir}")

    # Destination 2: release/v9.0.1/backend/ (for release distribution)
    for rel_ver in ["v9.0.1", "v9.0.0", "v8.0.0"]:
        rel_dir = root_dir / "release" / rel_ver
        if rel_dir.exists():
            release_backend_dir = rel_dir / "backend"
            if release_backend_dir.exists():
                shutil.rmtree(release_backend_dir, ignore_errors=True)
            shutil.copytree(built_dir, release_backend_dir)
            logger.info(f"✔ Deployed backend to Release ({rel_ver}): {release_backend_dir}")

    logger.info("==================================================")
    logger.info("✨ Production Backend Bundling Complete!")
    logger.info("==================================================")

if __name__ == "__main__":
    build()
