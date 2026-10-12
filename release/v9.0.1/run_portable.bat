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
  "$dir3 = (Join-Path $env:LOCALAPPDATA 'Microsoft\EdgeWebView\Application'); " ^
  "$hasDir = (Test-Path $dir1) -or (Test-Path $dir2) -or (Test-Path $dir3); " ^
  "if ((-not $v -or $v -eq '0.0.0.0') -and (-not $hasDir)) { " ^
  "  Write-Host '[MISA] Microsoft WebView2 Runtime topilmadi!' -ForegroundColor Yellow; " ^
  "  Write-Host '[MISA] Misa AI uchun Microsoft WebView2 Runtime kerak. O''rnatilmoqda...' -ForegroundColor Cyan; " ^
  "  $cands = @('.\webview2\MicrosoftEdgeWebview2Setup.exe', '.\MicrosoftEdgeWebview2Setup.exe', (Join-Path $env:TEMP 'MicrosoftEdgeWebview2Setup.exe')); " ^
  "  $setup = $cands | Where-Object { Test-Path $_ } | Select-Object -First 1; " ^
  "  if (-not $setup) { " ^
  "    $setup = Join-Path $env:TEMP 'MicrosoftEdgeWebview2Setup.exe'; " ^
  "    try { " ^
  "      Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $setup -TimeoutSec 30 -UseBasicParsing; " ^
  "    } catch { " ^
  "      Write-Host '[MISA XATOLIK] WebView2 bootstrapper yuklab olinmadi (Internet yo''q)!' -ForegroundColor Red; " ^
  "      exit 1; " ^
  "    } " ^
  "  } " ^
  "  Write-Host ('[MISA] Bootstrapper ishga tushirilmoqda: ' + $setup) -ForegroundColor Cyan; " ^
  "  Start-Process -FilePath $setup -ArgumentList '/silent /install' -Wait; " ^
  "  Start-Sleep -Seconds 1; " ^
  "  $v2 = (Get-ItemProperty -Path @($hklm64, $hklm32, $hkcu) -Name 'pv' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty pv -First 1); " ^
  "  $hasDir2 = (Test-Path $dir1) -or (Test-Path $dir2) -or (Test-Path $dir3); " ^
  "  if ((-not $v2 -or $v2 -eq '0.0.0.0') -and (-not $hasDir2)) { " ^
  "    Write-Host '[MISA] Silent rejim orqali o''rnatilmadi. UAC interaktiv oyna ochilmoqda...' -ForegroundColor Yellow; " ^
  "    Start-Process -FilePath $setup -ArgumentList '/install' -Wait; " ^
  "    Start-Sleep -Seconds 1; " ^
  "    $v3 = (Get-ItemProperty -Path @($hklm64, $hklm32, $hkcu) -Name 'pv' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty pv -First 1); " ^
  "    $hasDir3 = (Test-Path $dir1) -or (Test-Path $dir2) -or (Test-Path $dir3); " ^
  "    if ((-not $v3 -or $v3 -eq '0.0.0.0') -and (-not $hasDir3)) { " ^
  "      Write-Host '[MISA XATOLIK] Microsoft WebView2 Runtime o''rnatilmadi!' -ForegroundColor Red; " ^
  "      exit 1; " ^
  "    } " ^
  "  } " ^
  "  Write-Host '[MISA] Misa AI ishga tushirilmoqda... ✓' -ForegroundColor Green; " ^
  "}"
if errorlevel 1 (
  echo [MISA] WebView2 mavjud emasligi sababli ishga tushirish bekor qilindi. Backend ochilmadi.
  pause
  exit /b 1
)

REM 2. Launch Desktop App (Tauri UI manages backend lifecycle as parent process)
start "" "Misa-AI-v9.0.1.exe"
