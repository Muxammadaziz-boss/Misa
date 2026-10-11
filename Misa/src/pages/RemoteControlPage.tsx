// ========== RemoteControlPage.tsx ==========
// Misa AI v9.0.0 — Masofaviy Boshqaruv & Ruxsatlar Markazi
// Telegram Bot ↔ Misa Remote Gateway ↔ User Linking ↔ Permission Center ↔ PC Agent

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  RemoteControlIcon,
  ShieldIcon,
  RefreshIcon,
  CheckIcon,
  CopyIcon,
  TrashIcon,
  CpuIcon,
  GlobeIcon,
  ClockIcon,
  SearchIcon,
  KeyIcon,
} from "../components/icons/Icons";
import {
  backendService,
  RemoteDevice,
  PermissionDefinitionItem,
  RemoteAuditItem,
} from "../services/backendService";

interface RemoteControlPageProps {
  onNavigateHome: () => void;
}

export const RemoteControlPage: React.FC<RemoteControlPageProps> = () => {
  const [devices, setDevices] = useState<RemoteDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("local_pc");
  const [permissions, setPermissions] = useState<Record<string, boolean>>({});
  const [catalog, setCatalog] = useState<Record<string, PermissionDefinitionItem[]>>({});
  const [auditEvents, setAuditEvents] = useState<RemoteAuditItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [togglingPerm, setTogglingPerm] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Telegram pairing states
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number>(0);
  const [copied, setCopied] = useState<boolean>(false);
  const [isGeneratingCode, setIsGeneratingCode] = useState<boolean>(false);

  // Toast notification
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimeoutRef = useRef<any>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    toastTimeoutRef.current = setTimeout(() => setToastMessage(null), 3500);
  };

  // 1. Fetch devices and audit log
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const devRes = await backendService.getRemoteDevices();
      if (devRes.ok && devRes.devices.length > 0) {
        setDevices(devRes.devices);
        const currentSelected = devRes.devices.some((d) => d.device_id === selectedDeviceId)
          ? selectedDeviceId
          : devRes.devices[0].device_id;
        setSelectedDeviceId(currentSelected);
        await loadPermissions(currentSelected);
      }
      const auditRes = await backendService.getRemoteAudit();
      if (auditRes.ok && auditRes.events) {
        setAuditEvents(auditRes.events);
      }
    } catch (e) {
      console.error("Failed to load remote control data", e);
    } finally {
      setLoading(false);
    }
  }, [selectedDeviceId]);

  // 2. Fetch permissions for device
  const loadPermissions = async (deviceId: string) => {
    try {
      const res = await backendService.getDevicePermissions(deviceId);
      if (res.ok) {
        setPermissions(res.profile?.permissions || {});
        setCatalog(res.catalog || {});
      }
    } catch (e) {
      console.error("Failed to fetch permissions", e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Real-time WebSocket event listener
  useEffect(() => {
    const unsub = backendService.onRemoteEvent((event) => {
      if (event.type === "permission_changed") {
        if (event.data?.device_id === selectedDeviceId && event.data?.profile?.permissions) {
          setPermissions(event.data.profile.permissions);
          showToast("Ruxsatlar yangilandi (jonli sinxronizatsiya)");
        }
      } else if (event.type === "device_paired" || event.type === "device_unpaired") {
        loadData();
      }
    });
    return () => unsub();
  }, [selectedDeviceId, loadData]);

  // Countdown timer for pairing code
  useEffect(() => {
    if (countdown <= 0) {
      setPairingCode(null);
      return;
    }
    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  // Handle Generate Pairing Code
  const handleGenerateCode = async () => {
    setIsGeneratingCode(true);
    try {
      const res = await backendService.generatePairingCode(selectedDeviceId);
      if (res.ok && res.code) {
        setPairingCode(res.code);
        setCountdown(res.expires_in || 300);
        showToast("Bir martalik ulanish kodi hosil qilindi");
      } else {
        showToast(res.error || "Kod hosil qilib bo'lmadi");
      }
    } catch (err: any) {
      showToast("Xatolik yuz berdi");
    } finally {
      setIsGeneratingCode(false);
    }
  };

  // Handle Copy Code
  const handleCopyCode = () => {
    if (!pairingCode) return;
    navigator.clipboard.writeText(`/pair ${pairingCode}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    showToast("Nusxalandi! Telegram botga yuborishingiz mumkin");
  };

  // Handle Unpair
  const handleUnpair = async () => {
    if (!window.confirm("Haqiqatan ham Telegram hisobini bu qurilmadan uzmoqchimisiz?")) return;
    try {
      const res = await backendService.unpairTelegram(selectedDeviceId);
      if (res.ok) {
        showToast("Telegram hisobi muvaffaqiyatli uzildi");
        loadData();
      }
    } catch (e) {
      showToast("Uzishda xatolik yuz berdi");
    }
  };

  // Handle Session Lock
  const handleLockSession = async () => {
    try {
      const res = await backendService.lockRemoteSession(selectedDeviceId);
      if (res.ok) {
        showToast("Masofaviy sessiya qulflandi");
      }
    } catch (e) {
      showToast("Sessiyani qulflashda xatolik");
    }
  };

  // Handle Session Logout
  const handleLogoutSession = async () => {
    if (!window.confirm("Barcha faol masofaviy sessiyalarni yopishni tasdiqlaysizmi?")) return;
    try {
      const res = await backendService.logoutRemoteSession(selectedDeviceId);
      if (res.ok) {
        showToast("Masofaviy sessiya to'liq yakunlandi");
      }
    } catch (e) {
      showToast("Chiqishda xatolik");
    }
  };

  // Handle Permission Toggle
  const handleTogglePermission = async (permId: string) => {
    const nextVal = !permissions[permId];
    const prevVal = permissions[permId];

    // Optimistic UI update
    setPermissions((prev) => ({ ...prev, [permId]: nextVal }));
    setTogglingPerm(permId);

    try {
      const newPerms = { ...permissions, [permId]: nextVal };
      const res = await backendService.updateDevicePermissions(selectedDeviceId, newPerms);
      if (res.ok && res.profile?.permissions) {
        setPermissions(res.profile.permissions);
        showToast(nextVal ? `✅ ${permId} ruxsat berildi` : `🔒 ${permId} ruxsat bekor qilindi`);
      } else {
        // Rollback on failure
        setPermissions((prev) => ({ ...prev, [permId]: prevVal }));
        showToast("Ruxsatni yangilashda xatolik");
      }
    } catch (e) {
      setPermissions((prev) => ({ ...prev, [permId]: prevVal }));
      showToast("Server bilan aloqa uzildi");
    } finally {
      setTogglingPerm(null);
    }
  };

  // Flattened permission items with category filter and search
  const allPermItems: PermissionDefinitionItem[] = Object.values(catalog).flat();

  const filteredPermItems = allPermItems.filter((item) => {
    const matchesCat = selectedCategory === "all" || item.category === selectedCategory;
    const matchesSearch =
      searchQuery.trim() === "" ||
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const selectedDevice = devices.find((d) => d.device_id === selectedDeviceId) || devices[0];

  const getDangerBadge = (level: string) => {
    switch (level) {
      case "critical":
        return { label: "Kritik", bg: "rgba(239, 68, 68, 0.15)", text: "#EF4444", border: "rgba(239, 68, 68, 0.3)" };
      case "high":
        return { label: "Yuqori xavf", bg: "rgba(245, 158, 11, 0.15)", text: "#F59E0B", border: "rgba(245, 158, 11, 0.3)" };
      case "medium":
        return { label: "O'rtacha", bg: "rgba(59, 130, 246, 0.15)", text: "#3B82F6", border: "rgba(59, 130, 246, 0.3)" };
      default:
        return { label: "Xavfsiz", bg: "rgba(16, 185, 129, 0.15)", text: "#10B981", border: "rgba(16, 185, 129, 0.3)" };
    }
  };

  return (
    <div
      style={{
        flex: 1,
        width: "100%",
        height: "100%",
        overflowY: "auto",
        boxSizing: "border-box",
        padding: "24px 32px 48px 32px",
        maxWidth: "1380px",
        margin: "0 auto",
        color: "var(--text, #F8FAFC)",
        fontFamily: "var(--font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
      }}
    >
      {/* Toast Alert */}
      {toastMessage && (
        <div
          style={{
            position: "fixed",
            bottom: "28px",
            right: "28px",
            background: "rgba(15, 23, 42, 0.95)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(16, 185, 129, 0.35)",
            borderRadius: "12px",
            padding: "14px 20px",
            color: "#F8FAFC",
            fontSize: "14px",
            fontWeight: 500,
            boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            animation: "fadeIn 0.2s ease-out",
          }}
        >
          <span style={{ color: "#10B981" }}>●</span>
          {toastMessage}
        </div>
      )}

      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: "28px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "6px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(6, 78, 59, 0.3))",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#10B981",
                border: "1px solid rgba(16, 185, 129, 0.3)",
              }}
            >
              <RemoteControlIcon size={22} color="#10B981" />
            </div>
            <div>
              <h1 style={{ fontSize: "24px", fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>
                Masofaviy Boshqaruv & Ruxsatlar Markazi
              </h1>
              <p style={{ margin: 0, fontSize: "13px", color: "var(--text-muted, #94A3B8)" }}>
                Telegram Bot, Misa User App va Windows PC Agent xavfsiz boshqaruv tizimi
              </p>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => loadData()}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "9px 16px",
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "10px",
              color: "var(--text, #F8FAFC)",
              fontSize: "13px",
              fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <RefreshIcon size={14} color="#94A3B8" />
            Yangilash
          </button>
        </div>
      </div>

      {/* Grid: Left: Devices & Pairing, Right: Session Controls */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "20px",
          marginBottom: "28px",
        }}
      >
        {/* Qurilma Ma'lumotlari Card */}
        <div
          style={{
            background: "var(--card-bg, rgba(255, 255, 255, 0.03))",
            backdropFilter: "blur(12px)",
            border: "1px solid var(--border, rgba(255, 255, 255, 0.08))",
            borderRadius: "16px",
            padding: "20px",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <CpuIcon size={18} color="#10B981" />
              <h2 style={{ fontSize: "15px", fontWeight: 600, margin: 0 }}>Faol Windows PC Agent</h2>
            </div>
            {selectedDevice && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  padding: "3px 10px",
                  borderRadius: "20px",
                  background: selectedDevice.state === "online" ? "rgba(16, 185, 129, 0.15)" : "rgba(148, 163, 184, 0.15)",
                  color: selectedDevice.state === "online" ? "#10B981" : "#94A3B8",
                  border: `1px solid ${selectedDevice.state === "online" ? "rgba(16, 185, 129, 0.3)" : "rgba(148, 163, 184, 0.3)"}`,
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: selectedDevice.state === "online" ? "#10B981" : "#94A3B8",
                  }}
                />
                {selectedDevice.state.toUpperCase()}
              </span>
            )}
          </div>

          {selectedDevice ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <span style={{ color: "var(--text-muted, #94A3B8)" }}>Hostname:</span>
                <span style={{ fontWeight: 600, fontFamily: "monospace" }}>{selectedDevice.hostname}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <span style={{ color: "var(--text-muted, #94A3B8)" }}>Operatsion Tizim:</span>
                <span>{selectedDevice.os}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <span style={{ color: "var(--text-muted, #94A3B8)" }}>IP & MAC:</span>
                <span style={{ fontFamily: "monospace" }}>{selectedDevice.local_ip || "127.0.0.1"} ({selectedDevice.mac_address || "N/A"})</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0" }}>
                <span style={{ color: "var(--text-muted, #94A3B8)" }}>Agent Versiyasi:</span>
                <span style={{ color: "#10B981", fontWeight: 600 }}>v{selectedDevice.agent_version || "9.0.1"}</span>
              </div>
            </div>
          ) : (
            <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted, #94A3B8)" }}>
              Hech qanday qurilma ulanmagan
            </div>
          )}
        </div>

        {/* Telegram Bog'lash (Pairing) Card */}
        <div
          style={{
            background: "var(--card-bg, rgba(255, 255, 255, 0.03))",
            backdropFilter: "blur(12px)",
            border: "1px solid var(--border, rgba(255, 255, 255, 0.08))",
            borderRadius: "16px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <GlobeIcon size={18} color="#38BDF8" />
                <h2 style={{ fontSize: "15px", fontWeight: 600, margin: 0 }}>Telegram Hisobini Bog'lash</h2>
              </div>
              {selectedDevice?.is_paired ? (
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "3px 10px",
                    borderRadius: "20px",
                    background: "rgba(16, 185, 129, 0.15)",
                    color: "#10B981",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                  }}
                >
                  ✓ Bog'langan
                </span>
              ) : (
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    padding: "3px 10px",
                    borderRadius: "20px",
                    background: "rgba(245, 158, 11, 0.15)",
                    color: "#F59E0B",
                    border: "1px solid rgba(245, 158, 11, 0.3)",
                  }}
                >
                  Bog'lanmagan
                </span>
              )}
            </div>

            <p style={{ fontSize: "13px", color: "var(--text-muted, #94A3B8)", lineHeight: "1.5", margin: "0 0 16px 0" }}>
              {selectedDevice?.is_paired
                ? `Ushbu qurilma Telegram ID: ${selectedDevice.telegram_user_id} bilan xavfsiz bog'langan. Barcha buyruqlar ruxsatlar nazorati ostida bajariladi.`
                : "Telegram botingizdan foydalanib kompyuteringizni masofadan boshqarish uchun bir martalik 5 daqiqalik ulanish kodini oling."}
            </p>

            {pairingCode && (
              <div
                style={{
                  background: "rgba(16, 185, 129, 0.08)",
                  border: "1px dashed rgba(16, 185, 129, 0.4)",
                  borderRadius: "12px",
                  padding: "16px",
                  marginBottom: "16px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "11px", color: "#10B981", fontWeight: 600, textTransform: "uppercase", marginBottom: "6px" }}>
                  Bir Martalik Ulanish Kodi
                </div>
                <div
                  style={{
                    fontSize: "26px",
                    fontWeight: 800,
                    letterSpacing: "4px",
                    fontFamily: "monospace",
                    color: "#34D399",
                    marginBottom: "8px",
                  }}
                >
                  {pairingCode}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted, #94A3B8)", marginBottom: "12px" }}>
                  Amal qilish muddati: <strong style={{ color: "#F8FAFC" }}>{Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, "0")}</strong>
                </div>
                <button
                  onClick={handleCopyCode}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "7px 14px",
                    background: copied ? "#10B981" : "rgba(255, 255, 255, 0.08)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "8px",
                    color: "#F8FAFC",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {copied ? <CheckIcon size={13} color="#FFF" /> : <CopyIcon size={13} color="#FFF" />}
                  {copied ? "Nusxalandi!" : "Buyruqni nusxalash (/pair ...)"}
                </button>
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: "10px", marginTop: "12px" }}>
            <button
              onClick={handleGenerateCode}
              disabled={isGeneratingCode}
              style={{
                flex: 1,
                padding: "10px 16px",
                background: "linear-gradient(135deg, #10B981, #059669)",
                border: "none",
                borderRadius: "10px",
                color: "#FFFFFF",
                fontSize: "13px",
                fontWeight: 600,
                cursor: isGeneratingCode ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                boxShadow: "0 4px 14px rgba(16, 185, 129, 0.3)",
              }}
            >
              <KeyIcon size={14} color="#FFF" />
              {isGeneratingCode ? "Hosil qilinmoqda..." : "Yangi ulanish kodi olish"}
            </button>

            {selectedDevice?.is_paired && (
              <button
                onClick={handleUnpair}
                style={{
                  padding: "10px 16px",
                  background: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid rgba(239, 68, 68, 0.25)",
                  borderRadius: "10px",
                  color: "#EF4444",
                  fontSize: "13px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <TrashIcon size={14} color="#EF4444" />
                Uzish
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Quick Session Controls Banner */}
      <div
        style={{
          background: "linear-gradient(90deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.7))",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          borderRadius: "14px",
          padding: "14px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "32px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <ShieldIcon size={18} color="#F59E0B" />
          <span style={{ fontSize: "13px", color: "var(--text, #F8FAFC)" }}>
            <strong>Masofaviy Sessiya Xavfsizligi:</strong> Kutilmagan faollik bo'lsa darhol bloklash mumkin.
          </span>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={handleLockSession}
            style={{
              padding: "7px 14px",
              background: "rgba(245, 158, 11, 0.12)",
              border: "1px solid rgba(245, 158, 11, 0.3)",
              borderRadius: "8px",
              color: "#F59E0B",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🔒 Sessiyani qulflash
          </button>
          <button
            onClick={handleLogoutSession}
            style={{
              padding: "7px 14px",
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              color: "#EF4444",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🚪 Chiqish (Logout)
          </button>
        </div>
      </div>

      {/* Permission Center Matrix */}
      <div
        style={{
          background: "var(--card-bg, rgba(255, 255, 255, 0.03))",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--border, rgba(255, 255, 255, 0.08))",
          borderRadius: "16px",
          padding: "24px",
          marginBottom: "32px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "14px",
            marginBottom: "20px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
            paddingBottom: "16px",
          }}
        >
          <div>
            <h2 style={{ fontSize: "17px", fontWeight: 700, margin: "0 0 4px 0" }}>
              Ruxsatlar Markazi (Granular Permission Matrix)
            </h2>
            <p style={{ margin: 0, fontSize: "12px", color: "var(--text-muted, #94A3B8)" }}>
              O'zgarishlar darhol jonli saqlanadi va Telegram botda darhol kuchga kiradi (serverni qayta ishga tushirish shart emas).
            </p>
          </div>

          {/* Search bar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "10px",
              padding: "7px 12px",
              width: "260px",
            }}
          >
            <SearchIcon size={14} color="#94A3B8" />
            <input
              type="text"
              placeholder="Ruxsatlarni qidirish..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: "transparent",
                border: "none",
                color: "#FFF",
                fontSize: "13px",
                outline: "none",
                width: "100%",
              }}
            />
          </div>
        </div>

        {/* Category Tabs */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "20px", overflowX: "auto", paddingBottom: "4px" }}>
          {[
            { id: "all", label: "Barchasi" },
            { id: "system", label: "🖥️ Tizim" },
            { id: "apps", label: "🚀 Ilovalar" },
            { id: "files", label: "📁 Fayllar" },
            { id: "network", label: "🌐 Tarmoq" },
            { id: "power", label: "⚡ Quvvat" },
            { id: "advanced", label: "🛡️ Kengaytirilgan" },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              style={{
                padding: "6px 14px",
                borderRadius: "8px",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
                border: "none",
                background: selectedCategory === cat.id ? "rgba(16, 185, 129, 0.2)" : "rgba(255, 255, 255, 0.04)",
                color: selectedCategory === cat.id ? "#34D399" : "var(--text-muted, #94A3B8)",
                transition: "all 0.15s ease",
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Permission Switch List */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))", gap: "16px" }}>
          {filteredPermItems.map((item) => {
            const isEnabled = permissions[item.id] ?? false;
            const isToggling = togglingPerm === item.id;
            const badge = getDangerBadge(item.danger_level);

            return (
              <div
                key={item.id}
                style={{
                  background: isEnabled ? "rgba(16, 185, 129, 0.04)" : "rgba(255, 255, 255, 0.02)",
                  border: `1px solid ${isEnabled ? "rgba(16, 185, 129, 0.25)" : "rgba(255, 255, 255, 0.06)"}`,
                  borderRadius: "14px",
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  transition: "all 0.2s ease",
                }}
              >
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                    <div>
                      <div style={{ fontSize: "14px", fontWeight: 600, color: "#F8FAFC", marginBottom: "2px" }}>
                        {item.name}
                      </div>
                      <div style={{ fontSize: "11px", fontFamily: "monospace", color: "#94A3B8" }}>
                        {item.id}
                      </div>
                    </div>

                    {/* Toggle Switch */}
                    <button
                      onClick={() => handleTogglePermission(item.id)}
                      disabled={isToggling}
                      style={{
                        width: "44px",
                        height: "24px",
                        borderRadius: "12px",
                        background: isEnabled ? "#10B981" : "rgba(255, 255, 255, 0.15)",
                        border: "none",
                        cursor: isToggling ? "wait" : "pointer",
                        position: "relative",
                        transition: "background 0.2s ease",
                        flexShrink: 0,
                        padding: 0,
                      }}
                    >
                      <span
                        style={{
                          position: "absolute",
                          top: "2px",
                          left: isEnabled ? "22px" : "2px",
                          width: "20px",
                          height: "20px",
                          borderRadius: "50%",
                          background: "#FFFFFF",
                          boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                          transition: "left 0.2s ease",
                        }}
                      />
                    </button>
                  </div>

                  <p style={{ fontSize: "12px", color: "var(--text-muted, #94A3B8)", lineHeight: "1.4", margin: "0 0 12px 0" }}>
                    {item.description}
                  </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      padding: "2px 8px",
                      borderRadius: "6px",
                      background: badge.bg,
                      color: badge.text,
                      border: `1px solid ${badge.border}`,
                    }}
                  >
                    {badge.label}
                  </span>

                  {item.requires_confirmation && (
                    <span
                      style={{
                        fontSize: "10px",
                        fontWeight: 600,
                        padding: "2px 8px",
                        borderRadius: "6px",
                        background: "rgba(245, 158, 11, 0.1)",
                        color: "#F59E0B",
                        border: "1px solid rgba(245, 158, 11, 0.25)",
                      }}
                    >
                      ⚡ Tasdiqlash talab etiladi
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Real-time Audit Log Section */}
      <div
        style={{
          background: "var(--card-bg, rgba(255, 255, 255, 0.03))",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--border, rgba(255, 255, 255, 0.08))",
          borderRadius: "16px",
          padding: "24px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
          <ClockIcon size={18} color="#10B981" />
          <h2 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>
            Masofaviy Xavfsizlik Auditi (Sanitizatsiyalangan Log)
          </h2>
        </div>

        {auditEvents.length === 0 ? (
          <div style={{ padding: "24px", textAlign: "center", color: "var(--text-muted, #94A3B8)", fontSize: "13px" }}>
            Hozircha audit yozuvlari mavjud emas
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.1)", color: "var(--text-muted, #94A3B8)" }}>
                  <th style={{ padding: "10px 12px" }}>Vaqt</th>
                  <th style={{ padding: "10px 12px" }}>Hodisa Turi</th>
                  <th style={{ padding: "10px 12px" }}>Telegram Foydalanuvchi</th>
                  <th style={{ padding: "10px 12px" }}>Holat</th>
                  <th style={{ padding: "10px 12px" }}>Tafsilotlar</th>
                </tr>
              </thead>
              <tbody>
                {auditEvents.slice(0, 15).map((evt, idx) => {
                  const isOk = evt.status === "success" || evt.status === "authorized";
                  const isDenied = evt.status === "denied" || evt.status === "failed";

                  return (
                    <tr
                      key={evt.event_id || idx}
                      style={{
                        borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                      }}
                    >
                      <td style={{ padding: "10px 12px", fontFamily: "monospace", color: "#94A3B8" }}>
                        {new Date(evt.timestamp).toLocaleTimeString()}
                      </td>
                      <td style={{ padding: "10px 12px", fontWeight: 600, color: "#F8FAFC" }}>
                        {evt.event_type}
                      </td>
                      <td style={{ padding: "10px 12px", fontFamily: "monospace" }}>
                        {evt.telegram_user_id || "N/A"}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            padding: "2px 8px",
                            borderRadius: "10px",
                            background: isOk ? "rgba(16, 185, 129, 0.15)" : isDenied ? "rgba(239, 68, 68, 0.15)" : "rgba(255, 255, 255, 0.1)",
                            color: isOk ? "#10B981" : isDenied ? "#EF4444" : "#94A3B8",
                            fontWeight: 600,
                          }}
                        >
                          {evt.status.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted, #94A3B8)", fontFamily: "monospace" }}>
                        {JSON.stringify(evt.details || {})}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
