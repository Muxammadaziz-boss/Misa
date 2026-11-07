// ========== MemoryPage.tsx ==========
// Misa AI v9.0 — Ultra Glass Xotiralar Markazi (Memory Center)

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  DatabaseIcon,
  SparklesIcon,
  CloseIcon,
  TrashIcon,
  RefreshIcon,
  SearchIcon,
  CheckIcon,
  ShieldIcon,
  ClockIcon,
  SettingsIcon,
} from "../components/icons/Icons";
import { NeumorphicCard } from "../components/NeumorphicCard";
import {
  backendService,
  MemoryResponse,
  StructuredMemoryItem,
  MemoryPrivacySettings,
  TraceItem,
  AuditItem,
} from "../services/backendService";

interface MemoryPageProps {
  onNavigateHome: () => void;
}

type MemoryCategory = "Barchasi" | "Shaxsiy" | "Qiziqishlar" | "Loyihalar" | "Afzalliklar" | "Boshqa";
type ViewSection = "cards" | "working" | "episodes" | "observability";

interface EnrichedMemoryCard {
  id: string;
  key: string;
  title: string;
  content: string;
  category: Exclude<MemoryCategory, "Barchasi">;
  pinned: boolean;
  updatedAt: string;
  source: string;
  rawType: "fact" | "profile";
}

const CATEGORY_META: Record<
  Exclude<MemoryCategory, "Barchasi">,
  { bg: string; border: string; text: string }
> = {
  Loyihalar: {
    bg: "rgba(147, 3, 197, 0.2)",
    border: "rgba(192, 76, 253, 0.35)",
    text: "#E8B3FF",
  },
  Shaxsiy: {
    bg: "rgba(56, 189, 248, 0.15)",
    border: "rgba(56, 189, 248, 0.32)",
    text: "#7DD3FC",
  },
  Afzalliklar: {
    bg: "rgba(16, 185, 129, 0.15)",
    border: "rgba(16, 185, 129, 0.32)",
    text: "#6EE7B7",
  },
  Qiziqishlar: {
    bg: "rgba(245, 158, 11, 0.15)",
    border: "rgba(245, 158, 11, 0.32)",
    text: "#FCD34D",
  },
  Boshqa: {
    bg: "rgba(168, 85, 247, 0.15)",
    border: "rgba(168, 85, 247, 0.3)",
    text: "#D8B4FE",
  },
};

function inferCategory(key: string, value: string): Exclude<MemoryCategory, "Barchasi"> {
  const combined = `${key} ${value}`.toLowerCase();
  if (
    combined.includes("loyiha") ||
    combined.includes("project") ||
    combined.includes("misa") ||
    combined.includes("kod") ||
    combined.includes("dastur") ||
    combined.includes("react") ||
    combined.includes("python") ||
    combined.includes("tauri")
  ) {
    return "Loyihalar";
  }
  if (
    combined.includes("ism") ||
    combined.includes("name") ||
    combined.includes("shahar") ||
    combined.includes("kasb") ||
    combined.includes("yosh") ||
    combined.includes("manzil") ||
    combined.includes("til")
  ) {
    return "Shaxsiy";
  }
  if (
    combined.includes("uslub") ||
    combined.includes("afzal") ||
    combined.includes("rejim") ||
    combined.includes("dizayn") ||
    combined.includes("rang") ||
    combined.includes("ovoz")
  ) {
    return "Afzalliklar";
  }
  if (
    combined.includes("qiziq") ||
    combined.includes("hobbi") ||
    combined.includes("kitob") ||
    combined.includes("ilm") ||
    combined.includes("sport") ||
    combined.includes("ai")
  ) {
    return "Qiziqishlar";
  }
  return "Boshqa";
}

export const MemoryPage: React.FC<MemoryPageProps> = () => {
  const [memory, setMemory] = useState<MemoryResponse>({
    ok: true,
    profile: {},
    knowledge: [],
    facts: {},
    conversations: [],
    stats: { facts_count: 0, conversations_count: 0, total_items: 0 },
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeCategory, setActiveCategory] = useState<MemoryCategory>("Barchasi");
  const [activeSection, setActiveSection] = useState<ViewSection>("cards");

  // Local metadata overrides (category, pinned) stored in localStorage
  const [cardMetadata, setCardMetadata] = useState<
    Record<string, { category?: Exclude<MemoryCategory, "Barchasi">; pinned?: boolean; title?: string }>
  >(() => {
    try {
      const raw = localStorage.getItem("misa_memory_card_meta");
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });

  // Add / Edit Modal State
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [editingCard, setEditingCard] = useState<EnrichedMemoryCard | null>(null);
  const [formTitle, setFormTitle] = useState<string>("");
  const [formCategory, setFormCategory] = useState<Exclude<MemoryCategory, "Barchasi">>("Loyihalar");
  const [formContent, setFormContent] = useState<string>("");
  const [formPinned, setFormPinned] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // Delete Confirmation Modal State
  const [cardToDelete, setCardToDelete] = useState<EnrichedMemoryCard | null>(null);
  const [clearAllModalOpen, setClearAllModalOpen] = useState<boolean>(false);
  const [privacyModalOpen, setPrivacyModalOpen] = useState<boolean>(false);
  const [forgetKeyInput, setForgetKeyInput] = useState<string>("");

  // Observability state
  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditItem[]>([]);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  const saveMetadata = (
    next: Record<string, { category?: Exclude<MemoryCategory, "Barchasi">; pinned?: boolean; title?: string }>
  ) => {
    setCardMetadata(next);
    try {
      localStorage.setItem("misa_memory_card_meta", JSON.stringify(next));
    } catch {}
  };

  const fetchMemory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await backendService.getMemory();
      if (data && data.ok) {
        setMemory(data);
      }
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchObservability = useCallback(async () => {
    try {
      const res = await backendService.getAuditTraces();
      if (res.ok) {
        setTraces(res.traces || []);
        setAuditLogs(res.audit_logs || []);
      }
    } catch {}
  }, []);

  useEffect(() => {
    fetchMemory();
  }, [fetchMemory]);

  useEffect(() => {
    if (activeSection === "observability") {
      fetchObservability();
    }
  }, [activeSection, fetchObservability]);

  // Build unified EnrichedMemoryCard list from backend facts + structured facts + profile
  const memoryCards = useMemo<EnrichedMemoryCard[]>(() => {
    const cards: EnrichedMemoryCard[] = [];
    const seenKeys = new Set<string>();

    // 1. Structured facts
    const structuredFacts = Array.isArray(memory.structured_facts) ? memory.structured_facts : [];
    structuredFacts.forEach((item: StructuredMemoryItem) => {
      if (!item || !item.key) return;
      seenKeys.add(item.key);
      const meta = cardMetadata[item.key] || {};
      const cat = meta.category || inferCategory(item.key, String(item.value ?? ""));
      cards.push({
        id: item.id || `fact_${item.key}`,
        key: item.key,
        title: meta.title || item.key.replace(/_/g, " "),
        content: String(item.value ?? ""),
        category: cat,
        pinned: meta.pinned ?? (item.importance ? item.importance >= 0.8 : false),
        updatedAt: item.updated_at ? item.updated_at.slice(0, 16).replace("T", " ") : "Bugun",
        source: item.source === "chat" ? "Suhbatdan olingan" : "Qo'lda kiritilgan",
        rawType: "fact",
      });
    });

    // 2. Legacy / plain facts dictionary
    if (memory.facts && typeof memory.facts === "object" && !Array.isArray(memory.facts)) {
      Object.entries(memory.facts).forEach(([k, v]) => {
        if (!k || seenKeys.has(k)) return;
        seenKeys.add(k);
        const meta = cardMetadata[k] || {};
        const valStr = typeof v === "object" && v !== null ? JSON.stringify(v) : String(v ?? "");
        const cat = meta.category || inferCategory(k, valStr);
        cards.push({
          id: `fact_${k}`,
          key: k,
          title: meta.title || k.replace(/_/g, " "),
          content: valStr,
          category: cat,
          pinned: Boolean(meta.pinned),
          updatedAt: "Faol xotira",
          source: "Foydalanuvchi xotirasi",
          rawType: "fact",
        });
      });
    }

    // 3. Profile items: Ignore default system boilerplate keys and empty values.
    // Real user memories are populated when AI identifies meaningful user preferences/facts.
    const SYSTEM_PROFILE_KEYS = new Set([
      "ovoz_turi",
      "til",
      "qiziqishlar",
      "yoqtirgan_platformalar",
      "yaratilgan",
      "ism",
      "avatar",
      "token",
      "user_id",
      "id",
    ]);

    if (Array.isArray(memory.profile)) {
      memory.profile.forEach((item: StructuredMemoryItem) => {
        if (!item || !item.key || SYSTEM_PROFILE_KEYS.has(item.key.toLowerCase())) return;
        const valStr = String(item.value ?? "").trim();
        if (!valStr || valStr === "[]" || valStr === "{}") return;
        const pKey = `prof_${item.key}`;
        if (seenKeys.has(pKey)) return;
        seenKeys.add(pKey);
        const meta = cardMetadata[pKey] || {};
        cards.push({
          id: item.id || pKey,
          key: item.key,
          title: meta.title || `Profil: ${item.key.replace(/_/g, " ")}`,
          content: valStr,
          category: meta.category || "Shaxsiy",
          pinned: meta.pinned ?? true,
          updatedAt: item.updated_at ? item.updated_at.slice(0, 10) : "Doimiy",
          source: "Foydalanuvchi profili",
          rawType: "profile",
        });
      });
    } else if (memory.profile && typeof memory.profile === "object") {
      Object.entries(memory.profile).forEach(([k, v]) => {
        if (!k || SYSTEM_PROFILE_KEYS.has(k.toLowerCase()) || v === undefined || v === null || v === "") return;
        const rawVal =
          typeof v === "object" && v !== null && "value" in (v as any)
            ? (v as any).value
            : typeof v === "object"
            ? JSON.stringify(v)
            : v;
        const valStr = String(rawVal ?? "").trim();
        if (!valStr || valStr === "[]" || valStr === "{}") return;
        const pKey = `prof_${k}`;
        if (seenKeys.has(pKey)) return;
        seenKeys.add(pKey);
        const meta = cardMetadata[pKey] || {};
        const updatedAt =
          typeof v === "object" && v !== null && "updated_at" in (v as any) && (v as any).updated_at
            ? String((v as any).updated_at).slice(0, 10)
            : "Doimiy";
        cards.push({
          id: pKey,
          key: k,
          title: meta.title || `Profil: ${k.replace(/_/g, " ")}`,
          content: valStr,
          category: meta.category || "Shaxsiy",
          pinned: meta.pinned ?? true,
          updatedAt,
          source: "Foydalanuvchi profili",
          rawType: "profile",
        });
      });
    }

    // Sort pinned first
    return cards.sort((a, b) => Number(b.pinned) - Number(a.pinned));
  }, [memory, cardMetadata]);

  const filteredCards = useMemo(() => {
    return memoryCards.filter((c) => {
      if (activeCategory !== "Barchasi" && c.category !== activeCategory) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          c.title.toLowerCase().includes(q) ||
          c.content.toLowerCase().includes(q) ||
          c.category.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [memoryCards, activeCategory, searchQuery]);

  const privacy: MemoryPrivacySettings = memory.privacy || {
    can_remember: true,
    save_episodes: true,
    allow_profile_learning: true,
  };

  const handleToggleAutoRemember = async () => {
    const nextVal = !privacy.can_remember;
    await backendService.updateMemoryPrivacy({ can_remember: nextVal });
    await fetchMemory();
    showToast(nextVal ? "Xotira avtomatik o'rganish yoqildi" : "Xotira avtomatik o'rganish to'xtatildi");
  };

  const openAddModal = () => {
    setEditingCard(null);
    setFormTitle("");
    setFormCategory("Loyihalar");
    setFormContent("");
    setFormPinned(false);
    setModalOpen(true);
  };

  const openEditModal = (card: EnrichedMemoryCard) => {
    setEditingCard(card);
    setFormTitle(card.title);
    setFormCategory(card.category);
    setFormContent(card.content);
    setFormPinned(card.pinned);
    setModalOpen(true);
  };

  const handleSaveMemoryModal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formContent.trim() || isSaving) return;
    setIsSaving(true);

    try {
      const targetKey = editingCard
        ? editingCard.key
        : formTitle
            .trim()
            .toLowerCase()
            .replace(/\s+/g, "_")
            .replace(/[^a-z0-9_]/g, "") || `xotira_${Date.now()}`;

      if (editingCard) {
        await backendService.updateMemoryItem(
          editingCard.rawType === "profile" ? "profile" : "facts",
          editingCard.key,
          formContent.trim()
        );
      } else {
        await backendService.addFact(targetKey, formContent.trim());
      }

      const metaKey = editingCard?.rawType === "profile" ? `prof_${editingCard.key}` : targetKey;
      saveMetadata({
        ...cardMetadata,
        [metaKey]: {
          title: formTitle.trim(),
          category: formCategory,
          pinned: formPinned,
        },
      });

      await fetchMemory();
      setModalOpen(false);
      showToast(editingCard ? "Xotira muvaffaqiyatli yangilandi ✓" : "Yangi xotira saqlandi ✓");
    } catch {
      showToast("Saqlashda xatolik yuz berdi");
    } finally {
      setIsSaving(false);
    }
  };

  const handleTogglePin = (card: EnrichedMemoryCard) => {
    const metaKey = card.rawType === "profile" ? `prof_${card.key}` : card.key;
    const nextPinned = !card.pinned;
    saveMetadata({
      ...cardMetadata,
      [metaKey]: {
        ...cardMetadata[metaKey],
        title: card.title,
        category: card.category,
        pinned: nextPinned,
      },
    });
    showToast(nextPinned ? "Muhim xotira sifatida belgilandi" : "Muhimlik belgisi olindi");
  };

  const handleConfirmDeleteSingle = async () => {
    if (!cardToDelete) return;
    await backendService.deleteMemoryItem(
      cardToDelete.rawType === "profile" ? "profile" : "facts",
      cardToDelete.key
    );
    setCardToDelete(null);
    await fetchMemory();
    showToast("Xotira o'chirildi");
  };

  const handleConfirmClearAll = async () => {
    await backendService.clearMemoryCategory("all");
    setClearAllModalOpen(false);
    await fetchMemory();
    showToast("Barcha xotiralar tozalandi");
  };

  const handleForgetByKey = async () => {
    if (!forgetKeyInput.trim()) return;
    await backendService.forgetMemoryKey(forgetKeyInput.trim());
    setForgetKeyInput("");
    await fetchMemory();
    showToast("Kalit so'z bo'yicha xotiralar o'chirildi");
  };

  const handleExportMemory = () => {
    try {
      const dataStr = JSON.stringify(
        {
          exported_at: new Date().toISOString(),
          version: "9.4",
          memory_cards: memoryCards,
          facts: memory.facts,
          profile: memory.profile,
          conversations_count: memory.conversations?.length || 0,
        },
        null,
        2
      );
      const blob = new Blob([dataStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `misa_xotira_eksport_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("Xotira JSON fayl sifatida muvaffaqiyatli yuklab olindi");
    } catch {
      showToast("Eksport qilishda xatolik yuz berdi");
    }
  };

  const totalSavedCount = memoryCards.length + (memory.conversations?.length || 0);

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
        gap: "20px",
        overflowY: "auto",
        position: "relative",
        zIndex: 5,
      }}
    >
      {/* Toast Feedback */}
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
            boxShadow: "0 12px 32px rgba(0, 0, 0, 0.8)",
          }}
        >
          {toastMsg}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          1. PAGE HEADER & ACTION BAR
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
        }}
      >
        <div>
          <h1
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "28px",
              fontWeight: 700,
              color: "#F5F0FF",
              letterSpacing: "-0.02em",
              marginBottom: "4px",
            }}
          >
            Xotiralar
          </h1>
          <p style={{ fontSize: "13.5px", color: "var(--text-secondary)" }}>
            Misa eslab qolgan ma'lumotlaringizni boshqaring
          </p>
        </div>

        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" }}>
          {/* Search Input */}
          <div
            className="misa-glass-input"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "9999px",
              width: "250px",
            }}
          >
            <SearchIcon size={14} color="var(--text-secondary)" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Xotiralardan qidirish..."
              style={{
                flex: 1,
                fontSize: "12.5px",
                color: "#F5F0FF",
                background: "transparent",
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{ color: "var(--text-muted)", cursor: "pointer" }}
              >
                ×
              </button>
            )}
          </div>

          {/* Status Indicator Pill */}
          <div
            className="misa-glass-card"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              borderRadius: "9999px",
              fontSize: "12px",
            }}
          >
            <span
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                backgroundColor: privacy.can_remember ? "#10B981" : "#F59E0B",
                boxShadow: privacy.can_remember ? "0 0 8px #10B981" : "none",
              }}
            />
            <span style={{ color: "#F5F0FF", fontWeight: 500 }}>
              {privacy.can_remember ? "Xotira faol" : "Pauzada"}
            </span>
            <span style={{ color: "rgba(255,255,255,0.2)" }}>|</span>
            <span style={{ color: "var(--text-secondary)" }}>{totalSavedCount} / 500 ta saqlangan</span>
          </div>

          {/* Export Button (MISA-ROOT-027) */}
          <button
            type="button"
            onClick={handleExportMemory}
            title="Xotirani JSON fayl sifatida yuklab olish"
            className="misa-glass-card"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "9px 16px",
              borderRadius: "9999px",
              fontSize: "12.5px",
              fontWeight: 600,
              color: "#E8B3FF",
              cursor: "pointer",
            }}
          >
            <span>📥 Eksport</span>
          </button>

          {/* + Yangi xotira Button */}
          <button
            type="button"
            onClick={openAddModal}
            className="misa-btn-violet"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "9px 18px",
              borderRadius: "9999px",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <span style={{ fontSize: "16px", lineHeight: 1 }}>+</span>
            <span>Yangi xotira</span>
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          2. MEMORY OVERVIEW CARDS (3-COLUMN GRID)
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "16px",
        }}
      >
        {/* Overview 1: Total Memories */}
        <NeumorphicCard
          variant="stat"
          icon={<DatabaseIcon size={15} color="#E8B3FF" />}
          title={
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-secondary)",
              }}
            >
              Jami xotiralar
            </span>
          }
          value={`${memoryCards.length} ta`}
          trend={{ direction: "up", label: `+${Math.min(memoryCards.length, 4)} bu hafta` }}
        >
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            Faol foydalanilayotgan shaxsiy va loyiha bilimlari
          </p>
        </NeumorphicCard>

        {/* Overview 2: Categories */}
        <NeumorphicCard
          variant="stat"
          icon={<SparklesIcon size={15} color="#E8B3FF" />}
          title={
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-secondary)",
              }}
            >
              Kategoriyalar
            </span>
          }
          value="5 ta bo'lim"
          trend={{ direction: "neutral", label: "Eng faol: Loyihalar" }}
        >
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            Shaxsiy, Qiziqishlar, Loyihalar, Afzalliklar, Boshqa
          </p>
        </NeumorphicCard>

        {/* Overview 3: Memory Auto-Learn Toggle */}
        <NeumorphicCard
          variant="stat"
          badge={
            <button
              type="button"
              onClick={handleToggleAutoRemember}
              title="Avtomatik eslab qolishni yoqish/o'chirish"
              style={{
                width: "44px",
                height: "24px",
                borderRadius: "999px",
                padding: "3px",
                background: privacy.can_remember
                  ? "rgba(147, 3, 197, 0.45)"
                  : "rgba(255, 255, 255, 0.1)",
                border: privacy.can_remember
                  ? "1px solid rgba(192, 76, 253, 0.6)"
                  : "1px solid rgba(255, 255, 255, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: privacy.can_remember ? "flex-end" : "flex-start",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              <span
                style={{
                  width: "16px",
                  height: "16px",
                  borderRadius: "50%",
                  backgroundColor: privacy.can_remember ? "#E8B3FF" : "#94A3B8",
                  boxShadow: privacy.can_remember ? "0 0 8px #C04CFD" : "none",
                }}
              />
            </button>
          }
          title={
            <span
              style={{
                fontSize: "11px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                color: "var(--text-secondary)",
              }}
            >
              Xotira holati
            </span>
          }
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "24px",
                  fontWeight: 700,
                  color: "#FFFFFF",
                }}
              >
                {privacy.can_remember ? "Yoqilgan" : "To'xtatilgan"}
              </span>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "999px",
                  background: privacy.can_remember
                    ? "rgba(16, 185, 129, 0.15)"
                    : "rgba(245, 158, 11, 0.15)",
                  color: privacy.can_remember ? "#4EDEA3" : "#FCD34D",
                }}
              >
                {privacy.can_remember ? "Avto-sinxron" : "Qo'lda"}
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
              Suhbatlardan avtomatik o'rganish va moslashish
            </p>
          </div>
        </NeumorphicCard>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          3. CATEGORY FILTER TABS & ADVANCED MEMORY VIEW SWITCHER
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
        }}
      >
        {/* Category Filter Pills */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
          {(["Barchasi", "Shaxsiy", "Qiziqishlar", "Loyihalar", "Afzalliklar", "Boshqa"] as MemoryCategory[]).map(
            (cat) => {
              const isActive = activeCategory === cat && activeSection === "cards";
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => {
                    setActiveSection("cards");
                    setActiveCategory(cat);
                  }}
                  style={{
                    padding: "7px 16px",
                    borderRadius: "9999px",
                    fontSize: "12.5px",
                    fontWeight: isActive ? 600 : 500,
                    color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                    background: isActive
                      ? "linear-gradient(135deg, rgba(147, 3, 197, 0.38) 0%, rgba(192, 76, 253, 0.22) 100%)"
                      : "rgba(255, 255, 255, 0.035)",
                    border: isActive
                      ? "1px solid rgba(192, 76, 253, 0.5)"
                      : "1px solid rgba(255, 255, 255, 0.08)",
                    boxShadow: isActive ? "0 0 18px rgba(147, 3, 197, 0.3)" : "none",
                    cursor: "pointer",
                    transition: "all 0.18s ease",
                  }}
                >
                  {cat === "Barchasi" ? `Barchasi (${memoryCards.length})` : cat}
                </button>
              );
            }
          )}
        </div>

        {/* Sub-view switcher for RAM / Episodes / Observability */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "4px",
            padding: "4px",
            borderRadius: "9999px",
            background: "rgba(2, 6, 14, 0.5)",
            border: "1px solid rgba(255, 255, 255, 0.07)",
          }}
        >
          {[
            { id: "cards", label: "Xotira Kartochkalari" },
            { id: "working", label: `Kontekst RAM (${memory.working_memory?.length || 0})` },
            { id: "episodes", label: `Suhbatlar (${memory.conversations?.length || 0})` },
            { id: "observability", label: "Kuzatuv & Izlar" },
          ].map((sec) => {
            const active = activeSection === sec.id;
            return (
              <button
                key={sec.id}
                type="button"
                onClick={() => setActiveSection(sec.id as ViewSection)}
                style={{
                  padding: "5px 12px",
                  borderRadius: "999px",
                  fontSize: "11.5px",
                  fontWeight: active ? 600 : 500,
                  color: active ? "#E8B3FF" : "var(--text-secondary)",
                  background: active ? "rgba(147, 3, 197, 0.25)" : "transparent",
                  cursor: "pointer",
                }}
              >
                {sec.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          4. MAIN CONTENT AREA: 3-COLUMN ULTRA GLASS CARDS OR SUB-VIEWS
         ══════════════════════════════════════════════════════════════════ */}
      {activeSection === "cards" && (
        <>
          {loading ? (
            <div
              className="misa-glass-card"
              style={{
                padding: "48px",
                borderRadius: "24px",
                textAlign: "center",
                color: "var(--text-secondary)",
              }}
            >
              Xotiralar yuklanmoqda...
            </div>
          ) : filteredCards.length === 0 ? (
            <div
              className="misa-glass-card"
              style={{
                padding: "48px 24px",
                borderRadius: "24px",
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <DatabaseIcon size={32} color="#C04CFD" />
              <div style={{ fontSize: "16px", fontWeight: 600, color: "#FFFFFF" }}>
                Hozircha bu bo'limda xotiralar topilmadi
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", maxWidth: "420px" }}>
                Yangi xotira qo'shish uchun yuqoridagi "+ Yangi xotira" tugmasini bosing yoki Misa bilan suhbatda ma'lumot ulashing.
              </p>
              <button
                type="button"
                onClick={openAddModal}
                className="misa-btn-violet"
                style={{
                  marginTop: "6px",
                  padding: "9px 20px",
                  borderRadius: "999px",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
              >
                + Yangi xotira qo'shish
              </button>
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(330px, 1fr))",
                gap: "16px",
              }}
            >
              {filteredCards.map((card) => {
                const catStyle = CATEGORY_META[card.category] || CATEGORY_META.Boshqa;
                return (
                  <NeumorphicCard
                    key={card.id}
                    variant="interactive"
                    selected={card.pinned}
                    style={{
                      padding: "20px",
                      borderRadius: "20px",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                      gap: "14px",
                    }}
                  >
                    <div>
                      {/* Card Top Bar */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          marginBottom: "12px",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              padding: "3px 10px",
                              borderRadius: "999px",
                              fontSize: "11px",
                              fontWeight: 600,
                              background: catStyle.bg,
                              border: `1px solid ${catStyle.border}`,
                              color: catStyle.text,
                            }}
                          >
                            {card.category}
                          </span>
                          {card.pinned && (
                            <span
                              style={{
                                padding: "2px 8px",
                                borderRadius: "999px",
                                fontSize: "10px",
                                fontWeight: 600,
                                background: "rgba(255, 255, 255, 0.08)",
                                color: "#E8B3FF",
                              }}
                            >
                              ★ Muhim
                            </span>
                          )}
                        </div>

                        {/* Actions: Pin, Edit, Delete */}
                        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <button
                            type="button"
                            onClick={() => handleTogglePin(card)}
                            title={card.pinned ? "Muhimlikdan olish" : "Muhim deb belgilash"}
                            style={{
                              width: "28px",
                              height: "28px",
                              borderRadius: "8px",
                              background: "rgba(255, 255, 255, 0.04)",
                              color: card.pinned ? "#E8B3FF" : "var(--text-muted)",
                              fontSize: "13px",
                              cursor: "pointer",
                            }}
                          >
                            ★
                          </button>
                          <button
                            type="button"
                            onClick={() => openEditModal(card)}
                            title="Tahrirlash"
                            style={{
                              width: "28px",
                              height: "28px",
                              borderRadius: "8px",
                              background: "rgba(255, 255, 255, 0.04)",
                              color: "var(--text-secondary)",
                              fontSize: "12px",
                              cursor: "pointer",
                            }}
                          >
                            ✎
                          </button>
                          <button
                            type="button"
                            onClick={() => setCardToDelete(card)}
                            title="O'chirish"
                            style={{
                              width: "28px",
                              height: "28px",
                              borderRadius: "8px",
                              background: "rgba(255, 113, 108, 0.08)",
                              color: "#FF716C",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              cursor: "pointer",
                            }}
                          >
                            <TrashIcon size={13} color="#FF716C" />
                          </button>
                        </div>
                      </div>

                      {/* Card Title & Content */}
                      <h3
                        style={{
                          fontFamily: "var(--font-display)",
                          fontSize: "15px",
                          fontWeight: 600,
                          color: "#FFFFFF",
                          marginBottom: "6px",
                        }}
                      >
                        {card.title}
                      </h3>
                      <p
                        style={{
                          fontSize: "13px",
                          color: "var(--text-secondary)",
                          lineHeight: 1.55,
                          wordBreak: "break-word",
                        }}
                      >
                        {card.content}
                      </p>
                    </div>

                    {/* Card Footer Metadata */}
                    <div
                      style={{
                        paddingTop: "10px",
                        borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: "11px",
                        color: "var(--text-muted)",
                      }}
                    >
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                        <ClockIcon size={11} color="currentColor" />
                        <span>{card.updatedAt}</span>
                      </span>
                      <span>{card.source}</span>
                    </div>
                  </NeumorphicCard>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* SUB-VIEW: WORKING MEMORY (RAM) */}
      {activeSection === "working" && (
        <div className="misa-glass-card" style={{ padding: "24px", borderRadius: "22px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", marginBottom: "12px" }}>
            Joriy Suhbat Konteksti (Working RAM)
          </h3>
          {(!Array.isArray(memory.working_memory) || memory.working_memory.length === 0) ? (
            <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              Joriy sessiyada faol RAM elementlari mavjud emas.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {memory.working_memory.map((w, i) => (
                <div
                  key={i}
                  style={{
                    padding: "12px 16px",
                    borderRadius: "14px",
                    background: "rgba(2, 6, 14, 0.55)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                  }}
                >
                  <div>
                    <strong style={{ color: "#E8B3FF", fontSize: "12.5px" }}>{w.role}:</strong>{" "}
                    <span style={{ color: "#F5F0FF", fontSize: "13px" }}>{w.content}</span>
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{w.timestamp}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SUB-VIEW: EPISODES ARCHIVE */}
      {activeSection === "episodes" && (
        <div className="misa-glass-card" style={{ padding: "24px", borderRadius: "22px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "14px",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
              Suhbatlar Arxivi ({Array.isArray(memory.conversations) ? memory.conversations.length : 0})
            </h3>
            {Array.isArray(memory.conversations) && memory.conversations.length > 0 && (
              <button
                type="button"
                onClick={async () => {
                  await backendService.clearMemoryCategory("episodes");
                  await fetchMemory();
                  showToast("Suhbatlar arxivi tozalandi");
                }}
                style={{
                  padding: "6px 12px",
                  borderRadius: "999px",
                  background: "rgba(255, 113, 108, 0.12)",
                  border: "1px solid rgba(255, 113, 108, 0.3)",
                  color: "#FF716C",
                  fontSize: "11.5px",
                  fontWeight: 600,
                }}
              >
                Arxivni tozalash
              </button>
            )}
          </div>
          {(!Array.isArray(memory.conversations) || memory.conversations.length === 0) ? (
            <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              Saqlangan suhbat epizodlari mavjud emas.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {memory.conversations.slice(-30).reverse().map((ep, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "14px 16px",
                    borderRadius: "16px",
                    background: "rgba(2, 6, 14, 0.55)",
                    border: "1px solid rgba(255, 255, 255, 0.07)",
                  }}
                >
                  <div style={{ fontSize: "12.5px", color: "#E8B3FF", marginBottom: "4px" }}>
                    <strong>Siz:</strong> {ep.user}
                  </div>
                  <div style={{ fontSize: "13px", color: "#F5F0FF" }}>
                    <strong>Misa:</strong> {ep.assistant}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SUB-VIEW: OBSERVABILITY & TRACES */}
      {activeSection === "observability" && (
        <div className="misa-glass-card" style={{ padding: "24px", borderRadius: "22px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "14px",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
              Tizim Kuzatuvi va Izlar ({traces.length} trace / {auditLogs.length} audit)
            </h3>
            <button
              type="button"
              onClick={fetchObservability}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "999px",
                background: "rgba(255, 255, 255, 0.06)",
                fontSize: "12px",
                color: "#F5F0FF",
              }}
            >
              <RefreshIcon size={12} color="currentColor" />
              <span>Yangilash</span>
            </button>
          </div>
          {traces.length === 0 ? (
            <p style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
              Hozircha faol bajarilish izlari (traces) qayd etilmagan.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {traces.slice(0, 15).map((tr) => (
                <div
                  key={tr.trace_id}
                  style={{
                    padding: "12px 16px",
                    borderRadius: "14px",
                    background: "rgba(2, 6, 14, 0.55)",
                    border: "1px solid rgba(255, 255, 255, 0.07)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#F5F0FF" }}>
                      {tr.input_summary || tr.operation}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                      Model: {tr.model_used || "Misa Neural"} • {Math.round(tr.duration_ms ?? tr.total_duration_ms ?? 0)} ms
                    </div>
                  </div>
                  <span
                    style={{
                      fontSize: "11px",
                      padding: "2px 8px",
                      borderRadius: "999px",
                      background:
                        tr.status === "ok"
                          ? "rgba(16, 185, 129, 0.15)"
                          : "rgba(239, 68, 68, 0.15)",
                      color: tr.status === "ok" ? "#4EDEA3" : "#FF716C",
                    }}
                  >
                    {tr.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          5. BOTTOM PRIVACY & MEMORY MANAGEMENT FOOTER CARD
         ══════════════════════════════════════════════════════════════════ */}
      <div
        className="misa-glass-card"
        style={{
          marginTop: "auto",
          padding: "18px 22px",
          borderRadius: "20px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px", flex: 1, minWidth: "260px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "12px",
              background: "rgba(147, 3, 197, 0.18)",
              border: "1px solid rgba(192, 76, 253, 0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#E8B3FF",
              flexShrink: 0,
            }}
          >
            <ShieldIcon size={18} color="#E8B3FF" />
          </div>
          <div>
            <h4 style={{ fontSize: "13.5px", fontWeight: 600, color: "#FFFFFF" }}>
              Xotira boshqaruvi
            </h4>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
              Barcha xotiralar shifrlangan holda saqlanadi va faqat sizning ruxsatingiz bilan Misa tomonidan javoblarni shaxsiylashtirish uchun ishlatiladi.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            onClick={() => setClearAllModalOpen(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "9px 16px",
              borderRadius: "9999px",
              background: "rgba(255, 113, 108, 0.1)",
              border: "1px solid rgba(255, 113, 108, 0.28)",
              color: "#FF716C",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <TrashIcon size={13} color="#FF716C" />
            <span>Barcha xotiralarni tozalash</span>
          </button>

          <button
            type="button"
            onClick={() => setPrivacyModalOpen(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "9px 16px",
              borderRadius: "9999px",
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              color: "#F5F0FF",
              fontSize: "12px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            <SettingsIcon size={13} color="currentColor" />
            <span>Xotira sozlamalari</span>
          </button>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          MODAL 1: ADD / EDIT MEMORY MODAL (#memory-edit-modal)
         ══════════════════════════════════════════════════════════════════ */}
      {modalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.78)",
            backdropFilter: "blur(14px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <form
            onSubmit={handleSaveMemoryModal}
            className="misa-ultra-glass"
            style={{
              width: "100%",
              maxWidth: "520px",
              borderRadius: "24px",
              padding: "24px",
              border: "1px solid rgba(232, 179, 255, 0.25)",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "12px",
                    background: "rgba(147, 3, 197, 0.22)",
                    border: "1px solid rgba(192, 76, 253, 0.35)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#E8B3FF",
                  }}
                >
                  <SparklesIcon size={16} color="#E8B3FF" />
                </div>
                <div>
                  <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                    {editingCard ? "Xotirani tahrirlash" : "Yangi xotira qo'shish"}
                  </h3>
                  <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                    Misa eslab qolgan ma'lumotni o'zgartirish yoki boyitish
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                style={{
                  width: "30px",
                  height: "30px",
                  borderRadius: "50%",
                  background: "rgba(255, 255, 255, 0.05)",
                  color: "var(--text-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <CloseIcon size={14} color="currentColor" />
              </button>
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--text-secondary)",
                  marginBottom: "6px",
                }}
              >
                Xotira sarlavhasi
              </label>
              <input
                type="text"
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                placeholder="Masalan: Misa AI Desktop Loyihasi"
                required
                className="misa-glass-input"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "12px",
                  fontSize: "13.5px",
                }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "var(--text-secondary)",
                    marginBottom: "6px",
                  }}
                >
                  Kategoriya
                </label>
                <select
                  value={formCategory}
                  onChange={(e) =>
                    setFormCategory(e.target.value as Exclude<MemoryCategory, "Barchasi">)
                  }
                  className="misa-glass-input"
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: "12px",
                    fontSize: "13px",
                    backgroundColor: "#0B0F1C",
                  }}
                >
                  <option value="Loyihalar">Loyihalar</option>
                  <option value="Shaxsiy">Shaxsiy</option>
                  <option value="Afzalliklar">Afzalliklar</option>
                  <option value="Qiziqishlar">Qiziqishlar</option>
                  <option value="Boshqa">Boshqa</option>
                </select>
              </div>

              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "11px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    color: "var(--text-secondary)",
                    marginBottom: "6px",
                  }}
                >
                  Muhimlik darajasi
                </label>
                <button
                  type="button"
                  onClick={() => setFormPinned((p) => !p)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: "12px",
                    background: formPinned
                      ? "rgba(147, 3, 197, 0.24)"
                      : "rgba(8, 11, 20, 0.72)",
                    border: formPinned
                      ? "1px solid rgba(192, 76, 253, 0.5)"
                      : "1px solid rgba(255, 255, 255, 0.1)",
                    color: formPinned ? "#E8B3FF" : "var(--text-secondary)",
                    fontSize: "12.5px",
                    fontWeight: 600,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <span>★ Muhim xotira</span>
                  <span>{formPinned ? "Yoqilgan" : "Oddiy"}</span>
                </button>
              </div>
            </div>

            <div>
              <label
                style={{
                  display: "block",
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--text-secondary)",
                  marginBottom: "6px",
                }}
              >
                Xotira matni
              </label>
              <textarea
                rows={4}
                value={formContent}
                onChange={(e) => setFormContent(e.target.value)}
                placeholder="Misa eslab qolishi kerak bo'lgan aniq ma'lumotni kiriting..."
                required
                className="misa-glass-input"
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "12px",
                  fontSize: "13.5px",
                  resize: "none",
                  lineHeight: 1.5,
                }}
              />
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                gap: "10px",
                paddingTop: "8px",
              }}
            >
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                style={{
                  padding: "9px 18px",
                  borderRadius: "999px",
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                  fontWeight: 500,
                }}
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                disabled={isSaving}
                className="misa-btn-violet"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "9px 20px",
                  borderRadius: "999px",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                <CheckIcon size={14} color="#FFFFFF" />
                <span>{isSaving ? "Saqlanmoqda..." : "O'zgarishlarni saqlash"}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          MODAL 2: DELETE SINGLE MEMORY CONFIRMATION
         ══════════════════════════════════════════════════════════════════ */}
      {cardToDelete && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.78)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            className="misa-ultra-glass"
            style={{
              width: "100%",
              maxWidth: "420px",
              borderRadius: "22px",
              padding: "24px",
              border: "1px solid rgba(255, 113, 108, 0.35)",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
              Xotirani o'chirish
            </h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              "{cardToDelete.title}" xotirasini o'chirishni tasdiqlaysizmi? Misa bu ma'lumotni keyingi suhbatlarda ishlatmaydi.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
              <button
                type="button"
                onClick={() => setCardToDelete(null)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "999px",
                  background: "rgba(255, 255, 255, 0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="button"
                onClick={handleConfirmDeleteSingle}
                style={{
                  padding: "8px 18px",
                  borderRadius: "999px",
                  background: "#EF4444",
                  color: "#FFFFFF",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                O'chirish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          MODAL 3: CLEAR ALL MEMORIES CONFIRMATION
         ══════════════════════════════════════════════════════════════════ */}
      {clearAllModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.78)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            className="misa-ultra-glass"
            style={{
              width: "100%",
              maxWidth: "440px",
              borderRadius: "22px",
              padding: "24px",
              border: "1px solid rgba(255, 113, 108, 0.4)",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
              Barcha xotiralarni tozalash
            </h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              Haqiqatan ham barcha saqlangan xotiralar, profil ma'lumotlari va suhbat tarixini butunlay tozalamoqchimisiz?
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
              <button
                type="button"
                onClick={() => setClearAllModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "999px",
                  background: "rgba(255, 255, 255, 0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="button"
                onClick={handleConfirmClearAll}
                style={{
                  padding: "8px 18px",
                  borderRadius: "999px",
                  background: "#EF4444",
                  color: "#FFFFFF",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                Tasdiqlash va Tozalash
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          MODAL 4: MEMORY PRIVACY & FORGET SETTINGS
         ══════════════════════════════════════════════════════════════════ */}
      {privacyModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.78)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            className="misa-ultra-glass"
            style={{
              width: "100%",
              maxWidth: "480px",
              borderRadius: "24px",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                Xotira va Maxfiylik Sozlamalari
              </h3>
              <button
                type="button"
                onClick={() => setPrivacyModalOpen(false)}
                style={{ color: "var(--text-secondary)" }}
              >
                <CloseIcon size={14} color="currentColor" />
              </button>
            </div>

            {[
              {
                key: "can_remember",
                title: "Avtomatik eslab qolish",
                desc: "Suhbat davomida muhim faktlarni xotiraga saqlash",
                val: privacy.can_remember,
              },
              {
                key: "save_episodes",
                title: "Suhbat epizodlarini arxivlash",
                desc: "Oldingi muloqotlar tarixini saqlab borish",
                val: privacy.save_episodes,
              },
              {
                key: "allow_profile_learning",
                title: "Foydalanuvchi profilini boyitish",
                desc: "Qiziqishlar va muloqot uslubiga moslashish",
                val: privacy.allow_profile_learning,
              },
            ].map((item) => (
              <div
                key={item.key}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 14px",
                  borderRadius: "14px",
                  background: "rgba(2, 6, 14, 0.5)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                }}
              >
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                    {item.desc}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    await backendService.updateMemoryPrivacy({ [item.key]: !item.val });
                    await fetchMemory();
                  }}
                  style={{
                    padding: "5px 12px",
                    borderRadius: "999px",
                    background: item.val ? "rgba(16, 185, 129, 0.18)" : "rgba(255, 255, 255, 0.08)",
                    color: item.val ? "#4EDEA3" : "var(--text-secondary)",
                    fontSize: "11.5px",
                    fontWeight: 600,
                  }}
                >
                  {item.val ? "Yoqilgan" : "O'chirilgan"}
                </button>
              </div>
            ))}

            <div>
              <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                Kalit so'z bo'yicha xotirani unutish:
              </label>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  value={forgetKeyInput}
                  onChange={(e) => setForgetKeyInput(e.target.value)}
                  placeholder="Kalit so'zni kiriting..."
                  className="misa-glass-input"
                  style={{ flex: 1, padding: "8px 12px", borderRadius: "10px", fontSize: "13px" }}
                />
                <button
                  type="button"
                  onClick={handleForgetByKey}
                  className="misa-btn-violet"
                  style={{ padding: "8px 14px", borderRadius: "10px", fontSize: "12.5px", fontWeight: 600 }}
                >
                  Unutish
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
