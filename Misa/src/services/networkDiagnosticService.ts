// ========== networkDiagnosticService.ts ==========
// Misa AI v9.0.1 — Production Network Diagnostic & Health Suite
// Multi-layer inspection: URL Parsing -> DNS -> TCP -> TLS -> HTTP -> API Health
// Safe execution with exponential backoff & zero token leakage

import { resolveApiBase, PRODUCTION_API_URL, LOCAL_BACKEND_URL } from "./backendService";

export interface LayerStatus {
  ok: boolean;
  latency_ms?: number;
  details: string;
  error?: string;
}

export interface NetworkDiagnosticReport {
  target_url: string;
  parsed_scheme: string;
  parsed_host: string;
  parsed_port: number;
  parsed_path: string;
  overall_success: boolean;
  failed_stage?: "url_parse" | "dns" | "tcp" | "tls" | "http" | "api";
  human_cause: string;
  dns: LayerStatus;
  tcp: LayerStatus;
  tls: LayerStatus;
  http: LayerStatus;
  api: LayerStatus;
}

export class NetworkDiagnosticService {
  private static isTauri(): boolean {
    if (typeof window === "undefined") return false;
    const w = window as any;
    return Boolean(w.__TAURI_INTERNALS__ || w.__TAURI__ || w.__TAURI_METADATA__);
  }

  /**
   * Log xabarini xavfsiz tarzda %LOCALAPPDATA%\MisaAI\logs\network.log ga yuborish
   */
  public static async logNetwork(msg: string): Promise<void> {
    try {
      if (this.isTauri()) {
        const { invoke } = await import("@tauri-apps/api/core");
        await invoke("append_network_log", { message: msg });
      } else {
        console.log(`[NETWORK] ${msg}`);
      }
    } catch {
      // Silent logging fallback
    }
  }

  /**
   * Bir martalik qatlamli diagnostika tekshiruvini amalga oshirish
   */
  public static async runDiagnostics(targetUrl?: string): Promise<NetworkDiagnosticReport> {
    const effectiveUrl = (targetUrl || resolveApiBase()).trim();

    // 1. Agar Tauri ish stoli muhitida bo'lsa, mahalliy Rust network_diag modulini chaqiramiz
    if (this.isTauri()) {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const report = await invoke<NetworkDiagnosticReport>("network_diagnostic_check", {
          url: effectiveUrl,
        });
        return report;
      } catch (err: any) {
        console.warn("Tauri network_diagnostic_check fallback:", err);
      }
    }

    // 2. Web / Brauzer fallback diagnostikasi
    return this.runBrowserDiagnostics(effectiveUrl);
  }

  /**
   * Eksponentsial oraliq bilan boshqariladigan qayta urinish (Exponential Backoff Retry)
   * 1-urinish: Darhol
   * 2-urinish: 1 soniyadan keyin
   * 3-urinish: 2 soniyadan keyin
   * 4-urinish: 5 soniyadan keyin
   */
  public static async runWithExponentialBackoff(
    targetUrl?: string,
    onAttempt?: (attempt: number, max: number, delayMs: number) => void
  ): Promise<NetworkDiagnosticReport> {
    const delays = [0, 1000, 2000, 5000];
    let lastReport: NetworkDiagnosticReport | null = null;

    for (let i = 0; i < delays.length; i++) {
      const delay = delays[i];
      if (delay > 0) {
        if (onAttempt) onAttempt(i + 1, delays.length, delay);
        await new Promise((r) => setTimeout(r, delay));
      } else {
        if (onAttempt) onAttempt(1, delays.length, 0);
      }

      lastReport = await this.runDiagnostics(targetUrl);
      if (lastReport.overall_success) {
        await this.logNetwork(`Connected successfully on attempt ${i + 1}/${delays.length}`);
        return lastReport;
      }
    }

    return (
      lastReport || {
        target_url: targetUrl || resolveApiBase(),
        parsed_scheme: "https",
        parsed_host: "unknown",
        parsed_port: 443,
        parsed_path: "/",
        overall_success: false,
        failed_stage: "tcp",
        human_cause: "Belgilangan urinishlar ichida serverga ulanib bo'lmadi.",
        dns: { ok: false, details: "" },
        tcp: { ok: false, details: "" },
        tls: { ok: false, details: "" },
        http: { ok: false, details: "" },
        api: { ok: false, details: "" },
      }
    );
  }

  /**
   * Brauzer Fetch orqali diagnostika
   */
  private static async runBrowserDiagnostics(urlStr: string): Promise<NetworkDiagnosticReport> {
    let scheme = "https";
    let host = "misa.up.railway.app";
    let port = 443;
    let path = "/api/health";

    try {
      const parsed = new URL(urlStr);
      scheme = parsed.protocol.replace(":", "");
      host = parsed.hostname;
      port = parsed.port ? parseInt(parsed.port, 10) : scheme === "https" ? 443 : 80;
      path = parsed.pathname || "/api/health";
    } catch (e: any) {
      return {
        target_url: urlStr,
        parsed_scheme: scheme,
        parsed_host: host,
        parsed_port: port,
        parsed_path: path,
        overall_success: false,
        failed_stage: "url_parse",
        human_cause: `URL sintaksisi xato: ${e.message}`,
        dns: { ok: false, details: "" },
        tcp: { ok: false, details: "" },
        tls: { ok: false, details: "" },
        http: { ok: false, details: "" },
        api: { ok: false, details: "" },
      };
    }

    const report: NetworkDiagnosticReport = {
      target_url: urlStr,
      parsed_scheme: scheme,
      parsed_host: host,
      parsed_port: port,
      parsed_path: path,
      overall_success: false,
      human_cause: "",
      dns: { ok: true, details: `Domen: ${host}` },
      tcp: { ok: true, details: `Port: ${port}` },
      tls: { ok: scheme === "https", details: scheme === "https" ? "HTTPS" : "HTTP" },
      http: { ok: false, details: "" },
      api: { ok: false, details: "" },
    };

    const t0 = performance.now();
    try {
      const probeUrl = urlStr.endsWith("/api/health") || urlStr.endsWith("/health")
        ? urlStr
        : `${urlStr.replace(/\/$/, "")}/api/health`;

      const res = await fetch(probeUrl, {
        method: "GET",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });

      const elapsed = Math.round(performance.now() - t0);
      report.http.latency_ms = elapsed;

      if (res.ok) {
        report.http.ok = true;
        report.http.details = `HTTP ${res.status} OK (${elapsed}ms)`;

        const data = await res.json().catch(() => null);
        if (data && (data.status === "ok" || data.ready === true || data.app === "Misa AI")) {
          report.api.ok = true;
          report.api.details = "API holati sog'lom (status: ok)";
          report.overall_success = true;
          report.human_cause = "Serverga muvaffaqiyatli ulandi va API sog'lom holatda.";
        } else {
          report.api.ok = false;
          report.failed_stage = "api";
          report.human_cause = "Sabab: API kutilgan sog'lom formatda javob bermadi.";
        }
      } else {
        report.http.ok = false;
        report.http.error = `HTTP ${res.status}`;
        report.failed_stage = "http";
        report.human_cause = `Sabab: Server HTTP ${res.status} xatosini qaytardi.`;
      }
    } catch (err: any) {
      const elapsed = Math.round(performance.now() - t0);
      report.http.latency_ms = elapsed;
      report.tcp.ok = false;
      report.failed_stage = "tcp";
      report.human_cause = `Sabab: Serverga ulanib bo'lmadi (${host}:${port} ulanish rad etildi yoki internet mavjud emas).`;
    }

    return report;
  }

  /**
   * Server manzilini sozlash (Bulutli, Lokal yoki Maxsus)
   */
  public static setServerConfiguration(mode: "cloud" | "local" | "custom", customUrl?: string): string {
    if (typeof window === "undefined" || !window.localStorage) return PRODUCTION_API_URL;

    if (mode === "cloud") {
      window.localStorage.setItem("misa_server_mode", "cloud");
      window.localStorage.removeItem("misa_backend_url");
      return PRODUCTION_API_URL;
    } else if (mode === "local") {
      window.localStorage.setItem("misa_server_mode", "local");
      window.localStorage.removeItem("misa_backend_url");
      return LOCAL_BACKEND_URL;
    } else if (mode === "custom" && customUrl) {
      const clean = customUrl.trim().replace(/\/$/, "");
      window.localStorage.setItem("misa_server_mode", "custom");
      window.localStorage.setItem("misa_backend_url", clean);
      return clean;
    }

    return PRODUCTION_API_URL;
  }

  /**
   * Hozirgi saqlangan server rejimini aniqlash
   */
  public static getCurrentServerMode(): "cloud" | "local" | "custom" {
    if (typeof window === "undefined" || !window.localStorage) return "cloud";
    const custom = window.localStorage.getItem("misa_backend_url");
    if (custom) return "custom";
    const mode = window.localStorage.getItem("misa_server_mode");
    if (mode === "local") return "local";
    return "cloud";
  }
}
