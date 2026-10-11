// ========== SchedulerPage.tsx ==========
// Misa AI v9.0 — Rejalashtirish Markazi (4-View Calendar & Intelligent Task System)
// Views: Soatlik (Hourly), Kunlik (Daily), Oylik (Monthly), Yillik (Yearly)

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  SchedulerIcon,
  SparklesIcon,
  CloseIcon,
  TrashIcon,
  ClockIcon,
  CheckIcon,
} from "../components/icons/Icons";
import { backendService, SchedulerTask } from "../services/backendService";

interface SchedulerPageProps {
  onNavigateHome: () => void;
  onAskMisa?: (query: string) => void;
}

type CalendarViewMode = "hourly" | "daily" | "monthly" | "yearly";
type TaskFilterMode = "all" | "today" | "next7" | "completed" | "overdue";
type TaskPriority = "high" | "medium" | "low";
type TaskCategory = "Ishlab chiqish" | "Dizayn" | "Ta'lim" | "Boshqaruv" | "Tizim";

interface RichPlannerTask {
  id: string;
  backendId?: string;
  title: string;
  description: string;
  date: string; // YYYY-MM-DD
  startTime: string; // HH:MM
  endTime: string; // HH:MM
  priority: TaskPriority;
  category: TaskCategory;
  completed: boolean;
  repeatSeconds?: number;
}

const UZBEK_MONTHS = [
  "Yanvar",
  "Fevral",
  "Mart",
  "Aprel",
  "May",
  "Iyun",
  "Iyul",
  "Avgust",
  "Sentabr",
  "Oktabr",
  "Noyabr",
  "Dekabr",
];

const UZBEK_WEEKDAYS_SHORT = ["Dush", "Sesh", "Chor", "Pay", "Jum", "Shan", "Yak"];

function toIsoDateStr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const PRIORITY_BADGE: Record<
  TaskPriority,
  { label: string; bg: string; border: string; text: string; dot: string }
> = {
  high: {
    label: "Yuqori",
    bg: "rgba(239, 68, 68, 0.14)",
    border: "rgba(239, 68, 68, 0.32)",
    text: "#FCA5A5",
    dot: "#EF4444",
  },
  medium: {
    label: "O'rta",
    bg: "rgba(245, 158, 11, 0.14)",
    border: "rgba(245, 158, 11, 0.32)",
    text: "#FCD34D",
    dot: "#F59E0B",
  },
  low: {
    label: "Oddiy",
    bg: "rgba(147, 3, 197, 0.18)",
    border: "rgba(192, 76, 253, 0.32)",
    text: "#E8B3FF",
    dot: "#C04CFD",
  },
};

export const SchedulerPage: React.FC<SchedulerPageProps> = ({ onAskMisa }) => {
  const [viewMode, setViewMode] = useState<CalendarViewMode>("daily");
  const [taskFilter, setTaskFilter] = useState<TaskFilterMode>("all");
  const [selectedDate, setSelectedDate] = useState<Date>(() => new Date());

  // Backend scheduler tasks + local rich planner tasks
  const [backendTasks, setBackendTasks] = useState<SchedulerTask[]>([]);
  const [localTasks, setLocalTasks] = useState<RichPlannerTask[]>(() => {
    try {
      const raw = localStorage.getItem("misa_planner_tasks");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    const todayStr = toIsoDateStr(new Date());
    return [
      {
        id: "plan_1",
        title: "Misa AI v9.0 Ultra Glass tizim arxitekturasini ko'rib chiqish",
        description: "Asosiy oynalar, suzuvchi navigatsiya va xotira markazi integratsiyasini tekshirish.",
        date: todayStr,
        startTime: "10:00",
        endTime: "11:30",
        priority: "high",
        category: "Dizayn",
        completed: true,
      },
      {
        id: "plan_2",
        title: "Backend API va Neyron javob tezligini optimallashtirish",
        description: "Kontekst oynasi va tezkor xotira qidiruv algoritmini sinovdan o'tkazish.",
        date: todayStr,
        startTime: "14:00",
        endTime: "15:30",
        priority: "high",
        category: "Ishlab chiqish",
        completed: false,
      },
      {
        id: "plan_3",
        title: "Haftalik loyiha natijalari tahlili va hisobot",
        description: "Bajarilgan vazifalar ko'rsatkichlarini jamlash va keyingi sprint rejasini tuzish.",
        date: todayStr,
        startTime: "17:00",
        endTime: "18:00",
        priority: "medium",
        category: "Boshqaruv",
        completed: false,
      },
    ];
  });

  // Create Plan Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formTitle, setFormTitle] = useState<string>("");
  const [formDesc, setFormDesc] = useState<string>("");
  const [formDate, setFormDate] = useState<string>(() => toIsoDateStr(new Date()));
  const [formStartTime, setFormStartTime] = useState<string>("14:00");
  const [formEndTime, setFormEndTime] = useState<string>("15:00");
  const [formPriority, setFormPriority] = useState<TaskPriority>("high");
  const [formCategory, setFormCategory] = useState<TaskCategory>("Ishlab chiqish");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const saveLocalTasks = (next: RichPlannerTask[]) => {
    setLocalTasks(next);
    try {
      localStorage.setItem("misa_planner_tasks", JSON.stringify(next));
    } catch {}
  };

  const fetchBackendTasks = useCallback(async () => {
    try {
      const res = await backendService.getSchedulerTasks();
      if (res && res.ok) {
        setBackendTasks(res.tasks || []);
      }
    } catch {}
  }, []);

  useEffect(() => {
    fetchBackendTasks();
    const timer = setInterval(fetchBackendTasks, 8000);
    return () => clearInterval(timer);
  }, [fetchBackendTasks]);

  // Merge backend tasks with local rich tasks
  const allTasks = useMemo<RichPlannerTask[]>(() => {
    const todayStr = toIsoDateStr(new Date());
    const merged = [...localTasks];
    const existingBackendIds = new Set(merged.map((t) => t.backendId).filter(Boolean));

    backendTasks.forEach((bt) => {
      if (existingBackendIds.has(bt.id)) {
        const idx = merged.findIndex((m) => m.backendId === bt.id);
        if (idx !== -1) {
          merged[idx] = { ...merged[idx], completed: bt.completed };
        }
        return;
      }
      const datePart = bt.trigger_time?.includes(" ")
        ? bt.trigger_time.split(" ")[0]
        : todayStr;
      const timePart = bt.trigger_time?.includes(" ")
        ? bt.trigger_time.split(" ")[1].slice(0, 5)
        : bt.trigger_time?.slice(0, 5) || "12:00";

      merged.push({
        id: `bt_${bt.id}`,
        backendId: bt.id,
        title: bt.title || bt.data?.text || "Rejalashtirilgan vazifa",
        description: bt.command
          ? `Avtomatik buyruq: ${bt.command}`
          : "Misa eslatmasi va rejalashtirilgan vazifa",
        date: /^\d{4}-\d{2}-\d{2}$/.test(datePart) ? datePart : todayStr,
        startTime: /^\d{2}:\d{2}$/.test(timePart) ? timePart : "12:00",
        endTime: "13:00",
        priority: (bt.repeat_seconds ?? 0) > 0 ? "medium" : "high",
        category: "Tizim",
        completed: bt.completed,
        repeatSeconds: bt.repeat_seconds,
      });
    });

    return merged.sort((a, b) => a.startTime.localeCompare(b.startTime));
  }, [localTasks, backendTasks]);

  const selectedDateStr = toIsoDateStr(selectedDate);
  const todayDateStr = toIsoDateStr(new Date());

  // Filtered tasks for daily view
  const displayedTasks = useMemo(() => {
    return allTasks.filter((t) => {
      if (taskFilter === "today") return t.date === selectedDateStr;
      if (taskFilter === "completed") return t.completed;
      if (taskFilter === "overdue") return !t.completed && t.date < todayDateStr;
      if (taskFilter === "next7") {
        const d = new Date(t.date);
        const diffDays = (d.getTime() - selectedDate.getTime()) / (1000 * 3600 * 24);
        return diffDays >= -1 && diffDays <= 7;
      }
      return true;
    });
  }, [allTasks, taskFilter, selectedDateStr, todayDateStr, selectedDate]);

  // Metrics
  const stats = useMemo(() => {
    const total = allTasks.length;
    const done = allTasks.filter((t) => t.completed).length;
    const remaining = total - done;
    const percent = total > 0 ? Math.round((done / total) * 100) : 0;
    return { total, done, remaining, percent };
  }, [allTasks]);

  // Date navigation handlers
  const handleStepDate = (dir: -1 | 1) => {
    setSelectedDate((prev) => {
      const next = new Date(prev);
      if (viewMode === "hourly" || viewMode === "daily") {
        next.setDate(next.getDate() + dir);
      } else if (viewMode === "monthly") {
        next.setMonth(next.getMonth() + dir);
      } else {
        next.setFullYear(next.getFullYear() + dir);
      }
      return next;
    });
  };

  const formattedNavigatorLabel = useMemo(() => {
    const day = selectedDate.getDate();
    const month = UZBEK_MONTHS[selectedDate.getMonth()];
    const year = selectedDate.getFullYear();
    if (viewMode === "yearly") return `${year}-yil`;
    if (viewMode === "monthly") return `${month}, ${year}`;
    return `${day} ${month}, ${year}`;
  }, [selectedDate, viewMode]);

  const handleToggleTaskComplete = (task: RichPlannerTask) => {
    const updated = localTasks.map((t) =>
      t.id === task.id ? { ...t, completed: !t.completed } : t
    );
    saveLocalTasks(updated);
    showToast(!task.completed ? "Vazifa bajarildi ✓" : "Vazifa faol holatga qaytarildi");
  };

  const handleDeleteTask = async (task: RichPlannerTask) => {
    if (task.backendId) {
      await backendService.deleteSchedulerTask(task.backendId);
      await fetchBackendTasks();
    }
    const updated = localTasks.filter((t) => t.id !== task.id);
    saveLocalTasks(updated);
    showToast("Reja o'chirildi");
  };

  const handleCreatePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || isSubmitting) return;
    setIsSubmitting(true);

    try {
      // Also schedule on backend if startTime is valid HH:MM
      const res = await backendService.addSchedulerTask({
        title: formTitle.trim(),
        time_str: formStartTime || "14:00",
      });

      const newTask: RichPlannerTask = {
        id: `plan_${Date.now()}`,
        backendId: res.task?.id,
        title: formTitle.trim(),
        description: formDesc.trim() || "Misa Rejalashtirish Markazi orqali kiritilgan vazifa",
        date: formDate || selectedDateStr,
        startTime: formStartTime || "14:00",
        endTime: formEndTime || "15:00",
        priority: formPriority,
        category: formCategory,
        completed: false,
      };

      saveLocalTasks([newTask, ...localTasks]);
      await fetchBackendTasks();
      setFormTitle("");
      setFormDesc("");
      setIsModalOpen(false);
      showToast("Yangi reja muvaffaqiyatli qo'shildi ✓");
    } catch {
      showToast("Reja saqlandi");
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (!isModalOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsModalOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isModalOpen]);

  // Monthly Calendar Days Builder
  const monthlyCells = useMemo(() => {
    const year = selectedDate.getFullYear();
    const month = selectedDate.getMonth();
    const firstDayOfMonth = new Date(year, month, 1);
    const startOffset = (firstDayOfMonth.getDay() + 6) % 7; // Monday = 0
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const cells: { day: number | null; dateStr: string; tasks: RichPlannerTask[] }[] = [];
    for (let i = 0; i < startOffset; i++) {
      cells.push({ day: null, dateStr: "", tasks: [] });
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const dt = new Date(year, month, d);
      const dStr = toIsoDateStr(dt);
      const dayTasks = allTasks.filter((t) => t.date === dStr);
      cells.push({ day: d, dateStr: dStr, tasks: dayTasks });
    }
    return cells;
  }, [selectedDate, allTasks]);

  const highPriorityTasks = useMemo(
    () => allTasks.filter((t) => !t.completed && t.priority === "high").slice(0, 3),
    [allTasks]
  );

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        maxWidth: "1440px",
        margin: "0 auto",
        padding: "12px 24px 28px 24px",
        display: "flex",
        flexDirection: "column",
        gap: "18px",
        overflowY: "auto",
        position: "relative",
        zIndex: 5,
      }}
    >
      {toastMsg && (
        <div
          className="misa-ultra-glass"
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 600,
            padding: "10px 18px",
            borderRadius: "999px",
            border: "1px solid rgba(78, 222, 163, 0.45)",
            color: "#4EDEA3",
            fontSize: "12.5px",
            fontWeight: 600,
          }}
        >
          {toastMsg}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          1. PAGE HEADER, 4-VIEW SWITCHER & DATE NAVIGATOR
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "14px",
          paddingBottom: "14px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.06)",
        }}
      >
        {/* Title & Faol Rejim Badge */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "26px",
                fontWeight: 700,
                color: "#FFFFFF",
                letterSpacing: "-0.02em",
              }}
            >
              Rejalashtirish Markazi
            </h1>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "3px 10px",
                borderRadius: "999px",
                background: "rgba(16, 185, 129, 0.14)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "#4EDEA3",
                fontSize: "11px",
                fontWeight: 600,
              }}
            >
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  backgroundColor: "#10B981",
                }}
              />
              <span>Faol rejim</span>
            </span>
          </div>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "3px" }}>
            Misa yordamida kunlik, oylik va yillik maqsadlaringizni aqlli boshqaring
          </p>
        </div>

        {/* 4-View Segmented Control + Date Navigator + Actions */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" }}>
          {/* 4-View Segmented Control Pill */}
          <div
            className="misa-glass-card"
            style={{
              display: "flex",
              alignItems: "center",
              padding: "4px",
              borderRadius: "9999px",
              gap: "2px",
            }}
          >
            {(
              [
                { id: "hourly", label: "Soatlik" },
                { id: "daily", label: "Kunlik" },
                { id: "monthly", label: "Oylik" },
                { id: "yearly", label: "Yillik" },
              ] as { id: CalendarViewMode; label: string }[]
            ).map((v) => {
              const active = viewMode === v.id;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setViewMode(v.id)}
                  style={{
                    padding: "6px 14px",
                    borderRadius: "9999px",
                    fontSize: "12px",
                    fontWeight: active ? 600 : 500,
                    color: active ? "#FFFFFF" : "var(--text-secondary)",
                    background: active
                      ? "linear-gradient(135deg, rgba(147, 3, 197, 0.42) 0%, rgba(192, 76, 253, 0.24) 100%)"
                      : "transparent",
                    border: active
                      ? "1px solid rgba(192, 76, 253, 0.5)"
                      : "1px solid transparent",
                    boxShadow: active ? "0 0 16px rgba(147, 3, 197, 0.3)" : "none",
                    cursor: "pointer",
                  }}
                >
                  {v.label}
                </button>
              );
            })}
          </div>

          {/* Date Navigation Pill */}
          <div
            className="misa-glass-card"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              padding: "4px 6px",
              borderRadius: "9999px",
            }}
          >
            <button
              type="button"
              onClick={() => handleStepDate(-1)}
              title="Oldingi"
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              ‹
            </button>
            <span
              style={{
                fontSize: "12px",
                fontWeight: 600,
                color: "#FFFFFF",
                minWidth: "120px",
                textAlign: "center",
                padding: "0 6px",
              }}
            >
              {formattedNavigatorLabel}
            </span>
            <button
              type="button"
              onClick={() => handleStepDate(1)}
              title="Keyingi"
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                color: "var(--text-secondary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              ›
            </button>
            <div style={{ width: "1px", height: "14px", background: "rgba(255,255,255,0.1)" }} />
            <button
              type="button"
              onClick={() => setSelectedDate(new Date())}
              style={{
                padding: "4px 10px",
                borderRadius: "999px",
                fontSize: "11px",
                fontWeight: 600,
                color: "#E8B3FF",
              }}
            >
              Bugun
            </button>
          </div>

          {/* Misa bilan rejalashtirish AI Action Button */}
          <button
            type="button"
            onClick={() => {
              if (onAskMisa) {
                onAskMisa(
                  "Bugungi vazifalarim va maqsadlarim asosida eng samarali soatbay kun tartibini tuzib ber"
                );
              } else {
                showToast("Misa vazifalaringizni ustuvorlik bo'yicha saraladi ✨");
              }
            }}
            className="misa-glass-card"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "7px",
              padding: "8px 15px",
              borderRadius: "9999px",
              border: "1px solid rgba(192, 76, 253, 0.35)",
              color: "#E8B3FF",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <SparklesIcon size={14} color="#C04CFD" />
            <span>Misa bilan rejalashtirish</span>
          </button>

          {/* + Yangi reja Primary Button */}
          <button
            type="button"
            onClick={() => {
              setFormDate(selectedDateStr);
              setIsModalOpen(true);
            }}
            className="misa-btn-violet"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 18px",
              borderRadius: "9999px",
              fontSize: "12.5px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <span style={{ fontSize: "15px", lineHeight: 1 }}>+</span>
            <span>Yangi reja</span>
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          2. MAIN 12-COLUMN WORKSPACE GRID (8 LEFT + 4 RIGHT)
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 2fr) minmax(300px, 1fr)",
          gap: "20px",
          alignItems: "start",
        }}
      >
        {/* ── LEFT 8 COLUMNS: ACTIVE VIEW AREA ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px", minWidth: 0 }}>
          {/* ==============================================================
              VIEW A: KUNLIK (DAILY SUMMARY, FILTERS, TASKS & TIME RIBBON)
             ============================================================== */}
          {viewMode === "daily" && (
            <>
              {/* Daily Summary Report Card */}
              <div
                className="misa-glass-card"
                style={{
                  padding: "20px 24px",
                  borderRadius: "22px",
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "16px",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                    <span
                      style={{
                        padding: "2px 9px",
                        borderRadius: "6px",
                        background: "rgba(147, 3, 197, 0.22)",
                        border: "1px solid rgba(192, 76, 253, 0.35)",
                        fontSize: "10px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        color: "#E8B3FF",
                      }}
                    >
                      Bugungi Hisobot
                    </span>
                    <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                      • {formattedNavigatorLabel}
                    </span>
                  </div>
                  <h2
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: "20px",
                      fontWeight: 700,
                      color: "#FFFFFF",
                      marginBottom: "10px",
                    }}
                  >
                    Kunlik Reja va Bajarilish Ko'rsatkichi
                  </h2>
                  <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "18px" }}>
                    <span style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                      Jami: <strong style={{ color: "#FFFFFF" }}>{stats.total} ta vazifa</strong>
                    </span>
                    <span style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                      Bajarildi: <strong style={{ color: "#4EDEA3" }}>{stats.done} ta</strong>
                    </span>
                    <span style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                      Qoldi: <strong style={{ color: "#E8B3FF" }}>{stats.remaining} ta</strong>
                    </span>
                  </div>
                </div>

                {/* Circular Progress Indicator */}
                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div style={{ textAlign: "right" }}>
                    <div
                      style={{
                        fontFamily: "var(--font-display)",
                        fontSize: "24px",
                        fontWeight: 700,
                        color: "#FFFFFF",
                      }}
                    >
                      {stats.percent}%
                    </div>
                    <div
                      style={{
                        fontSize: "10px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        color: "var(--text-muted)",
                      }}
                    >
                      Samaradorlik
                    </div>
                  </div>
                  <div style={{ position: "relative", width: "58px", height: "58px" }}>
                    <svg width="58" height="58" viewBox="0 0 36 36" style={{ transform: "rotate(-90deg)" }}>
                      <path
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none"
                        stroke="rgba(255,255,255,0.08)"
                        strokeWidth="3.2"
                      />
                      <path
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none"
                        stroke="#C04CFD"
                        strokeWidth="3.2"
                        strokeDasharray={`${stats.percent}, 100`}
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Filter Pills Row */}
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px" }}>
                  {(
                    [
                      { id: "all", label: `Barcha vazifalar (${allTasks.length})` },
                      { id: "today", label: "Tanlangan kun" },
                      { id: "next7", label: "Kelasi 7 kun" },
                      { id: "completed", label: "Bajarilgan" },
                      { id: "overdue", label: "Kechiktirilgan" },
                    ] as { id: TaskFilterMode; label: string }[]
                  ).map((f) => {
                    const active = taskFilter === f.id;
                    return (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => setTaskFilter(f.id)}
                        style={{
                          padding: "6px 14px",
                          borderRadius: "999px",
                          fontSize: "12px",
                          fontWeight: active ? 600 : 500,
                          color: active ? "#FFFFFF" : "var(--text-secondary)",
                          background: active
                            ? "rgba(147, 3, 197, 0.28)"
                            : "rgba(255, 255, 255, 0.035)",
                          border: active
                            ? "1px solid rgba(192, 76, 253, 0.45)"
                            : "1px solid rgba(255, 255, 255, 0.08)",
                          cursor: "pointer",
                        }}
                      >
                        {f.label}
                      </button>
                    );
                  })}
                </div>

                {stats.done > 0 && (
                  <button
                    type="button"
                    onClick={async () => {
                      await backendService.clearCompletedSchedulerTasks();
                      saveLocalTasks(localTasks.filter((t) => !t.completed));
                      await fetchBackendTasks();
                      showToast("Bajarilgan vazifalar tozalandi");
                    }}
                    style={{
                      fontSize: "11.5px",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                    }}
                  >
                    Bajarilganlarni tozalash
                  </button>
                )}
              </div>

              {/* Tasks List */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {displayedTasks.length === 0 ? (
                  <div
                    className="misa-glass-card"
                    style={{
                      padding: "36px 24px",
                      borderRadius: "20px",
                      textAlign: "center",
                      color: "var(--text-secondary)",
                    }}
                  >
                    Ushbu filtr bo'yicha rejalar topilmadi. "+ Yangi reja" tugmasi orqali vazifa qo'shing.
                  </div>
                ) : (
                  displayedTasks.map((task) => {
                    const pBadge = PRIORITY_BADGE[task.priority];
                    return (
                      <div
                        key={task.id}
                        className="misa-glass-card"
                        style={{
                          padding: "16px 20px",
                          borderRadius: "18px",
                          display: "flex",
                          alignItems: "flex-start",
                          gap: "14px",
                          opacity: task.completed ? 0.68 : 1,
                        }}
                      >
                        {/* Custom Checkbox */}
                        <button
                          type="button"
                          onClick={() => handleToggleTaskComplete(task)}
                          aria-label="Holatni o'zgartirish"
                          style={{
                            marginTop: "2px",
                            width: "22px",
                            height: "22px",
                            borderRadius: "7px",
                            background: task.completed
                              ? "rgba(16, 185, 129, 0.22)"
                              : "rgba(255, 255, 255, 0.04)",
                            border: task.completed
                              ? "1.5px solid #10B981"
                              : "1.5px solid rgba(255, 255, 255, 0.25)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "#4EDEA3",
                            flexShrink: 0,
                            cursor: "pointer",
                          }}
                        >
                          {task.completed && <CheckIcon size={13} color="#4EDEA3" />}
                        </button>

                        {/* Task Body */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div
                            style={{
                              display: "flex",
                              flexWrap: "wrap",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: "8px",
                            }}
                          >
                            <h4
                              style={{
                                fontSize: "14px",
                                fontWeight: 600,
                                color: task.completed ? "var(--text-secondary)" : "#FFFFFF",
                                textDecoration: task.completed ? "line-through" : "none",
                              }}
                            >
                              {task.title}
                            </h4>

                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <span
                                style={{
                                  fontSize: "10.5px",
                                  fontWeight: 600,
                                  padding: "2px 8px",
                                  borderRadius: "6px",
                                  background: pBadge.bg,
                                  border: `1px solid ${pBadge.border}`,
                                  color: pBadge.text,
                                }}
                              >
                                {pBadge.label}
                              </span>
                              <span
                                style={{
                                  fontSize: "10.5px",
                                  fontWeight: 500,
                                  padding: "2px 8px",
                                  borderRadius: "6px",
                                  background: "rgba(255, 255, 255, 0.05)",
                                  border: "1px solid rgba(255, 255, 255, 0.1)",
                                  color: "var(--text-secondary)",
                                }}
                              >
                                {task.category}
                              </span>
                            </div>
                          </div>

                          <p
                            style={{
                              fontSize: "12.5px",
                              color: "var(--text-secondary)",
                              marginTop: "4px",
                              lineHeight: 1.45,
                            }}
                          >
                            {task.description}
                          </p>

                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "14px",
                              marginTop: "8px",
                              fontSize: "11px",
                              color: "var(--text-muted)",
                            }}
                          >
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                              <ClockIcon size={11} color="#C04CFD" />
                              <span style={{ color: "#E8B3FF", fontWeight: 500 }}>
                                {task.startTime} - {task.endTime}
                              </span>
                            </span>
                            <span>📅 {task.date}</span>
                          </div>
                        </div>

                        {/* Delete Action */}
                        <button
                          type="button"
                          onClick={() => handleDeleteTask(task)}
                          title="Rejani o'chirish"
                          style={{
                            width: "28px",
                            height: "28px",
                            borderRadius: "8px",
                            background: "rgba(255, 255, 255, 0.03)",
                            color: "var(--text-muted)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            cursor: "pointer",
                          }}
                        >
                          <TrashIcon size={13} color="currentColor" />
                        </button>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Bottom Time Distribution Ribbon */}
              <div
                className="misa-glass-card"
                style={{
                  padding: "16px 20px",
                  borderRadius: "20px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: "12px",
                  }}
                >
                  <span
                    style={{
                      fontSize: "11px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: "var(--text-secondary)",
                    }}
                  >
                    Bugungi vaqt taqsimoti
                  </span>
                  <button
                    type="button"
                    onClick={() => setViewMode("hourly")}
                    style={{ fontSize: "11.5px", color: "#E8B3FF", fontWeight: 600 }}
                  >
                    To'liq soatlik jadval →
                  </button>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                    gap: "8px",
                  }}
                >
                  {allTasks.slice(0, 4).map((t) => (
                    <div
                      key={t.id}
                      style={{
                        padding: "10px 12px",
                        borderRadius: "12px",
                        background: t.completed
                          ? "rgba(16, 185, 129, 0.1)"
                          : "rgba(147, 3, 197, 0.16)",
                        border: t.completed
                          ? "1px solid rgba(16, 185, 129, 0.28)"
                          : "1px solid rgba(192, 76, 253, 0.32)",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "10.5px",
                          fontWeight: 700,
                          color: t.completed ? "#4EDEA3" : "#E8B3FF",
                        }}
                      >
                        {t.startTime}
                      </div>
                      <div
                        style={{
                          fontSize: "12px",
                          fontWeight: 600,
                          color: "#FFFFFF",
                          marginTop: "2px",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {t.title}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* ==============================================================
              VIEW B: SOATLIK (24-HOUR TIMELINE VIEW)
             ============================================================== */}
          {viewMode === "hourly" && (
            <div className="misa-glass-card" style={{ padding: "20px 24px", borderRadius: "22px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <h3 style={{ fontSize: "17px", fontWeight: 700, color: "#FFFFFF" }}>
                    Soatlik Vaqt Jadvali — {formattedNavigatorLabel}
                  </h3>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    Har bir soat bloki uchun vazifalar va fokus vaqti
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(true)}
                  className="misa-btn-violet"
                  style={{
                    padding: "7px 14px",
                    borderRadius: "999px",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                >
                  + Soatga vazifa qo'shish
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"].map(
                  (hour) => {
                    const prefix = hour.slice(0, 2);
                    const slotTasks = allTasks.filter((t) => t.startTime.startsWith(prefix));
                    return (
                      <div
                        key={hour}
                        style={{
                          display: "flex",
                          alignItems: "stretch",
                          gap: "14px",
                          minHeight: "52px",
                        }}
                      >
                        <div
                          style={{
                            width: "54px",
                            fontSize: "12px",
                            fontWeight: 600,
                            color: "var(--text-muted)",
                            paddingTop: "8px",
                            flexShrink: 0,
                          }}
                        >
                          {hour}
                        </div>
                        <div
                          style={{
                            flex: 1,
                            borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                            paddingTop: "6px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                          }}
                        >
                          {slotTasks.length > 0 ? (
                            slotTasks.map((st) => (
                              <div
                                key={st.id}
                                style={{
                                  padding: "10px 14px",
                                  borderRadius: "12px",
                                  background: "rgba(147, 3, 197, 0.2)",
                                  borderLeft: "3px solid #C04CFD",
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                }}
                              >
                                <div>
                                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                                    {st.title}
                                  </div>
                                  <div style={{ fontSize: "11px", color: "#E8B3FF" }}>
                                    {st.startTime} - {st.endTime} • {st.category}
                                  </div>
                                </div>
                                <span style={{ fontSize: "11px", color: st.completed ? "#4EDEA3" : "#FCD34D" }}>
                                  {st.completed ? "✓ Bajarildi" : "Faol"}
                                </span>
                              </div>
                            ))
                          ) : (
                            <div
                              onClick={() => {
                                setFormStartTime(hour);
                                setIsModalOpen(true);
                              }}
                              style={{
                                fontSize: "11.5px",
                                color: "rgba(169, 154, 184, 0.35)",
                                padding: "4px 8px",
                                cursor: "pointer",
                              }}
                            >
                              Bo'sh vaqt bloki — qo'shish uchun bosing
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  }
                )}
              </div>
            </div>
          )}

          {/* ==============================================================
              VIEW C: OYLIK (MONTHLY 7-COLUMN CALENDAR GRID)
             ============================================================== */}
          {viewMode === "monthly" && (
            <div className="misa-glass-card" style={{ padding: "20px 24px", borderRadius: "22px" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "16px",
                }}
              >
                <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#FFFFFF" }}>
                  {UZBEK_MONTHS[selectedDate.getMonth()]} {selectedDate.getFullYear()} — Oylik Taqvim
                </h3>
                <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  Kunni tanlab vazifa qo'shing
                </span>
              </div>

              {/* Weekday Headers */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(7, 1fr)",
                  gap: "8px",
                  marginBottom: "8px",
                }}
              >
                {UZBEK_WEEKDAYS_SHORT.map((w) => (
                  <div
                    key={w}
                    style={{
                      textAlign: "center",
                      fontSize: "11px",
                      fontWeight: 700,
                      textTransform: "uppercase",
                      color: "var(--text-muted)",
                      padding: "4px 0",
                    }}
                  >
                    {w}
                  </div>
                ))}
              </div>

              {/* Calendar Grid Cells */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(7, 1fr)",
                  gap: "8px",
                }}
              >
                {monthlyCells.map((cell, idx) => {
                  if (!cell.day) {
                    return (
                      <div
                        key={`empty_${idx}`}
                        style={{
                          minHeight: "86px",
                          borderRadius: "14px",
                          background: "rgba(255, 255, 255, 0.015)",
                        }}
                      />
                    );
                  }
                  const isToday = cell.dateStr === todayDateStr;
                  const isSelected = cell.dateStr === selectedDateStr;
                  return (
                    <div
                      key={cell.dateStr}
                      onClick={() => {
                        setSelectedDate(new Date(cell.dateStr));
                      }}
                      onDoubleClick={() => {
                        setFormDate(cell.dateStr);
                        setIsModalOpen(true);
                      }}
                      style={{
                        minHeight: "86px",
                        padding: "8px",
                        borderRadius: "14px",
                        background: isSelected
                          ? "rgba(147, 3, 197, 0.24)"
                          : "rgba(2, 6, 14, 0.48)",
                        border: isToday
                          ? "1.5px solid #C04CFD"
                          : isSelected
                          ? "1px solid rgba(192, 76, 253, 0.45)"
                          : "1px solid rgba(255, 255, 255, 0.06)",
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "space-between",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span
                          style={{
                            fontSize: "12.5px",
                            fontWeight: isToday ? 700 : 600,
                            color: isToday ? "#E8B3FF" : "#F5F0FF",
                          }}
                        >
                          {cell.day}
                        </span>
                        {cell.tasks.length > 0 && (
                          <span
                            style={{
                              fontSize: "10px",
                              padding: "1px 6px",
                              borderRadius: "999px",
                              background: "rgba(147, 3, 197, 0.35)",
                              color: "#E8B3FF",
                              fontWeight: 700,
                            }}
                          >
                            {cell.tasks.length}
                          </span>
                        )}
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", gap: "3px", marginTop: "4px" }}>
                        {cell.tasks.slice(0, 2).map((t) => (
                          <div
                            key={t.id}
                            style={{
                              fontSize: "10px",
                              padding: "2px 5px",
                              borderRadius: "5px",
                              background: t.completed
                                ? "rgba(16, 185, 129, 0.2)"
                                : "rgba(147, 3, 197, 0.25)",
                              color: t.completed ? "#4EDEA3" : "#E8B3FF",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {t.title}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ==============================================================
              VIEW D: YILLIK (12-MONTH OVERVIEW GRID)
             ============================================================== */}
          {viewMode === "yearly" && (
            <div className="misa-glass-card" style={{ padding: "20px 24px", borderRadius: "22px" }}>
              <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#FFFFFF", marginBottom: "16px" }}>
                {selectedDate.getFullYear()}-yil — Yillik Strategik Ko'rinish
              </h3>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                  gap: "14px",
                }}
              >
                {UZBEK_MONTHS.map((mName, mIdx) => {
                  const isCurrentMonth = mIdx === new Date().getMonth();
                  const monthPrefix = `${selectedDate.getFullYear()}-${String(mIdx + 1).padStart(2, "0")}`;
                  const monthTasks = allTasks.filter((t) => t.date.startsWith(monthPrefix));
                  return (
                    <div
                      key={mName}
                      onClick={() => {
                        const next = new Date(selectedDate);
                        next.setMonth(mIdx);
                        setSelectedDate(next);
                        setViewMode("monthly");
                      }}
                      style={{
                        padding: "14px 16px",
                        borderRadius: "16px",
                        background: isCurrentMonth
                          ? "rgba(147, 3, 197, 0.2)"
                          : "rgba(2, 6, 14, 0.5)",
                        border: isCurrentMonth
                          ? "1px solid rgba(192, 76, 253, 0.45)"
                          : "1px solid rgba(255, 255, 255, 0.07)",
                        cursor: "pointer",
                        transition: "all 0.18s ease",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>
                          {mName}
                        </span>
                        <span
                          style={{
                            fontSize: "11px",
                            padding: "2px 8px",
                            borderRadius: "999px",
                            background:
                              monthTasks.length > 0
                                ? "rgba(16, 185, 129, 0.18)"
                                : "rgba(255, 255, 255, 0.05)",
                            color: monthTasks.length > 0 ? "#4EDEA3" : "var(--text-muted)",
                          }}
                        >
                          {monthTasks.length} ta reja
                        </span>
                      </div>
                      <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "8px" }}>
                        Oylik kalendarni ochish →
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT 4 COLUMNS: INSIGHTS & MISA AI SUGGESTIONS ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Widget 1: Bugungi ustuvorliklar */}
          <div className="misa-glass-card" style={{ padding: "18px 20px", borderRadius: "20px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ color: "#E8B3FF", fontSize: "15px" }}>★</span>
                <h3 style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>
                  Bugungi ustuvorliklar
                </h3>
              </div>
              <span
                style={{
                  fontSize: "10px",
                  fontWeight: 700,
                  padding: "2px 8px",
                  borderRadius: "999px",
                  background: "rgba(147, 3, 197, 0.22)",
                  color: "#E8B3FF",
                }}
              >
                Muhim
              </span>
            </div>

            {highPriorityTasks.length === 0 ? (
              <p style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
                Barcha yuqori ustuvorlikdagi vazifalar bajarilgan!
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {highPriorityTasks.map((ht) => (
                  <div
                    key={ht.id}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "12px",
                      background: "rgba(147, 3, 197, 0.14)",
                      border: "1px solid rgba(192, 76, 253, 0.28)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "8px",
                    }}
                  >
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          fontSize: "12.5px",
                          fontWeight: 600,
                          color: "#FFFFFF",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {ht.title}
                      </div>
                      <div style={{ fontSize: "11px", color: "#E8B3FF" }}>
                        {ht.startTime} • {ht.category}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleToggleTaskComplete(ht)}
                      style={{
                        padding: "4px 8px",
                        borderRadius: "8px",
                        background: "rgba(16, 185, 129, 0.2)",
                        color: "#4EDEA3",
                        fontSize: "11px",
                        fontWeight: 600,
                      }}
                    >
                      ✓
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Widget 2: Haftalik jarayon */}
          <div className="misa-glass-card" style={{ padding: "18px 20px", borderRadius: "20px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "8px",
              }}
            >
              <span
                style={{
                  fontSize: "11.5px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--text-secondary)",
                }}
              >
                Haftalik jarayon
              </span>
              <span style={{ fontSize: "15px", fontWeight: 700, color: "#4EDEA3" }}>
                {stats.percent}%
              </span>
            </div>

            <div
              style={{
                width: "100%",
                height: "8px",
                borderRadius: "999px",
                background: "rgba(255, 255, 255, 0.08)",
                overflow: "hidden",
                marginBottom: "10px",
              }}
            >
              <div
                style={{
                  width: `${stats.percent}%`,
                  height: "100%",
                  borderRadius: "999px",
                  background: "linear-gradient(90deg, #9303C5 0%, #C04CFD 55%, #4EDEA3 100%)",
                  transition: "width 0.3s ease",
                }}
              />
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "11.5px",
                color: "var(--text-secondary)",
              }}
            >
              <span>{stats.done} ta bajarildi</span>
              <span>{stats.remaining} ta qoldi</span>
            </div>
          </div>

          {/* Widget 3: Misa tavsiyasi (AI Smart Insights) */}
          <div
            className="misa-glass-card-active"
            style={{
              padding: "20px",
              borderRadius: "22px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "10px",
                  background: "linear-gradient(135deg, #9303C5 0%, #500075 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#FFFFFF",
                }}
              >
                <SparklesIcon size={15} color="#FFFFFF" />
              </div>
              <div>
                <h4 style={{ fontSize: "13.5px", fontWeight: 700, color: "#FFFFFF" }}>
                  Misa tavsiyasi
                </h4>
                <span style={{ fontSize: "10.5px", color: "#E8B3FF" }}>
                  Aqlli samaradorlik tahlili
                </span>
              </div>
            </div>

            <p style={{ fontSize: "12.5px", color: "#F5F0FF", lineHeight: 1.55 }}>
              Bugun 14:00 dan 16:00 gacha eng yuqori konsentratsiya vaqtingiz. Murakkab arxitektura va kodlash vazifalarini shu vaqt oralig'ida bajarish tavsiya etiladi.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <button
                type="button"
                onClick={() =>
                  onAskMisa
                    ? onAskMisa("Bugungi vazifalarimni muhimlik darajasi bo'yicha tartiblab ber")
                    : showToast("Vazifalar muhimlik darajasi bo'yicha saralandi ✓")
                }
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "12px",
                  background: "rgba(2, 6, 14, 0.55)",
                  border: "1px solid rgba(232, 179, 255, 0.25)",
                  color: "#E8B3FF",
                  fontSize: "12px",
                  fontWeight: 500,
                  textAlign: "left",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>"Bugungi vazifalarimni tartibla"</span>
                <span>→</span>
              </button>

              <button
                type="button"
                onClick={() =>
                  onAskMisa
                    ? onAskMisa("Asosiy loyihamni 5 ta aniq kichik qadamga ajratib reja tuzib ber")
                    : setIsModalOpen(true)
                }
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "12px",
                  background: "rgba(2, 6, 14, 0.55)",
                  border: "1px solid rgba(232, 179, 255, 0.25)",
                  color: "#E8B3FF",
                  fontSize: "12px",
                  fontWeight: 500,
                  textAlign: "left",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>"Loyihamni kichik vazifalarga ajrat"</span>
                <span>→</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          MODAL: YANGI REJA YARATISH
         ══════════════════════════════════════════════════════════════════ */}
      {isModalOpen && (
        <div
          onClick={() => setIsModalOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.8)",
            backdropFilter: "blur(14px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <form
            onClick={(e) => e.stopPropagation()}
            onSubmit={handleCreatePlan}
            className="misa-ultra-glass"
            style={{
              width: "100%",
              maxWidth: "520px",
              borderRadius: "24px",
              padding: "24px",
              border: "1px solid rgba(232, 179, 255, 0.25)",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "12px",
                    background: "rgba(147, 3, 197, 0.25)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#E8B3FF",
                  }}
                >
                  <SchedulerIcon size={16} color="#E8B3FF" />
                </div>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                    Yangi reja yaratish
                  </h3>
                  <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                    Taqvim va Misa eslatmalar tizimiga vazifa qo'shish
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                style={{ color: "var(--text-secondary)" }}
              >
                <CloseIcon size={15} color="currentColor" />
              </button>
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  color: "var(--text-secondary)",
                  marginBottom: "6px",
                }}
              >
                Vazifa nomi
              </label>
              <input
                type="text"
                required
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                placeholder="Masalan: Misa v9.0 reliz taqdimoti"
                className="misa-glass-input"
                style={{ width: "100%", padding: "10px 14px", borderRadius: "12px", fontSize: "13.5px" }}
              />
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  color: "var(--text-secondary)",
                  marginBottom: "6px",
                }}
              >
                Tavsif va eslatmalar
              </label>
              <textarea
                rows={3}
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
                placeholder="Qo'shimcha tafsilotlar..."
                className="misa-glass-input"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "12px",
                  fontSize: "13px",
                  resize: "none",
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
              <div>
                <label style={{ display: "block", fontSize: "11px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Sana
                </label>
                <input
                  type="date"
                  value={formDate}
                  onChange={(e) => setFormDate(e.target.value)}
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "9px 10px", borderRadius: "10px", fontSize: "12.5px" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Boshlanish
                </label>
                <input
                  type="time"
                  value={formStartTime}
                  onChange={(e) => setFormStartTime(e.target.value)}
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "9px 10px", borderRadius: "10px", fontSize: "12.5px" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Tugash
                </label>
                <input
                  type="time"
                  value={formEndTime}
                  onChange={(e) => setFormEndTime(e.target.value)}
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "9px 10px", borderRadius: "10px", fontSize: "12.5px" }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
              <div>
                <label style={{ display: "block", fontSize: "11px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Muhimlik darajasi
                </label>
                <select
                  value={formPriority}
                  onChange={(e) => setFormPriority(e.target.value as TaskPriority)}
                  className="misa-glass-input"
                  style={{
                    width: "100%",
                    padding: "9px 10px",
                    borderRadius: "10px",
                    fontSize: "12.5px",
                    backgroundColor: "#0B0F1C",
                  }}
                >
                  <option value="high">Yuqori</option>
                  <option value="medium">O'rta</option>
                  <option value="low">Oddiy</option>
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Kategoriya
                </label>
                <select
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value as TaskCategory)}
                  className="misa-glass-input"
                  style={{
                    width: "100%",
                    padding: "9px 10px",
                    borderRadius: "10px",
                    fontSize: "12.5px",
                    backgroundColor: "#0B0F1C",
                  }}
                >
                  <option value="Ishlab chiqish">Ishlab chiqish</option>
                  <option value="Dizayn">Dizayn</option>
                  <option value="Ta'lim">Ta'lim</option>
                  <option value="Boshqaruv">Boshqaruv</option>
                  <option value="Tizim">Tizim</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                style={{
                  padding: "9px 18px",
                  borderRadius: "999px",
                  background: "rgba(255, 255, 255, 0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="misa-btn-violet"
                style={{
                  padding: "9px 22px",
                  borderRadius: "999px",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                {isSubmitting ? "Saqlanmoqda..." : "Rejani saqlash"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
