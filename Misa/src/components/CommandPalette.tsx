// ========== CommandPalette.tsx ==========
// Misa AI v9.0 — Global Command Palette (Ctrl+K) — Ultra Glass Edition

import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  SearchIcon,
  HomeIcon,
  ChatIcon,
  CommandsIcon,
  DatabaseIcon,
  SchedulerIcon,
  PluginsIcon,
  SettingsIcon,
  SparklesIcon,
  CloseIcon,
  LaptopIcon,
  RemoteControlIcon,
  TelegramIcon,
} from "./icons/Icons";
import { backendService, CommandItem } from "../services/backendService";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
  onExecuteQuery: (query: string) => void;
}

interface PaletteAction {
  id: string;
  title: string;
  subtitle: string;
  category: string;
  shortcut?: string;
  action: () => void;
  icon: React.ReactNode;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onExecuteQuery,
}) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [dynamicCommands, setDynamicCommands] = useState<CommandItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 40);

      backendService.getCommands().then((res) => {
        if (res.ok && res.commands) {
          setDynamicCommands(res.commands);
        }
      });
    }
  }, [isOpen]);

  const actions = useMemo<PaletteAction[]>(() => {
    const navActions: PaletteAction[] = [
      {
        id: "nav_home",
        title: "Asosiy sahifa (Ish maydoni)",
        subtitle: "Misa AI v9.0 asosiy boshqaruv sahifasiga o'tish",
        category: "Navigatsiya",
        shortcut: "Ctrl+1",
        icon: <HomeIcon size={15} />,
        action: () => {
          onNavigate("/");
          onClose();
        },
      },
      {
        id: "nav_chat",
        title: "AI Suhbat oynasi",
        subtitle: "Misa Neural bilan matnli va ovozli muloqot",
        category: "Navigatsiya",
        shortcut: "Ctrl+2",
        icon: <ChatIcon size={15} />,
        action: () => {
          onNavigate("/chat");
          onClose();
        },
      },
      {
        id: "nav_memory",
        title: "Xotiralar Markazi",
        subtitle: "Saqlangan faktlar, profil va kontekst xotirasi",
        category: "Navigatsiya",
        shortcut: "Ctrl+3",
        icon: <DatabaseIcon size={15} />,
        action: () => {
          onNavigate("/memory");
          onClose();
        },
      },
      {
        id: "nav_scheduler",
        title: "Rejalashtirish Markazi (4-Ko'rinishli Taqvim)",
        subtitle: "Soatlik, Kunlik, Oylik va Yillik rejalar boshqaruvi",
        category: "Navigatsiya",
        shortcut: "Ctrl+4",
        icon: <SchedulerIcon size={15} />,
        action: () => {
          onNavigate("/scheduler");
          onClose();
        },
      },
      {
        id: "nav_commands",
        title: "Buyruqlar Markazi",
        subtitle: "Tizim va avtomatlashtirish buyruqlari katalogi",
        category: "Navigatsiya",
        shortcut: "Ctrl+5",
        icon: <CommandsIcon size={15} />,
        action: () => {
          onNavigate("/commands");
          onClose();
        },
      },
      {
        id: "nav_plugins",
        title: "Plaginlar Katalogi",
        subtitle: "Tashqi kengaytmalar va agent vositalari",
        category: "Navigatsiya",
        shortcut: "Ctrl+6",
        icon: <PluginsIcon size={15} />,
        action: () => {
          onNavigate("/plugins");
          onClose();
        },
      },
      {
        id: "nav_remote",
        title: "Masofaviy Boshqaruv va Ruxsatlar",
        subtitle: "Kompyuter agent ruxsatlari va xavfsizlik jurnali",
        category: "Navigatsiya",
        shortcut: "Ctrl+7",
        icon: <RemoteControlIcon size={15} />,
        action: () => {
          onNavigate("/remote");
          onClose();
        },
      },
      {
        id: "nav_devices",
        title: "Qurilmalar Boshqaruvi",
        subtitle: "Ulangan kompyuterlar va juftlash (Pairing)",
        category: "Navigatsiya",
        shortcut: "Ctrl+8",
        icon: <LaptopIcon size={15} />,
        action: () => {
          onNavigate("/devices");
          onClose();
        },
      },
      {
        id: "nav_account",
        title: "Profil va Sozlamalar",
        subtitle: "Shaxsiy ma'lumotlar, tashqi ko'rinish va xavfsizlik",
        category: "Navigatsiya",
        shortcut: "Ctrl+9",
        icon: <SettingsIcon size={15} />,
        action: () => {
          onNavigate("/account");
          onClose();
        },
      },
      {
        id: "nav_telegram",
        title: "Telegram Bot Integratsiya",
        subtitle: "OTP kod orqali Telegram hisobni ulash",
        category: "Navigatsiya",
        shortcut: "Ctrl+0",
        icon: <TelegramIcon size={15} />,
        action: () => {
          onNavigate("/telegram");
          onClose();
        },
      },
    ];

    const cmdActions: PaletteAction[] = dynamicCommands.map((cmd, idx) => ({
      id: `cmd_${idx}_${cmd.query}`,
      title: cmd.name,
      subtitle: `${cmd.desc} — "${cmd.query}"`,
      category: `Buyruq • ${cmd.category}`,
      icon: <SparklesIcon size={14} color="#E8B3FF" />,
      action: () => {
        onExecuteQuery(cmd.query);
        onClose();
      },
    }));

    return [...navActions, ...cmdActions];
  }, [dynamicCommands, onNavigate, onExecuteQuery, onClose]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return actions.slice(0, 12);
    return actions
      .filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.subtitle.toLowerCase().includes(q) ||
          a.category.toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [actions, query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (filtered.length > 0 ? (prev + 1) % filtered.length : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) =>
          filtered.length > 0 ? (prev - 1 + filtered.length) % filtered.length : 0
        );
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action();
        } else if (query.trim()) {
          onExecuteQuery(query.trim());
          onClose();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filtered, selectedIndex, query, onClose, onExecuteQuery]);

  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(2, 6, 14, 0.78)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        zIndex: 999,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "11vh",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="misa-ultra-glass"
        style={{
          width: "100%",
          maxWidth: "600px",
          background: "rgba(18, 12, 30, 0.94)",
          border: "1px solid rgba(232, 179, 255, 0.24)",
          borderRadius: "22px",
          boxShadow: "0 28px 70px rgba(0, 0, 0, 0.9), 0 0 40px rgba(147, 3, 197, 0.24)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Top Search Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            padding: "16px 20px",
            borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <SearchIcon size={18} color="#C04CFD" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Sahifa, buyruq yoki Misa uchun savol yozing..."
            style={{
              flex: 1,
              fontSize: "14.5px",
              color: "#F5F0FF",
              background: "transparent",
              border: "none",
              outline: "none",
            }}
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              style={{ color: "var(--text-muted)", cursor: "pointer", padding: "2px" }}
            >
              <CloseIcon size={14} />
            </button>
          )}
          <span
            style={{
              fontSize: "10.5px",
              padding: "2px 7px",
              borderRadius: "6px",
              background: "rgba(255, 255, 255, 0.06)",
              color: "var(--text-muted)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
            }}
          >
            ESC
          </span>
        </div>

        {/* Results List */}
        <div
          style={{
            maxHeight: "360px",
            overflowY: "auto",
            padding: "8px",
            display: "flex",
            flexDirection: "column",
            gap: "3px",
          }}
        >
          {filtered.map((item, idx) => {
            const isSelected = idx === selectedIndex;
            return (
              <div
                key={item.id}
                onMouseEnter={() => setSelectedIndex(idx)}
                onClick={item.action}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "12px",
                  cursor: "pointer",
                  background: isSelected
                    ? "linear-gradient(135deg, rgba(147, 3, 197, 0.32) 0%, rgba(192, 76, 253, 0.16) 100%)"
                    : "transparent",
                  border: isSelected
                    ? "1px solid rgba(192, 76, 253, 0.42)"
                    : "1px solid transparent",
                  transition: "all 0.12s ease",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "10px",
                      background: isSelected
                        ? "rgba(192, 76, 253, 0.28)"
                        : "rgba(255, 255, 255, 0.04)",
                      color: isSelected ? "#E8B3FF" : "var(--text-secondary)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    {item.icon}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: "13px",
                        fontWeight: 600,
                        color: isSelected ? "#FFFFFF" : "var(--text-primary)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {item.title}
                    </div>
                    <div
                      style={{
                        fontSize: "11px",
                        color: "var(--text-muted)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {item.subtitle}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
                  <span
                    style={{
                      fontSize: "10px",
                      padding: "2px 8px",
                      borderRadius: "6px",
                      background: "rgba(255, 255, 255, 0.04)",
                      color: "var(--text-secondary)",
                    }}
                  >
                    {item.category}
                  </span>
                  {item.shortcut && (
                    <span
                      style={{
                        fontSize: "10px",
                        padding: "2px 6px",
                        borderRadius: "5px",
                        background: "rgba(147, 3, 197, 0.2)",
                        color: "#E8B3FF",
                        border: "1px solid rgba(192, 76, 253, 0.3)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {item.shortcut}
                    </span>
                  )}
                </div>
              </div>
            );
          })}

          {query.trim() && (
            <div
              onClick={() => {
                onExecuteQuery(query.trim());
                onClose();
              }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "10px 14px",
                borderRadius: "12px",
                cursor: "pointer",
                background:
                  filtered.length === 0
                    ? "rgba(147, 3, 197, 0.24)"
                    : "rgba(255, 255, 255, 0.02)",
                border: "1px dashed rgba(192, 76, 253, 0.38)",
                marginTop: "4px",
              }}
            >
              <SparklesIcon size={15} color="#E8B3FF" />
              <div style={{ fontSize: "12.5px", color: "#E8B3FF" }}>
                Misa AI dan so'rash: <strong>"{query.trim()}"</strong> (Enter)
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "9px 18px",
            borderTop: "1px solid rgba(255, 255, 255, 0.06)",
            background: "rgba(2, 6, 14, 0.55)",
            fontSize: "11px",
            color: "var(--text-muted)",
          }}
        >
          <span>↑↓ Tanlash • Enter Bajarish • Esc Yopish</span>
          <span style={{ color: "#E8B3FF", fontWeight: 600 }}>Misa Command Palette v9.0</span>
        </div>
      </div>
    </div>
  );
};
