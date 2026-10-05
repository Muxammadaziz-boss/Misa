// ========== package_release.cjs ==========
// Misa AI 9.0 — Release Packaging and Version Management Script
// Places every built version into: yordamchi_9.0.0/release/v<version>/

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

// 1. Get current version from package.json
const packageJsonPath = path.resolve(__dirname, "../package.json");
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"));
const version = packageJson.version || "9.0.0";
const versionName = `v${version}`;

// 2. Define release target directory inside yordamchi_9.0.0/release/v<version>
const projectRoot = path.resolve(__dirname, "../../");
const releaseBaseDir = path.resolve(projectRoot, "release");
const releaseVersionDir = path.join(releaseBaseDir, versionName);

console.log(`========================================`);
console.log(`📦 MISA AI Release Packaging: ${versionName}`);
console.log(`Katalog: ${releaseVersionDir}`);
console.log(`========================================`);

if (!fs.existsSync(releaseBaseDir)) {
  fs.mkdirSync(releaseBaseDir, { recursive: true });
}
if (!fs.existsSync(releaseVersionDir)) {
  fs.mkdirSync(releaseVersionDir, { recursive: true });
}

// Security: never ship .env in release folder
const envReleaseFile = path.join(releaseVersionDir, ".env");
if (fs.existsSync(envReleaseFile)) {
  try { fs.unlinkSync(envReleaseFile); } catch {}
}
const legacyCands = ["misa-7.exe", "Misa.exe"];
for (const leg of legacyCands) {
  const p = path.join(releaseVersionDir, leg);
  if (fs.existsSync(p)) {
    try { fs.unlinkSync(p); } catch {}
  }
}

// 3. Locate built binaries
const tauriReleaseDir = path.resolve(__dirname, "../src-tauri/target/release");
const tauriBundleDir = path.join(tauriReleaseDir, "bundle");

let exeSource = path.join(tauriReleaseDir, "misa-7.exe");
const candidateExes = [
  path.join(tauriReleaseDir, "misa-7.exe"),
  path.join(tauriReleaseDir, "Misa AI.exe"),
  path.join(tauriReleaseDir, "Misa-AI.exe"),
  path.join(tauriReleaseDir, "misa.exe"),
  path.join(tauriReleaseDir, "mikasa-7.exe"),
  path.join(tauriReleaseDir, "Mikasa AI.exe"),
  path.join(tauriReleaseDir, "Mikasa-AI.exe"),
  path.join(tauriReleaseDir, "mikasa.exe"),
];
for (const cand of candidateExes) {
  if (fs.existsSync(cand)) {
    exeSource = cand;
    break;
  }
}
const exeTarget = path.join(releaseVersionDir, `Misa-AI-${versionName}.exe`);

const manifest = {
  app: "Misa AI",
  version: version,
  version_name: versionName,
  release_date: new Date().toISOString(),
  files: [],
  backend: {
    service: "core/api_server.py",
    port: 18420,
    protocol: "HTTP/REST + WebSocket",
  },
};

function calculateSha256(filePath) {
  const fileBuffer = fs.readFileSync(filePath);
  return crypto.createHash("sha256").update(fileBuffer).digest("hex");
}

function copyFileWithLog(src, dest, friendlyName) {
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    const stat = fs.statSync(dest);
    const hash = calculateSha256(dest);
    console.log(`✔ ${friendlyName}: ${path.basename(dest)} (${(stat.size / (1024 * 1024)).toFixed(2)} MB)`);
    manifest.files.push({
      name: path.basename(dest),
      size_bytes: stat.size,
      size_mb: parseFloat((stat.size / (1024 * 1024)).toFixed(2)),
      sha256: hash,
    });
    return true;
  } else {
    console.warn(`⚠ Topilmadi: ${src}`);
    return false;
  }
}

// 4. Copy Standalone Executable
copyFileWithLog(exeSource, exeTarget, "Mustaqil (.exe)");

// 4.1 Copy WebView2Loader.dll (required for native Windows execution on MinGW)
const dllSource = fs.existsSync(path.join(tauriReleaseDir, "WebView2Loader.dll"))
  ? path.join(tauriReleaseDir, "WebView2Loader.dll")
  : path.resolve(__dirname, "../src-tauri/WebView2Loader.dll");
const dllTarget = path.join(releaseVersionDir, "WebView2Loader.dll");
copyFileWithLog(dllSource, dllTarget, "WebView2 Loader DLL");

// 4.2 Copy Bundled Backend Runtime (if exists)
const backendSrcCandidates = [
  path.resolve(__dirname, "../src-tauri/backend"),
  path.join(projectRoot, "release", "v8.0.0", "backend"),
  path.join(projectRoot, "dist/backend_build/mikasa_backend"),
  path.join(releaseVersionDir, "backend"),
];
let backendSourceDir = null;
for (const cand of backendSrcCandidates) {
  if (
    (fs.existsSync(path.join(cand, "mikasa_backend.exe")) ||
      fs.existsSync(path.join(cand, "misa_backend.exe"))) &&
    fs.existsSync(path.join(cand, "_internal", "python311.dll"))
  ) {
    backendSourceDir = cand;
    break;
  }
}
const backendTargetDir = path.join(releaseVersionDir, "backend");
if (backendSourceDir && backendSourceDir !== backendTargetDir) {
  if (!fs.existsSync(backendTargetDir)) {
    fs.mkdirSync(backendTargetDir, { recursive: true });
  }
  fs.cpSync(backendSourceDir, backendTargetDir, { recursive: true, force: true });
  console.log(`✔ Bundled Backend Runtime (_internal bilan) joylandi: ${path.basename(backendTargetDir)}`);
} else if (fs.existsSync(path.join(backendTargetDir, "_internal", "python311.dll"))) {
  console.log(`✔ Bundled Backend Runtime (_internal bilan) mavjud: ${path.basename(backendTargetDir)}`);
}

// 5. Copy MSI Installer if exists
const msiDir = path.join(tauriBundleDir, "msi");
if (fs.existsSync(msiDir)) {
  const msiFiles = fs.readdirSync(msiDir)
    .filter((f) => f.endsWith(".msi"))
    .sort((a, b) => {
      const aVer = a.includes(version) ? 1 : 0;
      const bVer = b.includes(version) ? 1 : 0;
      if (bVer !== aVer) return bVer - aVer;
      return fs.statSync(path.join(msiDir, b)).mtimeMs - fs.statSync(path.join(msiDir, a)).mtimeMs;
    });
  if (msiFiles.length > 0) {
    const srcMsi = path.join(msiDir, msiFiles[0]);
    const destMsi = path.join(releaseVersionDir, `Misa-AI-${versionName}.msi`);
    copyFileWithLog(srcMsi, destMsi, "MSI Installer");
  }
}

// 6. Copy NSIS Setup if exists
const nsisDir = path.join(tauriBundleDir, "nsis");
if (fs.existsSync(nsisDir)) {
  const nsisFiles = fs.readdirSync(nsisDir)
    .filter((f) => f.endsWith(".exe"))
    .sort((a, b) => {
      const aVer = a.includes(version) ? 1 : 0;
      const bVer = b.includes(version) ? 1 : 0;
      if (bVer !== aVer) return bVer - aVer;
      return fs.statSync(path.join(nsisDir, b)).mtimeMs - fs.statSync(path.join(nsisDir, a)).mtimeMs;
    });
  if (nsisFiles.length > 0) {
    const srcNsis = path.join(nsisDir, nsisFiles[0]);
    const destNsis = path.join(releaseVersionDir, `Misa-AI-Setup-${versionName}.exe`);
    copyFileWithLog(srcNsis, destNsis, "NSIS Setup (.exe)");
  }
}

// 7. Write Quick One-Click Launcher (run_portable.bat)
const launcherBatContent = `@echo off
title Misa AI ${versionName} Launcher
cd /d "%~dp0"
echo ========================================================
echo   MISA AI ${versionName} - Launching Portable Desktop...
echo ========================================================

REM 1. Check if backend is already listening on port 18420
powershell -NoProfile -Command "$conn = Test-NetConnection -ComputerName 127.0.0.1 -Port 18420 -WarningAction SilentlyContinue -InformationLevel Quiet; if (-not $conn) { Write-Host 'Starting Misa Backend Service (127.0.0.1:18420)...' -ForegroundColor Cyan; $bExe = if (Test-Path '.\\\\backend\\\\misa_backend.exe') { '.\\\\backend\\\\misa_backend.exe' } elseif (Test-Path '.\\\\backend\\\\mikasa_backend.exe') { '.\\\\backend\\\\mikasa_backend.exe' } else { $null }; if ($bExe) { Start-Process -FilePath $bExe -WorkingDirectory '.\\\\backend' -WindowStyle Hidden; Start-Sleep -Milliseconds 1500 } else { $workDir = if (Test-Path '.\\\\core\\\\api_server.py') { (Resolve-Path '.').Path } elseif (Test-Path '..\\\\..\\\\core\\\\api_server.py') { (Resolve-Path '..\\\\..').Path } else { (Resolve-Path '.').Path }; $cands = @('.\\\\python\\\\python.exe', '.\\\\runtime\\\\python.exe', (Join-Path $workDir '.venv\\\\Scripts\\\\python.exe'), (Join-Path $workDir '..\\\\.venv\\\\Scripts\\\\python.exe'), (Join-Path $workDir '..\\\\..\\\\.venv\\\\Scripts\\\\python.exe'), 'python'); $chosen = 'python'; foreach ($c in $cands) { if ($c -eq 'python') { $chosen = 'python'; break } elseif (Test-Path $c) { $chosen = (Resolve-Path $c).Path; break } } Start-Process -FilePath $chosen -ArgumentList 'core\\\\api_server.py' -WorkingDirectory $workDir -WindowStyle Hidden; Start-Sleep -Seconds 2 } }"

REM 2. Start Desktop App
start "" "Misa-AI-${versionName}.exe"
`;

const batPath = path.join(releaseVersionDir, "run_portable.bat");
fs.writeFileSync(batPath, launcherBatContent, "utf-8");
console.log(`✔ Ishga tushirish fayli: run_portable.bat`);

// 7.1 Build Complete Self-Contained Portable ZIP
const zipTarget = path.join(releaseVersionDir, `Misa-AI-${versionName}-Portable.zip`);
const tempZipStaging = path.join(releaseVersionDir, `Misa-AI-${versionName}-Portable`);
try {
  if (fs.existsSync(tempZipStaging)) {
    fs.rmSync(tempZipStaging, { recursive: true, force: true });
  }
  fs.mkdirSync(tempZipStaging, { recursive: true });

  if (fs.existsSync(exeTarget)) {
    fs.copyFileSync(exeTarget, path.join(tempZipStaging, `Misa-AI-${versionName}.exe`));
  }
  if (fs.existsSync(dllTarget)) {
    fs.copyFileSync(dllTarget, path.join(tempZipStaging, "WebView2Loader.dll"));
  }
  if (fs.existsSync(batPath)) {
    fs.copyFileSync(batPath, path.join(tempZipStaging, "run_portable.bat"));
  }
  if (fs.existsSync(backendTargetDir)) {
    fs.cpSync(backendTargetDir, path.join(tempZipStaging, "backend"), { recursive: true });
  }

  if (fs.existsSync(zipTarget)) {
    fs.unlinkSync(zipTarget);
  }
  const pyCode = `import zipfile, os, sys
src = sys.argv[1]
dst = sys.argv[2]
with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(src):
        for f in files:
            p = os.path.join(root, f)
            zf.write(p, os.path.relpath(p, src))
`;
  const pyScript = path.join(releaseVersionDir, "_make_zip.py");
  fs.writeFileSync(pyScript, pyCode, "utf-8");
  const pyExe = fs.existsSync("d:\\\\Ishchi stoli\\\\Misa\\\\.venv\\\\Scripts\\\\python.exe")
    ? '"d:\\\\Ishchi stoli\\\\Misa\\\\.venv\\\\Scripts\\\\python.exe"'
    : fs.existsSync("d:\\\\Ishchi stoli\\\\Mikasa\\\\.venv\\\\Scripts\\\\python.exe")
    ? '"d:\\\\Ishchi stoli\\\\Mikasa\\\\.venv\\\\Scripts\\\\python.exe"'
    : "python";
  const { execSync } = require("child_process");
  execSync(`${pyExe} "${pyScript}" "${tempZipStaging}" "${zipTarget}"`, { stdio: "inherit" });
  if (fs.existsSync(pyScript)) fs.unlinkSync(pyScript);
  fs.rmSync(tempZipStaging, { recursive: true, force: true });

  if (fs.existsSync(zipTarget)) {
    const stat = fs.statSync(zipTarget);
    const hash = calculateSha256(zipTarget);
    console.log(`✔ To'liq Portativ Paket: ${path.basename(zipTarget)} (${(stat.size / (1024 * 1024)).toFixed(2)} MB)`);
    manifest.files.push({
      name: path.basename(zipTarget),
      size_bytes: stat.size,
      size_mb: parseFloat((stat.size / (1024 * 1024)).toFixed(2)),
      sha256: hash,
    });
  }
} catch (err) {
  console.warn(`⚠ Portable ZIP yaratishda ogohlantirish: ${err.message}`);
}

// 8. Write Manifest
const manifestPath = path.join(releaseVersionDir, "version_manifest.json");
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf-8");
console.log(`✔ Versiya manifesti: version_manifest.json`);

// 9. Update global RELEASES.md in release directory
const releasesMdPath = path.join(releaseBaseDir, "RELEASES.md");
let existingReleases = "";
if (fs.existsSync(releasesMdPath)) {
  existingReleases = fs.readFileSync(releasesMdPath, "utf-8");
}

const releaseEntry = `### [${versionName}] — ${new Date().toLocaleDateString("uz-UZ")}
- **Desktop Ilova**: \`${versionName}/Misa-AI-${versionName}.exe\`
- **Windows MSI**: \`${versionName}/Misa-AI-${versionName}.msi\`
- **NSIS Setup**: \`${versionName}/Misa-AI-Setup-${versionName}.exe\`
- **Manifest**: \`${versionName}/version_manifest.json\`
- **Backend**: Python API Server (\`http://127.0.0.1:18420\`)

`;

if (!existingReleases.includes(`### [${versionName}]`)) {
  const newReleasesMd = `# 🚀 Misa AI Versiyalar Arxiv (Releases Archive)\n\n` + releaseEntry + existingReleases.replace(/^# 🚀 (Mikasa|Misa) AI Versiyalar Arxiv \(Releases Archive\)\r?\n\r?\n/, "");
  fs.writeFileSync(releasesMdPath, newReleasesMd, "utf-8");
}

console.log(`========================================`);
console.log(`✨ ${versionName} reliz muvaffaqiyatli saqlandi!`);
console.log(`========================================`);
