// ========== src/components/UpdateModal.tsx ==========
// Misa AI v9.0.0 — Secure Auto-Update Ultra Glass Modal
// Ultra Glass Dark UI matching Misa's design system with Ed25519 & SHA-256 verification indicator.

import React, { useState, useEffect, useRef } from "react";
import {
  UpdateService,
  UpdateCheckResponse,
  UpdateState,
  UpdateStatusResponse,
} from "../services/updateService";

interface UpdateModalProps {
  isOpen: boolean;
  onClose: () => void;
  updateInfo: UpdateCheckResponse | null;
  onUpdateComplete?: () => void;
}

export const UpdateModal: React.FC<UpdateModalProps> = ({
  isOpen,
  onClose,
  updateInfo,
  onUpdateComplete,
}) => {
  const [currentState, setCurrentState] = useState<UpdateState>("UPDATE_AVAILABLE");
  const [downloadProgress, setDownloadProgress] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const pollingRef = useRef<number | null>(null);

  useEffect(() => {
    if (isOpen && updateInfo?.update_available) {
      setCurrentState("UPDATE_AVAILABLE");
      setDownloadProgress(0);
      setErrorMsg(null);
      setIsProcessing(false);
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isOpen, updateInfo]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isProcessing) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isProcessing, onClose]);

  const startStatusPolling = () => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = window.setInterval(async () => {
      try {
        const res: UpdateStatusResponse | null = await UpdateService.getStatus();
        if (!res) return;

        setCurrentState(res.state);
        if (res.data?.download_progress !== undefined) {
          setDownloadProgress(res.data.download_progress);
        }

        if (res.state === "STAGING" || res.state === "INSTALLING") {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setIsProcessing(false);
        } else if (res.state === "FAILED") {
          if (pollingRef.current) clearInterval(pollingRef.current);
          setErrorMsg(res.data?.error || "Yuklab olish yoki xavfsizlik tekshiruvi muvaffaqiyatsiz tugadi");
          setIsProcessing(false);
        }
      } catch (e: any) {
        console.debug("Status polling error", e);
      }
    }, 1000);
  };

  const handleStartUpdate = async () => {
    setIsProcessing(true);
    setErrorMsg(null);
    setCurrentState("DOWNLOADING");
    setDownloadProgress(5);

    startStatusPolling();

    const artifact = updateInfo?.artifacts?.[0];
    const res = await UpdateService.startDownload(artifact);

    if (!res.ok) {
      if (pollingRef.current) clearInterval(pollingRef.current);
      setCurrentState("FAILED");
      setErrorMsg(res.error || "Yangilanish yuklab olinmadi");
      setIsProcessing(false);
    }
  };

  const handleApplyUpdate = async () => {
    setIsProcessing(true);
    setErrorMsg(null);

    const res = await UpdateService.applyUpdate();
    if (!res.ok) {
      setErrorMsg(res.error || "Yangilanishni qo'llashda xatolik");
      setIsProcessing(false);
      return;
    }

    setCurrentState("SUCCESS");
    setIsProcessing(false);
    if (onUpdateComplete) onUpdateComplete();

    // Trigger restart notice
    setTimeout(() => {
      try {
        window.location.reload();
      } catch {}
    }, 2000);
  };

  if (!isOpen || !updateInfo) return null;

  const isMandatory = Boolean(updateInfo.mandatory);

  return (
    <div
      onClick={!isProcessing ? onClose : undefined}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        padding: "20px",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "480px",
          background: "linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.95))",
          border: "1px solid rgba(255, 255, 255, 0.12)",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 30px rgba(16, 185, 129, 0.15)",
          borderRadius: "16px",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "rgba(16, 185, 129, 0.15)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#10B981",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L15 8L21 9L17 14L18 20L12 17L6 20L7 14L3 9L9 8L12 2Z" />
              </svg>
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#F8FAFC" }}>
                Yangi Versiya Mavjud
              </h3>
              <span style={{ fontSize: 11.5, color: "#94A3B8" }}>
                Kanal: {updateInfo.target_version ? "Barqaror (Stable)" : "Rasmiy Reliz"}
              </span>
            </div>
          </div>

          {!isMandatory && currentState !== "DOWNLOADING" && currentState !== "VERIFYING" && (
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                color: "#94A3B8",
                cursor: "pointer",
                padding: 6,
                borderRadius: 6,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Version banner */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "rgba(0, 0, 0, 0.25)",
              padding: "14px 18px",
              borderRadius: 12,
              border: "1px solid rgba(255, 255, 255, 0.05)",
            }}
          >
            <div>
              <div style={{ fontSize: 11, color: "#64748B", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Joriy Versiya
              </div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#CBD5E1", marginTop: 2 }}>
                v{updateInfo.current_version}
              </div>
            </div>

            <div style={{ color: "#10B981" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </div>

            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 11, color: "#10B981", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Yangi Versiya
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#10B981", marginTop: 2 }}>
                v{updateInfo.target_version}
              </div>
            </div>
          </div>

          {/* Mandatory warning */}
          {isMandatory && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.1)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                padding: "10px 14px",
                borderRadius: 8,
                display: "flex",
                alignItems: "center",
                gap: 10,
                color: "#FCA5A5",
                fontSize: 12,
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>Ushbu yangilanish xavfsizlik va barqarorlik uchun majburiy (mandatory).</span>
            </div>
          )}

          {/* Release Notes */}
          {updateInfo.release_notes && updateInfo.release_notes.length > 0 && (
            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#94A3B8", marginBottom: 8 }}>
                O'zgarishlar va yangiliklar:
              </div>
              <div
                style={{
                  background: "rgba(0, 0, 0, 0.2)",
                  borderRadius: 8,
                  padding: "10px 14px",
                  maxHeight: "130px",
                  overflowY: "auto",
                  border: "1px solid rgba(255, 255, 255, 0.04)",
                }}
              >
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#E2E8F0", lineHeight: 1.6 }}>
                  {updateInfo.release_notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Security badge */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 11,
              color: "#64748B",
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>Ed25519 raqamli imzo va SHA-256 yaxlitligi tekshiriladi</span>
          </div>

          {/* Progress Section */}
          {(currentState === "DOWNLOADING" || currentState === "VERIFYING" || currentState === "STAGING") && (
            <div style={{ marginTop: 4 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#94A3B8", marginBottom: 6 }}>
                <span>
                  {currentState === "DOWNLOADING" && `Yuklab olinmoqda... ${downloadProgress}%`}
                  {currentState === "VERIFYING" && "Kriptografik tekshiruv (Ed25519)..."}
                  {currentState === "STAGING" && "O'rnatishga tayyorlanmoqda..."}
                </span>
                <span>{downloadProgress}%</span>
              </div>
              <div
                style={{
                  height: 6,
                  width: "100%",
                  background: "rgba(255, 255, 255, 0.1)",
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${downloadProgress}%`,
                    background: "linear-gradient(90deg, #10B981, #06B6D4)",
                    borderRadius: 3,
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMsg && (
            <div
              style={{
                background: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                padding: "10px 14px",
                borderRadius: 8,
                color: "#F87171",
                fontSize: 12,
              }}
            >
              {errorMsg}
            </div>
          )}

          {/* Success Message */}
          {currentState === "SUCCESS" && (
            <div
              style={{
                background: "rgba(16, 185, 129, 0.15)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                padding: "10px 14px",
                borderRadius: 8,
                color: "#34D399",
                fontSize: 12,
                textAlign: "center",
              }}
            >
              ✓ Muvaffaqiyatli yangilandi! Dastur qayta ishga tushirilmoqda...
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 12,
            background: "rgba(0, 0, 0, 0.15)",
          }}
        >
          {!isMandatory && currentState !== "SUCCESS" && (
            <button
              onClick={onClose}
              disabled={isProcessing}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                color: "#94A3B8",
                fontSize: 13,
                fontWeight: 500,
                cursor: isProcessing ? "not-allowed" : "pointer",
              }}
            >
              Keyinroq
            </button>
          )}

          {currentState === "UPDATE_AVAILABLE" && (
            <button
              onClick={handleStartUpdate}
              disabled={isProcessing}
              style={{
                padding: "8px 20px",
                borderRadius: 8,
                background: "linear-gradient(135deg, #10B981, #059669)",
                border: "none",
                color: "#FFFFFF",
                fontSize: 13,
                fontWeight: 600,
                cursor: isProcessing ? "not-allowed" : "pointer",
                boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)",
              }}
            >
              {isProcessing ? "Yuklanmoqda..." : "Yangilash"}
            </button>
          )}

          {(currentState === "STAGING" || currentState === "INSTALLING") && (
            <button
              onClick={handleApplyUpdate}
              disabled={isProcessing}
              style={{
                padding: "8px 20px",
                borderRadius: 8,
                background: "linear-gradient(135deg, #06B6D4, #0284C7)",
                border: "none",
                color: "#FFFFFF",
                fontSize: 13,
                fontWeight: 600,
                cursor: isProcessing ? "not-allowed" : "pointer",
              }}
            >
              Qayta Ishga Tushirish
            </button>
          )}

          {currentState === "FAILED" && (
            <button
              onClick={handleStartUpdate}
              style={{
                padding: "8px 20px",
                borderRadius: 8,
                background: "rgba(239, 68, 68, 0.8)",
                border: "none",
                color: "#FFFFFF",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Qayta Urinish
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
