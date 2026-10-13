// ========== diag.rs ==========
// Misa AI v9.0.1 — Structured Startup & Crash Diagnostic Logger
// Traces every startup lifecycle transition to %LOCALAPPDATA%\MisaAI\logs\startup.log

use std::fs::{create_dir_all, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;

static LOG_MUTEX: Mutex<()> = Mutex::new(());

#[repr(C)]
struct SYSTEMTIME {
    w_year: u16,
    w_month: u16,
    w_day_of_week: u16,
    w_day: u16,
    w_hour: u16,
    w_minute: u16,
    w_second: u16,
    w_milliseconds: u16,
}

#[cfg(target_os = "windows")]
extern "system" {
    fn GetLocalTime(lp_system_time: *mut SYSTEMTIME);
    fn GetCurrentProcessId() -> u32;
    fn GetCurrentThreadId() -> u32;
}

pub fn get_timestamp() -> String {
    #[cfg(target_os = "windows")]
    unsafe {
        let mut st: SYSTEMTIME = std::mem::zeroed();
        GetLocalTime(&mut st);
        format!(
            "{:04}-{:02}-{:02} {:02}:{:02}:{:02}.{:03}",
            st.w_year, st.w_month, st.w_day, st.w_hour, st.w_minute, st.w_second, st.w_milliseconds
        )
    }
    #[cfg(not(target_os = "windows"))]
    {
        "2026-10-13 00:00:00.000".to_string()
    }
}

pub fn get_log_dir() -> PathBuf {
    if let Ok(local_app_data) = std::env::var("LOCALAPPDATA") {
        PathBuf::from(local_app_data).join("MisaAI").join("logs")
    } else {
        std::env::temp_dir().join("MisaAI").join("logs")
    }
}

pub fn startup_log(tag: &str, msg: &str) {
    let _lock = LOG_MUTEX.lock();
    let ts = get_timestamp();
    let line = format!("{} [{}] {}\n", ts, tag, msg);

    // Konsolga chiqarish (agar biriktirilgan bo'lsa)
    print!("{}", line);

    let log_dir = get_log_dir();
    let _ = create_dir_all(&log_dir);
    let log_file = log_dir.join("startup.log");

    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_file) {
        let _ = file.write_all(line.as_bytes());
        let _ = file.flush();
    }
}

pub fn crash_log(stage: &str, details: &str) {
    let _lock = LOG_MUTEX.lock();
    let ts = get_timestamp();
    let pid = current_pid();
    let tid = current_tid();

    let line = format!("{} [CRASH] stage={} PID={} TID={} details={}\n", ts, stage, pid, tid, details);
    eprint!("{}", line);

    let log_dir = get_log_dir();
    let _ = create_dir_all(&log_dir);

    // crash.log ga yozish
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_dir.join("crash.log")) {
        let _ = file.write_all(line.as_bytes());
        let _ = file.flush();
    }

    // startup.log ga ham yozish
    if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_dir.join("startup.log")) {
        let _ = file.write_all(line.as_bytes());
        let _ = file.flush();
    }
}

pub fn current_pid() -> u32 {
    #[cfg(target_os = "windows")]
    unsafe { GetCurrentProcessId() }
    #[cfg(not(target_os = "windows"))]
    0
}

pub fn current_tid() -> u32 {
    #[cfg(target_os = "windows")]
    unsafe { GetCurrentThreadId() }
    #[cfg(not(target_os = "windows"))]
    0
}

#[cfg(target_os = "windows")]
#[allow(non_snake_case)]
#[repr(C)]
pub struct EXCEPTION_RECORD {
    pub ExceptionCode: u32,
    pub ExceptionFlags: u32,
    pub ExceptionRecord: *mut EXCEPTION_RECORD,
    pub ExceptionAddress: *mut std::ffi::c_void,
    pub NumberParameters: u32,
    pub ExceptionInformation: [usize; 15],
}

#[cfg(target_os = "windows")]
#[allow(non_snake_case)]
#[repr(C)]
pub struct EXCEPTION_POINTERS {
    pub ExceptionRecord: *mut EXCEPTION_RECORD,
    pub ContextRecord: *mut std::ffi::c_void,
}

#[cfg(target_os = "windows")]
unsafe extern "system" fn unhandled_exception_handler(pointers: *mut EXCEPTION_POINTERS) -> i32 {
    if !pointers.is_null() && !(*pointers).ExceptionRecord.is_null() {
        let rec = &*(*pointers).ExceptionRecord;
        let details = format!(
            "SEH Exception code=0x{:08X} at address={:p}",
            rec.ExceptionCode, rec.ExceptionAddress
        );
        crash_log("SEH_NATIVE_CRASH", &details);
    } else {
        crash_log("SEH_NATIVE_CRASH", "Unknown exception with null pointers");
    }
    1 // EXCEPTION_EXECUTE_HANDLER
}

pub fn install_crash_handlers() {
    #[cfg(target_os = "windows")]
    unsafe {
        extern "system" {
            fn SetUnhandledExceptionFilter(
                filter: Option<unsafe extern "system" fn(*mut EXCEPTION_POINTERS) -> i32>,
            ) -> isize;
        }
        SetUnhandledExceptionFilter(Some(unhandled_exception_handler));
    }

    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        let payload = if let Some(s) = info.payload().downcast_ref::<&str>() {
            s.to_string()
        } else if let Some(s) = info.payload().downcast_ref::<String>() {
            s.clone()
        } else {
            "Box<Any> unknown panic payload".to_string()
        };
        let location = info
            .location()
            .map(|l| format!("{}:{}:{}", l.file(), l.line(), l.column()))
            .unwrap_or_else(|| "unknown location".to_string());
        let details = format!("PANIC at {} payload: {}", location, payload);
        crash_log("RUST_PANIC", &details);
        default_hook(info);
    }));
}
