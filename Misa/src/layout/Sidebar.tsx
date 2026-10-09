import React, { useState, useEffect } from "react";
import {
  HomeIcon,
  ChatIcon,
  CommandsIcon,
  MemoryIcon,
  SchedulerIcon,
  PluginsIcon,
  RemoteControlIcon,
  TelegramIcon,
  LaptopIcon,
  CollapseSidebarIcon,
  ExpandSidebarIcon,
  SearchIcon,
} from "../components/icons/Icons";
import { MikasaLogo } from "../components/MikasaLogo";
import { AccountRow } from "./AccountRow";
import { backendService, BackendStatus } from "../services/backendService";

export interface NavItemDef {
  id: string;
  path: string;
  label: string;
  icon: React.ComponentType<{ size?: number; color?: string }>;
}

export interface NavSectionDef {
  title: string;
  items: NavItemDef[];
}

export const NAV_SECTIONS: NavSectionDef[] = [
  {
    title: "ASOSIY",
    items: [
      { id: "home", path: "/", label: "Home", icon: HomeIcon },
      { id: "chat", path: "/chat", label: "AI Suhbat", icon: ChatIcon },
    ],
  },
  {
    title: "INTELLIGENCE",
    items: [
      { id: "commands", path: "/commands", label: "Buyruqlar", icon: CommandsIcon },
      { id: "memory", path: "/memory", label: "Xotira", icon: MemoryIcon },
    ],
  },
  {
    title: "SYSTEM",
    items: [
      { id: "scheduler", path: "/scheduler", label: "Rejalashtiruvchi", icon: SchedulerIcon },
      { id: "plugins", path: "/plugins", label: "Plaginlar", icon: PluginsIcon },
      { id: "devices", path: "/devices", label: "Qurilmalar", icon: LaptopIcon },
      { id: "remote", path: "/remote", label: "Masofaviy Boshqaruv", icon: RemoteControlIcon },
      { id: "telegram", path: "/telegram", label: "Telegram Bot", icon: TelegramIcon },
    ],
  },
];

interface SidebarProps {
  currentPath: string;
  userName?: string;
  userAvatar?: string;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onNavigate: (path: string) => void;
  onOpenCommandPalette?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPath,
  userName = "Ustoz",
  userAvatar,
  collapsed = false,
  onToggleCollapse,
  onNavigate,
  onOpenCommandPalette,
}) => {
  const [backendState, setBackendState] = useState<"online" | "offline" | "connecting">("connecting");

  useEffect(() => {
    const unsub = backendService.onStatusChange((status: BackendStatus) => {
      setBackendState(status.status);
    });
    return () => unsub();
  }, []);

  return (
    <aside
      className="mikasa-sidebar"
      style={{
        width: collapsed ? "var(--sidebar-width-collapsed)" : "var(--sidebar-width-expanded)",
        height: "100%",
        backgroundColor: "var(--surface)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: collapsed ? "16px 8px 14px 8px" : "16px 12px 14px 12px",
        userSelect: "none",
        flexShrink: 0,
        zIndex: 20,
        transition: "width 0.22s cubic-bezier(0.4, 0, 0.2, 1), padding 0.22s ease",
      }}
    >
      {/* Top Header & Navigation */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* Sidebar Header: Logo + Collapse Button */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "space-between",
            padding: collapsed ? "0" : "0 4px",
            minHeight: "36px",
          }}
        >
          <MikasaLogo compact={collapsed} onClick={() => onNavigate("/")} />

          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              title={collapsed ? "Yon panelni kengaytirish" : "Yon panelni yig‘ish"}
              aria-label={collapsed ? "Yon panelni kengaytirish" : "Yon panelni yig‘ish"}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "28px",
                height: "28px",
                borderRadius: "8px",
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                color: "var(--text-secondary)",
                cursor: "pointer",
                transition: "all 0.15s ease",
                flexShrink: 0,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.1)";
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              {collapsed ? (
                <ExpandSidebarIcon size={13} color="currentColor" />
              ) : (
                <CollapseSidebarIcon size={13} color="currentColor" />
              )}
            </button>
          )}
        </div>

        {/* Quick Search / Command Palette Button */}
        {onOpenCommandPalette && (
          <button
            onClick={onOpenCommandPalette}
            title={collapsed ? "Qidiruv va buyruqlar (Ctrl+K)" : undefined}
            aria-label="Buyruqlar palitrasi va qidiruv (Ctrl+K)"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: collapsed ? "center" : "space-between",
              padding: collapsed ? "8px" : "8px 12px",
              borderRadius: "8px",
              backgroundColor: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              color: "var(--text-muted, #94A3B8)",
              cursor: "pointer",
              fontSize: "13px",
              transition: "all 0.15s ease",
              width: "100%",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.08)";
              e.currentTarget.style.color = "#FFFFFF";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.04)";
              e.currentTarget.style.color = "var(--text-muted, #94A3B8)";
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <SearchIcon size={15} color="currentColor" />
              {!collapsed && <span>Qidiruv...</span>}
            </div>
            {!collapsed && (
              <kbd
                style={{
                  fontSize: "10px",
                  backgroundColor: "rgba(255, 255, 255, 0.06)",
                  padding: "2px 5px",
                  borderRadius: "4px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  color: "var(--text-muted, #94A3B8)",
                }}
              >
                Ctrl+K
              </kbd>
            )}
          </button>
        )}

        {/* Navigation Sections */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", overflowY: "auto", overflowX: "hidden" }}>
          {NAV_SECTIONS.map((section, sIdx) => (
            <div key={sIdx} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              {section.title && !collapsed && (
                <span
                  style={{
                    fontSize: "var(--font-size-label)",
                    fontWeight: 700,
                    color: "var(--text-muted)",
                    letterSpacing: "0.09em",
                    padding: "6px 12px 2px 12px",
                  }}
                >
                  {section.title}
                </span>
              )}

              {section.items.map((item) => {
                const isActive = currentPath === item.path;
                const IconComp = item.icon;

                return (
                  <button
                    key={item.id}
                    onClick={() => onNavigate(item.path)}
                    title={collapsed ? item.label : undefined}
                    aria-label={item.label}
                    aria-current={isActive ? "page" : undefined}
                    style={{
                      position: "relative",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: collapsed ? "center" : "flex-start",
                      gap: "12px",
                      padding: collapsed ? "10px 0" : "9px 12px",
                      borderRadius: "12px",
                      backgroundColor: isActive
                        ? "rgba(14, 25, 45, 0.75)"
                        : "transparent",
                      border: isActive
                        ? "1px solid rgba(56, 189, 248, 0.35)"
                        : "1px solid transparent",
                      boxShadow: isActive
                        ? "0 0 16px rgba(2, 132, 199, 0.22), inset 0 1px 1px rgba(255, 255, 255, 0.1)"
                        : "none",
                      color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                      fontWeight: isActive ? 600 : 500,
                      fontSize: "13.5px",
                      transition: "all 0.15s ease",
                      cursor: "pointer",
                      width: "100%",
                      textAlign: "left",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.05)";
                        e.currentTarget.style.color = "#FFFFFF";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.backgroundColor = "transparent";
                        e.currentTarget.style.color = "var(--text-secondary)";
                      }
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: "24px",
                        height: "24px",
                        borderRadius: "7px",
                        backgroundColor: isActive ? "rgba(2, 132, 199, 0.25)" : "transparent",
                        flexShrink: 0,
                      }}
                    >
                      <IconComp
                        size={17}
                        color={isActive ? "var(--primary-glow)" : "rgba(255, 255, 255, 0.6)"}
                      />
                    </div>

                    {!collapsed && (
                      <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {item.label}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom User Account & App Readiness Status */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px", paddingTop: "8px" }}>
        <AccountRow
          name={userName}
          avatarStyle={userAvatar}
          collapsed={collapsed}
          active={currentPath === "/account"}
          onClick={() => onNavigate("/account")}
        />

        {/* Real Dynamic Status Indicator */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "flex-start",
            gap: "8px",
            padding: collapsed ? "4px 0" : "4px 8px",
            fontSize: "11.5px",
            color: "var(--text-muted)",
          }}
          title={
            backendState === "online"
              ? "Misa: Tayyor (Backend barqaror ishlamoqda)"
              : backendState === "connecting"
              ? "Misa: Ulanmoqda..."
              : "Misa: Backend oflayn"
          }
        >
          <div
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              backgroundColor:
                backendState === "online"
                  ? "var(--success)"
                  : backendState === "connecting"
                  ? "var(--warning)"
                  : "var(--error)",
              boxShadow:
                backendState === "online"
                  ? "0 0 8px rgba(16, 185, 129, 0.6)"
                  : backendState === "connecting"
                  ? "0 0 8px rgba(245, 158, 11, 0.6)"
                  : "0 0 8px rgba(239, 68, 68, 0.6)",
              flexShrink: 0,
            }}
          />
          {!collapsed && (
            <span>
              {backendState === "online"
                ? "Misa: Tayyor"
                : backendState === "connecting"
                ? "Ulanmoqda..."
                : "Oflayn"}
            </span>
          )}
        </div>
      </div>
    </aside>
  );
};
