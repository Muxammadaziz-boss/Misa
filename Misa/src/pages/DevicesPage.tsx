// ========== DevicesPage.tsx ==========
// Misa AI v9.0.0 — Universal Account & Device Management 2.0
// Multi-Device management page: list, select, rename, revoke

import React, { useState, useEffect, useCallback } from "react";
import {
  backendService,
  UserDevice,
} from "../services/backendService";
import {
  LaptopIcon,
  RefreshIcon,
  CheckIcon,
  TrashIcon,
  CopyIcon,
  AlertTriangleIcon,
  ClockIcon,
} from "../components/icons/Icons";

interface DevicesPageProps {
  onNavigateHome: () => void;
}

export const DevicesPage: React.FC<DevicesPageProps> = ({ onNavigateHome }) => {
  const [devices, setDevices] = useState<UserDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Rename modal state
  const [renameModalOpen, setRenameModalOpen] = useState<boolean>(false);
  const [deviceToRename, setDeviceToRename] = useState<UserDevice | null>(null);
  const [newName, setNewName] = useState<string>("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [renameSubmitting, setRenameSubmitting] = useState<boolean>(false);

  // Revoke modal state
  const [revokeModalOpen, setRevokeModalOpen] = useState<boolean>(false);
  const [deviceToRevoke, setDeviceToRevoke] = useState<UserDevice | null>(null);
  const [revokeSubmitting, setRevokeSubmitting] = useState<boolean>(false);

  // Notification message
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Phase 42: Device Enrollment & Pairing state
  const [pairingModalOpen, setPairingModalOpen] = useState<boolean>(false);
  const [pairingStep, setPairingStep] = useState<1 | 2 | 3>(1);
  const [pairingId, setPairingId] = useState<string | null>(null);
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [pairingExpiresAt, setPairingExpiresAt] = useState<number | null>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number>(300);
  const [pairingLoading, setPairingLoading] = useState<boolean>(false);
  const [pairingError, setPairingError] = useState<string | null>(null);
  const [pairedDevice, setPairedDevice] = useState<UserDevice | null>(null);
  const [customDeviceName, setCustomDeviceName] = useState<string>("");
  const [completingPairing, setCompletingPairing] = useState<boolean>(false);

  const showNotification = (type: "success" | "error", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 4000);
  };

  const loadDevices = useCallback(async () => {
    setLoading(true);
    try {
      const res = await backendService.getDevices();
      if (res.ok && res.devices) {
        setDevices(res.devices);
        const currentDev = res.devices.find((d: any) => d.is_current);
        const selId = res.selected_device_id || (currentDev ? currentDev.device_id : (res.devices.length > 0 ? res.devices[0].device_id : null));
        setSelectedDeviceId(selId);
      }
    } catch (err: any) {
      showNotification("error", `Qurilmalarni yuklashda xatolik: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDevices();

    // WebSocket real-time updates
    const unsubscribe = backendService.subscribe((msg: any) => {
      if (
        msg.type === "DEVICE_SELECTED" ||
        msg.type === "DEVICE_RENAMED" ||
        msg.type === "DEVICE_REVOKED" ||
        msg.type === "DEVICE_ADDED" ||
        msg.action === "DEVICE_SELECTED" ||
        msg.action === "DEVICE_RENAMED"
      ) {
        loadDevices();
      }
    });

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [loadDevices]);

  const handleSelectDevice = async (dev: UserDevice) => {
    try {
      const res = await backendService.selectDevice(dev.device_id);
      if (res.ok) {
        setSelectedDeviceId(dev.device_id);
        showNotification("success", `'${dev.name}' kompyuteri faol boshqaruv uchun tanlandi.`);
      } else {
        showNotification("error", res.error || "Qurilmani tanlashda xatolik yuz berdi.");
      }
    } catch (err: any) {
      showNotification("error", err.message || "Server xatosi");
    }
  };

  // Phase 42: Start Pairing Wizard
  const handleOpenPairingModal = async () => {
    setPairingModalOpen(true);
    setPairingStep(1);
    setPairingError(null);
    setPairedDevice(null);
    setCustomDeviceName("");
    await startPairingProcess();
  };

  const startPairingProcess = async () => {
    setPairingLoading(true);
    setPairingError(null);
    try {
      const res = await backendService.startDevicePairing(300);
      if (res.ok && res.pairing_id && res.code) {
        setPairingId(res.pairing_id);
        setPairingCode(res.code);
        const expiresAt = res.expires_at || (Date.now() / 1000 + 300);
        setPairingExpiresAt(expiresAt);
        setRemainingSeconds(Math.max(0, Math.floor(expiresAt - Date.now() / 1000)));
        setPairingStep(2);
      } else {
        setPairingError(res.error || "Juftlash kodini yaratishda xatolik yuz berdi.");
      }
    } catch (err: any) {
      setPairingError(err.message || "Server bilan aloqa uzildi.");
    } finally {
      setPairingLoading(false);
    }
  };

  // Countdown timer effect
  useEffect(() => {
    if (!pairingModalOpen || pairingStep !== 2 || !pairingExpiresAt) return;

    const timer = setInterval(() => {
      const diff = Math.max(0, Math.floor(pairingExpiresAt - Date.now() / 1000));
      setRemainingSeconds(diff);
      if (diff <= 0) {
        clearInterval(timer);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [pairingModalOpen, pairingStep, pairingExpiresAt]);

  // Polling effect for pairing completion
  useEffect(() => {
    if (!pairingModalOpen || pairingStep !== 2 || !pairingId) return;

    const pollInterval = setInterval(async () => {
      try {
        const res = await backendService.getDevicePairingStatus(pairingId);
        if (res.ok && res.session) {
          if (res.session.status === "COMPLETED") {
            clearInterval(pollInterval);
            const enrolledDevId = res.session.device_id || res.device_id;
            const devRes = await backendService.getDevices();
            if (devRes.ok && devRes.devices) {
              setDevices(devRes.devices);
              const found = devRes.devices.find((d) => d.device_id === enrolledDevId);
              if (found) {
                setPairedDevice(found);
                setCustomDeviceName(found.name);
              }
            }
            setPairingStep(3);
          } else if (res.session.status === "EXPIRED" || res.session.status === "CANCELLED") {
            clearInterval(pollInterval);
            setPairingError(
              res.session.status === "EXPIRED"
                ? "Juftlash kodi muddati tugadi. Qaytadan urinib ko'ring."
                : "Juftlash bekor qilindi."
            );
          }
        }
      } catch (e) {
        // ignore intermittent network errors during polling
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [pairingModalOpen, pairingStep, pairingId]);

  const handleCancelPairing = async () => {
    if (pairingId) {
      try {
        await backendService.cancelDevicePairing(pairingId);
      } catch {}
    }
    setPairingModalOpen(false);
    setPairingId(null);
    setPairingCode(null);
  };

  const handleFinishPairing = async () => {
    if (pairedDevice && customDeviceName && customDeviceName.trim() !== pairedDevice.name) {
      setCompletingPairing(true);
      try {
        await backendService.renameDevice(pairedDevice.device_id, customDeviceName.trim());
      } catch {}
      setCompletingPairing(false);
    }
    setPairingModalOpen(false);
    await loadDevices();
    showNotification("success", "Yangi kompyuter muvaffaqiyatli hisobingizga ulandi! ✓");
  };

  const openRenameModal = (dev: UserDevice) => {
    setDeviceToRename(dev);
    setNewName(dev.name);
    setRenameError(null);
    setRenameModalOpen(true);
  };

  const submitRename = async () => {
    if (!deviceToRename) return;
    const cleanName = newName.trim();
    if (!cleanName) {
      setRenameError("Qurilma nomi bo'sh bo'lishi mumkin emas.");
      return;
    }
    if (cleanName.length > 64) {
      setRenameError("Qurilma nomi 64 belgidan oshmasligi kerak.");
      return;
    }

    setRenameSubmitting(true);
    try {
      const targetId = deviceToRename.id || deviceToRename.device_id;
      const res = await backendService.renameDevice(targetId, cleanName);
      if (res.ok) {
        await loadDevices();
        setRenameModalOpen(false);
        showNotification("success", `Qurilma nomi muvaffaqiyatli "${cleanName}" deb o'zgartirildi.`);
      } else {
        setRenameError(res.error || "Nomni o'zgartirishda xatolik.");
      }
    } catch (err: any) {
      setRenameError(err.message || "Server bilan aloqa uzildi.");
    } finally {
      setRenameSubmitting(false);
    }
  };

  const openRevokeModal = (dev: UserDevice) => {
    setDeviceToRevoke(dev);
    setRevokeModalOpen(true);
  };

  const submitRevoke = async () => {
    if (!deviceToRevoke) return;
    setRevokeSubmitting(true);
    try {
      const res = await backendService.revokeDevice(deviceToRevoke.device_id);
      if (res.ok) {
        setDevices((prev) => prev.filter((d) => d.id !== deviceToRevoke.id && d.device_id !== deviceToRevoke.device_id));
        if (selectedDeviceId === deviceToRevoke.device_id || selectedDeviceId === deviceToRevoke.id) {
          setSelectedDeviceId(null);
        }
        setRevokeModalOpen(false);
        showNotification("success", `'${deviceToRevoke.name}' muvaffaqiyatli o'chirildi va barcha sessiyalar to'xtatildi.`);
      } else {
        showNotification("error", res.error || "Qurilmani bekor qilishda xatolik.");
      }
    } catch (err: any) {
      showNotification("error", err.message || "Server xatosi");
    } finally {
      setRevokeSubmitting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "online":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "3px 10px",
              borderRadius: "20px",
              fontSize: "11.5px",
              fontWeight: 600,
              backgroundColor: "rgba(16, 185, 129, 0.15)",
              color: "#34D399",
              border: "1px solid rgba(16, 185, 129, 0.35)",
            }}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: "#34D399",
                boxShadow: "0 0 8px #34D399",
              }}
            />
            Onlayn
          </span>
        );
      case "standby":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "3px 10px",
              borderRadius: "20px",
              fontSize: "11.5px",
              fontWeight: 600,
              backgroundColor: "rgba(245, 158, 11, 0.15)",
              color: "#FBBF24",
              border: "1px solid rgba(245, 158, 11, 0.35)",
            }}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: "#FBBF24",
              }}
            />
            Kutish rejimi
          </span>
        );
      default:
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "3px 10px",
              borderRadius: "20px",
              fontSize: "11.5px",
              fontWeight: 500,
              backgroundColor: "rgba(148, 163, 184, 0.12)",
              color: "#94A3B8",
              border: "1px solid rgba(148, 163, 184, 0.25)",
            }}
          >
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: "#64748B",
              }}
            />
            Oflayn
          </span>
        );
    }
  };

  const formatTimestamp = (ts?: number | null) => {
    if (!ts) return "Mavjud emas";
    return new Date(ts * 1000).toLocaleString("uz-UZ", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const onlineCount = devices.filter((d) => d.status.toLowerCase() === "online").length;
  const selectedDevice = devices.find((d) => d.device_id === selectedDeviceId || d.id === selectedDeviceId);

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "24px 32px",
        width: "100%",
        maxWidth: "1200px",
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        gap: "24px",
      }}
    >
      {/* ── 1. Header Toolbar ── */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
          paddingBottom: "20px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              padding: "10px",
              borderRadius: "14px",
              backgroundColor: "rgba(56, 189, 248, 0.15)",
              border: "1px solid rgba(56, 189, 248, 0.35)",
              color: "#38BDF8",
              boxShadow: "0 0 20px rgba(56, 189, 248, 0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <LaptopIcon size={24} />
          </div>
          <div>
            <h1 style={{ fontSize: "22px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
              Qurilmalar Boshqaruvi
            </h1>
            <p style={{ fontSize: "12px", color: "#94A3B8", margin: "3px 0 0 0" }}>
              Universal hisob va kompyuterlarni masofaviy sinxronlash (Multi-Device)
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {onNavigateHome && (
            <button
              type="button"
              onClick={onNavigateHome}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 14px",
                borderRadius: "10px",
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                color: "#CBD5E1",
                fontSize: "12px",
                fontWeight: 500,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.08)";
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
                e.currentTarget.style.color = "#CBD5E1";
              }}
            >
              <span>← Bosh sahifa</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleOpenPairingModal}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 16px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, rgba(2, 132, 199, 0.4), rgba(99, 102, 241, 0.4))",
              border: "1px solid rgba(56, 189, 248, 0.45)",
              color: "#FFFFFF",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "0 4px 16px rgba(2, 132, 199, 0.25)",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = "translateY(-1px)";
              e.currentTarget.style.borderColor = "rgba(56, 189, 248, 0.75)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = "translateY(0)";
              e.currentTarget.style.borderColor = "rgba(56, 189, 248, 0.45)";
            }}
          >
            <span style={{ fontSize: "15px", fontWeight: "bold" }}>+</span>
            <span>Kompyuter qo'shish</span>
          </button>

          <button
            type="button"
            onClick={loadDevices}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "10px",
              backgroundColor: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              color: "#CBD5E1",
              fontSize: "12px",
              fontWeight: 500,
              cursor: loading ? "default" : "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.08)";
            }}
            onMouseLeave={(e) => {
              if (!loading) e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
            }}
          >
            <RefreshIcon size={14} className={loading ? "animate-spin" : ""} />
            <span>Yangilash</span>
          </button>
        </div>
      </div>

      {/* ── 2. Notifications ── */}
      {message && (
        <div
          style={{
            padding: "12px 18px",
            borderRadius: "12px",
            fontSize: "12.5px",
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            backgroundColor:
              message.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
            border:
              message.type === "success"
                ? "1px solid rgba(16, 185, 129, 0.35)"
                : "1px solid rgba(239, 68, 68, 0.35)",
            color: message.type === "success" ? "#34D399" : "#F87171",
          }}
        >
          <span>{message.text}</span>
          <button
            type="button"
            onClick={() => setMessage(null)}
            style={{
              background: "transparent",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontSize: "16px",
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>
      )}

      {/* ── Auto Local Device Recognition Banner ── */}
      {devices.some((d) => d.is_current) && (
        <div
          style={{
            padding: "14px 20px",
            borderRadius: "14px",
            backgroundColor: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "14px",
            boxShadow: "0 4px 20px rgba(16, 185, 129, 0.12)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor: "#34D399",
                boxShadow: "0 0 12px #34D399",
                display: "inline-block",
                flexShrink: 0,
              }}
            />
            <div style={{ fontSize: "12.5px", color: "#E2E8F0" }}>
              <strong style={{ color: "#34D399" }}>Shu kompyuter avtomatik tanildi:</strong> Ushbu qurilma (
              <span style={{ color: "#38BDF8", fontFamily: "monospace" }}>
                {devices.find((d) => d.is_current)?.name || "Asosiy kompyuter"}
              </span>
              ) hisobingizga avtomatik biriktirildi va onlayn holatda. Terminaldan juftlash kodi kiritish shart emas!
            </div>
          </div>
          <span
            style={{
              fontSize: "11px",
              padding: "4px 12px",
              borderRadius: "20px",
              backgroundColor: "rgba(16, 185, 129, 0.2)",
              color: "#34D399",
              border: "1px solid rgba(16, 185, 129, 0.35)",
              fontWeight: 600,
              whiteSpace: "nowrap",
            }}
          >
            🟢 Shu qurilma (Onlayn)
          </span>
        </div>
      )}

      {/* ── 3. Summary KPI Cards ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "16px",
        }}
      >
        <div
          style={{
            padding: "18px 22px",
            borderRadius: "16px",
            backgroundColor: "rgba(15, 23, 42, 0.65)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.35)",
          }}
        >
          <div style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>Jami Kompyuterlar</div>
          <div style={{ fontSize: "28px", fontWeight: 700, color: "#FFFFFF", marginTop: "4px" }}>
            {devices.length}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
            Sizning hisobingizga ulangan
          </div>
        </div>

        <div
          style={{
            padding: "18px 22px",
            borderRadius: "16px",
            backgroundColor: "rgba(15, 23, 42, 0.65)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.35)",
          }}
        >
          <div style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>Onlayn Holatda</div>
          <div style={{ fontSize: "28px", fontWeight: 700, color: "#34D399", marginTop: "4px" }}>
            {onlineCount}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px" }}>
            Aloqaga tayyor kompyuterlar
          </div>
        </div>

        <div
          style={{
            padding: "18px 22px",
            borderRadius: "16px",
            backgroundColor: "rgba(15, 23, 42, 0.65)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.35)",
          }}
        >
          <div style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>Faol Tanlangan Kompyuter</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#38BDF8", marginTop: "8px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {selectedDevice ? selectedDevice.name : "Tanlanmagan"}
          </div>
          <div style={{ fontSize: "11px", color: "#64748B", marginTop: "4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {selectedDevice ? `ID: ${selectedDevice.device_id}` : "Buyruqlar uchun birorta kompyuter tanlang"}
          </div>
        </div>
      </div>

      {/* ── 4. Device List ── */}
      <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
        <h2 style={{ fontSize: "13px", fontWeight: 600, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.5px", margin: 0 }}>
          Kompyuterlar Ro'yxati ({devices.length})
        </h2>

        {loading && devices.length === 0 ? (
          <div style={{ padding: "48px", textAlign: "center", color: "#64748B", fontSize: "13px" }}>
            Kompyuterlar yuklanmoqda...
          </div>
        ) : devices.length === 0 ? (
          <div
            style={{
              padding: "48px 24px",
              textAlign: "center",
              borderRadius: "18px",
              backgroundColor: "rgba(15, 23, 42, 0.5)",
              border: "1px dashed rgba(255, 255, 255, 0.12)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div style={{ color: "#475569" }}>
              <LaptopIcon size={42} />
            </div>
            <h3 style={{ fontSize: "16px", fontWeight: 600, color: "#E2E8F0", margin: 0 }}>
              Kompyuterlar topilmadi
            </h3>
            <p style={{ fontSize: "12.5px", color: "#94A3B8", maxWidth: "420px", margin: 0, lineHeight: 1.5 }}>
              Hisobingizga birorta ham kompyuter ulanmagan. Misa Desktop agenti orqali kompyuteringizni juftlang.
            </p>
            <button
              type="button"
              onClick={handleOpenPairingModal}
              style={{
                marginTop: "8px",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 18px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, rgba(2, 132, 199, 0.4), rgba(99, 102, 241, 0.4))",
                border: "1px solid rgba(56, 189, 248, 0.45)",
                color: "#FFFFFF",
                fontSize: "12px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <span>+ Yangi Kompyuter Ulash</span>
            </button>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
              gap: "16px",
            }}
          >
            {devices.map((dev) => {
              const isSelected = dev.device_id === selectedDeviceId || dev.id === selectedDeviceId;
              return (
                <div
                  key={dev.id}
                  style={{
                    padding: "20px",
                    borderRadius: "16px",
                    backgroundColor: isSelected ? "rgba(15, 23, 42, 0.85)" : "rgba(15, 23, 42, 0.55)",
                    backdropFilter: "blur(20px)",
                    WebkitBackdropFilter: "blur(20px)",
                    border: isSelected ? "1px solid rgba(56, 189, 248, 0.5)" : "1px solid rgba(255, 255, 255, 0.08)",
                    boxShadow: isSelected ? "0 12px 36px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.2)" : "0 8px 32px rgba(0, 0, 0, 0.35)",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: "16px",
                    transition: "all 0.2s ease",
                  }}
                >
                  <div>
                    {/* Top Row: Title, Status, and Active Badge */}
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px" }}>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {dev.name}
                          </h3>
                          {dev.is_current && (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "5px",
                                padding: "2px 8px",
                                borderRadius: "6px",
                                fontSize: "10.5px",
                                fontWeight: 700,
                                backgroundColor: "rgba(16, 185, 129, 0.2)",
                                color: "#34D399",
                                border: "1px solid rgba(16, 185, 129, 0.4)",
                                boxShadow: "0 0 10px rgba(16, 185, 129, 0.25)",
                              }}
                            >
                              <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#34D399", boxShadow: "0 0 6px #34D399" }} />
                              Shu qurilma
                            </span>
                          )}
                          {isSelected && (
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                padding: "2px 8px",
                                borderRadius: "6px",
                                fontSize: "10px",
                                fontWeight: 700,
                                backgroundColor: "rgba(56, 189, 248, 0.2)",
                                color: "#38BDF8",
                                border: "1px solid rgba(56, 189, 248, 0.35)",
                              }}
                            >
                              <CheckIcon size={10} />
                              Faol
                            </span>
                          )}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
                          <span style={{ fontSize: "11px", color: "#64748B", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "200px" }}>
                            {dev.device_id}
                          </span>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(dev.device_id)}
                            style={{
                              background: "transparent",
                              border: "none",
                              color: "#64748B",
                              cursor: "pointer",
                              padding: "2px",
                              display: "flex",
                              alignItems: "center",
                            }}
                            title="ID nusxalash"
                          >
                            <CopyIcon size={12} />
                          </button>
                          {copiedId === dev.device_id && (
                            <span style={{ fontSize: "10px", color: "#34D399" }}>Nusxa olindi!</span>
                          )}
                        </div>
                      </div>

                      <div>{getStatusBadge(dev.status)}</div>
                    </div>

                    {/* Metadata Specs Grid */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(2, 1fr)",
                        gap: "10px",
                        marginTop: "16px",
                        paddingTop: "14px",
                        borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                        fontSize: "12px",
                      }}
                    >
                      <div>
                        <span style={{ color: "#64748B", display: "block", fontSize: "10px", textTransform: "uppercase", fontWeight: 600 }}>Xost nomi</span>
                        <span style={{ color: "#CBD5E1", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block" }}>
                          {dev.hostname || "Aniqlanmagan"}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: "#64748B", display: "block", fontSize: "10px", textTransform: "uppercase", fontWeight: 600 }}>Platforma</span>
                        <span style={{ color: "#CBD5E1", fontWeight: 500, textTransform: "capitalize", display: "block" }}>
                          {dev.platform || "Windows"}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: "#64748B", display: "block", fontSize: "10px", textTransform: "uppercase", fontWeight: 600 }}>Agent Versiyasi</span>
                        <span style={{ color: "#93C5FD", fontFamily: "monospace", display: "block" }}>
                          v{dev.agent_version || "9.0.1"}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: "#64748B", display: "block", fontSize: "10px", textTransform: "uppercase", fontWeight: 600 }}>Oxirgi faollik</span>
                        <span style={{ color: "#CBD5E1", display: "flex", alignItems: "center", gap: "4px" }}>
                          <ClockIcon size={11} color="#64748B" />
                          {formatTimestamp(dev.last_seen_at || dev.last_heartbeat_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions Footer */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "10px",
                      marginTop: "14px",
                      paddingTop: "14px",
                      borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <button
                        type="button"
                        onClick={() => openRenameModal(dev)}
                        style={{
                          padding: "6px 12px",
                          borderRadius: "8px",
                          backgroundColor: "rgba(255, 255, 255, 0.05)",
                          border: "1px solid rgba(255, 255, 255, 0.1)",
                          color: "#CBD5E1",
                          fontSize: "11.5px",
                          fontWeight: 500,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.1)")}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.05)")}
                      >
                        Nomlash
                      </button>
                      <button
                        type="button"
                        onClick={() => openRevokeModal(dev)}
                        style={{
                          padding: "6px 8px",
                          borderRadius: "8px",
                          backgroundColor: "rgba(239, 68, 68, 0.08)",
                          border: "1px solid rgba(239, 68, 68, 0.25)",
                          color: "#F87171",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.2)")}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.08)")}
                        title="Kompyuterni bekor qilish / o'chirish"
                      >
                        <TrashIcon size={13} />
                      </button>
                    </div>

                    <div>
                      {isSelected ? (
                        <span
                          style={{
                            fontSize: "11.5px",
                            color: "#34D399",
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            gap: "5px",
                            padding: "6px 14px",
                            borderRadius: "8px",
                            backgroundColor: "rgba(16, 185, 129, 0.12)",
                            border: "1px solid rgba(16, 185, 129, 0.3)",
                          }}
                        >
                          <CheckIcon size={12} />
                          Tanlangan
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleSelectDevice(dev)}
                          style={{
                            padding: "6px 14px",
                            borderRadius: "8px",
                            background: "linear-gradient(135deg, rgba(2, 132, 199, 0.4), rgba(99, 102, 241, 0.4))",
                            border: "1px solid rgba(56, 189, 248, 0.4)",
                            color: "#FFFFFF",
                            fontSize: "11.5px",
                            fontWeight: 600,
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = "rgba(56, 189, 248, 0.7)";
                            e.currentTarget.style.transform = "translateY(-1px)";
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = "rgba(56, 189, 248, 0.4)";
                            e.currentTarget.style.transform = "translateY(0)";
                          }}
                        >
                          Faol Tanlash
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 5. Rename Modal ── */}
      {renameModalOpen && deviceToRename && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              backgroundColor: "rgba(11, 17, 33, 0.96)",
              border: "1px solid rgba(56, 189, 248, 0.25)",
              borderRadius: "18px",
              boxShadow: "0 25px 60px rgba(0, 0, 0, 0.8)",
              padding: "24px",
              maxWidth: "460px",
              width: "100%",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                Kompyuter nomini o'zgartirish
              </h3>
              <p style={{ fontSize: "12px", color: "#94A3B8", margin: "4px 0 0 0" }}>
                Ushbu kompyuterni oson ajratib olish uchun qulay nom bering (masalan: "Gaming PC", "Ofis Noutbuk").
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12px", fontWeight: 600, color: "#CBD5E1" }}>
                Do'stona nom
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Kompyuter nomini kiriting"
                maxLength={64}
                autoFocus
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "10px",
                  backgroundColor: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#FFFFFF",
                  fontSize: "14px",
                  outline: "none",
                }}
              />
              {renameError && (
                <p style={{ fontSize: "12px", color: "#F87171", margin: 0 }}>{renameError}</p>
              )}
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "10px", paddingTop: "8px" }}>
              <button
                type="button"
                onClick={() => setRenameModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "10px",
                  backgroundColor: "transparent",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#CBD5E1",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="button"
                onClick={submitRename}
                disabled={renameSubmitting}
                style={{
                  padding: "8px 18px",
                  borderRadius: "10px",
                  backgroundColor: "#0284C7",
                  border: "1px solid rgba(56, 189, 248, 0.5)",
                  color: "#FFFFFF",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {renameSubmitting ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 6. Revoke Modal ── */}
      {revokeModalOpen && deviceToRevoke && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              backgroundColor: "rgba(11, 17, 33, 0.96)",
              border: "1px solid rgba(239, 68, 68, 0.35)",
              borderRadius: "18px",
              boxShadow: "0 25px 60px rgba(0, 0, 0, 0.8)",
              padding: "24px",
              maxWidth: "460px",
              width: "100%",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
              <div
                style={{
                  padding: "8px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(239, 68, 68, 0.15)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  color: "#EF4444",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <AlertTriangleIcon size={20} />
              </div>
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                  Kompyuterni o'chirishni tasdiqlang
                </h3>
                <p style={{ fontSize: "12px", color: "#94A3B8", margin: "4px 0 0 0" }}>
                  Haqiqatan ham <strong style={{ color: "#FFFFFF" }}>'{deviceToRevoke.name}'</strong> kompyuterini hisobingizdan o'chirmoqchimisiz?
                </p>
              </div>
            </div>

            <div
              style={{
                padding: "12px 16px",
                borderRadius: "12px",
                backgroundColor: "rgba(0, 0, 0, 0.4)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                fontSize: "11.5px",
                color: "#94A3B8",
                lineHeight: 1.6,
              }}
            >
              <p style={{ fontWeight: 600, color: "#CBD5E1", margin: "0 0 4px 0" }}>Xavfsizlik oqibatlari:</p>
              <ul style={{ margin: 0, paddingLeft: "18px" }}>
                <li>Ushbu kompyuterdagi barcha faol masofaviy sessiyalar darhol to'xtatiladi.</li>
                <li>Foydalanuvchi ruxsatlari profili bekor qilinadi.</li>
                <li>Kompyuter qayta ulangunga qadar unga buyruq yuborib bo'lmaydi.</li>
              </ul>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "10px", paddingTop: "8px" }}>
              <button
                type="button"
                onClick={() => setRevokeModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "10px",
                  backgroundColor: "transparent",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#CBD5E1",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="button"
                onClick={submitRevoke}
                disabled={revokeSubmitting}
                style={{
                  padding: "8px 18px",
                  borderRadius: "10px",
                  backgroundColor: "#DC2626",
                  border: "1px solid rgba(239, 68, 68, 0.5)",
                  color: "#FFFFFF",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {revokeSubmitting ? "O'chirilmoqda..." : "Ha, o'chirilsin"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 7. Phase 42: 3-Step Device Pairing Modal ── */}
      {pairingModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.85)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            style={{
              backgroundColor: "rgba(10, 16, 32, 0.96)",
              border: "1px solid rgba(56, 189, 248, 0.35)",
              borderRadius: "20px",
              boxShadow: "0 25px 60px rgba(0, 0, 0, 0.8), 0 0 30px rgba(2, 132, 199, 0.2)",
              padding: "28px",
              maxWidth: "520px",
              width: "100%",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                paddingBottom: "16px",
                borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    padding: "8px",
                    borderRadius: "12px",
                    backgroundColor: "rgba(56, 189, 248, 0.15)",
                    border: "1px solid rgba(56, 189, 248, 0.3)",
                    color: "#38BDF8",
                  }}
                >
                  <LaptopIcon size={22} />
                </div>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                    Kompyuterni Juftlash & Ulash
                    <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "4px", backgroundColor: "rgba(56, 189, 248, 0.15)", color: "#38BDF8", fontFamily: "monospace" }}>
                      Phase 42
                    </span>
                  </h3>
                  <p style={{ fontSize: "12px", color: "#94A3B8", margin: "2px 0 0 0" }}>
                    Ed25519 kriptografik kalitlar orqali xavfsiz enrollment
                  </p>
                </div>
              </div>

              {/* Step indicator badges */}
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                {[1, 2, 3].map((step) => (
                  <div
                    key={step}
                    style={{
                      width: "24px",
                      height: "24px",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "11px",
                      fontWeight: 700,
                      backgroundColor:
                        pairingStep === step
                          ? "#38BDF8"
                          : pairingStep > step
                          ? "rgba(16, 185, 129, 0.2)"
                          : "rgba(255, 255, 255, 0.06)",
                      color:
                        pairingStep === step
                          ? "#0B0F19"
                          : pairingStep > step
                          ? "#34D399"
                          : "#64748B",
                      border:
                        pairingStep > step
                          ? "1px solid rgba(16, 185, 129, 0.4)"
                          : "none",
                    }}
                  >
                    {pairingStep > step ? "✓" : step}
                  </div>
                ))}
              </div>
            </div>

            {/* Error Message */}
            {pairingError && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "10px",
                  backgroundColor: "rgba(239, 68, 68, 0.15)",
                  border: "1px solid rgba(239, 68, 68, 0.35)",
                  fontSize: "12px",
                  color: "#F87171",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>{pairingError}</span>
                <button
                  type="button"
                  onClick={() => setPairingError(null)}
                  style={{ background: "transparent", border: "none", color: "inherit", cursor: "pointer" }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* STEP 1: Generate Pairing Code */}
            {pairingStep === 1 && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", gap: "16px", padding: "12px 0" }}>
                <div
                  style={{
                    width: "64px",
                    height: "64px",
                    borderRadius: "18px",
                    backgroundColor: "rgba(56, 189, 248, 0.12)",
                    border: "1px solid rgba(56, 189, 248, 0.3)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#38BDF8",
                  }}
                >
                  <LaptopIcon size={32} />
                </div>
                <div>
                  <h4 style={{ fontSize: "15px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                    Yangi Windows PC Agentini Ulash
                  </h4>
                  <p style={{ fontSize: "12.5px", color: "#94A3B8", maxWidth: "380px", margin: "6px auto 0 auto", lineHeight: 1.5 }}>
                    Kompyuteringizni hisobingizga xavfsiz biriktirish uchun bir martalik 6-xonali juftlash kodi hosil qilinadi.
                  </p>
                </div>

                <div
                  style={{
                    padding: "14px 18px",
                    borderRadius: "12px",
                    backgroundColor: "rgba(0, 0, 0, 0.45)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    textAlign: "left",
                    fontSize: "12px",
                    color: "#94A3B8",
                    lineHeight: 1.6,
                    width: "100%",
                  }}
                >
                  <div style={{ fontWeight: 600, color: "#CBD5E1", marginBottom: "4px" }}>Xavfsizlik kafolati:</div>
                  <div>• Kod 5 daqiqa davomida amal qiladi va faqat bitta kompyuterga ishlatiladi.</div>
                  <div>• Kompyuteringiz Ed25519 kripto kalit yaratadi va uni Windows DPAPI da saqlaydi.</div>
                  <div>• Shaxsiy kalit hech qachon tarmoqqa yoki serverga yuborilmaydi.</div>
                </div>

                <button
                  type="button"
                  onClick={startPairingProcess}
                  disabled={pairingLoading}
                  style={{
                    width: "100%",
                    padding: "11px",
                    borderRadius: "12px",
                    background: "linear-gradient(135deg, rgba(2, 132, 199, 0.8), rgba(99, 102, 241, 0.8))",
                    border: "1px solid rgba(56, 189, 248, 0.5)",
                    color: "#FFFFFF",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    boxShadow: "0 4px 16px rgba(2, 132, 199, 0.3)",
                  }}
                >
                  {pairingLoading ? (
                    <>
                      <RefreshIcon size={16} className="animate-spin" />
                      <span>Kod generatsiya qilinmoqda...</span>
                    </>
                  ) : (
                    <span>Juftlash Kodini Olish</span>
                  )}
                </button>
              </div>
            )}

            {/* STEP 2: Display 6-digit Code & Countdown */}
            {pairingStep === 2 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
                <div style={{ textAlign: "center" }}>
                  <p style={{ fontSize: "12.5px", color: "#94A3B8", margin: "0 0 14px 0" }}>
                    Windows PC Agentingizda quyidagi 6 xonali kodni kiriting:
                  </p>

                  {/* Big 6-digit Display */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
                    {pairingCode
                      ? pairingCode.split("").map((digit, idx) => (
                          <div
                            key={idx}
                            style={{
                              width: "44px",
                              height: "56px",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: "28px",
                              fontWeight: 800,
                              fontFamily: "monospace",
                              borderRadius: "12px",
                              backgroundColor: "rgba(0, 0, 0, 0.6)",
                              border: "1.5px solid rgba(56, 189, 248, 0.5)",
                              color: "#38BDF8",
                              boxShadow: "0 8px 24px rgba(2, 132, 199, 0.25)",
                              marginRight: idx === 2 ? "10px" : "0",
                            }}
                          >
                            {digit}
                          </div>
                        ))
                      : null}
                  </div>

                  {/* Copy & Status Bar */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "16px", marginTop: "14px" }}>
                    {pairingCode && (
                      <button
                        type="button"
                        onClick={() => copyToClipboard(pairingCode)}
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          fontSize: "12px",
                          color: "#38BDF8",
                          background: "transparent",
                          border: "none",
                          cursor: "pointer",
                        }}
                      >
                        <CopyIcon size={13} />
                        <span>{copiedId === pairingCode ? "Nusxa olindi!" : "Kodni nusxalash"}</span>
                      </button>
                    )}

                    {/* Countdown */}
                    <div
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        fontSize: "12px",
                        fontFamily: "monospace",
                        fontWeight: 600,
                        padding: "4px 10px",
                        borderRadius: "8px",
                        backgroundColor: "rgba(245, 158, 11, 0.12)",
                        border: "1px solid rgba(245, 158, 11, 0.3)",
                        color: "#FBBF24",
                      }}
                    >
                      <ClockIcon size={13} />
                      <span>
                        {String(Math.floor(remainingSeconds / 60)).padStart(2, "0")}:
                        {String(remainingSeconds % 60).padStart(2, "0")}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Instructions card */}
                <div
                  style={{
                    padding: "14px",
                    borderRadius: "12px",
                    backgroundColor: "rgba(0, 0, 0, 0.45)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    fontSize: "12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ color: "#CBD5E1", fontWeight: 600 }}>Windows kompyuterda ishga tushiring:</div>
                  <div
                    style={{
                      padding: "8px 12px",
                      borderRadius: "8px",
                      backgroundColor: "rgba(0, 0, 0, 0.8)",
                      border: "1px solid rgba(56, 189, 248, 0.25)",
                      fontFamily: "monospace",
                      fontSize: "12px",
                      color: "#34D399",
                      overflowX: "auto",
                      userSelect: "all",
                    }}
                  >
                    misa-agent --pair {pairingCode || "******"}
                  </div>
                  <p style={{ fontSize: "11px", color: "#64748B", margin: 0 }}>
                    Agent ushbu kodni yuboradi, server unga Ed25519 mualliflik sertifikatini biriktiradi.
                  </p>
                </div>

                {/* Waiting indicator */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", fontSize: "12px", color: "#94A3B8" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#38BDF8" }} />
                  <span>Kompyuter agenti ulanishi kutilmoqda...</span>
                </div>

                {/* Actions */}
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "8px", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
                  <button
                    type="button"
                    onClick={handleCancelPairing}
                    style={{
                      padding: "8px 14px",
                      borderRadius: "10px",
                      background: "transparent",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      color: "#94A3B8",
                      fontSize: "12px",
                      cursor: "pointer",
                    }}
                  >
                    Bekor qilish
                  </button>

                  {remainingSeconds <= 0 && (
                    <button
                      type="button"
                      onClick={startPairingProcess}
                      style={{
                        padding: "8px 16px",
                        borderRadius: "10px",
                        backgroundColor: "#D97706",
                        color: "#FFFFFF",
                        fontSize: "12px",
                        fontWeight: 600,
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      Kodni yangilash
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* STEP 3: Paired Confirmation & Friendly Name */}
            {pairingStep === 3 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ textAlign: "center" }}>
                  <div
                    style={{
                      width: "48px",
                      height: "48px",
                      borderRadius: "50%",
                      backgroundColor: "rgba(16, 185, 129, 0.18)",
                      border: "1px solid rgba(16, 185, 129, 0.4)",
                      color: "#34D399",
                      margin: "0 auto",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "22px",
                    }}
                  >
                    ✓
                  </div>
                  <h4 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: "8px 0 2px 0" }}>
                    Kompyuter Topildi & Ulandi!
                  </h4>
                  <p style={{ fontSize: "12px", color: "#94A3B8", margin: 0 }}>
                    Kriptografik Ed25519 kalit tekshirildi va qurilma ro'yxatdan o'tdi.
                  </p>
                </div>

                {/* Device summary badge */}
                <div
                  style={{
                    padding: "14px",
                    borderRadius: "12px",
                    backgroundColor: "rgba(0, 0, 0, 0.45)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    fontSize: "12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#64748B" }}>Xost nomi:</span>
                    <span style={{ color: "#E2E8F0", fontWeight: 600, fontFamily: "monospace" }}>
                      {pairedDevice?.hostname || "DESKTOP-PC"}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#64748B" }}>Platforma:</span>
                    <span style={{ color: "#E2E8F0" }}>
                      {pairedDevice?.platform || "Windows"}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "#64748B" }}>Qurilma ID:</span>
                    <span style={{ color: "#38BDF8", fontFamily: "monospace", fontSize: "11px" }}>
                      {pairedDevice?.device_id || pairingId}
                    </span>
                  </div>
                </div>

                {/* Friendly name input */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12px", fontWeight: 600, color: "#CBD5E1" }}>
                    Do'stona nom (Ixtiyoriy)
                  </label>
                  <input
                    type="text"
                    value={customDeviceName}
                    onChange={(e) => setCustomDeviceName(e.target.value)}
                    placeholder="Masalan: Uy kompyuterim, Ofis PC"
                    maxLength={64}
                    style={{
                      width: "100%",
                      padding: "10px 14px",
                      borderRadius: "10px",
                      backgroundColor: "rgba(255, 255, 255, 0.05)",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      color: "#FFFFFF",
                      fontSize: "13.5px",
                      outline: "none",
                    }}
                  />
                  <p style={{ fontSize: "11px", color: "#64748B", margin: 0 }}>
                    Ushbu nom qurilmalar ro'yxatida va boshqaruv panelida ko'rinadi.
                  </p>
                </div>

                {/* Action button */}
                <div style={{ paddingTop: "8px" }}>
                  <button
                    type="button"
                    onClick={handleFinishPairing}
                    disabled={completingPairing}
                    style={{
                      width: "100%",
                      padding: "11px",
                      borderRadius: "12px",
                      backgroundColor: "#0284C7",
                      border: "1px solid rgba(56, 189, 248, 0.5)",
                      color: "#FFFFFF",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: "pointer",
                      boxShadow: "0 4px 16px rgba(2, 132, 199, 0.3)",
                    }}
                  >
                    {completingPairing ? "Saqlanmoqda..." : "Ulashni Yakunlash ✓"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
