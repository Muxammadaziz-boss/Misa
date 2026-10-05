@echo off
title Misa AI v9.0.1 Launcher
cd /d "%~dp0"
echo ========================================================
echo   MISA AI v9.0.1 - Launching Portable Desktop...
echo ========================================================

REM 1. Check if backend is already listening on port 18420
powershell -NoProfile -Command "$conn = Test-NetConnection -ComputerName 127.0.0.1 -Port 18420 -WarningAction SilentlyContinue -InformationLevel Quiet; if (-not $conn) { Write-Host 'Starting Misa Backend Service (127.0.0.1:18420)...' -ForegroundColor Cyan; $bExe = if (Test-Path '.\\backend\\misa_backend.exe') { '.\\backend\\misa_backend.exe' } elseif (Test-Path '.\\backend\\mikasa_backend.exe') { '.\\backend\\mikasa_backend.exe' } else { $null }; if ($bExe) { Start-Process -FilePath $bExe -WorkingDirectory '.\\backend' -WindowStyle Hidden; Start-Sleep -Milliseconds 1500 } else { $workDir = if (Test-Path '.\\core\\api_server.py') { (Resolve-Path '.').Path } elseif (Test-Path '..\\..\\core\\api_server.py') { (Resolve-Path '..\\..').Path } else { (Resolve-Path '.').Path }; $cands = @('.\\python\\python.exe', '.\\runtime\\python.exe', (Join-Path $workDir '.venv\\Scripts\\python.exe'), 'python'); $chosen = 'python'; foreach ($c in $cands) { if ($c -eq 'python') { $chosen = 'python'; break } elseif (Test-Path $c) { $chosen = (Resolve-Path $c).Path; break } } Start-Process -FilePath $chosen -ArgumentList 'core\\api_server.py' -WorkingDirectory $workDir -WindowStyle Hidden; Start-Sleep -Seconds 2 } }"

REM 2. Start Desktop App
start "" "Misa-AI-v9.0.1.exe"
