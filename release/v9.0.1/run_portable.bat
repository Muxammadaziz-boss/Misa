@echo off
title Misa AI v9.0.1 Launcher
cd /d "%~dp0"
echo ========================================================
echo   MISA AI v9.0.1 - Launching Portable Desktop...
echo ========================================================

REM 1. Verify Microsoft Edge WebView2 Runtime before starting backend
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$hklm64 = 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'; " ^
  "$hklm32 = 'HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'; " ^
  "$hkcu = 'HKCU:\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'; " ^
  "$v = (Get-ItemProperty -Path @($hklm64, $hklm32, $hkcu) -Name 'pv' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty pv -First 1); " ^
  "$dir1 = (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\EdgeWebView\Application'); " ^
  "$dir2 = (Join-Path $env:ProgramFiles 'Microsoft\EdgeWebView\Application'); " ^
  "$hasDir = (Test-Path $dir1) -or (Test-Path $dir2); " ^
  "if ((-not $v -or $v -eq '0.0.0.0') -and (-not $hasDir)) { " ^
  "  Write-Host '[MISA] Microsoft WebView2 Runtime topilmadi!' -ForegroundColor Yellow; " ^
  "  Write-Host '[MISA] WebView2 Runtime o''rnatilmoqda (Evergreen Bootstrapper)...' -ForegroundColor Cyan; " ^
  "  $setup = if (Test-Path '.\MicrosoftEdgeWebview2Setup.exe') { '.\MicrosoftEdgeWebview2Setup.exe' } else { (Join-Path $env:TEMP 'MicrosoftEdgeWebview2Setup.exe') }; " ^
  "  try { " ^
  "    if (-not (Test-Path $setup)) { Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $setup -UseBasicParsing }; " ^
  "    Start-Process -FilePath $setup -ArgumentList '/silent /install' -Wait; " ^
  "    Write-Host '[MISA] WebView2 Runtime o''rnatildi ✓' -ForegroundColor Green; " ^
  "  } catch { " ^
  "    Write-Host '[MISA XATOLIK] WebView2 Runtime o''rnatilmadi!' -ForegroundColor Red; " ^
  "    [System.Windows.Forms.MessageBox]::Show('Microsoft WebView2 Runtime o''rnatilmadi. Misa UI ochilishi uchun WebView2 kerak. Iltimos, uni rasmiy saytdan o''rnating: https://developer.microsoft.com/microsoft-edge/webview2/', 'Misa AI', 'OK', 'Error'); " ^
  "    exit 1; " ^
  "  } " ^
  "}"
if errorlevel 1 (
  echo [MISA] WebView2 mavjud emasligi sababli ishga tushirish bekor qilindi. Backend ochilmadi.
  pause
  exit /b 1
)

REM 2. Launch Desktop App (Tauri UI manages backend lifecycle as parent process)
start "" "Misa-AI-v9.0.1.exe"
