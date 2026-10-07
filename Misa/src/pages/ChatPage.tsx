// ========== ChatPage.tsx ==========
// Misa AI v9.0 — Ultra Glass AI Suhbat va Avtonom Agent Maydoni

import React, { useState, useEffect, useRef } from "react";
import { MisaAperture } from "../components/MisaAperture";
import { MarkdownView } from "../components/MarkdownView";
import {
  MicIcon,
  ArrowUpIcon,
  SparklesIcon,
  VolumeIcon,
  CopyIcon,
  CheckIcon,
  RefreshIcon,
  SearchIcon,
  SettingsIcon,
  CameraIcon,
} from "../components/icons/Icons";
import {
  backendService,
  VoiceState,
  BackendStatus,
  AgentPlanEvent,
} from "../services/backendService";

export interface Message {
  id: string;
  sender: "user" | "misa" | "mikasa";
  text: string;
  timestamp: string;
  feedback?: 1 | -1;
  imageUrl?: string;
  agentPlan?: AgentPlanEvent;
}

export interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
  messages: Message[];
}

interface ChatPageProps {
  userName?: string;
  initialQuery?: string;
  onNavigateHome: () => void;
  onNavigateVoice: () => void;
  onNavigate?: (path: string) => void;
}

type ComposerMode = "chat" | "image";

const saveSessionsToStorage = (sessions: ChatSession[], activeId?: string) => {
  try {
    const raw = JSON.stringify(sessions);
    localStorage.setItem("misa_chat_sessions", raw);
    if (activeId) {
      localStorage.setItem("misa_active_session_id", activeId);
    }
  } catch {}
};

export const ChatPage: React.FC<ChatPageProps> = ({
  userName = "Ustoz",
  initialQuery,
  onNavigateVoice,
  onNavigate,
}) => {
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try {
      const raw = localStorage.getItem("misa_chat_sessions");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    return [{ id: "session_default", title: "Asosiy suhbat", updatedAt: "Hozir", messages: [] }];
  });

  const [activeSessionId, setActiveSessionId] = useState<string>(() => {
    return localStorage.getItem("misa_active_session_id") || "session_default";
  });

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [_voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ status: "connecting" });
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const [sidebarTab, setSidebarTab] = useState<"chats" | "images">("chats");
  const [composerMode, setComposerMode] = useState<ComposerMode>("chat");
  const [sessionSearch, setSessionSearch] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<
    { name: string; content?: string; dataUrl?: string; type?: "text" | "image" }[]
  >([]);
  const [autoSpeak, setAutoSpeak] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem("misa_auto_speak");
      return saved !== null ? saved === "true" : true;
    } catch {
      return true;
    }
  });

  const toggleAutoSpeak = () => {
    setAutoSpeak((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("misa_auto_speak", String(next));
      } catch {}
      return next;
    });
  };

  // Live Multi-Step Agent Execution state
  const [activeAgentPlan, setActiveAgentPlan] = useState<AgentPlanEvent | null>(null);
  const activeAgentPlanRef = useRef<AgentPlanEvent | null>(null);

  const [generatedImages, setGeneratedImages] = useState<
    { url: string; filename: string; created_at: string }[]
  >([]);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialQuerySent = useRef(false);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const formatNow = () =>
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const loadImages = async () => {
    const imgs = await backendService.getGeneratedImages();
    setGeneratedImages(imgs);
  };

  useEffect(() => {
    loadImages();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Subscribe to backend status, voice, and agent plan events
  useEffect(() => {
    const unsubStatus = backendService.onStatusChange((st) => setBackendStatus(st));
    const unsubVoice = backendService.onVoiceStateChange((vs) => setVoiceState(vs));

    const unsubPlan = backendService.onAgentPlan((plan) => {
      activeAgentPlanRef.current = plan;
      setActiveAgentPlan(plan);
    });

    const unsubStep = backendService.onAgentStepUpdate((update) => {
      setActiveAgentPlan((prev) => {
        if (!prev) return prev;
        const updatedSteps = prev.steps.map((s) =>
          s.id === update.step_id
            ? {
                ...s,
                status: update.status,
                result_summary: update.result_summary ?? s.result_summary,
                error: update.error ?? s.error,
              }
            : s
        );
        const nextPlan = { ...prev, steps: updatedSteps };
        activeAgentPlanRef.current = nextPlan;
        return nextPlan;
      });
    });

    const unsubTranscript = backendService.onTranscript((data) => {
      const cleanText = (data.text || "").trim();
      if (!cleanText) return;
      const senderNorm = data.sender === "user" ? "user" : "misa";
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (
          lastMsg &&
          lastMsg.sender === senderNorm &&
          lastMsg.text.trim().toLowerCase() === cleanText.toLowerCase()
        ) {
          return prev;
        }
        return [
          ...prev,
          {
            id: `tr_${Date.now()}_${Math.random()}`,
            sender: senderNorm,
            text: cleanText,
            timestamp: formatNow(),
          },
        ];
      });
    });

    return () => {
      unsubStatus();
      unsubVoice();
      unsubPlan();
      unsubStep();
      unsubTranscript();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
    };
  }, []);

  // Load chat history on mount
  useEffect(() => {
    const raw =
      localStorage.getItem("misa_chat_sessions") ||
      localStorage.getItem("misa_chat_sessions");
    let hasLocalMessages = false;
    if (raw) {
      try {
        const parsed: ChatSession[] = JSON.parse(raw);
        const current = parsed.find((s) => s.id === activeSessionId) || parsed[0];
        if (current && current.messages && current.messages.length > 0) {
          setMessages(current.messages);
          hasLocalMessages = true;
        }
      } catch {}
    }

    if (!hasLocalMessages) {
      backendService.getMemory().then((mem) => {
        if (mem.ok && mem.conversations && mem.conversations.length > 0) {
          const loaded: Message[] = [];
          const recent = mem.conversations.slice(-20);
          recent.forEach((item, idx) => {
            if (item.user) {
              loaded.push({
                id: `hist_u_${idx}`,
                sender: "user",
                text: item.user,
                timestamp: item.timestamp ? item.timestamp.slice(11, 16) : "",
              });
            }
            if (item.assistant) {
              loaded.push({
                id: `hist_a_${idx}`,
                sender: "misa",
                text: item.assistant,
                timestamp: item.timestamp ? item.timestamp.slice(11, 16) : "",
              });
            }
          });
          if (loaded.length > 0) {
            setMessages(loaded);
            setSessions((prev) => {
              const firstTitle =
                loaded.find((m) => m.sender === "user")?.text.slice(0, 32) || "Asosiy suhbat";
              const defSession: ChatSession = {
                id: "session_default",
                title: firstTitle,
                updatedAt: "Avvalgi",
                messages: loaded,
              };
              const next = prev.length <= 1 ? [defSession] : prev;
              saveSessionsToStorage(next, "session_default");
              return next;
            });
          }
        }
      });
    }
  }, []);

  // Sync current messages into active session
  useEffect(() => {
    setSessions((prev) => {
      const idx = prev.findIndex((s) => s.id === activeSessionId);
      if (idx === -1) return prev;

      const currentSession = prev[idx];
      const userMsgs = messages.filter((m) => m.sender === "user");
      const greetingWords = ["salom", "assalom", "assalomu alaykum", "qale", "hello", "hi", "salom misa"];
      const meaningfulMsg = userMsgs.find(
        (m) => !greetingWords.includes(m.text.trim().toLowerCase())
      );
      const chosenMsg = meaningfulMsg || userMsgs[0];
      let newTitle = currentSession.title;
      if (chosenMsg) {
        const textClean = chosenMsg.text.replace(/^[📎\s]+/, "").trim();
        newTitle = textClean.length > 28 ? textClean.slice(0, 28) + "..." : textClean;
      }

      const updatedSession: ChatSession = {
        ...currentSession,
        title: newTitle,
        updatedAt: messages.length > 0 ? formatNow() : currentSession.updatedAt,
        messages,
      };

      const next = [...prev];
      next[idx] = updatedSession;
      saveSessionsToStorage(next);
      return next;
    });
  }, [messages, activeSessionId]);

  const handleCreateNewSession = () => {
    const newId = `session_${Date.now()}`;
    const newSession: ChatSession = {
      id: newId,
      title: "Yangi suhbat",
      updatedAt: "Hozir",
      messages: [],
    };
    setSessions((prev) => {
      const next = [newSession, ...prev];
      saveSessionsToStorage(next, newId);
      return next;
    });
    setActiveSessionId(newId);
    setMessages([]);
  };

  const handleSelectSession = (id: string) => {
    const target = sessions.find((s) => s.id === id);
    if (!target) return;
    setActiveSessionId(id);
    setMessages(target.messages || []);
    saveSessionsToStorage(sessions, id);
  };

  const handleDeleteSession = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== id);
      if (remaining.length === 0) {
        const freshId = `session_${Date.now()}`;
        const fresh: ChatSession = {
          id: freshId,
          title: "Yangi suhbat",
          updatedAt: "Hozir",
          messages: [],
        };
        setActiveSessionId(freshId);
        setMessages([]);
        saveSessionsToStorage([fresh], freshId);
        return [fresh];
      }
      if (id === activeSessionId) {
        const nextActive = remaining[0];
        setActiveSessionId(nextActive.id);
        setMessages(nextActive.messages || []);
        saveSessionsToStorage(remaining, nextActive.id);
      } else {
        saveSessionsToStorage(remaining);
      }
      return remaining;
    });
  };

  // Handle initial query passed from Home or CommandPalette
  useEffect(() => {
    if (initialQuery && !initialQuerySent.current) {
      initialQuerySent.current = true;
      handleSend(initialQuery);
    }
  }, [initialQuery]);

  const handleSend = async (textToSend?: string) => {
    const rawQuery = (textToSend ?? inputText).trim();
    if ((!rawQuery && attachedFiles.length === 0) || isLoading) return;

    if (!textToSend && composerMode === "image") {
      await handleGenerateImage(rawQuery);
      return;
    }

    const attachedImage = attachedFiles.find((f) => f.dataUrl || f.type === "image");
    const imageToSend = attachedImage?.dataUrl;

    const attachmentSuffix =
      attachedFiles.length > 0
        ? "\n\n[Biriktirilgan fayl: " +
          attachedFiles
            .map((f) => `${f.name}${f.content ? `\n${f.content.slice(0, 2000)}` : ""}`)
            .join("\n") +
          "]"
        : "";

    const effectiveQuery = `${rawQuery}${attachmentSuffix}`;

    const userMsg: Message = {
      id: `u_${Date.now()}`,
      sender: "user",
      text: rawQuery || `📎 ${attachedFiles.map((f) => f.name).join(", ")}`,
      timestamp: formatNow(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputText("");
    setAttachedFiles([]);
    setIsLoading(true);
    activeAgentPlanRef.current = null;
    setActiveAgentPlan(null);

    try {
      const response = await backendService.sendMessage(effectiveQuery, { speak: autoSpeak, image: imageToSend });
      const completedPlan = activeAgentPlanRef.current || undefined;
      const aiMsg: Message = {
        id: `a_${Date.now()}`,
        sender: "misa",
        text: response.reply || "Buyruq bajarildi.",
        timestamp: formatNow(),
        agentPlan: completedPlan,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: "misa",
          text: "Xatolik: Misa AI backend serveriga ulanib bo'lmadi.",
          timestamp: formatNow(),
        },
      ]);
    } finally {
      setIsLoading(false);
      activeAgentPlanRef.current = null;
      setActiveAgentPlan(null);
    }
  };

  const handleRegenerateLast = (msgIndex: number) => {
    if (isLoading) return;
    // Find the closest preceding user message
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (messages[i].sender === "user") {
        handleSend(messages[i].text);
        return;
      }
    }
  };

  const handleGenerateImage = async (customPrompt?: string) => {
    const prompt = (customPrompt ?? inputText).trim();
    if (!prompt || isLoading) return;

    const userMsg: Message = {
      id: `u_img_${Date.now()}`,
      sender: "user",
      text: `🎨 Tasvir yaratish: ${prompt}`,
      timestamp: formatNow(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsLoading(true);

    try {
      const res = await backendService.generateImage(prompt);
      if (res.ok && res.image_url) {
        const fullUrl = backendService.getAssetUrl(res.image_url);
        const aiMsg: Message = {
          id: `a_img_${Date.now()}`,
          sender: "misa",
          text: res.message || `'${prompt}' bo'yicha tasvir tayyor:`,
          timestamp: formatNow(),
          imageUrl: fullUrl,
        };
        setMessages((prev) => [...prev, aiMsg]);
        loadImages();
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `err_img_${Date.now()}`,
            sender: "misa",
            text: res.error || "Tasvir yaratishda xatolik yuz berdi.",
            timestamp: formatNow(),
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `err_img_${Date.now()}`,
          sender: "misa",
          text: "Tasvir xizmatiga ulanib bo'lmadi.",
          timestamp: formatNow(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const handleFeedback = async (msgIndex: number, rating: 1 | -1) => {
    const targetMsg = messages[msgIndex];
    if (!targetMsg || targetMsg.sender === "user") return;

    let userQuery = "";
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (messages[i].sender === "user") {
        userQuery = messages[i].text;
        break;
      }
    }

    setMessages((prev) =>
      prev.map((m, idx) => (idx === msgIndex ? { ...m, feedback: rating } : m))
    );

    await backendService.sendFeedback(userQuery, targetMsg.text, rating);
  };

  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    Array.from(files).forEach((file) => {
      if (file.type.startsWith("image/") || /\.(png|jpe?g|webp|gif|bmp)$/i.test(file.name)) {
        const reader = new FileReader();
        reader.onload = () => {
          setAttachedFiles((prev) => [
            ...prev,
            { name: file.name, dataUrl: String(reader.result || ""), type: "image" },
          ]);
        };
        reader.readAsDataURL(file);
      } else if (
        file.size <= 256 * 1024 &&
        (file.type.startsWith("text/") ||
          /\.(txt|md|json|py|ts|tsx|js|csv|html|css|log)$/i.test(file.name))
      ) {
        const reader = new FileReader();
        reader.onload = () => {
          setAttachedFiles((prev) => [
            ...prev,
            { name: file.name, content: String(reader.result || ""), type: "text" },
          ]);
        };
        reader.readAsText(file);
      } else {
        setAttachedFiles((prev) => [...prev, { name: file.name }]);
      }
    });
    e.target.value = "";
  };

  const filteredSessions = sessions.filter((s) =>
    !sessionSearch.trim()
      ? true
      : s.title.toLowerCase().includes(sessionSearch.toLowerCase())
  );

  const cycleComposerMode = () => {
    setComposerMode((prev) => (prev === "chat" ? "image" : "chat"));
  };

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        width: "100%",
        maxWidth: "1440px",
        margin: "0 auto",
        padding: "8px 16px 16px 16px",
        gap: "16px",
        position: "relative",
        zIndex: 5,
        overflow: "hidden",
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: "none" }}
        onChange={handleFileAttach}
      />

      {/* ══════════════════════════════════════════════════════════════════
          LEFT FLOATING GLASS SIDEBAR (CHAT HISTORY & WORKSPACE MODES)
         ══════════════════════════════════════════════════════════════════ */}
      {isSidebarOpen && (
        <aside
          className="misa-ultra-glass"
          style={{
            width: "280px",
            flexShrink: 0,
            borderRadius: "24px",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
            height: "100%",
            overflow: "hidden",
          }}
        >
          {/* Primary CTA: + Yangi suhbat */}
          <button
            type="button"
            onClick={handleCreateNewSession}
            className="misa-btn-violet"
            style={{
              width: "100%",
              padding: "11px 16px",
              borderRadius: "9999px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              fontSize: "13.5px",
              fontWeight: 600,
              cursor: "pointer",
              flexShrink: 0,
            }}
          >
            <span style={{ fontSize: "16px", lineHeight: 1 }}>+</span>
            <span>Yangi suhbat</span>
          </button>

          {/* Quick Workspace Mode Navigation */}
          <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexShrink: 0 }}>
            <button
              type="button"
              onClick={onNavigateVoice}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "9px 12px",
                borderRadius: "14px",
                color: "var(--text-secondary)",
                fontSize: "13px",
                fontWeight: 500,
                cursor: "pointer",
                transition: "all 0.15s ease",
                textAlign: "left",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              <MicIcon size={16} color="#E8B3FF" />
              <span>Ovozli rejim</span>
            </button>

            <button
              type="button"
              onClick={() => setSidebarTab("chats")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "9px 12px",
                borderRadius: "14px",
                background:
                  sidebarTab === "chats" ? "rgba(147, 3, 197, 0.22)" : "transparent",
                border:
                  sidebarTab === "chats"
                    ? "1px solid rgba(192, 76, 253, 0.4)"
                    : "1px solid transparent",
                color: sidebarTab === "chats" ? "#FFFFFF" : "var(--text-secondary)",
                fontSize: "13px",
                fontWeight: sidebarTab === "chats" ? 600 : 500,
                cursor: "pointer",
                transition: "all 0.15s ease",
                textAlign: "left",
              }}
            >
              <SparklesIcon size={16} color="#E8B3FF" />
              <span>AI Suhbat</span>
              <span
                style={{
                  marginLeft: "auto",
                  width: "7px",
                  height: "7px",
                  borderRadius: "50%",
                  backgroundColor: "#4EDEA3",
                  boxShadow: "0 0 8px #4EDEA3",
                }}
              />
            </button>

            <button
              type="button"
              onClick={() => setSidebarTab(sidebarTab === "images" ? "chats" : "images")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "9px 12px",
                borderRadius: "14px",
                background:
                  sidebarTab === "images" ? "rgba(147, 3, 197, 0.22)" : "transparent",
                border:
                  sidebarTab === "images"
                    ? "1px solid rgba(192, 76, 253, 0.4)"
                    : "1px solid transparent",
                color: sidebarTab === "images" ? "#FFFFFF" : "var(--text-secondary)",
                fontSize: "13px",
                fontWeight: sidebarTab === "images" ? 600 : 500,
                cursor: "pointer",
                transition: "all 0.15s ease",
                textAlign: "left",
              }}
            >
              <CameraIcon size={16} color="#E8B3FF" />
              <span>Tasvirlar galereyasi ({generatedImages.length})</span>
            </button>

            {onNavigate && (
              <button
                type="button"
                onClick={() => onNavigate("/account")}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "14px",
                  color: "var(--text-secondary)",
                  fontSize: "13px",
                  fontWeight: 500,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  textAlign: "left",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }}
              >
                <SettingsIcon size={16} color="currentColor" />
                <span>Sozlamalar</span>
              </button>
            )}
          </div>

          <div style={{ height: "1px", background: "rgba(255, 255, 255, 0.08)", flexShrink: 0 }} />

          {/* Search inside sessions */}
          {sidebarTab === "chats" && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "7px 12px",
                borderRadius: "12px",
                background: "rgba(2, 6, 14, 0.45)",
                border: "1px solid rgba(255, 255, 255, 0.07)",
                flexShrink: 0,
              }}
            >
              <SearchIcon size={13} color="var(--text-muted)" />
              <input
                type="text"
                value={sessionSearch}
                onChange={(e) => setSessionSearch(e.target.value)}
                placeholder="Suhbatlardan qidirish..."
                style={{
                  flex: 1,
                  fontSize: "12px",
                  color: "#F5F0FF",
                  background: "transparent",
                }}
              />
            </div>
          )}

          {/* Session List OR Images Gallery */}
          {sidebarTab === "chats" ? (
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                overflowY: "auto",
                paddingRight: "2px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0 6px",
                  marginBottom: "2px",
                }}
              >
                <span
                  style={{
                    fontSize: "10.5px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "var(--text-muted)",
                  }}
                >
                  Bugungi suhbatlar
                </span>
                {messages.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setMessages([])}
                    title="Joriy suhbatni tozalash"
                    style={{
                      fontSize: "10.5px",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                    }}
                  >
                    Tozalash
                  </button>
                )}
              </div>

              {filteredSessions.map((sess) => {
                const isActive = sess.id === activeSessionId;
                return (
                  <div
                    key={sess.id}
                    onClick={() => handleSelectSession(sess.id)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "8px",
                      padding: "10px 12px",
                      borderRadius: "16px",
                      background: isActive
                        ? "rgba(255, 255, 255, 0.08)"
                        : "transparent",
                      border: isActive
                        ? "1px solid rgba(232, 179, 255, 0.2)"
                        : "1px solid transparent",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = "rgba(255, 255, 255, 0.04)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = "transparent";
                      }
                    }}
                  >
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div
                        style={{
                          fontSize: "13px",
                          fontWeight: isActive ? 600 : 500,
                          color: isActive ? "#FFFFFF" : "var(--text-secondary)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {sess.title}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                        {sess.messages?.length || 0} ta xabar • {sess.updatedAt}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => handleDeleteSession(sess.id, e)}
                      title="Suhbatni o'chirish"
                      style={{
                        width: "22px",
                        height: "22px",
                        borderRadius: "6px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "var(--text-muted)",
                        fontSize: "14px",
                        cursor: "pointer",
                      }}
                    >
                      ×
                    </button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
                alignContent: "start",
              }}
            >
              {generatedImages.length === 0 ? (
                <div
                  style={{
                    gridColumn: "1 / -1",
                    textAlign: "center",
                    padding: "28px 12px",
                    fontSize: "12px",
                    color: "var(--text-muted)",
                  }}
                >
                  Hozircha tasvirlar yo'q. Pastdagi rejimni "Tasvir yaratish"ga o'tkazib rasm yarating.
                </div>
              ) : (
                generatedImages.map((img, i) => {
                  const fullUrl = backendService.getAssetUrl(img.url);
                  return (
                    <div
                      key={i}
                      onClick={() => setPreviewImage(fullUrl)}
                      style={{
                        borderRadius: "12px",
                        overflow: "hidden",
                        border: "1px solid rgba(255, 255, 255, 0.1)",
                        cursor: "pointer",
                        aspectRatio: "1 / 1",
                        background: "rgba(0, 0, 0, 0.4)",
                      }}
                    >
                      <img
                        src={fullUrl}
                        alt={img.filename}
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                      />
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Bottom Neural Status Card */}
          <div
            style={{
              padding: "12px",
              borderRadius: "16px",
              background: "rgba(2, 6, 14, 0.55)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "10px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#E8B3FF",
                }}
              >
                <SparklesIcon size={15} color="#E8B3FF" />
              </div>
              <div>
                <div style={{ fontSize: "12px", fontWeight: 600, color: "#FFFFFF" }}>
                  Misa Neural v9.0
                </div>
                <div style={{ fontSize: "10.5px", color: "#4EDEA3" }}>
                  {backendStatus.status === "online" ? "Kontekst oynasi faol" : "Ulanilmoqda..."}
                </div>
              </div>
            </div>
          </div>
        </aside>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          MAIN CHAT WORKSPACE (TIMELINE + FLOATING COMPOSER)
         ══════════════════════════════════════════════════════════════════ */}
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minWidth: 0,
          position: "relative",
        }}
      >
        {/* Top Context Bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "4px 12px 10px 12px",
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            onClick={() => setIsSidebarOpen((p) => !p)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "5px 12px",
              borderRadius: "999px",
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              fontSize: "11.5px",
              color: "var(--text-secondary)",
              cursor: "pointer",
            }}
          >
            <span>{isSidebarOpen ? "◧ Yon panelni yashirish" : "◨ Yon panelni ko'rsatish"}</span>
          </button>

          <span
            style={{
              padding: "4px 14px",
              borderRadius: "999px",
              background: "rgba(255, 255, 255, 0.035)",
              border: "1px solid rgba(255, 255, 255, 0.07)",
              fontSize: "11px",
              fontWeight: 500,
              color: "var(--text-secondary)",
            }}
          >
            Bugun • Misa v9.0 Avtonom Ish Maydoni
          </span>

          <div style={{ width: "110px" }} />
        </div>

        {/* Scrollable Message Stream */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "8px 16px 24px 16px",
            display: "flex",
            flexDirection: "column",
            gap: "20px",
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                gap: "18px",
                padding: "24px",
              }}
            >
              <MisaAperture width="280px" height="132px" state={isLoading ? "thinking" : "idle"} />
              <div>
                <h2
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "22px",
                    fontWeight: 700,
                    color: "#F5F0FF",
                    marginBottom: "6px",
                  }}
                >
                  Salom, {userName}!
                </h2>
                <p style={{ fontSize: "13.5px", color: "var(--text-secondary)", maxWidth: "460px" }}>
                  Misa v9.0 Neural suhbat oynasi tayyor. Savol bering, kod tahlil qiling yoki tizim buyruqlarini ishga tushiring.
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(210px, 260px))",
                  gap: "10px",
                  marginTop: "6px",
                }}
              >
                {[
                  {
                    title: "Kompyuter tahlili",
                    desc: "CPU, RAM va disk holatini tekshirish",
                    q: "Tizim ma'lumotlari",
                  },
                  {
                    title: "Arxitektura va Kod",
                    desc: "Python va TypeScript yechimlari",
                    q: "Python asinxron arxitektura bo'yicha namuna yozib ber",
                  },
                  {
                    title: "Kunlik reja tuzish",
                    desc: "Vazifalarni ustuvorlik bo'yicha saralash",
                    q: "Bugungi ish kunim uchun samarali reja tuzib ber",
                  },
                  {
                    title: "Ob-havo va Valyuta",
                    desc: "Jonli ma'lumotlar va kurslar",
                    q: "Toshkent ob-havosi va dollar kursi qanday?",
                  },
                ].map((card, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSend(card.q)}
                    className="misa-glass-card"
                    style={{
                      padding: "14px 16px",
                      borderRadius: "18px",
                      textAlign: "left",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                    }}
                  >
                    <span style={{ fontSize: "13px", fontWeight: 600, color: "#F5F0FF" }}>
                      {card.title}
                    </span>
                    <span style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                      {card.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div
              style={{
                width: "100%",
                maxWidth: "880px",
                margin: "0 auto",
                display: "flex",
                flexDirection: "column",
                gap: "22px",
              }}
            >
              {messages.map((msg, idx) => {
                const isUser = msg.sender === "user";
                return isUser ? (
                  /* ── USER MESSAGE BUBBLE (Right-Aligned) ── */
                  <div
                    key={msg.id}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-end",
                      gap: "6px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        paddingRight: "6px",
                      }}
                    >
                      <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 500 }}>
                        Siz • {msg.timestamp}
                      </span>
                    </div>
                    <div
                      style={{
                        maxWidth: "76%",
                        padding: "14px 20px",
                        borderRadius: "24px 6px 24px 24px",
                        background: "rgba(24, 13, 36, 0.9)",
                        border: "1px solid rgba(192, 76, 253, 0.42)",
                        boxShadow: "0 10px 30px rgba(147, 3, 197, 0.16)",
                        color: "#F5F0FF",
                        fontSize: "14px",
                        lineHeight: 1.6,
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {msg.text}
                    </div>
                  </div>
                ) : (
                  /* ── MISA AI RESPONSE CARD (Left-Aligned) ── */
                  <div
                    key={msg.id}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "14px",
                    }}
                  >
                    {/* Misa Avatar Badge */}
                    <div
                      style={{
                        width: "36px",
                        height: "36px",
                        borderRadius: "14px",
                        background: "linear-gradient(135deg, #9303C5 0%, #500075 100%)",
                        border: "1px solid rgba(255, 255, 255, 0.22)",
                        boxShadow: "0 0 20px rgba(147, 3, 197, 0.5)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        position: "relative",
                        marginTop: "2px",
                      }}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.4" strokeLinecap="round">
                        <line x1="6" y1="9" x2="6" y2="15" />
                        <line x1="10" y1="5" x2="10" y2="19" />
                        <line x1="14" y1="8" x2="14" y2="16" />
                        <line x1="18" y1="10" x2="18" y2="14" />
                      </svg>
                      <span
                        style={{
                          position: "absolute",
                          bottom: "-2px",
                          right: "-2px",
                          width: "9px",
                          height: "9px",
                          borderRadius: "50%",
                          backgroundColor: "#4EDEA3",
                          border: "2px solid #02060E",
                        }}
                      />
                    </div>

                    <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "8px" }}>
                      {/* Header Row */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "0 4px",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              fontFamily: "var(--font-display)",
                              fontSize: "13px",
                              fontWeight: 700,
                              color: "#FFFFFF",
                            }}
                          >
                            Misa
                          </span>
                          {(() => {
                            const isWarning = msg.text.includes("403") || msg.text.includes("429");
                            const isOffline =
                              msg.text.includes("offline") ||
                              msg.text.includes("mahalliy yordamchi") ||
                              msg.text.includes("Siz — **") ||
                              msg.text.includes("Google Gemini API kaliti xatoligi");

                            const badgeLabel = isWarning
                              ? "v9.0 Ogohlantirish"
                              : isOffline
                              ? "v9.0 Mahalliy"
                              : "v9.0 Neural";
                            const badgeBg = isWarning
                              ? "rgba(255, 171, 0, 0.18)"
                              : isOffline
                              ? "rgba(100, 116, 139, 0.2)"
                              : "rgba(147, 3, 197, 0.2)";
                            const badgeColor = isWarning
                              ? "#FFD166"
                              : isOffline
                              ? "#CBD5E1"
                              : "#E8B3FF";
                            const badgeBorder = isWarning
                              ? "1px solid rgba(255, 171, 0, 0.4)"
                              : isOffline
                              ? "1px solid rgba(148, 163, 184, 0.3)"
                              : "1px solid rgba(192, 76, 253, 0.3)";

                            return (
                              <span
                                style={{
                                  fontSize: "10px",
                                  fontWeight: 600,
                                  padding: "2px 8px",
                                  borderRadius: "999px",
                                  background: badgeBg,
                                  color: badgeColor,
                                  border: badgeBorder,
                                }}
                              >
                                {badgeLabel}
                              </span>
                            );
                          })()}
                          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                            • {msg.timestamp}
                          </span>
                        </div>

                        {/* Message Actions */}
                        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                          <button
                            type="button"
                            onClick={() => handleCopy(msg.id, msg.text)}
                            title="Nusxa olish"
                            style={{
                              padding: "5px 8px",
                              borderRadius: "8px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              fontSize: "11px",
                              color: copiedId === msg.id ? "#4EDEA3" : "var(--text-secondary)",
                              background: "rgba(255, 255, 255, 0.03)",
                              cursor: "pointer",
                            }}
                          >
                            {copiedId === msg.id ? (
                              <>
                                <CheckIcon size={12} color="#4EDEA3" />
                                <span>Nusxalandi</span>
                              </>
                            ) : (
                              <CopyIcon size={12} color="currentColor" />
                            )}
                          </button>

                          <button
                            type="button"
                            onClick={() => backendService.speakText(msg.text)}
                            title="Ovozda o'qish"
                            style={{
                              padding: "5px",
                              borderRadius: "8px",
                              color: "var(--text-secondary)",
                              background: "rgba(255, 255, 255, 0.03)",
                              cursor: "pointer",
                            }}
                          >
                            <VolumeIcon size={12} color="currentColor" />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleRegenerateLast(idx)}
                            title="Qayta generatsiya qilish"
                            style={{
                              padding: "5px",
                              borderRadius: "8px",
                              color: "var(--text-secondary)",
                              background: "rgba(255, 255, 255, 0.03)",
                              cursor: "pointer",
                            }}
                          >
                            <RefreshIcon size={12} color="currentColor" />
                          </button>

                          <button
                            type="button"
                            onClick={() => handleFeedback(idx, 1)}
                            title="Foydali javob"
                            style={{
                              padding: "3px 6px",
                              borderRadius: "6px",
                              fontSize: "11px",
                              background:
                                msg.feedback === 1 ? "rgba(78, 222, 163, 0.2)" : "transparent",
                              color: msg.feedback === 1 ? "#4EDEA3" : "var(--text-muted)",
                              cursor: "pointer",
                            }}
                          >
                            👍
                          </button>
                          <button
                            type="button"
                            onClick={() => handleFeedback(idx, -1)}
                            title="Yaxshilash kerak"
                            style={{
                              padding: "3px 6px",
                              borderRadius: "6px",
                              fontSize: "11px",
                              background:
                                msg.feedback === -1 ? "rgba(255, 113, 108, 0.2)" : "transparent",
                              color: msg.feedback === -1 ? "#FF716C" : "var(--text-muted)",
                              cursor: "pointer",
                            }}
                          >
                            👎
                          </button>
                        </div>
                      </div>

                      {/* Main Ultra Glass Message Body */}
                      <div
                        className="misa-ultra-glass"
                        style={{
                          padding: "20px 24px",
                          borderRadius: "6px 24px 24px 24px",
                          color: "#F5F0FF",
                          fontSize: "14px",
                          lineHeight: 1.65,
                        }}
                      >
                        {msg.agentPlan && msg.agentPlan.steps && msg.agentPlan.steps.length > 0 && (
                          <div
                            style={{
                              marginBottom: "14px",
                              padding: "10px 14px",
                              borderRadius: "14px",
                              background: "rgba(2, 6, 14, 0.55)",
                              border: "1px solid rgba(192, 76, 253, 0.25)",
                            }}
                          >
                            <div
                              style={{
                                fontSize: "11px",
                                fontWeight: 700,
                                color: "#E8B3FF",
                                marginBottom: "6px",
                              }}
                            >
                              Bajarilgan Avtonom Qadamlar ({msg.agentPlan.steps.length})
                            </div>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                              {msg.agentPlan.steps.map((s) => (
                                <span
                                  key={s.id}
                                  style={{
                                    fontSize: "11px",
                                    padding: "3px 9px",
                                    borderRadius: "999px",
                                    background: "rgba(78, 222, 163, 0.12)",
                                    color: "#4EDEA3",
                                    border: "1px solid rgba(78, 222, 163, 0.3)",
                                  }}
                                >
                                  ✓ {s.tool}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <MarkdownView content={msg.text} />

                        {msg.imageUrl && (
                          <div style={{ marginTop: "14px" }}>
                            <img
                              src={msg.imageUrl}
                              alt="Misa AI Generated"
                              onClick={() => setPreviewImage(msg.imageUrl!)}
                              style={{
                                maxWidth: "380px",
                                width: "100%",
                                borderRadius: "16px",
                                border: "1px solid rgba(232, 179, 255, 0.25)",
                                cursor: "pointer",
                              }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Live Thinking / Agent Execution Card */}
              {isLoading && (
                <div style={{ display: "flex", alignItems: "center", gap: "12px", paddingLeft: "8px" }}>
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "50%",
                      background: "rgba(147, 3, 197, 0.22)",
                      border: "1px solid rgba(192, 76, 253, 0.4)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <span
                      style={{
                        width: "8px",
                        height: "8px",
                        borderRadius: "50%",
                        backgroundColor: "#C04CFD",
                        animation: "pulse-slow 1s infinite",
                      }}
                    />
                  </div>
                  <span style={{ fontSize: "13px", color: "#E8B3FF", fontWeight: 500 }}>
                    {activeAgentPlan
                      ? `Avtonom reja bajarilmoqda: ${activeAgentPlan.goal}...`
                      : "Misa javob tayyorlamoqda..."}
                  </span>
                </div>
              )}

              {/* Ready status indicator at bottom of chat */}
              {!isLoading && messages.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingLeft: "10px" }}>
                  <div
                    style={{
                      width: "24px",
                      height: "24px",
                      borderRadius: "50%",
                      background: "rgba(147, 3, 197, 0.16)",
                      border: "1px solid rgba(192, 76, 253, 0.3)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <span
                      style={{
                        width: "6px",
                        height: "6px",
                        borderRadius: "50%",
                        backgroundColor: "#C04CFD",
                      }}
                    />
                  </div>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    Misa keyingi buyruqni qabul qilishga tayyor
                  </span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            BOTTOM FLOATING ULTRA GLASS COMPOSER
           ══════════════════════════════════════════════════════════════════ */}
        <div
          style={{
            padding: "8px 16px 4px 16px",
            flexShrink: 0,
          }}
        >
          <div style={{ maxWidth: "880px", margin: "0 auto" }}>
            {attachedFiles.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "8px" }}>
                {attachedFiles.map((f, i) => (
                  <span
                    key={i}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "4px 10px",
                      borderRadius: "999px",
                      background: "rgba(147, 3, 197, 0.22)",
                      border: "1px solid rgba(192, 76, 253, 0.4)",
                      fontSize: "11.5px",
                      color: "#E8B3FF",
                    }}
                  >
                    {f.type === "image" || f.dataUrl ? "🖼️" : "📎"} {f.name}
                    <button
                      type="button"
                      onClick={() => setAttachedFiles((p) => p.filter((_, idx) => idx !== i))}
                      style={{ color: "#E8B3FF", cursor: "pointer" }}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}

            <div
              className="misa-ultra-glass"
              style={{
                borderRadius: "9999px",
                padding: "8px 10px 8px 14px",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                background: "rgba(24, 13, 36, 0.76)",
                border: "1px solid rgba(232, 179, 255, 0.18)",
                boxShadow: "0 20px 50px rgba(0, 0, 0, 0.85), 0 0 28px rgba(147, 3, 197, 0.14)",
              }}
            >
              {/* Left Tools: File Attach & Mode Switcher Chip */}
              <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  title="Fayl biriktirish"
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--text-secondary)",
                    background: "rgba(255, 255, 255, 0.04)",
                    cursor: "pointer",
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                  </svg>
                </button>

                <button
                  type="button"
                  onClick={cycleComposerMode}
                  title={
                    composerMode === "image"
                      ? "Tasvir yaratish rejimi (Faol) — Oddiy chatga qaytish"
                      : "Tasvir yaratish rejimini yoqish"
                  }
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    padding: "6px 10px",
                    borderRadius: "9999px",
                    background:
                      composerMode === "image"
                        ? "rgba(78, 222, 163, 0.22)"
                        : "rgba(255, 255, 255, 0.04)",
                    border:
                      composerMode === "image"
                        ? "1px solid rgba(78, 222, 163, 0.45)"
                        : "1px solid rgba(255, 255, 255, 0.08)",
                    color: composerMode === "image" ? "#4EDEA3" : "var(--text-secondary)",
                    fontSize: "11.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                    transition: "all 0.15s ease",
                  }}
                >
                  <CameraIcon size={13} color={composerMode === "image" ? "#4EDEA3" : "currentColor"} />
                  <span>Tasvir</span>
                </button>

                <button
                  type="button"
                  onClick={toggleAutoSpeak}
                  title={autoSpeak ? "Ovozli javob: Yoqilgan (O'chirish uchun bosing)" : "Ovozli javob: O'chiq (Yoqish uchun bosing)"}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    padding: "6px 9px",
                    borderRadius: "9999px",
                    background: autoSpeak ? "rgba(147, 3, 197, 0.28)" : "rgba(255, 255, 255, 0.05)",
                    border: autoSpeak ? "1px solid rgba(192, 76, 253, 0.45)" : "1px solid rgba(255, 255, 255, 0.1)",
                    color: autoSpeak ? "#E8B3FF" : "var(--text-muted)",
                    fontSize: "11.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                    transition: "all 0.15s ease",
                  }}
                >
                  <VolumeIcon size={12} color={autoSpeak ? "#E8B3FF" : "currentColor"} />
                  <span>{autoSpeak ? "Ovoz" : "Ovozsiz"}</span>
                </button>
              </div>

              {/* Input Textarea */}
              <textarea
                rows={1}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  composerMode === "image"
                    ? "Yaratiladigan tasvirni ta'riflang..."
                    : "Misa'ga xabar yozing... (Yuborish uchun Enter)"
                }
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  resize: "none",
                  color: "#F5F0FF",
                  fontSize: "13.5px",
                  lineHeight: 1.4,
                  maxHeight: "96px",
                  padding: "6px 4px",
                }}
              />

              {/* Right Controls: Send */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
                <button
                  type="button"
                  onClick={() => handleSend()}
                  disabled={(!inputText.trim() && attachedFiles.length === 0) || isLoading}
                  title="Xabarni yuborish"
                  className="misa-btn-violet"
                  style={{
                    width: "38px",
                    height: "38px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    opacity: (inputText.trim() || attachedFiles.length > 0) && !isLoading ? 1 : 0.45,
                    cursor:
                      (inputText.trim() || attachedFiles.length > 0) && !isLoading
                        ? "pointer"
                        : "default",
                  }}
                >
                  <ArrowUpIcon size={16} color="#FFFFFF" />
                </button>
              </div>
            </div>

            <div
              style={{
                textAlign: "center",
                marginTop: "6px",
                fontSize: "10.5px",
                color: "var(--text-muted)",
              }}
            >
              Misa AI v9.0 xato qilishi mumkin. Muhim ma'lumotlarni tekshirib ko'ring.
            </div>
          </div>
        </div>
      </section>

      {/* Lightbox Image Preview Modal */}
      {previewImage && (
        <div
          onClick={() => setPreviewImage(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(2, 6, 14, 0.85)",
            backdropFilter: "blur(16px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 500,
            padding: "32px",
          }}
        >
          <img
            src={previewImage}
            alt="Preview"
            style={{
              maxWidth: "88vw",
              maxHeight: "84vh",
              borderRadius: "20px",
              border: "1px solid rgba(232, 179, 255, 0.3)",
              boxShadow: "0 24px 60px rgba(0, 0, 0, 0.9)",
            }}
          />
        </div>
      )}
    </div>
  );
};
