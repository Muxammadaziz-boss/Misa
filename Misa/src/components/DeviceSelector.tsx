// ========== DeviceSelector.tsx ==========
// Misa AI v9.4.0 - Grand PC & System Control Center
// Bioluminescent Void & Ultra Glass 480px Kengaytirilgan PC Boshqaruv Markazi

import React, { useState, useEffect, useRef, useCallback } from "react";
import { backendService, UserDevice, SystemMetrics } from "../services/backendService";
import {
  LaptopIcon,
  CheckIcon,
  ExternalLinkIcon,
  CpuIcon,
  RefreshIcon,
  SettingsIcon,
  RemoteControlIcon,
} from "./icons/Icons";

interface DeviceSelectorProps {
  onNavigateToDevices?: () => void;
  onManageDevices?: () => void;
  onNavigateToRemote?: () => void;
  className?: string;
}

const getStatusColor = (status: string): string => {
  switch (status?.toLowerCase()) {
    case "online":
      return "#4EDEA3";
    case "standby":
      return "#F59E0B";
    default:
      return "#6B7280";
  }
};

const getGaugeColor = (pct: number): string => {
  if (pct >= 85) return "#FF5C5C";
  if (pct >= 65) return "#F59E0B";
  return "#4EDEA3";
};

export const DeviceSelector: React.FC<DeviceSelectorProps> = ({
  onNavigateToDevices,
  onManageDevices,
  onNavigateToRemote,
  className = "",
}) => {
  const handleNavigateDevices = onNavigateToDevices || onManageDevices;
  const [devices, setDevices] = useState<UserDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [isRefreshingMetrics, setIsRefreshingMetrics] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchDevices = useCallback(async () => {
    try {
      const res = await backendService.getDevices();
      if (res.ok && res.devices) {
        setDevices(res.devices);
        setSelectedDeviceId(res.selected_device_id || null);
      }
    } catch (err) {
      console.error("Error fetching devices:", err);
    }
  }, []);

  const fetchMetrics = useCallback(async () => {
    try {
      setIsRefreshingMetrics(true);
      const data = await backendService.getSystemMetrics();
      if (data) {
        setMetrics(data);
      }
    } catch (err) {
      console.debug("Telemetry fetch error:", err);
    } finally {
      setIsRefreshingMetrics(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();

    const unsubscribe = backendService.subscribe((msg: any) => {
      if (
        msg.type === "DEVICE_SELECTED" ||
        msg.type === "DEVICE_RENAMED" ||
        msg.type === "DEVICE_REVOKED" ||
        msg.type === "DEVICE_ADDED" ||
        msg.action === "DEVICE_SELECTED" ||
        msg.action === "DEVICE_RENAMED"
      ) {
        fetchDevices();
      }
    });

    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [fetchDevices]);

  // Dropdown ochilganda telemetriyani olish va har 3 soniyada yangilab turish
  useEffect(() => {
    if (isOpen) {
      fetchMetrics();
      const interval = setInterval(fetchMetrics, 3000);
      return () => clearInterval(interval);
    }
  }, [isOpen, fetchMetrics]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleSelect = async (dev: UserDevice) => {
    setLoading(true);
    try {
      const res = await backendService.selectDevice(dev.device_id);
      if (res.ok) {
        setSelectedDeviceId(dev.device_id);
        setIsOpen(false);
      }
    } catch (err) {
      console.error("Error selecting device:", err);
    } finally {
      setLoading(false);
    }
  };

  const selectedDevice = devices.find(
    (d) => d.device_id === selectedDeviceId || d.id === selectedDeviceId
  );

  const displayName = selectedDevice
    ? (selectedDevice.name || "").replace(/\s*\(Joriy kompyuter\)/i, "").trim() || "Kompyuter"
    : "Home (PC)";

  return (
    <div
      ref={dropdownRef}
      className={`misa-device-selector-wrapper ${className}`}
      data-tauri-drag-region="false"
      style={{
        position: "relative",
        display: "inline-block",
        WebkitAppRegion: "no-drag",
      } as React.CSSProperties}
    >
      {/* ── Topbar Trigger Tugmasi (Ishonchli va Drag-Safe) ── */}
      <button
        type="button"
        data-tauri-drag-region="false"
        aria-expanded={isOpen}
        aria-haspopup="true"
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        disabled={loading}
        title="PC va Tizim Sozlamalari (Telemetriya, Masofaviy Boshqaruv)"
        className={`misa-device-btn ${isOpen ? "is-active" : ""}`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "6px 13px",
          borderRadius: "9999px",
          background: isOpen
            ? "linear-gradient(135deg, rgba(147, 3, 197, 0.38) 0%, rgba(78, 222, 163, 0.22) 100%)"
            : "rgba(255, 255, 255, 0.045)",
          border: isOpen
            ? "1px solid rgba(78, 222, 163, 0.55)"
            : "1px solid rgba(255, 255, 255, 0.1)",
          color: isOpen ? "#FFFFFF" : "var(--text-secondary)",
          fontSize: "12px",
          fontWeight: 600,
          cursor: loading ? "wait" : "pointer",
          transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
          backdropFilter: "blur(14px)",
          boxShadow: isOpen ? "0 0 20px rgba(78, 222, 163, 0.35)" : "none",
          WebkitAppRegion: "no-drag",
          userSelect: "none",
        } as React.CSSProperties}
        onMouseEnter={(e) => {
          if (!isOpen) {
            e.currentTarget.style.background = "rgba(147, 3, 197, 0.18)";
            e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.45)";
            e.currentTarget.style.color = "#FFFFFF";
          }
        }}
        onMouseLeave={(e) => {
          if (!isOpen) {
            e.currentTarget.style.background = "rgba(255, 255, 255, 0.045)";
            e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)";
            e.currentTarget.style.color = "var(--text-secondary)";
          }
        }}
      >
        <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
          <LaptopIcon size={14} color="#4EDEA3" />
          <span
            className="misa-beacon-pulse"
            style={{
              position: "absolute",
              top: "-2px",
              right: "-3px",
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: "#4EDEA3",
              boxShadow: "0 0 6px #4EDEA3",
            }}
          />
        </div>

        <span
          className="misa-device-name"
          style={{
            maxWidth: "115px",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontWeight: 600,
            color: "#F5F0FF",
          }}
        >
          {displayName}
        </span>

        <svg
          width="11"
          height="11"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          style={{
            transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s ease",
            opacity: 0.85,
            color: isOpen ? "#4EDEA3" : "currentColor",
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* ── Kengaytirilgan Grand PC & Tizim Boshqaruv Markazi (480px Ultra Glass) ── */}
      {isOpen && (
        <div
          data-tauri-drag-region="false"
          className="misa-ultra-glass misa-device-selector-menu"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => e.stopPropagation()}
          style={{
            position: "absolute",
            top: "calc(100% + 12px)",
            right: 0,
            width: "480px",
            maxWidth: "min(480px, calc(100vw - 28px))",
            borderRadius: "24px",
            background: "rgba(14, 10, 24, 0.98)",
            backdropFilter: "blur(34px) saturate(200%)",
            WebkitBackdropFilter: "blur(34px) saturate(200%)",
            border: "1px solid rgba(232, 179, 255, 0.24)",
            boxShadow:
              "0 28px 80px rgba(2, 6, 14, 0.98), 0 0 50px rgba(147, 3, 197, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.14)",
            zIndex: 1000,
            animation: "misa-fade-in 0.18s cubic-bezier(0.16, 1, 0.3, 1)",
            overflow: "hidden",
            boxSizing: "border-box",
            WebkitAppRegion: "no-drag",
          } as React.CSSProperties}
        >
          {/* 1. Header: Joriy PC Status & Beacon */}
          <div
            style={{
              padding: "16px 20px 14px",
              borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
              background: "linear-gradient(180deg, rgba(147, 3, 197, 0.18) 0%, rgba(2, 6, 14, 0.5) 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "15px",
                  background: "linear-gradient(135deg, rgba(78, 222, 163, 0.25) 0%, rgba(147, 3, 197, 0.4) 100%)",
                  border: "1px solid rgba(78, 222, 163, 0.45)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#4EDEA3",
                  boxShadow: "0 0 18px rgba(78, 222, 163, 0.3)",
                  flexShrink: 0,
                }}
              >
                <LaptopIcon size={22} color="#4EDEA3" />
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h4
                    style={{
                      margin: 0,
                      fontSize: "15px",
                      fontWeight: 700,
                      color: "#FFFFFF",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {displayName}
                  </h4>
                  <span
                    style={{
                      fontSize: "10.5px",
                      padding: "2px 8px",
                      borderRadius: "9999px",
                      background: "rgba(78, 222, 163, 0.16)",
                      border: "1px solid rgba(78, 222, 163, 0.4)",
                      color: "#4EDEA3",
                      fontWeight: 700,
                      letterSpacing: "0.02em",
                    }}
                  >
                    Online
                  </span>
                </div>
                <div
                  style={{
                    fontSize: "11px",
                    color: "var(--text-muted)",
                    marginTop: "3px",
                  }}
                >
                  Asosiy Ish Stansiyasi · Windows 11 x86_64
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={fetchMetrics}
              disabled={isRefreshingMetrics}
              title="Telemetriyani yangilash"
              style={{
                width: "34px",
                height: "34px",
                borderRadius: "11px",
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                color: isRefreshingMetrics ? "#4EDEA3" : "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(147, 3, 197, 0.22)";
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              <RefreshIcon size={15} color="currentColor" />
            </button>
          </div>

          {/* 2. Real-Time Hardware Telemetry Gauges (Katta va Chiroyli Dizayn) */}
          <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255, 255, 255, 0.08)" }}>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "#E8B3FF",
                marginBottom: "12px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>PC Apparat Holati & Telemetriya</span>
              <span style={{ fontSize: "10.5px", color: "var(--text-muted)", fontWeight: 500 }}>
                Real-vaqt monitoringi
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>
              {/* CPU Card */}
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  background: "rgba(255, 255, 255, 0.035)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-secondary)", fontWeight: 600 }}>
                    <CpuIcon size={14} color="#4EDEA3" />
                    CPU Yuklamasi
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 700,
                      color: metrics ? getGaugeColor(metrics.cpu_percent) : "#4EDEA3",
                    }}
                  >
                    {metrics ? `${Math.round(metrics.cpu_percent)}%` : "Tekshirilmoqda..."}
                  </span>
                </div>
                {/* Progress Bar */}
                <div
                  style={{
                    width: "100%",
                    height: "7px",
                    borderRadius: "9999px",
                    background: "rgba(255, 255, 255, 0.08)",
                    marginTop: "10px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: metrics ? `${Math.min(100, Math.max(4, metrics.cpu_percent))}%` : "30%",
                      height: "100%",
                      borderRadius: "9999px",
                      background: metrics
                        ? `linear-gradient(90deg, #4EDEA3 0%, ${getGaugeColor(metrics.cpu_percent)} 100%)`
                        : "linear-gradient(90deg, #4EDEA3, #C04CFD)",
                      transition: "width 0.4s ease",
                      boxShadow: "0 0 10px rgba(78, 222, 163, 0.5)",
                    }}
                  />
                </div>
              </div>

              {/* RAM Card */}
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "16px",
                  background: "rgba(255, 255, 255, 0.035)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 600 }}>
                    RAM Xotira
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 700,
                      color: metrics ? getGaugeColor(metrics.ram_percent) : "#C04CFD",
                    }}
                  >
                    {metrics ? `${Math.round(metrics.ram_percent)}%` : "Tekshirilmoqda..."}
                  </span>
                </div>
                {/* Progress Bar */}
                <div
                  style={{
                    width: "100%",
                    height: "7px",
                    borderRadius: "9999px",
                    background: "rgba(255, 255, 255, 0.08)",
                    marginTop: "10px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: metrics ? `${Math.min(100, Math.max(4, metrics.ram_percent))}%` : "60%",
                      height: "100%",
                      borderRadius: "9999px",
                      background: metrics
                        ? `linear-gradient(90deg, #C04CFD 0%, ${getGaugeColor(metrics.ram_percent)} 100%)`
                        : "linear-gradient(90deg, #C04CFD, #E8B3FF)",
                      transition: "width 0.4s ease",
                      boxShadow: "0 0 10px rgba(192, 76, 253, 0.5)",
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Disk & Tarmoq Sub-bar */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 14px",
                borderRadius: "14px",
                background: "rgba(2, 6, 14, 0.5)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                fontSize: "11.5px",
                color: "var(--text-secondary)",
              }}
            >
              <div>
                <span style={{ color: "var(--text-muted)" }}>Disk Bo'sh: </span>
                <strong style={{ color: "#F5F0FF" }}>
                  {metrics?.disk_free_gb ? `${metrics.disk_free_gb.toFixed(1)} GB` : "240 GB"}
                </strong>
              </div>
              <div style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.12)" }} />
              <div>
                <span style={{ color: "var(--text-muted)" }}>RAM Hajmi: </span>
                <strong style={{ color: "#F5F0FF" }}>
                  {metrics?.ram_used_gb ? `${metrics.ram_used_gb.toFixed(1)} / ${metrics.ram_total_gb.toFixed(1)} GB` : "16 GB"}
                </strong>
              </div>
              <div style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.12)" }} />
              <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4EDEA3" }} />
                <span style={{ color: "#4EDEA3", fontWeight: 600 }}>Port: 18420</span>
              </div>
            </div>
          </div>

          {/* 3. Tezkor Boshqaruv Tugmalari (Quick Actions) */}
          <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255, 255, 255, 0.08)" }}>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-muted)",
                marginBottom: "10px",
              }}
            >
              PC Boshqaruv & Xavfsizlik
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  if (onNavigateToRemote) {
                    onNavigateToRemote();
                  } else if (handleNavigateDevices) {
                    handleNavigateDevices();
                  }
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "9px",
                  padding: "10px 14px",
                  borderRadius: "14px",
                  background: "rgba(147, 3, 197, 0.18)",
                  border: "1px solid rgba(192, 76, 253, 0.38)",
                  color: "#FFFFFF",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  textAlign: "left",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(147, 3, 197, 0.3)";
                  e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.6)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(147, 3, 197, 0.18)";
                  e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.38)";
                }}
              >
                <RemoteControlIcon size={16} color="#E8B3FF" />
                <span>Masofaviy Kirish</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  if (handleNavigateDevices) handleNavigateDevices();
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "9px",
                  padding: "10px 14px",
                  borderRadius: "14px",
                  background: "rgba(255, 255, 255, 0.045)",
                  border: "1px solid rgba(255, 255, 255, 0.09)",
                  color: "var(--text-secondary)",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  textAlign: "left",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.08)";
                  e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.2)";
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.045)";
                  e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.09)";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }}
              >
                <SettingsIcon size={16} color="currentColor" />
                <span>Qurilmalar Markazi</span>
              </button>
            </div>
          </div>

          {/* 4. Ulangan Kompyuterlar Ro'yxati */}
          <div style={{ padding: "14px 20px 16px" }}>
            <div
              style={{
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-muted)",
                marginBottom: "10px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>Ulangan Kompyuterlar</span>
              <span style={{ fontSize: "10.5px", color: "#4EDEA3" }}>
                {devices.length > 0 ? `${devices.length} ta faol` : "Joriy PC"}
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "160px", overflowY: "auto" }}>
              {devices.length === 0 ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "9px 12px",
                    borderRadius: "12px",
                    background: "rgba(78, 222, 163, 0.12)",
                    border: "1px solid rgba(78, 222, 163, 0.35)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <span
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        backgroundColor: "#4EDEA3",
                        boxShadow: "0 0 8px #4EDEA3",
                      }}
                    />
                    <div>
                      <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                        {displayName} (Joriy PC)
                      </div>
                      <div style={{ fontSize: "10.5px", fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                        127.0.0.1 · Standalone Agent Node
                      </div>
                    </div>
                  </div>
                  <CheckIcon size={15} color="#4EDEA3" />
                </div>
              ) : (
                devices.map((dev) => {
                  const isSelected = dev.device_id === selectedDeviceId || dev.id === selectedDeviceId;
                  return (
                    <button
                      key={dev.device_id || dev.id}
                      type="button"
                      onClick={() => handleSelect(dev)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "9px 12px",
                        borderRadius: "12px",
                        textAlign: "left",
                        background: isSelected ? "rgba(78, 222, 163, 0.14)" : "rgba(255, 255, 255, 0.025)",
                        border: isSelected ? "1px solid rgba(78, 222, 163, 0.35)" : "1px solid rgba(255, 255, 255, 0.06)",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.background = "rgba(255, 255, 255, 0.07)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.background = "rgba(255, 255, 255, 0.025)";
                        }
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
                        <span
                          style={{
                            width: "7px",
                            height: "7px",
                            borderRadius: "50%",
                            backgroundColor: getStatusColor(dev.status),
                            boxShadow: `0 0 6px ${getStatusColor(dev.status)}`,
                            flexShrink: 0,
                          }}
                        />
                        <div style={{ minWidth: 0 }}>
                          <div
                            style={{
                              fontSize: "13px",
                              fontWeight: 600,
                              color: isSelected ? "#FFFFFF" : "var(--text-primary)",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {dev.name}
                          </div>
                          <div
                            style={{
                              fontSize: "10.5px",
                              fontFamily: "var(--font-mono)",
                              color: "var(--text-muted)",
                            }}
                          >
                            {dev.device_id}
                          </div>
                        </div>
                      </div>

                      {isSelected && <CheckIcon size={14} color="#4EDEA3" />}
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* 5. Footer Link */}
          {handleNavigateDevices && (
            <div
              style={{
                padding: "10px 20px 14px",
                borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                background: "rgba(2, 6, 14, 0.55)",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  handleNavigateDevices();
                }}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "7px",
                  padding: "9px 14px",
                  borderRadius: "13px",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#4EDEA3",
                  background: "rgba(78, 222, 163, 0.09)",
                  border: "1px solid rgba(78, 222, 163, 0.28)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(78, 222, 163, 0.2)";
                  e.currentTarget.style.borderColor = "rgba(78, 222, 163, 0.5)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(78, 222, 163, 0.09)";
                  e.currentTarget.style.borderColor = "rgba(78, 222, 163, 0.28)";
                }}
              >
                <span>Barcha kompyuter sozlamalarini boshqarish</span>
                <ExternalLinkIcon size={13} color="currentColor" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
