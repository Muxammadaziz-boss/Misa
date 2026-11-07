// ========== AgentsPage.tsx ==========
// Misa AI v9.0.0 — Native Multi-Agent Hub & Dashboard
// Ultra Glass UI for Agent Directory, Orchestrator, Task Monitor, and Governance

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  SparklesIcon,
  HomeIcon,
  SearchIcon,
  RefreshIcon,
  CpuIcon,
  ShieldIcon,
  CheckCircleIcon,
  PlayIcon,
  StopIcon,
  ClockIcon,
  GridIcon,
  CloseIcon,
} from "../components/icons/Icons";
import {
  multiAgentService,
  MultiAgentAgent,
  MultiAgentOverview,
  MultiAgentTask,
  MultiAgentApproval,
} from "../services/multiAgentService";

interface AgentsPageProps {
  onNavigateHome: () => void;
}

export const AgentsPage: React.FC<AgentsPageProps> = ({ onNavigateHome }) => {
  const [activeTab, setActiveTab] = useState<"overview" | "directory" | "monitor" | "governance">("overview");
  const [overview, setOverview] = useState<MultiAgentOverview | null>(null);
  const [agents, setAgents] = useState<MultiAgentAgent[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [selectedDept, setSelectedDept] = useState<string>("Barchasi");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [, setLoading] = useState<boolean>(true);

  // Inspector modal
  const [selectedAgent, setSelectedAgent] = useState<MultiAgentAgent | null>(null);

  // Orchestration Runner
  const [orchestratorQuery, setOrchestratorQuery] = useState<string>("Audit the authentication architecture and test coverage");
  const [isRunningPlan, setIsRunningPlan] = useState<boolean>(false);
  const [activeRunResult, setActiveRunResult] = useState<any>(null);
  const [activeTasks, setActiveTasks] = useState<MultiAgentTask[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  // Approvals
  const [approvals, setApprovals] = useState<MultiAgentApproval[]>([]);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const mountedRef = React.useRef(true);

  const loadData = useCallback(async () => {
    if (!mountedRef.current) return;
    setLoading(true);
    try {
      const [ovData, agList, appList] = await Promise.all([
        multiAgentService.getOverview(),
        multiAgentService.getAgents(),
        multiAgentService.getApprovals(),
      ]);
      if (mountedRef.current) {
        setOverview(ovData);
        setAgents(agList);
        setApprovals(appList);
        if (ovData?.departments) {
          setDepartments(["Barchasi", ...ovData.departments]);
        }
      }
    } catch (e) {
      console.error("Failed to load multi-agent data:", e);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    loadData();

    // Listen to real-time multi-agent events via WebSocket
    const unsub = multiAgentService.onEvent((evt: any) => {
      if (!mountedRef.current) return;
      if (evt.type === "plan_created" && evt.tasks) {
        setActiveTasks(evt.tasks);
        setActiveRunId(evt.run_id);
      } else if (evt.type === "task_updated" && evt.task) {
        setActiveTasks((prev) => {
          const idx = prev.findIndex((t) => t.task_id === evt.task.task_id);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = evt.task;
            return next;
          }
          return [...prev, evt.task];
        });
      } else if (evt.type === "run_completed" && evt.result) {
        setActiveRunResult(evt.result);
        setIsRunningPlan(false);
        loadData();
      }
    });

    return () => {
      mountedRef.current = false;
      unsub();
    };
  }, [loadData]);

  // Trigger orchestration
  const handleRunOrchestration = async () => {
    if (!orchestratorQuery.trim() || isRunningPlan) return;
    setIsRunningPlan(true);
    setActiveRunResult(null);
    setActiveTasks([]);
    setActionMessage(null);

    try {
      const res = await multiAgentService.executeGoal(orchestratorQuery.trim());
      if (res && res.ok && res.data) {
        setActiveRunResult(res.data);
        if (res.data.tasks) setActiveTasks(res.data.tasks);
      } else {
        setActionMessage(res?.error || "Rejani bajarishda xatolik yuz berdi.");
      }
    } catch (err: any) {
      setActionMessage(err.message || "Xatolik yuz berdi.");
    } finally {
      setIsRunningPlan(false);
      loadData();
    }
  };

  const handleCancelRun = async () => {
    if (activeRunId) {
      await multiAgentService.cancelRun(activeRunId);
      setIsRunningPlan(false);
    }
  };

  const handleApprove = async (token: string) => {
    const res = await multiAgentService.approveOperation(token);
    setActionMessage(res.message);
    loadData();
  };

  const handleReject = async (token: string) => {
    const res = await multiAgentService.rejectOperation(token);
    setActionMessage(res.message);
    loadData();
  };

  const handleToggleAgentStatus = async (agent: MultiAgentAgent) => {
    if (agent.status === "disabled") {
      await multiAgentService.enableAgent(agent.agent_id);
    } else {
      await multiAgentService.disableAgent(agent.agent_id);
    }
    loadData();
    if (selectedAgent && selectedAgent.agent_id === agent.agent_id) {
      const updated = await multiAgentService.getAgent(agent.agent_id);
      setSelectedAgent(updated);
    }
  };

  // Filtered agents
  const filteredAgents = useMemo(() => {
    return agents.filter((a) => {
      const matchesDept = selectedDept === "Barchasi" || a.department.toLowerCase() === selectedDept.toLowerCase();
      const q = searchQuery.toLowerCase().trim();
      const matchesQuery =
        !q ||
        a.name.toLowerCase().includes(q) ||
        a.agent_id.toLowerCase().includes(q) ||
        a.description.toLowerCase().includes(q) ||
        a.capabilities.some((c) => c.toLowerCase().includes(q));
      return matchesDept && matchesQuery;
    });
  }, [agents, selectedDept, searchQuery]);

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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
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
              <CpuIcon size={20} color="#fff" />
            </div>
            <h1 style={{ fontSize: "24px", fontWeight: 700, margin: 0, letterSpacing: "-0.5px" }}>
              Multi-Agent Ekologik Markazi
            </h1>
          </div>
          <p style={{ margin: "4px 0 0 0", color: "var(--text-secondary)", fontSize: "14px" }}>
            15 ta ixtisoslashgan mahalliy agentlar koordinatsiyasi, DAG vazifalar taqsimoti va xavfsiz boshqaruv.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
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

      {/* Navigation Tabs */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          borderBottom: "1px solid var(--border-subtle)",
          paddingBottom: "12px",
          marginBottom: "20px",
        }}
      >
        {[
          { id: "overview", label: "Umumiy Ko'rinish & Reja", icon: SparklesIcon },
          { id: "directory", label: `Agentlar Katalogi (${agents.length})`, icon: GridIcon },
          { id: "monitor", label: "Ishlash Monitori & Telemetriya", icon: ClockIcon },
          { id: "governance", label: `Xavfsizlik & Ruxsatlar (${approvals.length})`, icon: ShieldIcon },
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
              transition: "all 0.15s ease",
            }}
          >
            <tab.icon size={15} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Global Banner for Action Notifications */}
      {actionMessage && (
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
          <span>{actionMessage}</span>
          <button onClick={() => setActionMessage(null)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer" }}>
            <CloseIcon size={14} />
          </button>
        </div>
      )}

      {/* TAB 1: OVERVIEW & RUNNER */}
      {activeTab === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Key Metrics Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "14px" }}>
            <div style={cardStyle}>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Jami Mutaxassis Agentlar</span>
              <span style={{ fontSize: "28px", fontWeight: 700, color: "var(--text-primary)", marginTop: "4px" }}>
                {overview?.total_agents || agents.length || 15}
              </span>
              <span style={{ fontSize: "11px", color: "var(--success-glow)", marginTop: "2px" }}>
                {overview?.active_agents || 15} ta faol / 0 ta xato
              </span>
            </div>
            <div style={cardStyle}>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Bajarilgan Vazifalar</span>
              <span style={{ fontSize: "28px", fontWeight: 700, color: "var(--primary-glow)", marginTop: "4px" }}>
                {overview?.telemetry.total_tasks || 0}
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                {overview?.telemetry.total_runs || 0} ta orkestratsiyada
              </span>
            </div>
            <div style={cardStyle}>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Muvaffaqiyat Darajasi</span>
              <span style={{ fontSize: "28px", fontWeight: 700, color: "var(--success)", marginTop: "4px" }}>
                {overview?.telemetry.overall_success_rate || 100}%
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                0 ta muvaffaqiyatsiz
              </span>
            </div>
            <div style={cardStyle}>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Ishlatilgan Tokenlar</span>
              <span style={{ fontSize: "28px", fontWeight: 700, color: "var(--text-primary)", marginTop: "4px" }}>
                {overview?.telemetry.total_tokens?.toLocaleString() || 0}
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>
                Kontekst tejamkorligi
              </span>
            </div>
          </div>

          {/* Interactive Orchestrator Runner */}
          <div style={sectionBoxStyle}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <SparklesIcon size={18} color="var(--primary-glow)" />
                <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>
                  Misa Main — Multi-Agent Orkestratsiyasini Ishga Tushirish
                </h3>
              </div>
              {isRunningPlan && (
                <button
                  onClick={handleCancelRun}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "6px 12px",
                    borderRadius: "6px",
                    background: "rgba(239, 68, 68, 0.2)",
                    border: "1px solid var(--danger)",
                    color: "var(--danger-soft)",
                    cursor: "pointer",
                    fontSize: "12px",
                  }}
                >
                  <StopIcon size={12} /> Bekor qilish
                </button>
              )}
            </div>

            <p style={{ margin: "0 0 12px 0", fontSize: "13px", color: "var(--text-secondary)" }}>
              Istalgan murakkab so'rovni kiriting. Misa Main vazifani DAG grafigi bo'yicha tahlil qiladi, kerakli mutaxassis agentlarga taqsimlaydi va yakuniy dalillangan hisobotni taqdim etadi.
            </p>

            <div style={{ display: "flex", gap: "10px" }}>
              <input
                type="text"
                value={orchestratorQuery}
                onChange={(e) => setOrchestratorQuery(e.target.value)}
                placeholder="Masalan: Audit the authentication architecture, security controls and missing test cases"
                onKeyDown={(e) => e.key === "Enter" && handleRunOrchestration()}
                disabled={isRunningPlan}
                className="misa-glass-input"
                style={{
                  flex: 1,
                  padding: "12px 16px",
                  borderRadius: "12px",
                  fontSize: "14px",
                }}
              />
              <button
                onClick={handleRunOrchestration}
                disabled={isRunningPlan || !orchestratorQuery.trim()}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "12px 24px",
                  borderRadius: "10px",
                  background: isRunningPlan
                    ? "var(--surface)"
                    : "linear-gradient(135deg, var(--misa-accent), var(--misa-accent-glow))",
                  border: "none",
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: "14px",
                  cursor: isRunningPlan ? "not-allowed" : "pointer",
                  boxShadow: isRunningPlan ? "none" : "0 0 16px var(--misa-accent-glow)",
                }}
              >
                {isRunningPlan ? (
                  <>
                    <RefreshIcon size={16} /> Bajarilmoqda...
                  </>
                ) : (
                  <>
                    <PlayIcon size={16} /> Orkestratsiya
                  </>
                )}
              </button>
            </div>

            {/* Real-time Subtask Execution List */}
            {activeTasks.length > 0 && (
              <div style={{ marginTop: "20px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "10px", color: "var(--text-secondary)" }}>
                  DAG Taqsimot Vazifalari ({activeTasks.length}):
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {activeTasks.map((t) => (
                    <div
                      key={t.task_id}
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
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <StatusBadge status={t.status} />
                        <div>
                          <div style={{ fontSize: "13px", fontWeight: 600 }}>{t.title}</div>
                          <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                            Tayinlangan: <span style={{ color: "var(--primary-glow)" }}>{t.assigned_agent_id}</span>
                            {t.dependencies.length > 0 && ` | Bog'liq: ${t.dependencies.join(", ")}`}
                          </div>
                        </div>
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                        {t.status === "completed" && <CheckCircleIcon size={16} color="var(--success)" />}
                        {t.status === "running" && <RefreshIcon size={16} color="var(--primary-glow)" />}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Synthesized Output Result */}
            {activeRunResult && (
              <div
                style={{
                  marginTop: "20px",
                  padding: "16px",
                  borderRadius: "10px",
                  background: "rgba(10, 6, 18, 0.75)",
                  border: "1px solid var(--primary)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <h4 style={{ margin: 0, fontSize: "15px", color: "var(--primary-glow)" }}>
                    Konsolidatsiyalangan Yakuniy Natija
                  </h4>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    Vaqt: {activeRunResult.duration_seconds}s | Tokenlar: {activeRunResult.total_tokens}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: "13px",
                    lineHeight: "1.6",
                    whiteSpace: "pre-wrap",
                    fontFamily: "var(--font-mono, monospace)",
                    color: "var(--text-primary)",
                  }}
                >
                  {activeRunResult.final_response}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: AGENT DIRECTORY */}
      {activeTab === "directory" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Filters Bar */}
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ position: "relative", flex: 1, minWidth: "260px" }}>
              <span style={{ position: "absolute", left: "12px", top: "12px", pointerEvents: "none" }}><SearchIcon size={16} color="var(--text-muted)" /></span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Agent nomi, ID yoki qobiliyat bo'yicha qidirish..."
                className="misa-glass-input"
                style={{
                  width: "100%",
                  padding: "10px 14px 10px 38px",
                  borderRadius: "12px",
                  fontSize: "13px",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: "6px", overflowX: "auto" }}>
              {departments.map((dept) => (
                <button
                  key={dept}
                  onClick={() => setSelectedDept(dept)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: "6px",
                    background: selectedDept === dept ? "var(--primary)" : "var(--surface)",
                    border: "1px solid var(--border-subtle)",
                    color: selectedDept === dept ? "#fff" : "var(--text-secondary)",
                    fontSize: "12px",
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  {dept}
                </button>
              ))}
            </div>
          </div>

          {/* Agent Cards Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
              gap: "16px",
            }}
          >
            {filteredAgents.map((agent) => (
              <div
                key={agent.agent_id}
                onClick={() => setSelectedAgent(agent)}
                style={{
                  ...cardStyle,
                  cursor: "pointer",
                  transition: "transform 0.15s ease, border-color 0.15s ease",
                  border: "1px solid var(--border-subtle)",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "var(--primary-glow)";
                  e.currentTarget.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-subtle)";
                  e.currentTarget.style.transform = "none";
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                  <div>
                    <span
                      style={{
                        fontSize: "11px",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        background: "rgba(147, 3, 197, 0.2)",
                        color: "var(--primary-glow)",
                        fontWeight: 600,
                      }}
                    >
                      {agent.department}
                    </span>
                    <h3 style={{ margin: "6px 0 2px 0", fontSize: "16px", fontWeight: 600 }}>{agent.name}</h3>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "monospace" }}>
                      @{agent.agent_id} (v{agent.version})
                    </span>
                  </div>
                  <StatusBadge status={agent.status} />
                </div>

                <p
                  style={{
                    fontSize: "12px",
                    color: "var(--text-secondary)",
                    lineHeight: "1.4",
                    margin: "6px 0 10px 0",
                    height: "36px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {agent.description}
                </p>

                {/* Capabilities Badges */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginBottom: "12px" }}>
                  {agent.capabilities.slice(0, 3).map((cap) => (
                    <span
                      key={cap}
                      style={{
                        fontSize: "10px",
                        padding: "2px 6px",
                        borderRadius: "4px",
                        background: "rgba(255, 255, 255, 0.06)",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {cap}
                    </span>
                  ))}
                  {agent.capabilities.length > 3 && (
                    <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                      +{agent.capabilities.length - 3}
                    </span>
                  )}
                </div>

                {/* Model & Tools Meta */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "11px",
                    color: "var(--text-muted)",
                    borderTop: "1px solid var(--border-subtle)",
                    paddingTop: "8px",
                  }}
                >
                  <span>Model: {agent.model_preference?.tier || "global"}</span>
                  <span>Ruxsat: {agent.permission_profile?.category?.toUpperCase()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: MONITOR & TELEMETRY */}
      {activeTab === "monitor" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={sectionBoxStyle}>
            <h3 style={{ margin: "0 0 14px 0", fontSize: "16px" }}>Agentlar Bo'yicha Telemetriya va Statistika</h3>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-subtle)", textAlign: "left", color: "var(--text-muted)" }}>
                    <th style={{ padding: "8px 12px" }}>Agent</th>
                    <th style={{ padding: "8px 12px" }}>Bajarilgan Ishlar</th>
                    <th style={{ padding: "8px 12px" }}>Muvaffaqiyat</th>
                    <th style={{ padding: "8px 12px" }}>O'rtacha Vaqt</th>
                    <th style={{ padding: "8px 12px" }}>Jami Tokenlar</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(overview?.telemetry.agent_metrics || {}).map(([aid, m]: any) => (
                    <tr key={aid} style={{ borderBottom: "1px solid rgba(255, 255, 255, 0.04)" }}>
                      <td style={{ padding: "10px 12px", fontWeight: 600, color: "var(--primary-glow)" }}>{aid}</td>
                      <td style={{ padding: "10px 12px" }}>{m.tasks_executed}</td>
                      <td style={{ padding: "10px 12px", color: "var(--success)" }}>{m.success_rate_percent}%</td>
                      <td style={{ padding: "10px 12px" }}>{m.avg_duration_seconds}s</td>
                      <td style={{ padding: "10px 12px" }}>{m.total_tokens}</td>
                    </tr>
                  ))}
                  {Object.keys(overview?.telemetry.agent_metrics || {}).length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)" }}>
                        Hozircha orkestratsiya telemetriyasi qayd etilmagan. Yuqoridagi "Umumiy Ko'rinish" orqali birinchi rejalashtirishni ishga tushiring!
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: GOVERNANCE & APPROVALS */}
      {activeTab === "governance" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={sectionBoxStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
              <ShieldIcon size={18} color="var(--primary-glow)" />
              <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>
                Kriptografik Tasdiqlashlar (Human-in-the-Loop)
              </h3>
            </div>
            <p style={{ margin: "0 0 16px 0", fontSize: "13px", color: "var(--text-secondary)" }}>
              Xavfli amallar (fayl o'chirish, tizim buyruqlari, relizlar) bajarilishidan oldin foydalanuvchining bevosita ruxsatini talab qiladi.
            </p>

            {approvals.length === 0 ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                Ayni damda tasdiqlashni kutayotgan xavfli amallar mavjud emas. Barcha agentlar xavfsiz chegaralarda ishlamoqda.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {approvals.map((appr) => (
                  <div
                    key={appr.token}
                    style={{
                      padding: "14px 18px",
                      borderRadius: "10px",
                      background: "rgba(239, 68, 68, 0.1)",
                      border: "1px solid var(--danger)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--danger-soft)" }}>
                        {appr.agent_name} (@{appr.agent_id}) — Tool: {appr.tool_name}
                      </div>
                      <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
                        Parametrlar: {JSON.stringify(appr.arguments)}
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: "8px" }}>
                      <button
                        onClick={() => handleApprove(appr.token)}
                        style={{
                          padding: "6px 14px",
                          borderRadius: "6px",
                          background: "var(--success)",
                          border: "none",
                          color: "#fff",
                          fontWeight: 600,
                          fontSize: "12px",
                          cursor: "pointer",
                        }}
                      >
                        Ruxsat berish
                      </button>
                      <button
                        onClick={() => handleReject(appr.token)}
                        style={{
                          padding: "6px 14px",
                          borderRadius: "6px",
                          background: "var(--surface)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--text-secondary)",
                          fontSize: "12px",
                          cursor: "pointer",
                        }}
                      >
                        Rad etish
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* INSPECTOR MODAL */}
      {selectedAgent && (
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
          onClick={() => setSelectedAgent(null)}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "680px",
              maxHeight: "85vh",
              overflowY: "auto",
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
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <span style={{ fontSize: "11px", color: "var(--primary-glow)", fontWeight: 600 }}>
                  {selectedAgent.department}
                </span>
                <h2 style={{ margin: "4px 0 2px 0", fontSize: "20px" }}>{selectedAgent.name}</h2>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  ID: @{selectedAgent.agent_id} | Versiya: {selectedAgent.version}
                </span>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <CloseIcon size={20} />
              </button>
            </div>

            <div>
              <h4 style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 4px 0" }}>Tavsif</h4>
              <p style={{ fontSize: "13px", margin: 0, lineHeight: "1.5" }}>{selectedAgent.description}</p>
            </div>

            <div>
              <h4 style={{ fontSize: "13px", color: "var(--text-secondary)", margin: "0 0 6px 0" }}>System Instructions</h4>
              <div
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  background: "rgba(0,0,0,0.5)",
                  fontSize: "12px",
                  lineHeight: "1.5",
                  whiteSpace: "pre-wrap",
                  maxHeight: "160px",
                  overflowY: "auto",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {selectedAgent.system_instructions}
              </div>
            </div>

            {/* Permissions & Policies Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "12px" }}>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Xavfsizlik Toifasi:</span>
                <span style={{ fontWeight: 600, color: "var(--primary-glow)" }}>
                  {selectedAgent.permission_profile?.category?.toUpperCase()}
                </span>
              </div>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Faqat O'qish Rejimi:</span>
                <span style={{ fontWeight: 600 }}>{selectedAgent.permission_profile?.read_only ? "Ha (Read-Only)" : "Yo'q (Write/Exec)"}</span>
              </div>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Model Pog'onasi:</span>
                <span style={{ fontWeight: 600 }}>{selectedAgent.model_preference?.tier}</span>
              </div>
              <div style={innerBoxStyle}>
                <span style={{ color: "var(--text-muted)" }}>Timeout Cheklovi:</span>
                <span style={{ fontWeight: 600 }}>{selectedAgent.execution_limits?.timeout_seconds}s</span>
              </div>
            </div>

            {/* Toggle Status Button */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
              {!selectedAgent.is_builtin ? (
                <button
                  onClick={() => handleToggleAgentStatus(selectedAgent)}
                  style={{
                    padding: "8px 16px",
                    borderRadius: "8px",
                    background: selectedAgent.status === "disabled" ? "var(--success)" : "rgba(239, 68, 68, 0.2)",
                    border: "1px solid " + (selectedAgent.status === "disabled" ? "var(--success)" : "var(--danger)"),
                    color: "#fff",
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  {selectedAgent.status === "disabled" ? "Agentni Yoqish" : "Agentni O'chirish"}
                </button>
              ) : (
                <span style={{ fontSize: "11px", color: "var(--text-muted)", alignSelf: "center" }}>
                  Tizimiy asosiy agent (Built-in)
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// UI Components & Styles
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const isBusy = status === "running" || status === "busy" || status === "reviewing";
  const isErr = status === "failed" || status === "error";

  let bg = "rgba(16, 185, 129, 0.15)";
  let color = "var(--success-glow)";
  let label = "Faol";

  if (isBusy) {
    bg = "rgba(147, 3, 197, 0.25)";
    color = "var(--primary-glow)";
    label = status.toUpperCase();
  } else if (isErr) {
    bg = "rgba(239, 68, 68, 0.2)";
    color = "var(--danger-soft)";
    label = "XATO";
  } else if (status === "disabled") {
    bg = "rgba(255, 255, 255, 0.08)";
    color = "var(--text-muted)";
    label = "O'chiq";
  } else if (status === "queued" || status === "pending") {
    bg = "rgba(245, 158, 11, 0.15)";
    color = "var(--warning)";
    label = status.toUpperCase();
  }

  return (
    <span
      style={{
        fontSize: "11px",
        padding: "2px 8px",
        borderRadius: "12px",
        background: bg,
        color: color,
        fontWeight: 600,
        textTransform: "capitalize",
      }}
    >
      {label}
    </span>
  );
};

const cardStyle: React.CSSProperties = {
  background: "var(--surface)",
  backdropFilter: "blur(24px)",
  borderRadius: "12px",
  border: "1px solid var(--border-subtle)",
  padding: "16px",
  display: "flex",
  flexDirection: "column",
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
