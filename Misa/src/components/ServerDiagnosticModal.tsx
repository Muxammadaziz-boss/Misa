// ========== ServerDiagnosticModal.tsx ==========
// Misa AI v9.0.1 — Ultra Glass Server Diagnostic & Connectivity Controller
// Real-time multi-layer status: URL -> DNS -> TCP -> TLS -> HTTP -> API Health
// Safe execution with exponential backoff & zero token leakage

import React, { useState, useEffect } from "react";
import {
  NetworkDiagnosticService,
  NetworkDiagnosticReport,
} from "../services/networkDiagnosticService";
import {
  resolveApiBase,
  refreshApiBaseUrls,
  backendService,
} from "../services/backendService";
import {
  AlertTriangleIcon,
  CheckIcon,
  ShieldIcon,
} from "./icons/Icons";

interface ServerDiagnosticModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  onServerChanged?: () => void;
}

export const ServerDiagnosticModal: React.FC<ServerDiagnosticModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onServerChanged,
}) => {
  const [report, setReport] = useState<NetworkDiagnosticReport | null>(null);
  const [isChecking, setIsChecking] = useState<boolean>(false);
  const [attemptInfo, setAttemptInfo] = useState<string | null>(null);
  const [serverMode, setServerMode] = useState<"cloud" | "local" | "custom">(() =>
    NetworkDiagnosticService.getCurrentServerMode()
  );
  const [customInput, setCustomInput] = useState<string>(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      return window.localStorage.getItem("misa_backend_url") || "";
    }
    return "";
  });
  const [currentUrl, setCurrentUrl] = useState<string>(() => resolveApiBase());

  const executeCheck = async (urlToCheck?: string) => {
    setIsChecking(true);
    setAttemptInfo("Diagnostika tekshiruvi boshlanmoqda...");

    try {
      const res = await NetworkDiagnosticService.runWithExponentialBackoff(
        urlToCheck || resolveApiBase(),
        (att, max, delay) => {
          if (delay > 0) {
            setAttemptInfo(`Qayta urinish: ${att}/${max} (${delay / 1000}s kutilmoqda)...`);
          } else {
            setAttemptInfo(`Tekshirilmoqda: 1/${max}...`);
          }
        }
      );
      setReport(res);
      setAttemptInfo(null);
      if (res.overall_success) {
        backendService.reconnect();
        if (onSuccess) onSuccess();
        if (onServerChanged) onServerChanged();
      }
    } catch {
      setAttemptInfo(null);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      setCurrentUrl(resolveApiBase());
      executeCheck();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectMode = (mode: "cloud" | "local" | "custom") => {
    setServerMode(mode);
    if (mode === "cloud") {
      const url = NetworkDiagnosticService.setServerConfiguration("cloud");
      refreshApiBaseUrls();
      setCurrentUrl(url);
      if (onServerChanged) onServerChanged();
      executeCheck(url);
    } else if (mode === "local") {
      const url = NetworkDiagnosticService.setServerConfiguration("local");
      refreshApiBaseUrls();
      setCurrentUrl(url);
      if (onServerChanged) onServerChanged();
      executeCheck(url);
    }
  };

  const handleApplyCustom = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customInput.trim()) return;
    const clean = customInput.trim();
    const url = NetworkDiagnosticService.setServerConfiguration("custom", clean);
    refreshApiBaseUrls();
    setCurrentUrl(url);
    if (onServerChanged) onServerChanged();
    executeCheck(url);
  };

  const hostDisplay = (() => {
    try {
      return new URL(currentUrl).host;
    } catch {
      return currentUrl;
    }
  })();

  const renderLayerBadge = (ok: boolean, latency?: number, details?: string) => {
    if (isChecking && !report) {
      return (
        <span style={{ color: "#A78BFA", fontSize: "12px", display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: "#A78BFA", animation: "pulse 1.2s infinite" }} />
          Tekshirilmoqda
        </span>
      );
    }
    if (ok) {
      return (
        <span style={{ color: "#34D399", fontSize: "12px", display: "flex", alignItems: "center", gap: "6px", fontWeight: 600 }}>
          <CheckIcon size={14} color="#34D399" />
          Muvaffaqiyatli {latency !== undefined ? `(${latency}ms)` : ""}
        </span>
      );
    }
    return (
      <span
        style={{
          color: "#F87171",
          fontSize: "12px",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          fontWeight: 600,
          maxWidth: "260px",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
        title={details}
      >
        <AlertTriangleIcon size={14} color="#F87171" />
        Xatolik {details ? `(${details})` : ""}
      </span>
    );
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        backgroundColor: "rgba(2, 6, 14, 0.78)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "680px",
          background: "linear-gradient(145deg, rgba(17, 24, 39, 0.94), rgba(10, 15, 29, 0.98))",
          border: "1px solid rgba(192, 76, 253, 0.28)",
          borderRadius: "18px",
          boxShadow: "0 24px 64px rgba(0, 0, 0, 0.65), 0 0 32px rgba(192, 76, 253, 0.12)",
          padding: "24px 28px",
          color: "#F3F4F6",
          fontFamily: "var(--font-family, sans-serif)",
          display: "flex",
          flexDirection: "column",
          gap: "18px",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", paddingBottom: "14px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                background: "rgba(192, 76, 253, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid rgba(192, 76, 253, 0.35)",
              }}
            >
              <ShieldIcon size={20} color="#C04CFD" />
            </div>
            <div>
              <div style={{ fontSize: "16px", fontWeight: 700, letterSpacing: "-0.01em" }}>
                Misa AI — Tarmoq & Server Diagnostikasi
              </div>
              <div style={{ fontSize: "12px", color: "#9CA3AF" }}>
                To'liq tarmoq zanjiri: DNS → TCP → TLS → HTTP → API Health ({hostDisplay})
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "#9CA3AF",
              fontSize: "20px",
              cursor: "pointer",
              padding: "4px 8px",
              borderRadius: "6px",
            }}
          >
            ✕
          </button>
        </div>

        {/* Server Selection Tabs */}
        <div>
          <div style={{ fontSize: "12px", color: "#9CA3AF", marginBottom: "8px", fontWeight: 600 }}>
            SERVER MANZILI VA REJIMI:
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
            <button
              onClick={() => handleSelectMode("cloud")}
              style={{
                padding: "10px 12px",
                borderRadius: "10px",
                border: serverMode === "cloud" ? "1.5px solid #C04CFD" : "1px solid rgba(255, 255, 255, 0.1)",
                background: serverMode === "cloud" ? "rgba(192, 76, 253, 0.18)" : "rgba(255, 255, 255, 0.03)",
                color: serverMode === "cloud" ? "#F5F0FF" : "#9CA3AF",
                cursor: "pointer",
                fontSize: "12.5px",
                fontWeight: serverMode === "cloud" ? 600 : 500,
                textAlign: "left",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
                transition: "all 0.2s ease",
              }}
            >
              <span>● Masofaviy Bulut</span>
              <span style={{ fontSize: "10.5px", opacity: 0.7 }}>misa.up.railway.app</span>
            </button>

            <button
              onClick={() => handleSelectMode("local")}
              style={{
                padding: "10px 12px",
                borderRadius: "10px",
                border: serverMode === "local" ? "1.5px solid #C04CFD" : "1px solid rgba(255, 255, 255, 0.1)",
                background: serverMode === "local" ? "rgba(192, 76, 253, 0.18)" : "rgba(255, 255, 255, 0.03)",
                color: serverMode === "local" ? "#F5F0FF" : "#9CA3AF",
                cursor: "pointer",
                fontSize: "12.5px",
                fontWeight: serverMode === "local" ? 600 : 500,
                textAlign: "left",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
                transition: "all 0.2s ease",
              }}
            >
              <span>● Mahalliy Backend</span>
              <span style={{ fontSize: "10.5px", opacity: 0.7 }}>127.0.0.1:18420</span>
            </button>

            <button
              onClick={() => handleSelectMode("custom")}
              style={{
                padding: "10px 12px",
                borderRadius: "10px",
                border: serverMode === "custom" ? "1.5px solid #C04CFD" : "1px solid rgba(255, 255, 255, 0.1)",
                background: serverMode === "custom" ? "rgba(192, 76, 253, 0.18)" : "rgba(255, 255, 255, 0.03)",
                color: serverMode === "custom" ? "#F5F0FF" : "#9CA3AF",
                cursor: "pointer",
                fontSize: "12.5px",
                fontWeight: serverMode === "custom" ? 600 : 500,
                textAlign: "left",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
                transition: "all 0.2s ease",
              }}
            >
              <span>● Maxsus Server</span>
              <span style={{ fontSize: "10.5px", opacity: 0.7 }}>O'zingiz kiriting</span>
            </button>
          </div>

          {serverMode === "custom" && (
            <form onSubmit={handleApplyCustom} style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
              <input
                type="text"
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                placeholder="https://sizning-serveringiz.com"
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  borderRadius: "8px",
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid rgba(192, 76, 253, 0.3)",
                  color: "#FFF",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
              <button
                type="submit"
                style={{
                  padding: "8px 16px",
                  borderRadius: "8px",
                  background: "linear-gradient(135deg, #A855F7, #7C3AED)",
                  border: "none",
                  color: "#FFF",
                  fontWeight: 600,
                  fontSize: "12.5px",
                  cursor: "pointer",
                }}
              >
                Saqlash
              </button>
            </form>
          )}
        </div>

        {/* Current Target & Status Summary */}
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "10px",
            background: "rgba(255, 255, 255, 0.03)",
            border: "1px solid rgba(255, 255, 255, 0.06)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontSize: "11px", color: "#9CA3AF" }}>Hozirgi server domeni:</div>
            <div style={{ fontSize: "14px", fontWeight: 700, color: "#C04CFD" }}>
              {currentUrl}
            </div>
          </div>
          <div>
            {isChecking ? (
              <span style={{ fontSize: "12px", color: "#A78BFA", fontWeight: 600 }}>
                ● Tekshirilmoqda...
              </span>
            ) : report?.overall_success ? (
              <span style={{ fontSize: "12px", color: "#34D399", fontWeight: 700 }}>
                ● Aloqa o'rnatildi (Sog'lom)
              </span>
            ) : (
              <span style={{ fontSize: "12px", color: "#F87171", fontWeight: 700 }}>
                ✕ Ulanib bo'lmadi
              </span>
            )}
          </div>
        </div>

        {/* Diagnostic Checklist */}
        <div
          style={{
            background: "rgba(0, 0, 0, 0.25)",
            border: "1px solid rgba(255, 255, 255, 0.06)",
            borderRadius: "12px",
            padding: "12px 16px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {/* DNS */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
            <span style={{ color: "#D1D5DB" }}>1. DNS Manzil Qidiruvi:</span>
            {renderLayerBadge(report?.dns.ok || false, report?.dns.latency_ms, report?.dns.details)}
          </div>

          {/* TCP */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
            <span style={{ color: "#D1D5DB" }}>2. TCP Port Ulanishi:</span>
            {renderLayerBadge(report?.tcp.ok || false, report?.tcp.latency_ms, report?.tcp.details)}
          </div>

          {/* TLS */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
            <span style={{ color: "#D1D5DB" }}>3. TLS / HTTPS Shifrlash:</span>
            {renderLayerBadge(report?.tls.ok || false, report?.tls.latency_ms, report?.tls.details)}
          </div>

          {/* HTTP */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
            <span style={{ color: "#D1D5DB" }}>4. HTTP Protokoli:</span>
            {renderLayerBadge(report?.http.ok || false, report?.http.latency_ms, report?.http.details)}
          </div>

          {/* API */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
            <span style={{ color: "#D1D5DB" }}>5. API Sog'liq Holati (/api/health):</span>
            {renderLayerBadge(report?.api.ok || false, report?.api.latency_ms, report?.api.details)}
          </div>
        </div>

        {/* Detailed Explanation / Cause */}
        {report && !report.overall_success && (
          <div
            style={{
              padding: "12px 16px",
              borderRadius: "10px",
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#FCA5A5",
              fontSize: "13px",
              lineHeight: 1.5,
            }}
          >
            <div style={{ fontWeight: 700, marginBottom: "4px" }}>
              Xatolik sababi:
            </div>
            <div>{report.human_cause || "Server bilan aloqa o'rnatilmadi."}</div>
            {serverMode === "local" && (
              <div style={{ marginTop: "6px", fontSize: "11.5px", color: "#FCD34D" }}>
                Maslahat: Agar boshqa kompyuterda bo'lsangiz, yuqoridagi <b>"Masofaviy Bulut"</b> tugmasini tanlang.
              </div>
            )}
          </div>
        )}

        {attemptInfo && (
          <div style={{ fontSize: "12px", color: "#A78BFA", fontStyle: "italic", textAlign: "center" }}>
            {attemptInfo}
          </div>
        )}

        {/* Footer Actions */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "8px" }}>
          <div style={{ fontSize: "11px", color: "#6B7280" }}>
            Log: %LOCALAPPDATA%\MisaAI\logs\network.log
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={() => executeCheck()}
              disabled={isChecking}
              style={{
                padding: "8px 18px",
                borderRadius: "8px",
                background: "linear-gradient(135deg, #C04CFD, #7928CA)",
                border: "none",
                color: "#FFF",
                fontWeight: 600,
                fontSize: "13px",
                cursor: isChecking ? "wait" : "pointer",
                opacity: isChecking ? 0.7 : 1,
              }}
            >
              {isChecking ? "Tekshirilmoqda..." : "Qayta tekshirish"}
            </button>
            <button
              onClick={onClose}
              style={{
                padding: "8px 14px",
                borderRadius: "8px",
                background: "rgba(255, 255, 255, 0.08)",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                color: "#E5E7EB",
                fontWeight: 500,
                fontSize: "13px",
                cursor: "pointer",
              }}
            >
              Yopish
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
