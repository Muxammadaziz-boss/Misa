@echo off
title Misa AI v9.4 Launcher
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================================
echo   MISA AI v9.4 - Launching Portable Desktop...
echo ========================================================

REM 1. WebView2Loader.dll tekshiruvi (DLL muammosini oldini olish)
if not exist "WebView2Loader.dll" (
    echo [OGOHLANTIRISH] WebView2Loader.dll asosiy papkada topilmadi!
    if exist "webview2\WebView2Loader.dll" (
        copy /y "webview2\WebView2Loader.dll" "WebView2Loader.dll" >nul
        echo [OK] WebView2Loader.dll tiklandi.
    ) else if exist "backend\WebView2Loader.dll" (
        copy /y "backend\WebView2Loader.dll" "WebView2Loader.dll" >nul
        echo [OK] WebView2Loader.dll tiklandi.
    ) else (
        echo [XATOLIK] WebView2Loader.dll topilmadi. Iltimos, Misa.exe bilan birga ekanligiga ishonch hosil qiling.
        pause
        exit /b 1
    )
)

REM 2. Windows Edge WebView2 Runtime tekshiruvi
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-F552-4461-B5B9-9CE70246D2E0}" /v pv >nul 2>&1
if %errorlevel% neq 0 (
    reg query "HKCU\Software\Microsoft\EdgeUpdate\Clients\{F3017226-F552-4461-B5B9-9CE70246D2E0}" /v pv >nul 2>&1
    if %errorlevel% neq 0 (
        echo [OGOHLANTIRISH] Tizimda Microsoft Edge WebView2 topilmadi.
        if exist "webview2\MicrosoftEdgeWebview2Setup.exe" (
            echo [JARAYON] WebView2 avtomatik tarzda o'rnatilmoqda...
            "webview2\MicrosoftEdgeWebview2Setup.exe" /silent /install
        )
    )
)

REM 3. Portativ foydalanuvchi ma'lumotlari (Session va Login doimiyligi)
if not exist "%~dp0data\webview2" mkdir "%~dp0data\webview2" 2>nul
if not defined WEBVIEW2_USER_DATA_FOLDER set "WEBVIEW2_USER_DATA_FOLDER=%~dp0data\webview2"

attrib +r "%~dp0" >nul 2>&1
attrib +h +s "%~dp0desktop.ini" >nul 2>&1
echo [OK] Misa AI v9.4 ishga tushirilmoqda...
start "" "Misa.exe"
