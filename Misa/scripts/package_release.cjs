// ========== package_release.cjs ==========
// Misa AI 9.0 — Release Packaging and Version Management Script
// Places every built version into: yordamchi_9.0.0/release/v<version>/

const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

// 1. Get current version from package.json
const packageJsonPath = path.resolve(__dirname, "../package.json");
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, "utf-8"));
const version = packageJson.version || "9.3.0";
const match = version.match(/^(\d+\.\d+)/);
const versionName = match ? `v${match[1]}` : `v${version}`;

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
// 3. Locate built binaries (Always prioritize pure misa.exe)
const tauriReleaseDir = path.resolve(__dirname, "../src-tauri/target/release");
const tauriBundleDir = path.join(tauriReleaseDir, "bundle");

const legacyCands = ["misa-7.exe", "mikasa-7.exe", "mikasa.exe"];
for (const leg of legacyCands) {
  const p = path.join(releaseVersionDir, leg);
  if (fs.existsSync(p)) {
    try { fs.unlinkSync(p); } catch {}
  }
  const inTauri = path.join(tauriReleaseDir, leg);
  if (fs.existsSync(inTauri)) {
    try { fs.unlinkSync(inTauri); } catch {}
  }
}

let exeSource = path.join(tauriReleaseDir, "misa.exe");
const candidateExes = [
  path.join(tauriReleaseDir, "misa.exe"),
  path.join(tauriReleaseDir, "Misa.exe"),
  path.join(tauriReleaseDir, "Misa AI.exe"),
  path.join(tauriReleaseDir, "Misa-AI.exe"),
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
    const existingIdx = manifest.files.findIndex(f => f.name === path.basename(dest));
    const entry = {
      name: path.basename(dest),
      size_bytes: stat.size,
      size_mb: parseFloat((stat.size / (1024 * 1024)).toFixed(2)),
      sha256: hash,
    };
    if (existingIdx >= 0) {
      manifest.files[existingIdx] = entry;
    } else {
      manifest.files.push(entry);
    }
    return true;
  } else {
    console.warn(`⚠ Topilmadi: ${src}`);
    return false;
  }
}

// 4. Copy Standalone Executable
copyFileWithLog(exeSource, exeTarget, "Mustaqil (.exe)");
copyFileWithLog(exeSource, path.join(releaseVersionDir, "Misa.exe"), "Mustaqil (Misa.exe)");

// 4.1 Copy WebView2Loader.dll (required for native Windows execution on MinGW)
const dllSource = fs.existsSync(path.join(tauriReleaseDir, "WebView2Loader.dll"))
  ? path.join(tauriReleaseDir, "WebView2Loader.dll")
  : path.resolve(__dirname, "../src-tauri/WebView2Loader.dll");
const dllTarget = path.join(releaseVersionDir, "WebView2Loader.dll");
copyFileWithLog(dllSource, dllTarget, "WebView2 Loader DLL");

// 4.2 Copy Bundled Backend Runtime (if exists)
const backendSrcCandidates = [
  path.join(projectRoot, "dist/misa_backend"),
  path.join(projectRoot, "dist/backend_build/misa_backend"),
  path.resolve(__dirname, "../src-tauri/backend"),
  path.join(releaseVersionDir, "backend"),
  path.join(projectRoot, "release", "v9.0.1", "backend"),
  path.join(projectRoot, "dist/backend_build/mikasa_backend"),
  path.join(projectRoot, "release", "v8.0.0", "backend"),
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

// Har doim eng so'nggi core/ kodlarini backend runtime ga sinxronizatsiya qilish
const internalCoreTarget = path.join(backendTargetDir, "_internal", "core");
const workspaceCore = path.join(projectRoot, "core");
if (fs.existsSync(internalCoreTarget) && fs.existsSync(workspaceCore)) {
  fs.cpSync(workspaceCore, internalCoreTarget, { recursive: true, force: true });
  console.log(`✔ Backend _internal/core ga yangi kodlar sinxronlandi`);
}

// 5. Installers: Portable build is ALWAYS prioritized.
// Installers (.msi / .exe Setup) are only bundled if explicitly requested via --include-installers flag.
const includeInstallers = process.argv.includes("--include-installers") || process.argv.includes("--installers");

if (includeInstallers) {
  console.log(`📦 O'rnatuvchilar rejimi (--include-installers) faol`);
  // 5.1 Copy MSI Installer if exists
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

  // 5.2 Copy NSIS Setup if exists
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
} else {
  console.log(`✔ Standart Portativ reliz rejimi (O'rnatuvchi .msi / .exe faqat foydalanuvchi buyurtmasi bilan --include-installers orqali qilinadi)`);
  // Clean up any old installer files from release folder
  const staleInstallers = [
    path.join(releaseVersionDir, `Misa-AI-${versionName}.msi`),
    path.join(releaseVersionDir, `Misa-AI-Setup-${versionName}.exe`),
  ];
  for (const s of staleInstallers) {
    if (fs.existsSync(s)) {
      try { fs.unlinkSync(s); } catch {}
    }
  }
}

// 7. Write Quick One-Click Launcher (run_portable.bat)
const launcherBatContent = `@echo off
title Misa AI ${versionName} Launcher
cd /d "%~dp0"
attrib +r "%~dp0" >nul 2>&1
attrib +h +s "%~dp0desktop.ini" >nul 2>&1
echo ========================================================
echo   MISA AI ${versionName} - Launching Portable Desktop...
echo ========================================================

REM Launch Desktop App (Native Misa Preflight handles WebView2 detection, installation & verification)
start "" "Misa-AI-${versionName}.exe"
`;

const batPath = path.join(releaseVersionDir, "run_portable.bat");
fs.writeFileSync(batPath, launcherBatContent, "utf-8");
console.log(`✔ Ishga tushirish fayli: run_portable.bat`);

// 7.1 Locate & Bundle WebView2 Bootstrapper
const webview2Candidates = [
  path.resolve(__dirname, "../src-tauri/resources/MicrosoftEdgeWebview2Setup.exe"),
  path.join(releaseVersionDir, "webview2/MicrosoftEdgeWebview2Setup.exe"),
  path.join(releaseVersionDir, "MicrosoftEdgeWebview2Setup.exe"),
  path.join(process.env.TEMP || "", "MicrosoftEdgeWebview2Setup.exe"),
];
let webview2Source = null;
for (const cand of webview2Candidates) {
  if (fs.existsSync(cand)) {
    webview2Source = cand;
    break;
  }
}
const releaseWvDir = path.join(releaseVersionDir, "webview2");
if (!fs.existsSync(releaseWvDir)) {
  fs.mkdirSync(releaseWvDir, { recursive: true });
}
if (webview2Source) {
  const wvTarget = path.join(releaseWvDir, "MicrosoftEdgeWebview2Setup.exe");
  copyFileWithLog(webview2Source, wvTarget, "WebView2 Bootstrapper (webview2/)");
  copyFileWithLog(webview2Source, path.join(releaseVersionDir, "MicrosoftEdgeWebview2Setup.exe"), "WebView2 Bootstrapper (root)");
}

// 7.2 Create Dedicated Portable Directory: release/v<version>/portable/
const portableDir = path.join(releaseVersionDir, "portable");
if (!fs.existsSync(portableDir)) {
  fs.mkdirSync(portableDir, { recursive: true });
}
if (fs.existsSync(exeTarget)) {
  fs.copyFileSync(exeTarget, path.join(portableDir, `Misa-AI-${versionName}.exe`));
  fs.copyFileSync(exeTarget, path.join(portableDir, "Misa.exe"));
}
if (fs.existsSync(dllTarget)) {
  fs.copyFileSync(dllTarget, path.join(portableDir, "WebView2Loader.dll"));
}
if (fs.existsSync(batPath)) {
  fs.copyFileSync(batPath, path.join(portableDir, "run_portable.bat"));
}
if (fs.existsSync(backendTargetDir)) {
  fs.cpSync(backendTargetDir, path.join(portableDir, "backend"), { recursive: true });
}
if (webview2Source) {
  const portableWvDir = path.join(portableDir, "webview2");
  if (!fs.existsSync(portableWvDir)) fs.mkdirSync(portableWvDir, { recursive: true });
  fs.copyFileSync(webview2Source, path.join(portableWvDir, "MicrosoftEdgeWebview2Setup.exe"));
  fs.copyFileSync(webview2Source, path.join(portableDir, "MicrosoftEdgeWebview2Setup.exe"));
}

const introMp4Candidates = ["Misa.mp4", "Misa1.mp4", "misa_intro.mp4"];
for (const vid of introMp4Candidates) {
  const vidSrc = path.join(releaseVersionDir, vid);
  if (fs.existsSync(vidSrc)) {
    fs.copyFileSync(vidSrc, path.join(portableDir, vid));
    console.log(`✔ Intro Splash Video (${vid}) portativ papkaga nusxalandi`);
  }
}

// 7.2.1 Setup Custom Windows Folder Icon via desktop.ini and app.ico
const iconSource = path.resolve(__dirname, "../src-tauri/icons/icon.ico");
const desktopIniContent = `[.ShellClassInfo]
IconResource=app.ico,0
IconFile=app.ico
IconIndex=0
[ViewState]
Mode=
Vid=
FolderType=Generic
`;

function setupFolderIcon(dirPath) {
  if (!fs.existsSync(dirPath)) return;
  const icoTarget = path.join(dirPath, "app.ico");
  if (fs.existsSync(iconSource)) {
    try {
      if (fs.existsSync(icoTarget) && process.platform === "win32") {
        const { execSync } = require("child_process");
        execSync(`attrib -h -s -r "${icoTarget}"`, { stdio: "ignore" });
      }
      fs.copyFileSync(iconSource, icoTarget);
    } catch {}
  }
  const iniPath = path.join(dirPath, "desktop.ini");
  try {
    if (fs.existsSync(iniPath) && process.platform === "win32") {
      const { execSync } = require("child_process");
      execSync(`attrib -h -s -r "${iniPath}"`, { stdio: "ignore" });
    }
    fs.writeFileSync(iniPath, desktopIniContent, "utf-8");
    if (process.platform === "win32") {
      const { execSync } = require("child_process");
      execSync(`attrib +r "${dirPath}"`, { stdio: "ignore" });
      execSync(`attrib +h +s "${iniPath}"`, { stdio: "ignore" });
    }
  } catch {}
}

setupFolderIcon(releaseVersionDir);
setupFolderIcon(portableDir);
console.log(`✔ Windows Papka Ikonkasi (desktop.ini & app.ico) o'rnatildi`);
console.log(`✔ Tayyor Portativ Katalog: release/${versionName}/portable/`);

// 7.3 Build Complete Self-Contained Portable ZIP directly from portableDir
const zipTarget = path.join(releaseVersionDir, `Misa-AI-${versionName}-Portable.zip`);
try {
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
  const venvPy = path.join(projectRoot, ".venv", "Scripts", "python.exe");
  const pyExe = fs.existsSync(venvPy) ? `"${venvPy}"` : "python";
  const { execSync } = require("child_process");
  execSync(`${pyExe} "${pyScript}" "${portableDir}" "${zipTarget}"`, { stdio: "inherit" });
  if (fs.existsSync(pyScript)) fs.unlinkSync(pyScript);

  if (fs.existsSync(zipTarget)) {
    const stat = fs.statSync(zipTarget);
    const hash = calculateSha256(zipTarget);
    console.log(`✔ To'liq Portativ Paket: ${path.basename(zipTarget)} (${(stat.size / (1024 * 1024)).toFixed(2)} MB)`);
    const existingZipIdx = manifest.files.findIndex(f => f.name === path.basename(zipTarget));
    const zipEntry = {
      name: path.basename(zipTarget),
      size_bytes: stat.size,
      size_mb: parseFloat((stat.size / (1024 * 1024)).toFixed(2)),
      sha256: hash,
    };
    if (existingZipIdx >= 0) {
      manifest.files[existingZipIdx] = zipEntry;
    } else {
      manifest.files.push(zipEntry);
    }
  }
} catch (err) {
  console.warn(`⚠ Portable ZIP yaratishda ogohlantirish: ${err.message}`);
}

// 8. Write Manifest
const manifestPath = path.join(releaseVersionDir, "version_manifest.json");
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf-8");
console.log(`✔ Versiya manifesti: version_manifest.json`);

// 8.1 Write SHA256SUMS.txt
const sumsLines = [];
const primaryFiles = [
  `Misa-AI-${versionName}.exe`,
  ...(includeInstallers ? [`Misa-AI-Setup-${versionName}.exe`, `Misa-AI-${versionName}.msi`] : []),
  `Misa-AI-${versionName}-Portable.zip`
];
for (const pf of primaryFiles) {
  const pfp = path.join(releaseVersionDir, pf);
  if (fs.existsSync(pfp)) {
    const h = calculateSha256(pfp);
    sumsLines.push(`${h}  ${pf}`);
  }
}
if (sumsLines.length > 0) {
  fs.writeFileSync(path.join(releaseVersionDir, "SHA256SUMS.txt"), sumsLines.join("\n") + "\n", "utf-8");
  console.log(`✔ Kriptografik nazorat summalari: SHA256SUMS.txt`);
}

// 9. Update global RELEASES.md in release directory
const releasesMdPath = path.join(releaseBaseDir, "RELEASES.md");
let existingReleases = "";
if (fs.existsSync(releasesMdPath)) {
  existingReleases = fs.readFileSync(releasesMdPath, "utf-8");
}

const releaseEntry = `### [${versionName}] — ${new Date().toLocaleDateString("uz-UZ")}
- **Desktop Ilova (Portativ)**: \`${versionName}/Misa-AI-${versionName}.exe\`
- **Portativ Arxiv (.zip)**: \`${versionName}/Misa-AI-${versionName}-Portable.zip\`
- **Manifest**: \`${versionName}/version_manifest.json\`
- **Backend**: Python API Server (\`http://127.0.0.1:18420\`)
` + (includeInstallers ? `- **Windows MSI**: \`${versionName}/Misa-AI-${versionName}.msi\`\n- **NSIS Setup**: \`${versionName}/Misa-AI-Setup-${versionName}.exe\`\n` : "") + `\n`;

if (!existingReleases.includes(`### [${versionName}]`)) {
  const newReleasesMd = `# 🚀 Misa AI Versiyalar Arxiv (Releases Archive)\n\n` + releaseEntry + existingReleases.replace(/^# 🚀 (Mikasa|Misa) AI Versiyalar Arxiv \(Releases Archive\)\r?\n\r?\n/, "");
  fs.writeFileSync(releasesMdPath, newReleasesMd, "utf-8");
}



console.log(`========================================`);
console.log(`✨ ${versionName} reliz muvaffaqiyatli saqlandi!`);
console.log(`========================================`);
