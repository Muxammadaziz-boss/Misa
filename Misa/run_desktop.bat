@echo off
title Misa AI 9.0 Desktop
echo ===================================================
echo    MISA AI 9.0 - DESKTOP ISHCHI STOLI ILOVASI
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/3] Backend xizmati tekshirilmoqda (127.0.0.1:18420)...
powershell -NoProfile -Command "$conn = Test-NetConnection -ComputerName 127.0.0.1 -Port 18420 -WarningAction SilentlyContinue -InformationLevel Quiet; if (-not $conn) { Write-Host 'Backend ishga tushirilmoqda...' -ForegroundColor Yellow; $root = (Resolve-Path '..').Path; $pyCandidates = @((Join-Path $root '.venv\Scripts\python.exe'), (Join-Path $root 'python\python.exe'), (Join-Path $root 'runtime\python.exe'), 'python'); $chosenPy = 'python'; foreach ($py in $pyCandidates) { if ($py -eq 'python' -or (Test-Path $py)) { $chosenPy = $py; break; } } Start-Process -FilePath $chosenPy -ArgumentList 'core\api_server.py' -WorkingDirectory $root -WindowStyle Hidden; Start-Sleep -Seconds 2; Write-Host 'Backend muvaffaqiyatli ishga tushirildi (Port 18420).' -ForegroundColor Green; } else { Write-Host 'Backend allaqachon faol (Port 18420).' -ForegroundColor Green; }"

echo.
echo [2/3] Frontend serveri tekshirilmoqda (Port 1420)...
powershell -NoProfile -Command "$conn = Test-NetConnection -ComputerName 127.0.0.1 -Port 1420 -WarningAction SilentlyContinue -InformationLevel Quiet; if (-not $conn) { Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', 'npm run dev' -WindowStyle Hidden; Start-Sleep -Seconds 2; }"

echo.
echo [3/3] Misa AI 9.0 Desktop oynasi ochilmoqda...

set NATIVE_EXE="..\release\v9.0.0\Misa-AI-v9.0.0.exe"
if exist %NATIVE_EXE% (
    start "" %NATIVE_EXE%
    echo Misa AI 9.0 Native Desktop oynasi ochildi!
    exit /b 0
)

set CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"
set EDGE="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

if exist %CHROME% (
    start "" %CHROME% --app="http://localhost:1420" --window-size=1280,800 --app-id=misa-ai-9
) else if exist %EDGE% (
    start "" %EDGE% --app="http://localhost:1420" --window-size=1280,800
) else (
    start http://localhost:1420
)

echo.
echo Misa AI 9.0 Desktop oynasi muvaffaqiyatli ochildi!
echo.

