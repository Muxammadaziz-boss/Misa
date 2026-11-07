// ========== AuthPage.tsx ==========
// Misa AI v9.3 — Multi-Provider Authentication & Ultra Glass Portal
// Support for Google, GitHub, Telegram & Direct Email Auth with Fluid Micro-Animations

import React, { useState, useEffect, useRef } from "react";
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
  CopyIcon,
} from "../components/icons/Icons";
import { MisaLogo } from "../components/MisaLogo";
import { WindowControls } from "../components/WindowControls";
import { ServerDiagnosticModal } from "../components/ServerDiagnosticModal";

interface AuthPageProps {
  onAuthSuccess: (user: MikasaAuthUser) => void;
}

type AuthTab = "login" | "register" | "forgot" | "reset" | "verify";

const inputBoxStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  width: "100%",
  minWidth: 0,
  maxWidth: "100%",
  height: "50px",
  minHeight: "50px",
  background: "linear-gradient(173deg, #181126 0%, #0d0918 100%)",
  border: "1px solid rgba(192, 76, 253, 0.25)",
  borderRadius: "15px",
  padding: "0 14px",
  gap: "10px",
  boxSizing: "border-box",
  boxShadow:
    "6px 6px 18px rgba(0, 0, 0, 0.75), -4px -4px 14px rgba(60, 35, 90, 0.2), inset 4px 4px 10px rgba(0, 0, 0, 0.75), inset -3px -3px 8px rgba(70, 40, 105, 0.18)",
  transition: "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)",
};

const inputInnerStyle: React.CSSProperties = {
  flex: 1,
  width: "100%",
  minWidth: 0,
  height: "100%",
  boxSizing: "border-box",
  background: "transparent",
  border: "none",
  outline: "none",
  boxShadow: "none",
  color: "#FFFFFF",
  fontSize: "14.5px",
  padding: "0 6px",
  margin: 0,
  fontFamily: "inherit",
};

interface OtpCodeInputProps {
  value: string;
  onChange: (val: string) => void;
  onComplete?: (val: string) => void;
  disabled?: boolean;
}

const OtpCodeInput: React.FC<OtpCodeInputProps> = ({
  value,
  onChange,
  onComplete,
  disabled,
}) => {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length: 6 }, (_, i) => value[i] || "");

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (!digits[index] && index > 0) {
        const newDigits = [...digits];
        newDigits[index - 1] = "";
        onChange(newDigits.join(""));
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePasteString = (pasted: string) => {
    const digitsOnly = pasted.replace(/[^0-9]/g, "").slice(0, 6);
    if (!digitsOnly) return;
    onChange(digitsOnly);
    const focusIdx = Math.min(digitsOnly.length, 5);
    inputRefs.current[focusIdx]?.focus();
    if (digitsOnly.length === 6 && onComplete) {
      onComplete(digitsOnly);
    }
  };

  const handleChange = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const rawVal = e.target.value;
    const cleanDigits = rawVal.replace(/[^0-9]/g, "");

    if (!cleanDigits) {
      const newDigits = [...digits];
      newDigits[index] = "";
      onChange(newDigits.join(""));
      return;
    }

    if (cleanDigits.length > 1) {
      handlePasteString(cleanDigits);
      return;
    }

    const newDigits = [...digits];
    newDigits[index] = cleanDigits;
    const newVal = newDigits.join("");
    onChange(newVal);

    if (index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    if (newVal.length === 6 && onComplete) {
      onComplete(newVal);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text");
    handlePasteString(pasted);
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "10px",
        margin: "16px 0 12px",
      }}
      onPaste={handlePaste}
    >
      {digits.map((digit, idx) => (
        <React.Fragment key={idx}>
          {idx === 3 && (
            <div
              style={{
                width: "8px",
                height: "2px",
                background: "rgba(192, 76, 253, 0.4)",
                borderRadius: "2px",
                margin: "0 2px",
              }}
            />
          )}
          <input
            ref={(el) => {
              inputRefs.current[idx] = el;
            }}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            value={digit}
            autoFocus={idx === 0}
            disabled={disabled}
            onChange={(e) => handleChange(idx, e)}
            onKeyDown={(e) => handleKeyDown(idx, e)}
            onFocus={(e) => e.target.select()}
            className="misa-otp-slot"
            style={{
              width: "48px",
              height: "56px",
              boxSizing: "border-box",
              textAlign: "center",
              fontSize: "24px",
              fontWeight: 800,
              fontFamily: "'SF Mono', Consolas, Monaco, monospace",
              color: "#FFFFFF",
              background: digit ? "rgba(192, 76, 253, 0.2)" : "#141923",
              border: digit
                ? "1.5px solid #9303C5"
                : "1px solid rgba(192, 76, 253, 0.25)",
              borderRadius: "14px",
              outline: "none",
              transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
              boxShadow: digit
                ? "inset 0 0 10px rgba(147, 3, 197, 0.28), 0 0 16px rgba(192, 76, 253, 0.35)"
                : "inset 4px 4px 8px rgba(0, 0, 0, 0.75), inset -2px -2px 6px rgba(70, 40, 105, 0.18), 0 3px 8px rgba(0, 0, 0, 0.4)",
              cursor: disabled ? "not-allowed" : "text",
            }}
          />
        </React.Fragment>
      ))}
    </div>
  );
};

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

  // Telegram 2FA / OTP Login state
  const [telegramModalOpen, setTelegramModalOpen] = useState(false);
  const [telegramOtp, setTelegramOtp] = useState<string>("");
  const [telegramDeepLink, setTelegramDeepLink] = useState<string>("");
  const [telegramRequestId, setTelegramRequestId] = useState<string>("");
  const [telegramOtpLoading, setTelegramOtpLoading] = useState<boolean>(false);
  const [telegramOtpCopied, setTelegramOtpCopied] = useState<boolean>(false);
  const [telegramVerifiedData, setTelegramVerifiedData] = useState<{
    id: number;
    username: string;
    first_name?: string;
    last_name?: string;
  } | null>(null);
  const [telegramUserNotFound, setTelegramUserNotFound] = useState(false);
  const [telegramCreatingAccount, setTelegramCreatingAccount] = useState(false);

  // OTP Login state
  const [loginMethod, setLoginMethod] = useState<"password" | "otp">("password");
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [otpCooldown, setOtpCooldown] = useState(0);
  const [otpSending, setOtpSending] = useState(false);
  const [otpVerifying, setOtpVerifying] = useState(false);
  const isOtpVerificationMode = activeTab === "login" && loginMethod === "otp" && otpSent;

  // OTP cooldown timer
  useEffect(() => {
    if (otpCooldown <= 0) return;
    const t = setTimeout(() => setOtpCooldown((prev) => prev - 1), 1000);
    return () => clearTimeout(t);
  }, [otpCooldown]);

  // Clear messages on tab change
  const handleTabChange = (tab: AuthTab) => {
    setActiveTab(tab);
    setErrorMsg(null);
    setSuccessMsg(null);
    setOauthWaiting(false);
    setOauthState(null);
    setTelegramModalOpen(false);
    setTelegramUserNotFound(false);
    setTelegramVerifiedData(null);
    setTelegramOtp("");
    setTelegramDeepLink("");
    setTelegramRequestId("");
    setOtpSent(false);
    setOtpCode("");
  };

  // Check on mount if opened with recovery URL or type=recovery
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data?.session) {
        backendService.setAuthToken(null);
      }
    }).catch(() => {});
    const hash = window.location.hash || "";
    const search = window.location.search || "";
    if (hash.includes("type=recovery") || search.includes("type=recovery") || hash.includes("recovery_token=")) {
      setActiveTab("reset");
      setSuccessMsg("Emailingiz tasdiqlandi. Iltimos, hisobingiz uchun yangi parolingizni belgilang.");
      setErrorMsg(null);
    }
  }, []);

  // Listen for OAuth redirect & recovery sessions
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "PASSWORD_RECOVERY") {
        setActiveTab("reset");
        setSuccessMsg("Emailingiz tasdiqlandi. Iltimos, yangi parolingizni belgilang.");
        setErrorMsg(null);
        return;
      }
      if ((event === "SIGNED_IN" || event === "USER_UPDATED" || event === "TOKEN_REFRESHED") && session?.user) {
        const hash = window.location.hash || "";
        const search = window.location.search || "";
        if (hash.includes("type=recovery") || search.includes("type=recovery") || activeTab === "reset") {
          setActiveTab("reset");
          setSuccessMsg("Emailingiz tasdiqlandi. Iltimos, yangi parolingizni belgilang.");
          return;
        }
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
  }, [onAuthSuccess, activeTab]);

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
          const { access_token, refresh_token, code, type: sessType } = res.session as any;
          if (sessType === "recovery") {
            shouldContinue = false;
            setOauthWaiting(false);
            setOauthState(null);
            if (access_token) {
              await supabase.auth.setSession({
                access_token,
                refresh_token: refresh_token || access_token,
              });
              backendService.setAuthToken(access_token);
            }
            setActiveTab("reset");
            setSuccessMsg("Emailingiz tasdiqlandi. Iltimos, yangi parolingizni belgilang.");
            setErrorMsg(null);
            return;
          }
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
      // Pre-check if GitHub is enabled in Supabase
      if (provider === "github") {
        try {
          const probe = await fetch("https://vdcssmzguxfknqkfxbed.supabase.co/auth/v1/authorize?provider=github", { method: "GET" });
          if (!probe.ok && probe.status === 400) {
            const probeJson = await probe.json().catch(() => null);
            if (probeJson?.msg?.includes("not enabled") || probeJson?.error_code === "validation_failed") {
              setErrorMsg("GitHub orqali kirish Supabase konsolida hali faollashtirilmagan. Iltimos, hozircha Google yoki Email orqali kiring.");
              setOauthLoading(false);
              return;
            }
          }
        } catch {}
      }

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
    const targetUrl = telegramDeepLink || "https://t.me/Misa_ai_agent_bot?start=auth";
    try {
      await backendService.openExternalUrl(targetUrl);
      setSuccessMsg("Telegram bot (@Misa_ai_agent_bot) ochildi. Bot orqali tasdiqlang.");
    } catch {
      window.open(targetUrl, "_blank");
    }
  };

  // 1. Start Telegram OTP Login Session (Zero-trust 2FA)
  const handleOpenTelegramLogin = async () => {
    setTelegramModalOpen(true);
    setTelegramOtpLoading(true);
    setTelegramOtpCopied(false);
    setTelegramUserNotFound(false);
    setTelegramVerifiedData(null);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      let res = await backendService.startTelegramLink();
      if (!res?.ok && (res?.error?.includes("Token yaroqsiz") || res?.error?.includes("Avtorizatsiyadan"))) {
        backendService.setAuthToken(null);
        res = await backendService.startTelegramLink();
      }
      if (res && res.ok && res.otp) {
        setTelegramOtp(res.otp);
        const link =
          res.deep_link ||
          `https://t.me/${res.bot_username || "Misa_ai_agent_bot"}?start=${res.link_token || ""}`;
        setTelegramDeepLink(link);
        setTelegramRequestId(res.request_id || "");
      } else {
        setErrorMsg(res?.error || "Telegram serveri bilan bog'lanishda xatolik. Iltimos, qayta urinib ko'ring.");
        setTelegramOtp("");
      }
    } catch (err: any) {
      setErrorMsg(err?.message || "Telegram serveriga ulanib bo'lmadi");
      setTelegramOtp("");
    } finally {
      setTelegramOtpLoading(false);
    }
  };

  // 2. Real-time bot verification listener for Telegram Login
  useEffect(() => {
    if (!telegramModalOpen) return;
    let isSubscribed = true;

    const processVerifiedTelegramUser = async (verifiedId: number, verifiedUsername: string, extraData?: any) => {
      if (!isSubscribed) return;
      try {
        setTelegramOtpLoading(true);

        // 1. Supabase telegram_links tekshiruvi (user_id va profile bog'langanmi?)
        let foundProfile: any = null;
        if (verifiedId) {
          const { data: linkRecord } = await supabase
            .from("telegram_links")
            .select("user_id, profiles(*)")
            .eq("telegram_user_id", verifiedId)
            .maybeSingle();
          if (linkRecord?.profiles) {
            foundProfile = linkRecord.profiles;
          }
        }
        if (!foundProfile && verifiedUsername) {
          const { data: linkRecord } = await supabase
            .from("telegram_links")
            .select("user_id, profiles(*)")
            .ilike("telegram_username", verifiedUsername)
            .maybeSingle();
          if (linkRecord?.profiles) {
            foundProfile = linkRecord.profiles;
          }
        }

        // 2. Lokal saqlangan sessiyani tekshirish
        if (!foundProfile && verifiedUsername) {
          const storedUserStr = localStorage.getItem("misa_user_data");
          const storedLinkedTg = localStorage.getItem("misa_linked_telegram");
          if (storedUserStr && storedLinkedTg && storedLinkedTg.toLowerCase() === verifiedUsername.toLowerCase()) {
            try {
              foundProfile = JSON.parse(storedUserStr);
            } catch {}
          }
        }

        // Agar mavjud hisob topilsa — kirishga ruxsat beramiz!
        if (foundProfile) {
          const p = foundProfile;
          const u: MikasaAuthUser = {
            id: p.id || `tg_${verifiedId}`,
            username: p.display_name || p.username || verifiedUsername || "Foydalanuvchi",
            email: p.email || `${verifiedUsername || verifiedId}@telegram.misa.local`,
            avatar_url: p.avatar_url || undefined,
            is_active: true,
            is_verified: true,
            created_at: Date.now() / 1000,
            provider: "telegram",
          };
          const sessionToken = `tg_verified_${verifiedId}_${Date.now()}`;
          backendService.setAuthToken(sessionToken);
          try {
            localStorage.setItem("misa_user_name", u.username);
            localStorage.setItem("misa_auth_token", sessionToken);
            localStorage.setItem("misa_user_data", JSON.stringify(u));
            localStorage.setItem("misa_linked_telegram", verifiedUsername);
          } catch {}
          setSuccessMsg(`Xush kelibsiz, ${u.username}! Telegram 2FA orqali muvaffaqiyatli tasdiqlandi.`);
          setTimeout(() => {
            onAuthSuccess(u);
          }, 400);
          return;
        }

        // Agar hisob topilmasa — userga yangi ochish yoki mavjud hisobga kirish taklif qilinadi
        setTelegramVerifiedData({
          id: verifiedId,
          username: verifiedUsername,
          first_name: extraData?.first_name,
          last_name: extraData?.last_name,
        });
        setTelegramUserNotFound(true);
      } catch (err: any) {
        setErrorMsg(err.message || "Telegram tasdiqlashda xatolik yuz berdi");
      } finally {
        setTelegramOtpLoading(false);
      }
    };

    // WebSocket orqali jonli bildirishnoma
    const unsub = backendService.onWsMessage(async (msg: any) => {
      if (!isSubscribed) return;
      const type = msg?.type;
      if (type === "PAIRING_VERIFIED" || type === "TELEGRAM_CONNECTED") {
        const verifiedUsername = (msg.telegram_username || msg.username || "").replace(/^@/, "");
        const verifiedId = Number(msg.telegram_user_id) || Date.now();
        await processVerifiedTelegramUser(verifiedId, verifiedUsername, msg);
      }
    });

    // 2.5 soniyada bir marta fallback polling
    const pollInterval = setInterval(async () => {
      if (!isSubscribed || !telegramRequestId) return;
      try {
        const st = await backendService.getTelegramLinkStatus(telegramRequestId);
        if (st && st.ok && (st.status === "VERIFIED" || st.is_linked)) {
          const verifiedUsername = (st.link?.telegram_username || (st as any).telegram_username || "").replace(/^@/, "");
          const verifiedId = Number(st.telegram_user_id || st.link?.telegram_user_id) || Date.now();
          clearInterval(pollInterval);
          await processVerifiedTelegramUser(verifiedId, verifiedUsername, st);
        }
      } catch {}
    }, 2500);

    return () => {
      isSubscribed = false;
      unsub();
      clearInterval(pollInterval);
    };
  }, [telegramModalOpen, telegramRequestId, onAuthSuccess]);

  // 3. Confirm creating a new standalone Telegram account (Only after OTP verification!)
  const confirmCreateTelegramAccount = async () => {
    if (!telegramVerifiedData) return;
    setTelegramCreatingAccount(true);
    setErrorMsg(null);
    try {
      const res = await backendService.loginWithTelegram({
        telegram_id: telegramVerifiedData.id,
        username: telegramVerifiedData.username,
        first_name: telegramVerifiedData.first_name || firstName.trim() || undefined,
      });
      if (res.ok && res.user) {
        // Supabase telegram_links ga saqlash
        try {
          await supabase.from("telegram_links").upsert(
            {
              user_id: res.user.id,
              telegram_user_id: telegramVerifiedData.id,
              telegram_username: telegramVerifiedData.username,
              first_name: telegramVerifiedData.first_name || undefined,
              updated_at: new Date().toISOString(),
            },
            { onConflict: "telegram_user_id" }
          );
        } catch {}

        try {
          localStorage.setItem("misa_linked_telegram", telegramVerifiedData.username);
        } catch {}
        setSuccessMsg("Telegram orqali yangi hisob yaratildi!");
        setTimeout(() => {
          onAuthSuccess(res.user!);
        }, 400);
      } else {
        setErrorMsg(res.error || "Telegram hisob yaratishda xatolik");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Xatolik yuz berdi");
    } finally {
      setTelegramCreatingAccount(false);
    }
  };

  // Password validation helper
  const isPasswordStrong = (pwd: string) => {
    return pwd.length >= 8 && /[a-zA-Z]/.test(pwd) && /[0-9]/.test(pwd);
  };

  // OTP: Send Verification Code to Email
  const handleSendOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (loading || otpSending) return;
    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes("@")) {
      setErrorMsg("Iltimos, to'g'ri email manzilini kiriting");
      return;
    }
    setOtpSending(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.signInWithOtp(cleanEmail);
      if (res.ok) {
        setOtpSent(true);
        setOtpCooldown(60);
        setSuccessMsg(`6 xonali tasdiqlash kodi ${cleanEmail} manziliga yuborildi! Pochtadagi xatni tekshiring.`);
      } else {
        setErrorMsg(res.error || "Kod yuborishda xatolik yuz berdi");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Kod yuborishda kutilmagan xatolik");
    } finally {
      setOtpSending(false);
    }
  };

  // OTP: Verify 6-digit Code & Sign In
  const handleVerifyOtp = async (e?: React.FormEvent, customCode?: string) => {
    if (e) e.preventDefault();
    if (loading || otpVerifying) return;
    const cleanEmail = email.trim();
    const cleanCode = (customCode || otpCode).trim().replace(/\s+/g, "");
    if (!cleanEmail) {
      setErrorMsg("Email manzili kiritilmagan");
      return;
    }
    if (!cleanCode || cleanCode.length < 6) {
      setErrorMsg("Iltimos, 6 xonali tasdiqlash kodini to'liq kiriting");
      return;
    }

    setOtpVerifying(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await backendService.verifyEmailOtp(cleanEmail, cleanCode);
      if (res.ok && res.user) {
        setSuccessMsg("Tizimga muvaffaqiyatli kirildi!");
        setTimeout(() => {
          onAuthSuccess(res.user!);
        }, 400);
      } else {
        setErrorMsg(res.error || "Tasdiqlash kodi xato yoki muddati tugagan");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Tasdiqlashda xatolik yuz berdi");
    } finally {
      setOtpVerifying(false);
    }
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
        token: token.trim() || undefined,
        new_password: password,
      });

      if (res.ok) {
        setSuccessMsg("Parol muvaffaqiyatli yangilandi! Endi tizimga yangi parolingiz bilan kirishingiz mumkin.");
        setTimeout(() => {
          setPassword("");
          setConfirmPassword("");
          setToken("");
          setActiveTab("login");
        }, 1800);
      } else {
        setErrorMsg(res.error || "Parolni yangilashda xatolik yuz berdi");
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
        /* Hide native Edge/WebKit password reveal eye and clear icons */
        input::-ms-reveal { display: none !important; }
        input::-ms-clear { display: none !important; }
        input::-webkit-contacts-auto-fill-button { display: none !important; }
        input::-webkit-credentials-auto-fill-button { display: none !important; }

        /* Unified input box with icon and controls inside */
        .misa-input-box {
          display: flex;
          align-items: center;
          width: 100%;
          height: 50px;
          min-height: 50px;
          background: rgba(11, 16, 32, 0.95);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1.5px solid rgba(192, 76, 253, 0.45);
          border-radius: 12px;
          padding: 0 14px;
          box-sizing: border-box;
          transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .misa-input-box:hover {
          border-color: rgba(192, 76, 253, 0.78);
          background: rgba(16, 22, 44, 0.98);
        }
        .misa-input-box:focus-within {
          border-color: #C04CFD !important;
          background: rgba(20, 26, 52, 1) !important;
          box-shadow: 0 0 0 3px rgba(192, 76, 253, 0.32), 0 0 22px rgba(147, 3, 197, 0.38) !important;
        }
        .misa-input-inner {
          flex: 1;
          height: 100%;
          background: transparent !important;
          border: none !important;
          outline: none !important;
          box-shadow: none !important;
          color: #FFFFFF !important;
          font-size: 14.5px;
          padding: 0 10px !important;
          margin: 0 !important;
          font-family: inherit;
        }
        .misa-input-inner::placeholder {
          color: #64748B;
          font-size: 13.5px;
        }
        .misa-auth-input {
          width: 100%;
          height: 48px;
          min-height: 48px;
          line-height: normal;
          background: rgba(13, 19, 36, 0.95);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1.5px solid rgba(192, 76, 253, 0.42);
          border-radius: 12px;
          color: #FFFFFF;
          font-size: 14.5px;
          outline: none;
          box-sizing: border-box;
          transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .misa-auth-input:hover {
          border-color: rgba(192, 76, 253, 0.75);
          background: rgba(18, 24, 46, 0.98);
        }
        .misa-auth-input:focus {
          border-color: #C04CFD !important;
          background: rgba(22, 28, 54, 1) !important;
          box-shadow: 0 0 0 3px rgba(192, 76, 253, 0.32), 0 0 20px rgba(147, 3, 197, 0.35) !important;
        }
        .misa-auth-input::placeholder {
          color: #64748B;
          font-size: 13.5px;
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
        .misa-otp-slot:hover:not(:disabled) {
          border-color: rgba(192, 76, 253, 0.6) !important;
          background: rgba(192, 76, 253, 0.1) !important;
        }
        .misa-otp-slot:focus {
          border-color: #C04CFD !important;
          background: rgba(192, 76, 253, 0.22) !important;
          box-shadow: 0 0 0 3px rgba(192, 76, 253, 0.35), 0 0 22px rgba(147, 3, 197, 0.5) !important;
          transform: translateY(-2px);
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
          boxSizing: "border-box",
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
        {!isOtpVerificationMode && (
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
        )}

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

        {successMsg && !isOtpVerificationMode && (
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
          /* ═══ TELEGRAM 2FA / OTP LOGIN DRAWER ═══ */
          <div style={{ display: "flex", flexDirection: "column", gap: "16px", animation: "authEntrance 0.3s ease" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", paddingBottom: "10px", borderBottom: "1px solid rgba(255, 255, 255, 0.1)" }}>
              <TelegramColorIcon size={24} />
              <div style={{ flex: 1 }}>
                <h4 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>Telegram orqali xavfsiz kirish</h4>
                <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#94A3B8" }}>2FA / OTP orqali begona shaxslar kirishidan to'liq himoyalangan</p>
              </div>
            </div>

            {telegramUserNotFound && telegramVerifiedData ? (
              /* Verified but account not linked yet */
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  background: "rgba(245, 158, 11, 0.12)",
                  border: "1px solid rgba(245, 158, 11, 0.4)",
                  borderRadius: "14px",
                  padding: "16px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#FCD34D", fontWeight: 700, fontSize: "13.5px" }}>
                  <span>⚠️</span>
                  <span>Telegram hisobingiz tasdiqlandi, lekin Misa akkauntingiz topilmadi</span>
                </div>
                <p style={{ margin: 0, fontSize: "12.5px", color: "#E2E8F0", lineHeight: 1.5 }}>
                  Hurmatli <strong>@{telegramVerifiedData.username}</strong>, sizning Telegram hisobingiz xavfsiz tasdiqlandi. Ammo u hali hech qaysi Misa akkauntiga ulanmagan.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "4px" }}>
                  <button
                    type="button"
                    onClick={confirmCreateTelegramAccount}
                    disabled={telegramCreatingAccount}
                    style={{
                      width: "100%",
                      padding: "11px",
                      background: "linear-gradient(135deg, #24A1DE 0%, #1D88BE 100%)",
                      border: "none",
                      borderRadius: "10px",
                      color: "#FFFFFF",
                      fontSize: "13px",
                      fontWeight: 700,
                      cursor: "pointer",
                      boxShadow: "0 4px 14px rgba(36, 161, 222, 0.4)",
                    }}
                  >
                    {telegramCreatingAccount ? "Yaratilmoqda..." : "✨ Ushbu Telegram bilan yangi hisob ochish"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setTelegramUserNotFound(false);
                      setTelegramVerifiedData(null);
                      setTelegramModalOpen(false);
                      setActiveTab("login");
                    }}
                    style={{
                      width: "100%",
                      padding: "10px",
                      background: "rgba(255, 255, 255, 0.08)",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      borderRadius: "10px",
                      color: "#CBD5E1",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    🔑 Mavjud hisobimga kirish (Google / Email)
                  </button>
                </div>
              </div>
            ) : (
              /* OTP Display and Bot action */
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {/* Security Reassurance Badge */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px 12px",
                    background: "rgba(16, 185, 129, 0.1)",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                    borderRadius: "10px",
                    color: "#34D399",
                    fontSize: "11.5px",
                    lineHeight: 1.4,
                  }}
                >
                  <ShieldIcon size={16} />
                  <span>Hech kim boshqa birovning username orqali kira olmaydi — faqat botda tasdiqlash bilan.</span>
                </div>

                {/* 6-digit OTP Box with Copy button */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "14px 18px",
                    borderRadius: "14px",
                    background: "rgba(56, 189, 248, 0.08)",
                    border: "1.5px solid rgba(56, 189, 248, 0.45)",
                    boxShadow: "0 0 25px rgba(56, 189, 248, 0.15)",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                    <span style={{ fontSize: "11px", color: "#38BDF8", fontWeight: 600, textTransform: "uppercase" }}>
                      Bir martalik tasdiqlash kodi (OTP):
                    </span>
                    <span
                      style={{
                        fontSize: "26px",
                        fontWeight: 800,
                        letterSpacing: "6px",
                        color: "#FFFFFF",
                        fontFamily: "monospace",
                      }}
                    >
                      {telegramOtpLoading ? "Yuklanmoqda..." : telegramOtp || "------"}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      if (telegramOtp) {
                        navigator.clipboard.writeText(telegramOtp);
                        setTelegramOtpCopied(true);
                        setTimeout(() => setTelegramOtpCopied(false), 2000);
                        setSuccessMsg("Kod nusxalandi!");
                      }
                    }}
                    disabled={telegramOtpLoading || !telegramOtp}
                    style={{
                      padding: "8px 14px",
                      borderRadius: "10px",
                      background: telegramOtpCopied ? "rgba(16, 185, 129, 0.25)" : "rgba(255, 255, 255, 0.1)",
                      border: telegramOtpCopied ? "1px solid #10B981" : "1px solid rgba(255, 255, 255, 0.2)",
                      color: telegramOtpCopied ? "#34D399" : "#F1F5F9",
                      fontSize: "12px",
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <CopyIcon size={14} />
                    <span>{telegramOtpCopied ? "✓ Nusxalandi" : "Nusxalash"}</span>
                  </button>
                </div>

                {/* Primary Action Button */}
                <button
                  type="button"
                  onClick={handleOpenTelegramBot}
                  style={{
                    width: "100%",
                    padding: "13px 20px",
                    background: "linear-gradient(135deg, #24A1DE 0%, #0284C7 100%)",
                    border: "none",
                    borderRadius: "14px",
                    color: "#FFFFFF",
                    fontSize: "13.5px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "10px",
                    boxShadow: "0 4px 20px rgba(36, 161, 222, 0.4)",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.transform = "translateY(-1.5px)")}
                  onMouseLeave={(e) => (e.currentTarget.style.transform = "translateY(0)")}
                >
                  <TelegramColorIcon size={20} />
                  <span>🤖 @Misa_ai_agent_bot da tasdiqlash</span>
                </button>

                {/* Live Waiting Radar */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px",
                    padding: "8px",
                    fontSize: "12px",
                    color: "#94A3B8",
                  }}
                >
                  <span
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: "#38BDF8",
                      boxShadow: "0 0 10px #38BDF8",
                      animation: "pulse 1.5s infinite",
                    }}
                  />
                  <span>Botda 'Boshlash' (/start) yoki kodni yuborishingiz kutilmoqda...</span>
                </div>

                <div style={{ display: "flex", gap: "10px", marginTop: "4px" }}>
                  <button
                    type="button"
                    onClick={() => {
                      setTelegramModalOpen(false);
                      setTelegramUserNotFound(false);
                      setTelegramVerifiedData(null);
                    }}
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
                  >
                    Ortga
                  </button>
                  <button
                    type="button"
                    onClick={handleOpenTelegramLogin}
                    disabled={telegramOtpLoading}
                    style={{
                      flex: 1,
                      padding: "11px 16px",
                      background: "rgba(56, 189, 248, 0.12)",
                      border: "1px solid rgba(56, 189, 248, 0.3)",
                      borderRadius: "11px",
                      color: "#38BDF8",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {telegramOtpLoading ? "Yangilanmoqda..." : "Yangi kod olish"}
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : isOtpVerificationMode ? (
          /* ═══ DEDICATED OTP VERIFICATION VIEW (Ultra Modern & Focused) ═══ */
          <div style={{ display: "flex", flexDirection: "column", animation: "authEntrance 0.35s ease" }}>
            {/* Top Navigation & Step Indicator */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "20px",
              }}
            >
              <button
                type="button"
                onClick={() => {
                  setOtpSent(false);
                  setOtpCode("");
                  setErrorMsg(null);
                }}
                style={{
                  background: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.12)",
                  borderRadius: "10px",
                  padding: "7px 14px",
                  color: "#CBD5E1",
                  fontSize: "12.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  transition: "all 0.18s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(192, 76, 253, 0.16)";
                  e.currentTarget.style.borderColor = "rgba(192, 76, 253, 0.4)";
                  e.currentTarget.style.color = "#FFFFFF";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.06)";
                  e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.12)";
                  e.currentTarget.style.color = "#CBD5E1";
                }}
              >
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="19" y1="12" x2="5" y2="12"></line>
                  <polyline points="12 19 5 12 12 5"></polyline>
                </svg>
                <span>Ortga</span>
              </button>

              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "5px 12px",
                  borderRadius: "20px",
                  background: "rgba(192, 76, 253, 0.12)",
                  border: "1px solid rgba(192, 76, 253, 0.28)",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  color: "#D8B4FE",
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: "#C04CFD",
                    boxShadow: "0 0 8px #C04CFD",
                  }}
                />
                2-qadam: Tasdiqlash
              </div>
            </div>

            {/* Glowing Envelope & Header */}
            <div style={{ textAlign: "center", marginBottom: "18px" }}>
              <div
                style={{
                  width: "56px",
                  height: "56px",
                  margin: "0 auto 12px",
                  borderRadius: "16px",
                  background: "linear-gradient(135deg, rgba(147, 3, 197, 0.35) 0%, rgba(192, 76, 253, 0.2) 100%)",
                  border: "1px solid rgba(192, 76, 253, 0.4)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 8px 24px rgba(147, 3, 197, 0.35)",
                }}
              >
                <MailIcon size={26} color="#E879F9" />
              </div>
              <h2
                style={{
                  margin: "0 0 6px 0",
                  fontSize: "18px",
                  fontWeight: 700,
                  color: "#FFFFFF",
                  letterSpacing: "-0.01em",
                }}
              >
                Tasdiqlash kodi yuborildi
              </h2>
              <p style={{ margin: 0, fontSize: "12.5px", color: "#94A3B8" }}>
                6 xonali bir martalik kod quyidagi email manziliga yuborildi:
              </p>
            </div>

            {/* Email Address Pill with Edit action */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "9px 14px",
                background: "rgba(10, 15, 30, 0.7)",
                border: "1px solid rgba(192, 76, 253, 0.32)",
                borderRadius: "12px",
                marginBottom: "22px",
                boxShadow: "inset 0 1px 4px rgba(0,0,0,0.4)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                <MailIcon size={15} color="#C084FC" />
                <span
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    color: "#F1F5F9",
                    textOverflow: "ellipsis",
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                  }}
                >
                  {email}
                </span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setOtpSent(false);
                  setOtpCode("");
                  setErrorMsg(null);
                }}
                style={{
                  background: "rgba(192, 76, 253, 0.15)",
                  border: "none",
                  color: "#E879F9",
                  fontSize: "11.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                  padding: "4px 8px",
                  borderRadius: "6px",
                  transition: "all 0.15s ease",
                  flexShrink: 0,
                }}
              >
                O'zgartirish
              </button>
            </div>

            {/* Form for OTP verification */}
            <form onSubmit={handleVerifyOtp} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", alignItems: "center" }}>
                <label
                  style={{
                    fontSize: "12.5px",
                    color: "#CBD5E1",
                    fontWeight: 600,
                    textAlign: "center",
                  }}
                >
                  6 xonali tasdiqlash kodini kiriting
                </label>

                {/* 6-slot OtpCodeInput with Auto-advance, Paste, and Auto-complete */}
                <OtpCodeInput
                  value={otpCode}
                  onChange={setOtpCode}
                  onComplete={(val) => handleVerifyOtp(undefined, val)}
                  disabled={otpVerifying}
                />

                <span style={{ fontSize: "11px", color: "#64748B", textAlign: "center", lineHeight: 1.4 }}>
                  💡 Nusxalangan kodni to'g'ridan-to'g'ri joylashtirishingiz mumkin (Ctrl+V)
                </span>
              </div>

              {/* Verify & Enter Button */}
              <button
                type="submit"
                disabled={otpVerifying || otpCode.length < 6}
                style={{
                  marginTop: "6px",
                  padding: "13px 20px",
                  background: "linear-gradient(135deg, #9303C5 0%, #C04CFD 60%, #7C3AED 100%)",
                  border: "none",
                  borderRadius: "12px",
                  color: "#FFFFFF",
                  fontSize: "14.5px",
                  fontWeight: 700,
                  cursor: otpVerifying || otpCode.length < 6 ? "default" : "pointer",
                  boxShadow: "0 4px 22px rgba(147, 3, 197, 0.45)",
                  transition: "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)",
                  opacity: otpVerifying || otpCode.length < 6 ? 0.6 : 1,
                }}
                onMouseEnter={(e) => {
                  if (!otpVerifying && otpCode.length === 6) {
                    e.currentTarget.style.transform = "translateY(-1.5px)";
                    e.currentTarget.style.boxShadow = "0 6px 26px rgba(192, 76, 253, 0.58)";
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)";
                  e.currentTarget.style.boxShadow = "0 4px 22px rgba(147, 3, 197, 0.45)";
                }}
              >
                {otpVerifying ? "Tekshirilmoqda..." : "🚀 Tizimga kirish"}
              </button>

              {/* Action Links */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginTop: "4px",
                  paddingTop: "6px",
                  borderTop: "1px solid rgba(255, 255, 255, 0.06)",
                }}
              >
                <button
                  type="button"
                  onClick={() => handleSendOtp()}
                  disabled={otpCooldown > 0 || otpSending}
                  style={{
                    background: "none",
                    border: "none",
                    color: otpCooldown > 0 ? "#64748B" : "#C084FC",
                    fontSize: "12px",
                    fontWeight: 500,
                    cursor: otpCooldown > 0 ? "default" : "pointer",
                    padding: 0,
                    transition: "color 0.15s ease",
                  }}
                >
                  {otpCooldown > 0 ? `Qayta yuborish (${otpCooldown}s)` : "🔄 Yangi kod olish"}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setLoginMethod("password");
                    setOtpSent(false);
                    setErrorMsg(null);
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#94A3B8",
                    fontSize: "12px",
                    fontWeight: 500,
                    cursor: "pointer",
                    padding: 0,
                    transition: "color 0.15s ease",
                  }}
                >
                  🔑 Parol orqali kirish
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            {/* ═══ SOCIAL LOGINS (Google, GitHub, Telegram) ═══ */}
            <div style={{ marginBottom: "18px", width: "100%", boxSizing: "border-box" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "10px", width: "100%", boxSizing: "border-box" }}>
                {/* Google */}
                <button
                  type="button"
                  role="button"
                  aria-label="Google orqali kirish"
                  onClick={() => handleOAuthSignIn("google")}
                  disabled={loading || oauthLoading || oauthWaiting}
                  className="misa-social-btn"
                  title="Google orqali kirish"
                  style={{ minWidth: 0, width: "100%" }}
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
                  style={{ minWidth: 0, width: "100%" }}
                >
                  <GithubIcon size={18} color="#FFFFFF" />
                  <span>GitHub</span>
                </button>

                {/* Telegram */}
                <button
                  type="button"
                  role="button"
                  aria-label="Telegram orqali kirish"
                  onClick={handleOpenTelegramLogin}
                  disabled={loading || oauthLoading || oauthWaiting}
                  className="misa-social-btn"
                  title="Telegram orqali kirish"
                  style={{ minWidth: 0, width: "100%" }}
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
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {/* Method selector: Password vs OTP */}
                <div
                  style={{
                    display: "flex",
                    background: "rgba(8, 12, 24, 0.75)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: "11px",
                    padding: "3px",
                    gap: "4px",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setLoginMethod("password");
                      setErrorMsg(null);
                    }}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: "9px",
                      border: "none",
                      background: loginMethod === "password" ? "rgba(192, 76, 253, 0.28)" : "transparent",
                      color: loginMethod === "password" ? "#FFFFFF" : "#94A3B8",
                      fontSize: "12.5px",
                      fontWeight: loginMethod === "password" ? 700 : 500,
                      cursor: "pointer",
                      transition: "all 0.18s ease",
                      boxShadow: loginMethod === "password" ? "0 2px 10px rgba(147, 3, 197, 0.35)" : "none",
                    }}
                  >
                    🔑 Parol orqali
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setLoginMethod("otp");
                      setErrorMsg(null);
                    }}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: "9px",
                      border: "none",
                      background: loginMethod === "otp" ? "rgba(192, 76, 253, 0.28)" : "transparent",
                      color: loginMethod === "otp" ? "#FFFFFF" : "#94A3B8",
                      fontSize: "12.5px",
                      fontWeight: loginMethod === "otp" ? 700 : 500,
                      cursor: "pointer",
                      transition: "all 0.18s ease",
                      boxShadow: loginMethod === "otp" ? "0 2px 10px rgba(147, 3, 197, 0.35)" : "none",
                    }}
                  >
                    ✉️ Kod (OTP) orqali
                  </button>
                </div>

                {loginMethod === "password" ? (
                  <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                    {/* Email Address (Pure Email, No Username) */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <label htmlFor="login-email" style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                        Email manzil
                      </label>
                      <div className="misa-input-box" style={inputBoxStyle}>
                        <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                          <MailIcon size={18} />
                        </div>
                        <input
                          id="login-email"
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="user@example.com"
                          autoComplete="email"
                          required
                          className="misa-input-inner"
                          style={inputInnerStyle}
                        />
                      </div>
                    </div>

                    {/* Password with Eye Visibility Toggle */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <label htmlFor="login-password" style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
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
                      <div className="misa-input-box" style={inputBoxStyle}>
                        <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                          <LockIcon size={18} />
                        </div>
                        <input
                          id="login-password"
                          type={showPassword ? "text" : "password"}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          placeholder="••••••••"
                          autoComplete="current-password"
                          required
                          className="misa-input-inner"
                          style={inputInnerStyle}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          style={{
                            background: "none",
                            border: "none",
                            color: showPassword ? "#C04CFD" : "#94A3B8",
                            cursor: "pointer",
                            padding: "4px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                          }}
                          title={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                        >
                          {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                        </button>
                      </div>
                    </div>

                    {/* Submit Button */}
                    <button
                      type="submit"
                      disabled={loading || oauthLoading}
                      style={{
                        marginTop: "4px",
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

                    <div style={{ textAlign: "center", marginTop: "2px" }}>
                      <button
                        type="button"
                        onClick={() => {
                          setLoginMethod("otp");
                          setErrorMsg(null);
                        }}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#C084FC",
                          fontSize: "12px",
                          fontWeight: 500,
                          cursor: "pointer",
                          padding: 0,
                          textDecoration: "underline",
                        }}
                      >
                        ✉️ Parolsiz, emailga 6 xonali kod (OTP) olib kirish
                      </button>
                    </div>
                  </form>
                ) : (
                  /* OTP Step 1: Enter email & request code */
                  <form onSubmit={handleSendOtp} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <label htmlFor="otp-email" style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                        Email manzilingiz
                      </label>
                      <div className="misa-input-box" style={inputBoxStyle}>
                        <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                          <MailIcon size={18} />
                        </div>
                        <input
                          id="otp-email"
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="user@example.com"
                          autoComplete="email"
                          required
                          className="misa-input-inner"
                          style={inputInnerStyle}
                        />
                      </div>
                      <span style={{ fontSize: "12px", color: "#64748B", lineHeight: 1.4 }}>
                        Emailingizga bir martalik 6 xonali tasdiqlash kodi yuboriladi.
                      </span>
                    </div>

                    <button
                      type="submit"
                      disabled={otpSending || loading}
                      style={{
                        marginTop: "4px",
                        padding: "13px 20px",
                        background: "linear-gradient(135deg, #9303C5 0%, #C04CFD 60%, #7C3AED 100%)",
                        border: "none",
                        borderRadius: "12px",
                        color: "#FFFFFF",
                        fontSize: "14.5px",
                        fontWeight: 700,
                        cursor: otpSending || loading ? "default" : "pointer",
                        boxShadow: "0 4px 22px rgba(147, 3, 197, 0.45)",
                        transition: "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)",
                        opacity: otpSending || loading ? 0.7 : 1,
                      }}
                      onMouseEnter={(e) => {
                        if (!otpSending && !loading) {
                          e.currentTarget.style.transform = "translateY(-1.5px)";
                          e.currentTarget.style.boxShadow = "0 6px 26px rgba(192, 76, 253, 0.58)";
                        }
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = "translateY(0)";
                        e.currentTarget.style.boxShadow = "0 4px 22px rgba(147, 3, 197, 0.45)";
                      }}
                    >
                      {otpSending ? "Yuborilmoqda..." : "✉️ Tasdiqlash kodini yuborish"}
                    </button>

                    <div style={{ textAlign: "center", marginTop: "2px" }}>
                      <button
                        type="button"
                        onClick={() => {
                          setLoginMethod("password");
                          setErrorMsg(null);
                        }}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#94A3B8",
                          fontSize: "12px",
                          fontWeight: 500,
                          cursor: "pointer",
                          padding: 0,
                          textDecoration: "underline",
                        }}
                      >
                        🔑 Parol orqali kirishga qaytish
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}

            {/* ═══ TAB 2: REGISTER FORM (NO USERNAME) ═══ */}
            {activeTab === "register" && (
              <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: "13px" }}>
                {/* Ism va Familiya */}
                <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: "10px", width: "100%", boxSizing: "border-box" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "5px", minWidth: 0, overflow: "hidden" }}>
                    <label htmlFor="reg-first-name" style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                      Ism
                    </label>
                    <div className="misa-input-box" style={inputBoxStyle}>
                      <input
                        id="reg-first-name"
                        type="text"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        placeholder="Ismingiz"
                        autoComplete="given-name"
                        className="misa-input-inner"
                        style={inputInnerStyle}
                      />
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: "5px", minWidth: 0, overflow: "hidden" }}>
                    <label htmlFor="reg-last-name" style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                      Familiya
                    </label>
                    <div className="misa-input-box" style={inputBoxStyle}>
                      <input
                        id="reg-last-name"
                        type="text"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        placeholder="Familiyangiz"
                        autoComplete="family-name"
                        className="misa-input-inner"
                        style={inputInnerStyle}
                      />
                    </div>
                  </div>
                </div>

                {/* Email Address */}
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label htmlFor="reg-email" style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                    Email manzil
                  </label>
                  <div className="misa-input-box" style={inputBoxStyle}>
                    <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                      <MailIcon size={18} />
                    </div>
                    <input
                      id="reg-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      autoComplete="email"
                      required
                      className="misa-input-inner"
                      style={inputInnerStyle}
                    />
                  </div>
                </div>

                {/* Password */}
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label htmlFor="reg-password" style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                    Parol (kamida 8 belgi, harf va raqam)
                  </label>
                  <div className="misa-input-box" style={inputBoxStyle}>
                    <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                      <LockIcon size={18} />
                    </div>
                    <input
                      id="reg-password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      required
                      className="misa-input-inner"
                      style={inputInnerStyle}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        background: "none",
                        border: "none",
                        color: showPassword ? "#C04CFD" : "#94A3B8",
                        cursor: "pointer",
                        padding: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                      title={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                    >
                      {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                    </button>
                  </div>
                </div>

                {/* Confirm Password */}
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <label htmlFor="reg-confirm-password" style={{ fontSize: "12px", color: "#94A3B8", fontWeight: 500 }}>
                    Parolni tasdiqlang
                  </label>
                  <div className="misa-input-box" style={inputBoxStyle}>
                    <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                      <LockIcon size={18} />
                    </div>
                    <input
                      id="reg-confirm-password"
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      required
                      className="misa-input-inner"
                      style={inputInnerStyle}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{
                        background: "none",
                        border: "none",
                        color: showConfirmPassword ? "#C04CFD" : "#94A3B8",
                        cursor: "pointer",
                        padding: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                      title={showConfirmPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                    >
                      {showConfirmPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
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
                  <div className="misa-input-box" style={inputBoxStyle}>
                    <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                      <MailIcon size={18} />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      required
                      className="misa-input-inner"
                      style={inputInnerStyle}
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
                  {loading ? "Yuborilmoqda..." : "Tiklash havolasini yuborish"}
                </button>

                <div style={{ display: "flex", justifyContent: "center", marginTop: "8px" }}>
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
                </div>
              </form>
            )}

            {/* ═══ TAB 4: RESET PASSWORD FORM (NO MANUAL TOKEN NEEDED) ═══ */}
            {activeTab === "reset" && (
              <form onSubmit={handleResetPassword} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div style={{ fontSize: "13px", color: "#94A3B8", lineHeight: 1.5 }}>
                  Emailingiz tasdiqlandi. Iltimos, hisobingiz uchun yangi xavfsiz parol kiriting va saqlang.
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                    Yangi parol (kamida 8 belgi, harf va raqam)
                  </label>
                  <div className="misa-input-box" style={inputBoxStyle}>
                    <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                      <LockIcon size={18} />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="misa-input-inner"
                      style={inputInnerStyle}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        background: "none",
                        border: "none",
                        color: showPassword ? "#C04CFD" : "#94A3B8",
                        cursor: "pointer",
                        padding: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                      title={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                    >
                      {showPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                    </button>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <label style={{ fontSize: "12.5px", color: "#94A3B8", fontWeight: 500 }}>
                    Yangi parolni tasdiqlang
                  </label>
                  <div className="misa-input-box" style={inputBoxStyle}>
                    <div style={{ display: "flex", alignItems: "center", color: "#C084FC", flexShrink: 0 }}>
                      <LockIcon size={18} />
                    </div>
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="misa-input-inner"
                      style={inputInnerStyle}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{
                        background: "none",
                        border: "none",
                        color: showConfirmPassword ? "#C04CFD" : "#94A3B8",
                        cursor: "pointer",
                        padding: "4px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                      title={showConfirmPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                    >
                      {showConfirmPassword ? <EyeOffIcon size={18} /> : <EyeIcon size={18} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    marginTop: "6px",
                    padding: "13px 20px",
                    background: "linear-gradient(135deg, #9303C5 0%, #C04CFD 60%, #7C3AED 100%)",
                    border: "none",
                    borderRadius: "12px",
                    color: "#FFFFFF",
                    fontSize: "14.5px",
                    fontWeight: 700,
                    cursor: loading ? "default" : "pointer",
                    boxShadow: "0 4px 22px rgba(147, 3, 197, 0.45)",
                    transition: "all 0.22s cubic-bezier(0.16, 1, 0.3, 1)",
                    opacity: loading ? 0.7 : 1,
                  }}
                >
                  {loading ? "Parol saqlanmoqda..." : "Yangi parolni saqlash"}
                </button>

                <div style={{ display: "flex", justifyContent: "center", marginTop: "4px" }}>
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
                </div>
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
                    style={{ padding: "0 16px" }}
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
