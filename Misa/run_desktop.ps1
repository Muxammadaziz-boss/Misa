# Misa AI 9.0 Desktop Launcher (PowerShell)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   MISA AI 9.0 - DESKTOP ISHCHI STOLI ILOVASI    " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. Start Python backend on port 18420 if not already running
$bConn = Get-NetTCPConnection -LocalPort 18420 -ErrorAction SilentlyContinue
if (-not $bConn) {
    Write-Host "[1/3] Backend xizmati ishga tushirilmoqda (127.0.0.1:18420)..." -ForegroundColor Yellow
    $rootDir = (Resolve-Path "..").Path
    $parentDir = Split-Path $rootDir -Parent
    $pyCandidates = @(
        (Join-Path $parentDir ".venv\Scripts\python.exe"),
        (Join-Path $rootDir ".venv\Scripts\python.exe"),
        (Join-Path $rootDir "python\python.exe"),
        (Join-Path $rootDir "runtime\python.exe"),
        "python"
    )
    $chosenPy = "python"
    foreach ($py in $pyCandidates) {
        if ($py -ne "python" -and (Test-Path $py)) {
            $chosenPy = $py
            break
        }
    }
    Write-Host "[1/3] Python interpreter: $chosenPy" -ForegroundColor Cyan
    Start-Process -FilePath $chosenPy -ArgumentList "core\api_server.py" -WorkingDirectory $rootDir -WindowStyle Hidden
    Start-Sleep -Seconds 2
    Write-Host "[1/3] Backend muvaffaqiyatli ishga tushirildi (Port 18420)." -ForegroundColor Green
} else {
    Write-Host "[1/3] Backend allaqachon faol (Port 18420)." -ForegroundColor Green
}

# 2. Start dev server in background if not already running
$conn = Get-NetTCPConnection -LocalPort 1420 -ErrorAction SilentlyContinue
if (-not $conn) {
    Write-Host "[2/3] Frontend serveri ishga tushirilmoqda (Port 1420)..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WindowStyle Hidden
    Start-Sleep -Seconds 2
} else {
    Write-Host "[2/3] Frontend serveri allaqachon faol (Port 1420)." -ForegroundColor Green
}

# 3. Launch native desktop or web window
Write-Host "[3/3] Misa AI Desktop oynasi ochilmoqda..." -ForegroundColor Cyan

$nativeExe = "..\release\v9.0.1\Misa-AI-v9.0.1.exe"
if (-not (Test-Path $nativeExe)) {
    $nativeExe = "..\release\v9.0.0\Misa-AI-v9.0.0.exe"
}
if (Test-Path $nativeExe) {
    Start-Process $nativeExe
    Write-Host "Misa AI Native Desktop oynasi ochildi!" -ForegroundColor Green
    exit 0
}

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

if (Test-Path $chromePath) {
    Start-Process -FilePath $chromePath -ArgumentList "--app=http://localhost:1420", "--window-size=1280,800"
} elseif (Test-Path $edgePath) {
    Start-Process -FilePath $edgePath -ArgumentList "--app=http://localhost:1420", "--window-size=1280,800"
} else {
    Start-Process "http://localhost:1420"
}

Write-Host "Misa AI 9.0 Desktop oynasi ochildi!" -ForegroundColor Green

