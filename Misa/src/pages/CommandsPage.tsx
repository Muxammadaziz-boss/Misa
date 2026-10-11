// ========== CommandsPage.tsx ==========
// Misa AI v9.0.0 — Tizim va Avtomatlashtirish Buyruqlari Markazi
// Real ToolRegistry vositalari (29 tool) va tezkor tizim buyruqlari integratsiyasi

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  CommandsIcon,
  HomeIcon,
  SparklesIcon,
  ArrowUpIcon,
  CloseIcon,
  SearchIcon,
  GridIcon,
  ListIcon,
  PlayIcon,
  VolumeIcon,
  CalculatorIcon,
  GlobeIcon,
  FolderIcon,
  ClockIcon,
  SunIcon,
  DollarIcon,
  CodeIcon,
  DatabaseIcon,
  CameraIcon,
  BellIcon,
  SendIcon,
  CpuIcon,
  CheckIcon,
  CopyIcon,
  TerminalIcon,
  SettingsIcon,
  SchedulerIcon,
  ChatIcon,
} from "../components/icons/Icons";
import {
  backendService,
  CommandItem,
  CommandsResponse,
} from "../services/backendService";

interface CommandsPageProps {
  onNavigateHome: () => void;
}

// Icon resolver helper with clean SVG mappings
const renderCommandIcon = (iconName: string, size = 16, color = "currentColor") => {
  switch (iconName) {
    case "cpu":
      return <CpuIcon size={size} color={color} />;
    case "check":
      return <CheckIcon size={size} color={color} />;
    case "volume":
    case "volume-1":
    case "volume-2":
    case "volume-x":
      return <VolumeIcon size={size} color={color} />;
    case "terminal":
      return <TerminalIcon size={size} color={color} />;
    case "folder":
      return <FolderIcon size={size} color={color} />;
    case "calculator":
      return <CalculatorIcon size={size} color={color} />;
    case "dollar-sign":
      return <DollarIcon size={size} color={color} />;
    case "sun":
    case "cloud":
      return <SunIcon size={size} color={color} />;
    case "play":
    case "video":
      return <PlayIcon size={size} color={color} />;
    case "search":
      return <SearchIcon size={size} color={color} />;
    case "database":
      return <DatabaseIcon size={size} color={color} />;
    case "clock":
      return <ClockIcon size={size} color={color} />;
    case "calendar":
      return <SchedulerIcon size={size} color={color} />;
    case "code":
      return <CodeIcon size={size} color={color} />;
    case "chat":
      return <ChatIcon size={size} color={color} />;
    case "camera":
      return <CameraIcon size={size} color={color} />;
    case "bell":
      return <BellIcon size={size} color={color} />;
    case "send":
      return <SendIcon size={size} color={color} />;
    case "copy":
      return <CopyIcon size={size} color={color} />;
    case "globe":
      return <GlobeIcon size={size} color={color} />;
    case "settings":
      return <SettingsIcon size={size} color={color} />;
    case "commands":
    default:
      return <CommandsIcon size={size} color={color} />;
  }
};

const getCategoryColor = (category: string) => {
  switch (category.toLowerCase()) {
    case "tizim":
      return { bg: "rgba(59, 130, 246, 0.12)", text: "#60a5fa", border: "rgba(59, 130, 246, 0.25)" };
    case "ilovalar":
      return { bg: "rgba(16, 185, 129, 0.12)", text: "#34d399", border: "rgba(16, 185, 129, 0.25)" };
    case "utilitlar":
      return { bg: "rgba(245, 158, 11, 0.12)", text: "#fbbf24", border: "rgba(245, 158, 11, 0.25)" };
    case "ma'lumot":
      return { bg: "rgba(139, 92, 246, 0.12)", text: "#a78bfa", border: "rgba(139, 92, 246, 0.25)" };
    case "multimedia":
      return { bg: "rgba(236, 72, 153, 0.12)", text: "#f472b6", border: "rgba(236, 72, 153, 0.25)" };
    case "internet":
      return { bg: "rgba(14, 165, 233, 0.12)", text: "#38bdf8", border: "rgba(14, 165, 233, 0.25)" };
    case "xotira":
      return { bg: "rgba(168, 85, 247, 0.12)", text: "#c084fc", border: "rgba(168, 85, 247, 0.25)" };
    case "rejalashtirish":
      return { bg: "rgba(20, 184, 166, 0.12)", text: "#2dd4bf", border: "rgba(20, 184, 166, 0.25)" };
    case "dasturlash":
      return { bg: "rgba(239, 68, 68, 0.12)", text: "#f87171", border: "rgba(239, 68, 68, 0.25)" };
    case "interaktiv":
      return { bg: "rgba(99, 102, 241, 0.12)", text: "#818cf8", border: "rgba(99, 102, 241, 0.25)" };
    default:
      return { bg: "rgba(255, 255, 255, 0.06)", text: "var(--text-secondary)", border: "var(--border-subtle)" };
  }
};

// Reusable Memoized Command Card (Grid Mode)
interface CardProps {
  cmd: CommandItem;
  isExecuting: boolean;
  onExecute: (query: string, params?: Record<string, any>) => void;
  onInspect: (cmd: CommandItem) => void;
}

const CommandGridCard = React.memo<CardProps>(({ cmd, isExecuting, onExecute, onInspect }) => {
  const catStyle = getCategoryColor(cmd.category);
  const paramCount = cmd.parameters ? Object.keys(cmd.parameters).length : 0;

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 12,
        padding: "16px 18px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: 12,
        transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(59, 130, 246, 0.35)";
        e.currentTarget.style.background = "rgba(18, 24, 38, 0.95)";
        e.currentTarget.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--border-subtle)";
        e.currentTarget.style.background = "var(--surface)";
        e.currentTarget.style.transform = "translateY(0)";
      }}
    >
      <div>
        {/* Header Row */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 7,
                background: catStyle.bg,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: catStyle.text,
              }}
            >
              {renderCommandIcon(cmd.icon, 15, catStyle.text)}
            </div>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
              {cmd.name}
            </span>
          </div>
          <span
            style={{
              fontSize: 10,
              padding: "2px 7px",
              borderRadius: 6,
              background: catStyle.bg,
              color: catStyle.text,
              border: `1px solid ${catStyle.border}`,
              fontWeight: 500,
            }}
          >
            {cmd.category}
          </span>
        </div>

        {/* Description */}
        <p
          style={{
            margin: "0 0 10px",
            fontSize: 12,
            color: "var(--text-secondary)",
            lineHeight: 1.45,
            minHeight: 34,
          }}
        >
          {cmd.desc}
        </p>

        {/* Query & Parameter Badges */}
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <code
            style={{
              fontSize: 11,
              color: "var(--secondary)",
              background: "rgba(59, 130, 246, 0.08)",
              padding: "2px 6px",
              borderRadius: 4,
              border: "1px solid rgba(59, 130, 246, 0.2)",
            }}
          >
            {cmd.query}
          </code>

          {cmd.is_tool && (
            <span
              style={{
                fontSize: 10,
                padding: "2px 6px",
                borderRadius: 4,
                background: "rgba(147, 51, 234, 0.12)",
                color: "#c084fc",
                border: "1px solid rgba(147, 51, 234, 0.25)",
                fontWeight: 500,
              }}
            >
              Tool
            </span>
          )}

          {paramCount > 0 && (
            <button
              onClick={() => onInspect(cmd)}
              title="Parametrlarni ko'rish va sozlash"
              style={{
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 4,
                padding: "1px 6px",
                fontSize: 10,
                color: "var(--text-muted)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "var(--text-primary)")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
            >
              {paramCount} ta parametr
            </button>
          )}
        </div>
      </div>

      {/* Action Row */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          alignItems: "center",
          gap: 8,
          borderTop: "1px solid rgba(255, 255, 255, 0.04)",
          paddingTop: 10,
        }}
      >
        {paramCount > 0 && (
          <button
            onClick={() => onInspect(cmd)}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-secondary)",
              fontSize: 12,
              cursor: "pointer",
              padding: "4px 8px",
            }}
          >
            Sozlash
          </button>
        )}
        <button
          onClick={() => onExecute(cmd.query)}
          disabled={isExecuting}
          style={{
            background: isExecuting
              ? "rgba(59, 130, 246, 0.2)"
              : "rgba(59, 130, 246, 0.12)",
            border: "1px solid rgba(59, 130, 246, 0.3)",
            color: "var(--secondary)",
            borderRadius: 8,
            padding: "6px 14px",
            fontSize: 12,
            fontWeight: 500,
            cursor: isExecuting ? "default" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            if (!isExecuting) {
              e.currentTarget.style.background = "var(--secondary)";
              e.currentTarget.style.color = "#ffffff";
            }
          }}
          onMouseLeave={(e) => {
            if (!isExecuting) {
              e.currentTarget.style.background = "rgba(59, 130, 246, 0.12)";
              e.currentTarget.style.color = "var(--secondary)";
            }
          }}
        >
          <PlayIcon size={11} color="currentColor" />
          <span>{isExecuting ? "Bajarilmoqda..." : "Bajarish"}</span>
        </button>
      </div>
    </div>
  );
});

// Reusable Memoized Command Row (List Mode)
const CommandListRow = React.memo<CardProps>(({ cmd, isExecuting, onExecute, onInspect }) => {
  const catStyle = getCategoryColor(cmd.category);
  const paramCount = cmd.parameters ? Object.keys(cmd.parameters).length : 0;

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 10,
        padding: "12px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        transition: "all 0.15s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(59, 130, 246, 0.35)";
        e.currentTarget.style.background = "rgba(18, 24, 38, 0.95)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "var(--border-subtle)";
        e.currentTarget.style.background = "var(--surface)";
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 0 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: catStyle.bg,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: catStyle.text,
            flexShrink: 0,
          }}
        >
          {renderCommandIcon(cmd.icon, 16, catStyle.text)}
        </div>

        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              {cmd.name}
            </span>
            <code
              style={{
                fontSize: 10,
                color: "var(--secondary)",
                background: "rgba(59, 130, 246, 0.08)",
                padding: "1px 5px",
                borderRadius: 4,
              }}
            >
              {cmd.query}
            </code>
          </div>
          <p
            style={{
              margin: 0,
              fontSize: 11,
              color: "var(--text-secondary)",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {cmd.desc}
          </p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
        <span
          style={{
            fontSize: 10,
            padding: "2px 8px",
            borderRadius: 6,
            background: catStyle.bg,
            color: catStyle.text,
            border: `1px solid ${catStyle.border}`,
            fontWeight: 500,
          }}
        >
          {cmd.category}
        </span>

        {paramCount > 0 && (
          <button
            onClick={() => onInspect(cmd)}
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 6,
              padding: "4px 8px",
              fontSize: 11,
              color: "var(--text-secondary)",
              cursor: "pointer",
            }}
          >
            Parametrlar
          </button>
        )}

        <button
          onClick={() => onExecute(cmd.query)}
          disabled={isExecuting}
          style={{
            background: isExecuting
              ? "rgba(59, 130, 246, 0.2)"
              : "rgba(59, 130, 246, 0.12)",
            border: "1px solid rgba(59, 130, 246, 0.3)",
            color: "var(--secondary)",
            borderRadius: 6,
            padding: "5px 12px",
            fontSize: 11,
            fontWeight: 500,
            cursor: isExecuting ? "default" : "pointer",
            display: "flex",
            alignItems: "center",
            gap: 5,
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            if (!isExecuting) {
              e.currentTarget.style.background = "var(--secondary)";
              e.currentTarget.style.color = "#ffffff";
            }
          }}
          onMouseLeave={(e) => {
            if (!isExecuting) {
              e.currentTarget.style.background = "rgba(59, 130, 246, 0.12)";
              e.currentTarget.style.color = "var(--secondary)";
            }
          }}
        >
          <PlayIcon size={10} color="currentColor" />
          <span>{isExecuting ? "..." : "Bajarish"}</span>
        </button>
      </div>
    </div>
  );
});

// Main CommandsPage Component
export const CommandsPage: React.FC<CommandsPageProps> = ({ onNavigateHome }) => {
  const [commands, setCommands] = useState<CommandItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("Barchasi");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [debouncedQuery, setDebouncedQuery] = useState<string>("");
  const [sortMode, setSortMode] = useState<"name_asc" | "name_desc" | "category">("name_asc");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [customCommand, setCustomCommand] = useState<string>("");
  const [isExecuting, setIsExecuting] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<{
    command: string;
    message: string;
    success: boolean;
    timestamp: string;
  } | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [visibleLimit, setVisibleLimit] = useState<number>(36);

  // Inspector Modal State
  const [activeInspectTool, setActiveInspectTool] = useState<CommandItem | null>(null);
  const [toolParamValues, setToolParamValues] = useState<Record<string, any>>({});
  const [copiedResult, setCopiedResult] = useState<boolean>(false);

  // Debounce search input (150ms) for high-performance typing across 1000 items
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 150);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  useEffect(() => {
    if (!activeInspectTool) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveInspectTool(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeInspectTool]);

  // Load commands from backend
  const fetchCommands = useCallback(async () => {
    let mounted = true;
    setLoading(true);
    setLoadError(null);
    try {
      const res: CommandsResponse = await backendService.getCommands();
      if (mounted) {
        setCommands(res.commands || []);
        setCategories(res.categories || ["Barchasi"]);
      }
    } catch (err: any) {
      if (mounted) {
        setLoadError(err.message || "Backend serveriga ulanib bo'lmadi");
      }
    } finally {
      if (mounted) setLoading(false);
    }
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    fetchCommands();
  }, [fetchCommands]);

  // Pre-index commands for instant multi-term search
  const indexedCommands = useMemo(() => {
    return commands.map((c) => ({
      ...c,
      _searchIndex: `${c.name} ${c.query} ${c.desc} ${c.category} ${c.tool_name || ""}`.toLowerCase(),
    }));
  }, [commands]);

  // Category counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { Barchasi: commands.length };
    for (const cmd of commands) {
      counts[cmd.category] = (counts[cmd.category] || 0) + 1;
    }
    return counts;
  }, [commands]);

  // Filter & Sort
  const filteredCommands = useMemo(() => {
    let result = indexedCommands;

    // Filter category
    if (selectedCategory !== "Barchasi") {
      result = result.filter(
        (cmd) => cmd.category.toLowerCase() === selectedCategory.toLowerCase()
      );
    }

    // Filter search terms
    const trimmedQuery = debouncedQuery.trim().toLowerCase();
    if (trimmedQuery) {
      const terms = trimmedQuery.split(/\s+/);
      result = result.filter((cmd) =>
        terms.every((term) => cmd._searchIndex.includes(term))
      );
    }

    // Sort
    const sorted = [...result];
    if (sortMode === "name_asc") {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortMode === "name_desc") {
      sorted.sort((a, b) => b.name.localeCompare(a.name));
    } else if (sortMode === "category") {
      sorted.sort((a, b) => a.category.localeCompare(b.category));
    }

    return sorted;
  }, [indexedCommands, selectedCategory, debouncedQuery, sortMode]);

  // Visible sliced list (prevents DOM thrashing on large datasets)
  const visibleCommands = useMemo(() => {
    return filteredCommands.slice(0, visibleLimit);
  }, [filteredCommands, visibleLimit]);

  // Command Execution Handler
  const handleExecute = useCallback(
    async (cmdQuery: string, params?: Record<string, any>) => {
      if (!cmdQuery.trim() || isExecuting) return;
      setIsExecuting(cmdQuery);
      setExecutionResult(null);

      const res = await backendService.executeCommand(cmdQuery, params);
      setExecutionResult({
        command: cmdQuery,
        message: res.result || (res.ok ? "Buyruq muvaffaqiyatli bajarildi" : "Xatolik yuz berdi"),
        success: res.ok,
        timestamp: new Date().toLocaleTimeString(),
      });
      setIsExecuting(null);

      if (activeInspectTool) {
        setActiveInspectTool(null);
      }
    },
    [isExecuting, activeInspectTool]
  );

  // Parameter Inspector Open
  const handleOpenInspector = useCallback((cmd: CommandItem) => {
    setActiveInspectTool(cmd);
    const initialParams: Record<string, any> = {};
    if (cmd.parameters) {
      for (const [key, meta] of Object.entries(cmd.parameters)) {
        initialParams[key] = (meta as any).default ?? "";
      }
    }
    setToolParamValues(initialParams);
  }, []);

  // Copy result to clipboard
  const handleCopyResult = () => {
    if (!executionResult) return;
    navigator.clipboard.writeText(executionResult.message);
    setCopiedResult(true);
    setTimeout(() => setCopiedResult(false), 2000);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        background: "var(--bg-gradient)",
        color: "var(--text-primary)",
        overflowY: "auto",
        position: "relative",
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 28px",
          borderBottom: "1px solid var(--border-subtle)",
          background: "rgba(10, 15, 29, 0.85)",
          backdropFilter: "blur(20px)",
          position: "sticky",
          top: 0,
          zIndex: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              background: "rgba(59, 130, 246, 0.15)",
              border: "1px solid rgba(59, 130, 246, 0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <CommandsIcon size={20} color="var(--secondary)" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ margin: 0, fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em" }}>
                Buyruqlar Markazi
              </h1>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 12,
                  background: "rgba(59, 130, 246, 0.15)",
                  color: "var(--secondary)",
                  fontWeight: 500,
                  border: "1px solid rgba(59, 130, 246, 0.2)",
                }}
              >
                {commands.length} ta buyruq
              </span>
            </div>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
              ToolRegistry vositalari, tizim dispetcheri va tezkor Windows amallari
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {/* Grid / List View Toggle */}
          <div
            style={{
              display: "flex",
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 8,
              padding: 2,
            }}
          >
            <button
              onClick={() => setViewMode("grid")}
              title="Katakchalar (Grid)"
              style={{
                background: viewMode === "grid" ? "rgba(59, 130, 246, 0.2)" : "transparent",
                color: viewMode === "grid" ? "var(--secondary)" : "var(--text-muted)",
                border: "none",
                borderRadius: 6,
                padding: "6px 8px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
              }}
            >
              <GridIcon size={14} color="currentColor" />
            </button>
            <button
              onClick={() => setViewMode("list")}
              title="Ro'yxat (List)"
              style={{
                background: viewMode === "list" ? "rgba(59, 130, 246, 0.2)" : "transparent",
                color: viewMode === "list" ? "var(--secondary)" : "var(--text-muted)",
                border: "none",
                borderRadius: 6,
                padding: "6px 8px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
              }}
            >
              <ListIcon size={14} color="currentColor" />
            </button>
          </div>

          <button
            onClick={onNavigateHome}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-secondary)",
              padding: "8px 14px",
              borderRadius: 8,
              fontSize: 12,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "var(--text-primary)";
              e.currentTarget.style.borderColor = "var(--border-strong)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--text-secondary)";
              e.currentTarget.style.borderColor = "var(--border-subtle)";
            }}
          >
            <HomeIcon size={14} />
            <span>Bosh sahifa</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div
        style={{
          maxWidth: 1140,
          width: "100%",
          margin: "0 auto",
          padding: "24px 28px 48px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        {/* Instant Execution Prompt Box */}
        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: 14,
            padding: "16px 20px",
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 500 }}>
            <SparklesIcon size={15} color="var(--primary-glow)" />
            <span>Ixtiyoriy buyruq yoki Tool'ni sinab ko'rish</span>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <input
              type="text"
              placeholder="Masalan: system_info, calculator 25 * 4, weather Toshkent, currency USD UZS, telegram, skrinshot..."
              value={customCommand}
              onChange={(e) => setCustomCommand(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && customCommand.trim()) {
                  handleExecute(customCommand);
                }
              }}
              style={{
                flex: 1,
                background: "rgba(0, 0, 0, 0.25)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 10,
                padding: "10px 14px",
                color: "var(--text-primary)",
                fontSize: 13,
                outline: "none",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--secondary)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--border-subtle)")}
            />
            <button
              onClick={() => handleExecute(customCommand)}
              disabled={!customCommand.trim() || isExecuting !== null}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: customCommand.trim() ? "var(--secondary)" : "rgba(255, 255, 255, 0.08)",
                color: customCommand.trim() ? "#ffffff" : "var(--text-muted)",
                border: "none",
                borderRadius: 10,
                padding: "0 18px",
                fontSize: 13,
                fontWeight: 500,
                cursor: customCommand.trim() ? "pointer" : "default",
                transition: "all 0.2s ease",
              }}
            >
              <ArrowUpIcon size={14} />
              <span>{isExecuting === customCommand ? "Bajarilmoqda..." : "Ishga tushirish"}</span>
            </button>
          </div>

          {/* Execution Result Banner */}
          {executionResult && (
            <div
              style={{
                marginTop: 6,
                padding: "12px 16px",
                borderRadius: 10,
                fontSize: 12,
                display: "flex",
                flexDirection: "column",
                gap: 6,
                background: executionResult.success
                  ? "rgba(16, 185, 129, 0.12)"
                  : "rgba(239, 68, 68, 0.12)",
                border: `1px solid ${
                  executionResult.success ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"
                }`,
                color: executionResult.success ? "#34d399" : "#f87171",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontWeight: 600 }}>{executionResult.command}</span>
                  <span style={{ fontSize: 10, opacity: 0.8 }}>({executionResult.timestamp})</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <button
                    onClick={handleCopyResult}
                    style={{
                      background: "rgba(255, 255, 255, 0.08)",
                      border: "none",
                      borderRadius: 4,
                      padding: "2px 8px",
                      color: "inherit",
                      fontSize: 11,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    {copiedResult ? <CheckIcon size={12} /> : <CopyIcon size={12} />}
                    <span>{copiedResult ? "Nusxalandi" : "Nusxalash"}</span>
                  </button>
                  <button
                    onClick={() => setExecutionResult(null)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "inherit",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      padding: 2,
                    }}
                  >
                    <CloseIcon size={14} color="currentColor" />
                  </button>
                </div>
              </div>
              <div
                style={{
                  background: "rgba(0, 0, 0, 0.2)",
                  padding: "8px 12px",
                  borderRadius: 6,
                  fontFamily: "monospace",
                  fontSize: 12,
                  lineHeight: 1.4,
                  wordBreak: "break-word",
                }}
              >
                {executionResult.message}
              </div>
            </div>
          )}
        </div>

        {/* Search, Filter & Sort Controls */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            {/* Search Box */}
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                background: "var(--surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 10,
                padding: "0 14px",
                gap: 10,
              }}
            >
              <SearchIcon size={16} color="var(--text-muted)" />
              <input
                type="text"
                placeholder="Buyruqlar, tool nomlari va tavsiflar orasidan qidirish..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  padding: "10px 0",
                  color: "var(--text-primary)",
                  fontSize: 13,
                  outline: "none",
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                  }}
                >
                  <CloseIcon size={14} />
                </button>
              )}
            </div>

            {/* Sort Selector */}
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Tartiblash:</span>
              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value as any)}
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                  borderRadius: 8,
                  padding: "8px 12px",
                  fontSize: 12,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                <option value="name_asc">Nomi (A-Z)</option>
                <option value="name_desc">Nomi (Z-A)</option>
                <option value="category">Kategoriya bo'yicha</option>
              </select>
            </div>
          </div>

          {/* Category Chips */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {categories.map((cat) => {
              const count = categoryCounts[cat] || 0;
              const isSelected = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => {
                    setSelectedCategory(cat);
                    setVisibleLimit(36);
                  }}
                  style={{
                    background: isSelected ? "var(--secondary)" : "rgba(255, 255, 255, 0.04)",
                    color: isSelected ? "#ffffff" : "var(--text-secondary)",
                    border: `1px solid ${isSelected ? "var(--secondary)" : "var(--border-subtle)"}`,
                    borderRadius: 20,
                    padding: "5px 12px",
                    fontSize: 12,
                    fontWeight: isSelected ? 500 : 400,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    transition: "all 0.15s ease",
                  }}
                >
                  <span>{cat}</span>
                  <span
                    style={{
                      fontSize: 10,
                      padding: "1px 6px",
                      borderRadius: 10,
                      background: isSelected ? "rgba(255, 255, 255, 0.25)" : "rgba(255, 255, 255, 0.08)",
                      color: isSelected ? "#ffffff" : "var(--text-muted)",
                    }}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Results Counter */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12, color: "var(--text-muted)" }}>
          <span>{filteredCommands.length} ta buyruq topildi</span>
          {visibleCommands.length < filteredCommands.length && (
            <span>Ko'rsatilmoqda: {visibleCommands.length} / {filteredCommands.length}</span>
          )}
        </div>

        {/* Cards Display (Grid / List) */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "48px 0", color: "var(--text-secondary)" }}>
            Buyruqlar va vositalar yuklanmoqda...
          </div>
        ) : loadError ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              padding: "48px 24px",
              gap: "14px",
              textAlign: "center",
            }}
            role="alert"
          >
            <div
              style={{
                width: 52, height: 52, borderRadius: "50%",
                background: "rgba(239, 68, 68, 0.1)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <span style={{ fontSize: "15px", fontWeight: 600, color: "#F1F5F9" }}>
              Buyruqlar yuklanmadi
            </span>
            <span style={{ fontSize: "13px", color: "#94A3B8", maxWidth: "380px", lineHeight: 1.5 }}>
              {loadError}. Backend server ishga tushganligini tekshiring.
            </span>
            <button
              onClick={() => fetchCommands()}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "9px 18px",
                borderRadius: "10px",
                border: "1px solid rgba(192, 76, 253, 0.45)",
                background: "linear-gradient(135deg, rgba(147, 3, 197, 0.4) 0%, rgba(192, 76, 253, 0.3) 100%)",
                color: "#FFFFFF",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: "0 2px 12px rgba(147, 3, 197, 0.3)",
                transition: "all 0.2s ease",
              }}
            >
              Qayta yuklash
            </button>
          </div>
        ) : filteredCommands.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "48px 0",
              color: "var(--text-muted)",
              background: "rgba(255, 255, 255, 0.02)",
              borderRadius: 12,
              border: "1px dashed var(--border-subtle)",
            }}
          >
            "{searchQuery}" bo'yicha hech qanday buyruq topilmadi
          </div>
        ) : viewMode === "grid" ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 14,
            }}
          >
            {visibleCommands.map((cmd) => (
              <CommandGridCard
                key={cmd.id}
                cmd={cmd}
                isExecuting={isExecuting === cmd.query}
                onExecute={handleExecute}
                onInspect={handleOpenInspector}
              />
            ))}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {visibleCommands.map((cmd) => (
              <CommandListRow
                key={cmd.id}
                cmd={cmd}
                isExecuting={isExecuting === cmd.query}
                onExecute={handleExecute}
                onInspect={handleOpenInspector}
              />
            ))}
          </div>
        )}

        {/* Pagination / Load More Button */}
        {visibleCommands.length < filteredCommands.length && (
          <div style={{ display: "flex", justifyContent: "center", paddingTop: 16 }}>
            <button
              onClick={() => setVisibleLimit((prev) => prev + 36)}
              style={{
                background: "rgba(255, 255, 255, 0.05)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                padding: "10px 24px",
                borderRadius: 10,
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(59, 130, 246, 0.15)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)")}
            >
              Ko'proq yuklash (+36)
            </button>
          </div>
        )}
      </div>

      {/* Tool Parameter Inspector Modal */}
      {activeInspectTool && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.7)",
            backdropFilter: "blur(8px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 20,
          }}
          onClick={() => setActiveInspectTool(null)}
        >
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border-strong)",
              borderRadius: 14,
              maxWidth: 540,
              width: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "24px 26px",
              display: "flex",
              flexDirection: "column",
              gap: 16,
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: 9,
                    background: "rgba(59, 130, 246, 0.15)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--secondary)",
                  }}
                >
                  {renderCommandIcon(activeInspectTool.icon, 18, "var(--secondary)")}
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
                    {activeInspectTool.name}
                  </h3>
                  <code style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {activeInspectTool.query}
                  </code>
                </div>
              </div>
              <button
                onClick={() => setActiveInspectTool(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                <CloseIcon size={16} />
              </button>
            </div>

            {/* Description */}
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>
              {activeInspectTool.desc}
            </p>

            {/* Parameters Form */}
            {activeInspectTool.parameters && Object.keys(activeInspectTool.parameters).length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                  Parametrlar:
                </span>
                {Object.entries(activeInspectTool.parameters).map(([paramKey, pMeta]: [string, any]) => (
                  <div
                    key={paramKey}
                    style={{
                      background: "rgba(0, 0, 0, 0.2)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 8,
                      padding: "10px 12px",
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <strong style={{ fontSize: 12, color: "var(--text-primary)" }}>{paramKey}</strong>
                        <span style={{ fontSize: 10, color: "var(--text-muted)" }}>({pMeta.type || "string"})</span>
                      </div>
                      {pMeta.required && (
                        <span
                          style={{
                            fontSize: 9,
                            padding: "1px 5px",
                            borderRadius: 4,
                            background: "rgba(239, 68, 68, 0.15)",
                            color: "#f87171",
                          }}
                        >
                          Majburiy
                        </span>
                      )}
                    </div>
                    {pMeta.description && (
                      <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                        {pMeta.description}
                      </span>
                    )}
                    <input
                      type="text"
                      placeholder={`Qiymat kiriting...`}
                      value={toolParamValues[paramKey] ?? ""}
                      onChange={(e) =>
                        setToolParamValues((prev) => ({ ...prev, [paramKey]: e.target.value }))
                      }
                      style={{
                        background: "rgba(255, 255, 255, 0.05)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 6,
                        padding: "6px 10px",
                        color: "var(--text-primary)",
                        fontSize: 12,
                        outline: "none",
                      }}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                Ushbu buyruq uchun qo'shimcha parametr talab qilinmaydi.
              </div>
            )}

            {/* Modal Actions */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
              <button
                onClick={() => setActiveInspectTool(null)}
                style={{
                  background: "transparent",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-secondary)",
                  borderRadius: 8,
                  padding: "8px 16px",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                onClick={() => handleExecute(activeInspectTool.query, toolParamValues)}
                disabled={isExecuting !== null}
                style={{
                  background: "var(--secondary)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 8,
                  padding: "8px 18px",
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: isExecuting !== null ? "default" : "pointer",
                }}
              >
                {isExecuting ? "Bajarilmoqda..." : "Ishga tushirish"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CommandsPage;
