# Misa AI 9.0 Desktop Launcher (PowerShell)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   MISA AI 9.0 - DESKTOP ISHCHI STOLI ILOVASI    " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# 1. WebView2 Runtime pre-flight validation
Write-Host "[1/3] Microsoft WebView2 Runtime tekshirilmoqda..." -ForegroundColor Cyan

function Test-WebView2Installed {
    $keys = @(
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    )
    foreach ($k in $keys) {
        if (Test-Path $k) {
            $pv = (Get-ItemProperty -Path $k -ErrorAction SilentlyContinue).pv
            if ($pv -and $pv -ne "0.0.0.0" -and $pv -ne "") { return $true }
        }
    }
    $paths = @(
        "${env:ProgramFiles(x86)}\Microsoft\EdgeWebView\Application",
        "${env:ProgramFiles}\Microsoft\EdgeWebView\Application"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) {
            $exe = Get-ChildItem -Path $p -Filter "msedgewebview2.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($exe) { return $true }
        }
    }
    return $false
}

$hasWv2 = Test-WebView2Installed
if (-not $hasWv2) {
    Write-Host "[OGOHLANTIRISH] Microsoft WebView2 Runtime topilmadi!" -ForegroundColor Yellow
    Write-Host "Evergreen Bootstrapper yuklab olinmoqda va o'rnatilmoqda..." -ForegroundColor Yellow
    $setupUrl = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
    $tempSetup = Join-Path $env:TEMP "MicrosoftEdgeWebview2Setup.exe"
    try {
        Invoke-WebRequest -Uri $setupUrl -OutFile $tempSetup -UseBasicParsing
        $proc = Start-Process -FilePath $tempSetup -ArgumentList "/silent", "/install" -PassThru -Wait
        Start-Sleep -Seconds 3
    } catch {
        Write-Host "Avtomatik yuklab olishda xatolik yuz berdi." -ForegroundColor Red
    }

    if (-not (Test-WebView2Installed)) {
        Write-Host "XATOLIK: Microsoft WebView2 Runtime o'rnatilmadi." -ForegroundColor Red
        Write-Host "Misa UI ishga tushishi uchun WebView2 kerak." -ForegroundColor Red
        Write-Host "Iltimos, WebView2 Runtime'ni qo'lda o'rnating: https://go.microsoft.com/fwlink/p/?LinkId=2124703" -ForegroundColor Yellow
        [System.Windows.Forms.MessageBox]::Show("Microsoft WebView2 Runtime o'rnatilmadi.`nMisa UI ishga tushishi uchun WebView2 kerak.", "Misa AI - Xatolik", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
        exit 1
    }
    Write-Host "Microsoft WebView2 Runtime muvaffaqiyatli o'rnatildi!" -ForegroundColor Green
} else {
    Write-Host "[1/3] Microsoft WebView2 Runtime mavjud." -ForegroundColor Green
}

# 2. Start Python backend on port 18420 if not already healthy
Write-Host "[2/3] Backend xizmati tekshirilmoqda (127.0.0.1:18420)..." -ForegroundColor Cyan
$isHealthy = $false
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:18420/api/health" -TimeoutSec 2 -ErrorAction Stop
    if ($resp.status -eq "ok" -or $resp.version) { $isHealthy = $true }
} catch {
    $isHealthy = $false
}

if (-not $isHealthy) {
    # Check if a stale process is holding port 18420
    $bConn = Get-NetTCPConnection -LocalPort 18420 -ErrorAction SilentlyContinue
    if ($bConn) {
        Write-Host "Nosoz/qotib qolgan jarayon port 18420 ni egallagan, tozalanmoqda..." -ForegroundColor Yellow
        foreach ($c in $bConn) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 500
    }

    Write-Host "Backend xizmati ishga tushirilmoqda..." -ForegroundColor Yellow
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
    Write-Host "Python interpreter: $chosenPy" -ForegroundColor Cyan
    Start-Process -FilePath $chosenPy -ArgumentList "core\api_server.py" -WorkingDirectory $rootDir -WindowStyle Hidden
    
    # Wait for backend health check
    $retries = 15
    while ($retries -gt 0 -and -not $isHealthy) {
        Start-Sleep -Milliseconds 600
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:18420/api/health" -TimeoutSec 1 -ErrorAction Stop
            if ($resp.status -eq "ok" -or $resp.version) { $isHealthy = $true }
        } catch {}
        $retries--
    }
    if ($isHealthy) {
        Write-Host "[2/3] Backend muvaffaqiyatli ishga tushirildi va faol (Port 18420)." -ForegroundColor Green
    } else {
        Write-Host "[OGOHLANTIRISH] Backend hali javob bermadi, ammo davom etilmoqda." -ForegroundColor Yellow
    }
} else {
    Write-Host "[2/3] Backend allaqachon faol (Port 18420)." -ForegroundColor Green
}

# 3. Launch native desktop Tauri UI (No browser fallback)
Write-Host "[3/3] Misa AI Desktop oynasi ochilmoqda..." -ForegroundColor Cyan

$nativeExe = "..\release\v9.2\Misa-AI-v9.2.exe"
if (-not (Test-Path $nativeExe)) {
    $nativeExe = "..\release\v9.0.2\Misa-AI-v9.0.2.exe"
}
if (-not (Test-Path $nativeExe)) {
    $nativeExe = "..\release\v9.0.1\Misa-AI-v9.0.1.exe"
}
if (-not (Test-Path $nativeExe)) {
    $nativeExe = "..\release\v9.0.0\Misa-AI-v9.0.0.exe"
}
if (-not (Test-Path $nativeExe)) {
    $nativeExe = "src-tauri\target\release\misa-ai.exe"
}

if (Test-Path $nativeExe) {
    Start-Process $nativeExe
    Write-Host "Misa AI Native Desktop oynasi ochildi!" -ForegroundColor Green
    exit 0
}

# If no built binary exists in dev mode, launch via Tauri dev runner
Write-Host "Mahalliy ishlab chiquvchi (development) rejimida Tauri ishga tushirilmoqda..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "node scripts/tauri.js dev" -NoNewWindow


