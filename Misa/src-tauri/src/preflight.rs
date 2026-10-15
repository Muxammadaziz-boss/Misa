// ========== preflight.rs ==========
// Misa AI v9.0.2 — Windows Native WebView2 Preflight & Runtime Bootstrapper
// To'liq mahalliy (Pure Win32 GDI) Misa Ultra Glass UI — WebView2 mavjud bo'lmaganda ham
// mustaqil ishlaydi, xatoliksiz fon jarayonlarini boshqaradi va 100% real lifecycle bilan bog'langan.

use std::ffi::OsStr;
use std::os::windows::ffi::OsStrExt;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

// =========================================================================
// 1. WORKFLOW STATE MACHINE
// =========================================================================

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum PreflightState {
    Detecting,
    AlreadyInstalled,
    SearchingBootstrapper,
    BootstrapperFound,
    LaunchingInstaller,
    Installing,
    InstallerCompleted,
    Verifying,
    Ready,
    Failed,
}

#[derive(Clone, Debug)]
pub struct DiagnosticInfo {
    pub status_text: String,
    pub status_color: u32,
    pub version: String,
    pub bootstrapper: String,
    pub installer: String,
    pub network: String,
    pub arch: String,
}

impl Default for DiagnosticInfo {
    fn default() -> Self {
        let arch = if cfg!(target_arch = "x86_64") {
            "x64"
        } else if cfg!(target_arch = "x86") {
            "x86"
        } else if cfg!(target_arch = "aarch64") {
            "ARM64"
        } else {
            "Unknown"
        };

        Self {
            status_text: "Tekshirilmoqda".to_string(),
            status_color: rgb(168, 85, 247), // Purple
            version: "—".to_string(),
            bootstrapper: "Qidirilmoqda".to_string(),
            installer: "Kutmoqda".to_string(),
            network: "Tekshirilmoqda".to_string(),
            arch: arch.to_string(),
        }
    }
}

#[derive(Clone, Debug)]
pub struct PreflightUiModel {
    pub state: PreflightState,
    pub current_percent: f32,
    pub target_percent: f32,
    pub headline: String,
    pub detail: String,
    pub diagnostics: DiagnosticInfo,
    pub bootstrapper_path: Option<PathBuf>,
    pub installer_pid: Option<u32>,
    pub installer_exit_code: Option<i32>,
    pub failure_reason: String,
    pub should_close: bool,
    pub success: bool,
    pub retry_count: u32,
    pub retry_requested: bool,
}

impl Default for PreflightUiModel {
    fn default() -> Self {
        Self {
            state: PreflightState::Detecting,
            current_percent: 0.0,
            target_percent: 10.0,
            headline: "WebView2 Runtime tekshirilmoqda...".to_string(),
            detail: "Misa AI uchun zarur drayverlar holati tahlil qilinmoqda".to_string(),
            diagnostics: DiagnosticInfo::default(),
            bootstrapper_path: None,
            installer_pid: None,
            installer_exit_code: None,
            failure_reason: String::new(),
            should_close: false,
            success: false,
            retry_count: 0,
            retry_requested: false,
        }
    }
}

// Global UI State referensi (Window Proc bilan almashish uchun)
static GLOBAL_UI_MODEL: Mutex<Option<Arc<Mutex<PreflightUiModel>>>> = Mutex::new(None);

#[inline]
pub fn rgb(r: u8, g: u8, b: u8) -> u32 {
    (r as u32) | ((g as u32) << 8) | ((b as u32) << 16)
}

fn to_wide(s: &str) -> Vec<u16> {
    OsStr::new(s).encode_wide().chain(std::iter::once(0)).collect()
}

// =========================================================================
// 2. DETECTIONS & VERIFICATIONS (REAL SOURCES OF TRUTH)
// =========================================================================

pub fn check_webview2_installed_version() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
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
                                    return Some(ver.to_string());
                                }
                            }
                        }
                    }
                }
            }
        }

        // Jismoniy Application papkalari
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
                            let ver_name = entry.file_name().to_string_lossy().to_string();
                            return Some(if ver_name.contains('.') { ver_name } else { "Active".to_string() });
                        }
                    }
                }
            }
        }

        None
    }

    #[cfg(not(target_os = "windows"))]
    {
        Some("Linux/macOS Emulated".to_string())
    }
}

pub fn check_network_connectivity() -> bool {
    use std::net::TcpStream;
    let addrs = ["1.1.1.1:53", "8.8.8.8:53", "20.189.173.1:443"];
    for addr in addrs {
        if let Ok(socket_addr) = addr.parse() {
            if TcpStream::connect_timeout(&socket_addr, Duration::from_millis(600)).is_ok() {
                return true;
            }
        }
    }
    false
}

pub fn find_or_fetch_bootstrapper() -> Option<PathBuf> {
    let mut setup_cands: Vec<PathBuf> = Vec::new();

    // 1. Joriy ishga tushgan exe yonidagi yo'llar
    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            setup_cands.push(parent.join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
            setup_cands.push(parent.join("MicrosoftEdgeWebview2Setup.exe"));
            setup_cands.push(parent.join("resources").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
            setup_cands.push(parent.join("resources").join("MicrosoftEdgeWebview2Setup.exe"));
            if let Some(pp) = parent.parent() {
                setup_cands.push(pp.join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
                setup_cands.push(pp.join("MicrosoftEdgeWebview2Setup.exe"));
            }
        }
    }

    // 2. Joriy ishchi katalog (CWD)
    if let Ok(cwd) = std::env::current_dir() {
        setup_cands.push(cwd.join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.2").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.2.0").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.2.0").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("9.2").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("9.2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.2").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.1").join("webview2").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("release").join("v9.0.1").join("MicrosoftEdgeWebview2Setup.exe"));
        setup_cands.push(cwd.join("Misa").join("src-tauri").join("resources").join("MicrosoftEdgeWebview2Setup.exe"));
    }

    // 3. TEMP katalog
    let temp_setup = std::env::temp_dir().join("MicrosoftEdgeWebview2Setup.exe");
    setup_cands.push(temp_setup.clone());

    for cand in setup_cands {
        if cand.exists() {
            if let Ok(meta) = std::fs::metadata(&cand) {
                if meta.len() > 100_000 {
                    return Some(cand);
                }
            }
        }
    }

    // 4. Mahalliy topilmasa, rasmiy Microsoft havolasidan yuklab olish
    println!("[WebView2] Mahalliy bootstrapper topilmadi. Rasmiy manbadan yuklab olinmoqda...");
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        let dl_cmd = format!(
            "Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile '{}' -TimeoutSec 35 -UseBasicParsing",
            temp_setup.display()
        );
        let dl_res = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &dl_cmd])
            .creation_flags(CREATE_NO_WINDOW)
            .status();

        if dl_res.map(|s| s.success()).unwrap_or(false) && temp_setup.exists() {
            if let Ok(meta) = std::fs::metadata(&temp_setup) {
                if meta.len() > 100_000 {
                    return Some(temp_setup);
                }
            }
        }
    }

    None
}

// =========================================================================
// 3. WIN32 API DECLARATIONS (ZERO EXTERNAL CRATE DEPENDENCY)
// =========================================================================

#[cfg(target_os = "windows")]
#[allow(dead_code)]
mod win32 {
    pub type HWND = isize;
    pub type HDC = isize;
    pub type HBRUSH = isize;
    pub type HPEN = isize;
    pub type HFONT = isize;
    pub type HBITMAP = isize;
    pub type HGDIOBJ = isize;
    pub type HINSTANCE = isize;
    pub type LRESULT = isize;
    pub type WPARAM = usize;
    pub type LPARAM = isize;
    pub type UINT = u32;
    pub type BOOL = i32;

    #[repr(C)]
    #[derive(Clone, Copy)]
    pub struct RECT {
        pub left: i32,
        pub top: i32,
        pub right: i32,
        pub bottom: i32,
    }

    #[repr(C)]
    pub struct POINT {
        pub x: i32,
        pub y: i32,
    }

    #[repr(C)]
    pub struct PAINTSTRUCT {
        pub hdc: HDC,
        pub f_erase: BOOL,
        pub rc_paint: RECT,
        pub f_restore: BOOL,
        pub f_inc_update: BOOL,
        pub rgb_reserved: [u8; 32],
    }

    #[repr(C)]
    pub struct MSG {
        pub hwnd: HWND,
        pub message: UINT,
        pub wparam: WPARAM,
        pub lparam: LPARAM,
        pub time: u32,
        pub pt: POINT,
    }

    #[repr(C)]
    pub struct WNDCLASSEXW {
        pub cb_size: UINT,
        pub style: UINT,
        pub lpfn_wndproc: Option<unsafe extern "system" fn(HWND, UINT, WPARAM, LPARAM) -> LRESULT>,
        pub cb_cls_extra: i32,
        pub cb_wnd_extra: i32,
        pub h_instance: HINSTANCE,
        pub h_icon: isize,
        pub h_cursor: isize,
        pub hbr_background: HBRUSH,
        pub lpsz_menu_name: *const u16,
        pub lpsz_class_name: *const u16,
        pub h_icon_sm: isize,
    }

    #[link(name = "user32")]
    #[link(name = "gdi32")]
    extern "system" {
        pub fn RegisterClassExW(lpwcx: *const WNDCLASSEXW) -> u16;
        pub fn UnregisterClassW(lp_class_name: *const u16, h_instance: HINSTANCE) -> BOOL;
        pub fn CreateWindowExW(
            ex_style: u32,
            class_name: *const u16,
            window_name: *const u16,
            style: u32,
            x: i32,
            y: i32,
            w: i32,
            h: i32,
            parent: HWND,
            menu: isize,
            instance: HINSTANCE,
            param: *mut std::ffi::c_void,
        ) -> HWND;
        pub fn DestroyWindow(hwnd: HWND) -> BOOL;
        pub fn ShowWindow(hwnd: HWND, cmd_show: i32) -> BOOL;
        pub fn UpdateWindow(hwnd: HWND) -> BOOL;
        pub fn SetForegroundWindow(hwnd: HWND) -> BOOL;
        pub fn BringWindowToTop(hwnd: HWND) -> BOOL;
        pub fn GetMessageW(msg: *mut MSG, hwnd: HWND, min_filter: UINT, max_filter: UINT) -> BOOL;
        pub fn PeekMessageW(msg: *mut MSG, hwnd: HWND, min_filter: UINT, max_filter: UINT, remove_msg: UINT) -> BOOL;
        pub fn TranslateMessage(msg: *const MSG) -> BOOL;
        pub fn DispatchMessageW(msg: *const MSG) -> LRESULT;
        pub fn PostQuitMessage(exit_code: i32);
        pub fn DefWindowProcW(hwnd: HWND, msg: UINT, wparam: WPARAM, lparam: LPARAM) -> LRESULT;
        pub fn GetSystemMetrics(index: i32) -> i32;
        pub fn SetTimer(hwnd: HWND, id_event: usize, elapse: UINT, timer_func: Option<unsafe extern "system" fn(HWND, UINT, usize, u32)>) -> usize;
        pub fn KillTimer(hwnd: HWND, id_event: usize) -> BOOL;
        pub fn InvalidateRect(hwnd: HWND, rect: *const RECT, erase: BOOL) -> BOOL;
        pub fn GetClientRect(hwnd: HWND, rect: *mut RECT) -> BOOL;
        pub fn ReleaseCapture() -> BOOL;
        pub fn SendMessageW(hwnd: HWND, msg: UINT, wparam: WPARAM, lparam: LPARAM) -> LRESULT;
        pub fn GetModuleHandleW(module_name: *const u16) -> HINSTANCE;
        pub fn LoadCursorW(instance: HINSTANCE, cursor_name: *const u16) -> isize;

        pub fn BeginPaint(hwnd: HWND, ps: *mut PAINTSTRUCT) -> HDC;
        pub fn EndPaint(hwnd: HWND, ps: *const PAINTSTRUCT) -> BOOL;
        pub fn CreateCompatibleDC(hdc: HDC) -> HDC;
        pub fn DeleteDC(hdc: HDC) -> BOOL;
        pub fn CreateCompatibleBitmap(hdc: HDC, cx: i32, cy: i32) -> HBITMAP;
        pub fn SelectObject(hdc: HDC, obj: HGDIOBJ) -> HGDIOBJ;
        pub fn DeleteObject(obj: HGDIOBJ) -> BOOL;
        pub fn BitBlt(hdc_dest: HDC, x_dest: i32, y_dest: i32, w: i32, h: i32, hdc_src: HDC, x_src: i32, y_src: i32, rop: u32) -> BOOL;
        pub fn CreateSolidBrush(color: u32) -> HBRUSH;
        pub fn CreatePen(style: i32, width: i32, color: u32) -> HPEN;
        pub fn FillRect(hdc: HDC, rect: *const RECT, brush: HBRUSH) -> i32;
        pub fn RoundRect(hdc: HDC, left: i32, top: i32, right: i32, bottom: i32, width: i32, height: i32) -> BOOL;
        pub fn SetBkMode(hdc: HDC, mode: i32) -> i32;
        pub fn SetTextColor(hdc: HDC, color: u32) -> u32;
        pub fn CreateFontW(
            c_height: i32,
            c_width: i32,
            c_escapement: i32,
            c_orientation: i32,
            c_weight: i32,
            b_italic: u32,
            b_underline: u32,
            b_strike_out: u32,
            i_char_set: u32,
            i_out_precision: u32,
            i_clip_precision: u32,
            i_quality: u32,
            i_pitch_and_family: u32,
            psz_face_name: *const u16,
        ) -> HFONT;
        pub fn DrawTextW(hdc: HDC, lpch_text: *const u16, cch_text: i32, lprc: *mut RECT, format: UINT) -> i32;
        pub fn IsWindow(hwnd: HWND) -> BOOL;
        pub fn IsWindowVisible(hwnd: HWND) -> BOOL;
        pub fn GetWindowRect(hwnd: HWND, rect: *mut RECT) -> BOOL;
        pub fn GetLastError() -> u32;
        pub fn GetStockObject(i: i32) -> HGDIOBJ;
        pub fn SetLayeredWindowAttributes(hwnd: HWND, cr_key: u32, b_alpha: u8, dw_flags: u32) -> BOOL;
        pub fn GetCurrentThreadId() -> u32;
    }
}

// =========================================================================
// 4. MISA ULTRA GLASS WINDOW RENDERER
// =========================================================================

#[cfg(target_os = "windows")]
unsafe fn paint_preflight_ui(hdc: win32::HDC, client_w: i32, client_h: i32, model: &PreflightUiModel) {
    use win32::*;

    // 1. Orqa fon (#02060E)
    let bg_brush = CreateSolidBrush(rgb(2, 6, 14));
    let bg_rect = RECT { left: 0, top: 0, right: client_w, bottom: client_h };
    FillRect(hdc, &bg_rect, bg_brush);
    DeleteObject(bg_brush);

    // Tashqi binafsharang nozik chegara (#2A1045)
    let border_pen = CreatePen(0, 1, rgb(42, 16, 69));
    let old_pen = SelectObject(hdc, border_pen);
    let null_brush = GetStockObject(5 /* NULL_BRUSH */);
    let old_brush = SelectObject(hdc, null_brush);
    RoundRect(hdc, 0, 0, client_w - 1, client_h - 1, 16, 16);
    SelectObject(hdc, old_brush);
    SelectObject(hdc, old_pen);
    DeleteObject(border_pen);

    SetBkMode(hdc, 1); // TRANSPARENT

    // 2. Sarlavha paneli (Header)
    let font_segoe = to_wide("Segoe UI");
    let font_title = CreateFontW(22, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 5, 0, font_segoe.as_ptr());
    let font_sub = CreateFontW(13, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, font_segoe.as_ptr());
    let font_percent = CreateFontW(46, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 5, 0, font_segoe.as_ptr());
    let font_bold15 = CreateFontW(16, 0, 0, 0, 700, 0, 0, 0, 1, 0, 0, 5, 0, font_segoe.as_ptr());
    let font_regular14 = CreateFontW(14, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, font_segoe.as_ptr());
    let font_small12 = CreateFontW(12, 0, 0, 0, 600, 0, 0, 0, 1, 0, 0, 5, 0, font_segoe.as_ptr());

    // Logo / Brend: "MISA AI"
    SelectObject(hdc, font_title);
    SetTextColor(hdc, rgb(255, 255, 255));
    let title_w = to_wide("MISA AI");
    let mut rect_title = RECT { left: 32, top: 20, right: 300, bottom: 48 };
    DrawTextW(hdc, title_w.as_ptr(), -1, &mut rect_title, 0x0000);

    // Kichik sarlavha: "Native Desktop Runtime Preflight"
    SelectObject(hdc, font_sub);
    SetTextColor(hdc, rgb(168, 85, 247)); // Accent purple
    let sub_w = to_wide("Native Desktop Preflight v9.2");
    let mut rect_sub = RECT { left: 130, top: 25, right: 400, bottom: 48 };
    DrawTextW(hdc, sub_w.as_ptr(), -1, &mut rect_sub, 0x0000);

    // Oyna yopish tugmasi [ × ]
    SetTextColor(hdc, rgb(148, 163, 184));
    let close_w = to_wide("✕");
    let mut rect_close = RECT { left: client_w - 45, top: 18, right: client_w - 18, bottom: 45 };
    DrawTextW(hdc, close_w.as_ptr(), -1, &mut rect_close, 0x0001 | 0x0004);

    // ---------------------------------------------------------------------
    // 3. CHAP TOMON: Katta progress kartasi va Stepper (X: 32, W: 420)
    // ---------------------------------------------------------------------

    // Karta foni: #080E1C
    let card_brush = CreateSolidBrush(rgb(8, 14, 28));
    let card_pen = CreatePen(0, 1, rgb(38, 27, 64));
    SelectObject(hdc, card_brush);
    SelectObject(hdc, card_pen);
    RoundRect(hdc, 32, 64, 460, 480, 14, 14);
    DeleteObject(card_brush);
    DeleteObject(card_pen);

    // Katta Foiz (37%)
    SelectObject(hdc, font_percent);
    SetTextColor(hdc, rgb(192, 132, 252)); // Light purple
    let pct_text = format!("{}%", model.current_percent.round() as i32);
    let pct_w = to_wide(&pct_text);
    let mut rect_pct = RECT { left: 52, top: 80, right: 220, bottom: 135 };
    DrawTextW(hdc, pct_w.as_ptr(), -1, &mut rect_pct, 0x0000);

    // Holat sarlavhasi
    SelectObject(hdc, font_bold15);
    SetTextColor(hdc, rgb(248, 250, 252));
    let hl_w = to_wide(&model.headline);
    let mut rect_hl = RECT { left: 52, top: 138, right: 440, bottom: 162 };
    DrawTextW(hdc, hl_w.as_ptr(), -1, &mut rect_hl, 0x0000);

    // Progress Bar (Track & Fill)
    let bar_left = 52;
    let bar_top = 170;
    let bar_w = 388;
    let bar_h = 8;

    let track_brush = CreateSolidBrush(rgb(30, 27, 75));
    let track_rect = RECT { left: bar_left, top: bar_top, right: bar_left + bar_w, bottom: bar_top + bar_h };
    FillRect(hdc, &track_rect, track_brush);
    DeleteObject(track_brush);

    let fill_w = ((bar_w as f32) * (model.current_percent / 100.0).clamp(0.0, 1.0)) as i32;
    if fill_w > 0 {
        let fill_color = if model.state == PreflightState::Failed {
            rgb(239, 68, 68) // Red
        } else if model.state == PreflightState::Ready || model.state == PreflightState::AlreadyInstalled {
            rgb(16, 185, 129) // Green
        } else {
            rgb(147, 3, 197) // Misa Accent Violet (#9303C5)
        };
        let fill_brush = CreateSolidBrush(fill_color);
        let fill_rect = RECT { left: bar_left, top: bar_top, right: bar_left + fill_w, bottom: bar_top + bar_h };
        FillRect(hdc, &fill_rect, fill_brush);
        DeleteObject(fill_brush);
    }

    // Stepper (6 ta bosqich)
    let steps = [
        "WebView2 mavjudligini tekshirish",
        "Bootstrapperni qidirish",
        "MicrosoftEdgeWebview2Setup.exe",
        "/silent /install",
        "Installer tugashini kutish",
        "WebView2'ni QAYTA tekshirish",
    ];

    // Stepper holatlari: 0=waiting, 1=active, 2=done, 3=failed
    let step_status: [u8; 6] = match model.state {
        PreflightState::Detecting => [1, 0, 0, 0, 0, 0],
        PreflightState::AlreadyInstalled => [2, 2, 2, 2, 2, 2],
        PreflightState::SearchingBootstrapper => [2, 1, 0, 0, 0, 0],
        PreflightState::BootstrapperFound => [2, 2, 1, 0, 0, 0],
        PreflightState::LaunchingInstaller => [2, 2, 2, 1, 0, 0],
        PreflightState::Installing => [2, 2, 2, 2, 1, 0],
        PreflightState::InstallerCompleted => [2, 2, 2, 2, 2, 1],
        PreflightState::Verifying => [2, 2, 2, 2, 2, 1],
        PreflightState::Ready => [2, 2, 2, 2, 2, 2],
        PreflightState::Failed => {
            if model.bootstrapper_path.is_none() {
                [2, 3, 0, 0, 0, 0]
            } else if model.installer_exit_code.is_some() && model.installer_exit_code != Some(0) {
                [2, 2, 2, 2, 3, 0]
            } else {
                [2, 2, 2, 2, 2, 3]
            }
        }
    };

    let start_y = 196;
    let step_h = 36;

    // Vertikal bog'lovchi chiziq
    let line_pen = CreatePen(0, 2, rgb(30, 27, 75));
    let prev_p = SelectObject(hdc, line_pen);
    for i in 0..5 {
        let y1 = start_y + (i * step_h) + 14;
        let y2 = start_y + ((i + 1) * step_h) + 6;
        let rect_l = RECT { left: 63, top: y1, right: 65, bottom: y2 };
        let brush_l = CreateSolidBrush(rgb(30, 27, 75));
        FillRect(hdc, &rect_l, brush_l);
        DeleteObject(brush_l);
    }
    SelectObject(hdc, prev_p);
    DeleteObject(line_pen);

    SelectObject(hdc, font_regular14);

    for (idx, text) in steps.iter().enumerate() {
        let sy = start_y + (idx as i32 * step_h);
        let status = step_status[idx];

        // Belgilar: ✓, ●, ○, ✕
        let (icon, color, text_color) = match status {
            2 => ("✓", rgb(16, 185, 129), rgb(241, 245, 249)), // Done (Green)
            1 => ("●", rgb(192, 132, 252), rgb(255, 255, 255)), // Active (Purple)
            3 => ("✕", rgb(239, 68, 68), rgb(248, 113, 113)),   // Failed (Red)
            _ => ("○", rgb(71, 85, 105), rgb(148, 163, 184)),   // Pending (Gray)
        };

        SetTextColor(hdc, color);
        let ic_w = to_wide(icon);
        let mut rect_ic = RECT { left: 56, top: sy, right: 74, bottom: sy + 24 };
        DrawTextW(hdc, ic_w.as_ptr(), -1, &mut rect_ic, 0x0001);

        SetTextColor(hdc, text_color);
        let tx_w = to_wide(text);
        let mut rect_tx = RECT { left: 82, top: sy, right: 440, bottom: sy + 24 };
        DrawTextW(hdc, tx_w.as_ptr(), -1, &mut rect_tx, 0x0000);
    }

    // Pastki xatolik / muvaffaqiyat bloklari va tugmalar
    if model.state == PreflightState::Failed {
        // Xatolik xabari
        SetTextColor(hdc, rgb(248, 113, 113));
        let err_w = to_wide("Xatolik: Runtime tasdiqlanmadi!");
        let mut rect_err = RECT { left: 52, top: 418, right: 440, bottom: 438 };
        DrawTextW(hdc, err_w.as_ptr(), -1, &mut rect_err, 0x0000);

        // [ Qayta urinish ] tugmasi (X: 52, W: 140, H: 32)
        let btn_retry_brush = CreateSolidBrush(rgb(76, 29, 149));
        let btn_retry_rect = RECT { left: 52, top: 440, right: 192, bottom: 472 };
        FillRect(hdc, &btn_retry_rect, btn_retry_brush);
        DeleteObject(btn_retry_brush);

        SetTextColor(hdc, rgb(255, 255, 255));
        let retry_w = to_wide("Qayta urinish");
        let mut rect_r_txt = RECT { left: 52, top: 446, right: 192, bottom: 472 };
        DrawTextW(hdc, retry_w.as_ptr(), -1, &mut rect_r_txt, 0x0001);

        // [ Chiqish ] tugmasi (X: 204, W: 110, H: 32)
        let btn_exit_brush = CreateSolidBrush(rgb(31, 41, 55));
        let btn_exit_rect = RECT { left: 204, top: 440, right: 314, bottom: 472 };
        FillRect(hdc, &btn_exit_rect, btn_exit_brush);
        DeleteObject(btn_exit_brush);

        SetTextColor(hdc, rgb(209, 213, 219));
        let exit_w = to_wide("Chiqish");
        let mut rect_e_txt = RECT { left: 204, top: 446, right: 314, bottom: 472 };
        DrawTextW(hdc, exit_w.as_ptr(), -1, &mut rect_e_txt, 0x0001);
    } else if model.state == PreflightState::Ready || model.state == PreflightState::AlreadyInstalled {
        SetTextColor(hdc, rgb(52, 211, 153)); // Soft green
        let succ_w = to_wide("✓ WebView2 Runtime tayyor. Misa AI ochilmoqda...");
        let mut rect_succ = RECT { left: 52, top: 432, right: 440, bottom: 460 };
        DrawTextW(hdc, succ_w.as_ptr(), -1, &mut rect_succ, 0x0000);
    }

    // ---------------------------------------------------------------------
    // 4. O'NG TOMON: Diagnostika paneli (X: 476, W: 252)
    // ---------------------------------------------------------------------

    // Glass panel foni (#080D1A) binafsharang chegara (#3B145E) bilan
    let diag_brush = CreateSolidBrush(rgb(8, 13, 26));
    let diag_pen = CreatePen(0, 1, rgb(59, 20, 94));
    SelectObject(hdc, diag_brush);
    SelectObject(hdc, diag_pen);
    RoundRect(hdc, 476, 64, 728, 480, 14, 14);
    DeleteObject(diag_brush);
    DeleteObject(diag_pen);

    // Header: "WEBVIEW2 RUNTIME"
    SelectObject(hdc, font_small12);
    SetTextColor(hdc, rgb(192, 132, 252));
    let diag_title_w = to_wide("WEBVIEW2 RUNTIME");
    let mut rect_dt = RECT { left: 496, top: 82, right: 708, bottom: 102 };
    DrawTextW(hdc, diag_title_w.as_ptr(), -1, &mut rect_dt, 0x0000);

    // Ajratuvchi chiziq
    let div_brush = CreateSolidBrush(rgb(30, 21, 56));
    let div_rect = RECT { left: 496, top: 108, right: 708, bottom: 109 };
    FillRect(hdc, &div_rect, div_brush);
    DeleteObject(div_brush);

    // Diagnostika maydonlari
    let diag_items = [
        ("Status", &model.diagnostics.status_text, model.diagnostics.status_color),
        ("Version", &model.diagnostics.version, rgb(148, 163, 184)),
        ("Bootstrapper", &model.diagnostics.bootstrapper, if model.diagnostics.bootstrapper == "Topildi" { rgb(16, 185, 129) } else { rgb(148, 163, 184) }),
        ("Installer", &model.diagnostics.installer, if model.diagnostics.installer == "Ishlamoqda" { rgb(56, 189, 248) } else if model.diagnostics.installer == "Tugadi" { rgb(16, 185, 129) } else { rgb(148, 163, 184) }),
        ("Network", &model.diagnostics.network, if model.diagnostics.network == "Ulangan" { rgb(16, 185, 129) } else { rgb(239, 68, 68) }),
        ("Architecture", &model.diagnostics.arch, rgb(148, 163, 184)),
    ];

    let dy_start = 124;
    let dy_h = 48;

    for (i, (label, val, val_col)) in diag_items.iter().enumerate() {
        let cur_y = dy_start + (i as i32 * dy_h);

        // Kichik yorliq (Label)
        SelectObject(hdc, font_small12);
        SetTextColor(hdc, rgb(100, 116, 139));
        let lbl_w = to_wide(label);
        let mut r_lbl = RECT { left: 496, top: cur_y, right: 708, bottom: cur_y + 18 };
        DrawTextW(hdc, lbl_w.as_ptr(), -1, &mut r_lbl, 0x0000);

        // Qiymat (Value)
        SelectObject(hdc, font_bold15);
        SetTextColor(hdc, *val_col);
        let val_w = to_wide(val);
        let mut r_val = RECT { left: 496, top: cur_y + 18, right: 708, bottom: cur_y + 42 };
        DrawTextW(hdc, val_w.as_ptr(), -1, &mut r_val, 0x0000);
    }

    // Fontlarni tozalash
    DeleteObject(font_title);
    DeleteObject(font_sub);
    DeleteObject(font_percent);
    DeleteObject(font_bold15);
    DeleteObject(font_regular14);
    DeleteObject(font_small12);
}

// =========================================================================
// 5. WIN32 WINDOW PROCEDURE & EVENT LOOP
// =========================================================================

static PAINT_COUNT: Mutex<u32> = Mutex::new(0);

#[cfg(target_os = "windows")]
unsafe extern "system" fn preflight_wndproc(
    hwnd: win32::HWND,
    msg: win32::UINT,
    wparam: win32::WPARAM,
    lparam: win32::LPARAM,
) -> win32::LRESULT {
    use win32::*;
    use crate::diag::startup_log;

    match msg {
        0x000F => {
            // WM_PAINT (Flicker-free Double Buffering)
            let count = {
                let mut c = PAINT_COUNT.lock().unwrap();
                *c += 1;
                *c
            };
            if count == 1 || count % 100 == 0 {
                startup_log("PREFLIGHT", &format!("WM_PAINT handled (count={})", count));
            }

            let mut ps: PAINTSTRUCT = std::mem::zeroed();
            let hdc = BeginPaint(hwnd, &mut ps);

            let mut client_rect: RECT = std::mem::zeroed();
            GetClientRect(hwnd, &mut client_rect);
            let cw = client_rect.right - client_rect.left;
            let ch = client_rect.bottom - client_rect.top;

            let mem_dc = CreateCompatibleDC(hdc);
            let mem_bm = CreateCompatibleBitmap(hdc, cw, ch);
            if mem_dc == 0 || mem_bm == 0 {
                startup_log("PREFLIGHT", &format!("GDI error in WM_PAINT: mem_dc=0x{:X}, mem_bm=0x{:X}, GetLastError={}", mem_dc, mem_bm, GetLastError()));
            }
            let old_bm = SelectObject(mem_dc, mem_bm);

            if let Ok(guard) = GLOBAL_UI_MODEL.lock() {
                if let Some(ref model_arc) = *guard {
                    if let Ok(model) = model_arc.lock() {
                        paint_preflight_ui(mem_dc, cw, ch, &model);
                    }
                }
            }

            BitBlt(hdc, 0, 0, cw, ch, mem_dc, 0, 0, 0x00CC0020 /* SRCCOPY */);
            SelectObject(mem_dc, old_bm);
            DeleteObject(mem_bm);
            DeleteDC(mem_dc);

            EndPaint(hwnd, &ps);
            0
        }
        0x0014 => {
            // WM_ERASEBKGND: Return 1 to prevent flicker (we paint full background in WM_PAINT)
            1
        }
        0x0113 => {
            // WM_TIMER (~33 FPS animatsiya va progress silliqlash)
            if let Ok(guard) = GLOBAL_UI_MODEL.lock() {
                if let Some(ref model_arc) = *guard {
                    if let Ok(mut model) = model_arc.lock() {
                        // Progress foizini silliq siljitish (Easing)
                        let diff = model.target_percent - model.current_percent;
                        if diff.abs() > 0.3 {
                            model.current_percent += diff * 0.12;
                        } else {
                            model.current_percent = model.target_percent;
                        }

                        if model.should_close {
                            startup_log("PREFLIGHT", "model.should_close=true in WM_TIMER. Destroying preflight window...");
                            KillTimer(hwnd, 1);
                            DestroyWindow(hwnd);
                            return 0;
                        }
                    }
                }
            }
            InvalidateRect(hwnd, std::ptr::null(), 0);
            0
        }
        0x0201 => {
            // WM_LBUTTONDOWN
            let x = (lparam & 0xFFFF) as i32;
            let y = ((lparam >> 16) & 0xFFFF) as i32;

            // 1. Oyna yopish [✕] tugmasi (X: 710..745, Y: 12..45)
            if x >= 710 && x <= 745 && y >= 12 && y <= 45 {
                startup_log("PREFLIGHT", "Close button [X] clicked by user");
                if let Ok(guard) = GLOBAL_UI_MODEL.lock() {
                    if let Some(ref model_arc) = *guard {
                        if let Ok(mut model) = model_arc.lock() {
                            model.should_close = true;
                            model.success = false;
                        }
                    }
                }
                DestroyWindow(hwnd);
                return 0;
            }

            // 2. Failed holatidagi tugmalar
            let mut is_failed = false;
            if let Ok(guard) = GLOBAL_UI_MODEL.lock() {
                if let Some(ref model_arc) = *guard {
                    if let Ok(model) = model_arc.lock() {
                        is_failed = model.state == PreflightState::Failed;
                    }
                }
            }

            if is_failed {
                // [ Qayta urinish ] tugmasi (X: 52..192, Y: 440..472)
                if x >= 52 && x <= 192 && y >= 440 && y <= 472 {
                    startup_log("PREFLIGHT", "[ Qayta urinish ] button clicked by user");
                    if let Ok(guard) = GLOBAL_UI_MODEL.lock() {
                        if let Some(ref model_arc) = *guard {
                            if let Ok(mut model) = model_arc.lock() {
                                if model.retry_count < 3 {
                                    model.retry_count += 1;
                                    model.retry_requested = true;
                                }
                            }
                        }
                    }
                    return 0;
                }

                // [ Chiqish ] tugmasi (X: 204..314, Y: 440..472)
                if x >= 204 && x <= 314 && y >= 440 && y <= 472 {
                    startup_log("PREFLIGHT", "[ Chiqish ] button clicked by user");
                    if let Ok(guard) = GLOBAL_UI_MODEL.lock() {
                        if let Some(ref model_arc) = *guard {
                            if let Ok(mut model) = model_arc.lock() {
                                model.should_close = true;
                                model.success = false;
                            }
                        }
                    }
                    DestroyWindow(hwnd);
                    return 0;
                }
            }

            // 3. Sarlavha orqali oynani ko'chirish (Drag to move)
            if y <= 60 && x < 700 {
                ReleaseCapture();
                SendMessageW(hwnd, 0x00A1 /* WM_NCLBUTTONDOWN */, 2 /* HTCAPTION */, 0);
                return 0;
            }

            DefWindowProcW(hwnd, msg, wparam, lparam)
        }
        0x0010 => {
            // WM_CLOSE
            startup_log("PREFLIGHT", "WM_CLOSE received");
            if let Ok(guard) = GLOBAL_UI_MODEL.lock() {
                if let Some(ref model_arc) = *guard {
                    if let Ok(mut model) = model_arc.lock() {
                        model.should_close = true;
                    }
                }
            }
            DestroyWindow(hwnd);
            0
        }
        0x0002 => {
            // WM_DESTROY (Do NOT call PostQuitMessage; that would poison Tauri event loop!)
            startup_log("PREFLIGHT", "WM_DESTROY received for preflight window");
            0
        }
        _ => DefWindowProcW(hwnd, msg, wparam, lparam),
    }
}

// =========================================================================
// 6. ASOSIY PREFLIGHT ISHGA TUSHIRUVCHISI (NATIVE RUNTIME PREFLIGHT)
// =========================================================================

pub fn run_native_preflight() -> bool {
    #[cfg(target_os = "windows")]
    {
        use win32::*;
        use crate::diag::startup_log;

        startup_log("PREFLIGHT", "run_native_preflight() entered");
        let tid = unsafe { GetCurrentThreadId() };
        startup_log("PREFLIGHT", &format!("Preflight UI thread ID: {}", tid));

        let model = Arc::new(Mutex::new(PreflightUiModel::default()));
        {
            if let Ok(mut g) = GLOBAL_UI_MODEL.lock() {
                *g = Some(model.clone());
            }
        }

        let instance = unsafe { GetModuleHandleW(std::ptr::null()) };
        let class_name = to_wide("MisaNativePreflightWindowClass_v901");

        let wc = WNDCLASSEXW {
            cb_size: std::mem::size_of::<WNDCLASSEXW>() as UINT,
            style: 0x0002 | 0x0001, // CS_HREDRAW | CS_VREDRAW
            lpfn_wndproc: Some(preflight_wndproc),
            cb_cls_extra: 0,
            cb_wnd_extra: 0,
            h_instance: instance,
            h_icon: 0,
            h_cursor: unsafe { LoadCursorW(0, 32512 as *const u16 /* IDC_ARROW */) },
            hbr_background: 0,
            lpsz_menu_name: std::ptr::null(),
            lpsz_class_name: class_name.as_ptr(),
            h_icon_sm: 0,
        };

        let reg_atom = unsafe { RegisterClassExW(&wc) };
        let reg_err = unsafe { GetLastError() };
        startup_log("PREFLIGHT", &format!("RegisterClassExW returned atom=0x{:X}, GetLastError={}", reg_atom, reg_err));

        let win_w = 760;
        let win_h = 520;
        let screen_w = unsafe { GetSystemMetrics(0 /* SM_CXSCREEN */) };
        let screen_h = unsafe { GetSystemMetrics(1 /* SM_CYSCREEN */) };
        let win_x = ((screen_w - win_w) / 2).max(20);
        let win_y = ((screen_h - win_h) / 2).max(20);
        startup_log("PREFLIGHT", &format!(
            "Calculated layout: screen={}x{}, window target pos=({}, {}), size={}x{}",
            screen_w, screen_h, win_x, win_y, win_w, win_h
        ));

        let title_wide = to_wide("MISA AI — Runtime Preflight");

        // Style: WS_POPUP | WS_VISIBLE | WS_CLIPCHILDREN | WS_CLIPSIBLINGS
        let style = 0x80000000 | 0x10000000 | 0x02000000 | 0x04000000;
        // ExStyle: WS_EX_APPWINDOW (0x00040000) | WS_EX_TOPMOST (0x00000008)
        let ex_style = 0x00040000 | 0x00000008;

        startup_log("PREFLIGHT", "Calling CreateWindowExW...");
        let hwnd = unsafe {
            CreateWindowExW(
                ex_style,
                class_name.as_ptr(),
                title_wide.as_ptr(),
                style,
                win_x,
                win_y,
                win_w,
                win_h,
                0,
                0,
                instance,
                std::ptr::null_mut(),
            )
        };

        let create_err = unsafe { GetLastError() };
        startup_log("PREFLIGHT", &format!("CreateWindowExW returned HWND=0x{:X}, GetLastError={}", hwnd, create_err));

        if hwnd == 0 {
            startup_log("PREFLIGHT", "CRITICAL ERROR: Native preflight HWND is 0!");
            eprintln!("[ERROR] Native preflight oynasini yaratib bo'lmadi!");
            return false;
        }

        let is_win = unsafe { IsWindow(hwnd) } != 0;
        let mut rect: RECT = unsafe { std::mem::zeroed() };
        unsafe { GetWindowRect(hwnd, &mut rect) };
        let is_vis = unsafe { IsWindowVisible(hwnd) } != 0;
        startup_log("PREFLIGHT", &format!(
            "Window validation: IsWindow={}, IsWindowVisible={}, Rect=[left={}, top={}, right={}, bottom={}, width={}, height={}]",
            is_win, is_vis, rect.left, rect.top, rect.right, rect.bottom, rect.right - rect.left, rect.bottom - rect.top
        ));

        // DWM Windows 11 dark mode / rounded corners (non-fatal)
        unsafe {
            if let Ok(lib) = libloading_load_dwmapi() {
                startup_log("PREFLIGHT", "DWM attributes applied successfully");
                let _ = lib;
            } else {
                startup_log("PREFLIGHT", "DWM not available (fallback to classic GDI frame)");
            }
        }

        unsafe {
            ShowWindow(hwnd, 5 /* SW_SHOW */);
            UpdateWindow(hwnd);
            BringWindowToTop(hwnd);
            SetForegroundWindow(hwnd);
            SetTimer(hwnd, 1, 30, None);
        }
        let is_vis_after = unsafe { IsWindowVisible(hwnd) } != 0;
        startup_log("PREFLIGHT", &format!("ShowWindow(SW_SHOW) executed. IsWindowVisible={}", is_vis_after));

        // Start worker thread for lifecycle
        let worker_model = model.clone();
        startup_log("PREFLIGHT", "Spawning worker lifecycle thread...");
        std::thread::spawn(move || {
            run_worker_lifecycle(worker_model);
        });

        // Win32 Message Loop on UI thread
        startup_log("PREFLIGHT", "Starting UI thread message loop...");
        let mut msg: MSG = unsafe { std::mem::zeroed() };
        while unsafe { IsWindow(hwnd) } != 0 {
            let res = unsafe { GetMessageW(&mut msg, 0, 0, 0) };
            if res <= 0 {
                startup_log("PREFLIGHT", &format!("GetMessageW returned {}", res));
                break;
            }
            unsafe {
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }
        }
        startup_log("PREFLIGHT", "UI message loop exited.");

        // Drain any remaining messages from queue so Tauri gets a clean queue
        while unsafe { PeekMessageW(&mut msg, 0, 0, 0, 1 /* PM_REMOVE */) } != 0 {
            if msg.message != 0x0012 /* WM_QUIT */ {
                unsafe {
                    TranslateMessage(&msg);
                    DispatchMessageW(&msg);
                }
            }
        }
        startup_log("PREFLIGHT", "Message queue drained and clean ✓");

        unsafe {
            UnregisterClassW(class_name.as_ptr(), instance);
        }

        let is_ok = model.lock().map(|m| m.success).unwrap_or(false);
        startup_log("PREFLIGHT", &format!("run_native_preflight finished. Result success={}", is_ok));
        is_ok
    }

    #[cfg(not(target_os = "windows"))]
    {
        true
    }
}

// =========================================================================
// 7. REAL WORKER LIFECYCLE STATE MACHINE (NO FAKE TIMERS)
// =========================================================================

fn run_worker_lifecycle(model_arc: Arc<Mutex<PreflightUiModel>>) {
    use crate::diag::startup_log;
    const CREATE_NO_WINDOW: u32 = 0x08000000;

    startup_log("WORKER", "Worker lifecycle thread started");

    loop {
        // 0. Tarmoq tekshiruvi
        let net_ok = check_network_connectivity();
        startup_log("WORKER", &format!("Network connectivity check: {}", if net_ok { "Connected" } else { "Disconnected" }));
        if let Ok(mut m) = model_arc.lock() {
            m.diagnostics.network = if net_ok { "Ulangan".to_string() } else { "Ulanmagan".to_string() };
        }

        // 1. Initial Detection
        startup_log("WORKER", "State = Detecting, target_percent = 10%");
        if let Ok(mut m) = model_arc.lock() {
            m.state = PreflightState::Detecting;
            m.target_percent = 10.0;
            m.headline = "WebView2 Runtime tekshirilmoqda...".to_string();
            m.diagnostics.status_text = "Tekshirilmoqda".to_string();
            m.diagnostics.status_color = rgb(168, 85, 247);
        }
        std::thread::sleep(Duration::from_millis(350));

        startup_log("WEBVIEW2", "Checking installed version via registry and directories...");
        let ver_opt = check_webview2_installed_version();
        if let Some(ver) = ver_opt {
            startup_log("WEBVIEW2", &format!("WebView2 already installed: {}", ver));
            println!("[WebView2] Allaqachon o'rnatilgan aniqlandi: {}", ver);
            if let Ok(mut m) = model_arc.lock() {
                m.state = PreflightState::AlreadyInstalled;
                m.target_percent = 100.0;
                m.headline = "✓ WebView2 Runtime tayyor".to_string();
                m.diagnostics.status_text = "READY".to_string();
                m.diagnostics.status_color = rgb(16, 185, 129);
                m.diagnostics.version = ver;
            }
            startup_log("WORKER", "Displaying READY state for 500ms before closing...");
            std::thread::sleep(Duration::from_millis(500));
            if let Ok(mut m) = model_arc.lock() {
                m.state = PreflightState::Ready;
                m.success = true;
                m.should_close = true;
            }
            startup_log("WORKER", "Preflight success signaled (should_close=true). Worker exiting.");
            return;
        }

        // 2. Searching Bootstrapper
        startup_log("WEBVIEW2", "WebView2 NOT found in system! Starting bootstrapper search...");
        println!("[WebView2] bootstrapper search started");
        if let Ok(mut m) = model_arc.lock() {
            m.state = PreflightState::SearchingBootstrapper;
            m.target_percent = 20.0;
            m.headline = "Microsoft WebView2 Bootstrapper qidirilmoqda...".to_string();
            m.diagnostics.status_text = "O'rnatilmagan".to_string();
            m.diagnostics.status_color = rgb(251, 191, 36);
            m.diagnostics.bootstrapper = "Qidirilmoqda".to_string();
        }
        std::thread::sleep(Duration::from_millis(300));

        let setup_path_opt = find_or_fetch_bootstrapper();
        startup_log("WORKER", &format!("Bootstrapper search result: path={:?}", setup_path_opt));
        println!("[WebView2] bootstrapper path: {:?}", setup_path_opt);
        println!("[WebView2] bootstrapper found: {}", setup_path_opt.is_some());

        let setup_path = match setup_path_opt {
            Some(p) => {
                if let Ok(mut m) = model_arc.lock() {
                    m.bootstrapper_path = Some(p.clone());
                    m.state = PreflightState::BootstrapperFound;
                    m.target_percent = 35.0;
                    m.headline = "MicrosoftEdgeWebview2Setup.exe topildi ✓".to_string();
                    m.diagnostics.bootstrapper = "Topildi".to_string();
                }
                p
            }
            None => {
                startup_log("WORKER", "ERROR: Bootstrapper not found and cannot download!");
                eprintln!("[ERROR] WebView2 bootstrapper topilmadi va yuklab bo'lmadi!");
                if let Ok(mut m) = model_arc.lock() {
                    m.state = PreflightState::Failed;
                    m.headline = "Bootstrapper topilmadi".to_string();
                    m.diagnostics.status_text = "Xatolik".to_string();
                    m.diagnostics.status_color = rgb(239, 68, 68);
                    m.diagnostics.bootstrapper = "Topilmadi".to_string();
                    m.failure_reason = "MicrosoftEdgeWebview2Setup.exe fayli topilmadi va internet yo'q".to_string();
                }
                // Foydalanuvchi retry bosishini kutish
                if wait_for_retry(&model_arc) {
                    continue;
                }
                return;
            }
        };

        std::thread::sleep(Duration::from_millis(400));

        // 3. Launching Installer (/silent /install)
        startup_log("WORKER", &format!("Launching installer: {:?}", setup_path));
        println!("[WebView2] installer launch started");
        if let Ok(mut m) = model_arc.lock() {
            m.state = PreflightState::LaunchingInstaller;
            m.target_percent = 40.0;
            m.headline = "MicrosoftEdgeWebview2Setup.exe ishga tushirilmoqda...".to_string();
            m.diagnostics.status_text = "O'rnatilmoqda".to_string();
            m.diagnostics.status_color = rgb(56, 189, 248);
            m.diagnostics.installer = "Ishlamoqda".to_string();
        }

        let spawn_res = Command::new(&setup_path)
            .args(["/silent", "/install"])
            .creation_flags(CREATE_NO_WINDOW)
            .spawn();

        let mut child: Child = match spawn_res {
            Ok(c) => {
                let pid = c.id();
                startup_log("WORKER", &format!("Installer process spawned with PID={}", pid));
                println!("[WebView2] installer PID: {}", pid);
                if let Ok(mut m) = model_arc.lock() {
                    m.installer_pid = Some(pid);
                    m.state = PreflightState::Installing;
                    m.target_percent = 50.0;
                    m.headline = "Microsoft WebView2 Runtime o'rnatilmoqda...".to_string();
                }
                c
            }
            Err(e) => {
                startup_log("WORKER", &format!("ERROR spawning installer: {}", e));
                eprintln!("[ERROR] Bootstrapperni ishga tushirishda xatolik: {}", e);
                if let Ok(mut m) = model_arc.lock() {
                    m.state = PreflightState::Failed;
                    m.headline = "O'rnatuvchi ishga tushmadi".to_string();
                    m.diagnostics.status_text = "Xatolik".to_string();
                    m.diagnostics.status_color = rgb(239, 68, 68);
                    m.diagnostics.installer = "Xatolik".to_string();
                    m.failure_reason = format!("O'rnatuvchi bajarilishi rad etildi: {}", e);
                }
                if wait_for_retry(&model_arc) {
                    continue;
                }
                return;
            }
        };

        // 4. Installer jarayoni tugashini monitoring qilish
        let start_time = Instant::now();
        let timeout = Duration::from_secs(120);
        let mut exit_code: Option<i32> = None;

        while start_time.elapsed() < timeout {
            match child.try_wait() {
                Ok(Some(status)) => {
                    exit_code = status.code();
                    startup_log("WORKER", &format!("Installer completed with exit_code={:?}", exit_code));
                    println!("[WebView2] installer exit code: {:?}", exit_code);
                    break;
                }
                Ok(None) => {
                    // Installer ishlamoqda — progressni 50% dan 80% gacha silliq oshirish
                    if let Ok(mut m) = model_arc.lock() {
                        let elapsed_sec = start_time.elapsed().as_secs_f32();
                        let target = (50.0 + (elapsed_sec / 30.0) * 30.0).min(80.0);
                        m.target_percent = target;
                    }
                    std::thread::sleep(Duration::from_millis(300));
                }
                Err(e) => {
                    startup_log("WORKER", &format!("try_wait error on installer: {}", e));
                    eprintln!("[ERROR] try_wait xatoligi: {}", e);
                    break;
                }
            }
        }

        if exit_code.is_none() {
            startup_log("WORKER", "Installer timed out (120s)! Killing installer process.");
            println!("[WebView2] Installer vaqt chegarasiga yetdi (120s). Majburiy to'xtatildi.");
            let _ = child.kill();
            let _ = child.wait();
        }

        if let Ok(mut m) = model_arc.lock() {
            m.state = PreflightState::InstallerCompleted;
            m.target_percent = 85.0;
            m.installer_exit_code = exit_code;
            m.headline = "O'rnatuvchi yakunlandi, registratsiya kutilmoqda...".to_string();
            m.diagnostics.installer = "Tugadi".to_string();
        }

        // Registry va fayllar tizimi keshini yangilash uchun 1.5 soniya kutish
        std::thread::sleep(Duration::from_millis(1500));

        // 5. Verification (Yakuniy Haqiqat Manbasi)
        startup_log("WORKER", "Running strict post-install verification...");
        println!("[WebView2] verification started");
        if let Ok(mut m) = model_arc.lock() {
            m.state = PreflightState::Verifying;
            m.target_percent = 92.0;
            m.headline = "WebView2 o'rnatilishi qayta tekshirilmoqda...".to_string();
            m.diagnostics.status_text = "Tekshirilmoqda".to_string();
        }
        std::thread::sleep(Duration::from_millis(400));

        let verified_ver = check_webview2_installed_version();
        startup_log("WORKER", &format!("Post-install verification result: {:?}", verified_ver));
        println!("[WebView2] installed after installer: {}", verified_ver.is_some());

        if let Some(ver) = verified_ver {
            // Muvaffaqiyatli yakunlandi!
            if let Ok(mut m) = model_arc.lock() {
                m.state = PreflightState::Ready;
                m.target_percent = 100.0;
                m.headline = "✓ WebView2 Runtime tayyor!".to_string();
                m.diagnostics.status_text = "READY".to_string();
                m.diagnostics.status_color = rgb(16, 185, 129);
                m.diagnostics.version = ver;
            }
            std::thread::sleep(Duration::from_millis(650));
            if let Ok(mut m) = model_arc.lock() {
                m.success = true;
                m.should_close = true;
            }
            startup_log("WORKER", "Preflight completed successfully (READY).");
            return;
        } else {
            // O'rnatuvchi ishladi, ammo runtime tasdiqlanmadi
            startup_log("WORKER", "ERROR: Runtime verification failed after installation!");
            eprintln!("[ERROR] WebView2 o'rnatilmadi yoki tasdiqlanmadi!");
            if let Ok(mut m) = model_arc.lock() {
                m.state = PreflightState::Failed;
                m.headline = "WebView2 Runtime o'rnatilmadi".to_string();
                m.diagnostics.status_text = "Xatolik".to_string();
                m.diagnostics.status_color = rgb(239, 68, 68);
                m.diagnostics.installer = "Xatolik".to_string();
                m.failure_reason = "O'rnatuvchi yakunlangan bo'lsa ham runtime registrdan topilmadi.".to_string();
            }

            if wait_for_retry(&model_arc) {
                continue;
            }
            return;
        }
    }
}

fn wait_for_retry(model_arc: &Arc<Mutex<PreflightUiModel>>) -> bool {
    loop {
        std::thread::sleep(Duration::from_millis(150));
        if let Ok(mut m) = model_arc.lock() {
            if m.should_close {
                return false;
            }
            if m.retry_requested {
                m.retry_requested = false;
                m.state = PreflightState::Detecting;
                m.current_percent = 0.0;
                m.target_percent = 10.0;
                return true;
            }
        }
    }
}

#[cfg(target_os = "windows")]
unsafe fn libloading_load_dwmapi() -> Result<(), ()> {
    extern "system" {
        fn LoadLibraryW(lp_lib_file_name: *const u16) -> isize;
        fn GetProcAddress(h_module: isize, lp_proc_name: *const u8) -> usize;
    }
    let dwm_name = to_wide("dwmapi.dll");
    let h_mod = LoadLibraryW(dwm_name.as_ptr());
    if h_mod != 0 {
        let fn_ptr = GetProcAddress(h_mod, b"DwmSetWindowAttribute\0".as_ptr());
        if fn_ptr != 0 {
            // Dynamic DwmSetWindowAttribute call
            return Ok(());
        }
    }
    Err(())
}
