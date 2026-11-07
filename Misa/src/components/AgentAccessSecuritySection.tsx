// ========== AgentAccessSecuritySection.tsx ==========
// Misa AI v9.0.0 — Full Agent Access & User Consent Security Center
// User-Controlled Agent Authority UI: Device Selection, Warning Modal, Re-Auth, Final Confirmation & Overrides

import React, { useState, useEffect } from "react";
import {
  backendService,
  AgentAccessStatus,
  SecurityWarningPayload,
} from "../services/backendService";

interface DeviceItem {
  id: string;
  device_id: string;
  name: string;
  hostname?: string;
  platform?: string;
  status: string;
}

export const AgentAccessSecuritySection: React.FC = () => {
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [accessStatus, setAccessStatus] = useState<AgentAccessStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [successMsg, setSuccessMsg] = useState<string>("");

  // Flow State
  const [showWarningModal, setShowWarningModal] = useState<boolean>(false);
  const [warningData, setWarningData] = useState<SecurityWarningPayload | null>(null);
  const [warningAcknowledged, setWarningAcknowledged] = useState<boolean>(false);

  const [showReauthModal, setShowReauthModal] = useState<boolean>(false);
  const [reauthPassword, setReauthPassword] = useState<string>("");
  const [reauthError, setReauthError] = useState<string>("");
  const [reauthLoading, setReauthLoading] = useState<boolean>(false);
  const [confirmationToken, setConfirmationToken] = useState<string>("");

  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [confirmLoading, setConfirmLoading] = useState<boolean>(false);

  // Manage permissions drawer/panel
  const [showPermissionsPanel, setShowPermissionsPanel] = useState<boolean>(false);

  // 1. Fetch devices list on mount
  useEffect(() => {
    loadDevices();
  }, []);

  // 2. Fetch access status whenever selected device changes
  useEffect(() => {
    if (selectedDeviceId) {
      loadAccessStatus(selectedDeviceId);
    }
  }, [selectedDeviceId]);

  const loadDevices = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const res = await backendService.getDevicesList();
      if (res.ok && res.devices && res.devices.length > 0) {
        setDevices(res.devices);
        setSelectedDeviceId(res.devices[0].device_id);
      } else {
        // Fallback default mock device if offline
        const fallbackDev: DeviceItem = {
          id: "local_pc",
          device_id: "MyPC@local",
          name: "My Windows PC",
          hostname: "Misa-PC",
          platform: "windows",
          status: "online",
        };
        setDevices([fallbackDev]);
        setSelectedDeviceId(fallbackDev.device_id);
      }
    } catch (e: any) {
      setErrorMsg("Qurilmalarni yuklashda xatolik: " + String(e));
    } finally {
      setLoading(false);
    }
  };

  const loadAccessStatus = async (devId: string) => {
    try {
      const res = await backendService.getAgentAccess(devId);
      if (res.ok && res.access) {
        setAccessStatus(res.access);
      }
    } catch (e: any) {
      console.error("Access status yuklashda xatolik:", e);
    }
  };

  // Step 1: User clicks "Enable Full Access" -> request warning
  const handleStartEnable = async () => {
    if (!selectedDeviceId) return;
    setErrorMsg("");
    setSuccessMsg("");
    setWarningAcknowledged(false);

    try {
      const res = await backendService.requestAgentAccessWarning(selectedDeviceId);
      const warningPayload = res.warning || (res as any).data;
      if (res.ok && warningPayload) {
        setWarningData(warningPayload);
        setShowWarningModal(true);
      } else {
        setErrorMsg(res.error || res.message || "Aktivatsiyani boshlab bo'lmadi");
      }
    } catch (e: any) {
      setErrorMsg("Xatolik: " + String(e));
    }
  };

  // Step 2: Warning acknowledged -> go to Re-auth
  const handleAcknowledgeWarning = async () => {
    if (!warningData || !warningAcknowledged) return;
    try {
      const res = await backendService.acknowledgeAgentAccessWarning(
        selectedDeviceId,
        warningData.warning_token
      );
      if (res.ok) {
        setShowWarningModal(false);
        setReauthPassword("");
        setReauthError("");
        setShowReauthModal(true);
      } else {
        setErrorMsg(res.error || res.message || "Ogohlantirishni tasdiqlab bo'lmadi");
      }
    } catch (e: any) {
      setErrorMsg("Xatolik: " + String(e));
    }
  };

  // Step 3: Re-authentication verify -> go to Final Confirm
  const handleVerifyReauth = async () => {
    if (!warningData || !reauthPassword.trim()) {
      setReauthError("Parol yoki autentifikatsiya kodi kiritilishi shart");
      return;
    }
    setReauthLoading(true);
    setReauthError("");

    try {
      const res = await backendService.reauthenticateAgentAccess(
        selectedDeviceId,
        warningData.challenge_id,
        reauthPassword
      );
      if (res.ok && res.confirmation_token) {
        setConfirmationToken(res.confirmation_token);
        setShowReauthModal(false);
        setShowConfirmModal(true);
      } else {
        setReauthError(res.error || res.message || "Qayta autentifikatsiyadan o'tib bo'lmadi");
      }
    } catch (e: any) {
      setReauthError("Xatolik: " + String(e));
    } finally {
      setReauthLoading(false);
    }
  };

  // Step 4: Final Confirmation -> Activate Full Access
  const handleFinalConfirm = async () => {
    if (!confirmationToken) return;
    setConfirmLoading(true);
    try {
      const res = await backendService.confirmAgentAccess(selectedDeviceId, confirmationToken);
      if (res.ok) {
        setShowConfirmModal(false);
        setSuccessMsg("🎉 Full Agent Access muvaffaqiyatli faollashtirildi!");
        loadAccessStatus(selectedDeviceId);
      } else {
        setErrorMsg(res.error || res.message || "Faollashtirishda xatolik");
      }
    } catch (e: any) {
      setErrorMsg("Xatolik: " + String(e));
    } finally {
      setConfirmLoading(false);
    }
  };

  // Disable Full Access
  const handleDisableAccess = async () => {
    if (!selectedDeviceId) return;
    if (!window.confirm("Full Agent Access ni o'chirib, cheklangan (LIMITED) rejimga qaytarishni xohlaysizmi?")) {
      return;
    }
    try {
      const res = await backendService.disableAgentAccess(selectedDeviceId);
      if (res.ok) {
        setSuccessMsg("Full Agent Access o'chirildi (LIMITED holatga qaytarildi).");
        loadAccessStatus(selectedDeviceId);
      } else {
        setErrorMsg(res.error || res.message || "O'chirishda xatolik");
      }
    } catch (e: any) {
      setErrorMsg("Xatolik: " + String(e));
    }
  };

  // Emergency Revoke All Access
  const handleEmergencyRevoke = async () => {
    if (!selectedDeviceId) return;
    const confirmPrompt = window.prompt(
      "DIQQAT: Barcha agent vakolatlarini bekor qilish, navbatdagi buyruqlarni to'xtatish va masofaviy sessiyalarni o'chirish uchun 'REVOKE' deb yozing:"
    );
    if (confirmPrompt !== "REVOKE") {
      return;
    }

    try {
      const res = await backendService.emergencyRevokeAgentAccess(selectedDeviceId);
      if (res.ok) {
        setSuccessMsg("🚨 Favqulodda barcha agent vakolatlari bekor qilindi!");
        loadAccessStatus(selectedDeviceId);
      } else {
        setErrorMsg(res.error || res.message || "Bekor qilishda xatolik");
      }
    } catch (e: any) {
      setErrorMsg("Xatolik: " + String(e));
    }
  };

  // Toggle individual permission override
  const handleTogglePermission = async (permissionId: string, currentVal: boolean) => {
    try {
      const res = await backendService.overrideAgentPermission(
        selectedDeviceId,
        permissionId,
        !currentVal
      );
      if (res.ok) {
        loadAccessStatus(selectedDeviceId);
      }
    } catch (e: any) {
      console.error("Permission o'zgartirishda xatolik:", e);
    }
  };

  const selectedDevice = devices.find((d) => d.device_id === selectedDeviceId);
  const isFull = accessStatus?.is_full_access ?? false;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Messages */}
      {errorMsg && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: 8,
            padding: "12px 16px",
            color: "#FCA5A5",
            fontSize: 13,
          }}
        >
          {errorMsg}
        </div>
      )}
      {successMsg && (
        <div
          style={{
            background: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            borderRadius: 8,
            padding: "12px 16px",
            color: "#6EE7B7",
            fontSize: 13,
          }}
        >
          {successMsg}
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            padding: "40px 0",
            color: "#94A3B8",
            fontSize: 14,
          }}
        >
          Qurilmalar yuklanmoqda...
        </div>
      )}

      {/* Device Selection & Status */}
      <div
        style={{
          background: "rgba(255, 255, 255, 0.03)",
          border: "1px solid var(--border-subtle, rgba(255,255,255,0.07))",
          borderRadius: 12,
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "#F8FAFC" }}>
              Tanlangan Kompyuter (Selected Device)
            </h3>
            <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "#94A3B8" }}>
              Full Agent Access faqat tanlangan muayyan qurilmaga biriktiriladi (Device-Scoped).
            </p>
          </div>
          {devices.length > 1 ? (
            <select
              value={selectedDeviceId}
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              style={{
                background: "rgba(0,0,0,0.3)",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: 8,
                padding: "8px 12px",
                color: "#F8FAFC",
                fontSize: 13,
                outline: "none",
              }}
            >
              {devices.map((d) => (
                <option key={d.device_id} value={d.device_id}>
                  {d.name} ({d.status})
                </option>
              ))}
            </select>
          ) : (
            <span
              style={{
                fontSize: 12,
                padding: "4px 10px",
                borderRadius: 8,
                background: "rgba(255,255,255,0.06)",
                color: "#CBD5E1",
              }}
            >
              {selectedDevice ? selectedDevice.name : "Local PC"}
            </span>
          )}
        </div>

        {/* Access Level Card */}
        <div
          style={{
            background: isFull ? "rgba(16, 185, 129, 0.08)" : "rgba(234, 179, 8, 0.08)",
            border: isFull ? "1px solid rgba(16, 185, 129, 0.25)" : "1px solid rgba(234, 179, 8, 0.25)",
            borderRadius: 10,
            padding: "16px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ fontSize: 24 }}>{isFull ? "🟢" : "🟡"}</span>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: isFull ? "#34D399" : "#FBBF24" }}>
                  {isFull ? "FULL AGENT ACCESS" : "LIMITED ACCESS"}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    padding: "2px 8px",
                    borderRadius: 12,
                    background: isFull ? "rgba(16, 185, 129, 0.2)" : "rgba(234, 179, 8, 0.2)",
                    color: isFull ? "#6EE7B7" : "#FDE68A",
                  }}
                >
                  {accessStatus ? `${accessStatus.permissions_granted} / ${accessStatus.total_supported_permissions} ruxsatlar` : "Standart"}
                </span>
              </div>
              <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "#94A3B8" }}>
                {isFull
                  ? "Misa ushbu kompyuterda barcha tasdiqlangan va qo'llab-quvvatlanuvchi agent vositalaridan foydalanishi mumkin."
                  : "Misa faqat oldindan ruxsat berilgan minimal va xavfsiz vositalar bilan cheklangan."}
              </p>
            </div>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            {isFull ? (
              <>
                <button
                  onClick={() => setShowPermissionsPanel(!showPermissionsPanel)}
                  style={{
                    background: "rgba(255, 255, 255, 0.08)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: 8,
                    padding: "8px 14px",
                    color: "#F8FAFC",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  Ruxsatlarni Boshqarish
                </button>
                <button
                  onClick={handleDisableAccess}
                  style={{
                    background: "rgba(234, 179, 8, 0.15)",
                    border: "1px solid rgba(234, 179, 8, 0.3)",
                    borderRadius: 8,
                    padding: "8px 14px",
                    color: "#FDE68A",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  Full Access'ni O'chirish
                </button>
              </>
            ) : (
              <button
                onClick={handleStartEnable}
                style={{
                  background: "linear-gradient(135deg, #10B981 0%, #059669 100%)",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 18px",
                  color: "#FFFFFF",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  boxShadow: "0 2px 10px rgba(16, 185, 129, 0.3)",
                }}
              >
                Enable Full Agent Access
              </button>
            )}
          </div>
        </div>

        {/* Policy & Timestamp metadata */}
        {accessStatus && (
          <div style={{ display: "flex", gap: 20, fontSize: 11, color: "#64748B" }}>
            <span>Siyosat: {accessStatus.policy_version}</span>
            {accessStatus.enabled_at && (
              <span>Yoqilgan vaqt: {new Date(accessStatus.enabled_at * 1000).toLocaleString()}</span>
            )}
          </div>
        )}
      </div>

      {/* Permissions Management Panel */}
      {showPermissionsPanel && (
        <div
          style={{
            background: "rgba(255, 255, 255, 0.02)",
            border: "1px solid var(--border-subtle, rgba(255,255,255,0.07))",
            borderRadius: 12,
            padding: 20,
          }}
        >
          <h4 style={{ margin: "0 0 12px 0", fontSize: 14, fontWeight: 600, color: "#F8FAFC" }}>
            Alohida Ruxsatlarni Sozlash (Permission Overrides)
          </h4>
          <p style={{ margin: "0 0 16px 0", fontSize: 12, color: "#94A3B8" }}>
            Full Agent Access yoqilgan bo'lsa ham, alohida ruxsatni o'chirib qo'yishingiz mumkin (masalan: Fayllarni o'chirish). O'chirilgan ruxsat ustuvorlikka ega.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[
              { id: "system.status", name: "Kompyuter holati", cat: "SYSTEM", risk: "LOW" },
              { id: "system.info", name: "Tizim ma'lumotlari (CPU/RAM)", cat: "SYSTEM", risk: "LOW" },
              { id: "system.screenshot", name: "Ekran tasviri (Screenshot)", cat: "SYSTEM", risk: "LOW" },
              { id: "app.list", name: "Dasturlar ro'yxati", cat: "APPS", risk: "LOW" },
              { id: "app.launch", name: "Dasturni ochish", cat: "APPS", risk: "MED" },
              { id: "app.close", name: "Dasturni yopish", cat: "APPS", risk: "MED" },
              { id: "file.list", name: "Fayllar ro'yxati", cat: "FILES", risk: "LOW" },
              { id: "file.read", name: "Faylni o'qish", cat: "FILES", risk: "MED" },
              { id: "file.write", name: "Fayl yozish", cat: "FILES", risk: "MED" },
              { id: "file.delete", name: "Faylni o'chirish", cat: "FILES", risk: "HIGH" },
              { id: "network.info", name: "Tarmoq holati", cat: "NET", risk: "LOW" },
              { id: "power.restart", name: "Qayta yuklash (Restart)", cat: "POWER", risk: "HIGH" },
              { id: "power.shutdown", name: "O'chirish (Shutdown)", cat: "POWER", risk: "HIGH" },
              { id: "power.sleep", name: "Uyqu rejimi (Sleep)", cat: "POWER", risk: "HIGH" },
              { id: "power.wake", name: "Uyg'otish (WoL)", cat: "POWER", risk: "LOW" },
            ].map((p) => {
              const isOverriddenFalse = accessStatus?.overrides?.[p.id] === false;
              const isGranted = isFull ? !isOverriddenFalse : false;

              return (
                <div
                  key={p.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "rgba(0,0,0,0.2)",
                    borderRadius: 6,
                    border: "1px solid rgba(255,255,255,0.05)",
                  }}
                >
                  <div>
                    <span style={{ fontSize: 13, color: "#E2E8F0" }}>{p.name}</span>
                    <span style={{ marginLeft: 6, fontSize: 10, color: p.risk === "HIGH" ? "#F87171" : "#94A3B8" }}>
                      [{p.risk}]
                    </span>
                  </div>
                  <button
                    onClick={() => handleTogglePermission(p.id, isGranted)}
                    style={{
                      background: isGranted ? "rgba(16, 185, 129, 0.2)" : "rgba(255,255,255,0.06)",
                      border: isGranted ? "1px solid #10B981" : "1px solid rgba(255,255,255,0.15)",
                      borderRadius: 4,
                      padding: "3px 8px",
                      color: isGranted ? "#34D399" : "#94A3B8",
                      fontSize: 11,
                      cursor: "pointer",
                    }}
                  >
                    {isGranted ? "ON" : "OFF"}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Danger Zone */}
      <div
        style={{
          background: "rgba(239, 68, 68, 0.05)",
          border: "1px solid rgba(239, 68, 68, 0.2)",
          borderRadius: 12,
          padding: 20,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <h4 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "#F87171" }}>
            Xavfli Hudud (Danger Zone)
          </h4>
          <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "#94A3B8" }}>
            Shubhali faoliyat sezilsa, barcha agent vakolatlarini, navbatdagi buyruqlarni va masofaviy ulanishlarni zudlik bilan to'xtating.
          </p>
        </div>
        <button
          onClick={handleEmergencyRevoke}
          style={{
            background: "rgba(239, 68, 68, 0.2)",
            border: "1px solid #EF4444",
            borderRadius: 8,
            padding: "9px 18px",
            color: "#FCA5A5",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Revoke All Agent Access
        </button>
      </div>

      {/* ============================================================ */}
      {/* MODAL 1: SECURITY WARNING MODAL */}
      {/* ============================================================ */}
      {showWarningModal && warningData && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "#0F172A",
              border: "1px solid rgba(234, 179, 8, 0.4)",
              borderRadius: 16,
              maxWidth: 580,
              width: "100%",
              padding: 28,
              boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}>⚠️</span>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#FBBF24" }}>
                XAVFSIZLIK OGOHLANTIRISHI: FULL AGENT ACCESS
              </h3>
            </div>

            <div
              style={{
                background: "rgba(0, 0, 0, 0.3)",
                borderRadius: 8,
                padding: 16,
                fontSize: 13,
                color: "#E2E8F0",
                lineHeight: 1.6,
                whiteSpace: "pre-line",
                maxHeight: 280,
                overflowY: "auto",
              }}
            >
              {warningData.warning_text}
            </div>

            <label
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                fontSize: 13,
                color: "#F8FAFC",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={warningAcknowledged}
                onChange={(e) => setWarningAcknowledged(e.target.checked)}
                style={{ marginTop: 3 }}
              />
              <span>
                Men ushbu xavfsizlik ogohlantirishini o'qidim va Full Agent Access berish oqibatlarini tushundim.
              </span>
            </label>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
              <button
                onClick={() => setShowWarningModal(false)}
                style={{
                  background: "rgba(255, 255, 255, 0.08)",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 18px",
                  color: "#CBD5E1",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                disabled={!warningAcknowledged}
                onClick={handleAcknowledgeWarning}
                style={{
                  background: warningAcknowledged ? "#EAB308" : "rgba(234, 179, 8, 0.3)",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 20px",
                  color: "#0F172A",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: warningAcknowledged ? "pointer" : "not-allowed",
                }}
              >
                Davom etish →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL 2: RE-AUTHENTICATION MODAL */}
      {/* ============================================================ */}
      {showReauthModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "#0F172A",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              borderRadius: 16,
              maxWidth: 460,
              width: "100%",
              padding: 28,
              boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
              display: "flex",
              flexDirection: "column",
              gap: 18,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 22 }}>🔐</span>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: "#F8FAFC" }}>
                QAYTA AUTENTIFIKATSIYA (RE-AUTH)
              </h3>
            </div>

            <p style={{ margin: 0, fontSize: 13, color: "#94A3B8" }}>
              Full Agent Access xavfsizlik darajasini oshirish maqsadida shaxsingizni tasdiqlang. Parol yoki sessiya tasdig'ini kiriting.
            </p>

            {reauthError && (
              <div
                style={{
                  background: "rgba(239, 68, 68, 0.15)",
                  color: "#F87171",
                  padding: "8px 12px",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              >
                {reauthError}
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ fontSize: 12, color: "#CBD5E1" }}>Hisob Paroli</label>
              <input
                type="password"
                value={reauthPassword}
                onChange={(e) => setReauthPassword(e.target.value)}
                placeholder="Parolni kiriting"
                className="misa-glass-input"
                style={{
                  padding: "10px 14px",
                  borderRadius: "12px",
                  fontSize: "14px",
                }}
              />
              <span style={{ fontSize: 11, color: "#64748B" }}>
                Parolingiz backend serveriga saqlanmaydi va uzatilmaydi.
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
              <button
                onClick={() => setShowReauthModal(false)}
                style={{
                  background: "rgba(255, 255, 255, 0.08)",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 18px",
                  color: "#CBD5E1",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                disabled={reauthLoading}
                onClick={handleVerifyReauth}
                style={{
                  background: "#10B981",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 20px",
                  color: "#FFFFFF",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: reauthLoading ? "wait" : "pointer",
                }}
              >
                {reauthLoading ? "Tekshirilmoqda..." : "Tasdiqlash →"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL 3: FINAL CONFIRMATION MODAL */}
      {/* ============================================================ */}
      {showConfirmModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "#0F172A",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              borderRadius: 16,
              maxWidth: 480,
              width: "100%",
              padding: 28,
              boxShadow: "0 20px 40px rgba(0,0,0,0.6)",
              display: "flex",
              flexDirection: "column",
              gap: 18,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 24 }}>🛡️</span>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#34D399" }}>
                FULL AGENT ACCESS'NI YOQISH
              </h3>
            </div>

            <div
              style={{
                background: "rgba(0,0,0,0.25)",
                borderRadius: 10,
                padding: 16,
                fontSize: 13,
                display: "flex",
                flexDirection: "column",
                gap: 8,
                color: "#E2E8F0",
              }}
            >
              <div>
                <strong>Qurilma:</strong> {selectedDevice ? selectedDevice.name : "Windows PC"}
              </div>
              <div>
                <strong>Vakolat:</strong> FULL AGENT ACCESS
              </div>
              <div>
                <strong>Imkoniyatlar:</strong> 15 ta standart agent amallari
              </div>
            </div>

            <p style={{ margin: 0, fontSize: 12, color: "#94A3B8", lineHeight: 1.5 }}>
              Misa ushbu qurilmada siz yoqqan agent capability'laridan foydalanishi mumkin. Bu vakolatni keyinchalik istalgan vaqtda Security bo'limidan bekor qilishingiz mumkin.
            </p>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
              <button
                onClick={() => setShowConfirmModal(false)}
                style={{
                  background: "rgba(255, 255, 255, 0.08)",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 18px",
                  color: "#CBD5E1",
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Orqaga
              </button>
              <button
                disabled={confirmLoading}
                onClick={handleFinalConfirm}
                style={{
                  background: "linear-gradient(135deg, #10B981 0%, #059669 100%)",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 22px",
                  color: "#FFFFFF",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: confirmLoading ? "wait" : "pointer",
                  boxShadow: "0 4px 15px rgba(16, 185, 129, 0.4)",
                }}
              >
                {confirmLoading ? "Faollashtirilmoqda..." : "FULL ACCESS'NI YOQISH"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
