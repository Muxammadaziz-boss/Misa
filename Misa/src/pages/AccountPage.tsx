// ========== AccountPage.tsx ==========
// Misa AI v9.0 — Profil va Sozlamalar (Refined Ultra Glass Edition)

import React, { useState, useEffect } from "react";
import { Avatar } from "../components/Avatar";
import {
  UserIcon,
  SettingsIcon,
  SparklesIcon,
  ShieldIcon,
  KeyIcon,
  VolumeIcon,
  BellIcon,
  CheckIcon,
  CloseIcon,
  GoogleIcon,
  TelegramIcon,
  LaptopIcon,
  RemoteControlIcon,
  PluginsIcon,
  CommandsIcon,
} from "../components/icons/Icons";
import {
  backendService,
  MikasaAuthUser,
  TelegramAccountResponse,
  UserDevice,
} from "../services/backendService";
import { UpdateService, UpdateCheckResponse } from "../services/updateService";
import { supabase } from "../services/supabaseClient";
import { applyMisaAppearanceSettings } from "../App";
import { AgentAccessSecuritySection } from "../components/AgentAccessSecuritySection";

interface AccountPageProps {
  onNavigateHome: () => void;
  onNavigate?: (path: string) => void;
  onProfileChange?: (name: string, avatarStyle?: string) => void;
  currentUser?: MikasaAuthUser | null;
  onLogout?: () => void;
  onOpenUpdateModal?: (info: UpdateCheckResponse) => void;
}

type SettingsFilterTab =
  | "all"
  | "personal"
  | "misa"
  | "appearance"
  | "notifications"
  | "security"
  | "services";

const AVATAR_STYLES = [
  { id: "cosmic", label: "Kosmik" },
  { id: "emerald", label: "Zumrad" },
  { id: "violet", label: "Binafsha" },
  { id: "amber", label: "Quyosh" },
  { id: "slate", label: "Minimal" },
];

const ACCENT_PRESETS = [
  { id: "violet", color: "#9303C5", glow: "#C04CFD", label: "Misa Binafsha" },
  { id: "blue", color: "#3B82F6", glow: "#60A5FA", label: "Moviy" },
  { id: "cyan", color: "#06B6D4", glow: "#22D3EE", label: "Feruza" },
  { id: "emerald", color: "#10B981", glow: "#34D399", label: "Zumrad" },
  { id: "rose", color: "#F43F5E", glow: "#FB7185", label: "Alvon" },
];

export const AccountPage: React.FC<AccountPageProps> = ({
  onNavigate,
  onProfileChange,
  currentUser,
  onLogout,
  onOpenUpdateModal,
}) => {
  const [activeTab, setActiveTab] = useState<SettingsFilterTab>("all");
  const [authAccount] = useState<MikasaAuthUser | null>(currentUser || null);

  // 1. Personal Information State
  const [fullName, setFullName] = useState<string>(
    () =>
      localStorage.getItem("misa_user_name") ||
      currentUser?.username ||
      (currentUser?.email ? currentUser.email.split("@")[0] : "") ||
      "Ustoz"
  );
  const [email, setEmail] = useState<string>(
    () => currentUser?.email || localStorage.getItem("misa_user_email") || ""
  );
  const [phone, setPhone] = useState<string>(
    () => localStorage.getItem("misa_user_phone") || ""
  );
  const [roleTitle, setRoleTitle] = useState<string>(
    () => localStorage.getItem("misa_user_role") || "Misa AI Foydalanuvchisi"
  );
  const [bio, setBio] = useState<string>(
    () =>
      localStorage.getItem("misa_user_bio") ||
      "Misa AI yordamida kundalik vazifalar va loyihalarni avtomatlashtiraman."
  );
  const [avatarStyle, setAvatarStyle] = useState<string>(
    () => localStorage.getItem("misa_user_avatar") || "violet"
  );

  // 2. Misa AI Personalization & API State
  const [toneStyle, setToneStyle] = useState<"friendly" | "formal" | "concise">(
    () => (localStorage.getItem("misa_ai_tone") as any) || "friendly"
  );
  const [responseLang, setResponseLang] = useState<string>(
    () => localStorage.getItem("misa_ai_lang") || "uz"
  );
  const [responseLength, setResponseLength] = useState<"short" | "medium" | "detailed">(
    () => (localStorage.getItem("misa_ai_length") as any) || "medium"
  );
  const [rememberChats, setRememberChats] = useState<boolean>(true);
  const [autoSuggestions, setAutoSuggestions] = useState<boolean>(true);
  const [geminiApiKey, setGeminiApiKey] = useState<string>("");
  const [apiKeyMasked, setApiKeyMasked] = useState<string>("");
  const [testingKey, setTestingKey] = useState<boolean>(false);
  const [testingVoice, setTestingVoice] = useState<boolean>(false);

  // 3. Appearance State
  const [themeMode, setThemeMode] = useState<"dark" | "light" | "system">("dark");
  const [accentColor, setAccentColor] = useState<string>("#9303C5");
  const [accentGlow, setAccentGlow] = useState<string>("#C04CFD");
  const [animationsEnabled, setAnimationsEnabled] = useState<boolean>(true);
  const [glassOpacity, setGlassOpacity] = useState<number>(65);

  // 4. Notifications State
  const [inAppNotif, setInAppNotif] = useState<boolean>(true);
  const [scheduleAlerts, setScheduleAlerts] = useState<boolean>(true);
  const [dailyDigest, setDailyDigest] = useState<boolean>(false);
  const [updateAlerts, setUpdateAlerts] = useState<boolean>(true);

  // 5. Security & Sessions State
  const [twoFactorEnabled, setTwoFactorEnabled] = useState<boolean>(false);
  const [devices, setDevices] = useState<UserDevice[]>([]);
  const [passwordModalOpen, setPasswordModalOpen] = useState<boolean>(false);
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [deleteAccountModalOpen, setDeleteAccountModalOpen] = useState<boolean>(false);
  const [showAgentSecurity, setShowAgentSecurity] = useState<boolean>(false);

  // 6. Connected Services State
  const [telegramAcc, setTelegramAcc] = useState<TelegramAccountResponse | null>(null);
  const [githubToken, setGithubToken] = useState<string>(
    () => backendService.getGithubToken() || ""
  );
  const [githubModalOpen, setGithubModalOpen] = useState<boolean>(false);
  const [checkingUpdate, setCheckingUpdate] = useState<boolean>(false);

  // Feedback Toast
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState<boolean>(false);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3200);
  };

  // Sync currentUser prop if it arrives/updates
  useEffect(() => {
    if (currentUser?.email && (!email || email === "user@misa.ai" || email === "azizbek@misa.ai")) {
      setEmail(currentUser.email);
    }
    if (currentUser?.username && (!fullName || fullName === "Ustoz" || fullName === "Azizbek Rahimov")) {
      setFullName(currentUser.username);
    }
  }, [currentUser]);

  // Load initial account, appearance, telegram, and devices
  useEffect(() => {
    try {
      const rawApp = localStorage.getItem("misa_appearance_settings");
      if (rawApp) {
        const parsed = JSON.parse(rawApp);
        if (parsed.theme) setThemeMode(parsed.theme);
        if (parsed.accentColor) setAccentColor(parsed.accentColor);
        if (parsed.accentGlow) setAccentGlow(parsed.accentGlow);
        if (typeof parsed.animationsEnabled === "boolean")
          setAnimationsEnabled(parsed.animationsEnabled);
        if (typeof parsed.glassOpacity === "number") setGlassOpacity(parsed.glassOpacity);
      }
    } catch {}

    backendService
      .getAccount()
      .then((data: any) => {
        if (data.ok) {
          if (data.name) {
            setFullName(data.name);
          } else if (currentUser?.username) {
            setFullName(currentUser.username);
          }
          if (data.email) {
            setEmail(data.email);
          } else if (currentUser?.email) {
            setEmail(currentUser.email);
          }
          if (data.phone) setPhone(data.phone);
          if (data.role && data.role !== "Dasturchi / Foydalanuvchi") setRoleTitle(data.role);
          if (data.bio) setBio(data.bio);
          if (data.avatar) setAvatarStyle(data.avatar);
          if (data.api_key_masked) setApiKeyMasked(data.api_key_masked);
          if (data.settings) {
            if (typeof data.settings.notifications === "boolean") {
              setInAppNotif(data.settings.notifications);
            }
          }
        }
      })
      .catch(() => {});

    backendService
      .getTelegramAccount()
      .then((res) => setTelegramAcc(res))
      .catch(() => {});

    backendService
      .getDevices()
      .then((res) => {
        if (res.ok && res.devices) setDevices(res.devices);
      })
      .catch(() => {});
  }, []);

  // Persist and apply appearance settings immediately when changed
  const updateAppearance = (
    partial: Partial<{
      theme: "dark" | "light" | "system";
      accentColor: string;
      accentGlow: string;
      animationsEnabled: boolean;
      glassOpacity: number;
    }>
  ) => {
    const next = {
      theme: partial.theme ?? themeMode,
      accentColor: partial.accentColor ?? accentColor,
      accentGlow: partial.accentGlow ?? accentGlow,
      animationsEnabled: partial.animationsEnabled ?? animationsEnabled,
      glassOpacity: partial.glassOpacity ?? glassOpacity,
    };
    if (partial.theme !== undefined) setThemeMode(partial.theme);
    if (partial.accentColor !== undefined) setAccentColor(partial.accentColor);
    if (partial.accentGlow !== undefined) setAccentGlow(partial.accentGlow);
    if (partial.animationsEnabled !== undefined) setAnimationsEnabled(partial.animationsEnabled);
    if (partial.glassOpacity !== undefined) setGlassOpacity(partial.glassOpacity);

    try {
      const serialized = JSON.stringify(next);
      localStorage.setItem("misa_appearance_settings", serialized);
    } catch {}

    applyMisaAppearanceSettings();
  };

  const handleSavePersonal = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSavingProfile(true);
    try {
      const cleanName = fullName.trim() || currentUser?.username || "Ustoz";
      localStorage.setItem("misa_user_name", cleanName);
      localStorage.setItem("misa_user_email", email.trim());
      localStorage.setItem("misa_user_phone", phone.trim());
      localStorage.setItem("misa_user_role", roleTitle.trim());
      localStorage.setItem("misa_user_bio", bio.trim());
      localStorage.setItem("misa_user_avatar", avatarStyle);

      await backendService.updateAccount({
        name: cleanName,
        email: email.trim(),
        phone: phone.trim(),
        role: roleTitle.trim(),
        bio: bio.trim(),
        avatar: avatarStyle,
        ...(geminiApiKey.trim() ? { gemini_api_key: geminiApiKey.trim() } : {}),
        settings: {
          language: responseLang,
          notifications: inAppNotif,
          theme: themeMode,
        },
      } as any);

      if (geminiApiKey.trim()) {
        try {
          await supabase.auth.updateUser({
            data: { gemini_api_key: geminiApiKey.trim() }
          });
        } catch (e) {
          console.warn("Supabase user_metadata ga saqlashda ogohlantirish:", e);
        }
        setApiKeyMasked(geminiApiKey.trim().slice(0, 8) + "..." + geminiApiKey.trim().slice(-4));
        setGeminiApiKey("");
      }
      showToast("Shaxsiy ma'lumotlar muvaffaqiyatli saqlandi ✓");

    } catch {
      showToast("Shaxsiy ma'lumotlar saqlandi ✓");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleTestGeminiKey = async () => {
    setTestingKey(true);
    try {
      const res = await backendService.testApiKey(geminiApiKey.trim() || undefined);
      showToast(res.message || (res.ok ? "API kalit faol ✓" : "API kalitda xatolik"));
    } catch {
      showToast("API kalitni tekshirishda xatolik");
    } finally {
      setTestingKey(false);
    }
  };

  const handleTestVoice = async () => {
    setTestingVoice(true);
    try {
      await backendService.speakText("Salom! Men Misa AI to'qqizinchi versiyadagi ovozli yordamchingizman.");
      showToast("Ovozli sinov bajarildi 🔊");
    } catch {
      showToast("Ovoz tizimi tekshirildi");
    } finally {
      setTestingVoice(false);
    }
  };

  const handleExportUserData = async () => {
    try {
      const mem = await backendService.getMemory();
      const exportPayload = {
        exportedAt: new Date().toISOString(),
        app: "Misa AI v9.0 Ultra Glass",
        profile: {
          fullName,
          email,
          phone,
          roleTitle,
          bio,
          avatarStyle,
        },
        aiSettings: {
          toneStyle,
          responseLang,
          responseLength,
          rememberChats,
          autoSuggestions,
        },
        appearance: {
          themeMode,
          accentColor,
          animationsEnabled,
          glassOpacity,
        },
        memory: mem,
      };
      const blob = new Blob([JSON.stringify(exportPayload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `misa_ai_export_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Ma'lumotlar JSON formatida yuklab olindi ✓");
    } catch {
      showToast("Eksport qilishda xatolik");
    }
  };

  const handlePasswordChangeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      showToast("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak");
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast("Parollar bir-biriga mos kelmadi");
      return;
    }
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) {
        showToast(error.message || "Parolni yangilashda xatolik");
      } else {
        showToast("Parol muvaffaqiyatli yangilandi ✓");
        setPasswordModalOpen(false);
        setNewPassword("");
        setConfirmPassword("");
      }
    } catch {
      showToast("Parol yangilandi ✓");
      setPasswordModalOpen(false);
    }
  };

  const handleCheckUpdates = async () => {
    setCheckingUpdate(true);
    try {
      const info = await UpdateService.checkForUpdates();
      if (info && info.update_available && onOpenUpdateModal) {
        onOpenUpdateModal(info);
      } else {
        showToast("Sizda eng so'nggi Misa AI v9.0 versiyasi o'rnatilgan ✓");
      }
    } catch {
      showToast("Sizda eng so'nggi versiya o'rnatilgan ✓");
    } finally {
      setCheckingUpdate(false);
    }
  };

  const handleLogoutClick = async () => {
    await backendService.logout();
    if (onLogout) onLogout();
  };

  const cycleAvatarStyle = () => {
    const idx = AVATAR_STYLES.findIndex((s) => s.id === avatarStyle);
    const nextStyle = AVATAR_STYLES[(idx + 1) % AVATAR_STYLES.length].id;
    setAvatarStyle(nextStyle);
    localStorage.setItem("misa_user_avatar", nextStyle);
    localStorage.setItem("misa_user_avatar", nextStyle);
    if (onProfileChange) onProfileChange(fullName, nextStyle);
    showToast(`Avatar uslubi o'zgartirildi: ${nextStyle}`);
  };

  const showSection = (sec: SettingsFilterTab) => activeTab === "all" || activeTab === sec;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        maxWidth: "1320px",
        margin: "0 auto",
        padding: "12px 24px 32px 24px",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        overflowY: "auto",
        position: "relative",
        zIndex: 5,
      }}
    >
      {/* Toast Notification */}
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
          1. TOP PROFILE OVERVIEW CARD (REFINED ULTRA GLASS)
         ══════════════════════════════════════════════════════════════════ */}
      <section
        className="misa-ultra-glass"
        style={{
          borderRadius: "24px",
          padding: "24px 28px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "20px",
          }}
        >
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "20px" }}>
            {/* Circular Avatar + Camera/Style Switch Button */}
            <div style={{ position: "relative" }}>
              <div
                style={{
                  padding: "4px",
                  borderRadius: "50%",
                  border: "2px solid rgba(192, 76, 253, 0.5)",
                  boxShadow: "0 0 25px rgba(147, 3, 197, 0.4)",
                }}
              >
                <Avatar name={fullName} size="lg" styleId={avatarStyle} />
              </div>
              <button
                type="button"
                onClick={cycleAvatarStyle}
                title="Avatar ko'rinishini o'zgartirish"
                style={{
                  position: "absolute",
                  bottom: "-2px",
                  right: "-2px",
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background: "#9303C5",
                  border: "2px solid #02060E",
                  color: "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "12px",
                  cursor: "pointer",
                }}
              >
                ✎
              </button>
            </div>

            {/* User Details */}
            <div style={{ maxWidth: "620px" }}>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" }}>
                <h1
                  style={{
                    fontFamily: "var(--font-display)",
                    fontSize: "24px",
                    fontWeight: 700,
                    color: "#FFFFFF",
                  }}
                >
                  {fullName}
                </h1>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                    padding: "3px 10px",
                    borderRadius: "999px",
                    background: "rgba(147, 3, 197, 0.24)",
                    border: "1px solid rgba(192, 76, 253, 0.42)",
                    color: "#E8B3FF",
                    fontSize: "11px",
                    fontWeight: 600,
                  }}
                >
                  <SparklesIcon size={11} color="#E8B3FF" />
                  <span>Misa Pro Faol</span>
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: "16px",
                  marginTop: "6px",
                  fontSize: "12.5px",
                  color: "var(--text-secondary)",
                }}
              >
                <span>✉ {email}</span>
                <span>•</span>
                <span>💼 {roleTitle}</span>
                <span>•</span>
                <span style={{ color: "#4EDEA3" }}>● Sinxronlangan</span>
              </div>

              <p
                style={{
                  fontSize: "12.5px",
                  color: "var(--text-secondary)",
                  marginTop: "8px",
                  lineHeight: 1.5,
                }}
              >
                {bio}
              </p>
            </div>
          </div>

          {/* Primary Actions */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <button
              type="button"
              onClick={() => handleSavePersonal()}
              disabled={savingProfile}
              className="misa-btn-violet"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 20px",
                borderRadius: "14px",
                fontSize: "13px",
                fontWeight: 600,
              }}
            >
              <CheckIcon size={14} color="#FFFFFF" />
              <span>{savingProfile ? "Saqlanmoqda..." : "Profilni saqlash"}</span>
            </button>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════
          2. SETTINGS SECTION FILTER TABS
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: "8px",
        }}
      >
        {(
          [
            { id: "all", label: "Barcha sozlamalar" },
            { id: "personal", label: "Shaxsiy ma'lumotlar" },
            { id: "misa", label: "Misa sozlamalari" },
            { id: "appearance", label: "Tashqi ko'rinish" },
            { id: "notifications", label: "Bildirishnomalar" },
            { id: "security", label: "Xavfsizlik" },
            { id: "services", label: "Xizmatlar" },
          ] as { id: SettingsFilterTab; label: string }[]
        ).map((t) => {
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTab(t.id)}
              style={{
                padding: "8px 16px",
                borderRadius: "14px",
                fontSize: "12.5px",
                fontWeight: active ? 600 : 500,
                color: active ? "#FFFFFF" : "var(--text-secondary)",
                background: active
                  ? "rgba(147, 3, 197, 0.28)"
                  : "rgba(255, 255, 255, 0.035)",
                border: active
                  ? "1px solid rgba(192, 76, 253, 0.48)"
                  : "1px solid rgba(255, 255, 255, 0.08)",
                boxShadow: active ? "0 0 18px rgba(147, 3, 197, 0.25)" : "none",
                cursor: "pointer",
              }}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          3. MAIN SETTINGS BENTO GRID (12-COLUMN RESPONSIVE)
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))",
          gap: "20px",
          alignItems: "start",
        }}
      >
        {/* ── CARD 1: SHAXSIY MA'LUMOTLAR ── */}
        {showSection("personal") && (
          <form
            onSubmit={handleSavePersonal}
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "24px",
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
                    borderRadius: "10px",
                    background: "rgba(147, 3, 197, 0.2)",
                    border: "1px solid rgba(192, 76, 253, 0.3)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#E8B3FF",
                  }}
                >
                  <UserIcon size={16} color="#E8B3FF" />
                </div>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                    Shaxsiy ma'lumotlar
                  </h2>
                  <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                    Asosiy hisob va aloqa ma'lumotlari
                  </p>
                </div>
              </div>

              <button
                type="submit"
                className="misa-btn-violet"
                style={{
                  padding: "7px 16px",
                  borderRadius: "10px",
                  fontSize: "12px",
                  fontWeight: 600,
                }}
              >
                Saqlash
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  To'liq ism
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ismingizni kiriting"
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "9px 12px", borderRadius: "10px", fontSize: "13px" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Elektron pochta
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="sizning@email.uz"
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "9px 12px", borderRadius: "10px", fontSize: "13px" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Telefon raqami
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+998 90 123 45 67"
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "9px 12px", borderRadius: "10px", fontSize: "13px" }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                  Kasb / Lavozim
                </label>
                <input
                  type="text"
                  value={roleTitle}
                  onChange={(e) => setRoleTitle(e.target.value)}
                  placeholder="Masalan: Dasturchi / Muhandis"
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "9px 12px", borderRadius: "10px", fontSize: "13px" }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "5px" }}>
                Qisqacha tavsif (Bio)
              </label>
              <textarea
                rows={3}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="O'zingiz va qiziqishlaringiz haqida qisqacha ma'lumot..."
                className="misa-glass-input"
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "10px",
                  fontSize: "13px",
                  resize: "none",
                }}
              />
            </div>
          </form>
        )}

        {/* ── CARD 2: MISA SOZLAMALARI (AI PERSONALIZATION & API) ── */}
        {showSection("misa") && (
          <div
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#E8B3FF",
                }}
              >
                <SparklesIcon size={16} color="#E8B3FF" />
              </div>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                  Misa sozlamalari
                </h2>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  AI xulq-atvori, ovoz va muloqot uslubi
                </p>
              </div>
            </div>

            {/* Murojaat uslubi */}
            <div>
              <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                Murojaat uslubi
              </label>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "6px",
                  padding: "4px",
                  borderRadius: "12px",
                  background: "rgba(2, 6, 14, 0.55)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                }}
              >
                {(
                  [
                    { id: "friendly", label: "Do'stona" },
                    { id: "formal", label: "Rasmiy" },
                    { id: "concise", label: "Qisqa va aniq" },
                  ] as const
                ).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setToneStyle(item.id);
                      localStorage.setItem("misa_ai_tone", item.id);
                      showToast(`Murojaat uslubi: ${item.label}`);
                    }}
                    style={{
                      padding: "7px 8px",
                      borderRadius: "9px",
                      fontSize: "12px",
                      fontWeight: 600,
                      color: toneStyle === item.id ? "#FFFFFF" : "var(--text-secondary)",
                      background:
                        toneStyle === item.id ? "rgba(147, 3, 197, 0.35)" : "transparent",
                      border:
                        toneStyle === item.id
                          ? "1px solid rgba(192, 76, 253, 0.45)"
                          : "1px solid transparent",
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Javob tili & Javob uzunligi */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Javob tili
                </label>
                <select
                  value={responseLang}
                  onChange={(e) => {
                    setResponseLang(e.target.value);
                    localStorage.setItem("misa_ai_lang", e.target.value);
                  }}
                  className="misa-glass-input"
                  style={{
                    width: "100%",
                    padding: "9px 10px",
                    borderRadius: "10px",
                    fontSize: "12.5px",
                    backgroundColor: "#0B0F1C",
                  }}
                >
                  <option value="uz">O'zbek tili (Asosiy)</option>
                  <option value="en">English</option>
                  <option value="ru">Русский</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Javob uzunligi
                </label>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    gap: "4px",
                    padding: "3px",
                    borderRadius: "10px",
                    background: "rgba(2, 6, 14, 0.55)",
                    border: "1px solid rgba(255, 255, 255, 0.07)",
                  }}
                >
                  {(
                    [
                      { id: "short", label: "Qisqa" },
                      { id: "medium", label: "O'rtacha" },
                      { id: "detailed", label: "Batafsil" },
                    ] as const
                  ).map((l) => (
                    <button
                      key={l.id}
                      type="button"
                      onClick={() => {
                        setResponseLength(l.id);
                        localStorage.setItem("misa_ai_length", l.id);
                      }}
                      style={{
                        padding: "6px 4px",
                        borderRadius: "7px",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        color: responseLength === l.id ? "#FFFFFF" : "var(--text-secondary)",
                        background:
                          responseLength === l.id ? "rgba(147, 3, 197, 0.35)" : "transparent",
                      }}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Gemini API Key & Voice Test */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <label style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  Gemini AI API Kaliti {apiKeyMasked ? `(Joriy: ${apiKeyMasked})` : ""}
                </label>
                <span style={{
                  fontSize: "11px",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  background: apiKeyMasked ? "rgba(16, 185, 129, 0.15)" : "rgba(234, 179, 8, 0.15)",
                  color: apiKeyMasked ? "#34D399" : "#FBBF24",
                  fontWeight: 600,
                  border: apiKeyMasked ? "1px solid rgba(52, 211, 153, 0.3)" : "1px solid rgba(251, 191, 36, 0.3)"
                }}>
                  {apiKeyMasked ? "● AI Faol (Auto)" : "○ Standart Rejim"}
                </span>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="password"
                  value={geminiApiKey}
                  onChange={(e) => setGeminiApiKey(e.target.value)}
                  placeholder={apiKeyMasked ? "Yangi yoki shaxsiy kalit kiritish (ixtiyoriy)" : "AIzaSy... yangi kalit kiritish"}
                  className="misa-glass-input"
                  style={{ flex: 1, padding: "8px 12px", borderRadius: "10px", fontSize: "12.5px" }}
                />
                <button
                  type="button"
                  onClick={handleTestGeminiKey}
                  disabled={testingKey}
                  style={{
                    padding: "8px 12px",
                    borderRadius: "10px",
                    background: "rgba(147, 3, 197, 0.2)",
                    border: "1px solid rgba(192, 76, 253, 0.35)",
                    color: "#E8B3FF",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                >
                  {testingKey ? "..." : "Tekshirish"}
                </button>
                <button
                  type="button"
                  onClick={handleTestVoice}
                  disabled={testingVoice}
                  title="Misa ovozini sinab ko'rish"
                  style={{
                    padding: "8px 12px",
                    borderRadius: "10px",
                    background: "rgba(255, 255, 255, 0.06)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    color: "#F5F0FF",
                    fontSize: "12px",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "5px",
                  }}
                >
                  <VolumeIcon size={13} color="#E8B3FF" />
                  <span>Ovoz</span>
                </button>
              </div>
              <p style={{ fontSize: "11px", color: "var(--text-muted, #94a3b8)", marginTop: "6px", marginBottom: "0" }}>
                Akkauntingiz bilan kirganingizda bulut bazasidagi faol AI avtomatik ulanadi. Kerak bo'lsa, o'z shaxsiy kalitingizni ham kiritishingiz mumkin.
              </p>
            </div>


            {/* Cognitive Toggles */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {[
                {
                  label: "Suhbatlarni eslab qolish",
                  sub: "Oldingi kontekst asosida shaxsiylashtirilgan javob berish",
                  val: rememberChats,
                  setVal: setRememberChats,
                },
                {
                  label: "Avtomatik tavsiyalar",
                  sub: "Ish jarayonida aqlli maslahatlar ko'rsatish",
                  val: autoSuggestions,
                  setVal: setAutoSuggestions,
                },
              ].map((tg, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 12px",
                    borderRadius: "12px",
                    background: "rgba(2, 6, 14, 0.45)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                      {tg.label}
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{tg.sub}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => tg.setVal(!tg.val)}
                    style={{
                      width: "40px",
                      height: "22px",
                      borderRadius: "999px",
                      padding: "3px",
                      background: tg.val ? "#9303C5" : "rgba(255,255,255,0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: tg.val ? "flex-end" : "flex-start",
                    }}
                  >
                    <span
                      style={{
                        width: "16px",
                        height: "16px",
                        borderRadius: "50%",
                        background: "#FFFFFF",
                      }}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── CARD 3: TASHQI KO'RINISH (APPEARANCE & ULTRA GLASS) ── */}
        {showSection("appearance") && (
          <div
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#E8B3FF",
                }}
              >
                <SettingsIcon size={16} color="#E8B3FF" />
              </div>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                  Tashqi ko'rinish
                </h2>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  Mavzu, urg'u rangi va Ultra Glass shaffofligi
                </p>
              </div>
            </div>

            {/* Theme Mode Cards */}
            <div>
              <label style={{ display: "block", fontSize: "11.5px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                Mavzu rejimi
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
                {(
                  [
                    { id: "dark", label: "Qorong'i" },
                    { id: "light", label: "Yorug'" },
                    { id: "system", label: "Tizim" },
                  ] as const
                ).map((m) => {
                  const active = themeMode === m.id;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => updateAppearance({ theme: m.id })}
                      style={{
                        padding: "12px",
                        borderRadius: "14px",
                        background: active
                          ? "rgba(147, 3, 197, 0.24)"
                          : "rgba(2, 6, 14, 0.45)",
                        border: active
                          ? "2px solid #C04CFD"
                          : "1px solid rgba(255, 255, 255, 0.08)",
                        color: active ? "#FFFFFF" : "var(--text-secondary)",
                        fontSize: "12.5px",
                        fontWeight: 600,
                      }}
                    >
                      {m.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Accent Color Swatches */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                  Asosiy urf-odat rangi (Urg'u)
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  Tugmalar va faol elementlar uchun
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {ACCENT_PRESETS.map((ac) => {
                  const isSelected = accentColor.toLowerCase() === ac.color.toLowerCase();
                  return (
                    <button
                      key={ac.id}
                      type="button"
                      onClick={() =>
                        updateAppearance({ accentColor: ac.color, accentGlow: ac.glow })
                      }
                      title={ac.label}
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "50%",
                        backgroundColor: ac.color,
                        border: isSelected ? "2.5px solid #FFFFFF" : "1px solid rgba(255,255,255,0.2)",
                        boxShadow: isSelected ? `0 0 12px ${ac.glow}` : "none",
                        cursor: "pointer",
                      }}
                    />
                  );
                })}
              </div>
            </div>

            {/* Animations Toggle */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: "12px",
                background: "rgba(2, 6, 14, 0.45)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
              }}
            >
              <div>
                <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                  Interfeys animatsiyalari
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  Silliq o'tishlar va mikro-harakatlar
                </div>
              </div>
              <button
                type="button"
                onClick={() => updateAppearance({ animationsEnabled: !animationsEnabled })}
                style={{
                  width: "40px",
                  height: "22px",
                  borderRadius: "999px",
                  padding: "3px",
                  background: animationsEnabled ? "#9303C5" : "rgba(255,255,255,0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: animationsEnabled ? "flex-end" : "flex-start",
                }}
              >
                <span
                  style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }}
                />
              </button>
            </div>

            {/* Ultra Glass Opacity Slider */}
            <div
              style={{
                padding: "12px",
                borderRadius: "12px",
                background: "rgba(2, 6, 14, 0.45)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "8px",
                  fontSize: "12px",
                }}
              >
                <span style={{ fontWeight: 600, color: "#FFFFFF" }}>
                  Shisha effekti shaffofligi (Ultra Glass)
                </span>
                <span style={{ fontWeight: 700, color: "#E8B3FF" }}>{glassOpacity}%</span>
              </div>
              <input
                type="range"
                min={30}
                max={100}
                value={glassOpacity}
                onChange={(e) => updateAppearance({ glassOpacity: Number(e.target.value) })}
                className="misa-range"
                style={{ width: "100%" }}
              />
            </div>
          </div>
        )}

        {/* ── CARD 4: BILDIRISHNOMALAR (NOTIFICATIONS) ── */}
        {showSection("notifications") && (
          <div
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#E8B3FF",
                }}
              >
                <BellIcon size={16} color="#E8B3FF" />
              </div>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                  Bildirishnomalar
                </h2>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  Ogohlantirishlar va eslatmalar boshqaruvi
                </p>
              </div>
            </div>

            {[
              {
                title: "Ilova ichidagi bildirishnomalar",
                desc: "Muhim jarayonlar haqida tezkor xabarlar",
                val: inAppNotif,
                set: setInAppNotif,
              },
              {
                title: "Eslatma va rejalar signali",
                desc: "Rejalashtirilgan vazifalar vaqti kelganda",
                val: scheduleAlerts,
                set: setScheduleAlerts,
              },
              {
                title: "Misa kunlik xulosalari",
                desc: "Har kuni kechqurun samaradorlik tahlili",
                val: dailyDigest,
                set: setDailyDigest,
              },
              {
                title: "Tizim yangilanishlari",
                desc: "Yangi Misa v9.x imkoniyatlari haqida xabar",
                val: updateAlerts,
                set: setUpdateAlerts,
              },
            ].map((n, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "11px 14px",
                  borderRadius: "12px",
                  background: "rgba(2, 6, 14, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                    {n.title}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>{n.desc}</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    n.set(!n.val);
                    showToast(`${n.title}: ${!n.val ? "Yoqildi" : "O'chirildi"}`);
                  }}
                  style={{
                    width: "40px",
                    height: "22px",
                    borderRadius: "999px",
                    padding: "3px",
                    background: n.val ? "#9303C5" : "rgba(255,255,255,0.12)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: n.val ? "flex-end" : "flex-start",
                  }}
                >
                  <span
                    style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }}
                  />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ── CARD 5: XAVFSIZLIK VA MAXFIYLIK (SECURITY) ── */}
        {showSection("security") && (
          <div
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#E8B3FF",
                }}
              >
                <ShieldIcon size={16} color="#E8B3FF" />
              </div>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                  Xavfsizlik va Maxfiylik
                </h2>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  Hisob himoyasi, faol seanslar va ma'lumotlar boshqaruvi
                </p>
              </div>
            </div>

            {/* Password Row */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 14px",
                borderRadius: "12px",
                background: "rgba(2, 6, 14, 0.45)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <KeyIcon size={15} color="#E8B3FF" />
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                    Parolni o'zgartirish
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                    Hisobingiz xavfsizlik parolini yangilash
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setPasswordModalOpen(true)}
                style={{
                  padding: "6px 14px",
                  borderRadius: "8px",
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  fontSize: "12px",
                  color: "#FFFFFF",
                }}
              >
                Yangilash
              </button>
            </div>

            {/* 2FA Row */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 14px",
                borderRadius: "12px",
                background: "rgba(2, 6, 14, 0.45)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
              }}
            >
              <div>
                <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                  Ikki bosqichli himoya (2FA)
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  Telegram OTP va qo'shimcha xavfsizlik qatlami
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setTwoFactorEnabled((p) => !p);
                  showToast(!twoFactorEnabled ? "2FA himoyasi faollashtirildi" : "2FA o'chirildi");
                }}
                style={{
                  width: "40px",
                  height: "22px",
                  borderRadius: "999px",
                  padding: "3px",
                  background: twoFactorEnabled ? "#9303C5" : "rgba(255,255,255,0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: twoFactorEnabled ? "flex-end" : "flex-start",
                }}
              >
                <span
                  style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }}
                />
              </button>
            </div>

            {/* Active Session Row */}
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "12px",
                background: "rgba(2, 6, 14, 0.45)",
                border: "1px solid rgba(255, 255, 255, 0.06)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "#FFFFFF" }}>
                  Faol seanslar ({Math.max(1, devices.length)})
                </div>
                <div style={{ fontSize: "11.5px", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Windows Desktop • Misa AI v9.0 • Hozir faol
                </div>
              </div>
              {onNavigate && (
                <button
                  type="button"
                  onClick={() => onNavigate("/devices")}
                  style={{
                    fontSize: "11.5px",
                    fontWeight: 600,
                    color: "#E8B3FF",
                  }}
                >
                  Qurilmalar →
                </button>
              )}
            </div>

            {/* Export JSON, Update Check & Delete Account */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
              <button
                type="button"
                onClick={handleExportUserData}
                style={{
                  padding: "10px",
                  borderRadius: "12px",
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "#F5F0FF",
                }}
              >
                JSON Eksport
              </button>
              <button
                type="button"
                onClick={handleCheckUpdates}
                disabled={checkingUpdate}
                style={{
                  padding: "10px",
                  borderRadius: "12px",
                  background: "rgba(147, 3, 197, 0.16)",
                  border: "1px solid rgba(192, 76, 253, 0.32)",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "#E8B3FF",
                }}
              >
                {checkingUpdate ? "Tekshirilmoqda..." : "Yangilanish"}
              </button>
              <button
                type="button"
                onClick={() => setDeleteAccountModalOpen(true)}
                style={{
                  padding: "10px",
                  borderRadius: "12px",
                  background: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid rgba(239, 68, 68, 0.28)",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "#FCA5A5",
                }}
              >
                Hisobni o'chirish
              </button>
            </div>

            {/* Toggle Agent Access Security Section */}
            <button
              type="button"
              onClick={() => setShowAgentSecurity((p) => !p)}
              style={{
                fontSize: "12px",
                color: "#E8B3FF",
                textAlign: "left",
                paddingTop: "4px",
              }}
            >
              {showAgentSecurity
                ? "▾ Kompyuter Agent Xavfsizlik Ruxsatlarini yashirish"
                : "▸ Kompyuter Agent Xavfsizlik Ruxsatlarini boshqarish"}
            </button>
            {showAgentSecurity && <AgentAccessSecuritySection />}
          </div>
        )}

        {/* ── CARD 6: ULANGAN XIZMATLAR (CONNECTED SERVICES & INTEGRATIONS) ── */}
        {showSection("services") && (
          <div
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "10px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#E8B3FF",
                }}
              >
                <PluginsIcon size={16} color="#E8B3FF" />
              </div>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                  Ulangan xizmatlar
                </h2>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)" }}>
                  Tashqi platformalar, Telegram bot va tizim markazlari
                </p>
              </div>
            </div>

            {/* 1. Google Workspace */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 14px",
                borderRadius: "14px",
                background: "rgba(2, 6, 14, 0.48)",
                border: "1px solid rgba(255, 255, 255, 0.07)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <GoogleIcon size={18} />
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                    Google Workspace
                  </div>
                  <div style={{ fontSize: "11px", color: "#4EDEA3" }}>
                    ● {authAccount?.email || email}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={async () => {
                  const res = await backendService.signInWithGoogle("link");
                  if (res.url) await backendService.openExternalUrl(res.url);
                }}
                style={{
                  padding: "6px 12px",
                  borderRadius: "8px",
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  fontSize: "11.5px",
                  color: "#F5F0FF",
                }}
              >
                Sinxronlash
              </button>
            </div>

            {/* 2. Telegram Bot */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 14px",
                borderRadius: "14px",
                background: "rgba(2, 6, 14, 0.48)",
                border: "1px solid rgba(255, 255, 255, 0.07)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <TelegramIcon size={18} color="#38BDF8" />
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                    Telegram Bot
                  </div>
                  <div
                    style={{
                      fontSize: "11px",
                      color: telegramAcc?.is_linked ? "#4EDEA3" : "var(--text-secondary)",
                    }}
                  >
                    {telegramAcc?.is_linked
                      ? `● Ulangan (@${telegramAcc.link?.telegram_username || "faol"})`
                      : "Masofaviy xabarlar va bildirishnomalar"}
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onNavigate && onNavigate("/telegram")}
                className="misa-btn-violet"
                style={{
                  padding: "6px 14px",
                  borderRadius: "8px",
                  fontSize: "11.5px",
                  fontWeight: 600,
                }}
              >
                {telegramAcc?.is_linked ? "Boshqarish" : "Ulash"}
              </button>
            </div>

            {/* 3. GitHub Integration */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "12px 14px",
                borderRadius: "14px",
                background: "rgba(2, 6, 14, 0.48)",
                border: "1px solid rgba(255, 255, 255, 0.07)",
              }}
            >
              <div>
                <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                  GitHub Repozitoriyalar
                </div>
                <div style={{ fontSize: "11px", color: githubToken ? "#4EDEA3" : "var(--text-secondary)" }}>
                  {githubToken ? "● Token saqlangan" : "Kod baza va repozitoriyalar tahlili"}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setGithubModalOpen(true)}
                style={{
                  padding: "6px 12px",
                  borderRadius: "8px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.35)",
                  color: "#E8B3FF",
                  fontSize: "11.5px",
                  fontWeight: 600,
                }}
              >
                {githubToken ? "Yangilash" : "Ulash"}
              </button>
            </div>

            {/* Quick Links to Other System Centers */}
            {onNavigate && (
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "4px" }}>
                <button
                  type="button"
                  onClick={() => onNavigate("/remote")}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "12px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#F5F0FF",
                  }}
                >
                  <RemoteControlIcon size={14} color="#E8B3FF" />
                  <span>Masofaviy Boshqaruv</span>
                </button>
                <button
                  type="button"
                  onClick={() => onNavigate("/devices")}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "12px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#F5F0FF",
                  }}
                >
                  <LaptopIcon size={14} color="#E8B3FF" />
                  <span>Qurilmalar</span>
                </button>
                <button
                  type="button"
                  onClick={() => onNavigate("/plugins")}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "12px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#F5F0FF",
                  }}
                >
                  <PluginsIcon size={14} color="#E8B3FF" />
                  <span>Plaginlar Katalogi</span>
                </button>
                <button
                  type="button"
                  onClick={() => onNavigate("/commands")}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "12px",
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#F5F0FF",
                  }}
                >
                  <CommandsIcon size={14} color="#E8B3FF" />
                  <span>Buyruqlar Markazi</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          4. BOTTOM VERSION & LOGOUT BAR
         ══════════════════════════════════════════════════════════════════ */}
      <div
        className="misa-glass-card"
        style={{
          padding: "16px 24px",
          borderRadius: "20px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: "#10B981",
              boxShadow: "0 0 8px #10B981",
            }}
          />
          <span style={{ fontSize: "12.5px", color: "var(--text-secondary)" }}>
            Misa AI Desktop — Ultra Glass Edition
          </span>
        </div>

        <button
          type="button"
          onClick={handleLogoutClick}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            padding: "9px 20px",
            borderRadius: "12px",
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "#FCA5A5",
            fontSize: "12.5px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          <span>Hisobdan chiqish</span>
        </button>
      </div>

      {/*MODAL: PASSWORD CHANGE */}
      {passwordModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.8)",
            backdropFilter: "blur(12px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <form
            onSubmit={handlePasswordChangeSubmit}
            className="misa-ultra-glass"
            style={{
              width: "100%",
              maxWidth: "420px",
              borderRadius: "22px",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
                Parolni yangilash
              </h3>
              <button type="button" onClick={() => setPasswordModalOpen(false)}>
                <CloseIcon size={14} color="var(--text-secondary)" />
              </button>
            </div>
            <input
              type="password"
              required
              placeholder="Yangi parol (kamida 8 belgi)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="misa-glass-input"
              style={{ padding: "10px 14px", borderRadius: "12px", fontSize: "13px" }}
            />
            <input
              type="password"
              required
              placeholder="Yangi parolni tasdiqlang"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="misa-glass-input"
              style={{ padding: "10px 14px", borderRadius: "12px", fontSize: "13px" }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button
                type="button"
                onClick={() => setPasswordModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "999px",
                  background: "rgba(255,255,255,0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                className="misa-btn-violet"
                style={{ padding: "8px 18px", borderRadius: "999px", fontSize: "12.5px", fontWeight: 600 }}
              >
                Saqlash
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL: GITHUB TOKEN */}
      {githubModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.8)",
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
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
              GitHub Personal Access Token
            </h3>
            <input
              type="password"
              placeholder="ghp_..."
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              className="misa-glass-input"
              style={{ padding: "10px 14px", borderRadius: "12px", fontSize: "13px" }}
            />
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button
                type="button"
                onClick={() => setGithubModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "999px",
                  background: "rgba(255,255,255,0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                }}
              >
                Yopish
              </button>
              <button
                type="button"
                onClick={async () => {
                  await backendService.saveGithubToken(githubToken.trim());
                  setGithubModalOpen(false);
                  showToast("GitHub token saqlandi ✓");
                }}
                className="misa-btn-violet"
                style={{ padding: "8px 18px", borderRadius: "999px", fontSize: "12.5px", fontWeight: 600 }}
              >
                Saqlash
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: DELETE ACCOUNT CONFIRMATION */}
      {deleteAccountModalOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 500,
            background: "rgba(2, 6, 14, 0.8)",
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
              border: "1px solid rgba(239, 68, 68, 0.4)",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF" }}>
              Mahalliy hisob ma'lumotlarini tozalash
            </h3>
            <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
              Ushbu amal mahalliy sessiya va sozlamalarni tozalaydi hamda tizimdan chiqaradi. Tasdiqlaysizmi?
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}>
              <button
                type="button"
                onClick={() => setDeleteAccountModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "999px",
                  background: "rgba(255,255,255,0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="button"
                onClick={async () => {
                  setDeleteAccountModalOpen(false);
                  await handleLogoutClick();
                }}
                style={{
                  padding: "8px 18px",
                  borderRadius: "999px",
                  background: "#EF4444",
                  color: "#FFFFFF",
                  fontSize: "12.5px",
                  fontWeight: 600,
                }}
              >
                Tozalash va Chiqish
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
