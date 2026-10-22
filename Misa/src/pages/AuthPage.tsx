// ========== AuthPage.tsx ==========
// Misa AI v9.3 — Multi-Provider Authentication & Ultra Glass Portal
// Support for Google, GitHub, Telegram & Direct Email Auth with Fluid Micro-Animations

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
  CheckIcon,
  AlertTriangleIcon,
  GoogleIcon,
  GithubIcon,
  TelegramColorIcon,
  MailIcon,
  LockIcon,
  EyeIcon,
  EyeOffIcon,
  GlobeIcon,
} from "../components/icons/Icons";
import { MisaLogo } from "../components/MisaLogo";
import { WindowControls } from "../components/WindowControls";
import { ServerDiagnosticModal } from "../components/ServerDiagnosticModal";

interface AuthPageProps {
  onAuthSuccess: (user: MikasaAuthUser) => void;
}

type AuthTab = "login" | "register" | "forgot" | "reset" | "verify";

export const AuthPage: React.FC<AuthPageProps> = ({ onAuthSuccess }) => {
  const [activeTab, setActiveTab] = useState<AuthTab>("login");

  // Form fields
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [token, setToken] = useState("");

  // Password visibility
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Status & Feedback
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthWaiting, setOauthWaiting] = useState(false);
  const [oauthProvider, setOauthProvider] = useState<"google" | "github">("google");
  const [oauthUrl, setOauthUrl] = useState<string | null>(null);
  const [oauthState, setOauthState] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [diagModalOpen, setDiagModalOpen] = useState(false);

  // Telegram modal state
  const [telegramModalOpen, setTelegramModalOpen] = useState(false);
  const [telegramInput, setTelegramInput] = useState("");
  const [telegramLoading, setTelegramLoading] = useState(false);

  // Clear messages on tab change
  const handleTabChange = (tab: AuthTab) => {
    setActiveTab(tab);
    setErrorMsg(null);
    setSuccessMsg(null);
    setOauthWaiting(false);
    setOauthState(null);
    setTelegramModalOpen(false);
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
          provider: session.user.app_metadata?.provider || "oauth",
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
    const MAX_WAIT_MS = 5 * 60 * 1000; // 5 minutes

    const providerName = oauthProvider === "google" ? "Google" : "GitHub";

    const poll = async () => {
      if (isCancelled || inFlight) return;
      if (Date.now() - startedAt > MAX_WAIT_MS) {
        shouldContinue = false;
        setOauthWaiting(false);
        setOauthState(null);
        setSuccessMsg(null);
        setErrorMsg(`${providerName} sessiyasi kutish vaqti tugadi. Iltimos, qaytadan urinib ko'ring.`);
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
          setErrorMsg(res.error || `${providerName} orqali kirishda xatolik yuz berdi.`);
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
              setErrorMsg(`${providerName} sessiyasi muddati tugagan yoki yaroqsiz. Qaytadan urinib ko'ring.`);
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
              setErrorMsg(`${providerName} avtorizatsiya kodini almashishda xatolik yuz berdi. Qaytadan urinib ko'ring.`);
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
              provider: sessionUser.app_metadata?.provider || oauthProvider,
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
  }, [oauthWaiting, oauthState, oauthProvider, onAuthSuccess]);

  // Unified OAuth handler (Google & GitHub)
  const handleOAuthSignIn = async (provider: "google" | "github", forceRestart?: boolean) => {
    if (loading || oauthLoading || (oauthWaiting && !forceRestart)) return;
    if (forceRestart) {
      setOauthWaiting(false);
    }
    setOauthLoading(true);
    setOauthProvider(provider);
    setErrorMsg(null);
    setSuccessMsg(null);

    const providerName = provider === "google" ? "Google" : "GitHub";

    try {
      const res = await backendService.signInWithOAuthProvider(provider);
      if (!res.ok) {
        setErrorMsg(res.error || `${providerName} orqali kirishda xatolik yuz berdi`);
        setOauthLoading(false);
      } else if (res.url) {
        setOauthState(res.state || null);
        setOauthUrl(res.url);
        setOauthWaiting(true);
        setOauthLoading(false);
        setSuccessMsg(`Brauzeringizda ${providerName} orqali tizimga kirishni tasdiqlang...`);
        await backendService.openExternalUrl(res.url);
      } else {
        setErrorMsg(`${providerName} avtorizatsiya manzili olinmadi`);
        setOauthLoading(false);
      }
    } catch (err: any) {
      setErrorMsg(err.message || `${providerName} tizimiga ulanishda xatolik`);
      setOauthLoading(false);
    }
  };

  // Telegram Quick Link / Bot Open
  const handleOpenTelegramBot = async () => {
    try {
      await backendService.openExternalUrl("https://t.me/Misa_ai_agent_bot?start=auth");
      setSuccessMsg("Telegram bot (@Misa_ai_agent_bot) ochildi. Bot orqali tasdiqlang.");
    } catch {
      window.open("https://t.me/Misa_ai_agent_bot?start=auth", "_blank");
    }
  };

  // Telegram Quick Sign-In by Username or ID
  const handleTelegramSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!telegramInput.trim()) {
      setErrorMsg("Telegram @username yoki telefon raqamingizni kiriting");
      return;
    }
    setTelegramLoading(true);
    setErrorMsg(null);

    try {
      const res = await backendService.loginWithTelegram({
        username: telegramInput.trim(),
        first_name: firstName.trim() || undefined,
      });

      if (res.ok && res.user) {
        setSuccessMsg("Telegram orqali muvaffaqiyatli kirildi!");
        setTimeout(() => {
          onAuthSuccess(res.user!);
        }, 400);
      } else {
        setErrorMsg(res.error || "Telegram orqali kirishda xatolik");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Telegram bilan bog'lanishda xatolik");
    } finally {
      setTelegramLoading(false);
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
    if (!email.trim() || !password) {
      setErrorMsg("Email manzil va parolni kiriting");
      return;
    }

    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.login({
        username_or_email: email.trim(),
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

  // 2. REGISTER HANDLER (No username asked, derived seamlessly)
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading || oauthLoading || oauthWaiting) return;
    if (!email.trim() || !password) {
      setErrorMsg("Email manzil va parolni kiriting");
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

    const derivedUsername =
      email.trim().split("@")[0].replace(/[^a-zA-Z0-9_-]/g, "") ||
      (firstName.trim() ? firstName.trim().toLowerCase().replace(/[^a-zA-Z0-9_-]/g, "") : `user_${Date.now().toString().slice(-4)}`);

    try {
      const res = await backendService.register({
        username: derivedUsername,
        first_name: firstName.trim() || undefined,
        last_name: lastName.trim() || undefined,
        email: email.trim(),
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
    const target = email.trim();
    if (!target) {
      setErrorMsg("Email manzilingizni kiriting");
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
      });

      if (res.ok) {
        setSuccessMsg("Parol muvaffaqiyatli yangilandi! Tizimga kirishingiz mumkin.");
        setTimeout(() => {
          setPassword("");
          setConfirmPassword("");
          setToken("");
          setActiveTab("login");
        }, 1500);
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
        setSuccessMsg("Email muvaffaqiyatli tasdiqlandi! Endi tizimga kirishingiz mumkin.");
        setTimeout(() => {
          setToken("");
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
      {/* Dynamic Keyframe Animations */}
      <style>{`
        @keyframes authEntrance {
          0% {
            opacity: 0;
            transform: translateY(22px) scale(0.975);
          }
          100% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        @keyframes nebulaPulseA {
          0%, 100% {
            transform: translate(0, 0) scale(1);
            opacity: 0.22;
          }
          50% {
            transform: translate(30px, -20px) scale(1.12);
            opacity: 0.35;
          }
        }
        @keyframes nebulaPulseB {
          0%, 100% {
            transform: translate(0, 0) scale(1);
            opacity: 0.20;
          }
          50% {
            transform: translate(-30px, 25px) scale(1.1);
            opacity: 0.32;
          }
        }
        @keyframes authBtnGlow {
          0%, 100% {
            box-shadow: 0 4px 20px rgba(147, 3, 197, 0.45);
          }
          50% {
            box-shadow: 0 6px 28px rgba(192, 76, 253, 0.65);
          }
        }
        @keyframes authSpin {
          to { transform: rotate(360deg); }
        }
        .misa-auth-input {
          width: 100%;
          background: rgba(8, 14, 28, 0.72);
          backdrop-filter: blur(14px);
          -webkit-backdrop-filter: blur(14px);
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 12px;
          color: #FFFFFF;
          font-size: 13.5px;
          outline: none;
          box-sizing: border-box;
          transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .misa-auth-input:focus {
          border-color: #C04CFD !important;
          background: rgba(14, 20, 38, 0.85) !important;
          box-shadow: 0 0 0 3px rgba(192, 76, 253, 0.25), 0 0 16px rgba(147, 3, 197, 0.2) !important;
        }
        .misa-social-btn {
          flex: 1;
          display: flex;
          align-items: center;
          justifyContent: center;
          gap: 8px;
          padding: 11px 12px;
          background: rgba(255, 255, 255, 0.05);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.12);
          border-radius: 12px;
          color: #F8FAFC;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
          box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
        }
        .misa-social-btn:hover {
          background: rgba(255, 255, 255, 0.12);
          border-color: rgba(192, 76, 253, 0.45);
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(147, 3, 197, 0.28);
        }
        .misa-social-btn:active {
          transform: translateY(0);
        }
      `}</style>

      {/* Misa v9.3 Canvas & Grid Backdrop */}
      <div className="misa-canvas-bg" />
      <div className="misa-grid-overlay" />

      {/* ═══ TOP CHROME HEADER ═══ */}
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
          top: "8%",
          left: "12%",
          width: "500px",
          height: "500px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(147, 3, 197, 0.3) 0%, rgba(192, 76, 253, 0.12) 50%, transparent 70%)",
          filter: "blur(90px)",
          pointerEvents: "none",
          zIndex: 1,
          animation: "nebulaPulseA 12s ease-in-out infinite",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "8%",
          right: "12%",
          width: "540px",
          height: "540px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(192, 76, 253, 0.24) 0%, rgba(36, 161, 222, 0.12) 50%, transparent 70%)",
          filter: "blur(95px)",
          pointerEvents: "none",
          zIndex: 1,
          animation: "nebulaPulseB 14s ease-in-out infinite",
        }}
      />

      {/* Main Ultra Glass Portal Card */}
      <div
        className="misa-ultra-glass"
        style={{
          width: "100%",
          maxWidth: "470px",
          background: "rgba(16, 20, 32, 0.68)",
          backdropFilter: "blur(36px) saturate(190%)",
          WebkitBackdropFilter: "blur(36px) saturate(190%)",
          border: "1px solid rgba(192, 76, 253, 0.28)",
          borderRadius: "26px",
          boxShadow: "0 28px 72px rgba(0, 0, 0, 0.72), 0 0 45px rgba(147, 3, 197, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.15)",
          padding: "36px 32px",
          position: "relative",
          zIndex: 10,
          margin: "auto",
          animation: "authEntrance 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        }}
      >
        {/* Header Branding */}
        <div style={{ textAlign: "center", marginBottom: "24px", display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ marginBottom: "12px", filter: "drop-shadow(0 0 16px rgba(192, 76, 253, 0.35))" }}>
            <MisaLogo size={46} showText={true} showBadge={true} />
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8", letterSpacing: "0.01em" }}>
            Avtonom Intellektual Ish Maydoni & Masofaviy Boshqaruv
          </p>
        </div>

        {/* Tab Navigation Segmented Glass Control */}
        <div
          style={{
            display: "flex",
            background: "rgba(6, 10, 22, 0.65)",
            backdropFilter: "blur(16px)",
            WebkitBackdropFilter: "blur(16px)",
            borderRadius: "14px",
            padding: "4px",
            marginBottom: "22px",
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
              borderRadius: "11px",
              background: activeTab === "login" ? "linear-gradient(135deg, rgba(147, 3, 197, 0.4) 0%, rgba(192, 76, 253, 0.25) 100%)" : "transparent",
              color: activeTab === "login" ? "#FFFFFF" : "#94A3B8",
              fontSize: "13.5px",
              fontWeight: activeTab === "login" ? 700 : 500,
              cursor: "pointer",
              transition: "all 0.22s ease",
              boxShadow: activeTab === "login" ? "0 2px 14px rgba(147, 3, 197, 0.32)" : "none",
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
              borderRadius: "11px",
              background: activeTab === "register" ? "linear-gradient(135deg, rgba(147, 3, 197, 0.4) 0%, rgba(192, 76, 253, 0.25) 100%)" : "transparent",
              color: activeTab === "register" ? "#FFFFFF" : "#94A3B8",
              fontSize: "13.5px",
              fontWeight: activeTab === "register" ? 700 : 500,
              cursor: "pointer",
              transition: "all 0.22s ease",
              boxShadow: activeTab === "register" ? "0 2px 14px rgba(147, 3, 197, 0.32)" : "none",
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
              borderRadius: "12px",
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
                Tizimga kirish uchun <code style={{ background: "rgba(0,0,0,0.3)", padding: "1px 4px", borderRadius: "4px" }}>Misa/.env</code> faylida <code style={{ background: "rgba(0,0,0,0.3)", padding: "1px 4px", borderRadius: "4px" }}>VITE_SUPABASE_URL</code> sozlamasini kiriting.
              </div>
            </div>
          </div>
        )}

        {/* Alerts / Feedback */}
        {errorMsg && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              padding: "12px 14px",
              borderRadius: "12px",
              background: "rgba(239, 68, 68, 0.14)",
              border: "1px solid rgba(239, 68, 68, 0.32)",
              color: "#FCA5A5",
              fontSize: "13px",
              marginBottom: "18px",
              lineHeight: 1.4,
              animation: "authEntrance 0.3s ease",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <AlertTriangleIcon size={18} color="#EF4444" />
              <span style={{ flex: 1 }}>{errorMsg}</span>
            </div>
            {(errorMsg.toLowerCase().includes("server") ||
              errorMsg.toLowerCase().includes("ulanib") ||
              errorMsg.toLowerCase().includes("tarmoq") ||
              errorMsg.toLowerCase().includes("aloqa")) && (
              <button
                type="button"
                onClick={() => setDiagModalOpen(true)}
                style={{
                  alignSelf: "flex-start",
                  background: "rgba(192, 76, 253, 0.22)",
                  border: "1px solid rgba(192, 76, 253, 0.5)",
                  borderRadius: "8px",
                  padding: "5px 12px",
                  color: "#FFFFFF",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  transition: "all 0.15s ease",
                }}
              >
                <span>🔍 Server Diagnostikasi & Sozlamalar</span>
              </button>
            )}
          </div>
        )}

        {successMsg && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "12px 14px",
              borderRadius: "12px",
              background: "rgba(16, 185, 129, 0.14)",
              border: "1px solid rgba(16, 185, 129, 0.32)",
              color: "#6EE7B7",
              fontSize: "13px",
              marginBottom: "18px",
              lineHeight: 1.4,
              animation: "authEntrance 0.3s ease",
            }}
          >
            <CheckIcon size={18} color="#10B981" />
            <span style={{ flex: 1 }}>{successMsg}</span>
          </div>
        )}

        {/* ═══ OAUTH WAITING VIEW ═══ */}
        {oauthWaiting ? (
          <div
            style={{
              textAlign: "center",
              padding: "12px 4px 8px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "18px",
              animation: "authEntrance 0.3s ease",
            }}
          >
            <div
              style={{
                width: "68px",
                height: "68px",
                borderRadius: "20px",
                background: "linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.03) 100%)",
                border: "1px solid rgba(255, 255, 255, 0.2)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 35px rgba(192, 76, 253, 0.35)",
                position: "relative",
              }}
            >
              {oauthProvider === "google" ? (
                <GoogleIcon size={34} />
              ) : (
                <GithubIcon size={34} color="#FFFFFF" />
              )}
              <div
                style={{
                  position: "absolute",
                  inset: -4,
                  borderRadius: "24px",
                  border: "2px solid transparent",
                  borderTopColor: "#C04CFD",
                  borderRightColor: "#38BDF8",
                  animation: "authSpin 1.2s linear infinite",
                }}
              />
            </div>

            <div>
              <h3 style={{ margin: "0 0 6px", fontSize: "17px", fontWeight: 700, color: "#FFFFFF" }}>
                {oauthProvider === "google" ? "Google" : "GitHub"} orqali kirish kutilmoqda...
              </h3>
              <p style={{ margin: 0, fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
                Tashqi brauzeringizda avtorizatsiya oynasi ochildi.
                <br />
                Hisobingizni tasdiqlang va ruxsat bering.
              </p>
            </div>

            <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px" }}>
              {oauthUrl && (
                <button
                  type="button"
                  onClick={() => handleOAuthSignIn(oauthProvider, true)}
                  style={{
                    width: "100%",
                    padding: "11px 16px",
                    background: "rgba(255, 255, 255, 0.09)",
                    border: "1px solid rgba(255, 255, 255, 0.2)",
                    borderRadius: "11px",
                    color: "#F1F5F9",
                    fontSize: "13.5px",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.16)")}
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
                  padding: "10px 16px",
                  background: "transparent",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "11px",
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
        ) : telegramModalOpen ? (
          /* ═══ TELEGRAM QUICK LOGIN DRAWER ═══ */
          <div style={{ display: "flex", flexDirection: "column", gap: "16px", animation: "authEntrance 0.3s ease" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingBottom: "10px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)" }}>
              <TelegramColorIcon size={24} />
              <div style={{ flex: 1 }}>
                <h4 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>Telegram orqali kirish</h4>
                <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#94A3B8" }}>Bot yoki Telegram @username orqali tezkor kirish</p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleOpenTelegramBot}
              style={{
                width: "100%",
                padding: "12px 16px",
                background: "linear-gradient(135deg, #24A1DE 0%, #1D88BE 100%)",
                border: "none",
                borderRadius: "12px",
                color: "#FFFFFF",
                fontSize: "13.5px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                boxShadow: "0 4px 18px rgba(36, 161, 222, 0.4)",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-1.5px)")}
              onMouseLeave={(e) => (e.currentTarget.style.transform = "translateY(0)")}
            >
              <span>🤖 @Misa_ai_agent_bot orqali ochish</span>
            </button>

            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#64748B", fontSize: "12px" }}>
              <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.08)" }} />
              <span>yoki Telegram @username kiriting</span>
              <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.08)" }} />
            </div>

            <form onSubmit={handleTelegramSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ position: "relative" }}>
                <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#38BDF8", pointerEvents: "none" }}>
                  <TelegramColorIcon size={18} />
                </div>
                <input
                  type="text"
                  value={telegramInput}
                  onChange={(e) => setTelegramInput(e.target.value)}
                  placeholder="@sherzod_dev yoki ID"
                  className="misa-auth-input"
                  style={{ padding: "12px 14px 12px 42px" }}
                  required
                />
              </div>

              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setTelegramModalOpen(false)}
                  style={{
                    flex: 1,
                    padding: "11px 16px",
                    background: "rgba(255, 255, 255, 0.08)",
                    border: "1px solid rgba(255, 255, 255, 0.14)",
                    borderRadius: "11px",
                    color: "#94A3B8",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.14)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255, 255, 255, 0.08)")}
                >
                  Ortga
                </button>
                <button
                  type="submit"
                  disabled={telegramLoading}
                  style={{
                    flex: 2,
                    padding: "11px 16px",
                    background: "linear-gradient(135deg, #24A1DE 0%, #1D88BE 100%)",
                    border: "none",
                    borderRadius: "11px",
                    color: "#FFFFFF",
                    fontSize: "13px",
                    fontWeight: 700,
                    cursor: telegramLoading ? "default" : "pointer",
                    boxShadow: "0 4px 16px rgba(36, 161, 222, 0.35)",
                    transition: "all 0.15s ease",
                    opacity: telegramLoading ? 0.7 : 1,
                  }}
                >
                  {telegramLoading ? "Tekshirilmoqda..." : "Kirish"}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            {/* ═══ SOCIAL LOGINS (Google, GitHub, Telegram) ═══ */}
            <div style={{ marginBottom: "18px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
                {/* Google */}
                <button
                  type="button"
                  role="button"
                  aria-label="Google orqali kirish"
                  onClick={() => handleOAuthSignIn("google")}
                  disabled={loading || oauthLoading || oauthWaiting}
                  className="misa-social-btn"
                  title="Google orqali kirish"
                >
                  <GoogleIcon size={18} />
                  <span>Google</span>
                </button>

                {/* GitHub */}
                <button
                  type="button"
                  role="button"
                  aria-label="GitHub orqali kirish"
                  onClick={() => handleOAuthSignIn("github")}
                  disabled={loading || oauthLoading || oauthWaiting}
                  className="misa-social-btn"
                  title="GitHub orqali kirish"
                >
                  <GithubIcon size={18} color="#FFFFFF" />
                  <span>GitHub</span>
                </button>

                {/* Telegram */}
                <button
                  type="button"
                  role="button"
                  aria-label="Telegram orqali kirish"
                  onClick={() => setTelegramModalOpen(true)}
                  disabled={loading || oauthLoading || oauthWaiting}
                  className="misa-social-btn"
                  title="Telegram orqali kirish"
                >
                  <TelegramColorIcon size={18} />
                  <span>Telegram</span>
                </button>
              </div>

              {/* Glowing Divider */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  margin: "18px 0 14px",
                  color: "#64748B",
                  fontSize: "12px",
                }}
              >
                <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.1)" }} />
                <span>{activeTab === "login" ? "yoki email orqali" : "yoki yangi akkaunt"}</span>
                <div style={{ flex: 1, height: "1px", background: "rgba(255, 255, 255, 0.1)" }} />
              </div>
            </div>

            {/* ═══ TAB 1: LOGIN FORM ═══ */}
            {activeTab === "login" && (
              <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                {/* Email Address (Pure Email, No Username) */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                    Email manzil
                  </label>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <MailIcon size={16} />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      autoComplete="email"
                      required
                      className="misa-auth-input"
                      style={{ padding: "12px 14px 12px 42px" }}
                    />
                  </div>
                </div>

                {/* Password with Eye Visibility Toggle */}
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
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <LockIcon size={16} />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="current-password"
                      required
                      className="misa-auth-input"
                      style={{ padding: "12px 42px 12px 42px" }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        color: showPassword ? "#C04CFD" : "#64748B",
                        cursor: "pointer",
                        padding: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                      title={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                    >
                      {showPassword ? <EyeOffIcon size={16} /> : <EyeIcon size={16} />}
                    </button>
                  </div>
                </div>

                {/* Submit Button */}
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
                    boxShadow: "0 4px 22px rgba(147, 3, 197, 0.45)",
                    transition: "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)",
                    opacity: loading || oauthLoading ? 0.7 : 1,
                  }}
                  onMouseEnter={(e) => {
                    if (!loading && !oauthLoading) {
                      e.currentTarget.style.transform = "translateY(-1.5px)";
                      e.currentTarget.style.boxShadow = "0 6px 26px rgba(192, 76, 253, 0.58)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.boxShadow = "0 4px 22px rgba(147, 3, 197, 0.45)";
                  }}
                >
                  {loading ? "Kirilmoqda..." : "Tizimga kirish"}
                </button>
              </form>
            )}

            {/* ═══ TAB 2: REGISTER FORM (NO USERNAME) ═══ */}
            {activeTab === "register" && (
              <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: "13px" }}>
                {/* Ism va Familiya */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <label style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                      Ism
                    </label>
                    <input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      placeholder="Ismingiz"
                      autoComplete="given-name"
                      className="misa-auth-input"
                      style={{ padding: "10px 14px" }}
                    />
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                    <label style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                      Familiya
                    </label>
                    <input
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      placeholder="Familiyangiz"
                      autoComplete="family-name"
                      className="misa-auth-input"
                      style={{ padding: "10px 14px" }}
                    />
                  </div>
                </div>

                {/* Email Address */}
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                    Email manzil
                  </label>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <MailIcon size={16} />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      autoComplete="email"
                      required
                      className="misa-auth-input"
                      style={{ padding: "11px 14px 11px 40px" }}
                    />
                  </div>
                </div>

                {/* Password */}
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                    Parol (kamida 8 belgi, harf va raqam)
                  </label>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <LockIcon size={16} />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      required
                      className="misa-auth-input"
                      style={{ padding: "11px 40px 11px 40px" }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        color: showPassword ? "#C04CFD" : "#64748B",
                        cursor: "pointer",
                        padding: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                      title={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                    >
                      {showPassword ? <EyeOffIcon size={15} /> : <EyeIcon size={15} />}
                    </button>
                  </div>
                </div>

                {/* Confirm Password */}
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                    Parolni tasdiqlang
                  </label>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <LockIcon size={16} />
                    </div>
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      required
                      className="misa-auth-input"
                      style={{ padding: "11px 40px 11px 40px" }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        color: showConfirmPassword ? "#C04CFD" : "#64748B",
                        cursor: "pointer",
                        padding: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                      title={showConfirmPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                    >
                      {showConfirmPassword ? <EyeOffIcon size={15} /> : <EyeIcon size={15} />}
                    </button>
                  </div>
                </div>

                {/* Submit Button */}
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
                    boxShadow: "0 4px 22px rgba(147, 3, 197, 0.45)",
                    transition: "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)",
                    opacity: loading || oauthLoading ? 0.7 : 1,
                  }}
                  onMouseEnter={(e) => {
                    if (!loading && !oauthLoading) {
                      e.currentTarget.style.transform = "translateY(-1.5px)";
                      e.currentTarget.style.boxShadow = "0 6px 26px rgba(192, 76, 253, 0.58)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.boxShadow = "0 4px 22px rgba(147, 3, 197, 0.45)";
                  }}
                >
                  {loading ? "Yaratilmoqda..." : "Hisob yaratish"}
                </button>
              </form>
            )}

            {/* ═══ TAB 3: FORGOT PASSWORD FORM ═══ */}
            {activeTab === "forgot" && (
              <form onSubmit={handleForgotPassword} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
                  Hisobingizga bog'langan email manzilni kiriting. Biz parolni tiklash kodini yuboramiz.
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                    Email manzil
                  </label>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <MailIcon size={16} />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      required
                      className="misa-auth-input"
                      style={{ padding: "12px 14px 12px 42px" }}
                    />
                  </div>
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
                    fontSize: "14px",
                    fontWeight: 700,
                    cursor: loading ? "default" : "pointer",
                    boxShadow: "0 4px 20px rgba(16, 185, 129, 0.35)",
                    transition: "all 0.2s ease",
                    opacity: loading ? 0.7 : 1,
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

            {/* ═══ TAB 4: RESET PASSWORD FORM ═══ */}
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
                    className="misa-auth-input"
                    style={{ padding: "11px 14px" }}
                  />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                    Yangi parol
                  </label>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <LockIcon size={16} />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="misa-auth-input"
                      style={{ padding: "11px 40px 11px 40px" }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        color: showPassword ? "#C04CFD" : "#64748B",
                        cursor: "pointer",
                        padding: "4px",
                      }}
                    >
                      {showPassword ? <EyeOffIcon size={15} /> : <EyeIcon size={15} />}
                    </button>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                    Yangi parolni tasdiqlang
                  </label>
                  <div style={{ position: "relative" }}>
                    <div style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", display: "flex", alignItems: "center", color: "#94A3B8", pointerEvents: "none" }}>
                      <LockIcon size={16} />
                    </div>
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="misa-auth-input"
                      style={{ padding: "11px 40px 11px 40px" }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{
                        position: "absolute",
                        right: "12px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        color: showConfirmPassword ? "#C04CFD" : "#64748B",
                        cursor: "pointer",
                        padding: "4px",
                      }}
                    >
                      {showConfirmPassword ? <EyeOffIcon size={15} /> : <EyeIcon size={15} />}
                    </button>
                  </div>
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
                    fontSize: "14px",
                    fontWeight: 700,
                    cursor: loading ? "default" : "pointer",
                    boxShadow: "0 4px 20px rgba(16, 185, 129, 0.35)",
                    transition: "all 0.2s ease",
                    opacity: loading ? 0.7 : 1,
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

            {/* ═══ TAB 5: VERIFY EMAIL FORM ═══ */}
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
                    className="misa-auth-input"
                    style={{ padding: "11px 14px" }}
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
                    fontSize: "14px",
                    fontWeight: 700,
                    cursor: loading ? "default" : "pointer",
                    boxShadow: "0 4px 20px rgba(16, 185, 129, 0.35)",
                    transition: "all 0.2s ease",
                    opacity: loading ? 0.7 : 1,
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

        {/* ═══ FOOTER INFO ═══ */}
        <div
          style={{
            marginTop: "24px",
            paddingTop: "16px",
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
            <span style={{ color: "#4EDEA3", fontWeight: 500 }}>Secured by Supabase & OAuth</span>
          </div>
          <button
            type="button"
            onClick={() => setDiagModalOpen(true)}
            title="Server ulanish holatini tekshirish"
            style={{
              background: "none",
              border: "none",
              color: "#A78BFA",
              cursor: "pointer",
              fontSize: "11.5px",
              padding: "3px 6px",
              borderRadius: "6px",
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(167, 139, 250, 0.12)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
          >
            <GlobeIcon size={13} color="#A78BFA" />
            <span>Server sozlamalari</span>
          </button>
        </div>
      </div>

      <ServerDiagnosticModal
        isOpen={diagModalOpen}
        onClose={() => setDiagModalOpen(false)}
        onServerChanged={() => {
          setErrorMsg(null);
        }}
      />
    </div>
  );
};
