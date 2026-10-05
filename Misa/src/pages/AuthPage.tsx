// ========== AuthPage.tsx ==========
// Misa AI v9.0.0 — Account Registration & Authentication System
// Ultra Glass Auth Gate for Login, Registration, Password Reset and Email Verification

import React, { useState, useEffect } from "react";
import {
  backendService,
  MikasaAuthUser,
} from "../services/backendService";
import {
  supabase,
  isSupabaseConfigured,
} from "../services/supabaseClient";
import {
  SparklesIcon,
  ShieldIcon,
  KeyIcon,
  UserIcon,
  CheckIcon,
  AlertTriangleIcon,
  GoogleIcon,
} from "../components/icons/Icons";
import { MisaLogo } from "../components/MisaLogo";
import { WindowControls } from "../components/WindowControls";

interface AuthPageProps {
  onAuthSuccess: (user: MikasaAuthUser) => void;
}

type AuthTab = "login" | "register" | "forgot" | "reset" | "verify";

export const AuthPage: React.FC<AuthPageProps> = ({ onAuthSuccess }) => {
  const [activeTab, setActiveTab] = useState<AuthTab>("login");

  // Form fields
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [token, setToken] = useState("");

  // Status & Feedback
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthWaiting, setOauthWaiting] = useState(false);
  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [oauthState, setOauthState] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Clear messages on tab change
  const handleTabChange = (tab: AuthTab) => {
    setActiveTab(tab);
    setErrorMsg(null);
    setSuccessMsg(null);
    setOauthWaiting(false);
    setOauthState(null);
  };

  // Listen for OAuth redirect sessions
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if ((event === "SIGNED_IN" || event === "USER_UPDATED" || event === "TOKEN_REFRESHED") && session?.user) {
        if (session.access_token) {
          backendService.setAuthToken(session.access_token);
        }
        const user: MikasaAuthUser = {
          id: session.user.id,
          username:
            session.user.user_metadata?.full_name ||
            session.user.user_metadata?.name ||
            session.user.email?.split("@")[0] ||
            "User",
          email: session.user.email || "",
          is_active: true,
          is_verified: Boolean(session.user.email_confirmed_at),
          created_at: Date.now() / 1000,
          avatar_url: session.user.user_metadata?.avatar_url || session.user.user_metadata?.picture || undefined,
          provider: session.user.app_metadata?.provider || "google",
        };
        onAuthSuccess(user);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [onAuthSuccess]);

  // Poll backend session when waiting for OAuth completion in browser
  useEffect(() => {
    if (!oauthWaiting) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let isCancelled = false;
    let inFlight = false;
    let shouldContinue = true;
    const startedAt = Date.now();
    const MAX_WAIT_MS = 5 * 60 * 1000; // 5 daqiqa

    const poll = async () => {
      if (isCancelled || inFlight) return;
      if (Date.now() - startedAt > MAX_WAIT_MS) {
        shouldContinue = false;
        setOauthWaiting(false);
        setOauthState(null);
        setSuccessMsg(null);
        setErrorMsg("Google sessiyasi kutish vaqti tugadi. Iltimos, qaytadan urinib ko'ring.");
        return;
      }

      inFlight = true;
      try {
        const res = await backendService.checkPendingOAuthSession(oauthState || undefined);
        if (isCancelled) return;

        if (res.fatal || res.serverUnreachable) {
          shouldContinue = false;
          setOauthWaiting(false);
          setOauthState(null);
          setSuccessMsg(null);
          setErrorMsg(res.error || "Google orqali kirishda xatolik yuz berdi.");
          return;
        }

        if (res.ok && res.session) {
          const { access_token, refresh_token, code } = res.session;
          let sessionUser: any = null;
          let activeToken = access_token || "";

          if (access_token) {
            setSuccessMsg("Hisobingiz tasdiqlandi! Tizimga kirilmoqda...");
            const { data, error: sessErr } = await supabase.auth.setSession({
              access_token,
              refresh_token: refresh_token || access_token,
            });
            if (sessErr) {
              shouldContinue = false;
              setOauthWaiting(false);
              setOauthState(null);
              setSuccessMsg(null);
              setErrorMsg("Google sessiyasi muddati tugagan yoki yaroqsiz. Qaytadan urinib ko'ring.");
              return;
            }
            sessionUser = data?.user;
            activeToken = data?.session?.access_token || access_token;
          } else if (code) {
            setSuccessMsg("Hisobingiz tasdiqlandi! Tizimga kirilmoqda...");
            const { data, error: codeErr } = await supabase.auth.exchangeCodeForSession(code);
            if (codeErr) {
              shouldContinue = false;
              setOauthWaiting(false);
              setOauthState(null);
              setSuccessMsg(null);
              setErrorMsg("Google avtorizatsiya kodini almashishda xatolik yuz berdi. Qaytadan urinib ko'ring.");
              return;
            }
            sessionUser = data?.user;
            activeToken = data?.session?.access_token || "";
          }

          if (activeToken) {
            backendService.setAuthToken(activeToken);
          }

          if (sessionUser && !isCancelled) {
            shouldContinue = false;
            const u: MikasaAuthUser = {
              id: sessionUser.id,
              username:
                sessionUser.user_metadata?.full_name ||
                sessionUser.user_metadata?.name ||
                sessionUser.email?.split("@")[0] ||
                "User",
              email: sessionUser.email || "",
              is_active: true,
              is_verified: true,
              created_at: Date.now() / 1000,
              avatar_url: sessionUser.user_metadata?.avatar_url || sessionUser.user_metadata?.picture || undefined,
              provider: sessionUser.app_metadata?.provider || "google",
            };
            setOauthWaiting(false);
            setOauthState(null);
            setTimeout(() => {
              onAuthSuccess(u);
            }, 400);
            return;
          }
        }
      } catch {
        // Continue polling
      } finally {
        inFlight = false;
        if (!isCancelled && shouldContinue) {
          timer = setTimeout(poll, 1200);
        }
      }
    };

    timer = setTimeout(poll, 1000);

    return () => {
      isCancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [oauthWaiting, oauthState, onAuthSuccess]);

  // Google OAuth handler
  const handleGoogleSignIn = async (forceRestartOrEvent?: boolean | React.MouseEvent<HTMLButtonElement>) => {
    const forceRestart = forceRestartOrEvent === true;
    if (loading || oauthLoading || (oauthWaiting && !forceRestart)) return;
    if (forceRestart) {
      setOauthWaiting(false);
    }
    setOauthLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.signInWithGoogle();
      if (!res.ok) {
        setErrorMsg(res.error || "Google orqali kirishda xatolik yuz berdi");
        setOauthLoading(false);
      } else if (res.url) {
        setOauthState(res.state || null);
        setOauthUrl(res.url);
        setOauthWaiting(true);
        setOauthLoading(false);
        setSuccessMsg("Brauzeringizda Google orqali tizimga kirishni tasdiqlang...");
        await backendService.openExternalUrl(res.url);
      } else {
        setErrorMsg("Google avtorizatsiya manzili olinmadi");
        setOauthLoading(false);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Google tizimiga ulanishda xatolik");
      setOauthLoading(false);
    }
  };


  // Password validation helper
  const isPasswordStrong = (pwd: string) => {
    return pwd.length >= 8 && /[a-zA-Z]/.test(pwd) && /[0-9]/.test(pwd);
  };

  // 1. LOGIN HANDLER
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || oauthLoading || oauthWaiting) return;
    if (!username.trim() || !password) {
      setErrorMsg("Foydalanuvchi nomi yoki email va parolni kiriting");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.login({
        username_or_email: username.trim(),
        password,
      });

      if (res.ok && res.user) {
        setSuccessMsg("Muvaffaqiyatli tizimga kirildi!");
        setTimeout(() => {
          onAuthSuccess(res.user!);
        }, 400);
      } else {
        setErrorMsg(res.error || "Kirishda xatolik yuz berdi");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Server bilan bog'lanishda xatolik");
    } finally {
      setLoading(false);
    }
  };

  // 2. REGISTER HANDLER
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || oauthLoading || oauthWaiting) return;
    if (!username.trim() || !password) {
      setErrorMsg("Foydalanuvchi nomi va parolni kiriting");
      return;
    }
    if (!isPasswordStrong(password)) {
      setErrorMsg("Parol kamida 8 ta belgidan iborat bo'lib, harf va raqam qatnashishi shart");
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg("Parollar bir-biriga mos kelmadi");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.register({
        username: username.trim(),
        email: email.trim() || undefined,
        password,
        confirm_password: confirmPassword,
      });

      if (res.ok && res.user) {
        setSuccessMsg("Hisob muvaffaqiyatli yaratildi!");
        setTimeout(() => {
          onAuthSuccess(res.user!);
        }, 500);
      } else {
        setErrorMsg(res.error || "Ro'yxatdan o'tishda xatolik");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Server bilan bog'lanishda xatolik");
    } finally {
      setLoading(false);
    }
  };

  // 3. FORGOT PASSWORD HANDLER
  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || oauthLoading || oauthWaiting) return;
    const target = email.trim() || username.trim();
    if (!target) {
      setErrorMsg("Email yoki foydalanuvchi nomingizni kiriting");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.forgotPassword(target);
      if (res.ok) {
        if (res.token) {
          setToken(res.token);
          setSuccessMsg(`${res.message || "Tiklash kodi yaratildi."} Qayta tiklash formasiga o'ting.`);
          setTimeout(() => {
            setActiveTab("reset");
          }, 1200);
        } else {
          setSuccessMsg(res.message || "Agar hisob mavjud bo'lsa, tiklash xabari yuborildi.");
        }
      } else {
        setErrorMsg(res.error || "So'rov yuborishda xatolik");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Server bilan bog'lanishda xatolik");
    } finally {
      setLoading(false);
    }
  };

  // 4. RESET PASSWORD HANDLER
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || oauthLoading || oauthWaiting) return;
    if (!token.trim()) {
      setErrorMsg("Tiklash tokenini kiriting");
      return;
    }
    if (!isPasswordStrong(password)) {
      setErrorMsg("Yangi parol kamida 8 ta belgidan iborat bo'lib, harf va raqam qatnashishi kerak");
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg("Yangi parollar mos kelmadi");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.resetPassword({
        token: token.trim(),
        new_password: password,
        confirm_password: confirmPassword,
      });

      if (res.ok) {
        setSuccessMsg(res.message || "Parol muvaffaqiyatli yangilandi! Endi kirishingiz mumkin.");
        setPassword("");
        setConfirmPassword("");
        setTimeout(() => {
          setActiveTab("login");
        }, 1200);
      } else {
        setErrorMsg(res.error || "Parolni yangilashda xatolik");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Server bilan bog'lanishda xatolik");
    } finally {
      setLoading(false);
    }
  };

  // 5. VERIFY EMAIL HANDLER
  const handleVerifyEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || oauthLoading || oauthWaiting) return;
    if (!token.trim()) {
      setErrorMsg("Tasdiqlash tokenini kiriting");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.verifyEmail(token.trim());
      if (res.ok) {
        setSuccessMsg(res.message || "Email manzilingiz muvaffaqiyatli tasdiqlandi!");
        setTimeout(() => {
          setActiveTab("login");
        }, 1200);
      } else {
        setErrorMsg(res.error || "Emailni tasdiqlashda xatolik");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Server bilan bog'lanishda xatolik");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        maxHeight: "100vh",
        width: "100%",
        backgroundColor: "var(--bg-darkest, #02060E)",
        color: "#F8FAFC",
        fontFamily: "var(--font-sans)",
        position: "relative",
        overflowY: "auto",
        overflowX: "hidden",
        padding: "64px 20px 32px 20px",
        boxSizing: "border-box",
      }}
    >
      {/* Misa v9.0 Ultra Glass Background & Micro-Grid */}
      <div className="misa-canvas-bg" />
      <div className="misa-grid-overlay" />

      {/* ═══ TOP CHROME HEADER (Native Window Drag & Controls) ═══ */}
      <header
        data-tauri-drag-region
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          height: "46px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 10px 0 18px",
          zIndex: 1000,
          userSelect: "none",
          background: "rgba(10, 14, 24, 0.65)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        }}
      >
        <div data-tauri-drag-region style={{ display: "flex", alignItems: "center", gap: "9px", cursor: "default" }}>
          <SparklesIcon size={16} color="#C04CFD" />
          <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#E2E8F0", letterSpacing: "0.04em", fontFamily: "var(--font-display)" }}>
            MISA AI
          </span>
        </div>
        <div data-tauri-drag-region style={{ flex: 1, height: "100%", cursor: "default" }} />
        <WindowControls />
      </header>

      {/* Atmospheric Glowing Cosmic Nebula Orbs */}
      <div
        style={{
          position: "absolute",
          top: "10%",
          left: "15%",
          width: "480px",
          height: "480px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(147, 3, 197, 0.24) 0%, rgba(192, 76, 253, 0.1) 50%, transparent 70%)",
          filter: "blur(90px)",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "10%",
          right: "15%",
          width: "520px",
          height: "520px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(192, 76, 253, 0.2) 0%, rgba(78, 222, 163, 0.08) 50%, transparent 70%)",
          filter: "blur(95px)",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />

      {/* Main Ultra Glass Card */}
      <div
        className="misa-ultra-glass"
        style={{
          width: "100%",
          maxWidth: "460px",
          background: "rgba(18, 22, 34, 0.62)",
          backdropFilter: "blur(32px) saturate(180%)",
          WebkitBackdropFilter: "blur(32px) saturate(180%)",
          border: "1px solid rgba(192, 76, 253, 0.24)",
          borderRadius: "24px",
          boxShadow: "0 24px 64px rgba(0, 0, 0, 0.65), 0 0 40px rgba(147, 3, 197, 0.16), inset 0 1px 0 rgba(255, 255, 255, 0.14)",
          padding: "36px 32px",
          position: "relative",
          zIndex: 10,
          margin: "auto",
        }}
      >
        {/* Header Branding */}
        <div style={{ textAlign: "center", marginBottom: "26px", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ marginBottom: "12px" }}>
            <MisaLogo size={42} showText={true} showBadge={true} />
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8" }}>
            Avtonom Intellektual Ish Maydoni & Masofaviy Boshqaruv
          </p>
        </div>

        {/* Tab Navigation Segmented Glass Control */}
        <div
          style={{
            display: "flex",
            background: "rgba(6, 10, 22, 0.6)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            borderRadius: "12px",
            padding: "4px",
            marginBottom: "24px",
            border: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <button
            type="button"
            onClick={() => handleTabChange("login")}
            style={{
              flex: 1,
              padding: "10px 0",
              border: activeTab === "login" ? "1px solid rgba(192, 76, 253, 0.45)" : "1px solid transparent",
              borderRadius: "9px",
              background: activeTab === "login" ? "linear-gradient(135deg, rgba(147, 3, 197, 0.35) 0%, rgba(192, 76, 253, 0.22) 100%)" : "transparent",
              color: activeTab === "login" ? "#FFFFFF" : "#94A3B8",
              fontSize: "13.5px",
              fontWeight: activeTab === "login" ? 700 : 500,
              cursor: "pointer",
              transition: "all 0.2s ease",
              boxShadow: activeTab === "login" ? "0 2px 12px rgba(147, 3, 197, 0.28)" : "none",
            }}
          >
            Kirish
          </button>
          <button
            type="button"
            onClick={() => handleTabChange("register")}
            style={{
              flex: 1,
              padding: "10px 0",
              border: activeTab === "register" ? "1px solid rgba(192, 76, 253, 0.45)" : "1px solid transparent",
              borderRadius: "9px",
              background: activeTab === "register" ? "linear-gradient(135deg, rgba(147, 3, 197, 0.35) 0%, rgba(192, 76, 253, 0.22) 100%)" : "transparent",
              color: activeTab === "register" ? "#FFFFFF" : "#94A3B8",
              fontSize: "13.5px",
              fontWeight: activeTab === "register" ? 700 : 500,
              cursor: "pointer",
              transition: "all 0.2s ease",
              boxShadow: activeTab === "register" ? "0 2px 12px rgba(147, 3, 197, 0.28)" : "none",
            }}
          >
            Ro'yxatdan o'tish
          </button>
        </div>

        {/* Supabase Unconfigured Warning Banner */}
        {!isSupabaseConfigured && (
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
              padding: "12px 14px",
              borderRadius: "10px",
              background: "rgba(245, 158, 11, 0.12)",
              border: "1px solid rgba(245, 158, 11, 0.3)",
              color: "#FDE68A",
              fontSize: "12.5px",
              marginBottom: "18px",
              lineHeight: 1.45,
            }}
          >
            <AlertTriangleIcon size={18} color="#F59E0B" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, marginBottom: "2px" }}>Supabase sozlanmagan</div>
              <div>
                Tizimga kirish yoki ro'yxatdan o'tish uchun <code style={{ background: "rgba(0,0,0,0.3)", padding: "1px 4px", borderRadius: "4px" }}>Misa/.env</code> faylida <code style={{ background: "rgba(0,0,0,0.3)", padding: "1px 4px", borderRadius: "4px" }}>VITE_SUPABASE_URL</code> va <code style={{ background: "rgba(0,0,0,0.3)", padding: "1px 4px", borderRadius: "4px" }}>VITE_SUPABASE_PUBLISHABLE_KEY</code> sozlamalarini kiriting.
              </div>
            </div>
          </div>
        )}

        {/* Alerts / Feedback */}
        {errorMsg && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "12px 14px",
              borderRadius: "10px",
              background: "rgba(239, 68, 68, 0.12)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "#FCA5A5",
              fontSize: "13px",
              marginBottom: "18px",
              lineHeight: 1.4,
            }}
          >
            <AlertTriangleIcon size={18} color="#EF4444" />
            <span style={{ flex: 1 }}>{errorMsg}</span>
          </div>
        )}

        {successMsg && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "12px 14px",
              borderRadius: "10px",
              background: "rgba(16, 185, 129, 0.12)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              color: "#6EE7B7",
              fontSize: "13px",
              marginBottom: "18px",
              lineHeight: 1.4,
            }}
          >
            <CheckIcon size={18} color="#10B981" />
            <span style={{ flex: 1 }}>{successMsg}</span>
          </div>
        )}

        {/* OAUTH WAITING CARD */}
        {oauthWaiting ? (
          <div
            style={{
              textAlign: "center",
              padding: "10px 4px 8px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "16px",
            }}
          >
            <div
              style={{
                width: "64px",
                height: "64px",
                borderRadius: "18px",
                background: "linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%)",
                border: "1px solid rgba(255, 255, 255, 0.18)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 30px rgba(16, 185, 129, 0.25)",
              }}
            >
              <GoogleIcon size={32} />
            </div>

            <div>
              <h3 style={{ margin: "0 0 6px", fontSize: "17px", fontWeight: 700, color: "#FFFFFF" }}>
                Google orqali kirish kutilmoqda...
              </h3>
              <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
                Tizimga kirish sahifasi tashqi brauzeringizda ochildi.
                <br />
                Google hisobingizni tanlang va ruxsat bering.
              </p>
            </div>

            <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px" }}>
              {oauthUrl && (
                <button
                  type="button"
                  onClick={() => handleGoogleSignIn(true)}
                  style={{
                    width: "100%",
                    padding: "11px 16px",
                    background: "rgba(255, 255, 255, 0.09)",
                    border: "1px solid rgba(255, 255, 255, 0.2)",
                    borderRadius: "10px",
                    color: "#F1F5F9",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.15)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.09)")}
                >
                  Brauzerda qayta ochish
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  setOauthWaiting(false);
                  setErrorMsg(null);
                  setSuccessMsg(null);
                }}
                style={{
                  width: "100%",
                  padding: "9px 16px",
                  background: "transparent",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "10px",
                  color: "#94A3B8",
                  fontSize: "12.5px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "rgba(239, 68, 68, 0.4)";
                  e.currentTarget.style.color = "#F87171";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.1)";
                  e.currentTarget.style.color = "#94A3B8";
                }}
              >
                Bekor qilish
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* TAB 1: LOGIN FORM */}
            {activeTab === "login" && (
          <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Google OAuth Button */}
            <button
              type="button"
              role="button"
              aria-label="Google orqali tizimga kirish"
              onClick={handleGoogleSignIn}
              disabled={loading || oauthLoading || oauthWaiting}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "11px",
                padding: "12px 18px",
                background: "rgba(255, 255, 255, 0.08)",
                backdropFilter: "blur(14px)",
                WebkitBackdropFilter: "blur(14px)",
                border: "1px solid rgba(255, 255, 255, 0.18)",
                borderRadius: "12px",
                color: "#F8FAFC",
                fontSize: "13.5px",
                fontWeight: 600,
                cursor: loading || oauthLoading || oauthWaiting ? "not-allowed" : "pointer",
                transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                opacity: loading || oauthLoading || oauthWaiting ? 0.65 : 1,
                boxShadow: "0 4px 16px rgba(0, 0, 0, 0.3)",
              }}
              onMouseEnter={(e) => {
                if (!loading && !oauthLoading && !oauthWaiting) {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.14)";
                  e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.45)";
                  e.currentTarget.style.transform = "translateY(-1.5px)";
                  e.currentTarget.style.boxShadow = "0 6px 20px rgba(147, 3, 197, 0.28)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.08)";
                e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.18)";
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.3)";
              }}
            >
              <GoogleIcon size={19} />
              <span>{oauthLoading ? "Google orqali ulanilmoqda..." : "Google bilan davom etish"}</span>
            </button>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                margin: "4px 0",
                color: "#64748B",
                fontSize: "12px",
              }}
            >
              <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.1)" }} />
              <span>yoki login va parol</span>
              <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.1)" }} />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Foydalanuvchi nomi yoki Email
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin yoki user@example.com"
                  autoComplete="username"
                  required
                  style={{
                    width: "100%",
                    padding: "12px 14px 12px 42px",
                    background: "rgba(8, 14, 28, 0.65)",
                    backdropFilter: "blur(12px)",
                    WebkitBackdropFilter: "blur(12px)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    borderRadius: "12px",
                    color: "#FFFFFF",
                    fontSize: "14px",
                    outline: "none",
                    boxSizing: "border-box",
                    transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#C04CFD";
                    e.target.style.boxShadow = "0 0 0 3px rgba(192, 76, 253, 0.22)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                    e.target.style.boxShadow = "none";
                  }}
                />
                <div style={{ position: "absolute", left: "14px", top: "13px", opacity: 0.55, pointerEvents: "none" }}>
                  <UserIcon size={16} />
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                  Parol
                </label>
                <button
                  type="button"
                  onClick={() => handleTabChange("forgot")}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    color: "#E8B3FF",
                    fontSize: "12px",
                    fontWeight: 500,
                    cursor: "pointer",
                  }}
                >
                  Parolni unutdingizmi?
                </button>
              </div>
              <div style={{ position: "relative" }}>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                  style={{
                    width: "100%",
                    padding: "12px 14px 12px 42px",
                    background: "rgba(8, 14, 28, 0.65)",
                    backdropFilter: "blur(12px)",
                    WebkitBackdropFilter: "blur(12px)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    borderRadius: "12px",
                    color: "#FFFFFF",
                    fontSize: "14px",
                    outline: "none",
                    boxSizing: "border-box",
                    transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#C04CFD";
                    e.target.style.boxShadow = "0 0 0 3px rgba(192, 76, 253, 0.22)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                    e.target.style.boxShadow = "none";
                  }}
                />
                <div style={{ position: "absolute", left: "14px", top: "13px", opacity: 0.55, pointerEvents: "none" }}>
                  <KeyIcon size={16} />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || oauthLoading}
              style={{
                marginTop: "8px",
                padding: "13px 20px",
                background: "linear-gradient(135deg, #9303C5 0%, #C04CFD 60%, #7C3AED 100%)",
                border: "none",
                borderRadius: "12px",
                color: "#FFFFFF",
                fontSize: "14.5px",
                fontWeight: 700,
                cursor: loading || oauthLoading ? "default" : "pointer",
                boxShadow: "0 4px 20px rgba(147, 3, 197, 0.4)",
                transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                opacity: loading || oauthLoading ? 0.7 : 1,
              }}
              onMouseEnter={(e) => {
                if (!loading && !oauthLoading) {
                  e.currentTarget.style.transform = "translateY(-1px)";
                  e.currentTarget.style.boxShadow = "0 6px 24px rgba(192, 76, 253, 0.5)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 20px rgba(147, 3, 197, 0.4)";
              }}
            >
              {loading ? "Kirilmoqda..." : "Tizimga kirish"}
            </button>
          </form>
        )}

        {/* TAB 2: REGISTER FORM */}
        {activeTab === "register" && (
          <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {/* Google OAuth Button */}
            <button
              type="button"
              role="button"
              aria-label="Google orqali ro'yxatdan o'tish"
              onClick={handleGoogleSignIn}
              disabled={loading || oauthLoading || oauthWaiting}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "11px",
                padding: "12px 18px",
                background: "rgba(255, 255, 255, 0.08)",
                backdropFilter: "blur(14px)",
                WebkitBackdropFilter: "blur(14px)",
                border: "1px solid rgba(255, 255, 255, 0.18)",
                borderRadius: "12px",
                color: "#F8FAFC",
                fontSize: "13.5px",
                fontWeight: 600,
                cursor: loading || oauthLoading || oauthWaiting ? "not-allowed" : "pointer",
                transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                opacity: loading || oauthLoading || oauthWaiting ? 0.65 : 1,
                boxShadow: "0 4px 16px rgba(0, 0, 0, 0.3)",
              }}
              onMouseEnter={(e) => {
                if (!loading && !oauthLoading && !oauthWaiting) {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.14)";
                  e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.45)";
                  e.currentTarget.style.transform = "translateY(-1.5px)";
                  e.currentTarget.style.boxShadow = "0 6px 20px rgba(147, 3, 197, 0.28)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.08)";
                e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.18)";
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 16px rgba(0, 0, 0, 0.3)";
              }}
            >
              <GoogleIcon size={19} />
              <span>{oauthLoading ? "Google orqali ulanilmoqda..." : "Google bilan davom etish"}</span>
            </button>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                margin: "2px 0",
                color: "#64748B",
                fontSize: "12px",
              }}
            >
              <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.1)" }} />
              <span>yoki yangi akkaunt ochish</span>
              <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.1)" }} />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Foydalanuvchi nomi
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="masalan: sherzod_dev"
                  autoComplete="username"
                  required
                  style={{
                    width: "100%",
                    padding: "11px 14px 11px 40px",
                    background: "rgba(8, 14, 28, 0.65)",
                    backdropFilter: "blur(12px)",
                    WebkitBackdropFilter: "blur(12px)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    borderRadius: "12px",
                    color: "#FFFFFF",
                    fontSize: "13.5px",
                    outline: "none",
                    boxSizing: "border-box",
                    transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#C04CFD";
                    e.target.style.boxShadow = "0 0 0 3px rgba(192, 76, 253, 0.22)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                    e.target.style.boxShadow = "none";
                  }}
                />
                <div style={{ position: "absolute", left: "13px", top: "12px", opacity: 0.55, pointerEvents: "none" }}>
                  <UserIcon size={16} />
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Email manzil (ixtiyoriy)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                autoComplete="email"
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  background: "rgba(8, 14, 28, 0.65)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "13.5px",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#C04CFD";
                  e.target.style.boxShadow = "0 0 0 3px rgba(192, 76, 253, 0.22)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Parol (kamida 8 belgi, harf va raqam)
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  required
                  style={{
                    width: "100%",
                    padding: "11px 14px 11px 40px",
                    background: "rgba(8, 14, 28, 0.65)",
                    backdropFilter: "blur(12px)",
                    WebkitBackdropFilter: "blur(12px)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    borderRadius: "12px",
                    color: "#FFFFFF",
                    fontSize: "13.5px",
                    outline: "none",
                    boxSizing: "border-box",
                    transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#C04CFD";
                    e.target.style.boxShadow = "0 0 0 3px rgba(192, 76, 253, 0.22)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                    e.target.style.boxShadow = "none";
                  }}
                />
                <div style={{ position: "absolute", left: "13px", top: "12px", opacity: 0.55, pointerEvents: "none" }}>
                  <KeyIcon size={16} />
                </div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Parolni tasdiqlang
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                required
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  background: "rgba(8, 14, 28, 0.65)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "13.5px",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#C04CFD";
                  e.target.style.boxShadow = "0 0 0 3px rgba(192, 76, 253, 0.22)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading || oauthLoading}
              style={{
                marginTop: "8px",
                padding: "13px 20px",
                background: "linear-gradient(135deg, #9303C5 0%, #C04CFD 60%, #7C3AED 100%)",
                border: "none",
                borderRadius: "12px",
                color: "#FFFFFF",
                fontSize: "14.5px",
                fontWeight: 700,
                cursor: loading || oauthLoading ? "default" : "pointer",
                boxShadow: "0 4px 20px rgba(147, 3, 197, 0.4)",
                transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                opacity: loading || oauthLoading ? 0.7 : 1,
              }}
              onMouseEnter={(e) => {
                if (!loading && !oauthLoading) {
                  e.currentTarget.style.transform = "translateY(-1px)";
                  e.currentTarget.style.boxShadow = "0 6px 24px rgba(192, 76, 253, 0.5)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 20px rgba(147, 3, 197, 0.4)";
              }}
            >
              {loading ? "Yaratilmoqda..." : "Hisob yaratish"}
            </button>
          </form>
        )}

        {/* TAB 3: FORGOT PASSWORD FORM */}
        {activeTab === "forgot" && (
          <form onSubmit={handleForgotPassword} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
              Hisobingizga tegishli email manzil yoki foydalanuvchi nomini kiriting. Biz parolni tiklash kodini jo'natamiz.
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Email yoki Foydalanuvchi nomi
              </label>
              <input
                type="text"
                value={email || username}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setUsername(e.target.value);
                }}
                placeholder="user@example.com"
                required
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  background: "rgba(8, 14, 28, 0.65)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "13.5px",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#10B981";
                  e.target.style.boxShadow = "0 0 0 3px rgba(16, 185, 129, 0.22)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: "4px",
                padding: "13px 20px",
                background: "linear-gradient(135deg, #059669 0%, #10B981 100%)",
                border: "none",
                borderRadius: "12px",
                color: "#FFFFFF",
                fontSize: "14.5px",
                fontWeight: 700,
                cursor: loading ? "default" : "pointer",
                boxShadow: "0 4px 20px rgba(16, 185, 129, 0.35)",
                transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                opacity: loading ? 0.7 : 1,
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.transform = "translateY(-1px)";
                  e.currentTarget.style.boxShadow = "0 6px 24px rgba(16, 185, 129, 0.45)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 20px rgba(16, 185, 129, 0.35)";
              }}
            >
              {loading ? "Yuborilmoqda..." : "Tiklash kodini yuborish"}
            </button>

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
              <button
                type="button"
                onClick={() => handleTabChange("login")}
                style={{
                  background: "none",
                  border: "none",
                  color: "#94A3B8",
                  fontSize: "12.5px",
                  cursor: "pointer",
                  transition: "color 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#F1F5F9")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#94A3B8")}
              >
                ← Kirishga qaytish
              </button>
              <button
                type="button"
                onClick={() => handleTabChange("reset")}
                style={{
                  background: "none",
                  border: "none",
                  color: "#34D399",
                  fontSize: "12.5px",
                  cursor: "pointer",
                  fontWeight: 600,
                  transition: "color 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#6EE7B7")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#34D399")}
              >
                Kodingiz bormi? Tiklash →
              </button>
            </div>
          </form>
        )}

        {/* TAB 4: RESET PASSWORD FORM */}
        {activeTab === "reset" && (
          <form onSubmit={handleResetPassword} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
              Yuborilgan bir martalik tiklash tokeni va yangi parolingizni kiriting.
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Tiklash tokeni
              </label>
              <input
                type="text"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="masalan: 1a2b3c4d..."
                required
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  background: "rgba(8, 14, 28, 0.65)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "13.5px",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#10B981";
                  e.target.style.boxShadow = "0 0 0 3px rgba(16, 185, 129, 0.22)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Yangi parol
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  background: "rgba(8, 14, 28, 0.65)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "13.5px",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#10B981";
                  e.target.style.boxShadow = "0 0 0 3px rgba(16, 185, 129, 0.22)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Yangi parolni tasdiqlang
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  background: "rgba(8, 14, 28, 0.65)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "13.5px",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#10B981";
                  e.target.style.boxShadow = "0 0 0 3px rgba(16, 185, 129, 0.22)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: "6px",
                padding: "13px 20px",
                background: "linear-gradient(135deg, #059669 0%, #10B981 100%)",
                border: "none",
                borderRadius: "12px",
                color: "#FFFFFF",
                fontSize: "14.5px",
                fontWeight: 700,
                cursor: loading ? "default" : "pointer",
                boxShadow: "0 4px 20px rgba(16, 185, 129, 0.35)",
                transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                opacity: loading ? 0.7 : 1,
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.transform = "translateY(-1px)";
                  e.currentTarget.style.boxShadow = "0 6px 24px rgba(16, 185, 129, 0.45)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 20px rgba(16, 185, 129, 0.35)";
              }}
            >
              {loading ? "Yangilanmoqda..." : "Parolni yangilash"}
            </button>

            <button
              type="button"
              onClick={() => handleTabChange("login")}
              style={{
                background: "none",
                border: "none",
                color: "#94A3B8",
                fontSize: "12.5px",
                cursor: "pointer",
                marginTop: "4px",
                transition: "color 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#F1F5F9")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#94A3B8")}
            >
              ← Kirishga qaytish
            </button>
          </form>
        )}

        {/* TAB 5: VERIFY EMAIL FORM */}
        {activeTab === "verify" && (
          <form onSubmit={handleVerifyEmail} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
              Email manzilingizga yuborilgan tasdiqlash tokenini kiriting.
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                Tasdiqlash tokeni
              </label>
              <input
                type="text"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="masalan: 1a2b3c4d..."
                required
                style={{
                  width: "100%",
                  padding: "11px 14px",
                  background: "rgba(8, 14, 28, 0.65)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "13.5px",
                  outline: "none",
                  boxSizing: "border-box",
                  transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = "#10B981";
                  e.target.style.boxShadow = "0 0 0 3px rgba(16, 185, 129, 0.22)";
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.target.style.boxShadow = "none";
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: "4px",
                padding: "13px 20px",
                background: "linear-gradient(135deg, #059669 0%, #10B981 100%)",
                border: "none",
                borderRadius: "12px",
                color: "#FFFFFF",
                fontSize: "14.5px",
                fontWeight: 700,
                cursor: loading ? "default" : "pointer",
                boxShadow: "0 4px 20px rgba(16, 185, 129, 0.35)",
                transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
                opacity: loading ? 0.7 : 1,
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.transform = "translateY(-1px)";
                  e.currentTarget.style.boxShadow = "0 6px 24px rgba(16, 185, 129, 0.45)";
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 4px 20px rgba(16, 185, 129, 0.35)";
              }}
            >
              {loading ? "Tasdiqlanmoqda..." : "Emailni tasdiqlash"}
            </button>

            <button
              type="button"
              onClick={() => handleTabChange("login")}
              style={{
                background: "none",
                border: "none",
                color: "#94A3B8",
                fontSize: "12.5px",
                cursor: "pointer",
                marginTop: "4px",
                transition: "color 0.15s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#F1F5F9")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#94A3B8")}
            >
              ← Kirishga qaytish
            </button>
          </form>
        )}
        </>
        )}

        {/* Footer info */}
        <div
          style={{
            marginTop: "26px",
            paddingTop: "18px",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            fontSize: "12px",
            color: "#64748B",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <ShieldIcon size={14} color="#4EDEA3" />
            <span style={{ color: "#4EDEA3", fontWeight: 500 }}>Secured by Supabase Auth</span>
          </div>
          <span style={{ color: "#94A3B8" }}>Ultra Glass Edition</span>
        </div>
      </div>
    </div>
  );
};
