#![windows_subsystem = "windows"]

use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

const APP_VERSION: &str = "v8.0.0";
static APP_CORE_BYTES: &[u8] = include_bytes!("../../../Misa/src-tauri/target/release/misa.exe");
static WEBVIEW2_BYTES: &[u8] = include_bytes!("../../../Misa/src-tauri/target/release/WebView2Loader.dll");

fn main() {
    let parent_dir = env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|d| d.to_path_buf()));

    // 1. If writable, extract WebView2Loader.dll next to this running launcher
    if let Some(ref parent) = parent_dir {
        let local_dll = parent.join("WebView2Loader.dll");
        if !local_dll.exists() || fs::metadata(&local_dll).map(|m| m.len()).unwrap_or(0) != WEBVIEW2_BYTES.len() as u64 {
            let _ = fs::write(&local_dll, WEBVIEW2_BYTES);
        }
    }

    // 2. Prepare isolated local runtime folder in %LOCALAPPDATA%\MisaAI\runtime\v8.0.0
    let local_app_data = env::var("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| env::temp_dir());
    let runtime_dir = local_app_data.join("MisaAI").join("runtime").join(APP_VERSION);
    let _ = fs::create_dir_all(&runtime_dir);

    let target_dll = runtime_dir.join("WebView2Loader.dll");
    let target_exe = runtime_dir.join("Misa-AI-Core.exe");

    // Write WebView2Loader.dll if missing or size differs
    if !target_dll.exists() || fs::metadata(&target_dll).map(|m| m.len()).unwrap_or(0) != WEBVIEW2_BYTES.len() as u64 {
        let _ = fs::write(&target_dll, WEBVIEW2_BYTES);
    }

    // Write core executable if missing or size differs
    if !target_exe.exists() || fs::metadata(&target_exe).map(|m| m.len()).unwrap_or(0) != APP_CORE_BYTES.len() as u64 {
        let _ = fs::write(&target_exe, APP_CORE_BYTES);
    }

    // 3. Determine best working directory (prefer portable parent containing backend/)
    let launch_dir = if let Some(ref parent) = parent_dir {
        if parent.join("backend").exists() {
            parent.clone()
        } else {
            runtime_dir.clone()
        }
    } else {
        runtime_dir.clone()
    };

    // 4. Launch the core Tauri executable (which hosts the full Supervisor)
    let args: Vec<String> = env::args().skip(1).collect();
    let mut cmd = Command::new(&target_exe);
    cmd.args(&args);
    cmd.current_dir(&launch_dir);
    if let Some(ref parent) = parent_dir {
        cmd.env("MISA_PORTABLE_DIR", parent);
    }

    let _ = cmd.spawn();
}
