@echo off
title Misa AI v9.4 Launcher
cd /d "%~dp0"
attrib +r "%~dp0" >nul 2>&1
attrib +h +s "%~dp0desktop.ini" >nul 2>&1
echo ========================================================
echo   MISA AI v9.4 - Launching Portable Desktop...
echo ========================================================

REM Launch Desktop App (Native Misa Preflight handles WebView2 detection, installation & verification)
start "" "Misa.exe"
