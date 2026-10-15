@echo off
title Misa AI 9.0 Desktop
echo ===================================================
echo    MISA AI 9.0 - DESKTOP ISHCHI STOLI ILOVASI
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/3] Microsoft WebView2 Runtime tekshirilmoqda...
powershell -NoProfile -Command ^
  "$keys = @('HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'); " ^
  "$found = $false; " ^
  "foreach ($k in $keys) { if (Test-Path $k) { $pv = (Get-ItemProperty -Path $k -ErrorAction SilentlyContinue).pv; if ($pv -and $pv -ne '0.0.0.0' -and $pv -ne '') { $found = $true; break; } } } " ^
  "if (-not $found) { " ^
  "  $paths = @(\"${env:ProgramFiles(x86)}\Microsoft\EdgeWebView\Application\", \"${env:ProgramFiles}\Microsoft\EdgeWebView\Application\"); " ^
  "  foreach ($p in $paths) { if (Test-Path $p) { $exe = Get-ChildItem -Path $p -Filter 'msedgewebview2.exe' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1; if ($exe) { $found = $true; break; } } } " ^
  "} " ^
  "if (-not $found) { exit 1; } else { exit 0; }"

if %ERRORLEVEL% NEQ 0 (
    echo [OGOHLANTIRISH] Microsoft WebView2 Runtime topilmadi!
    echo Evergreen Bootstrapper yuklab olinmoqda va o'rnatilmoqda...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile '$env:TEMP\MicrosoftEdgeWebview2Setup.exe' -UseBasicParsing; Start-Process -FilePath \"$env:TEMP\MicrosoftEdgeWebview2Setup.exe\" -ArgumentList '/silent', '/install' -Wait"
    rem Check again
    powershell -NoProfile -Command ^
      "$keys = @('HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'); " ^
      "$found = $false; foreach ($k in $keys) { if (Test-Path $k) { $pv = (Get-ItemProperty -Path $k -ErrorAction SilentlyContinue).pv; if ($pv -and $pv -ne '0.0.0.0') { $found = $true; break; } } } " ^
      "if (-not $found) { exit 1; } else { exit 0; }"
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo XATOLIK: Microsoft WebView2 Runtime o'rnatilmadi.
        echo Misa UI ishga tushishi uchun WebView2 kerak.
        echo Iltimos, WebView2 Runtime'ni qo'lda o'rnating: https://go.microsoft.com/fwlink/p/?LinkId=2124703
        pause
        exit /b 1
    )
)
echo [1/3] Microsoft WebView2 Runtime mavjud.

echo.
echo [2/3] Backend xizmati tekshirilmoqda (127.0.0.1:18420)...
powershell -NoProfile -Command ^
  "$isHealthy = $false; " ^
  "try { $resp = Invoke-RestMethod -Uri 'http://127.0.0.1:18420/api/health' -TimeoutSec 2 -ErrorAction Stop; if ($resp.status -eq 'ok' -or $resp.version) { $isHealthy = $true; } } catch {}; " ^
  "if (-not $isHealthy) { " ^
  "  $bConn = Get-NetTCPConnection -LocalPort 18420 -ErrorAction SilentlyContinue; " ^
  "  if ($bConn) { foreach ($c in $bConn) { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; } Start-Sleep -Milliseconds 500; } " ^
  "  Write-Host 'Backend ishga tushirilmoqda...' -ForegroundColor Yellow; " ^
  "  $root = (Resolve-Path '..').Path; $parentRoot = (Split-Path $root -Parent); " ^
  "  $pyCandidates = @((Join-Path $parentRoot '.venv\Scripts\python.exe'), (Join-Path $root '.venv\Scripts\python.exe'), (Join-Path $root 'python\python.exe'), (Join-Path $root 'runtime\python.exe'), 'python'); " ^
  "  $chosenPy = 'python'; foreach ($py in $pyCandidates) { if ($py -ne 'python' -and (Test-Path $py)) { $chosenPy = $py; break; } }; " ^
  "  Start-Process -FilePath $chosenPy -ArgumentList 'core\api_server.py' -WorkingDirectory $root -WindowStyle Hidden; " ^
  "  Start-Sleep -Seconds 2; " ^
  "  Write-Host 'Backend muvaffaqiyatli ishga tushirildi (Port 18420).' -ForegroundColor Green; " ^
  "} else { Write-Host 'Backend allaqachon faol (Port 18420).' -ForegroundColor Green; }"

echo.
echo [3/3] Misa AI 9.0 Desktop oynasi ochilmoqda...

set NATIVE_EXE="..\release\v9.0.2\Misa-AI-v9.0.2.exe"
if not exist %NATIVE_EXE% (
    set NATIVE_EXE="..\release\v9.0.1\Misa-AI-v9.0.1.exe"
)
if not exist %NATIVE_EXE% (
    set NATIVE_EXE="..\release\v9.0.0\Misa-AI-v9.0.0.exe"
)
if not exist %NATIVE_EXE% (
    set NATIVE_EXE="src-tauri\target\release\misa-ai.exe"
)
if exist %NATIVE_EXE% (
    start "" %NATIVE_EXE%
    echo Misa AI Native Desktop oynasi ochildi!
    exit /b 0
)

echo Mahalliy ishlab chiquvchi rejimida Tauri ishga tushirilmoqda...
node scripts\tauri.js dev


