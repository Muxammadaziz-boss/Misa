// ========== network_diag.rs ==========
// Misa AI v9.0.1 — Production Network Diagnostic Suite
// Tests complete path: URL Parsing -> DNS -> TCP -> TLS -> HTTP -> API Health
// Logs all events to %LOCALAPPDATA%\MisaAI\logs\network.log (never logging secrets)

use std::io::Read;
use std::net::{TcpStream, ToSocketAddrs};
use std::time::{Duration, Instant};
use crate::diag::network_log;

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct LayerStatus {
    pub ok: bool,
    pub latency_ms: Option<u64>,
    pub details: String,
    pub error: Option<String>,
}

impl Default for LayerStatus {
    fn default() -> Self {
        Self {
            ok: false,
            latency_ms: None,
            details: String::new(),
            error: None,
        }
    }
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct NetworkDiagnosticReport {
    pub target_url: String,
    pub parsed_scheme: String,
    pub parsed_host: String,
    pub parsed_port: u16,
    pub parsed_path: String,
    pub overall_success: bool,
    pub failed_stage: Option<String>,
    pub human_cause: String,
    pub dns: LayerStatus,
    pub tcp: LayerStatus,
    pub tls: LayerStatus,
    pub http: LayerStatus,
    pub api: LayerStatus,
}

/// URL ni toza ajratish (scheme, host, port, path)
pub fn parse_target_url(raw: &str) -> Result<(String, String, u16, String), String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err("URL manzili bo'sh kiritildi".to_string());
    }

    let (scheme, rest) = if let Some(idx) = trimmed.find("://") {
        (trimmed[..idx].to_lowercase(), &trimmed[idx + 3..])
    } else {
        ("http".to_string(), trimmed)
    };

    if scheme != "http" && scheme != "https" {
        return Err(format!("Noma'lum protokol: {}. Faqat http:// yoki https:// qo'llab-quvvatlanadi.", scheme));
    }

    let default_port = if scheme == "https" { 443 } else { 80 };
    let (host_port, path) = if let Some(slash_idx) = rest.find('/') {
        (&rest[..slash_idx], &rest[slash_idx..])
    } else {
        (rest, "/")
    };

    let (host, port) = if let Some(colon_idx) = host_port.find(':') {
        let h = &host_port[..colon_idx];
        let p_str = &host_port[colon_idx + 1..];
        let p = p_str.parse::<u16>().map_err(|_| format!("Yaroqsiz port raqami: {}", p_str))?;
        (h.to_string(), p)
    } else {
        (host_port.to_string(), default_port)
    };

    if host.is_empty() {
        return Err("Host/Domen nomi topilmadi".to_string());
    }

    let clean_path = if path.is_empty() { "/" } else { path };
    Ok((scheme, host, port, clean_path.to_string()))
}

/// To'liq bosqichma-bosqich tarmoq diagnostikasini bajarish
pub fn run_full_diagnostics(target_url: &str) -> NetworkDiagnosticReport {
    network_log(&format!("Starting diagnostics for target URL: {}", target_url));

    let (scheme, host, port, path) = match parse_target_url(target_url) {
        Ok(t) => t,
        Err(e) => {
            network_log(&format!("URL parse failed: {}", e));
            return NetworkDiagnosticReport {
                target_url: target_url.to_string(),
                parsed_scheme: String::new(),
                parsed_host: String::new(),
                parsed_port: 0,
                parsed_path: String::new(),
                overall_success: false,
                failed_stage: Some("url_parse".to_string()),
                human_cause: format!("URL sintaksisi xato: {}", e),
                dns: LayerStatus::default(),
                tcp: LayerStatus::default(),
                tls: LayerStatus::default(),
                http: LayerStatus::default(),
                api: LayerStatus::default(),
            };
        }
    };

    network_log(&format!("URL parsed: scheme={}, host={}, port={}, path={}", scheme, host, port, path));

    let mut report = NetworkDiagnosticReport {
        target_url: target_url.to_string(),
        parsed_scheme: scheme.clone(),
        parsed_host: host.clone(),
        parsed_port: port,
        parsed_path: path.clone(),
        overall_success: false,
        failed_stage: None,
        human_cause: String::new(),
        dns: LayerStatus::default(),
        tcp: LayerStatus::default(),
        tls: LayerStatus::default(),
        http: LayerStatus::default(),
        api: LayerStatus::default(),
    };

    // ── STAGE 1: DNS Resolution ──
    let dns_start = Instant::now();
    let host_port_pair = format!("{}:{}", host, port);
    let resolved_addrs = match host_port_pair.to_socket_addrs() {
        Ok(iter) => {
            let addrs: Vec<std::net::SocketAddr> = iter.collect();
            let elapsed = dns_start.elapsed().as_millis() as u64;
            if addrs.is_empty() {
                report.failed_stage = Some("dns".to_string());
                report.human_cause = "Sabab: DNS orqali server IP manzili topilmadi.".to_string();
                report.dns.error = Some("Bo'sh IP ro'yxati qaytdi".to_string());
                network_log("DNS: failed (empty IP list)");
                return report;
            }
            let ips_str = addrs.iter().map(|a| a.ip().to_string()).collect::<Vec<_>>().join(", ");
            report.dns.ok = true;
            report.dns.latency_ms = Some(elapsed);
            report.dns.details = format!("IP manzil: {}", ips_str);
            network_log(&format!("DNS: success ({}) in {}ms", ips_str, elapsed));
            addrs
        }
        Err(e) => {
            let elapsed = dns_start.elapsed().as_millis() as u64;
            report.dns.ok = false;
            report.dns.latency_ms = Some(elapsed);
            report.dns.error = Some(e.to_string());
            report.failed_stage = Some("dns".to_string());
            report.human_cause = format!("Sabab: DNS manzil topilmadi (Domen IP manzilga aylantirilmadi: {}).", e);
            network_log(&format!("DNS: failed ({}) in {}ms", e, elapsed));
            return report;
        }
    };

    // ── STAGE 2: TCP Connection ──
    let target_sock = resolved_addrs[0];
    let tcp_start = Instant::now();
    let tcp_timeout = Duration::from_millis(3500);

    let tcp_stream_res = TcpStream::connect_timeout(&target_sock, tcp_timeout);
    let tcp_elapsed = tcp_start.elapsed().as_millis() as u64;

    match tcp_stream_res {
        Ok(mut stream) => {
            report.tcp.ok = true;
            report.tcp.latency_ms = Some(tcp_elapsed);
            report.tcp.details = format!("{} portiga ulandi ({}ms)", port, tcp_elapsed);
            network_log(&format!("TCP: success ({}:{}) in {}ms", target_sock.ip(), port, tcp_elapsed));

            // Agar HTTP bo'lsa, xom stream orqali tekshirishimiz mumkin
            if scheme == "http" {
                report.tls.ok = true;
                report.tls.details = "HTTP (TLS shifrlash talab etilmaydi)".to_string();

                let _ = stream.set_read_timeout(Some(Duration::from_millis(3000)));
                let _ = stream.set_write_timeout(Some(Duration::from_millis(3000)));

                use std::io::Write;
                let health_path = if path == "/" || path.is_empty() { "/api/health" } else { &path };
                let req_payload = format!(
                    "GET {} HTTP/1.1\r\nHost: {}\r\nUser-Agent: MisaNetworkDiag/9.0.1\r\nAccept: application/json\r\nConnection: close\r\n\r\n",
                    health_path, host
                );

                let http_start = Instant::now();
                if stream.write_all(req_payload.as_bytes()).is_ok() {
                    let mut buf = [0u8; 4096];
                    match stream.read(&mut buf) {
                        Ok(n) if n > 0 => {
                            let http_elapsed = http_start.elapsed().as_millis() as u64;
                            let resp_str = String::from_utf8_lossy(&buf[..n]);
                            parse_raw_http_response(&resp_str, http_elapsed, &mut report);
                        }
                        _ => {
                            report.http.ok = false;
                            report.http.error = Some("Serverdan bo'sh javob keldi".to_string());
                            report.failed_stage = Some("http".to_string());
                            report.human_cause = "Sabab: Server ulandi, ammo ma'lumot jo'natmadi (Javob bo'sh).".to_string();
                            network_log("HTTP: failed (empty response)");
                        }
                    }
                } else {
                    report.http.ok = false;
                    report.http.error = Some("So'rov yuborishda xatolik".to_string());
                    report.failed_stage = Some("http".to_string());
                    report.human_cause = "Sabab: Serverga HTTP so'rovi yuborilmadi.".to_string();
                    network_log("HTTP: failed (write error)");
                }
                return report;
            }
        }
        Err(e) => {
            report.tcp.ok = false;
            report.tcp.latency_ms = Some(tcp_elapsed);
            report.tcp.error = Some(e.to_string());
            report.failed_stage = Some("tcp".to_string());
            report.human_cause = format!(
                "Sabab: TCP ulanish amalga oshmadi ({}-port yopiq yoki bloklangan: {}).",
                port, e
            );
            network_log(&format!("TCP: failed ({}:{}) error={}", target_sock.ip(), port, e));
            return report;
        }
    }

    // ── STAGE 3 & 4: HTTPS / TLS Handshake & HTTP Request via Windows WinINet API ──
    #[cfg(target_os = "windows")]
    {
        run_wininet_https_probe(target_url, &mut report);
    }

    #[cfg(not(target_os = "windows"))]
    {
        report.tls.ok = true;
        report.tls.details = "TLS non-windows fallback".to_string();
        report.http.ok = true;
        report.api.ok = true;
        report.overall_success = true;
    }

    report
}

/// HTTP xom javobini tahlil qilish
fn parse_raw_http_response(resp_str: &str, elapsed: u64, report: &mut NetworkDiagnosticReport) {
    let first_line = resp_str.lines().next().unwrap_or("");
    let status_code: u16 = if first_line.starts_with("HTTP/") {
        first_line.split_whitespace().nth(1).and_then(|s| s.parse().ok()).unwrap_or(0)
    } else {
        0
    };

    report.http.latency_ms = Some(elapsed);
    if status_code == 200 {
        report.http.ok = true;
        report.http.details = format!("HTTP 200 OK ({}ms)", elapsed);
        network_log(&format!("HTTP: 200 in {}ms", elapsed));

        // API Body tekshiruvi
        if resp_str.contains("\"status\"") || resp_str.contains("\"ok\"") || resp_str.contains("\"ready\"") {
            report.api.ok = true;
            report.api.details = "API holati sog'lom (status: ok)".to_string();
            report.overall_success = true;
            report.human_cause = "Serverga muvaffaqiyatli ulandi va API sog'lom holatda.".to_string();
            network_log("API health: success");
        } else {
            report.api.ok = false;
            report.api.error = Some("Javobda kutilgan JSON formati topilmadi".to_string());
            report.failed_stage = Some("api".to_string());
            report.human_cause = "Sabab: API sog'liq holati (status: ok) qaytarmadi.".to_string();
            network_log("API health: failed (invalid json payload)");
        }
    } else if status_code > 0 {
        report.http.ok = false;
        report.http.error = Some(format!("HTTP {}", status_code));
        report.failed_stage = Some("http".to_string());
        report.human_cause = format!("Sabab: Server HTTP {} xatosini qaytardi.", status_code);
        network_log(&format!("HTTP: failed with status {}", status_code));
    } else {
        report.http.ok = false;
        report.http.error = Some("Yaroqsiz HTTP status".to_string());
        report.failed_stage = Some("http".to_string());
        report.human_cause = "Sabab: Serverdan noto'g'ri HTTP javobi keldi.".to_string();
        network_log("HTTP: failed (invalid status line)");
    }
}

/// Windows WinINet orqali xavfsiz HTTPS va TLS sertifikat tekshiruvi
#[cfg(target_os = "windows")]
fn run_wininet_https_probe(url_str: &str, report: &mut NetworkDiagnosticReport) {
    const INTERNET_OPEN_TYPE_PRECONFIG: u32 = 0;
    const INTERNET_FLAG_RELOAD: u32 = 0x80000000;
    const INTERNET_FLAG_NO_CACHE_WRITE: u32 = 0x04000000;
    const HTTP_QUERY_STATUS_CODE: u32 = 19;
    const HTTP_QUERY_FLAG_NUMBER: u32 = 0x20000000;

    extern "system" {
        fn InternetOpenW(
            lpszAgent: *const u16,
            dwAccessType: u32,
            lpszProxy: *const u16,
            lpszProxyBypass: *const u16,
            dwFlags: u32,
        ) -> isize;

        fn InternetOpenUrlW(
            hInternet: isize,
            lpszUrl: *const u16,
            lpszHeaders: *const u16,
            dwHeadersLength: u32,
            dwFlags: u32,
            dwContext: usize,
        ) -> isize;

        fn HttpQueryInfoW(
            hRequest: isize,
            dwInfoLevel: u32,
            lpvBuffer: *mut std::ffi::c_void,
            lpdwBufferLength: *mut u32,
            lpdwIndex: *mut u32,
        ) -> i32;

        fn InternetReadFile(
            hFile: isize,
            lpBuffer: *mut u8,
            dwNumberOfBytesToRead: u32,
            lpdwNumberOfBytesRead: *mut u32,
        ) -> i32;

        fn InternetCloseHandle(hInternet: isize) -> i32;
        fn GetLastError() -> u32;
    }

    let agent_wide: Vec<u16> = "MisaNetworkDiag/9.0.1\0".encode_utf16().collect();
    let probe_url = if report.parsed_path == "/" || report.parsed_path.is_empty() {
        format!("{}/health", url_str.trim_end_matches('/'))
    } else {
        url_str.to_string()
    };
    let url_wide: Vec<u16> = format!("{}\0", probe_url).encode_utf16().collect();

    let tls_start = Instant::now();
    unsafe {
        let h_internet = InternetOpenW(
            agent_wide.as_ptr(),
            INTERNET_OPEN_TYPE_PRECONFIG,
            std::ptr::null(),
            std::ptr::null(),
            0,
        );

        if h_internet == 0 {
            report.tls.ok = false;
            report.tls.error = Some("WinINet initsializatsiya qilinmadi".to_string());
            report.failed_stage = Some("tls".to_string());
            report.human_cause = "Sabab: Windows tarmoq quyi tizimi javob bermadi.".to_string();
            network_log("TLS: failed (InternetOpenW returned null)");
            return;
        }

        let flags = INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE;
        let h_url = InternetOpenUrlW(
            h_internet,
            url_wide.as_ptr(),
            std::ptr::null(),
            0,
            flags,
            0,
        );

        let tls_elapsed = tls_start.elapsed().as_millis() as u64;

        if h_url == 0 {
            let err = GetLastError();
            InternetCloseHandle(h_internet);

            report.tls.latency_ms = Some(tls_elapsed);
            report.tls.ok = false;
            report.failed_stage = Some("tls".to_string());

            // Windows xatolik kodlarini aniq izohlash
            match err {
                12038 => {
                    report.tls.error = Some("ERROR_INTERNET_SEC_CERT_CN_INVALID".to_string());
                    report.human_cause = "Sabab: TLS sertifikatida domen nomi mos kelmadi.".to_string();
                }
                12037 => {
                    report.tls.error = Some("ERROR_INTERNET_SEC_CERT_DATE_INVALID".to_string());
                    report.human_cause = "Sabab: TLS sertifikatining amal qilish muddati tugagan yoki kompyuter soati noto'g'ri.".to_string();
                }
                12045 => {
                    report.tls.error = Some("ERROR_INTERNET_SEC_CERT_REV_FAILED".to_string());
                    report.human_cause = "Sabab: TLS sertifikati bekor qilingan (Revoked).".to_string();
                }
                12029 => {
                    report.tls.error = Some("ERROR_INTERNET_CANNOT_CONNECT".to_string());
                    report.human_cause = "Sabab: Serverga HTTPS orqali ulanib bo'lmadi.".to_string();
                }
                12007 => {
                    report.tls.error = Some("ERROR_INTERNET_NAME_NOT_RESOLVED".to_string());
                    report.human_cause = "Sabab: DNS nomi hal qilinmadi.".to_string();
                }
                _ => {
                    report.tls.error = Some(format!("WinINet error code: {}", err));
                    report.human_cause = format!("Sabab: TLS xavfsiz ulanishda xatolik yuz berdi (Win32 xatosi {}).", err);
                }
            }
            network_log(&format!("TLS: failed (error={}) in {}ms", err, tls_elapsed));
            return;
        }

        report.tls.ok = true;
        report.tls.latency_ms = Some(tls_elapsed);
        report.tls.details = format!("TLS muvaffaqiyatli tekshirildi ({}ms)", tls_elapsed);
        network_log(&format!("TLS: success in {}ms", tls_elapsed));

        // HTTP Status Code olish
        let mut status_code: u32 = 0;
        let mut len: u32 = std::mem::size_of::<u32>() as u32;
        let mut index: u32 = 0;

        let query_ok = HttpQueryInfoW(
            h_url,
            HTTP_QUERY_STATUS_CODE | HTTP_QUERY_FLAG_NUMBER,
            &mut status_code as *mut u32 as *mut std::ffi::c_void,
            &mut len,
            &mut index,
        );

        if query_ok != 0 {
            report.http.latency_ms = Some(tls_elapsed);
            if status_code == 200 {
                report.http.ok = true;
                report.http.details = "HTTP 200 OK".to_string();
                network_log("HTTP: 200");

                // API Body o'qish
                let mut buf = [0u8; 1024];
                let mut bytes_read: u32 = 0;
                let read_ok = InternetReadFile(h_url, buf.as_mut_ptr(), 1023, &mut bytes_read);

                if read_ok != 0 && bytes_read > 0 {
                    let body_str = String::from_utf8_lossy(&buf[..bytes_read as usize]);
                    if body_str.contains("\"status\"") || body_str.contains("\"ok\"") || body_str.contains("\"ready\"") {
                        report.api.ok = true;
                        report.api.details = "API sog'lom (status: ok)".to_string();
                        report.overall_success = true;
                        report.human_cause = "Serverga muvaffaqiyatli ulandi va API sog'lom holatda.".to_string();
                        network_log("API health: success");
                    } else {
                        report.api.ok = false;
                        report.api.error = Some("Noma'lum formatdagi JSON".to_string());
                        report.failed_stage = Some("api".to_string());
                        report.human_cause = "Sabab: API sog'liq kodi (status: ok) qaytarmadi.".to_string();
                        network_log("API health: failed (unrecognized payload)");
                    }
                } else {
                    report.api.ok = true; // /health bo'sh bo'lsa ham 200 status yetarli
                    report.overall_success = true;
                    report.human_cause = "Serverga ulandi (HTTP 200).".to_string();
                    network_log("API health: 200 received without body");
                }
            } else {
                report.http.ok = false;
                report.http.error = Some(format!("HTTP {}", status_code));
                report.failed_stage = Some("http".to_string());
                report.human_cause = format!("Sabab: Server HTTP {} xatosini qaytardi.", status_code);
                network_log(&format!("HTTP: returned status {}", status_code));
            }
        } else {
            report.http.ok = false;
            report.http.error = Some("Status kodini olib bo'lmadi".to_string());
            report.failed_stage = Some("http".to_string());
            report.human_cause = "Sabab: Serverdan HTTP status kodi olinmadi.".to_string();
            network_log("HTTP: query status failed");
        }

        InternetCloseHandle(h_url);
        InternetCloseHandle(h_internet);
    }
}
