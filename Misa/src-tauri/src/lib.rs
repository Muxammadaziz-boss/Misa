// ========== lib.rs ==========
// Misa AI 9.0.0 — Native Desktop Window Management & Runtime Backend Supervisor
// To'liq mahalliy boshqaruv, HTTP /api/health tekshiruvi, bolalar jarayonlarini xavfsiz tozalash

use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tauri::Manager;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

pub mod diag;
pub use diag::{startup_log, crash_log, network_log, backend_lifecycle_log, voice_runtime_log, install_crash_handlers, current_pid, current_tid};

pub mod preflight;
pub use preflight::{run_native_preflight, check_webview2_installed_version, find_or_fetch_bootstrapper};

pub mod network_diag;
pub use network_diag::{run_full_diagnostics, NetworkDiagnosticReport};

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum AppLifecycleState {
    Starting,
    Ready,
    Visible,
    HiddenToTray,
    Restoring,
    ShuttingDown,
    Exited,
}

impl Default for AppLifecycleState {
    fn default() -> Self {
        AppLifecycleState::Starting
    }
}

#[derive(Clone, Default)]
pub struct SupervisorState {
    pub backend_child: Arc<Mutex<Option<Child>>>,
    pub backend_pid: Arc<Mutex<Option<u32>>>,
    pub is_managed: Arc<Mutex<bool>>,
    pub is_spawning: Arc<Mutex<bool>>,
    pub spawn_attempts: Arc<Mutex<u32>>,
    pub is_permanently_failed: Arc<Mutex<bool>>,
    pub lifecycle_state: Arc<Mutex<AppLifecycleState>>,
}

#[cfg(target_os = "windows")]
pub struct SingleInstanceGuard {
    handle: isize,
}

#[cfg(target_os = "windows")]
impl SingleInstanceGuard {
    pub fn acquire(name: &str) -> Option<Self> {
        use std::ffi::OsStr;
        use std::os::windows::ffi::OsStrExt;

        extern "system" {
            fn CreateMutexW(lpMutexAttributes: *mut std::ffi::c_void, bInitialOwner: i32, lpName: *const u16) -> isize;
            fn GetLastError() -> u32;
            fn CloseHandle(hObject: isize) -> i32;
            fn FindWindowW(lpClassName: *const u16, lpWindowName: *const u16) -> isize;
            fn SetForegroundWindow(hWnd: isize) -> i32;
            fn ShowWindow(hWnd: isize, nCmdShow: i32) -> i32;
        }

        const ERROR_ALREADY_EXISTS: u32 = 183;
        const SW_SHOW: i32 = 5;
        const SW_RESTORE: i32 = 9;

        startup_log("SINGLE_INSTANCE", &format!("Acquiring mutex: {}", name));
        let wide_name: Vec<u16> = OsStr::new(name).encode_wide().chain(std::iter::once(0)).collect();
        let handle = unsafe { CreateMutexW(std::ptr::null_mut(), 1, wide_name.as_ptr()) };
        let last_err = unsafe { GetLastError() };
        startup_log("SINGLE_INSTANCE", &format!("CreateMutexW returned handle=0x{:X}, GetLastError={}", handle, last_err));

        if handle == 0 {
            startup_log("SINGLE_INSTANCE", "CreateMutexW returned NULL handle!");
            return None;
        }

        if last_err == ERROR_ALREADY_EXISTS {
            startup_log("SINGLE_INSTANCE", "ERROR_ALREADY_EXISTS: existing instance detected!");
            println!("[INSTANCE] Boshqa Misa AI nusxasi allaqachon faol (Single Instance Lock).");
            let titles = ["MISA AI v9.3", "MISA AI v9.2", "Misa AI", "MISA AI", "MISA AI v9.0.2"];
            let mut hwnd = 0;
            for t in &titles {
                let win_title: Vec<u16> = OsStr::new(t).encode_wide().chain(std::iter::once(0)).collect();
                let found = unsafe { FindWindowW(std::ptr::null(), win_title.as_ptr()) };
                if found != 0 {
                    hwnd = found;
                    startup_log("SINGLE_INSTANCE", &format!("FindWindowW('{}') returned HWND=0x{:X}", t, hwnd));
                    break;
                }
            }
            if hwnd != 0 {
                unsafe {
                    ShowWindow(hwnd, SW_SHOW);
                    ShowWindow(hwnd, SW_RESTORE);
                    SetForegroundWindow(hwnd);
                }
            }
            unsafe { CloseHandle(handle); }
            return None;
        }

        startup_log("SINGLE_INSTANCE", "SingleInstanceGuard acquired successfully (Primary instance) ✓");
        Some(SingleInstanceGuard { handle })
    }
}

#[cfg(target_os = "windows")]
impl Drop for SingleInstanceGuard {
    fn drop(&mut self) {
        if self.handle != 0 {
            extern "system" {
                fn CloseHandle(hObject: isize) -> i32;
            }
            unsafe { CloseHandle(self.handle); }
        }
    }
}

#[cfg(not(target_os = "windows"))]
pub struct SingleInstanceGuard;
#[cfg(not(target_os = "windows"))]
impl SingleInstanceGuard {
    pub fn acquire(_name: &str) -> Option<Self> {
        Some(SingleInstanceGuard)
    }
}

#[derive(Debug, Clone)]
pub struct BackendHandshake {
    pub is_healthy: bool,
    pub is_compatible_version: bool,
    pub version: String,
    pub app: String,
}

/// HTTP GET /api/health orqali versiya, build provenance va sog'lomlikni tekshirish
pub fn check_backend_handshake(addr_str: &str, expected_version: &str) -> BackendHandshake {
    let mut result = BackendHandshake {
        is_healthy: false,
        is_compatible_version: false,
        version: String::new(),
        app: String::new(),
    };

    let addr: std::net::SocketAddr = match addr_str.parse() {
        Ok(a) => a,
        Err(_) => return result,
    };
    let mut stream = match TcpStream::connect_timeout(&addr, Duration::from_millis(1000)) {
        Ok(s) => s,
        Err(_) => return result,
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(2000)));
    let _ = stream.set_write_timeout(Some(Duration::from_millis(2000)));

    let request = format!(
        "GET /api/health HTTP/1.1\r\nHost: {}\r\nUser-Agent: MisaDesktopSupervisor/9.3.0\r\nConnection: close\r\n\r\n",
        addr_str
    );
    if stream.write_all(request.as_bytes()).is_err() {
        return result;
    }

    let mut buf = [0u8; 4096];
    if let Ok(n) = stream.read(&mut buf) {
        if n > 0 {
            let response = String::from_utf8_lossy(&buf[..n]);
            if response.contains("200 OK") && (response.contains("\"status\"") || response.contains("Misa AI")) {
                result.is_healthy = true;

                // "version": "..." ni ajratib olish
                if let Some(v_idx) = response.find("\"version\"") {
                    let rest = &response[v_idx..];
                    if let Some(colon_idx) = rest.find(':') {
                        let after_colon = rest[colon_idx + 1..].trim_start();
                        if after_colon.starts_with('"') {
                            if let Some(end_quote) = after_colon[1..].find('"') {
                                result.version = after_colon[1..1 + end_quote].to_string();
                            }
                        }
                    }
                }

                // "app": "..." ni ajratib olish
                if let Some(a_idx) = response.find("\"app\"") {
                    let rest = &response[a_idx..];
                    if let Some(colon_idx) = rest.find(':') {
                        let after_colon = rest[colon_idx + 1..].trim_start();
                        if after_colon.starts_with('"') {
                            if let Some(end_quote) = after_colon[1..].find('"') {
                                result.app = after_colon[1..1 + end_quote].to_string();
                            }
                        }
                    }
                }

                // Moslik tekshiruvi: 9.x seriyasi yoki aniq moslik
                if !expected_version.is_empty() && !result.version.is_empty() {
                    let major_prefix = if let Some(dot_idx) = expected_version.find('.') {
                        &expected_version[..=dot_idx]
                    } else {
                        "9."
                    };
                    if result.version == expected_version || result.version.starts_with(major_prefix) {
                        result.is_compatible_version = true;
                    }
                } else if result.is_healthy {
                    result.is_compatible_version = true;
                }
            }
        }
    }

    result
}

/// HTTP GET /api/health tekshiruvi (Pure Rust stdlib)
pub fn check_http_health(addr_str: &str, _path: &str) -> bool {
    check_backend_handshake(addr_str, "9.3.0").is_healthy
}

pub fn stop_backend(state: &SupervisorState) {
    println!("[SHUTDOWN] Backend jarayonini to'xtatish va tozalash...");
    let is_managed = state.is_managed.lock().map(|m| *m).unwrap_or(false);

    if let Ok(mut lock) = state.backend_child.lock() {
        if let Some(mut child) = lock.take() {
            let pid = child.id();
            println!("[BACKEND] Managed backend jarayoni to'xtatilmoqda (PID: {})...", pid);
            #[cfg(target_os = "windows")]
            {
                const CREATE_NO_WINDOW: u32 = 0x08000000;
                let _ = Command::new("taskkill")
                    .args(["/F", "/T", "/PID", &pid.to_string()])
                    .creation_flags(CREATE_NO_WINDOW)
                    .status();
            }
            let _ = child.kill();
            let _ = child.wait();
            println!("[BACKEND] Backend jarayoni muvaffaqiyatli to'xtatildi (PID: {}) ✓", pid);
        }
    }
    if let Ok(mut pid_lock) = state.backend_pid.lock() {
        *pid_lock = None;
    }
    if let Ok(mut managed_lock) = state.is_managed.lock() {
        *managed_lock = false;
    }

    if is_managed {
        // Managed backend to'xtatilgandan keyin portni tozalash
        cleanup_port_process(18420);
        println!("[SHUTDOWN] 18420-port tekshirildi va tozalandi ✓");
    } else {
        println!("[BACKEND] Backend tashqi/mavjud mustaqil jarayon bo'lgani uchun majburan o'ldirilmadi (Unmanaged)");
    }
}

/// Standalone yig'ilgan backend binarisini qidirish
fn find_bundled_backend_binary() -> Option<(PathBuf, PathBuf)> {
    let mut candidates: Vec<(PathBuf, PathBuf)> = Vec::new();

    // 1. Joriy ishga tushgan exe yonidagi backend papkasi
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(exe_dir) = exe_path.parent() {
            // exe_dir\backend\misa_backend.exe
            candidates.push((exe_dir.join("backend").join("misa_backend.exe"), exe_dir.join("backend")));
            // exe_dir\misa_backend.exe
            candidates.push((exe_dir.join("misa_backend.exe"), exe_dir.to_path_buf()));
            // exe_dir\resources\backend\misa_backend.exe (Tauri resources)
            candidates.push((exe_dir.join("resources").join("backend").join("misa_backend.exe"), exe_dir.join("resources").join("backend")));
            candidates.push((exe_dir.join("resources").join("misa_backend.exe"), exe_dir.join("resources")));
        }
    }

    // 2. Joriy ishchi katalog
    if let Ok(cwd) = std::env::current_dir() {
        candidates.push((cwd.join("backend").join("misa_backend.exe"), cwd.join("backend")));
        candidates.push((cwd.join("release").join("v9.2").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.2").join("backend")));
        candidates.push((cwd.join("release").join("v9.0.2").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.0.2").join("backend")));
        candidates.push((cwd.join("release").join("v9.0.1").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.0.1").join("backend")));
        candidates.push((cwd.join("release").join("v9.0.0").join("backend").join("misa_backend.exe"), cwd.join("release").join("v9.0.0").join("backend")));
        candidates.push((cwd.join("release").join("v8.0.0").join("backend").join("misa_backend.exe"), cwd.join("release").join("v8.0.0").join("backend")));
        candidates.push((cwd.join("Misa").join("src-tauri").join("backend").join("misa_backend.exe"), cwd.join("Misa").join("src-tauri").join("backend")));
        candidates.push((cwd.join("mikasa-7").join("src-tauri").join("backend").join("misa_backend.exe"), cwd.join("mikasa-7").join("src-tauri").join("backend")));
    }

    // 3. LocalAppData runtime katalogi (%LOCALAPPDATA%\MisaAI\...)
    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        let p = PathBuf::from(local_app_data);
        candidates.push((p.join("MisaAI").join("runtime").join("v9.2").join("backend").join("misa_backend.exe"), p.join("MisaAI").join("runtime").join("v9.2").join("backend")));
        candidates.push((p.join("MisaAI").join("runtime").join("v9.0.2").join("backend").join("misa_backend.exe"), p.join("MisaAI").join("runtime").join("v9.0.2").join("backend")));
        candidates.push((p.join("MisaAI").join("runtime").join("v9.0.1").join("backend").join("misa_backend.exe"), p.join("MisaAI").join("runtime").join("v9.0.1").join("backend")));
        candidates.push((p.join("MisaAI").join("runtime").join("v9.0.0").join("backend").join("misa_backend.exe"), p.join("MisaAI").join("runtime").join("v9.0.0").join("backend")));
        candidates.push((p.join("MisaAI").join("backend").join("misa_backend.exe"), p.join("MisaAI").join("backend")));
        candidates.push((p.join("MisaAI").join("runtime").join("v8.0.0").join("backend").join("misa_backend.exe"), p.join("MisaAI").join("runtime").join("v8.0.0").join("backend")));
    }

    // 4. Dinamik reliz katalogi tekshiruvi (har qanday disk va papka uchun portativ)
    if let Ok(exe_path) = std::env::current_exe() {
        let mut curr = exe_path.as_path();
        while let Some(parent) = curr.parent() {
            let rel92 = parent.join("release").join("v9.2").join("backend");
            if rel92.exists() {
                candidates.push((rel92.join("misa_backend.exe"), rel92));
            }
            let rel902 = parent.join("release").join("v9.0.2").join("backend");
            if rel902.exists() {
                candidates.push((rel902.join("misa_backend.exe"), rel902));
            }
            let rel91 = parent.join("release").join("v9.0.1").join("backend");
            if rel91.exists() {
                candidates.push((rel91.join("misa_backend.exe"), rel91));
            }
            let rel9 = parent.join("release").join("v9.0.0").join("backend");
            if rel9.exists() {
                candidates.push((rel9.join("misa_backend.exe"), rel9));
            }
            let rel8 = parent.join("release").join("v8.0.0").join("backend");
            if rel8.exists() {
                candidates.push((rel8.join("misa_backend.exe"), rel8));
            }
            curr = parent;
        }
    }

    for (exe, work_dir) in candidates {
        if exe.exists() && work_dir.join("_internal").join("python311.dll").exists() {
            return Some((exe, work_dir));
        }
    }

    None
}

/// Rivojlantirish (dev) muhiti uchun loyiha katalogini aniqlash
fn resolve_dev_base_dir() -> Option<PathBuf> {
    if let Ok(exe_path) = std::env::current_exe() {
        let mut curr = exe_path.as_path();
        while let Some(parent) = curr.parent() {
            if parent.join("core").join("api_server.py").exists() {
                return Some(parent.to_path_buf());
            }
            if parent.join("yordamchi_9.0.0").join("core").join("api_server.py").exists() {
                return Some(parent.join("yordamchi_9.0.0"));
            }
            if parent.join("yordamchi_8.0.0").join("core").join("api_server.py").exists() {
                return Some(parent.join("yordamchi_8.0.0"));
            }
            curr = parent;
        }
    }

    if let Ok(cwd) = std::env::current_dir() {
        if cwd.join("core").join("api_server.py").exists() {
            return Some(cwd);
        }
        if cwd.join("yordamchi_9.0.0").join("core").join("api_server.py").exists() {
            return Some(cwd.join("yordamchi_9.0.0"));
        }
        if cwd.join("yordamchi_8.0.0").join("core").join("api_server.py").exists() {
            return Some(cwd.join("yordamchi_8.0.0"));
        }
        let mut curr = cwd.as_path();
        while let Some(parent) = curr.parent() {
            if parent.join("core").join("api_server.py").exists() {
                return Some(parent.to_path_buf());
            }
            if parent.join("yordamchi_9.0.0").join("core").join("api_server.py").exists() {
                return Some(parent.join("yordamchi_9.0.0"));
            }
            if parent.join("yordamchi_8.0.0").join("core").join("api_server.py").exists() {
                return Some(parent.join("yordamchi_8.0.0"));
            }
            curr = parent;
        }
    }

    None
}

/// Rivojlantirish muhitidagi python.exe ni aniqlash
fn find_dev_python_executable(base_dir: &PathBuf) -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    candidates.push(base_dir.join(".venv").join("Scripts").join("python.exe"));
    candidates.push(base_dir.join("python").join("python.exe"));
    candidates.push(base_dir.join("runtime").join("python.exe"));

    if let Some(p1) = base_dir.parent() {
        candidates.push(p1.join(".venv").join("Scripts").join("python.exe"));
        if let Some(p2) = p1.parent() {
            candidates.push(p2.join(".venv").join("Scripts").join("python.exe"));
        }
    }

    for py in candidates {
        if py.exists() {
            return Some(py);
        }
    }
    None
}

fn is_port_listening(port: u16) -> bool {
    let addr = std::net::SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok()
}

#[cfg(target_os = "windows")]
fn cleanup_port_process(port: u16) {
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    let cmd_str = format!(
        "$p = (Get-NetTCPConnection -LocalPort {} -State Listen -ErrorAction SilentlyContinue).OwningProcess; if ($p) {{ Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }}",
        port
    );
    let _ = Command::new("powershell")
        .args(["-NoProfile", "-NonInteractive", "-Command", &cmd_str])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
}

#[cfg(not(target_os = "windows"))]
fn cleanup_port_process(_port: u16) {}

pub fn ensure_backend_running(state: &SupervisorState) {
    backend_lifecycle_log("HEALTH_CHECK", "Backend holati tekshirilmoqda (127.0.0.1:18420)...");
    println!("[BACKEND] Backend holati tekshirilmoqda (127.0.0.1:18420)...");

    // 1. Agar 127.0.0.1:18420 da backend allaqachon ishlab turgan bo'lsa va versiyasi mos bo'lsa
    let initial_hs = check_backend_handshake("127.0.0.1:18420", "9.3.0");
    if initial_hs.is_healthy && initial_hs.is_compatible_version {
        backend_lifecycle_log("HEALTH_OK", &format!("Mavjud backend aniqlandi va mos (127.0.0.1:18420, v{}) — yangi jarayon ochilmaydi ✓", initial_hs.version));
        println!("[BACKEND] Mavjud backend aniqlandi va mos (127.0.0.1:18420, v{}) — yangi jarayon ochilmaydi ✓", initial_hs.version);
        if let Ok(mut m) = state.is_managed.lock() {
            *m = false;
        }
        if let Ok(mut a) = state.spawn_attempts.lock() {
            *a = 0;
        }
        if let Ok(mut f) = state.is_permanently_failed.lock() {
            *f = false;
        }
        return;
    } else if initial_hs.is_healthy && !initial_hs.is_compatible_version {
        backend_lifecycle_log("VERSION_MISMATCH", &format!("18420-portdagi mavjud backend versiyasi mos emas: '{}' (kutilgan: 9.3.0). Jarayon xavfsiz to'xtatilib, yangilanadi...", initial_hs.version));
        println!("[BACKEND] 18420-portdagi mavjud backend versiyasi mos emas: '{}' (kutilgan: 9.3.0). Jarayon to'xtatilib yangilanadi...", initial_hs.version);
        cleanup_port_process(18420);
        std::thread::sleep(Duration::from_millis(500));
    }

    // 2. Barqaror xatolik va cheksiz qayta urinishdan himoya
    if let Ok(mut attempts) = state.spawn_attempts.lock() {
        if *attempts >= 5 {
            backend_lifecycle_log("MAX_ATTEMPTS_REACHED", "Backend ishga tushirish uchun maksimal 5 ta urinish tugadi.");
            println!("[ERROR] Backend ishga tushirish uchun maksimal 5 ta urinish tugadi. Avtomatik qayta urinish to'xtatildi.");
            if let Ok(mut f) = state.is_permanently_failed.lock() {
                *f = true;
            }
            return;
        }
        *attempts += 1;
        backend_lifecycle_log("SPAWN_ATTEMPT", &format!("Backend ishga tushirish urinishi: {}/5", *attempts));
        println!("[BACKEND] Backend ishga tushirish urinishi: {}/5", *attempts);
    }

    // 3. Concurrency guard (bir vaqtda bir nechta spawn chaqirilmasligi uchun)
    if let Ok(mut spawning) = state.is_spawning.lock() {
        if *spawning {
            backend_lifecycle_log("CONCURRENCY_GUARD", "Backend allaqachon initsializatsiya jarayonida, kutilmoqda...");
            println!("[BACKEND] Backend allaqachon initsializatsiya jarayonida, kutilmoqda...");
            return;
        }
        *spawning = true;
    }

    // 4. Stale yoki versiyasi mos kelmagan port jarayonini xavfsiz tekshirish
    if is_port_listening(18420) {
        let mut port_healthy = false;
        let mut port_compatible = false;
        for _ in 0..3 {
            std::thread::sleep(Duration::from_millis(400));
            let hs = check_backend_handshake("127.0.0.1:18420", "9.3.0");
            if hs.is_healthy {
                port_healthy = true;
                port_compatible = hs.is_compatible_version;
                break;
            }
        }
        if port_healthy && port_compatible {
            backend_lifecycle_log("PORT_HEALTH_CONFIRMED", "18420-portdagi mavjud jarayon qayta tekshiruvda sog'lom va versiyasi mos deb tasdiqlandi ✓");
            if let Ok(mut a) = state.spawn_attempts.lock() { *a = 0; }
            if let Ok(mut f) = state.is_permanently_failed.lock() { *f = false; }
            if let Ok(mut spawning) = state.is_spawning.lock() { *spawning = false; }
            return;
        }
        backend_lifecycle_log("PORT_CLEANUP", "18420-port band, ammo /api/health javob bermayapti yoki versiyasi mos emas (Stale process). Tozalanmoqda...");
        println!("[BACKEND] 18420-port band, ammo /api/health javob bermayapti yoki versiyasi mos emas (Stale process). Tozalanmoqda...");
        cleanup_port_process(18420);
        std::thread::sleep(Duration::from_millis(400));
    }

    #[cfg(target_os = "windows")]
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    #[cfg(target_os = "windows")]
    const CREATE_NEW_PROCESS_GROUP: u32 = 0x00000200;
    #[cfg(target_os = "windows")]
    let creation_flags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP;

    let mut child_opt: Option<Child> = None;

    // 5. Variant A: Standalone bundled backend (misa_backend.exe)
    if let Some((backend_bin, work_dir)) = find_bundled_backend_binary() {
        println!("[BACKEND] Standalone bundled backend ishga tushirilmoqda: {:?}", backend_bin);
        let sup_url = std::env::var("SUPABASE_URL")
            .unwrap_or_else(|_| "https://vdcssmzguxfknqkfxbed.supabase.co".to_string());
        let sup_key = std::env::var("SUPABASE_PUBLISHABLE_KEY")
            .or_else(|_| std::env::var("SUPABASE_ANON_KEY"))
            .unwrap_or_else(|_| "sb_publishable_Mwowz4aOLM4njc3OyX7VNQ_GxpxuTr8".to_string());

        let mut cmd = Command::new(&backend_bin);
        cmd.current_dir(&work_dir)
            .env("MISA_API_HOST", "127.0.0.1")
            .env("MISA_API_PORT", "18420")
            .env("PORT", "18420")
            .env("ENVIRONMENT", "desktop")
            .env("SUPABASE_URL", &sup_url)
            .env("SUPABASE_ANON_KEY", &sup_key)
            .env("SUPABASE_PUBLISHABLE_KEY", &sup_key);

        #[cfg(target_os = "windows")]
        cmd.creation_flags(creation_flags);

        match cmd.spawn() {
            Ok(c) => child_opt = Some(c),
            Err(e) => println!("[ERROR] Bundled backendni ishga tushirishda xatolik: {}", e),
        }
    }

    // 6. Variant B: Rivojlantirish muhiti orqali python fallback (faqat dev muhitda mavjud bo'lsa)
    if child_opt.is_none() {
        if let Some(base_dir) = resolve_dev_base_dir() {
            let py_exe = find_dev_python_executable(&base_dir).unwrap_or_else(|| PathBuf::from("python"));
            println!("[BACKEND] Python fallback orqali ishga tushirilmoqda: {:?} core/api_server.py", py_exe);
            let mut cmd = Command::new(&py_exe);
            cmd.arg("core/api_server.py")
                .current_dir(&base_dir)
                .env("MISA_API_HOST", "127.0.0.1")
                .env("MISA_API_PORT", "18420")
                .env("PORT", "18420");

            #[cfg(target_os = "windows")]
            cmd.creation_flags(creation_flags);

            match cmd.spawn() {
                Ok(c) => child_opt = Some(c),
                Err(e) => println!("[ERROR] Python orqali ishga tushirishda xatolik: {}", e),
            }
        }
    }

    // 7. Jarayon qayd etildi
    if let Some(child) = child_opt {
        let pid = child.id();
        println!("[BACKEND] Backend jarayoni boshlandi (PID: {})", pid);
        if let Ok(mut lock) = state.backend_child.lock() {
            *lock = Some(child);
        }
        if let Ok(mut pid_lock) = state.backend_pid.lock() {
            *pid_lock = Some(pid);
        }
        if let Ok(mut managed_lock) = state.is_managed.lock() {
            *managed_lock = true;
        }
    } else {
        println!("[ERROR] Hech qanday backend ijrochi fayli topilmadi!");
        if let Ok(mut spawning) = state.is_spawning.lock() {
            *spawning = false;
        }
        return;
    }

    // 8. Eksponentsial kutish bilan /api/health tekshiruvi (Health check with backoff)
    println!("[BACKEND] /api/health tayyor bo'lishi kutilmoqda...");
    let backoff_delays = [100, 250, 500, 1000, 1500, 2000, 2000, 2000, 2000, 2000];
    let mut is_ready = false;

    for delay in backoff_delays {
        // Jarayon barvaqt to'xtab qolmaganini tekshirish
        if let Ok(mut lock) = state.backend_child.lock() {
            if let Some(ref mut child) = *lock {
                if let Ok(Some(status)) = child.try_wait() {
                    println!("[ERROR] Backend jarayoni kutilmaganda to'xtadi: {:?}", status);
                    break;
                }
            } else {
                break;
            }
        }

        if check_http_health("127.0.0.1:18420", "/api/health") {
            is_ready = true;
            break;
        }
        std::thread::sleep(Duration::from_millis(delay));
    }

    if is_ready {
        backend_lifecycle_log("BACKEND_READY", "Backend 127.0.0.1:18420 da muvaffaqiyatli tayyor bo'ldi (READY) ✓");
        println!("[BACKEND] Backend 127.0.0.1:18420 da muvaffaqiyatli tayyor bo'ldi (READY) ✓");
        if let Ok(mut a) = state.spawn_attempts.lock() {
            *a = 0;
        }
        if let Ok(mut f) = state.is_permanently_failed.lock() {
            *f = false;
        }
    } else {
        backend_lifecycle_log("BACKEND_TIMEOUT", "Backend health check vaqt chegarasiga yetdi (Timeout)");
        println!("[ERROR] Backend health check vaqt chegarasiga yetdi (Timeout)");
    }

    if let Ok(mut spawning) = state.is_spawning.lock() {
        *spawning = false;
    }
}

// ========== Tauri Buyruqlari (IPC Commands) ==========

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn app_minimize(window: tauri::Window) -> Result<(), String> {
    window.minimize().map_err(|e| e.to_string())
}

#[tauri::command]
fn app_toggle_maximize(window: tauri::Window) -> Result<bool, String> {
    let is_max = window.is_maximized().map_err(|e| e.to_string())?;
    if is_max {
        window.unmaximize().map_err(|e| e.to_string())?;
        Ok(false)
    } else {
        window.maximize().map_err(|e| e.to_string())?;
        Ok(true)
    }
}

#[tauri::command]
fn app_open_external_url(url: String) -> Result<(), String> {
    startup_log("OPENER", &format!("Opening external URL via native OS shell: {}", url));
    #[cfg(target_os = "windows")]
    {
        use std::ffi::OsStr;
        use std::os::windows::ffi::OsStrExt;
        extern "system" {
            fn ShellExecuteW(
                hwnd: isize,
                lpOperation: *const u16,
                lpFile: *const u16,
                lpParameters: *const u16,
                lpDirectory: *const u16,
                nShowCmd: i32,
            ) -> isize;
        }
        let op: Vec<u16> = OsStr::new("open").encode_wide().chain(std::iter::once(0)).collect();
        let target: Vec<u16> = OsStr::new(&url).encode_wide().chain(std::iter::once(0)).collect();
        let res = unsafe {
            ShellExecuteW(0, op.as_ptr(), target.as_ptr(), std::ptr::null(), std::ptr::null(), 1)
        };
        if res <= 32 {
            return Err(format!("ShellExecuteW failed with code {}", res));
        }
        Ok(())
    }
    #[cfg(not(target_os = "windows"))]
    {
        std::process::Command::new("xdg-open")
            .arg(&url)
            .spawn()
            .map(|_| ())
            .map_err(|e| e.to_string())
    }
}

#[tauri::command]
fn app_focus_window(window: tauri::Window) -> Result<(), String> {
    let _ = window.show();
    let _ = window.unminimize();
    let _ = window.set_focus();
    #[cfg(target_os = "windows")]
    {
        extern "system" {
            fn SetForegroundWindow(hWnd: isize) -> i32;
            fn ShowWindow(hWnd: isize, nCmdShow: i32) -> i32;
        }
        if let Ok(hwnd) = window.hwnd() {
            unsafe {
                ShowWindow(hwnd.0 as isize, 9); // SW_RESTORE
                SetForegroundWindow(hwnd.0 as isize);
            }
        }
    }
    Ok(())
}

#[tauri::command]
fn app_close(window: tauri::Window, state: tauri::State<SupervisorState>) -> Result<(), String> {
    startup_log("UI", "app_close invoked -> Hiding window to system tray (Idempotent)");
    let mut lc = state.lifecycle_state.lock().map_err(|e| e.to_string())?;
    if *lc == AppLifecycleState::HiddenToTray {
        startup_log("UI", "Window is already in HiddenToTray state, ignoring duplicate call.");
        return Ok(());
    }
    *lc = AppLifecycleState::HiddenToTray;
    drop(lc);
    window.hide().map_err(|e| e.to_string())
}

#[tauri::command]
fn app_exit(app_handle: tauri::AppHandle, state: tauri::State<SupervisorState>) -> Result<(), String> {
    startup_log("UI", "app_exit invoked -> Stopping backend and exiting application...");
    let mut lc = state.lifecycle_state.lock().map_err(|e| e.to_string())?;
    if *lc == AppLifecycleState::ShuttingDown || *lc == AppLifecycleState::Exited {
        return Ok(());
    }
    *lc = AppLifecycleState::ShuttingDown;
    drop(lc);
    stop_backend(&state);
    app_handle.exit(0);
    Ok(())
}

#[tauri::command]
fn app_show_from_tray(window: tauri::Window, state: tauri::State<SupervisorState>) -> Result<(), String> {
    backend_lifecycle_log("APP_SHOW_FROM_TRAY", "Window restored from tray, verifying state...");
    let mut lc = state.lifecycle_state.lock().map_err(|e| e.to_string())?;
    *lc = AppLifecycleState::Visible;
    drop(lc);
    window.show().map_err(|e| e.to_string())?;
    window.unminimize().map_err(|e| e.to_string())?;
    let _ = window.set_focus();

    // Reopen paytida backend holatini tekshirish va kutilmaganda to'xtagan bo'lsa darhol jonlantirish
    if !check_http_health("127.0.0.1:18420", "/api/health") {
        backend_lifecycle_log("TRAY_REOPEN_REVIVE", "Backend faol emas, traydan ochilganda qayta ishga tushirilmoqda...");
        if let Ok(mut a) = state.spawn_attempts.lock() { *a = 0; }
        if let Ok(mut f) = state.is_permanently_failed.lock() { *f = false; }
        let state_clone = state.inner().clone();
        std::thread::spawn(move || {
            ensure_backend_running(&state_clone);
        });
    }

    Ok(())
}

#[tauri::command]
fn app_get_lifecycle_state(state: tauri::State<SupervisorState>) -> String {
    let lc = state.lifecycle_state.lock().map(|s| *s).unwrap_or(AppLifecycleState::Starting);
    format!("{:?}", lc)
}

#[tauri::command]
fn app_is_maximized(window: tauri::Window) -> Result<bool, String> {
    window.is_maximized().map_err(|e| e.to_string())
}

#[tauri::command]
fn app_start_resize(window: tauri::Window, direction: String) -> Result<(), String> {
    let canonical = match direction.as_str() {
        "North" | "N" => "North",
        "South" | "S" => "South",
        "East" | "E" => "East",
        "West" | "W" => "West",
        "NorthEast" | "NE" => "NorthEast",
        "NorthWest" | "NW" => "NorthWest",
        "SouthEast" | "SE" => "SouthEast",
        "SouthWest" | "SW" => "SouthWest",
        _ => return Err(format!("Invalid resize direction: {}", direction)),
    };
    let dir = serde_json::from_value(serde_json::Value::String(canonical.to_string()))
        .map_err(|e| e.to_string())?;
    window.start_resize_dragging(dir).map_err(|e| e.to_string())
}

#[tauri::command]
fn backend_get_status(state: tauri::State<SupervisorState>) -> serde_json::Value {
    if let Ok(mut lock) = state.backend_child.lock() {
        if let Some(ref mut child) = *lock {
            if let Ok(Some(_exit_status)) = child.try_wait() {
                backend_lifecycle_log("CHILD_EXITED", &format!("Backend child jarayoni yakunlandi: {:?}", _exit_status));
                *lock = None;
                if let Ok(mut pid_lock) = state.backend_pid.lock() {
                    *pid_lock = None;
                }
                if let Ok(mut managed_lock) = state.is_managed.lock() {
                    *managed_lock = false;
                }
            }
        }
    }

    let is_healthy = check_http_health("127.0.0.1:18420", "/api/health");
    let is_spawning = state.is_spawning.lock().map(|s| *s).unwrap_or(false);
    let permanently_failed = state.is_permanently_failed.lock().map(|f| *f).unwrap_or(false);
    let attempts = state.spawn_attempts.lock().map(|a| *a).unwrap_or(0);

    // Qayta urinish faqat limit doirasida va barqaror xato holatida bo'lmasa
    if !is_healthy && !is_spawning && attempts < 5 {
        backend_lifecycle_log("AUTO_RECOVERY", &format!("Backend sog'lom emas, auto-recovery chaqirilmoqda (urinish: {}/5)", attempts));
        let state_clone = state.inner().clone();
        std::thread::spawn(move || {
            ensure_backend_running(&state_clone);
        });
    }

    let is_managed = state.is_managed.lock().map(|m| *m).unwrap_or(false);
    let pid = state.backend_pid.lock().ok().and_then(|p| *p);

    serde_json::json!({
        "running": is_healthy,
        "healthy": is_healthy,
        "spawning": is_spawning || (!is_healthy && !permanently_failed),
        "port": 18420,
        "pid": pid,
        "managed": is_managed,
        "permanently_failed": permanently_failed,
        "attempts": attempts
    })
}

#[tauri::command]
fn backend_restart(state: tauri::State<SupervisorState>) -> Result<bool, String> {
    backend_lifecycle_log("MANUAL_RESTART", "Foydalanuvchi/Frontend orqali backend_restart chaqirildi");
    let currently_spawning = state.is_spawning.lock().map(|s| *s).unwrap_or(false);
    if currently_spawning || check_http_health("127.0.0.1:18420", "/api/health") {
        return Ok(true);
    }
    stop_backend(&state);
    if let Ok(mut spawning) = state.is_spawning.lock() {
        *spawning = false;
    }
    if let Ok(mut attempts) = state.spawn_attempts.lock() {
        *attempts = 0;
    }
    if let Ok(mut f) = state.is_permanently_failed.lock() {
        *f = false;
    }
    std::thread::sleep(Duration::from_millis(300));
    let state_clone = state.inner().clone();
    std::thread::spawn(move || {
        ensure_backend_running(&state_clone);
    });
    Ok(true)
}

#[tauri::command]
fn get_backend_lifecycle_log_path() -> Result<String, String> {
    let log_file = crate::diag::get_log_dir().join("backend-lifecycle.log");
    Ok(log_file.to_string_lossy().to_string())
}

#[tauri::command]
fn get_voice_runtime_log_path() -> Result<String, String> {
    let log_file = crate::diag::get_log_dir().join("voice-runtime.log");
    Ok(log_file.to_string_lossy().to_string())
}

#[tauri::command]
fn network_diagnostic_check(url: Option<String>) -> Result<crate::network_diag::NetworkDiagnosticReport, String> {
    let target = url.unwrap_or_else(|| "https://misa.up.railway.app/api/health".to_string());
    Ok(crate::network_diag::run_full_diagnostics(&target))
}

#[tauri::command]
fn get_network_log_path() -> Result<String, String> {
    let log_file = crate::diag::get_log_dir().join("network.log");
    Ok(log_file.to_string_lossy().to_string())
}

#[tauri::command]
fn append_network_log(message: String) -> Result<(), String> {
    crate::diag::network_log(&message);
    Ok(())
}

pub struct BackendGuard {
    pub state: SupervisorState,
}

impl Drop for BackendGuard {
    fn drop(&mut self) {
        stop_backend(&self.state);
    }
}

#[cfg(target_os = "windows")]
pub fn check_webview2_installed() -> bool {
    const CREATE_NO_WINDOW: u32 = 0x08000000;

    // 1. WEBVIEW2_BROWSER_EXECUTABLE_FOLDER muhit o'zgaruvchisi (Fixed Version / maxsus runtime)
    if let Ok(fixed_dir) = std::env::var("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER") {
        let p = PathBuf::from(&fixed_dir);
        if p.exists() && (p.join("msedgewebview2.exe").exists() || p.join("Application").exists()) {
            println!("[MISA] WebView2 Fixed Version muhit orqali aniqlandi: {:?}", p);
            return true;
        }
    }

    // 2. Mahalliy Fixed Version Runtime katalogini tekshirish (exe yonidagi offline runtime)
    let mut fixed_candidates: Vec<PathBuf> = Vec::new();
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            fixed_candidates.push(parent.join("webview2_runtime"));
            fixed_candidates.push(parent.join("webview2_fixed"));
            fixed_candidates.push(parent.join("FixedRuntime"));
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        fixed_candidates.push(cwd.join("webview2_runtime"));
        fixed_candidates.push(cwd.join("webview2_fixed"));
    }
    for fc in fixed_candidates {
        if fc.exists() {
            let direct_exe = fc.join("msedgewebview2.exe");
            if direct_exe.exists() {
                println!("[MISA] Mahalliy WebView2 Fixed Version aniqlandi: {:?}", fc);
                std::env::set_var("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", &fc);
                return true;
            }
            if let Ok(entries) = std::fs::read_dir(&fc) {
                for entry in entries.flatten() {
                    let sub = entry.path();
                    if sub.join("msedgewebview2.exe").exists() {
                        println!("[MISA] Mahalliy WebView2 Fixed Version aniqlandi: {:?}", sub);
                        std::env::set_var("WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", &sub);
                        return true;
                    }
                }
            }
        }
    }

    // 3. Windows Registry tekshiruvi (Evergreen Runtime x86, x64, HKCU, Policies)
    let reg_paths = [
        r"HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        r"HKLM\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        r"HKCU\Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        r"HKLM\SOFTWARE\Policies\Microsoft\Edge\WebView2",
        r"HKCU\Software\Policies\Microsoft\Edge\WebView2",
    ];

    for path in reg_paths {
        if let Ok(output) = Command::new("reg")
            .args(["query", path, "/v", "pv"])
            .creation_flags(CREATE_NO_WINDOW)
            .output()
        {
            if output.status.success() {
                let stdout = String::from_utf8_lossy(&output.stdout);
                for line in stdout.lines() {
                    if line.contains("pv") && !line.contains("0.0.0.0") {
                        let parts: Vec<&str> = line.split_whitespace().collect();
                        if let Some(ver) = parts.last() {
                            if *ver != "0.0.0.0" && ver.contains('.') {
                                println!("[MISA] WebView2 Runtime aniqlandi (Registry): {} ({})", ver, path);
                                return true;
                            }
                        }
                    }
                }
            }
        }
    }

    // 4. Jismoniy papkalar tekshiruvi (ProgramFiles x86, x64 va LOCALAPPDATA)
    let mut check_dirs: Vec<PathBuf> = Vec::new();
    if let Ok(prog_files_x86) = std::env::var("ProgramFiles(x86)") {
        check_dirs.push(PathBuf::from(prog_files_x86).join("Microsoft").join("EdgeWebView").join("Application"));
    }
    if let Ok(prog_files) = std::env::var("ProgramFiles") {
        check_dirs.push(PathBuf::from(prog_files).join("Microsoft").join("EdgeWebView").join("Application"));
    }
    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        check_dirs.push(PathBuf::from(local_app_data).join("Microsoft").join("EdgeWebView").join("Application"));
    }

    for wv_dir in check_dirs {
        if wv_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(&wv_dir) {
                for entry in entries.flatten() {
                    if entry.path().join("msedgewebview2.exe").exists() {
                        println!("[MISA] WebView2 Application binarisi aniqlandi: {:?}", entry.path());
                        return true;
                    }
                }
            }
        }
    }

    false
}

#[cfg(not(target_os = "windows"))]
pub fn check_webview2_installed() -> bool {
    true
}

#[cfg(target_os = "windows")]
pub fn try_install_webview2() -> bool {
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    println!("[MISA] WebView2 Runtime o'rnatish jarayoni boshlanmoqda...");

    let mut setup_cands: Vec<PathBuf> = Vec::new();

    // 1. Portable / Standalone EXE yonidagi kandidatlar
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            setup_cands.push(parent.join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
            setup_cands.push(parent.join("MicrosoftEdgeWebview2Setup.exe"));
            setup_cands.push(parent.join("resources").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
            setup_cands.push(parent.join("resources").join("MicrosoftEdgeWebview2Setup.exe"));
        }
    }

    // 2. Joriy ishchi katalogdagi kandidatlar (CWD)
    if let Ok(cwd) = std::env::current_dir() {
        setup_cands.push(cwd.join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.2").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.2").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.1").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.1").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("Misa").join("src-tauri").join("resources").join("MicrosoftEdgeWebview2Setup.exe"));
    }

    // 3. Vaqtinchalik katalogdagi kandidat
    let temp_setup = std::env::temp_dir().join("MicrosoftEdgeWebview2Setup.exe");
    setup_cands.push(temp_setup.clone());

    let mut found_setup: Option<PathBuf> = None;
    for cand in setup_cands {
        if cand.exists() {
            println!("[MISA] Mahalliy WebView2 Bootstrapper aniqlandi: {:?}", cand);
            found_setup = Some(cand);
            break;
        }
    }

    // 4. Agar mahalliy bootstrapper topilmasa, Microsoft rasmiy serveridan yuklab olish
    if found_setup.is_none() {
        println!("[MISA] Mahalliy bootstrapper topilmadi. Microsoft rasmiy serveridan yuklab olinmoqda...");
        let dl_cmd = format!(
            "Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile '{}' -TimeoutSec 30 -UseBasicParsing",
            temp_setup.display()
        );
        let dl_res = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &dl_cmd])
            .creation_flags(CREATE_NO_WINDOW)
            .status();

        if dl_res.map(|s| s.success()).unwrap_or(false) && temp_setup.exists() {
            println!("[MISA] MicrosoftEdgeWebview2Setup.exe yuklab olindi ✓");
            found_setup = Some(temp_setup);
        } else {
            eprintln!("[ERROR] WebView2 bootstrapper yuklab olinmadi (Internet aloqasi mavjud emas)!");
            return false;
        }
    }

    let setup_path = match found_setup {
        Some(p) => p,
        None => return false,
    };

    println!("[MISA] WebView2 Bootstrapper ishga tushirilmoqda: {:?}", setup_path);

    // 5. Bosqich A: Silent rejim (/silent /install) - 90 soniya timeout va process monitoring bilan
    let mut _silent_spawned = false;
    match Command::new(&setup_path)
        .args(["/silent", "/install"])
        .creation_flags(CREATE_NO_WINDOW)
        .spawn()
    {
        Ok(mut child) => {
            _silent_spawned = true;
            let start = std::time::Instant::now();
            let timeout = Duration::from_secs(90);
            while start.elapsed() < timeout {
                if let Ok(Some(st)) = child.try_wait() {
                    println!("[MISA] Silent bootstrapper jarayoni yakunlandi: {:?}", st);
                    break;
                }
                std::thread::sleep(Duration::from_millis(500));
            }
            if child.try_wait().ok().flatten().is_none() {
                println!("[MISA] Silent o'rnatish 90 soniyadan oshdi. Jarayon to'xtatilmoqda...");
                let _ = child.kill();
                let _ = child.wait();
            }
        }
        Err(e) => {
            println!("[ERROR] Silent bootstrapper ishga tushirishda xatolik: {}", e);
        }
    }

    // Registry yangilanishi uchun kutiladi
    std::thread::sleep(Duration::from_millis(1500));

    // Qayta tekshirish (Re-check)
    if check_webview2_installed() {
        println!("[MISA] Silent o'rnatish muvaffaqiyatli: WebView2 o'rnatildi va tasdiqlandi ✓");
        return true;
    }

    // 6. Bosqich B: Agar silent o'rnatish UAC talab qilsa, interaktiv rejimda ishga tushirish
    println!("[MISA] Silent rejim orqali o'rnatilmadi. Foydalanuvchi UAC ruxsati uchun interaktiv oyna ochilmoqda...");
    match Command::new(&setup_path)
        .args(["/install"])
        .spawn()
    {
        Ok(mut child) => {
            let start = std::time::Instant::now();
            let timeout = Duration::from_secs(120);
            while start.elapsed() < timeout {
                if let Ok(Some(st)) = child.try_wait() {
                    println!("[MISA] Interaktiv o'rnatuvchi yakunlandi: {:?}", st);
                    break;
                }
                std::thread::sleep(Duration::from_millis(500));
            }
            if child.try_wait().ok().flatten().is_none() {
                println!("[MISA] Interaktiv o'rnatuvchi 120 soniyadan oshdi. Jarayon to'xtatilmoqda...");
                let _ = child.kill();
                let _ = child.wait();
            }
        }
        Err(e) => {
            println!("[ERROR] Interaktiv bootstrapper ishga tushirishda xatolik: {}", e);
        }
    }

    // Registry yangilanishi uchun kutiladi
    std::thread::sleep(Duration::from_millis(1500));

    // Yakuniy qayta tekshiruv (Strict Re-check)
    let verified = check_webview2_installed();
    if verified {
        println!("[MISA] WebView2 Runtime muvaffaqiyatli o'rnatildi va qayta tekshiruvdan o'tdi ✓");
    } else {
        eprintln!("[ERROR] WebView2 o'rnatilmadi yoki jarayon bekor qilindi!");
    }
    verified
}

#[cfg(not(target_os = "windows"))]
pub fn try_install_webview2() -> bool {
    true
}

#[cfg(target_os = "windows")]
pub fn show_native_message_box(title: &str, message: &str, is_error: bool) {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;

    let wide_title: Vec<u16> = OsStr::new(title).encode_wide().chain(std::iter::once(0)).collect();
    let wide_msg: Vec<u16> = OsStr::new(message).encode_wide().chain(std::iter::once(0)).collect();

    extern "system" {
        fn MessageBoxW(hwnd: isize, text: *const u16, caption: *const u16, u_type: u32) -> i32;
    }

    const MB_OK: u32 = 0x00000000;
    const MB_ICONERROR: u32 = 0x00000010;
    const MB_ICONINFORMATION: u32 = 0x00000040;
    const MB_TOPMOST: u32 = 0x00040000;

    let flags = MB_OK | MB_TOPMOST | if is_error { MB_ICONERROR } else { MB_ICONINFORMATION };
    unsafe {
        MessageBoxW(0, wide_msg.as_ptr(), wide_title.as_ptr(), flags);
    }
}

#[cfg(target_os = "windows")]
fn register_custom_protocol() {
    if let Ok(current_exe) = std::env::current_exe() {
        let exe_str = current_exe.to_string_lossy().to_string();
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        let cmd = format!(
            "reg add \"HKCU\\Software\\Classes\\misa\" /ve /d \"URL:Misa Protocol\" /f >nul 2>&1 & reg add \"HKCU\\Software\\Classes\\misa\" /v \"URL Protocol\" /d \"\" /f >nul 2>&1 & reg add \"HKCU\\Software\\Classes\\misa\\shell\\open\\command\" /ve /d \"\\\"{}\\\" \\\"%1\\\"\" /f >nul 2>&1",
            exe_str
        );
        let _ = Command::new("cmd")
            .args(["/C", &cmd])
            .creation_flags(CREATE_NO_WINDOW)
            .status();
    }
}
#[cfg(not(target_os = "windows"))]
fn register_custom_protocol() {}

#[cfg(not(target_os = "windows"))]
pub fn show_native_message_box(_title: &str, _message: &str, _is_error: bool) {}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    install_crash_handlers();

    let exe_path = std::env::current_exe()
        .map(|p| p.display().to_string())
        .unwrap_or_else(|_| "unknown".to_string());
    startup_log("STARTUP", "Misa AI process started");
    startup_log("STARTUP", &format!("Executable path: {}", exe_path));
    startup_log("STARTUP", &format!("PID: {} TID: {}", current_pid(), current_tid()));
    println!("[BOOT] MISA AI v9.3.0 Desktop Application ishga tushmoqda...");
    register_custom_protocol();

    // 1. Single-Instance Guard tekshiruvi (faqat 1 ta Misa UI instansiyasi ishlaydi)
    startup_log("SINGLE_INSTANCE", "Checking single instance guard...");
    println!("[INSTANCE] Yagona nusxa (Single-Instance) tekshirilmoqda...");
    let _instance_guard = match SingleInstanceGuard::acquire("Local\\Misa_AI_SingleInstance_Mutex_v9.3") {
        Some(g) => {
            startup_log("SINGLE_INSTANCE", "Acquired mutex successfully (Primary instance)");
            println!("[INSTANCE] Yagona nusxa qulfi o'rnatildi (Primary instance) ✓");
            g
        }
        None => {
            startup_log("SINGLE_INSTANCE", "Existing instance detected! Exiting process cleanly.");
            println!("[INSTANCE] Mavjud Misa AI nusxasi topildi. Yangi jarayon to'xtatildi (No duplicate instance).");
            return;
        }
    };

    let supervisor_state = SupervisorState::default();

    // 2. Backend Guard o'rnatish: Jarayon har qanday holatda yopilganda backendni to'xtatadi
    let _guard = BackendGuard {
        state: supervisor_state.clone(),
    };

    // 3. Panic hook: Kutilmagan qulashlarda backend bolalar jarayonini o'ldirish
    let state_for_panic = supervisor_state.clone();
    let old_panic_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        let err_msg = format!("Panic: {:?}", info);
        crash_log("RUST_PANIC_SUPERVISOR", &err_msg);
        eprintln!("[ERROR] Kutilmagan qulash (Panic): {:?}", info);
        stop_backend(&state_for_panic);
        old_panic_hook(info);
    }));

    // 4. Windows Native Misa Preflight: WebView2 tekshiruvi va avtomatik o'rnatish
    #[cfg(target_os = "windows")]
    {
        startup_log("PREFLIGHT", "Entering run_native_preflight()...");
        println!("[PREFLIGHT] Misa Native Preflight tekshiruvi boshlanmoqda...");
        let preflight_ok = preflight::run_native_preflight();
        startup_log("PREFLIGHT", &format!("run_native_preflight returned: {}", preflight_ok));
        if !preflight_ok {
            startup_log("PREFLIGHT", "Preflight FAILED or aborted by user! Stopping backend and exiting.");
            eprintln!("[ERROR] Microsoft WebView2 Runtime o'rnatilmadi.");
            eprintln!("[INFO] UI startup aborted.");
            eprintln!("[INFO] Backend process was NOT started.");
            eprintln!("[INFO] Automatic restart disabled because dependency is missing.");
            stop_backend(&supervisor_state);
            return;
        }
        startup_log("PREFLIGHT", "Preflight SUCCEEDED ✓");
        println!("[PREFLIGHT] WebView2 Runtime muvaffaqiyatli tasdiqlandi ✓");
    }

    // 5. Tauri App Builder
    let state_for_setup = supervisor_state.clone();
    let state_for_exit = supervisor_state.clone();
    let state_for_build_err = supervisor_state.clone();

    startup_log("TAURI", "Tauri Builder initsializatsiya qilinmoqda...");
    println!("[UI] Tauri oynasi va muhiti initsializatsiya qilinmoqda...");
    let builder = tauri::Builder::default()
        .manage(supervisor_state)
        .setup(move |app| {
            use tauri::Manager;
            use tauri::Emitter;
            use tauri::menu::{Menu, MenuItem};
            use tauri::tray::{TrayIconBuilder, TrayIconEvent, MouseButton, MouseButtonState};

            startup_log("TAURI", "setup hook entered");
            println!("[UI] Tauri asosiy oynasi va System Tray sozlanmoqda...");

            // 1. Asosiy oynani yaratish (on_new_window handler bilan — bo'sh qora oyna chiqishini butunlay bloklaydi)
            startup_log("TAURI", "Building main WebviewWindow with on_new_window interceptor...");
            let win = tauri::WebviewWindowBuilder::new(app, "main", tauri::WebviewUrl::default())
                .title("MISA AI v9.3")
                .inner_size(1280.0, 800.0)
                .min_inner_size(1024.0, 700.0)
                .resizable(true)
                .center()
                .decorations(false)
                .transparent(false)
                .shadow(false)
                .background_color(tauri::window::Color(6, 3, 12, 255))
                .theme(Some(tauri::Theme::Dark))
                .on_new_window(move |url, _features| {
                    startup_log("OPENER", &format!("Intercepted on_new_window -> opening in system browser: {}", url));
                    let _ = app_open_external_url(url.to_string());
                    tauri::webview::NewWindowResponse::Deny
                })
                .build()?;

            let is_vis = win.is_visible().unwrap_or(false);
            startup_log("TAURI", &format!("Main webview window initial is_visible={}", is_vis));
            let _ = win.set_background_color(Some(tauri::window::Color(6, 3, 12, 255)));
            let _ = win.show();
            let _ = win.set_focus();
            let is_vis_after = win.is_visible().unwrap_or(false);
            startup_log("TAURI", &format!("Main webview window after win.show() is_visible={}", is_vis_after));

            // 2. Lifecycle holatini Visible ga o'tkazish
            if let Some(state) = app.try_state::<SupervisorState>() {
                if let Ok(mut lc) = state.lifecycle_state.lock() {
                    *lc = AppLifecycleState::Visible;
                }
            }

            // 3. System Tray Menyu yaratish
            let show_item = MenuItem::with_id(app, "tray_show", "Ochish", true, None::<&str>)?;
            let pause_item = MenuItem::with_id(app, "tray_pause", "Tinglashni pauza qilish", true, None::<&str>)?;
            let resume_item = MenuItem::with_id(app, "tray_resume", "Tinglashni davom ettirish", true, None::<&str>)?;
            let settings_item = MenuItem::with_id(app, "tray_settings", "Sozlamalar", true, None::<&str>)?;
            let exit_item = MenuItem::with_id(app, "tray_exit", "Chiqish", true, None::<&str>)?;

            let tray_menu = Menu::with_items(app, &[
                &show_item,
                &pause_item,
                &resume_item,
                &settings_item,
                &exit_item,
            ])?;

            let mut tray_builder = TrayIconBuilder::with_id("misa_main_tray")
                .menu(&tray_menu)
                .tooltip("Misa AI v9.3")
                .show_menu_on_left_click(false);

            if let Some(icon) = app.default_window_icon() {
                tray_builder = tray_builder.icon(icon.clone());
            }

            let restore_window_and_verify_backend = |app_handle: &tauri::AppHandle| {
                if let Some(win) = app_handle.get_webview_window("main") {
                    let _ = win.show();
                    let _ = win.unminimize();
                    let _ = win.set_focus();
                }
                if let Some(state) = app_handle.try_state::<SupervisorState>() {
                    if let Ok(mut lc) = state.lifecycle_state.lock() {
                        *lc = AppLifecycleState::Visible;
                    }
                    backend_lifecycle_log("TRAY_RESTORE", "Oyna tray orqali tiklandi, backend tekshirilmoqda...");
                    if !check_http_health("127.0.0.1:18420", "/api/health") {
                        backend_lifecycle_log("TRAY_REOPEN_REVIVE", "Backend traydan ochilganda faol emas, auto-revive boshlanmoqda...");
                        if let Ok(mut a) = state.spawn_attempts.lock() { *a = 0; }
                        if let Ok(mut f) = state.is_permanently_failed.lock() { *f = false; }
                        let state_clone = state.inner().clone();
                        std::thread::spawn(move || {
                            ensure_backend_running(&state_clone);
                        });
                    }
                }
            };

            let _tray = tray_builder
                .on_menu_event(move |app_handle, event| {
                    let id_str = event.id().as_ref();
                    startup_log("TRAY", &format!("Tray menu event: {}", id_str));
                    match id_str {
                        "tray_show" => {
                            restore_window_and_verify_backend(app_handle);
                        }
                        "tray_pause" => {
                            let _ = app_handle.emit("misa_tray_command", "pause_listening");
                        }
                        "tray_resume" => {
                            let _ = app_handle.emit("misa_tray_command", "resume_listening");
                        }
                        "tray_settings" => {
                            restore_window_and_verify_backend(app_handle);
                            let _ = app_handle.emit("misa_navigate", "/account");
                        }
                        "tray_exit" => {
                            startup_log("TRAY", "Tray Exit bosildi -> Backend to'xtatilib dastur yopilmoqda...");
                            if let Some(state) = app_handle.try_state::<SupervisorState>() {
                                let mut do_exit = false;
                                if let Ok(mut lc) = state.lifecycle_state.lock() {
                                    if *lc != AppLifecycleState::ShuttingDown && *lc != AppLifecycleState::Exited {
                                        *lc = AppLifecycleState::ShuttingDown;
                                        do_exit = true;
                                    }
                                }
                                if do_exit {
                                    stop_backend(&state);
                                    app_handle.exit(0);
                                }
                            } else {
                                app_handle.exit(0);
                            }
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event {
                        let app = tray.app_handle();
                        if let Some(win) = app.get_webview_window("main") {
                            let is_vis = win.is_visible().unwrap_or(false);
                            if is_vis {
                                let _ = win.set_focus();
                            } else {
                                let _ = win.show();
                                let _ = win.unminimize();
                                let _ = win.set_focus();
                                if let Some(state) = app.try_state::<SupervisorState>() {
                                    if let Ok(mut lc) = state.lifecycle_state.lock() {
                                        *lc = AppLifecycleState::Visible;
                                    }
                                    backend_lifecycle_log("TRAY_RESTORE", "Oyna tray icon click orqali tiklandi, backend tekshirilmoqda...");
                                    if !check_http_health("127.0.0.1:18420", "/api/health") {
                                        backend_lifecycle_log("TRAY_REOPEN_REVIVE", "Backend faol emas, auto-revive boshlanmoqda...");
                                        if let Ok(mut a) = state.spawn_attempts.lock() { *a = 0; }
                                        if let Ok(mut f) = state.is_permanently_failed.lock() { *f = false; }
                                        let state_clone = state.inner().clone();
                                        std::thread::spawn(move || {
                                            ensure_backend_running(&state_clone);
                                        });
                                    }
                                }
                            }
                        }
                    }
                })
                .build(app)?;

            startup_log("TRAY", "System Tray muvaffaqiyatli yaratildi va ro'yxatdan o'tdi ✓");

            // 4. Backend nazoratchi oqimini boshlash
            std::thread::spawn(move || {
                startup_log("BACKEND", "Starting managed backend supervisor thread...");
                ensure_backend_running(&state_for_setup);
            });
            Ok(())
        })
        .on_window_event(move |window, event| {
            match event {
                tauri::WindowEvent::CloseRequested { api, .. } => {
                    startup_log("TAURI_WINDOW", "CloseRequested qabul qilindi -> Chiqish bekor qilindi, oyna trayga yashirilmoqda.");
                    api.prevent_close();
                    if let Some(state) = window.try_state::<SupervisorState>() {
                        if let Ok(mut lc) = state.lifecycle_state.lock() {
                            if *lc == AppLifecycleState::HiddenToTray {
                                return;
                            }
                            *lc = AppLifecycleState::HiddenToTray;
                        }
                    }
                    let _ = window.hide();
                }
                _ => {}
            }
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            app_minimize,
            app_toggle_maximize,
            app_close,
            app_exit,
            app_show_from_tray,
            app_get_lifecycle_state,
            app_is_maximized,
            app_start_resize,
            backend_get_status,
            backend_restart,
            network_diagnostic_check,
            get_network_log_path,
            append_network_log,
            get_backend_lifecycle_log_path,
            get_voice_runtime_log_path,
            app_open_external_url,
            app_focus_window
        ]);

    startup_log("TAURI", "Calling builder.build(tauri::generate_context!())...");
    let app = match builder.build(tauri::generate_context!()) {
        Ok(a) => {
            startup_log("TAURI", "builder.build() SUCCEEDED ✓");
            a
        }
        Err(e) => {
            startup_log("TAURI", &format!("ERROR builder.build() failed: {}", e));
            eprintln!("[ERROR] Tauri oynasini yaratishda xatolik: {}", e);
            stop_backend(&state_for_build_err);
            #[cfg(target_os = "windows")]
            show_native_message_box(
                "Misa AI — Oynani ochishda xatolik",
                &format!("Misa Desktop ilovasi oynasini ochib bo'lmadi:\n{}\n\nBackend jarayoni to'xtatildi.", e),
                true,
            );
            return;
        }
    };

    startup_log("TAURI", "Calling app.run()...");
    println!("[UI] Misa AI Desktop dasturi muvaffaqiyatli ochildi ✓");
    app.run(move |_app_handle, event| {
        match event {
            tauri::RunEvent::Ready => {
                startup_log("TAURI", "RunEvent::Ready received ✓");
            }
            tauri::RunEvent::Resumed => {
                startup_log("TAURI", "RunEvent::Resumed received");
            }
            tauri::RunEvent::ExitRequested { api, .. } => {
                // Agar foydalanuvchi menyudan 'Chiqish' ni tanlamagan bo'lsa (masalan oyna yashiringanda), jarayonni to'xtatmaymiz!
                if let Some(state) = _app_handle.try_state::<SupervisorState>() {
                    let is_shutting_down = state.lifecycle_state.lock().map(|lc| *lc == AppLifecycleState::ShuttingDown).unwrap_or(false);
                    if !is_shutting_down {
                        startup_log("TAURI", "ExitRequested received while in Tray mode. Preventing exit.");
                        api.prevent_exit();
                        return;
                    }
                }
                startup_log("TAURI", "ExitRequested confirmed in ShuttingDown state. Stopping backend...");
                stop_backend(&state_for_exit);
            }
            tauri::RunEvent::Exit => {
                startup_log("TAURI", "RunEvent::Exit received. Ensuring backend stopped...");
                stop_backend(&state_for_exit);
            }
            _ => {}
        }
    });
}
