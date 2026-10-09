// ========== PluginsPage.tsx ==========
// Misa AI v9.0.0 — Plaginlar va Agent Vositalari Katalogi
// 5 ta holat: installed, available, disabled, error, updates

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  PluginsIcon,
  HomeIcon,
  SparklesIcon,
  CloseIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  RefreshIcon,
  SearchIcon,
  CheckIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  GlobeIcon,
  CodeIcon,
  DatabaseIcon,
  TerminalIcon,
  CalculatorIcon,
  CpuIcon,
  SunIcon,
  VolumeIcon,
  CameraIcon,
  ClockIcon,
  FolderIcon,
} from "../components/icons/Icons";
import {
  backendService,
  PluginItem,
  PluginsResponse,
  PluginStatus,
} from "../services/backendService";

interface PluginsPageProps {
  onNavigateHome: () => void;
}

export const PluginsPage: React.FC<PluginsPageProps> = ({ onNavigateHome }) => {
  const [plugins, setPlugins] = useState<PluginItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("Barchasi");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Tool sinov modal holati
  const [selectedTool, setSelectedTool] = useState<PluginItem | null>(null);
  const [paramValues, setParamValues] = useState<Record<string, string>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);

  // Plagin o'rnatish modali
  const [isInstallModalOpen, setIsInstallModalOpen] = useState(false);
  const [customName, setCustomName] = useState("");
  const [customDesc, setCustomDesc] = useState("");
  const [customType, setCustomType] = useState<"url" | "command">("url");
  const [customTarget, setCustomTarget] = useState("");
  const [isSubmittingInstall, setIsSubmittingInstall] = useState(false);

  const mountedRef = React.useRef(true);

  const fetchPlugins = useCallback(async () => {
    if (!mountedRef.current) return;
    setLoading(true);
    setLoadError(null);
    try {
      const res: PluginsResponse = await backendService.getPlugins();
      if (mountedRef.current && res.ok) {
        const list = res.plugins || res.tools || [];
        setPlugins(list);
        setCategories(res.categories || ["Barchasi"]);
      }
    } catch (err: any) {
      if (mountedRef.current) {
        setLoadError(err.message || "Backend serveriga ulanib bo'lmadi");
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    fetchPlugins();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchPlugins]);

  const handleToggle = async (plugin: PluginItem) => {
    const newStatus = !plugin.enabled;
    const res = await backendService.togglePlugin(plugin.name, newStatus);
    if (res.ok) {
      await fetchPlugins();
    }
  };

  const handleInstallTemplate = async (templateName: string) => {
    const res = await backendService.installPlugin(templateName);
    if (res.ok) {
      await fetchPlugins();
      setIsInstallModalOpen(false);
    }
  };

  const handleCreateCustom = async () => {
    if (!customName.trim() || !customTarget.trim() || isSubmittingInstall) return;
    setIsSubmittingInstall(true);

    const data = {
      name: customName.trim(),
      description: customDesc.trim() || "Foydalanuvchi maxsus plagini",
      category: "Foydalanuvchi",
      type: customType,
      parameters: { query: { type: "string", description: "Parametr" } },
      version: "1.0.0",
      ...(customType === "url" ? { url: customTarget.trim() } : { command: customTarget.trim() }),
    };

    const res = await backendService.installPlugin(customName.trim(), data);
    if (res.ok) {
      setCustomName("");
      setCustomDesc("");
      setCustomTarget("");
      setIsInstallModalOpen(false);
      await fetchPlugins();
    }
    setIsSubmittingInstall(false);
  };

  const handleUninstall = async (name: string) => {
    const res = await backendService.uninstallPlugin(name);
    if (res.ok) {
      await fetchPlugins();
    }
  };

  const handleUpdate = async (name: string) => {
    const res = await backendService.updatePlugin(name);
    if (res.ok) {
      await fetchPlugins();
    }
  };

  const openToolModal = (tool: PluginItem) => {
    setSelectedTool(tool);
    setParamValues({});
    setExecutionResult(null);
  };

  const closeToolModal = () => {
    setSelectedTool(null);
    setExecutionResult(null);
  };

  const handleRunTool = async () => {
    if (!selectedTool || isExecuting) return;
    setIsExecuting(true);
    setExecutionResult(null);

    const res = await backendService.executePlugin(selectedTool.name, paramValues);
    setExecutionResult(res);
    setIsExecuting(false);
  };

  // Status statistikasi
  const stats = useMemo(() => {
    const total = plugins.length;
    let installed = 0;
    let available = 0;
    let disabled = 0;
    let error = 0;
    let updates = 0;

    plugins.forEach((p) => {
      const s = p.status || (p.enabled ? "installed" : "disabled");
      if (s === "installed") installed++;
      else if (s === "available") available++;
      else if (s === "disabled") disabled++;
      else if (s === "error") error++;
      else if (s === "updates") updates++;
    });

    return { total, installed, available, disabled, error, updates };
  }, [plugins]);

  // Filtrlash
  const filteredPlugins = useMemo(() => {
    return plugins.filter((p) => {
      const s = p.status || (p.enabled ? "installed" : "disabled");
      if (filterStatus !== "all" && s !== filterStatus) return false;
      if (selectedCategory !== "Barchasi" && p.category.toLowerCase() !== selectedCategory.toLowerCase()) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const nameMatch = p.name.toLowerCase().includes(q);
        const descMatch = (p.description || "").toLowerCase().includes(q);
        if (!nameMatch && !descMatch) return false;
      }
      return true;
    });
  }, [plugins, filterStatus, selectedCategory, searchQuery]);

  const getPluginIcon = (name: string, category: string) => {
    const n = name.toLowerCase();
    const c = category.toLowerCase();
    if (n.includes("calculator") || n.includes("currency")) return <CalculatorIcon size={18} color="#38bdf8" />;
    if (n.includes("weather") || n.includes("sun")) return <SunIcon size={18} color="#fbbf24" />;
    if (n.includes("search") || n.includes("wikipedia") || n.includes("web")) return <GlobeIcon size={18} color="#60a5fa" />;
    if (n.includes("code") || n.includes("github") || n.includes("script")) return <CodeIcon size={18} color="#34d399" />;
    if (n.includes("audio") || n.includes("music")) return <VolumeIcon size={18} color="#ec4899" />;
    if (n.includes("screenshot") || n.includes("camera")) return <CameraIcon size={18} color="#a855f7" />;
    if (n.includes("file")) return <FolderIcon size={18} color="#f59e0b" />;
    if (n.includes("system") || n.includes("cpu") || n.includes("process")) return <CpuIcon size={18} color="#38bdf8" />;
    if (n.includes("time") || n.includes("schedule") || n.includes("remind")) return <ClockIcon size={18} color="#f59e0b" />;
    if (c.includes("xotira") || c.includes("bilim") || c.includes("rag")) return <DatabaseIcon size={18} color="#818cf8" />;
    return <TerminalIcon size={18} color="#a855f7" />;
  };

  const renderStatusBadge = (status: PluginStatus | string) => {
    switch (status) {
      case "installed":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 6,
              background: "rgba(16, 185, 129, 0.15)",
              color: "#34d399",
              border: "1px solid rgba(16, 185, 129, 0.3)",
            }}
          >
            <CheckCircleIcon size={11} color="#34d399" />
            <span>O'rnatilgan</span>
          </span>
        );
      case "available":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 6,
              background: "rgba(59, 130, 246, 0.15)",
              color: "#60a5fa",
              border: "1px solid rgba(59, 130, 246, 0.3)",
            }}
          >
            <SparklesIcon size={11} color="#60a5fa" />
            <span>Mavjud</span>
          </span>
        );
      case "disabled":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 6,
              background: "rgba(100, 116, 139, 0.15)",
              color: "#94a3b8",
              border: "1px solid rgba(100, 116, 139, 0.3)",
            }}
          >
            <PauseIcon size={11} color="#94a3b8" />
            <span>Nofaol</span>
          </span>
        );
      case "updates":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 6,
              background: "rgba(245, 158, 11, 0.15)",
              color: "#fbbf24",
              border: "1px solid rgba(245, 158, 11, 0.3)",
            }}
          >
            <RefreshIcon size={11} color="#fbbf24" />
            <span>Yangilanish</span>
          </span>
        );
      case "error":
        return (
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              fontSize: 11,
              fontWeight: 600,
              padding: "2px 8px",
              borderRadius: 6,
              background: "rgba(239, 68, 68, 0.15)",
              color: "#f87171",
              border: "1px solid rgba(239, 68, 68, 0.3)",
            }}
          >
            <AlertCircleIcon size={11} color="#f87171" />
            <span>Xatolik</span>
          </span>
        );
      default:
        return null;
    }
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
          background: "rgba(10, 15, 29, 0.75)",
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
              background: "rgba(168, 85, 247, 0.15)",
              border: "1px solid rgba(168, 85, 247, 0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <PluginsIcon size={20} color="#a855f7" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <h1 style={{ margin: 0, fontSize: 18, fontWeight: 600, letterSpacing: "-0.01em" }}>
                Plaginlar Markazi
              </h1>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 12,
                  background: "rgba(168, 85, 247, 0.15)",
                  color: "#a855f7",
                  fontWeight: 500,
                  border: "1px solid rgba(168, 85, 247, 0.2)",
                }}
              >
                {stats.installed} ta faol plagin
              </span>
            </div>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--text-secondary)" }}>
              5 holatli modulli arxitektura: installed, available, disabled, error, updates
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            onClick={() => setIsInstallModalOpen(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(168, 85, 247, 0.15)",
              border: "1px solid rgba(168, 85, 247, 0.3)",
              color: "#c084fc",
              padding: "8px 14px",
              borderRadius: 8,
              fontSize: 12,
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <SparklesIcon size={14} color="#c084fc" />
            <span>Yangi plagin qo'shish</span>
          </button>

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
          >
            <HomeIcon size={14} />
            <span>Bosh sahifa</span>
          </button>
        </div>
      </div>

      {/* Main Container */}
      <div
        style={{
          maxWidth: 1100,
          width: "100%",
          margin: "0 auto",
          padding: "24px 28px 48px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        {/* Status Tabs Bar */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {[
            { id: "all", label: `Barchasi (${stats.total})` },
            { id: "installed", label: `O'rnatilgan (${stats.installed})` },
            { id: "available", label: `Mavjud (${stats.available})` },
            { id: "disabled", label: `Nofaol (${stats.disabled})` },
            { id: "updates", label: `Yangilanishlar (${stats.updates})` },
            { id: "error", label: `Xatoliklar (${stats.error})` },
          ].map((tab) => {
            const active = filterStatus === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setFilterStatus(tab.id)}
                style={{
                  background: active ? "rgba(168, 85, 247, 0.2)" : "rgba(255, 255, 255, 0.03)",
                  border: active ? "1px solid rgba(168, 85, 247, 0.4)" : "1px solid var(--border-subtle)",
                  color: active ? "#c084fc" : "var(--text-secondary)",
                  borderRadius: 8,
                  padding: "8px 14px",
                  fontSize: 12,
                  fontWeight: active ? 600 : 400,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Filter and Search Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          {/* Categories */}
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {categories.slice(0, 8).map((cat) => {
              const active = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  style={{
                    background: active ? "rgba(255, 255, 255, 0.1)" : "transparent",
                    border: active ? "1px solid var(--border-strong)" : "1px solid transparent",
                    color: active ? "var(--text-primary)" : "var(--text-muted)",
                    borderRadius: 6,
                    padding: "4px 10px",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  {cat}
                </button>
              );
            })}
          </div>

          {/* Search Box */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(0, 0, 0, 0.25)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 8,
              padding: "6px 12px",
              width: 260,
            }}
          >
            <SearchIcon size={14} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Plagin nomidan izlash..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                background: "transparent",
                border: "none",
                outline: "none",
                color: "var(--text-primary)",
                fontSize: 12,
                width: "100%",
              }}
            />
          </div>
        </div>

        {/* Plugins Grid */}
        {loading ? (
          <div style={{ textAlign: "center", padding: "60px", color: "var(--text-secondary)" }}>
            Plaginlar yuklanmoqda...
          </div>
        ) : loadError ? (
          <div
            style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", padding: "48px 24px", gap: "14px", textAlign: "center",
            }}
            role="alert"
          >
            <div style={{ width: 52, height: 52, borderRadius: "50%", background: "rgba(239, 68, 68, 0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#EF4444" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <span style={{ fontSize: "15px", fontWeight: 600, color: "#F1F5F9" }}>Plaginlar yuklanmadi</span>
            <button
              onClick={() => fetchPlugins()}
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
        ) : filteredPlugins.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "60px 20px",
              color: "var(--text-muted)",
              border: "1px dashed var(--border-subtle)",
              borderRadius: 12,
              fontSize: 13,
            }}
          >
            Ushbu filtr bo'yicha hech qanday plagin topilmadi.
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 14,
            }}
          >
            {filteredPlugins.map((p) => {
              const status = p.status || (p.enabled ? "installed" : "disabled");
              const isCustom = p.type === "json" || p.type === "python";

              return (
                <div
                  key={p.name}
                  style={{
                    background: "rgba(255, 255, 255, 0.025)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 12,
                    padding: "16px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    gap: 12,
                    position: "relative",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {/* Card Header */}
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div
                          style={{
                            width: 36,
                            height: 36,
                            borderRadius: 8,
                            background: "rgba(255, 255, 255, 0.04)",
                            border: "1px solid var(--border-subtle)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          {getPluginIcon(p.name, p.category)}
                        </div>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                              {p.name}
                            </span>
                            <span
                              style={{
                                fontSize: 10,
                                padding: "1px 5px",
                                borderRadius: 4,
                                background: "rgba(255, 255, 255, 0.06)",
                                color: "var(--text-muted)",
                                fontFamily: "monospace",
                              }}
                            >
                              v{p.version || "1.0.0"}
                            </span>
                          </div>
                          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                            {p.category} {p.type ? `• ${p.type}` : ""}
                          </div>
                        </div>
                      </div>

                      {renderStatusBadge(status)}
                    </div>

                    {/* Description */}
                    <p
                      style={{
                        margin: 0,
                        fontSize: 12,
                        color: "var(--text-secondary)",
                        lineHeight: 1.45,
                      }}
                    >
                      {p.description || "Tavsif mavjud emas"}
                    </p>

                    {/* Error info */}
                    {p.error && (
                      <div
                        style={{
                          fontSize: 11,
                          color: "#f87171",
                          background: "rgba(239, 68, 68, 0.1)",
                          padding: "6px 8px",
                          borderRadius: 6,
                        }}
                      >
                        Xatolik: {p.error}
                      </div>
                    )}
                  </div>

                  {/* Actions Footer */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      paddingTop: 10,
                      borderTop: "1px solid var(--border-subtle)",
                      marginTop: 4,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {/* Sinash / Run */}
                      {status !== "available" && status !== "error" && (
                        <button
                          onClick={() => openToolModal(p)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            background: "rgba(255, 255, 255, 0.05)",
                            border: "1px solid var(--border-subtle)",
                            color: "var(--text-primary)",
                            borderRadius: 6,
                            padding: "5px 8px",
                            fontSize: 11,
                            cursor: "pointer",
                          }}
                        >
                          <PlayIcon size={11} color="#34d399" />
                          <span>Sinash</span>
                        </button>
                      )}

                      {/* Updates button */}
                      {status === "updates" && (
                        <button
                          onClick={() => handleUpdate(p.name)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            background: "rgba(245, 158, 11, 0.15)",
                            border: "1px solid rgba(245, 158, 11, 0.3)",
                            color: "#fbbf24",
                            borderRadius: 6,
                            padding: "5px 8px",
                            fontSize: 11,
                            cursor: "pointer",
                          }}
                        >
                          <RefreshIcon size={11} color="#fbbf24" />
                          <span>Yangilash</span>
                        </button>
                      )}

                      {/* Install Available */}
                      {status === "available" && (
                        <button
                          onClick={() => handleInstallTemplate(p.name)}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            background: "rgba(59, 130, 246, 0.15)",
                            border: "1px solid rgba(59, 130, 246, 0.3)",
                            color: "#60a5fa",
                            borderRadius: 6,
                            padding: "5px 10px",
                            fontSize: 11,
                            fontWeight: 500,
                            cursor: "pointer",
                          }}
                        >
                          <SparklesIcon size={11} color="#60a5fa" />
                          <span>O'rnatish</span>
                        </button>
                      )}
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      {/* Enable / Disable toggle */}
                      {status !== "available" && status !== "error" && (
                        <button
                          onClick={() => handleToggle(p)}
                          title={p.enabled ? "To'xtatish" : "Yoqish"}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                            background: "transparent",
                            border: "1px solid var(--border-subtle)",
                            color: p.enabled ? "#fbbf24" : "#34d399",
                            borderRadius: 6,
                            padding: "5px 8px",
                            fontSize: 11,
                            cursor: "pointer",
                          }}
                        >
                          {p.enabled ? <PauseIcon size={12} /> : <CheckIcon size={12} />}
                          <span>{p.enabled ? "O'chirish" : "Yoqish"}</span>
                        </button>
                      )}

                      {/* Custom plugin uninstall */}
                      {isCustom && (
                        <button
                          onClick={() => handleUninstall(p.name)}
                          title="Butunlay o'chirish"
                          style={{
                            background: "rgba(239, 68, 68, 0.1)",
                            border: "1px solid rgba(239, 68, 68, 0.2)",
                            color: "#f87171",
                            borderRadius: 6,
                            padding: "5px 7px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <TrashIcon size={12} />
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

      {/* Tool Test Modal */}
      {selectedTool && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.7)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 20,
          }}
          onClick={closeToolModal}
        >
          <div
            style={{
              background: "#0e1422",
              border: "1px solid var(--border-subtle)",
              borderRadius: 14,
              padding: 24,
              width: "100%",
              maxWidth: 520,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              boxShadow: "0 10px 40px rgba(0, 0, 0, 0.5)",
              maxHeight: "85vh",
              overflowY: "auto",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <PlayIcon size={16} color="#34d399" />
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{selectedTool.name}</h3>
                <span
                  style={{
                    background: "rgba(59, 130, 246, 0.15)",
                    border: "1px solid rgba(59, 130, 246, 0.3)",
                    color: "#60a5fa",
                    fontSize: 10,
                    fontWeight: 600,
                    padding: "2px 6px",
                    borderRadius: 4,
                  }}
                >
                  v{selectedTool.version || "2.0.0"}
                </span>
              </div>
              <button
                onClick={closeToolModal}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                <CloseIcon size={14} />
              </button>
            </div>

            {/* Metadata Pills Row (Tool Contract 2.0) */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
              {/* Risk Level */}
              <span
                style={{
                  background:
                    selectedTool.risk_level === "high"
                      ? "rgba(239, 68, 68, 0.15)"
                      : selectedTool.risk_level === "medium"
                      ? "rgba(245, 158, 11, 0.15)"
                      : "rgba(16, 185, 129, 0.15)",
                  color:
                    selectedTool.risk_level === "high"
                      ? "#f87171"
                      : selectedTool.risk_level === "medium"
                      ? "#fbbf24"
                      : "#34d399",
                  border: "1px solid currentColor",
                  fontSize: 10,
                  fontWeight: 600,
                  padding: "2px 6px",
                  borderRadius: 4,
                  textTransform: "uppercase",
                }}
              >
                Risk: {selectedTool.risk_level || "low"}
              </span>

              {/* Health */}
              <span
                style={{
                  background:
                    selectedTool.health === "unavailable"
                      ? "rgba(239, 68, 68, 0.15)"
                      : selectedTool.health === "degraded"
                      ? "rgba(245, 158, 11, 0.15)"
                      : "rgba(16, 185, 129, 0.15)",
                  color:
                    selectedTool.health === "unavailable"
                      ? "#f87171"
                      : selectedTool.health === "degraded"
                      ? "#fbbf24"
                      : "#34d399",
                  border: "1px solid currentColor",
                  fontSize: 10,
                  fontWeight: 600,
                  padding: "2px 6px",
                  borderRadius: 4,
                  textTransform: "uppercase",
                }}
              >
                Salomatlik: {selectedTool.health || "available"}
              </span>

              {/* Idempotency */}
              <span
                style={{
                  background: "rgba(99, 102, 241, 0.12)",
                  color: "#a5b4fc",
                  border: "1px solid rgba(99, 102, 241, 0.3)",
                  fontSize: 10,
                  fontWeight: 500,
                  padding: "2px 6px",
                  borderRadius: 4,
                }}
              >
                {selectedTool.idempotent !== false ? "Idempotent" : "No-idempotent"}
              </span>

              {/* Destructive */}
              {selectedTool.destructive && (
                <span
                  style={{
                    background: "rgba(239, 68, 68, 0.2)",
                    color: "#f87171",
                    border: "1px solid #ef4444",
                    fontSize: 10,
                    fontWeight: 600,
                    padding: "2px 6px",
                    borderRadius: 4,
                  }}
                >
                  Destruktiv
                </span>
              )}

              {/* Timeout */}
              <span
                style={{
                  background: "rgba(255, 255, 255, 0.05)",
                  color: "var(--text-muted)",
                  border: "1px solid var(--border-subtle)",
                  fontSize: 10,
                  padding: "2px 6px",
                  borderRadius: 4,
                }}
              >
                Timeout: {selectedTool.timeout || 10}s
              </span>
            </div>

            <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
              {selectedTool.description}
            </p>

            {/* Capabilities */}
            {selectedTool.capabilities && selectedTool.capabilities.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)" }}>
                  Qobiliyatlar (Capabilities):
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {selectedTool.capabilities.map((cap) => (
                    <span
                      key={cap}
                      style={{
                        background: "rgba(14, 165, 233, 0.12)",
                        border: "1px solid rgba(14, 165, 233, 0.3)",
                        color: "#38bdf8",
                        fontSize: 10,
                        padding: "2px 6px",
                        borderRadius: 4,
                      }}
                    >
                      ⚡ {cap}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Parameters */}
            {selectedTool.parameters && Object.keys(selectedTool.parameters).length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>
                  Parametrlar:
                </span>
                {Object.entries(selectedTool.parameters).map(([key, val]: [string, any]) => {
                  const isRequired =
                    val.required === true ||
                    (selectedTool.required_parameters &&
                      selectedTool.required_parameters.includes(key));
                  return (
                    <div key={key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <label style={{ fontSize: 12, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 6 }}>
                        <span>{key}</span>
                        <span style={{ color: "var(--text-muted)", fontSize: 10 }}>
                          ({val.type || "string"})
                        </span>
                        {isRequired ? (
                          <span style={{ color: "#f87171", fontSize: 10, fontWeight: 600 }}>* Majburiy</span>
                        ) : (
                          <span style={{ color: "var(--text-muted)", fontSize: 10 }}>Ixtiyoriy</span>
                        )}
                      </label>
                      <input
                        type="text"
                        placeholder={val.description || key}
                        value={paramValues[key] || ""}
                        onChange={(e) =>
                          setParamValues((prev) => ({ ...prev, [key]: e.target.value }))
                        }
                        style={{
                          background: "rgba(0, 0, 0, 0.3)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: 8,
                          padding: "8px 12px",
                          color: "var(--text-primary)",
                          fontSize: 12,
                          outline: "none",
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                Ushbu vosita qo'shimcha parametrlar talab qilmaydi.
              </div>
            )}

            {/* Result Box */}
            {executionResult && (
              <div
                style={{
                  background: "rgba(0, 0, 0, 0.4)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 8,
                  padding: "12px",
                  fontSize: 12,
                  fontFamily: "monospace",
                  maxHeight: 180,
                  overflowY: "auto",
                  color: executionResult.ok ? "#34d399" : "#f87171",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 11, color: "var(--text-muted)" }}>
                  <span>Natija (ToolResult)</span>
                  {executionResult.result?.duration_ms !== undefined && (
                    <span>Davomiyligi: {executionResult.result.duration_ms} ms</span>
                  )}
                </div>
                <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(executionResult, null, 2)}
                </pre>
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 6 }}>
              <button
                onClick={closeToolModal}
                style={{
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-secondary)",
                  padding: "8px 16px",
                  borderRadius: 8,
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Yopish
              </button>
              <button
                onClick={handleRunTool}
                disabled={isExecuting}
                style={{
                  background: "#34d399",
                  color: "#022c22",
                  border: "none",
                  padding: "8px 18px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: isExecuting ? "not-allowed" : "pointer",
                }}
              >
                {isExecuting ? "Bajarilmoqda..." : "Ishga tushirish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Install Modal */}
      {isInstallModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.7)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
            padding: 20,
          }}
          onClick={() => setIsInstallModalOpen(false)}
        >
          <div
            style={{
              background: "#0e1422",
              border: "1px solid var(--border-subtle)",
              borderRadius: 14,
              padding: 24,
              width: "100%",
              maxWidth: 480,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              boxShadow: "0 10px 40px rgba(0, 0, 0, 0.5)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <SparklesIcon size={16} color="#c084fc" />
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Maxsus Plagin Yaratish</h3>
              </div>
              <button
                onClick={() => setIsInstallModalOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                }}
              >
                <CloseIcon size={14} />
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ fontSize: 12, color: "var(--text-secondary)" }}>Plagin nomi (lotincha):</label>
              <input
                type="text"
                placeholder="my_custom_tool"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                style={{
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 8,
                  padding: "8px 12px",
                  color: "var(--text-primary)",
                  fontSize: 13,
                  outline: "none",
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ fontSize: 12, color: "var(--text-secondary)" }}>Tavsifi:</label>
              <input
                type="text"
                placeholder="Veb-saytni ochish yoki skript chaqirish..."
                value={customDesc}
                onChange={(e) => setCustomDesc(e.target.value)}
                style={{
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 8,
                  padding: "8px 12px",
                  color: "var(--text-primary)",
                  fontSize: 13,
                  outline: "none",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, color: "var(--text-secondary)" }}>Turi:</label>
                <select
                  value={customType}
                  onChange={(e) => setCustomType(e.target.value as any)}
                  style={{
                    background: "rgba(0, 0, 0, 0.3)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 8,
                    padding: "8px 12px",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    outline: "none",
                  }}
                >
                  <option value="url">URL (Brauzerda ochish)</option>
                  <option value="command">CLI Buyruq (Terminal)</option>
                </select>
              </div>

              <div style={{ flex: 2, display: "flex", flexDirection: "column", gap: 6 }}>
                <label style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  {customType === "url" ? "URL shablon:" : "CLI Buyruq shabloni:"}
                </label>
                <input
                  type="text"
                  placeholder={
                    customType === "url"
                      ? "https://example.com/search?q={query}"
                      : "python script.py {query}"
                  }
                  value={customTarget}
                  onChange={(e) => setCustomTarget(e.target.value)}
                  style={{
                    background: "rgba(0, 0, 0, 0.3)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 8,
                    padding: "8px 12px",
                    color: "var(--text-primary)",
                    fontSize: 13,
                    outline: "none",
                  }}
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
              <button
                onClick={() => setIsInstallModalOpen(false)}
                style={{
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-secondary)",
                  padding: "8px 16px",
                  borderRadius: 8,
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                onClick={handleCreateCustom}
                disabled={!customName.trim() || !customTarget.trim() || isSubmittingInstall}
                style={{
                  background: "#c084fc",
                  color: "#18181b",
                  border: "none",
                  padding: "8px 18px",
                  borderRadius: 8,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: !customName.trim() || !customTarget.trim() || isSubmittingInstall ? "not-allowed" : "pointer",
                }}
              >
                {isSubmittingInstall ? "Yaratilmoqda..." : "Yaratish va O'rnatish"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default PluginsPage;
