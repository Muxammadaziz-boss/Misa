import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  TelegramIcon,
  RefreshIcon,
  CopyIcon,
  CheckIcon,
  ShieldCheckIcon,
  ClockIcon,
  ExternalLinkIcon,
  AlertTriangleIcon,
  UnlinkIcon,
  ArrowLeftIcon,
} from "../components/icons/Icons";
import {
  backendService,
  TelegramAccountResponse,
  TelegramBotStatusResponse,
} from "../services/backendService";

interface TelegramIntegrationPageProps {
  onNavigateHome?: () => void;
}

type PairingState =
  | "LOADING"
  | "NOT_CONNECTED"
  | "PAIRING"
  | "WAITING_FOR_OTP"
  | "CONNECTED"
  | "EXPIRED"
  | "FAILED"
  | "REVOKED";

export const TelegramIntegrationPage: React.FC<TelegramIntegrationPageProps> = ({ onNavigateHome }) => {
  const [pairingState, setPairingState] = useState<PairingState>("LOADING");
  const [accountInfo, setAccountInfo] = useState<TelegramAccountResponse | null>(null);
  const [botStatus, setBotStatus] = useState<TelegramBotStatusResponse | null>(null);

  // OTP flow state
  const [requestId, setRequestId] = useState<string>("");
  const [otpCode, setOtpCode] = useState<string>("");
  const [deepLink, setDeepLink] = useState<string>("");
  const [expiresAt, setExpiresAt] = useState<number>(0);
  const [remainingSeconds, setRemainingSeconds] = useState<number>(300);

  // UI state
  const [copied, setCopied] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [manualOtp, setManualOtp] = useState<string>("");
  const [manualTgId, setManualTgId] = useState<string>("");
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [isRechecking, setIsRechecking] = useState<boolean>(false);
  const [attemptCount, setAttemptCount] = useState<number>(0);
  const [lastErrorMsg, setLastErrorMsg] = useState<string | null>(null);

  const countdownTimerRef = useRef<any>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Load account status and bot info
  const loadStatus = useCallback(async () => {
    try {
      const [accRes, botRes] = await Promise.all([
        backendService.getTelegramAccount(),
        backendService.getTelegramBotStatus(),
      ]);
      setAccountInfo(accRes);
      setBotStatus(botRes);

      if (accRes.is_linked && accRes.link) {
        setPairingState("CONNECTED");
      } else {
        setPairingState((prev) => (prev === "WAITING_FOR_OTP" ? prev : "NOT_CONNECTED"));
      }
    } catch {
      setPairingState("NOT_CONNECTED");
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  // WebSocket event subscriptions
  useEffect(() => {
    const unsub = backendService.onWsMessage((msg: any) => {
      const type = msg?.type;
      if (type === "TELEGRAM_CONNECTED" || type === "PAIRING_VERIFIED") {
        showToast("🎉 Telegram hisobingiz muvaffaqiyatli bog'landi!");
        loadStatus();
      } else if (type === "TELEGRAM_DISCONNECTED") {
        showToast("Telegram hisobi uzildi");
        setPairingState("NOT_CONNECTED");
        loadStatus();
      } else if (type === "PAIRING_EXPIRED") {
        setPairingState("EXPIRED");
      }
    });
    return () => unsub();
  }, [loadStatus]);

  const checkCurrentRequestStatus = useCallback(
    async (manual: boolean = false) => {
      if (!requestId) {
        await loadStatus();
        return;
      }
      if (manual) setIsRechecking(true);
      try {
        const res = await backendService.getTelegramLinkStatus(requestId);
        const reqStatus = (res as any).request_status || res.status;
        if (typeof res.attempt_count === "number") {
          setAttemptCount(res.attempt_count);
        }
        if (res.ok && (res.is_linked || reqStatus === "VERIFIED" || res.status === "CONNECTED")) {
          showToast("🎉 Telegram hisobingiz muvaffaqiyatli bog'landi!");
          await loadStatus();
        } else if (reqStatus === "EXPIRED") {
          setPairingState("EXPIRED");
        } else if (reqStatus === "FAILED") {
          setLastErrorMsg("Maksimal 5 ta noto'g'ri urinish qayd etildi. Iltimos, yangi kod oling.");
          setPairingState("FAILED");
        } else if (manual) {
          showToast("Hali tasdiqlanmadi — botga 6 xonali kodni yuboring");
        }
      } catch {
        if (manual) showToast("Holatni tekshirishda xatolik yuz berdi");
      } finally {
        if (manual) setIsRechecking(false);
      }
    },
    [requestId, loadStatus]
  );

  // Fallback polling during WAITING_FOR_OTP to detect mobile Telegram verification even if WebSocket drops
  useEffect(() => {
    if (pairingState !== "WAITING_FOR_OTP" || !requestId) return;

    const pollInterval = setInterval(() => {
      checkCurrentRequestStatus(false);
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [pairingState, requestId, checkCurrentRequestStatus]);

  // Countdown timer effect
  useEffect(() => {
    if (pairingState === "WAITING_FOR_OTP" && expiresAt > 0) {
      if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);

      countdownTimerRef.current = setInterval(() => {
        const now = Date.now() / 1000;
        const left = Math.max(0, Math.floor(expiresAt - now));
        setRemainingSeconds(left);

        if (left <= 0) {
          clearInterval(countdownTimerRef.current);
          setPairingState("EXPIRED");
        }
      }, 1000);

      return () => {
        if (countdownTimerRef.current) clearInterval(countdownTimerRef.current);
      };
    }
  }, [pairingState, expiresAt]);

  // Start link flow
  const handleStartLink = async () => {
    setPairingState("PAIRING");
    setAttemptCount(0);
    setLastErrorMsg(null);
    try {
      const res = await backendService.startTelegramLink();
      if (res.ok && res.otp && res.request_id) {
        setRequestId(res.request_id);
        setOtpCode(res.otp);
        setDeepLink(res.deep_link || "");
        setExpiresAt(res.expires_at || Date.now() / 1000 + 300);
        setRemainingSeconds(res.ttl_seconds || 300);
        if (res.bot_username) {
          setBotStatus((prev) =>
            prev
              ? { ...prev, bot_username: res.bot_username! }
              : {
                  ok: true,
                  configured: true,
                  bot_username: res.bot_username!,
                  active_links_count: 0,
                  pending_requests_count: 1,
                }
          );
        }
        setPairingState("WAITING_FOR_OTP");
        showToast("6 xonali tasdiqlash kodi tayyorlandi");
      } else {
        const errText = res.error || "Ulanish kodini olishda xatolik";
        setLastErrorMsg(errText);
        showToast(errText);
        setPairingState("FAILED");
      }
    } catch {
      const errText = "Server bilan bog'lanishda xatolik";
      setLastErrorMsg(errText);
      showToast(errText);
      setPairingState("FAILED");
    }
  };

  // Copy OTP code
  const handleCopyCode = () => {
    if (!otpCode) return;
    navigator.clipboard.writeText(otpCode);
    setCopied(true);
    showToast("Kod nusxalandi!");
    setTimeout(() => setCopied(false), 2000);
  };

  // Unlink account
  const handleUnlink = async () => {
    if (!window.confirm("Haqiqatan ham Telegram hisobini Misadan uzmoqchimisiz?")) return;
    try {
      const res = await backendService.unlinkTelegramAccount();
      if (res.ok) {
        showToast("Telegram hisobi muvaffaqiyatli uzildi");
        setPairingState("NOT_CONNECTED");
        loadStatus();
      } else {
        showToast(res.error || "Uzishda xatolik");
      }
    } catch {
      showToast("Server xatosi");
    }
  };

  // Manual verify in UI
  const handleManualVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualOtp || !manualTgId) {
      showToast("OTP kod va Telegram ID kiritilishi shart");
      return;
    }
    const tgInt = parseInt(manualTgId.trim(), 10);
    if (isNaN(tgInt) || tgInt <= 0) {
      showToast("Telegram ID faqat musbat butun son bo'lishi kerak");
      return;
    }

    setIsVerifying(true);
    try {
      const res = await backendService.verifyTelegramLink(
        manualOtp.trim(),
        tgInt,
        undefined,
        undefined,
        requestId || undefined
      );
      if (res.ok) {
        showToast("Muvaffaqiyatli bog'landi!");
        setManualOtp("");
        loadStatus();
      } else {
        showToast(res.error || "Tasdiqlashda xatolik");
      }
    } catch {
      showToast("Tarmoq xatosi");
    } finally {
      setIsVerifying(false);
    }
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div
      style={{
        flex: 1,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "transparent",
        color: "var(--text-primary, #F8FAFC)",
        overflowY: "auto",
        position: "relative",
      }}
    >
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            backgroundColor: "rgba(18, 22, 34, 0.9)",
            color: "#F8FAFC",
            border: "1px solid #4EDEA3",
            padding: "12px 20px",
            borderRadius: "12px",
            fontSize: "14px",
            boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            animation: "fadeIn 0.2s ease-out",
          }}
        >
          <CheckIcon size={16} color="#4EDEA3" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "20px 32px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          backgroundColor: "rgba(18, 22, 34, 0.55)",
          backdropFilter: "blur(24px)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {onNavigateHome && (
            <button
              onClick={onNavigateHome}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted, #94A3B8)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                padding: "8px",
                borderRadius: "6px",
              }}
              title="Bosh sahifaga qaytish"
            >
              <ArrowLeftIcon size={18} />
            </button>
          )}
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "12px",
              backgroundColor: "rgba(147, 3, 197, 0.2)",
              border: "1px solid rgba(192, 76, 253, 0.35)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#E8B3FF",
            }}
          >
            <TelegramIcon size={22} />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 style={{ fontSize: "20px", fontWeight: 700, margin: 0, fontFamily: "var(--font-display)" }}>
                Universal Telegram Bot
              </h1>
              <span
                style={{
                  fontSize: "11px",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  backgroundColor: "rgba(147, 3, 197, 0.22)",
                  color: "#E8B3FF",
                  border: "1px solid rgba(192, 76, 253, 0.35)",
                  fontWeight: 600,
                }}
              >
                Telegram Gateway
              </span>
            </div>
            <p style={{ fontSize: "13px", color: "var(--text-muted, #94A3B8)", margin: "4px 0 0 0" }}>
              Misa hisobingizni yagona universal Telegram bot bilan xavfsiz OTP orqali bog'lang
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            onClick={loadStatus}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 14px",
              backgroundColor: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "8px",
              color: "#E2E8F0",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            <RefreshIcon size={14} />
            <span>Yangilash</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ flex: 1, padding: "32px", maxWidth: "960px", margin: "0 auto", width: "100%" }}>
        {/* Bot System Health Bar */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "16px",
            marginBottom: "32px",
          }}
        >
          <div
            style={{
              padding: "16px",
              borderRadius: "12px",
              backgroundColor: "rgba(18, 22, 34, 0.55)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
            }}
          >
            <div style={{ fontSize: "12px", color: "#94A3B8", marginBottom: "4px" }}>Bot Nomi</div>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "#E8B3FF" }}>
              @{(botStatus?.bot_username || "Misa_ai_agent_bot").replace(/^@/, "")}
            </div>
          </div>
          <div
            style={{
              padding: "16px",
              borderRadius: "12px",
              backgroundColor: "rgba(30, 41, 59, 0.5)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
            }}
          >
            <div style={{ fontSize: "12px", color: "#94A3B8", marginBottom: "4px" }}>Faol Bog'lanishlar</div>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "#10B981" }}>
              {botStatus?.active_links_count ?? 0} ta foydalanuvchi
            </div>
          </div>
          <div
            style={{
              padding: "16px",
              borderRadius: "12px",
              backgroundColor: "rgba(30, 41, 59, 0.5)",
              border: "1px solid rgba(255, 255, 255, 0.06)",
            }}
          >
            <div style={{ fontSize: "12px", color: "#94A3B8", marginBottom: "4px" }}>Xavfsizlik Standarti</div>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "#F59E0B" }}>
              Salted SHA-256 (Anti-enumeration)
            </div>
          </div>
        </div>

        {/* State 0: LOADING or PAIRING */}
        {(pairingState === "LOADING" || pairingState === "PAIRING") && (
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.8)",
              border: "1px solid rgba(56, 189, 248, 0.25)",
              borderRadius: "16px",
              padding: "40px 32px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "14px",
                backgroundColor: "rgba(56, 189, 248, 0.12)",
                border: "1px solid rgba(56, 189, 248, 0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px auto",
                color: "#38BDF8",
              }}
            >
              <TelegramIcon size={28} />
            </div>
            <h2 style={{ fontSize: "18px", fontWeight: 600, margin: "0 0 8px 0" }}>
              {pairingState === "PAIRING"
                ? "6 xonali tasdiqlash kodi tayyorlanmoqda..."
                : "Telegram bog'lanish holati tekshirilmoqda..."}
            </h2>
            <p style={{ fontSize: "13px", color: "#94A3B8", margin: 0 }}>
              Iltimos, bir necha soniya kuting...
            </p>
          </div>
        )}

        {/* State 1: CONNECTED */}
        {pairingState === "CONNECTED" && accountInfo?.link && (
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.8)",
              border: "1px solid rgba(16, 185, 129, 0.4)",
              borderRadius: "16px",
              padding: "32px",
              boxShadow: "0 8px 32px rgba(16, 185, 129, 0.08)",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
              <div style={{ display: "flex", gap: "16px" }}>
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "12px",
                    backgroundColor: "rgba(16, 185, 129, 0.15)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#10B981",
                  }}
                >
                  <ShieldCheckIcon size={26} />
                </div>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <h2 style={{ fontSize: "18px", fontWeight: 600, margin: 0 }}>
                      Telegram Hisobi Ulangan
                    </h2>
                    <span
                      style={{
                        padding: "2px 10px",
                        borderRadius: "10px",
                        backgroundColor: "rgba(16, 185, 129, 0.2)",
                        color: "#10B981",
                        fontSize: "12px",
                        fontWeight: 600,
                      }}
                    >
                      FAOL (ACTIVE)
                    </span>
                  </div>
                  <p style={{ fontSize: "13px", color: "#94A3B8", margin: "6px 0 0 0" }}>
                    Sizning Misa profilingiz ushbu Telegram identifikatori bilan xavfsiz bog'langan.
                  </p>
                </div>
              </div>

              <button
                onClick={handleUnlink}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 16px",
                  backgroundColor: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  borderRadius: "8px",
                  color: "#EF4444",
                  fontSize: "13px",
                  fontWeight: 500,
                  cursor: "pointer",
                }}
              >
                <UnlinkIcon size={14} />
                <span>Bog'lanishni uzish</span>
              </button>
            </div>

            <hr style={{ border: "none", borderTop: "1px solid rgba(255, 255, 255, 0.08)", margin: "24px 0" }} />

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "20px",
              }}
            >
              <div>
                <div style={{ fontSize: "12px", color: "#94A3B8", marginBottom: "4px" }}>Misa User ID</div>
                <div style={{ fontSize: "14px", fontWeight: 600 }}>
                  {accountInfo.link.misa_user_id}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "12px", color: "#94A3B8", marginBottom: "4px" }}>Telegram Raqamli ID</div>
                <div style={{ fontSize: "14px", fontWeight: 600, fontFamily: "monospace", color: "#38BDF8" }}>
                  {accountInfo.link.telegram_user_id}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "12px", color: "#94A3B8", marginBottom: "4px" }}>Telegram Foydalanuvchi</div>
                <div style={{ fontSize: "14px", fontWeight: 600 }}>
                  {accountInfo.telegram_identity?.username ? `@${accountInfo.telegram_identity.username}` : "Kiritilmagan"}
                </div>
              </div>
              <div>
                <div style={{ fontSize: "12px", color: "#94A3B8", marginBottom: "4px" }}>Bog'langan Sana</div>
                <div style={{ fontSize: "14px", color: "#E2E8F0" }}>
                  {new Date(accountInfo.link.linked_at * 1000).toLocaleString("uz-UZ")}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* State 2: WAITING_FOR_OTP */}
        {pairingState === "WAITING_FOR_OTP" && (
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.8)",
              border: "1px solid rgba(56, 189, 248, 0.4)",
              borderRadius: "16px",
              padding: "32px",
              boxShadow: "0 8px 32px rgba(56, 189, 248, 0.08)",
            }}
          >
            <div style={{ textAlign: "center", marginBottom: "28px" }}>
              <div style={{ display: "flex", justifyContent: "center", gap: "10px", flexWrap: "wrap", marginBottom: "12px" }}>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "4px 14px",
                    borderRadius: "20px",
                    backgroundColor: "rgba(245, 158, 11, 0.15)",
                    color: "#F59E0B",
                    fontSize: "12px",
                    fontWeight: 600,
                  }}
                >
                  <ClockIcon size={14} />
                  <span>Qolgan vaqt: {formatTimer(remainingSeconds)}</span>
                </div>
                {attemptCount > 0 && (
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      padding: "4px 14px",
                      borderRadius: "20px",
                      backgroundColor: "rgba(239, 68, 68, 0.15)",
                      color: "#F87171",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    <AlertTriangleIcon size={14} />
                    <span>Noto'g'ri kod urinishlari: {attemptCount}/5</span>
                  </div>
                )}
              </div>
              <h2 style={{ fontSize: "22px", fontWeight: 700, margin: "0 0 8px 0" }}>
                Telegram Botda Kodni Kiriting
              </h2>
              <p style={{ fontSize: "14px", color: "#94A3B8", margin: 0, maxWidth: "560px", marginInline: "auto" }}>
                Quyidagi bir martalik 6 xonali tasdiqlash kodini nusxalang va botga yuboring yoki to'g'ridan-to'g'ri havolani bosing.
              </p>
            </div>

            {/* Big Monospace OTP Display */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "14px",
                marginBottom: "28px",
                flexWrap: "wrap",
              }}
            >
              <div
                style={{
                  fontSize: "36px",
                  fontWeight: 800,
                  letterSpacing: "8px",
                  fontFamily: "monospace",
                  backgroundColor: "rgba(30, 41, 59, 0.8)",
                  border: "2px solid #10B981",
                  borderRadius: "14px",
                  padding: "16px 32px",
                  color: "#10B981",
                  boxShadow: "0 0 24px rgba(16, 185, 129, 0.2)",
                  userSelect: "all",
                }}
              >
                {otpCode}
              </div>
              <button
                onClick={handleCopyCode}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "56px",
                  height: "56px",
                  borderRadius: "12px",
                  backgroundColor: copied ? "#10B981" : "rgba(255, 255, 255, 0.08)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: copied ? "#0B0F17" : "#F8FAFC",
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                }}
                title="Kodni nusxalash"
              >
                {copied ? <CheckIcon size={22} /> : <CopyIcon size={22} />}
              </button>
            </div>

            {/* Action Buttons: Open Telegram, Recheck Status, or Cancel */}
            <div style={{ display: "flex", justifyContent: "center", gap: "12px", flexWrap: "wrap", marginBottom: "32px" }}>
              {deepLink && (
                <button
                  type="button"
                  onClick={() => backendService.openExternalUrl(deepLink)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "10px",
                    backgroundColor: "#0284C7",
                    color: "#FFFFFF",
                    padding: "12px 24px",
                    borderRadius: "10px",
                    fontWeight: 600,
                    fontSize: "14px",
                    border: "none",
                    cursor: "pointer",
                    boxShadow: "0 4px 14px rgba(2, 132, 199, 0.35)",
                  }}
                >
                  <TelegramIcon size={18} />
                  <span>Telegram orqali ochish</span>
                  <ExternalLinkIcon size={14} />
                </button>
              )}

              <button
                type="button"
                onClick={() => checkCurrentRequestStatus(true)}
                disabled={isRechecking}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "12px 20px",
                  backgroundColor: "rgba(16, 185, 129, 0.12)",
                  border: "1px solid rgba(16, 185, 129, 0.35)",
                  borderRadius: "10px",
                  color: "#10B981",
                  fontSize: "14px",
                  fontWeight: 600,
                  cursor: isRechecking ? "wait" : "pointer",
                }}
              >
                <RefreshIcon size={14} />
                <span>{isRechecking ? "Tekshirilmoqda..." : "Holatni tekshirish"}</span>
              </button>

              <button
                type="button"
                onClick={() => setPairingState("NOT_CONNECTED")}
                style={{
                  padding: "12px 20px",
                  backgroundColor: "transparent",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "10px",
                  color: "#94A3B8",
                  fontSize: "14px",
                  cursor: "pointer",
                }}
              >
                Bekor qilish
              </button>
            </div>

            {/* Step-by-step instructions */}
            <div
              style={{
                backgroundColor: "rgba(30, 41, 59, 0.4)",
                borderRadius: "12px",
                padding: "20px",
                border: "1px solid rgba(255, 255, 255, 0.06)",
              }}
            >
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#E2E8F0", marginBottom: "12px" }}>
                💡 Qanday bog'lanish kerak:
              </div>
              <ol style={{ margin: 0, paddingLeft: "20px", fontSize: "13px", color: "#94A3B8", lineHeight: "1.8" }}>
                <li>Yuqoridagi 6 xonali kodni nusxalang.</li>
                <li>
                  Telegramda <strong style={{ color: "#E8B3FF" }}>@{(botStatus?.bot_username || "Misa_ai_agent_bot").replace(/^@/, "")}</strong> botini oching.
                </li>
                <li>
                  Kodni shunchaki botga yuboring (masalan: <code style={{ color: "#10B981" }}>{otpCode}</code>) yoki{" "}
                  <code style={{ color: "#10B981" }}>/link {otpCode}</code> buyrug'ini bering.
                </li>
                <li>Ulanish tasdiqlangach, ushbu oyna avtomatik tarzda yangilanadi.</li>
              </ol>
            </div>
          </div>
        )}

        {/* State 3: EXPIRED or FAILED */}
        {(pairingState === "EXPIRED" || pairingState === "FAILED") && (
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.8)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              borderRadius: "16px",
              padding: "32px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                backgroundColor: "rgba(239, 68, 68, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px auto",
                color: "#EF4444",
              }}
            >
              <AlertTriangleIcon size={24} />
            </div>
            <h2 style={{ fontSize: "18px", fontWeight: 600, margin: "0 0 8px 0" }}>
              {pairingState === "EXPIRED" ? "Kodning Muddati Tugagan" : "Bog'lanishda Xatolik"}
            </h2>
            <p style={{ fontSize: "14px", color: "#94A3B8", margin: "0 0 24px 0" }}>
              {pairingState === "EXPIRED"
                ? "5 daqiqalik ulanish kodi eskirgan. Yangi kod olish uchun quyidagi tugmani bosing."
                : lastErrorMsg || "Kod noto'g'ri kiritilgan yoki maksimal urinishlar soni tugagan."}
            </p>
            <div style={{ display: "flex", justifyContent: "center", gap: "12px", flexWrap: "wrap" }}>
              <button
                onClick={handleStartLink}
                style={{
                  padding: "12px 24px",
                  backgroundColor: "#10B981",
                  border: "none",
                  borderRadius: "10px",
                  color: "#0B0F17",
                  fontSize: "14px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Yangi Kod Olish
              </button>
              <button
                onClick={loadStatus}
                style={{
                  padding: "12px 20px",
                  backgroundColor: "rgba(255, 255, 255, 0.06)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "10px",
                  color: "#E2E8F0",
                  fontSize: "14px",
                  cursor: "pointer",
                }}
              >
                Holatni qayta tekshirish
              </button>
            </div>
          </div>
        )}

        {/* State 4: NOT_CONNECTED */}
        {(pairingState === "NOT_CONNECTED" || pairingState === "REVOKED") && (
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.8)",
              border: "1px solid rgba(255, 255, 255, 0.08)",
              borderRadius: "16px",
              padding: "40px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "64px",
                height: "64px",
                borderRadius: "16px",
                backgroundColor: "rgba(56, 189, 248, 0.1)",
                border: "1px solid rgba(56, 189, 248, 0.2)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 20px auto",
                color: "#38BDF8",
              }}
            >
              <TelegramIcon size={32} />
            </div>

            <h2 style={{ fontSize: "20px", fontWeight: 700, margin: "0 0 10px 0" }}>
              Telegram Hisobingizni Bog'lang
            </h2>
            <p
              style={{
                fontSize: "14px",
                color: "#94A3B8",
                margin: "0 auto 28px auto",
                maxWidth: "520px",
                lineHeight: "1.6",
              }}
            >
              Misa AI universal Telegram botiga ulaning va hisobingiz orqali shaxsiy bildirishnomalar hamda buyruqlardan foydalaning.
            </p>

            <button
              onClick={handleStartLink}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "10px",
                backgroundColor: "#10B981",
                color: "#0B0F17",
                padding: "14px 28px",
                borderRadius: "12px",
                fontWeight: 700,
                fontSize: "15px",
                border: "none",
                cursor: "pointer",
                boxShadow: "0 4px 20px rgba(16, 185, 129, 0.3)",
              }}
            >
              <TelegramIcon size={20} />
              <span>Bog'lanish Kodini Olish</span>
            </button>
          </div>
        )}

        {/* Manual Verification Form (Direct Tester/Developer Interface) */}
        <div
          style={{
            marginTop: "32px",
            backgroundColor: "rgba(15, 23, 42, 0.4)",
            border: "1px solid rgba(255, 255, 255, 0.05)",
            borderRadius: "12px",
            padding: "20px",
          }}
        >
          <div style={{ fontSize: "13px", fontWeight: 600, color: "#94A3B8", marginBottom: "12px" }}>
            🛠️ To'g'ridan-to'g'ri Tasdiqlash (Qo'lda sinash uchun):
          </div>
          <form onSubmit={handleManualVerify} style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <input
              type="text"
              placeholder="6 xonali OTP kod"
              value={manualOtp}
              onChange={(e) => setManualOtp(e.target.value)}
              style={{
                backgroundColor: "rgba(0,0,0,0.4)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                padding: "8px 12px",
                color: "#F8FAFC",
                fontSize: "13px",
                width: "160px",
              }}
            />
            <input
              type="text"
              placeholder="Telegram Numeric ID"
              value={manualTgId}
              onChange={(e) => setManualTgId(e.target.value)}
              style={{
                backgroundColor: "rgba(0,0,0,0.4)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "8px",
                padding: "8px 12px",
                color: "#F8FAFC",
                fontSize: "13px",
                width: "180px",
              }}
            />
            <button
              type="submit"
              disabled={isVerifying}
              style={{
                padding: "8px 16px",
                backgroundColor: "rgba(255, 255, 255, 0.08)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                borderRadius: "8px",
                color: "#F8FAFC",
                fontSize: "13px",
                cursor: "pointer",
              }}
            >
              {isVerifying ? "Tekshirilmoqda..." : "Tasdiqlash"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};
