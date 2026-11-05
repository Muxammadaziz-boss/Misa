// ========== WorkspacePage.tsx ==========
// Misa AI v9.0.0 — Native Workspace & Autonomy Execution Environment
// Ultra Glass UI for Project Connection, File Explorer, Terminal, Git, and 9-Step Autonomous Workflow

import React, { useState, useEffect, useCallback } from "react";
import {
  TerminalIcon,
  HomeIcon,
  FolderIcon,
  RefreshIcon,
  PlayIcon,
  CodeIcon,
  CheckCircleIcon,
  ShieldIcon,
  SparklesIcon,
  FileTextIcon,
  CloseIcon,
} from "../components/icons/Icons";
import {
  workspaceService,
  WorkspaceConfig,
  WorkspaceMode,
  FileItem,
  ProjectMap,
  ActivityEvent,
  CommandExecution,
} from "../services/workspaceService";

interface WorkspacePageProps {
  onNavigateHome: () => void;
}

export const WorkspacePage: React.FC<WorkspacePageProps> = ({ onNavigateHome }) => {
  const [activeTab, setActiveTab] = useState<"workflow" | "files" | "terminal" | "git" | "project" | "activity">("workflow");
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceConfig | null>(null);
  const [workspacesList, setWorkspacesList] = useState<WorkspaceConfig[]>([]);
  const [projectMap, setProjectMap] = useState<ProjectMap | null>(null);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [currentDir, setCurrentDir] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>("");
  const [gitStatus, setGitStatus] = useState<any>(null);
  const [gitDiff, setGitDiff] = useState<string>("");
  const [activities, setActivities] = useState<ActivityEvent[]>([]);

  // Terminal
  const [terminalInput, setTerminalInput] = useState<string>("");
  const [isRunningCommand, setIsRunningCommand] = useState<boolean>(false);
  const [commandHistory, setCommandHistory] = useState<CommandExecution[]>([]);

  // Workflow Runner (9-Step Autonomous Pipeline)
  const [workflowGoal, setWorkflowGoal] = useState<string>("Inspect authentication architecture and run security tests");
  const [isRunningWorkflow, setIsRunningWorkflow] = useState<boolean>(false);
  const [workflowResult, setWorkflowResult] = useState<any>(null);
  const [workflowSteps, setWorkflowSteps] = useState<any[]>([]);

  // Connect modal
  const [isConnectModalOpen, setIsConnectModalOpen] = useState<boolean>(false);
  const [newWsPath, setNewWsPath] = useState<string>("");
  const [newWsName, setNewWsName] = useState<string>("");
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const mountedRef = React.useRef(true);

  const loadData = useCallback(async () => {
    if (!mountedRef.current) return;
    try {
      const [wsData, pmap, gstat, gdiff, acts] = await Promise.all([
        workspaceService.getWorkspace(),
        workspaceService.getProjectAnalysis(),
        workspaceService.getGitStatus(),
        workspaceService.getGitDiff(),
        workspaceService.getRecentActivity(),
      ]);

      if (mountedRef.current) {
        setActiveWorkspace(wsData.active);
        setWorkspacesList(wsData.list);
        setProjectMap(pmap);
        setGitStatus(gstat);
        setGitDiff(gdiff);
        setActivities(acts);
      }
    } catch (e) {
      console.error("Failed to load workspace data:", e);
    }
  }, []);

  const loadFiles = useCallback(async (dir: string = "") => {
    try {
      const items = await workspaceService.getFiles(dir);
      if (mountedRef.current) {
        setFiles(items);
        setCurrentDir(dir);
      }
    } catch (e) {
      console.error("Failed to list files:", e);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    loadData();
    loadFiles("");

    const unsub = workspaceService.onActivity((act: ActivityEvent) => {
      if (mountedRef.current) {
        setActivities((prev) => [act, ...prev.slice(0, 49)]);
      }
    });

    return () => {
      mountedRef.current = false;
      unsub();
    };
  }, [loadData, loadFiles]);

  const handleSelectFile = async (filePath: string) => {
    setSelectedFile(filePath);
    try {
      const res = await workspaceService.readFile(filePath);
      setFileContent(res?.content || "");
    } catch (err: any) {
      setFileContent(`Xatolik: ${err.message}`);
    }
  };

  const handleModeChange = async (mode: WorkspaceMode) => {
    if (!activeWorkspace) return;
    const updated = await workspaceService.updateMode(activeWorkspace.workspace_id, mode);
    if (updated) {
      setActiveWorkspace(updated);
      setActionNotice(`Ishchi muhit rejimi o'zgartirildi: ${mode.toUpperCase()}`);
    }
  };

  const handleConnectNew = async () => {
    if (!newWsPath.trim()) return;
    const ws = await workspaceService.connectWorkspace(newWsPath.trim(), newWsName.trim() || undefined);
    if (ws) {
      setIsConnectModalOpen(false);
      setNewWsPath("");
      setNewWsName("");
      loadData();
      loadFiles("");
      setActionNotice(`Yangi loyiha muvaffaqiyatli ulandi: ${ws.name}`);
    } else {
      setActionNotice("Katalog topilmadi yoki ulanishda xatolik yuz berdi.");
    }
  };

  const handleRunCommand = async () => {
    if (!terminalInput.trim() || isRunningCommand) return;
    const cmd = terminalInput.trim();
    setIsRunningCommand(true);
    setTerminalInput("");

    try {
      const res = await workspaceService.runCommand(cmd);
      if (res) {
        setCommandHistory((prev) => [res, ...prev.slice(0, 19)]);
      }
    } finally {
      setIsRunningCommand(false);
      loadData();
    }
  };

  const handleRunWorkflow = async () => {
    if (!workflowGoal.trim() || isRunningWorkflow) return;
    setIsRunningWorkflow(true);
    setWorkflowResult(null);
    setWorkflowSteps([]);

    try {
      const res = await workspaceService.executeAutonomousWorkflow(workflowGoal.trim());
      if (res && res.ok && res.data) {
        setWorkflowResult(res.data);
        if (res.data.workflow_steps) {
          setWorkflowSteps(res.data.workflow_steps);
        }
      } else {
        setActionNotice(res?.error || "Avtonom workflow xatolik bilan yakunlandi.");
      }
    } catch (err: any) {
      setActionNotice(err.message);
    } finally {
      setIsRunningWorkflow(false);
      loadData();
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        padding: "24px 32px",
        overflowY: "auto",
        backgroundColor: "var(--background)",
        color: "var(--text-primary)",
      }}
    >
      {/* Top Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, var(--misa-accent), var(--misa-accent-glow))",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 16px var(--misa-accent-glow)",
              }}
            >
              <TerminalIcon size={20} color="#fff" />
            </div>
            <h1 style={{ fontSize: "24px", fontWeight: 700, margin: 0, letterSpacing: "-0.5px" }}>
              Loyiha Ishchi Muhiti (Workspace Autonomy)
            </h1>
          </div>
          <p style={{ margin: "4px 0 0 0", color: "var(--text-secondary)", fontSize: "14px" }}>
            Lokal loyiha tahlili, kodni o'zgartirish, testlarni yurgizish va 9-bosqichli avtonom dasturlash tizimi.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={() => setIsConnectModalOpen(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, var(--misa-accent), var(--misa-accent-glow))",
              border: "none",
              color: "#fff",
              fontWeight: 600,
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            <FolderIcon size={14} /> Loyiha Qo'shish
          </button>
          <button
            onClick={loadData}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "8px",
              background: "var(--surface)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
              cursor: "pointer",
            }}
          >
            <RefreshIcon size={14} /> Yangilash
          </button>
          <button
            onClick={onNavigateHome}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "8px",
              background: "var(--surface)",
              border: "1px solid var(--border-subtle)",
              color: "var(--text-primary)",
              cursor: "pointer",
            }}
          >
            <HomeIcon size={14} /> Asosiy
          </button>
        </div>
      </div>

      {/* Active Workspace Status & Mode Banner */}
      <div
        style={{
          padding: "16px 20px",
          borderRadius: "12px",
          background: "var(--surface)",
          backdropFilter: "blur(24px)",
          border: "1px solid var(--border-subtle)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Faol Loyiha:</span>
            <span style={{ fontSize: "16px", fontWeight: 700, color: "var(--primary-glow)" }}>
              {activeWorkspace?.name || "Loyiha tanlanmagan"}
            </span>
            <span
              style={{
                fontSize: "11px",
                padding: "2px 8px",
                borderRadius: "12px",
                background: "rgba(16, 185, 129, 0.15)",
                color: "var(--success-glow)",
                fontWeight: 600,
              }}
            >
              Ulandirildi
            </span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", fontFamily: "monospace", marginTop: "2px" }}>
            {activeWorkspace?.root_path}
          </div>
        </div>

        {/* Operation Mode Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Rejim:</span>
          {(["observe", "supervised", "controlled_autonomy"] as WorkspaceMode[]).map((m) => (
            <button
              key={m}
              onClick={() => handleModeChange(m)}
              style={{
                padding: "6px 12px",
                borderRadius: "6px",
                background: activeWorkspace?.mode === m ? "var(--primary)" : "var(--surface-elevated)",
                border: activeWorkspace?.mode === m ? "1px solid var(--primary-glow)" : "1px solid var(--border-subtle)",
                color: activeWorkspace?.mode === m ? "#fff" : "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: activeWorkspace?.mode === m ? 600 : 400,
                cursor: "pointer",
                textTransform: "capitalize",
              }}
            >
              {m === "controlled_autonomy" ? "Avtonom" : m === "supervised" ? "Nazorat" : "Ko'rish"}
            </button>
          ))}
        </div>
      </div>

      {/* Global Notice */}
      {actionNotice && (
        <div
          style={{
            padding: "10px 16px",
            marginBottom: "16px",
            borderRadius: "8px",
            background: "rgba(16, 185, 129, 0.15)",
            border: "1px solid var(--success)",
            color: "var(--success-glow)",
            fontSize: "13px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer" }}>
            <CloseIcon size={14} />
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          borderBottom: "1px solid var(--border-subtle)",
          paddingBottom: "12px",
          marginBottom: "20px",
          overflowX: "auto",
        }}
      >
        {[
          { id: "workflow", label: "9-Bosqichli Avtonom Dasturlash", icon: SparklesIcon },
          { id: "files", label: "Fayl Boshqaruvi & Kod", icon: FolderIcon },
          { id: "terminal", label: "Terminal & Buyruqlar", icon: TerminalIcon },
          { id: "git", label: "Git Nazorati & Diff", icon: CodeIcon },
          { id: "project", label: "Loyiha Arxitekturasi", icon: FileTextIcon },
          { id: "activity", label: `Jonli Faoliyat (${activities.length})`, icon: ShieldIcon },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 16px",
              borderRadius: "8px",
              background: activeTab === tab.id ? "rgba(147, 3, 197, 0.22)" : "transparent",
              border: activeTab === tab.id ? "1px solid var(--primary-glow)" : "1px solid transparent",
              color: activeTab === tab.id ? "var(--primary-glow)" : "var(--text-secondary)",
              fontWeight: activeTab === tab.id ? 600 : 400,
              fontSize: "13px",
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            <tab.icon size={15} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: 9-STEP AUTONOMOUS WORKFLOW */}
      {activeTab === "workflow" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={sectionBoxStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
              <SparklesIcon size={18} color="var(--primary-glow)" />
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>
                Avtonom Dasturlash Konveyeri (9-Step Pipeline)
              </h3>
            </div>
            <p style={{ margin: "0 0 16px 0", fontSize: "13px", color: "var(--text-secondary)" }}>
              UNDERSTAND &rarr; ANALYZE &rarr; PLAN &rarr; DELEGATE &rarr; IMPLEMENT &rarr; EXECUTE &rarr; REVIEW &rarr; VERIFY &rarr; REPORT
            </p>

            <div style={{ display: "flex", gap: "10px" }}>
              <input
                type="text"
                value={workflowGoal}
                onChange={(e) => setWorkflowGoal(e.target.value)}
                placeholder="Dasturlash vazifasini kiriting..."
                onKeyDown={(e) => e.key === "Enter" && handleRunWorkflow()}
                disabled={isRunningWorkflow}
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  borderRadius: "10px",
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  color: "#fff",
                  fontSize: "14px",
                  outline: "none",
                }}
              />
              <button
                onClick={handleRunWorkflow}
                disabled={isRunningWorkflow || !workflowGoal.trim()}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "12px 24px",
                  borderRadius: "10px",
                  background: isRunningWorkflow
                    ? "var(--surface)"
                    : "linear-gradient(135deg, var(--misa-accent), var(--misa-accent-glow))",
                  border: "none",
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "14px",
                  cursor: isRunningWorkflow ? "not-allowed" : "pointer",
                  boxShadow: isRunningWorkflow ? "none" : "0 0 16px var(--misa-accent-glow)",
                }}
              >
                {isRunningWorkflow ? (
                  <>
                    <RefreshIcon size={16} /> Bajarilmoqda...
                  </>
                ) : (
                  <>
                    <PlayIcon size={16} /> Avtonom Dasturlash
                  </>
                )}
              </button>
            </div>

            {/* Workflow Step Progress Cards */}
            {workflowSteps.length > 0 && (
              <div style={{ marginTop: "24px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px", color: "var(--text-secondary)" }}>
                  Konveyer Bosqichlari ({workflowSteps.length} / 9):
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "10px" }}>
                  {workflowSteps.map((step) => (
                    <div
                      key={step.step}
                      style={{
                        padding: "12px",
                        borderRadius: "8px",
                        background: "rgba(24, 13, 36, 0.45)",
                        border: "1px solid var(--border-subtle)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--primary-glow)" }}>
                          BOSQICH {step.step}
                        </span>
                        <CheckCircleIcon size={14} color="var(--success)" />
                      </div>
                      <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "4px" }}>{step.name}</div>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {JSON.stringify(step.details)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Final Report Card */}
            {workflowResult && (
              <div
                style={{
                  marginTop: "20px",
                  padding: "18px",
                  borderRadius: "10px",
                  background: "rgba(10, 6, 18, 0.75)",
                  border: "1px solid var(--primary)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <h4 style={{ margin: 0, fontSize: "15px", color: "var(--primary-glow)" }}>
                    Misa Main — Yakuniy Dasturlash Hisoboti
                  </h4>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    Vaqt: {workflowResult.duration_seconds}s | Holat: {workflowResult.ok ? "MUVAFFAQIYATLI" : "TEKSHIRISH TALAB"}
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "13px", marginBottom: "14px" }}>
                  <div style={innerBoxStyle}>
                    <span style={{ color: "var(--text-muted)" }}>O'zgartirilgan fayllar:</span>
                    <span style={{ fontWeight: 600 }}>{workflowResult.summary?.files_changed?.length || 0} ta</span>
                  </div>
                  <div style={innerBoxStyle}>
                    <span style={{ color: "var(--text-muted)" }}>Bajarilgan buyruqlar:</span>
                    <span style={{ fontWeight: 600 }}>{workflowResult.summary?.commands_executed?.length || 0} ta</span>
                  </div>
                  <div style={innerBoxStyle}>
                    <span style={{ color: "var(--text-muted)" }}>Testlar natijasi:</span>
                    <span style={{ fontWeight: 600, color: workflowResult.summary?.tests_passed ? "var(--success)" : "var(--danger)" }}>
                      {workflowResult.summary?.tests_passed ? "BARCHASI O'TDI" : "XATOLIK ANIQLANDI"}
                    </span>
                  </div>
                  <div style={innerBoxStyle}>
                    <span style={{ color: "var(--text-muted)" }}>Qolgan muammolar:</span>
                    <span style={{ fontWeight: 600 }}>{workflowResult.summary?.remaining_issues?.length || 0} ta</span>
                  </div>
                </div>

                {workflowResult.git_diff_preview && (
                  <div>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)", fontWeight: 600 }}>Git Diff Ko'rinishi:</span>
                    <pre
                      style={{
                        margin: "6px 0 0 0",
                        padding: "10px",
                        borderRadius: "6px",
                        background: "#000",
                        color: "#a7f3d0",
                        fontSize: "11px",
                        fontFamily: "monospace",
                        maxHeight: "160px",
                        overflowY: "auto",
                      }}
                    >
                      {workflowResult.git_diff_preview}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: FILE EXPLORER & CODE VIEWER */}
      {activeTab === "files" && (
        <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "16px", minHeight: "450px" }}>
          {/* File Tree Explorer */}
          <div style={{ ...sectionBoxStyle, padding: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <span style={{ fontSize: "13px", fontWeight: 600 }}>Fayllar ({files.length})</span>
              {currentDir && (
                <button
                  onClick={() => loadFiles("")}
                  style={{ background: "none", border: "none", color: "var(--primary-glow)", fontSize: "11px", cursor: "pointer" }}
                >
                  Ildizga qaytish
                </button>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "400px", overflowY: "auto" }}>
              {files.map((f) => (
                <div
                  key={f.path}
                  onClick={() => (f.is_dir ? loadFiles(f.path) : handleSelectFile(f.path))}
                  style={{
                    padding: "6px 10px",
                    borderRadius: "6px",
                    background: selectedFile === f.path ? "rgba(147, 3, 197, 0.25)" : "transparent",
                    color: f.is_dir ? "var(--primary-glow)" : "var(--text-primary)",
                    fontSize: "12px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  {f.is_dir ? <FolderIcon size={14} /> : <FileTextIcon size={14} />}
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{f.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* File Previewer */}
          <div style={{ ...sectionBoxStyle, padding: "16px", display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--primary-glow)" }}>
                {selectedFile || "Fayl tanlanmagan"}
              </span>
            </div>
            <pre
              style={{
                flex: 1,
                margin: 0,
                padding: "14px",
                borderRadius: "8px",
                background: "rgba(0, 0, 0, 0.6)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontFamily: "var(--font-mono, monospace)",
                fontSize: "12px",
                lineHeight: "1.5",
                overflow: "auto",
                maxHeight: "440px",
              }}
            >
              {fileContent || "// Chap tomondan faylni tanlang."}
            </pre>
          </div>
        </div>
      )}

      {/* TAB 3: TERMINAL */}
      {activeTab === "terminal" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={sectionBoxStyle}>
            <div style={{ display: "flex", gap: "10px", marginBottom: "14px" }}>
              <input
                type="text"
                value={terminalInput}
                onChange={(e) => setTerminalInput(e.target.value)}
                placeholder="Terminal buyrug'ini kiriting (masalan: pytest tests/test_multi_agent_ecosystem.py)..."
                onKeyDown={(e) => e.key === "Enter" && handleRunCommand()}
                disabled={isRunningCommand}
                style={{
                  flex: 1,
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--border-subtle)",
                  color: "#fff",
                  fontFamily: "monospace",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
              <button
                onClick={handleRunCommand}
                disabled={isRunningCommand || !terminalInput.trim()}
                style={{
                  padding: "10px 20px",
                  borderRadius: "8px",
                  background: "var(--primary)",
                  border: "none",
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                {isRunningCommand ? "Bajarilmoqda..." : "Ishga Tushirish"}
              </button>
            </div>

            {/* Command History / Console Output */}
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {commandHistory.map((cmd) => (
                <div
                  key={cmd.command_id}
                  style={{
                    padding: "12px",
                    borderRadius: "8px",
                    background: "rgba(0,0,0,0.5)",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px", fontSize: "12px" }}>
                    <span style={{ color: "var(--primary-glow)", fontFamily: "monospace" }}>$ {cmd.command}</span>
                    <span style={{ color: cmd.status === "completed" ? "var(--success)" : "var(--danger)" }}>
                      {cmd.status.toUpperCase()} ({cmd.duration_seconds}s)
                    </span>
                  </div>
                  {cmd.stdout && (
                    <pre
                      style={{
                        margin: 0,
                        fontSize: "11px",
                        fontFamily: "monospace",
                        color: "#a7f3d0",
                        whiteSpace: "pre-wrap",
                        maxHeight: "150px",
                        overflowY: "auto",
                      }}
                    >
                      {cmd.stdout}
                    </pre>
                  )}
                  {cmd.stderr && (
                    <pre style={{ margin: "4px 0 0 0", fontSize: "11px", fontFamily: "monospace", color: "var(--danger-soft)" }}>
                      {cmd.stderr}
                    </pre>
                  )}
                </div>
              ))}
              {commandHistory.length === 0 && (
                <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                  Hozircha buyruq bajarilmagan. Yuqoridagi satr orqali buyruq bering.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: GIT */}
      {activeTab === "git" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={sectionBoxStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
              <span style={{ fontSize: "15px", fontWeight: 600 }}>
                Git Holati ({gitStatus?.branch || "main"})
              </span>
              <span style={{ fontSize: "12px", color: gitStatus?.clean ? "var(--success)" : "var(--warning)" }}>
                {gitStatus?.clean ? "Ishchi daraxt toza (Clean)" : "O'zgarishlar mavjud (Dirty)"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>O'zgartirilgan:</span>
                <span style={{ fontWeight: 600 }}>{gitStatus?.modified?.length || 0} ta fayl</span>
              </div>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Kuzatilmayotgan (Untracked):</span>
                <span style={{ fontWeight: 600 }}>{gitStatus?.untracked?.length || 0} ta fayl</span>
              </div>
            </div>

            <div>
              <span style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)" }}>Hozirgi Git Diff:</span>
              <pre
                style={{
                  margin: "8px 0 0 0",
                  padding: "12px",
                  borderRadius: "8px",
                  background: "#000",
                  color: "#e2e8f0",
                  fontFamily: "monospace",
                  fontSize: "12px",
                  lineHeight: "1.4",
                  maxHeight: "300px",
                  overflowY: "auto",
                }}
              >
                {gitDiff || "// O'zgarishlar mavjud emas."}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: PROJECT MAP */}
      {activeTab === "project" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={sectionBoxStyle}>
            <h3 style={{ margin: "0 0 14px 0", fontSize: "16px" }}>Loyiha Arxitekturasi va Bog'liqliklar</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginBottom: "16px" }}>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Asosiy Til:</span>
                <span style={{ fontWeight: 600, color: "var(--primary-glow)" }}>{projectMap?.primary_language}</span>
              </div>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Frameworklar:</span>
                <span style={{ fontWeight: 600 }}>{projectMap?.frameworks?.join(", ") || "None"}</span>
              </div>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Bog'liqliklar Soni:</span>
                <span style={{ fontWeight: 600 }}>{Object.keys(projectMap?.dependencies || {}).length} ta</span>
              </div>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>API Endpointlar:</span>
                <span style={{ fontWeight: 600 }}>{projectMap?.api_endpoints?.length || 0} ta</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 6: LIVE ACTIVITY */}
      {activeTab === "activity" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div style={sectionBoxStyle}>
            <h3 style={{ margin: "0 0 14px 0", fontSize: "16px" }}>Jonli Ijro Faoliyati (Activity Stream)</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {activities.map((act) => (
                <div
                  key={act.event_id}
                  style={{
                    padding: "10px 14px",
                    borderRadius: "8px",
                    background: "rgba(24, 13, 36, 0.45)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600 }}>
                      <span style={{ color: "var(--primary-glow)" }}>[{act.tool_name}]</span> {act.operation}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)", fontFamily: "monospace" }}>
                      Agent: {act.agent_id} | Natija: {act.output_preview}
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: "11px",
                      padding: "2px 8px",
                      borderRadius: "10px",
                      background: act.status === "completed" ? "rgba(16, 185, 129, 0.15)" : "rgba(147, 3, 197, 0.2)",
                      color: act.status === "completed" ? "var(--success-glow)" : "var(--primary-glow)",
                      fontWeight: 600,
                    }}
                  >
                    {act.status.toUpperCase()} ({act.duration_seconds}s)
                  </span>
                </div>
              ))}
              {activities.length === 0 && (
                <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                  Hozircha jonli faoliyat qayd etilmagan.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* CONNECT WORKSPACE MODAL */}
      {isConnectModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(10px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
          onClick={() => setIsConnectModalOpen(false)}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "500px",
              backgroundColor: "var(--surface-lowest)",
              borderRadius: "14px",
              border: "1px solid var(--border-strong)",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: "18px" }}>Yangi Loyiha Katalogini Ulash</h3>
              <button onClick={() => setIsConnectModalOpen(false)} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}>
                <CloseIcon size={18} />
              </button>
            </div>

            {workspacesList.length > 0 && (
              <div>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "6px" }}>
                  Mavjud Loyihalarga O'tish:
                </label>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "120px", overflowY: "auto", marginBottom: "12px" }}>
                  {workspacesList.map((w) => (
                    <div
                      key={w.workspace_id}
                      onClick={async () => {
                        await workspaceService.connectWorkspace(w.root_path, w.name);
                        setIsConnectModalOpen(false);
                        loadData();
                        loadFiles("");
                      }}
                      style={{
                        padding: "6px 10px",
                        borderRadius: "6px",
                        background: w.workspace_id === activeWorkspace?.workspace_id ? "rgba(147, 3, 197, 0.2)" : "rgba(255, 255, 255, 0.05)",
                        border: "1px solid var(--border-subtle)",
                        cursor: "pointer",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        fontSize: "12px",
                      }}
                    >
                      <span style={{ fontWeight: 600 }}>{w.name}</span>
                      <span style={{ color: "var(--text-muted)", fontSize: "11px", maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{w.root_path}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Yangi Loyiha Yo'li (Absolute Directory Path)
              </label>
              <input
                type="text"
                value={newWsPath}
                onChange={(e) => setNewWsPath(e.target.value)}
                placeholder="D:\Projects\my-app"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--surface)",
                  border: "1px solid var(--border-subtle)",
                  color: "#fff",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: "12px", color: "var(--text-secondary)", display: "block", marginBottom: "4px" }}>
                Loyiha Nomi (Ixtiyoriy)
              </label>
              <input
                type="text"
                value={newWsName}
                onChange={(e) => setNewWsName(e.target.value)}
                placeholder="My Application"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--surface)",
                  border: "1px solid var(--border-subtle)",
                  color: "#fff",
                  fontSize: "13px",
                  outline: "none",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
              <button
                onClick={() => setIsConnectModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "8px",
                  background: "var(--surface)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-secondary)",
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                onClick={handleConnectNew}
                disabled={!newWsPath.trim()}
                style={{
                  padding: "8px 20px",
                  borderRadius: "8px",
                  background: "linear-gradient(135deg, var(--misa-accent), var(--misa-accent-glow))",
                  border: "none",
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "13px",
                  cursor: !newWsPath.trim() ? "not-allowed" : "pointer",
                }}
              >
                Ulash
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const sectionBoxStyle: React.CSSProperties = {
  background: "var(--surface)",
  backdropFilter: "blur(24px)",
  borderRadius: "14px",
  border: "1px solid var(--border-subtle)",
  padding: "20px",
};

const innerBoxStyle: React.CSSProperties = {
  background: "rgba(0, 0, 0, 0.3)",
  padding: "10px 14px",
  borderRadius: "8px",
  border: "1px solid var(--border-subtle)",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
};
