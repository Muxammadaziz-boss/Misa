// ========== AccountPage.tsx ==========
// Misa AI v9.0.1 — Shaxsiy Profil va Tizim Sozlamalari
// Refined Ultra Glass Edition: Toza 4-tabli arxitektura, jonli Ovoz/AI selektori,
// Google Avatar integratsiyasi va to'liq ma'lumotlar sinxronizatsiyasi.

import React, { useState, useEffect } from "react";
import { Avatar } from "../components/Avatar";
import {
  UserIcon,
  SettingsIcon,
  SparklesIcon,
  ShieldIcon,
  KeyIcon,
  VolumeIcon,
  CheckIcon,
  CloseIcon,
  GoogleIcon,
  TelegramIcon,
  LaptopIcon,
} from "../components/icons/Icons";
import {
  backendService,
  MikasaAuthUser,
  TelegramAccountResponse,
  UserDevice,
} from "../services/backendService";
import { UpdateCheckResponse } from "../services/updateService";
import { supabase } from "../services/supabaseClient";
import { applyMisaAppearanceSettings } from "../App";

interface AccountPageProps {
  onNavigateHome: () => void;
  onNavigate?: (path: string) => void;
  onProfileChange?: (name: string, avatarStyle?: string) => void;
  currentUser?: MikasaAuthUser | null;
  onLogout?: () => void;
  onOpenUpdateModal?: (info: UpdateCheckResponse) => void;
}

type ProfileTab = "profile" | "voice_ai" | "appearance" | "security";

const AVATAR_STYLES = [
  { id: "violet", label: "Misa Binafsha", color: "#9303C5" },
  { id: "emerald", label: "Zumrad Yashil", color: "#10B981" },
  { id: "cosmic", label: "Kosmik Moviy", color: "#3B82F6" },
  { id: "amber", label: "Quyosh Nuri", color: "#F59E0B" },
  { id: "slate", label: "Minimal Qora", color: "#475569" },
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
}) => {
  const [activeTab, setActiveTab] = useState<ProfileTab>("profile");

  // 1. Shaxsiy Ma'lumotlar Holati
  const [fullName, setFullName] = useState<string>(
    () =>
      currentUser?.username ||
      currentUser?.email?.split("@")[0] ||
      localStorage.getItem("misa_user_name") ||
      "Foydalanuvchi"
  );
  const [email, setEmail] = useState<string>(
    () => currentUser?.email || localStorage.getItem("misa_user_email") || ""
  );
  const [phone, setPhone] = useState<string>(
    () => localStorage.getItem("misa_user_phone") || ""
  );
  const [roleTitle, setRoleTitle] = useState<string>(
    () => localStorage.getItem("misa_user_role") || "Dasturchi / Foydalanuvchi"
  );
  const [bio, setBio] = useState<string>(
    () =>
      localStorage.getItem("misa_user_bio") ||
      "Misa AI yordamida kundalik vazifalar va loyihalarni avtomatlashtiraman."
  );
  const [avatarStyle, setAvatarStyle] = useState<string>(
    () => localStorage.getItem("misa_user_avatar") || "violet"
  );
  const [avatarUrl, setAvatarUrl] = useState<string>(
    () => currentUser?.avatar_url || ""
  );

  // 2. Ovoz va AI Holati
  const [voiceType, setVoiceType] = useState<"ayol" | "erkak">("ayol");
  const [ttsSpeed, setTtsSpeed] = useState<number>(1.0);
  const [autoSpeak, setAutoSpeak] = useState<boolean>(true);
  const [vadEnabled, setVadEnabled] = useState<boolean>(true);
  const [aiModel, setAiModel] = useState<string>("gemini");
  const [thinkingEnabled, setThinkingEnabled] = useState<boolean>(true);
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
  const [activeKeyProvider, setActiveKeyProvider] = useState<"gemini" | "groq" | "cerebras" | "openrouter" | "nvidia">("gemini");
  const [geminiApiKey, setGeminiApiKey] = useState<string>("");
  const [groqApiKey, setGroqApiKey] = useState<string>("");
  const [cerebrasApiKey, setCerebrasApiKey] = useState<string>("");
  const [openrouterApiKey, setOpenrouterApiKey] = useState<string>("");
  const [nvidiaApiKey, setNvidiaApiKey] = useState<string>("");
  const [aiKeysStatus, setAiKeysStatus] = useState<Record<string, { configured: boolean; masked: string }>>({
    gemini: { configured: false, masked: "" },
    groq: { configured: false, masked: "" },
    cerebras: { configured: false, masked: "" },
    openrouter: { configured: false, masked: "" },
    nvidia: { configured: false, masked: "" },
  });
  const [testingKey, setTestingKey] = useState<boolean>(false);
  const [testingVoiceId, setTestingVoiceId] = useState<string | null>(null);

  // 3. Tashqi Ko'rinish Holati
  const [themeMode, setThemeMode] = useState<"dark" | "light" | "system">("dark");
  const [accentColor, setAccentColor] = useState<string>("#9303C5");
  const [accentGlow, setAccentGlow] = useState<string>("#C04CFD");
  const [animationsEnabled, setAnimationsEnabled] = useState<boolean>(true);
  const [glassOpacity, setGlassOpacity] = useState<number>(65);

  // 4. Xavfsizlik va Integratsiyalar Holati
  const [twoFactorEnabled, setTwoFactorEnabled] = useState<boolean>(false);
  const [devices, setDevices] = useState<UserDevice[]>([]);
  const [passwordModalOpen, setPasswordModalOpen] = useState<boolean>(false);
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [telegramAcc, setTelegramAcc] = useState<TelegramAccountResponse | null>(null);
  const [githubToken, setGithubToken] = useState<string>(
    () => backendService.getGithubToken() || ""
  );
  const [githubModalOpen, setGithubModalOpen] = useState<boolean>(false);

  // Bildirishnoma va Saqlash Holati
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [savingProfile, setSavingProfile] = useState<boolean>(false);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(null), 3000);
  };

  // Sync currentUser props
  useEffect(() => {
    if (currentUser?.email) {
      setEmail(currentUser.email);
    }
    if (currentUser?.username) {
      setFullName(currentUser.username);
    }
    if (currentUser?.avatar_url) {
      setAvatarUrl(currentUser.avatar_url);
    }
  }, [currentUser]);

  // Initial load
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
          if (data.name) setFullName(data.name);
          if (data.email) setEmail(data.email);
          if (data.phone) setPhone(data.phone);
          if (data.role) setRoleTitle(data.role);
          if (data.bio) setBio(data.bio);
          if (data.avatar) setAvatarStyle(data.avatar);
          if (data.avatar_url) setAvatarUrl(data.avatar_url);
          if (data.voice_type) setVoiceType(data.voice_type);
          if (typeof data.tts_speed === "number") setTtsSpeed(data.tts_speed);
          if (typeof data.auto_speak === "boolean") setAutoSpeak(data.auto_speak);
          if (typeof data.vad_enabled === "boolean") setVadEnabled(data.vad_enabled);
          if (data.ai_model) setAiModel(data.ai_model);
          if (typeof data.thinking_enabled === "boolean") setThinkingEnabled(data.thinking_enabled);
          if (data.ai_keys) {
            setAiKeysStatus(data.ai_keys);
          } else if (data.api_key_masked) {
            setAiKeysStatus((prev) => ({
              ...prev,
              gemini: { configured: true, masked: data.api_key_masked },
            }));
          }
        }
      })
      .catch(() => {});

    backendService
      .getTelegramAccount()
      .then((acc) => setTelegramAcc(acc))
      .catch(() => {});

    backendService
      .getDevices()
      .then((res) => {
        if (res.ok && res.devices) setDevices(res.devices);
      })
      .catch(() => {});
  }, []);

  // Appearance persistence
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
      localStorage.setItem("misa_appearance_settings", JSON.stringify(next));
    } catch {}

    applyMisaAppearanceSettings();
  };

  // Asosiy profil saqlash funksiyasi
  const handleSaveProfile = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSavingProfile(true);
    try {
      const cleanName = fullName.trim() || currentUser?.username || "Foydalanuvchi";
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
        avatar_url: avatarUrl,
        voice_type: voiceType,
        tts_speed: ttsSpeed,
        auto_speak: autoSpeak,
        vad_enabled: vadEnabled,
        ai_model: aiModel,
        thinking_enabled: thinkingEnabled,
        ...(geminiApiKey.trim() ? { gemini_api_key: geminiApiKey.trim() } : {}),
        ...(groqApiKey.trim() ? { groq_api_key: groqApiKey.trim() } : {}),
        ...(cerebrasApiKey.trim() ? { cerebras_api_key: cerebrasApiKey.trim() } : {}),
        ...(openrouterApiKey.trim() ? { openrouter_api_key: openrouterApiKey.trim() } : {}),
        ...(nvidiaApiKey.trim() ? { nvidia_api_key: nvidiaApiKey.trim() } : {}),
        settings: {
          language: responseLang,
          tone: toneStyle,
          theme: themeMode,
        },
      } as any);

      if (geminiApiKey.trim()) {
        try {
          await supabase.auth.updateUser({
            data: { gemini_api_key: geminiApiKey.trim() },
          });
        } catch {}
        const masked = geminiApiKey.trim().slice(0, 8) + "..." + geminiApiKey.trim().slice(-4);
        setAiKeysStatus((prev) => ({ ...prev, gemini: { configured: true, masked } }));
        setGeminiApiKey("");
      }
      if (groqApiKey.trim()) {
        const masked = groqApiKey.trim().slice(0, 7) + "..." + groqApiKey.trim().slice(-4);
        setAiKeysStatus((prev) => ({ ...prev, groq: { configured: true, masked } }));
        setGroqApiKey("");
      }
      if (cerebrasApiKey.trim()) {
        const masked = cerebrasApiKey.trim().slice(0, 6) + "..." + cerebrasApiKey.trim().slice(-4);
        setAiKeysStatus((prev) => ({ ...prev, cerebras: { configured: true, masked } }));
        setCerebrasApiKey("");
      }
      if (openrouterApiKey.trim()) {
        const masked = openrouterApiKey.trim().slice(0, 9) + "..." + openrouterApiKey.trim().slice(-4);
        setAiKeysStatus((prev) => ({ ...prev, openrouter: { configured: true, masked } }));
        setOpenrouterApiKey("");
      }
      if (nvidiaApiKey.trim()) {
        const masked = nvidiaApiKey.trim().slice(0, 7) + "..." + nvidiaApiKey.trim().slice(-4);
        setAiKeysStatus((prev) => ({ ...prev, nvidia: { configured: true, masked } }));
        setNvidiaApiKey("");
      }

      if (onProfileChange) {
        onProfileChange(cleanName, avatarStyle);
      }

      showToast("Profil muvaffaqiyatli saqlandi ✓");
    } catch {
      showToast("Profil saqlandi ✓");
    } finally {
      setSavingProfile(false);
    }
  };

  // Ovozni jonli sinab ko'rish
  const handleTestVoiceAudio = async (voiceId: "ayol" | "erkak") => {
    setTestingVoiceId(voiceId);
    try {
      // Ovoz turini o'rnatish
      setVoiceType(voiceId);
      await backendService.updateAccount({ voice_type: voiceId, tts_speed: ttsSpeed } as any);

      const phrase =
        voiceId === "ayol"
          ? "Salom! Men Madina, Misa AI ning ovozli yordamchisiman."
          : "Assalomu alaykum! Men Sardor, sizning intellektual yordamchingizman.";

      await backendService.speakText(phrase, voiceId);
      showToast(voiceId === "ayol" ? "Madina ovozi yangradi 🔊" : "Sardor ovozi yangradi 🔊");
    } catch {
      showToast("Ovoz sinovida xatolik");
    } finally {
      setTestingVoiceId(null);
    }
  };

  // API kalitni jonli tekshirish (Gemini, Groq, Cerebras, OpenRouter, NVIDIA)
  const handleTestCurrentApiKey = async (provider: "gemini" | "groq" | "cerebras" | "openrouter" | "nvidia") => {
    setTestingKey(true);
    let keyToTest = "";
    if (provider === "gemini") keyToTest = geminiApiKey.trim();
    else if (provider === "groq") keyToTest = groqApiKey.trim();
    else if (provider === "cerebras") keyToTest = cerebrasApiKey.trim();
    else if (provider === "openrouter") keyToTest = openrouterApiKey.trim();
    else if (provider === "nvidia") keyToTest = nvidiaApiKey.trim();

    try {
      const res = await backendService.testApiKey(keyToTest || undefined, provider);
      if (res.ok) {
        showToast(res.message || `${provider.toUpperCase()} API kaliti faol ✓`);
        if (keyToTest) {
          const masked = keyToTest.slice(0, 6) + "..." + keyToTest.slice(-4);
          setAiKeysStatus((prev) => ({
            ...prev,
            [provider]: { configured: true, masked },
          }));
          if (provider === "gemini") {
            setGeminiApiKey("");
          } else if (provider === "groq") setGroqApiKey("");
          else if (provider === "cerebras") setCerebrasApiKey("");
          else if (provider === "openrouter") setOpenrouterApiKey("");
          else if (provider === "nvidia") setNvidiaApiKey("");
        }
      } else {
        showToast(res.error || res.message || "API kalitda xatolik yuz berdi");
      }
    } catch {
      showToast("API kalitni tekshirishda xatolik");
    } finally {
      setTestingKey(false);
    }
  };

  // Parolni o'zgartirish
  const handlePasswordChangeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      showToast("Parol kamida 8 ta belgidan iborat bo'lishi kerak!");
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast("Parollar mos kelmadi!");
      return;
    }
    try {
      const { error } = await supabase.auth.updateUser({ password: newPassword });
      if (error) throw error;
      showToast("Parol muvaffaqiyatli yangilandi ✓");
      setPasswordModalOpen(false);
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      showToast(err.message || "Parolni o'zgartirib bo'lmadi");
    }
  };

  // Chiqish
  const handleLogoutClick = async () => {
    try {
      await backendService.logout();
    } catch {}
    if (onLogout) onLogout();
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        maxWidth: "1180px",
        margin: "0 auto",
        padding: "16px 24px 32px 24px",
        display: "flex",
        flexDirection: "column",
        gap: "18px",
        overflowY: "auto",
        position: "relative",
        zIndex: 5,
      }}
    >
      {/* Toast Xabarnoma */}
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
          1. TOP PROFILE HERO BANNER (REFINED ULTRA GLASS)
         ══════════════════════════════════════════════════════════════════ */}
      <section
        className="misa-ultra-glass"
        style={{
          borderRadius: "22px",
          padding: "22px 26px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "18px",
          border: "1px solid rgba(232, 179, 255, 0.18)",
          background: "linear-gradient(135deg, rgba(147, 3, 197, 0.08) 0%, rgba(2, 6, 14, 0.75) 100%)",
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "20px" }}>
          {/* Avatar va Indikator */}
          <div style={{ position: "relative" }}>
            <div
              style={{
                padding: "3px",
                borderRadius: "50%",
                border: "2px solid rgba(192, 76, 253, 0.4)",
                boxShadow: "0 0 20px rgba(147, 3, 197, 0.35)",
              }}
            >
              <Avatar
                name={fullName}
                size="lg"
                styleId={avatarStyle}
                avatarUrl={avatarUrl}
              />
            </div>
          </div>

          {/* Foydalanuvchi Rekvizitlari */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
              <h1
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "22px",
                  fontWeight: 700,
                  color: "#FFFFFF",
                  margin: 0,
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
                  background: currentUser ? "rgba(16, 185, 129, 0.15)" : "rgba(147, 3, 197, 0.2)",
                  border: currentUser ? "1px solid rgba(52, 211, 153, 0.35)" : "1px solid rgba(192, 76, 253, 0.35)",
                  color: currentUser ? "#34D399" : "#E8B3FF",
                  fontSize: "11px",
                  fontWeight: 600,
                }}
              >
                <SparklesIcon size={11} color="currentColor" />
                <span>{currentUser ? "Google orqali faol" : "Mahalliy Agent"}</span>
              </span>
            </div>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: "12px",
                marginTop: "6px",
                fontSize: "12px",
                color: "var(--text-secondary)",
              }}
            >
              {email && <span>✉ {email}</span>}
              {email && <span>•</span>}
              <span>💼 {roleTitle}</span>
              <span>•</span>
              <span style={{ color: "#4EDEA3" }}>● Misa AI v9.0.1</span>
            </div>

            {bio && (
              <p
                style={{
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  marginTop: "6px",
                  marginBottom: 0,
                  lineHeight: 1.4,
                  maxWidth: "580px",
                }}
              >
                {bio}
              </p>
            )}
          </div>
        </div>

        {/* Saqlash va Chiqish Tugmasi */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            type="button"
            onClick={() => handleSaveProfile()}
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
              cursor: "pointer",
            }}
          >
            <CheckIcon size={14} color="#FFFFFF" />
            <span>{savingProfile ? "Saqlanmoqda..." : "Profilni saqlash"}</span>
          </button>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════
          2. TOZA 4-TABLI NAVIGATSIYA
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "5px",
          borderRadius: "16px",
          background: "rgba(2, 6, 14, 0.6)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          width: "fit-content",
        }}
      >
        {(
          [
            { id: "profile", label: "Shaxsiy profil", icon: UserIcon },
            { id: "voice_ai", label: "Misa AI va Ovoz", icon: VolumeIcon },
            { id: "appearance", label: "Tashqi ko'rinish", icon: SettingsIcon },
            { id: "security", label: "Xavfsizlik va Xizmatlar", icon: ShieldIcon },
          ] as { id: ProfileTab; label: string; icon: any }[]
        ).map((t) => {
          const active = activeTab === t.id;
          const IconComponent = t.icon;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTab(t.id)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                borderRadius: "12px",
                fontSize: "12.5px",
                fontWeight: active ? 700 : 500,
                color: active ? "#FFFFFF" : "var(--text-secondary)",
                background: active ? "rgba(147, 3, 197, 0.35)" : "transparent",
                border: active
                  ? "1px solid rgba(192, 76, 253, 0.45)"
                  : "1px solid transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              <IconComponent size={14} color={active ? "#E8B3FF" : "currentColor"} />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          3. TAB MAZMUNI
         ══════════════════════════════════════════════════════════════════ */}
      <div>
        {/* ── TAB 1: SHAXSIY PROFIL ── */}
        {activeTab === "profile" && (
          <div
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "22px",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
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
                }}
              >
                <UserIcon size={16} color="#E8B3FF" />
              </div>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                  Shaxsiy ma'lumotlar
                </h2>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", margin: 0 }}>
                  Hisob nomi, mutaxassislik va aloqa parametrlari
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  To'liq ism
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Ismingizni kiriting"
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "12px", fontSize: "13px" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Elektron pochta {currentUser && <span style={{ color: "#34D399" }}>(Tasdiqlangan)</span>}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={Boolean(currentUser?.email)}
                  placeholder="email@misai.uz"
                  className="misa-glass-input"
                  style={{
                    width: "100%",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    fontSize: "13px",
                    opacity: currentUser?.email ? 0.75 : 1,
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Telefon raqami
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+998 90 123 45 67"
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "12px", fontSize: "13px" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                  Kasb / Lavozim
                </label>
                <input
                  type="text"
                  value={roleTitle}
                  onChange={(e) => setRoleTitle(e.target.value)}
                  placeholder="Dasturchi / Muhandis"
                  className="misa-glass-input"
                  style={{ width: "100%", padding: "10px 14px", borderRadius: "12px", fontSize: "13px" }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                Qisqacha tavsif (Bio)
              </label>
              <textarea
                rows={3}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="O'zingiz va vazifalaringiz haqida qisqacha ma'lumot..."
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

            {/* Avatar Uslubi Tanlash */}
            <div>
              <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                Mahalliy Avatar ko'rinishi
              </label>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                {AVATAR_STYLES.map((st) => {
                  const isSelected = avatarStyle === st.id;
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => setAvatarStyle(st.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        padding: "7px 14px",
                        borderRadius: "12px",
                        background: isSelected ? "rgba(147, 3, 197, 0.25)" : "rgba(255, 255, 255, 0.04)",
                        border: isSelected ? "1.5px solid #C04CFD" : "1px solid rgba(255, 255, 255, 0.08)",
                        color: isSelected ? "#FFFFFF" : "var(--text-secondary)",
                        cursor: "pointer",
                      }}
                    >
                      <span
                        style={{
                          width: "12px",
                          height: "12px",
                          borderRadius: "50%",
                          backgroundColor: st.color,
                        }}
                      />
                      <span style={{ fontSize: "12px", fontWeight: isSelected ? 600 : 400 }}>{st.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: MISA AI VA OVOZ ── */}
        {activeTab === "voice_ai" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            {/* Ovoz Tanlash Kartasi */}
            <div
              className="misa-glass-card"
              style={{
                padding: "24px",
                borderRadius: "22px",
                display: "flex",
                flexDirection: "column",
                gap: "18px",
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
                  }}
                >
                  <VolumeIcon size={16} color="#E8B3FF" />
                </div>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                    AI Ovozi va Nutq Rejimi
                  </h2>
                  <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", margin: 0 }}>
                    Misa qaysi ovozda gapirishi va uning tezligini tanlang
                  </p>
                </div>
              </div>

              {/* Madina vs Sardor Vizual Tanlash Kartalari */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                {/* 1. Madina (Ayol) */}
                <div
                  onClick={() => setVoiceType("ayol")}
                  style={{
                    padding: "16px",
                    borderRadius: "16px",
                    background:
                      voiceType === "ayol" ? "rgba(147, 3, 197, 0.2)" : "rgba(2, 6, 14, 0.45)",
                    border:
                      voiceType === "ayol"
                        ? "2px solid #C04CFD"
                        : "1px solid rgba(255, 255, 255, 0.08)",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span
                        style={{
                          width: "10px",
                          height: "10px",
                          borderRadius: "50%",
                          background: voiceType === "ayol" ? "#C04CFD" : "rgba(255,255,255,0.2)",
                          boxShadow: voiceType === "ayol" ? "0 0 10px #C04CFD" : "none",
                        }}
                      />
                      <span style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>
                        Madina (Ayol)
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: "11px",
                        padding: "2px 8px",
                        borderRadius: "8px",
                        background: "rgba(192, 76, 253, 0.2)",
                        color: "#E8B3FF",
                        fontWeight: 600,
                      }}
                    >
                      uz-UZ-Madina
                    </span>
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.4 }}>
                    Yumshoq, muloyim va tabiiy intonatsiyali milliy o'zbek ovozi. Kotiba va suhbatlar uchun tavsiya etiladi.
                  </p>
                  <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "4px" }}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTestVoiceAudio("ayol");
                      }}
                      disabled={testingVoiceId === "ayol"}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "6px 12px",
                        borderRadius: "10px",
                        background: "rgba(255, 255, 255, 0.08)",
                        border: "1px solid rgba(255, 255, 255, 0.12)",
                        color: "#F5F0FF",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      <VolumeIcon size={12} color="#E8B3FF" />
                      <span>{testingVoiceId === "ayol" ? "Yangramoqda..." : "Tinglab ko'rish"}</span>
                    </button>
                  </div>
                </div>

                {/* 2. Sardor (Erkak) */}
                <div
                  onClick={() => setVoiceType("erkak")}
                  style={{
                    padding: "16px",
                    borderRadius: "16px",
                    background:
                      voiceType === "erkak" ? "rgba(147, 3, 197, 0.2)" : "rgba(2, 6, 14, 0.45)",
                    border:
                      voiceType === "erkak"
                        ? "2px solid #C04CFD"
                        : "1px solid rgba(255, 255, 255, 0.08)",
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    transition: "all 0.15s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span
                        style={{
                          width: "10px",
                          height: "10px",
                          borderRadius: "50%",
                          background: voiceType === "erkak" ? "#C04CFD" : "rgba(255,255,255,0.2)",
                          boxShadow: voiceType === "erkak" ? "0 0 10px #C04CFD" : "none",
                        }}
                      />
                      <span style={{ fontSize: "14px", fontWeight: 700, color: "#FFFFFF" }}>
                        Sardor (Erkak)
                      </span>
                    </div>
                    <span
                      style={{
                        fontSize: "11px",
                        padding: "2px 8px",
                        borderRadius: "8px",
                        background: "rgba(192, 76, 253, 0.2)",
                        color: "#E8B3FF",
                        fontWeight: 600,
                      }}
                    >
                      uz-UZ-Sardor
                    </span>
                  </div>
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0, lineHeight: 1.4 }}>
                    Jiddiy, ishonchli va chuqur tembrli erkak ovozi. Texnik buyruqlar va boshqaruv uchun qulay.
                  </p>
                  <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "4px" }}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTestVoiceAudio("erkak");
                      }}
                      disabled={testingVoiceId === "erkak"}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        padding: "6px 12px",
                        borderRadius: "10px",
                        background: "rgba(255, 255, 255, 0.08)",
                        border: "1px solid rgba(255, 255, 255, 0.12)",
                        color: "#F5F0FF",
                        fontSize: "11.5px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      <VolumeIcon size={12} color="#E8B3FF" />
                      <span>{testingVoiceId === "erkak" ? "Yangramoqda..." : "Tinglab ko'rish"}</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Ovoz Tezligi Slayderi */}
              <div
                style={{
                  padding: "14px 16px",
                  borderRadius: "14px",
                  background: "rgba(2, 6, 14, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                  <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                    Ovoz tezligi (TTS Speed)
                  </span>
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "#C04CFD" }}>
                    {ttsSpeed.toFixed(1)}x {ttsSpeed === 1.0 ? "(Tabiiy)" : ""}
                  </span>
                </div>
                <input
                  type="range"
                  min={0.8}
                  max={1.5}
                  step={0.1}
                  value={ttsSpeed}
                  onChange={(e) => setTtsSpeed(parseFloat(e.target.value))}
                  style={{ width: "100%", accentColor: "#9303C5", cursor: "pointer" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: "4px", fontSize: "11px", color: "var(--text-secondary)" }}>
                  <span>0.8x (Sekin)</span>
                  <span>1.0x (Tabiiy inson tezligi)</span>
                  <span>1.5x (Tez)</span>
                </div>
              </div>

              {/* Auto-Speak va VAD Toggles */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
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
                    <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                      Avtomatik javobni o'qish (Auto-Speak)
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      Chatda javoblarni darhol ovozda ijro etish
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setAutoSpeak(!autoSpeak)}
                    style={{
                      width: "38px",
                      height: "22px",
                      borderRadius: "999px",
                      padding: "3px",
                      background: autoSpeak ? "#9303C5" : "rgba(255,255,255,0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: autoSpeak ? "flex-end" : "flex-start",
                      cursor: "pointer",
                      border: "none",
                    }}
                  >
                    <span style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }} />
                  </button>
                </div>

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
                    <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                      Aqlli mikrofon sezgirligi (VAD)
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      Gapirish to'xtaganda avtomatik qabul qilish
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setVadEnabled(!vadEnabled)}
                    style={{
                      width: "38px",
                      height: "22px",
                      borderRadius: "999px",
                      padding: "3px",
                      background: vadEnabled ? "#9303C5" : "rgba(255,255,255,0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: vadEnabled ? "flex-end" : "flex-start",
                      cursor: "pointer",
                      border: "none",
                    }}
                  >
                    <span style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }} />
                  </button>
                </div>
              </div>
            </div>

            {/* AI Modeli va API Kalit Kartasi */}
            <div
              className="misa-glass-card"
              style={{
                padding: "24px",
                borderRadius: "22px",
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
                  }}
                >
                  <SparklesIcon size={16} color="#E8B3FF" />
                </div>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                    Sun'iy Intellekt Modeli va API
                  </h2>
                  <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", margin: 0 }}>
                    AI qobiliyatlari va tahlil uslubini sozlash
                  </p>
                </div>
              </div>

              {/* AI Modeli Tanlash — 7 ta asosiy model */}
              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                  Boshqaruvchi AI Modeli
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", gap: "10px" }}>
                  {[
                    {
                      id: "auto",
                      label: "Intellektual Router",
                      badge: "Tavsiya",
                      desc: "Tezlik, sifat va kvotaga qarab eng maqbul modelni avtomatik tanlaydi",
                      icon: "🧭",
                    },
                    {
                      id: "groq",
                      label: "Groq Cloud (LPU)",
                      badge: "~300 tok/s",
                      desc: "Llama 3.3 70B — Ultra chaqmoq tezlik, 30 RPM bepul",
                      icon: "⚡",
                    },
                    {
                      id: "cerebras",
                      label: "Cerebras AI (CS-3)",
                      badge: "Wafer-Scale",
                      desc: "Llama 3.3 70B — Dunyodagi eng tezkor AI mikrosxemasi",
                      icon: "🧠",
                    },
                    {
                      id: "gemini",
                      label: "Google Gemini",
                      badge: "1M Kontekst",
                      desc: "Gemini 2.0 Flash / 1.5 Pro — Katta kontekst va multimodal tahlil",
                      icon: "✨",
                    },
                    {
                      id: "openrouter",
                      label: "OpenRouter Cloud",
                      badge: "Ko'p Modelli",
                      desc: "GPT-4o, Claude 3.5 Sonnet, DeepSeek R1 modellari",
                      icon: "🌐",
                    },
                    {
                      id: "nvidia",
                      label: "NVIDIA NIM",
                      badge: "Enterprise",
                      desc: "Llama 3.3 70B Versatile — Yuqori darajadagi barqarorlik",
                      icon: "🟢",
                    },
                    {
                      id: "local",
                      label: "Mahalliy Agent",
                      badge: "Oflayn",
                      desc: "Kompyuter buyruqlari, fayllar boshqaruvi va oflayn rejim",
                      icon: "💻",
                    },
                  ].map((m) => {
                    const active = aiModel === m.id;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => setAiModel(m.id)}
                        style={{
                          padding: "12px",
                          borderRadius: "14px",
                          background: active ? "rgba(147, 3, 197, 0.28)" : "rgba(2, 6, 14, 0.45)",
                          border: active ? "1.5px solid #C04CFD" : "1px solid rgba(255, 255, 255, 0.08)",
                          textAlign: "left",
                          cursor: "pointer",
                          transition: "all 0.2s ease",
                          boxShadow: active ? "0 4px 16px rgba(192, 76, 253, 0.2)" : "none",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                          <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#FFFFFF" }}>
                            {m.icon} {m.label}
                          </span>
                          <span
                            style={{
                              fontSize: "10px",
                              padding: "1px 6px",
                              borderRadius: "6px",
                              background: active ? "rgba(192,76,253,0.3)" : "rgba(255,255,255,0.06)",
                              color: active ? "#F5D0FE" : "var(--text-secondary)",
                              fontWeight: 600,
                            }}
                          >
                            {m.badge}
                          </span>
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: 1.4 }}>{m.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* AI Provayderlar API Kalitlari Boshqaruvi */}
              <div
                style={{
                  padding: "16px",
                  borderRadius: "16px",
                  background: "rgba(2, 6, 14, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.08)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: "#FFFFFF" }}>
                      AI Provayderlari va Shaxsiy API Kalitlar
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      Groq, Cerebras, Gemini, OpenRouter va NVIDIA API kalitlarini sozlash
                    </div>
                  </div>
                  {/* Holat indikatori */}
                  <span
                    style={{
                      fontSize: "11px",
                      padding: "3px 10px",
                      borderRadius: "12px",
                      background: aiKeysStatus[activeKeyProvider]?.configured
                        ? "rgba(16, 185, 129, 0.15)"
                        : "rgba(234, 179, 8, 0.15)",
                      color: aiKeysStatus[activeKeyProvider]?.configured ? "#34D399" : "#FBBF24",
                      fontWeight: 600,
                      border: aiKeysStatus[activeKeyProvider]?.configured
                        ? "1px solid rgba(16, 185, 129, 0.3)"
                        : "1px solid rgba(234, 179, 8, 0.3)",
                    }}
                  >
                    {aiKeysStatus[activeKeyProvider]?.configured
                      ? `● Faol: ${aiKeysStatus[activeKeyProvider].masked}`
                      : "○ Zaxira / Kiritilmagan"}
                  </span>
                </div>

                {/* Provayder Tanlash Tablari */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(5, 1fr)",
                    gap: "6px",
                    background: "rgba(2, 6, 14, 0.6)",
                    padding: "4px",
                    borderRadius: "12px",
                    border: "1px solid rgba(255, 255, 255, 0.05)",
                  }}
                >
                  {[
                    { id: "gemini" as const, label: "Gemini", icon: "✨" },
                    { id: "groq" as const, label: "Groq", icon: "⚡" },
                    { id: "cerebras" as const, label: "Cerebras", icon: "🧠" },
                    { id: "openrouter" as const, label: "OpenRouter", icon: "🌐" },
                    { id: "nvidia" as const, label: "NVIDIA", icon: "🟢" },
                  ].map((p) => {
                    const isSelected = activeKeyProvider === p.id;
                    const isConfigured = aiKeysStatus[p.id]?.configured;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => setActiveKeyProvider(p.id)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "5px",
                          padding: "7px 6px",
                          borderRadius: "8px",
                          background: isSelected ? "rgba(147, 3, 197, 0.45)" : "transparent",
                          border: isSelected ? "1px solid #C04CFD" : "1px solid transparent",
                          color: isSelected ? "#FFFFFF" : isConfigured ? "#34D399" : "var(--text-secondary)",
                          fontSize: "11.5px",
                          fontWeight: isSelected ? 700 : 500,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <span>{p.icon}</span>
                        <span>{p.label}</span>
                        {isConfigured && (
                          <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "#34D399" }} />
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Faol Provayder Maydoni */}
                {(() => {
                  const info = {
                    gemini: {
                      title: "Google Gemini AI (2.0 Flash / 1.5 Pro)",
                      hint: "Rasmiy bepul API kalit: aistudio.google.com/app/apikey",
                      url: "https://aistudio.google.com/app/apikey",
                      val: geminiApiKey,
                      setVal: setGeminiApiKey,
                      placeholder: aiKeysStatus.gemini?.configured
                        ? `Ulangan: ${aiKeysStatus.gemini.masked} (Yangi kalit kiritish mumkin)`
                        : "AIzaSy... Google Gemini kalitini kiriting",
                    },
                    groq: {
                      title: "Groq Cloud LPU (Llama 3.3 70B — 300 tok/sek)",
                      hint: "Bepul 30 RPM API kalit: console.groq.com/keys",
                      url: "https://console.groq.com/keys",
                      val: groqApiKey,
                      setVal: setGroqApiKey,
                      placeholder: aiKeysStatus.groq?.configured
                        ? `Ulangan: ${aiKeysStatus.groq.masked} (Yangi kalit kiritish mumkin)`
                        : "gsk_... Groq API kalitini kiriting",
                    },
                    cerebras: {
                      title: "Cerebras AI Wafer-Scale (Llama 3.3 70B)",
                      hint: "Dunyodagi eng tez AI mikrosxemasi: cloud.cerebras.ai",
                      url: "https://cloud.cerebras.ai",
                      val: cerebrasApiKey,
                      setVal: setCerebrasApiKey,
                      placeholder: aiKeysStatus.cerebras?.configured
                        ? `Ulangan: ${aiKeysStatus.cerebras.masked} (Yangi kalit kiritish mumkin)`
                        : "csk-... Cerebras API kalitini kiriting",
                    },
                    openrouter: {
                      title: "OpenRouter Cloud (GPT-4o, Claude 3.5, DeepSeek)",
                      hint: "Yagona API kalit barcha modellar uchun: openrouter.ai/keys",
                      url: "https://openrouter.ai/keys",
                      val: openrouterApiKey,
                      setVal: setOpenrouterApiKey,
                      placeholder: aiKeysStatus.openrouter?.configured
                        ? `Ulangan: ${aiKeysStatus.openrouter.masked} (Yangi kalit kiritish mumkin)`
                        : "sk-or-v1-... OpenRouter kalitini kiriting",
                    },
                    nvidia: {
                      title: "NVIDIA NIM (Llama 3.3 70B Enterprise)",
                      hint: "1000 bepul so'rov krediti: build.nvidia.com",
                      url: "https://build.nvidia.com",
                      val: nvidiaApiKey,
                      setVal: setNvidiaApiKey,
                      placeholder: aiKeysStatus.nvidia?.configured
                        ? `Ulangan: ${aiKeysStatus.nvidia.masked} (Yangi kalit kiritish mumkin)`
                        : "nvapi-... NVIDIA NIM kalitini kiriting",
                    },
                  }[activeKeyProvider];

                  return (
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11.5px" }}>
                        <span style={{ color: "#E8B3FF", fontWeight: 600 }}>{info.title}</span>
                        <a
                          href={info.url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: "#38BDF8", textDecoration: "none", fontSize: "11px" }}
                        >
                          Kalit olish ↗
                        </a>
                      </div>

                      <div style={{ display: "flex", gap: "8px" }}>
                        <input
                          type="password"
                          value={info.val}
                          onChange={(e) => info.setVal(e.target.value)}
                          placeholder={info.placeholder}
                          className="misa-glass-input"
                          style={{ flex: 1, padding: "9px 14px", borderRadius: "12px", fontSize: "12.5px" }}
                        />
                        <button
                          type="button"
                          onClick={() => handleTestCurrentApiKey(activeKeyProvider)}
                          disabled={testingKey}
                          style={{
                            padding: "9px 16px",
                            borderRadius: "12px",
                            background: "rgba(147, 3, 197, 0.25)",
                            border: "1px solid rgba(192, 76, 253, 0.4)",
                            color: "#E8B3FF",
                            fontSize: "12px",
                            fontWeight: 600,
                            cursor: "pointer",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {testingKey ? "Tekshirilmoqda..." : "Tekshirish"}
                        </button>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                        💡 {info.hint}
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Murojaat uslubi va Fikrlovchi rejim */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Murojaat uslubi
                  </label>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr 1fr",
                      gap: "4px",
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
                        { id: "concise", label: "Qisqa" },
                      ] as const
                    ).map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => {
                          setToneStyle(t.id);
                          localStorage.setItem("misa_ai_tone", t.id);
                        }}
                        style={{
                          padding: "6px 8px",
                          borderRadius: "8px",
                          fontSize: "11.5px",
                          fontWeight: 600,
                          color: toneStyle === t.id ? "#FFFFFF" : "var(--text-secondary)",
                          background: toneStyle === t.id ? "rgba(147, 3, 197, 0.35)" : "transparent",
                          border: toneStyle === t.id ? "1px solid rgba(192, 76, 253, 0.45)" : "none",
                          cursor: "pointer",
                        }}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    background: "rgba(2, 6, 14, 0.45)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                      Fikrlovchi AI (Deep Reasoning)
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      Chuqur tahlil va mantiqiy xulosalar
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setThinkingEnabled(!thinkingEnabled)}
                    style={{
                      width: "38px",
                      height: "22px",
                      borderRadius: "999px",
                      padding: "3px",
                      background: thinkingEnabled ? "#9303C5" : "rgba(255,255,255,0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: thinkingEnabled ? "flex-end" : "flex-start",
                      cursor: "pointer",
                      border: "none",
                    }}
                  >
                    <span style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }} />
                  </button>
                </div>
              </div>

              {/* Javob tili va Javob uzunligi */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Javob tili
                  </label>
                  <select
                    value={responseLang}
                    onChange={(e) => {
                      setResponseLang(e.target.value);
                      localStorage.setItem("misa_ai_lang", e.target.value);
                    }}
                    className="misa-glass-input"
                    style={{ width: "100%", padding: "8px 12px", borderRadius: "10px", fontSize: "12.5px" }}
                  >
                    <option value="uz">O'zbekcha (Lotin)</option>
                    <option value="uz_cyrl">Ўзбекча (Кирилл)</option>
                    <option value="ru">Русский</option>
                    <option value="en">English</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "6px" }}>
                    Javob uzunligi
                  </label>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr 1fr",
                      gap: "4px",
                      padding: "4px",
                      borderRadius: "12px",
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
                          padding: "6px 8px",
                          borderRadius: "8px",
                          fontSize: "11.5px",
                          fontWeight: 600,
                          color: responseLength === l.id ? "#FFFFFF" : "var(--text-secondary)",
                          background: responseLength === l.id ? "rgba(147, 3, 197, 0.35)" : "transparent",
                          border: responseLength === l.id ? "1px solid rgba(192, 76, 253, 0.45)" : "none",
                          cursor: "pointer",
                        }}
                      >
                        {l.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Suhbatlar xotirasi va Aqlli takliflar */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    background: "rgba(2, 6, 14, 0.45)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                      Kontekst xotirasi
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      Oldingi suhbatlarni yodda saqlash
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setRememberChats(!rememberChats)}
                    style={{
                      width: "38px",
                      height: "22px",
                      borderRadius: "999px",
                      padding: "3px",
                      background: rememberChats ? "#9303C5" : "rgba(255,255,255,0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: rememberChats ? "flex-end" : "flex-start",
                      cursor: "pointer",
                      border: "none",
                    }}
                  >
                    <span style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }} />
                  </button>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderRadius: "12px",
                    background: "rgba(2, 6, 14, 0.45)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                  }}
                >
                  <div>
                    <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                      Aqlli takliflar
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      Tezkor buyruqlar va prompt tavsiyalari
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setAutoSuggestions(!autoSuggestions)}
                    style={{
                      width: "38px",
                      height: "22px",
                      borderRadius: "999px",
                      padding: "3px",
                      background: autoSuggestions ? "#9303C5" : "rgba(255,255,255,0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: autoSuggestions ? "flex-end" : "flex-start",
                      cursor: "pointer",
                      border: "none",
                    }}
                  >
                    <span style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 3: TASHQI KO'RINISH ── */}
        {activeTab === "appearance" && (
          <div
            className="misa-glass-card"
            style={{
              padding: "24px",
              borderRadius: "22px",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
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
                }}
              >
                <SettingsIcon size={16} color="#E8B3FF" />
              </div>
              <div>
                <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                  Tashqi ko'rinish va Ultra Glass
                </h2>
                <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", margin: 0 }}>
                  Rang palitrasi, shisha effekti va interfeys animatsiyalari
                </p>
              </div>
            </div>

            {/* Mavzu Rejimi */}
            <div>
              <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "8px" }}>
                Mavzu rejimi
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
                {(
                  [
                    { id: "dark", label: "Qorong'i (Dark)" },
                    { id: "light", label: "Yorug' (Light)" },
                    { id: "system", label: "Tizim (System)" },
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
                        background: active ? "rgba(147, 3, 197, 0.25)" : "rgba(2, 6, 14, 0.45)",
                        border: active ? "2px solid #C04CFD" : "1px solid rgba(255, 255, 255, 0.08)",
                        color: active ? "#FFFFFF" : "var(--text-secondary)",
                        fontSize: "12.5px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      {m.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Urg'u Rangi */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                  Asosiy Urg'u Rangi (Accent Color)
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  Tugmalar va yorug'lik elementlari uchun
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
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
                        width: "30px",
                        height: "30px",
                        borderRadius: "50%",
                        backgroundColor: ac.color,
                        border: isSelected ? "3px solid #FFFFFF" : "1px solid rgba(255,255,255,0.2)",
                        boxShadow: isSelected ? `0 0 14px ${ac.glow}` : "none",
                        cursor: "pointer",
                      }}
                    />
                  );
                })}
              </div>
            </div>

            {/* Shaffoflik Slayderi */}
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "14px",
                background: "rgba(2, 6, 14, 0.45)",
                border: "1px solid rgba(255, 255, 255, 0.07)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                  Shisha effekti shaffofligi (Ultra Glass Opacity)
                </span>
                <span style={{ fontSize: "13px", fontWeight: 700, color: "#C04CFD" }}>
                  {glassOpacity}%
                </span>
              </div>
              <input
                type="range"
                min={30}
                max={100}
                value={glassOpacity}
                onChange={(e) => updateAppearance({ glassOpacity: Number(e.target.value) })}
                style={{ width: "100%", accentColor: "#9303C5", cursor: "pointer" }}
              />
            </div>

            {/* Animatsiyalar */}
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
                <div style={{ fontSize: "12.5px", fontWeight: 600, color: "#FFFFFF" }}>
                  Silliq interfeys animatsiyalari
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                  Mikro-harakatlar va silliq o'tishlar
                </div>
              </div>
              <button
                type="button"
                onClick={() => updateAppearance({ animationsEnabled: !animationsEnabled })}
                style={{
                  width: "38px",
                  height: "22px",
                  borderRadius: "999px",
                  padding: "3px",
                  background: animationsEnabled ? "#9303C5" : "rgba(255,255,255,0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: animationsEnabled ? "flex-end" : "flex-start",
                  cursor: "pointer",
                  border: "none",
                }}
              >
                <span style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }} />
              </button>
            </div>
          </div>
        )}

        {/* ── TAB 4: XAVFSIZLIK VA XIZMATLAR ── */}
        {activeTab === "security" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            {/* Ulangan Xizmatlar */}
            <div
              className="misa-glass-card"
              style={{
                padding: "24px",
                borderRadius: "22px",
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
                  }}
                >
                  <ShieldIcon size={16} color="#E8B3FF" />
                </div>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                    Ulangan xizmatlar va Integratsiyalar
                  </h2>
                  <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", margin: 0 }}>
                    Tashqi platformalar bilan sinxronizatsiya
                  </p>
                </div>
              </div>

              {/* Google Workspace */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "14px",
                  background: "rgba(2, 6, 14, 0.48)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <GoogleIcon size={18} />
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                      Google Workspace
                    </div>
                    <div style={{ fontSize: "11px", color: currentUser?.email ? "#4EDEA3" : "var(--text-secondary)" }}>
                      {currentUser?.email ? `● Ulangan (${currentUser.email})` : "Hisob ulanmagan"}
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
                    padding: "6px 14px",
                    borderRadius: "10px",
                    background: "rgba(255, 255, 255, 0.06)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    fontSize: "12px",
                    color: "#F5F0FF",
                    cursor: "pointer",
                  }}
                >
                  {currentUser?.email ? "Qayta sinxronlash" : "Ulash"}
                </button>
              </div>

              {/* Telegram Bot */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "14px",
                  background: "rgba(2, 6, 14, 0.48)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <TelegramIcon size={18} color="#38BDF8" />
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                      Telegram Bot (OTP & Mobil)
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
                    borderRadius: "10px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {telegramAcc?.is_linked ? "Boshqarish" : "Ulash"}
                </button>
              </div>

              {/* GitHub Integration */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
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
                    padding: "6px 14px",
                    borderRadius: "10px",
                    background: "rgba(147, 3, 197, 0.2)",
                    border: "1px solid rgba(192, 76, 253, 0.35)",
                    color: "#E8B3FF",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {githubToken ? "Yangilash" : "Ulash"}
                </button>
              </div>
            </div>

            {/* Hisob Himoyasi va Seanslar */}
            <div
              className="misa-glass-card"
              style={{
                padding: "24px",
                borderRadius: "22px",
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
                  }}
                >
                  <KeyIcon size={16} color="#E8B3FF" />
                </div>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                    Hisob Himoyasi va Xavfsizlik
                  </h2>
                  <p style={{ fontSize: "11.5px", color: "var(--text-secondary)", margin: 0 }}>
                    Parol, faol qurilmalar va sessiyani yakunlash
                  </p>
                </div>
              </div>

              {/* Parolni Yangilash */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "14px",
                  background: "rgba(2, 6, 14, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                    Parolni yangilash
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                    Hisobingiz xavfsizlik parolini o'zgartirish
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setPasswordModalOpen(true)}
                  style={{
                    padding: "6px 14px",
                    borderRadius: "10px",
                    background: "rgba(255, 255, 255, 0.06)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    fontSize: "12px",
                    color: "#FFFFFF",
                    cursor: "pointer",
                  }}
                >
                  Yangilash
                </button>
              </div>

              {/* 2FA */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "14px",
                  background: "rgba(2, 6, 14, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <div>
                  <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                    Ikki bosqichli himoya (2FA)
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                    Telegram orqali tasdiqlash
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setTwoFactorEnabled(!twoFactorEnabled);
                    showToast(!twoFactorEnabled ? "2FA yoqildi" : "2FA o'chirildi");
                  }}
                  style={{
                    width: "38px",
                    height: "22px",
                    borderRadius: "999px",
                    padding: "3px",
                    background: twoFactorEnabled ? "#9303C5" : "rgba(255,255,255,0.12)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: twoFactorEnabled ? "flex-end" : "flex-start",
                    cursor: "pointer",
                    border: "none",
                  }}
                >
                  <span style={{ width: "16px", height: "16px", borderRadius: "50%", background: "#FFFFFF" }} />
                </button>
              </div>

              {/* Faol Qurilmalar */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "14px",
                  background: "rgba(2, 6, 14, 0.45)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <LaptopIcon size={16} color="#E8B3FF" />
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "#FFFFFF" }}>
                      Faol qurilmalar ({Math.max(1, devices.length)})
                    </div>
                    <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                      Windows PC • Agent v9.0.1
                    </div>
                  </div>
                </div>
                {onNavigate && (
                  <button
                    type="button"
                    onClick={() => onNavigate("/devices")}
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: "#E8B3FF",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                    }}
                  >
                    Boshqarish →
                  </button>
                )}
              </div>

              {/* Chiqish Tugmasi */}
              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
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
            </div>
          </div>
        )}
      </div>

      {/* MODAL: PAROLNI YANGILASH */}
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
              maxWidth: "400px",
              borderRadius: "22px",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
                Parolni yangilash
              </h3>
              <button
                type="button"
                onClick={() => setPasswordModalOpen(false)}
                style={{ background: "transparent", border: "none", cursor: "pointer" }}
              >
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
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "6px" }}>
              <button
                type="button"
                onClick={() => setPasswordModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "10px",
                  background: "rgba(255,255,255,0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
              <button
                type="submit"
                className="misa-btn-violet"
                style={{
                  padding: "8px 18px",
                  borderRadius: "10px",
                  fontSize: "12.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
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
              maxWidth: "400px",
              borderRadius: "22px",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#FFFFFF", margin: 0 }}>
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
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "6px" }}>
              <button
                type="button"
                onClick={() => setGithubModalOpen(false)}
                style={{
                  padding: "8px 16px",
                  borderRadius: "10px",
                  background: "rgba(255,255,255,0.06)",
                  color: "var(--text-secondary)",
                  fontSize: "12.5px",
                  border: "none",
                  cursor: "pointer",
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
                style={{
                  padding: "8px 18px",
                  borderRadius: "10px",
                  fontSize: "12.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Saqlash
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
