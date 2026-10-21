@echo off
title Misa AI v9.3 Launcher
cd /d "%~dp0"
echo ========================================================
echo   MISA AI v9.3 - Launching Portable Desktop...
echo ========================================================

REM Launch Desktop App (Native Misa Preflight handles WebView2 detection, installation & verification)
start "" "Misa-AI-v9.3.exe"
