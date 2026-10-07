import React, { useState, useRef, useEffect } from "react";
import { WindowControls } from "../components/WindowControls";
import { Avatar } from "../components/Avatar";
import { DeviceSelector } from "../components/DeviceSelector";
import { MisaLogo } from "../components/MisaLogo";
import {
  HomeIcon,
  ChatIcon,
  CommandsIcon,
  DatabaseIcon,
  SchedulerIcon,
  PluginsIcon,
  RemoteControlIcon,
  LaptopIcon,
  TelegramIcon,
  SearchIcon,
} from "../components/icons/Icons";

interface AppShellProps {
  children: React.ReactNode;
  activePath: string;
  onNavigate: (path: string) => void;
  onOpenCommandPalette?: () => void;
  userName?: string;
  avatarStyle?: string;
  avatarUrl?: string;
}

const PRIMARY_NAV_ITEMS = [
  { path: "/", label: "Asosiy sahifa", icon: HomeIcon },
  { path: "/chat", label: "Suhbat", icon: ChatIcon },
  { path: "/memory", label: "Xotira", icon: DatabaseIcon },
  { path: "/scheduler", label: "Rejalashtirish", icon: SchedulerIcon },
];

const EXTRA_NAV_ITEMS = [
  { path: "/commands", label: "Buyruqlar Markazi", desc: "29+ tizim va AI vositalari", icon: CommandsIcon },
  { path: "/plugins", label: "Plaginlar Katalogi", desc: "Kengaytmalar va integratsiyalar", icon: PluginsIcon },
  { path: "/devices", label: "Qurilmalar", desc: "Ulangan kompyuterlar boshqaruvi", icon: LaptopIcon },
  { path: "/remote", label: "Masofaviy Boshqaruv", desc: "Ruxsatlar va xavfsizlik markazi", icon: RemoteControlIcon },
  { path: "/telegram", label: "Telegram Integratsiya", desc: "OTP ulanish va mobil agent", icon: TelegramIcon },
];

export const AppShell: React.FC<AppShellProps> = ({
  children,
  activePath,
  onNavigate,
  onOpenCommandPalette,
  userName = "Foydalanuvchi",
  avatarStyle = "violet",
  avatarUrl,
}) => {
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement>(null);

  const activeExtraItem = EXTRA_NAV_ITEMS.find((item) => item.path === activePath);

  const handleStartResize = async (direction: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("app_start_resize", { direction });
    } catch {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await (getCurrentWindow() as any).startResizeDragging(direction);
      } catch {
        // Browser fallback
      }
    }
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(e.target as Node)) {
        setMoreMenuOpen(false);
      }
    };
    if (moreMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [moreMenuOpen]);

  return (
    <div
      className="misa-app-shell mikasa-app-shell"
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100vw",
        height: "100vh",
        backgroundColor: "var(--bg-darkest, #06030C)",
        color: "var(--text-primary)",
        overflow: "hidden",
        position: "relative",
        border: "1px solid rgba(232, 179, 255, 0.14)",
        boxSizing: "border-box",
      }}
    >
      {/* 0. Native 8-Direction Window Resize Grips (Borderless Window) */}
      <div
        onMouseDown={(e) => handleStartResize("North", e)}
        style={{ position: "fixed", top: 0, left: 10, right: 10, height: 5, cursor: "ns-resize", zIndex: 9999 }}
      />
      <div
        onMouseDown={(e) => handleStartResize("South", e)}
        style={{ position: "fixed", bottom: 0, left: 10, right: 10, height: 6, cursor: "ns-resize", zIndex: 9999 }}
      />
      <div
        onMouseDown={(e) => handleStartResize("West", e)}
        style={{ position: "fixed", left: 0, top: 10, bottom: 10, width: 5, cursor: "ew-resize", zIndex: 9999 }}
      />
      <div
        onMouseDown={(e) => handleStartResize("East", e)}
        style={{ position: "fixed", right: 0, top: 10, bottom: 10, width: 6, cursor: "ew-resize", zIndex: 9999 }}
      />
      <div
        onMouseDown={(e) => handleStartResize("NorthWest", e)}
        style={{ position: "fixed", top: 0, left: 0, width: 10, height: 10, cursor: "nwse-resize", zIndex: 10000 }}
      />
      <div
        onMouseDown={(e) => handleStartResize("NorthEast", e)}
        style={{ position: "fixed", top: 0, right: 0, width: 10, height: 10, cursor: "nesw-resize", zIndex: 10000 }}
      />
      <div
        onMouseDown={(e) => handleStartResize("SouthWest", e)}
        style={{ position: "fixed", bottom: 0, left: 0, width: 10, height: 10, cursor: "nesw-resize", zIndex: 10000 }}
      />
      <div
        onMouseDown={(e) => handleStartResize("SouthEast", e)}
        style={{ position: "fixed", bottom: 0, right: 0, width: 10, height: 10, cursor: "nwse-resize", zIndex: 10000 }}
      />

      {/* 1. Deep Midnight Canvas & Ambient Violet Glows */}
      <div className="cinematic-bg misa-canvas-bg" />

      {/* 2. Subtle Architectural Micro-Grid Overlay */}
      <div className="cinematic-vignette misa-grid-overlay" />

      {/* 3. FLOATING ULTRA GLASS TOP NAVIGATION BAR (No Sidebar) */}
      <header
        data-tauri-drag-region
        style={{
          position: "relative",
          zIndex: 100,
          width: "100%",
          padding: "10px 14px 6px 14px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "10px",
          flexShrink: 0,
          userSelect: "none",
          boxSizing: "border-box",
        }}
      >
        <nav
          data-tauri-drag-region
          className="misa-ultra-glass mikasa-glass-topnav"
          aria-label="Asosiy navigatsiya"
          style={{
            flex: 1,
            maxWidth: "1320px",
            minWidth: 0,
            margin: "0 auto",
            height: "52px",
            borderRadius: "9999px",
            padding: "0 10px 0 14px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "8px",
            boxSizing: "border-box",
            background: "rgba(24, 13, 36, var(--misa-glass-opacity, 0.62))",
            backdropFilter: "blur(24px) saturate(180%)",
            WebkitBackdropFilter: "blur(24px) saturate(180%)",
            border: "1px solid rgba(232, 179, 255, 0.14)",
            boxShadow:
              "0 20px 50px rgba(2, 6, 14, 0.82), 0 0 30px rgba(147, 3, 197, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.12)",
          }}
        >
          {/* ── LEFT: Misa v9.0 Brand Capsule ── */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              flexShrink: 0,
              ...({ WebkitAppRegion: "no-drag" } as React.CSSProperties),
            }}
          >
            <MisaLogo onClick={() => onNavigate("/")} showVersion={true} />
            <div
              className="misa-topnav-divider"
              style={{
                width: "1px",
                height: "18px",
                background: "rgba(255, 255, 255, 0.1)",
              }}
            />
          </div>

          {/* ── CENTER: Detached Floating Navigation Pills ── */}
          <div
            className="misa-topnav-center mikasa-topnav-center"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "3px",
              padding: "4px",
              borderRadius: "9999px",
              background: "rgba(2, 6, 14, 0.48)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              minWidth: 0,
              flexShrink: 1,
              ...({ WebkitAppRegion: "no-drag" } as React.CSSProperties),
            }}
          >
            {PRIMARY_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activePath === item.path;
              return (
                <button
                  key={item.path}
                  onClick={() => onNavigate(item.path)}
                  aria-current={isActive ? "page" : undefined}
                  title={item.label}
                  className={`misa-nav-pill ${isActive ? "is-active" : ""}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "6px 12px",
                    borderRadius: "9999px",
                    fontSize: "12px",
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                    background: isActive
                      ? "linear-gradient(135deg, rgba(147, 3, 197, 0.36) 0%, rgba(192, 76, 253, 0.22) 100%)"
                      : "transparent",
                    border: isActive
                      ? "1px solid rgba(192, 76, 253, 0.45)"
                      : "1px solid transparent",
                    boxShadow: isActive ? "0 0 18px rgba(147, 3, 197, 0.35)" : "none",
                    cursor: "pointer",
                    transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.color = "#FFFFFF";
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.color = "var(--text-secondary)";
                      e.currentTarget.style.background = "transparent";
                    }
                  }}
                >
                  <Icon size={14} color={isActive ? "#E8B3FF" : "currentColor"} />
                  <span className="misa-topnav-label">{item.label}</span>
                </button>
              );
            })}

            {/* More / System Centers Dropdown Pill */}
            <div ref={moreMenuRef} style={{ position: "relative", flexShrink: 0 }}>
              <button
                type="button"
                onClick={() => setMoreMenuOpen((prev) => !prev)}
                aria-expanded={moreMenuOpen}
                title="Boshqa bo'limlar va vositalar"
                className={`misa-nav-pill ${activeExtraItem ? "is-active" : ""}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                  padding: "6px 11px",
                  borderRadius: "9999px",
                  fontSize: "12px",
                  fontWeight: activeExtraItem ? 600 : 500,
                  color: activeExtraItem || moreMenuOpen ? "#FFFFFF" : "var(--text-secondary)",
                  background: activeExtraItem
                    ? "linear-gradient(135deg, rgba(147, 3, 197, 0.36) 0%, rgba(192, 76, 253, 0.22) 100%)"
                    : moreMenuOpen
                    ? "rgba(255, 255, 255, 0.08)"
                    : "transparent",
                  border: activeExtraItem
                    ? "1px solid rgba(192, 76, 253, 0.45)"
                    : "1px solid transparent",
                  boxShadow: activeExtraItem ? "0 0 18px rgba(147, 3, 197, 0.35)" : "none",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  whiteSpace: "nowrap",
                }}
              >
                {activeExtraItem ? (
                  <>
                    <activeExtraItem.icon size={14} color="#E8B3FF" />
                    <span className="misa-topnav-label">{activeExtraItem.label.split(" ")[0]}</span>
                  </>
                ) : (
                  <>
                    <CommandsIcon size={14} color="currentColor" />
                    <span className="misa-topnav-label">Markazlar</span>
                  </>
                )}
                <svg
                  width="11"
                  height="11"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  style={{
                    transform: moreMenuOpen ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s ease",
                    opacity: 0.75,
                  }}
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>

              {moreMenuOpen && (
                <div
                  className="misa-ultra-glass"
                  style={{
                    position: "absolute",
                    top: "calc(100% + 10px)",
                    right: 0,
                    width: "270px",
                    padding: "8px",
                    borderRadius: "20px",
                    background: "rgba(15, 11, 26, 0.94)",
                    backdropFilter: "blur(28px)",
                    WebkitBackdropFilter: "blur(28px)",
                    border: "1px solid rgba(232, 179, 255, 0.2)",
                    boxShadow: "0 24px 60px rgba(2, 6, 14, 0.92), 0 0 30px rgba(147, 3, 197, 0.2)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px",
                    zIndex: 300,
                    animation: "misa-fade-in 0.16s ease-out",
                  }}
                >
                  <div
                    style={{
                      padding: "6px 10px 4px",
                      fontSize: "10px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "var(--text-muted)",
                    }}
                  >
                    Misa Tizim Markazlari
                  </div>
                  {EXTRA_NAV_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isItemActive = activePath === item.path;
                    return (
                      <button
                        key={item.path}
                        type="button"
                        onClick={() => {
                          setMoreMenuOpen(false);
                          onNavigate(item.path);
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          width: "100%",
                          padding: "9px 11px",
                          borderRadius: "12px",
                          textAlign: "left",
                          background: isItemActive ? "rgba(147, 3, 197, 0.22)" : "transparent",
                          border: isItemActive
                            ? "1px solid rgba(192, 76, 253, 0.38)"
                            : "1px solid transparent",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={(e) => {
                          if (!isItemActive) {
                            e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isItemActive) {
                            e.currentTarget.style.background = "transparent";
                          }
                        }}
                      >
                        <div
                          style={{
                            width: "30px",
                            height: "30px",
                            borderRadius: "9px",
                            background: isItemActive
                              ? "rgba(192, 76, 253, 0.25)"
                              : "rgba(255, 255, 255, 0.05)",
                            border: "1px solid rgba(255, 255, 255, 0.08)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: isItemActive ? "#E8B3FF" : "var(--text-secondary)",
                            flexShrink: 0,
                          }}
                        >
                          <Icon size={15} color="currentColor" />
                        </div>
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div
                            style={{
                              fontSize: "12.5px",
                              fontWeight: 600,
                              color: isItemActive ? "#FFFFFF" : "var(--text-primary)",
                            }}
                          >
                            {item.label}
                          </div>
                          <div
                            style={{
                              fontSize: "10.5px",
                              color: "var(--text-muted)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {item.desc}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ── RIGHT: Search Pill (Ctrl+K), Device Selector & Profile Pill ── */}
          <div
            className="misa-topnav-right"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              flexShrink: 0,
              minWidth: 0,
              ...({ WebkitAppRegion: "no-drag" } as React.CSSProperties),
            }}
          >
            {/* Command Palette Trigger Pill */}
            <button
              type="button"
              onClick={onOpenCommandPalette}
              title="Tezkor qidiruv va buyruqlar (Ctrl+K)"
              className="misa-search-btn"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "5px 10px",
                borderRadius: "9999px",
                background: "rgba(255, 255, 255, 0.035)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                color: "var(--text-secondary)",
                fontSize: "12px",
                cursor: "pointer",
                transition: "all 0.2s ease",
                flexShrink: 0,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(147, 3, 197, 0.14)";
                e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.35)";
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.035)";
                e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.08)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              <SearchIcon size={13} color="currentColor" />
              <span className="misa-search-text">Qidirish...</span>
              <kbd
                className="misa-search-kbd"
                style={{
                  fontSize: "10px",
                  fontFamily: "var(--font-mono)",
                  padding: "1px 5px",
                  borderRadius: "4px",
                  background: "rgba(255, 255, 255, 0.08)",
                  color: "var(--text-muted)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                Ctrl+K
              </kbd>
            </button>

            <DeviceSelector onManageDevices={() => onNavigate("/devices")} />

            {/* User Profile Pill (without extra settings gear icon) */}
            <button
              type="button"
              onClick={() => onNavigate("/account")}
              title="Profil va Sozlamalar"
              className="misa-profile-btn"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "4px 6px 4px 12px",
                borderRadius: "9999px",
                background:
                  activePath === "/account"
                    ? "linear-gradient(135deg, rgba(147, 3, 197, 0.36) 0%, rgba(192, 76, 253, 0.2) 100%)"
                    : "rgba(255, 255, 255, 0.04)",
                border:
                  activePath === "/account"
                    ? "1px solid rgba(192, 76, 253, 0.45)"
                    : "1px solid rgba(255, 255, 255, 0.1)",
                cursor: "pointer",
                transition: "all 0.2s ease",
                flexShrink: 0,
              }}
              onMouseEnter={(e) => {
                if (activePath !== "/account") {
                  e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.35)";
                  e.currentTarget.style.background = "rgba(147, 3, 197, 0.12)";
                }
              }}
              onMouseLeave={(e) => {
                if (activePath !== "/account") {
                  e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)";
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.04)";
                }
              }}
            >
              <span
                className="misa-user-name-label"
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "#F5F0FF",
                  maxWidth: "160px",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {userName}
              </span>
              <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
                <Avatar name={userName} size="sm" styleId={avatarStyle} avatarUrl={avatarUrl} />
                <span
                  style={{
                    position: "absolute",
                    bottom: "-1px",
                    right: "-1px",
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: "#4EDEA3",
                    border: "1.5px solid #02060E",
                    boxShadow: "0 0 6px rgba(78, 222, 163, 0.8)",
                  }}
                />
              </div>
            </button>
          </div>
        </nav>

        {/* Detached Native Window Controls (outside nav pill, always visible) */}
        <WindowControls />
      </header>

      {/* 4. FULL-BLEED WORKSPACE STAGE */}
      <main
        style={{
          flex: 1,
          position: "relative",
          zIndex: 10,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {children}
      </main>
    </div>
  );
};
