import { useState, useEffect, useCallback, lazy, Suspense } from "react";
import { AppShell } from "./layout/AppShell";

const LandingPage = lazy(() => import("./pages/LandingPage").then(m => ({ default: m.LandingPage })));
const ChatPage = lazy(() => import("./pages/ChatPage").then(m => ({ default: m.ChatPage })));
const VoicePage = lazy(() => import("./pages/VoicePage").then(m => ({ default: m.VoicePage })));
const CommandsPage = lazy(() => import("./pages/CommandsPage").then(m => ({ default: m.CommandsPage })));
const MemoryPage = lazy(() => import("./pages/MemoryPage").then(m => ({ default: m.MemoryPage })));
const SchedulerPage = lazy(() => import("./pages/SchedulerPage").then(m => ({ default: m.SchedulerPage })));
const PluginsPage = lazy(() => import("./pages/PluginsPage").then(m => ({ default: m.PluginsPage })));
const AccountPage = lazy(() => import("./pages/AccountPage").then(m => ({ default: m.AccountPage })));
const RemoteControlPage = lazy(() => import("./pages/RemoteControlPage").then(m => ({ default: m.RemoteControlPage })));
const DevicesPage = lazy(() => import("./pages/DevicesPage").then(m => ({ default: m.DevicesPage })));
const TelegramIntegrationPage = lazy(() => import("./pages/TelegramIntegrationPage").then(m => ({ default: m.TelegramIntegrationPage })));
const AuthPage = lazy(() => import("./pages/AuthPage").then(m => ({ default: m.AuthPage })));
import { CommandPalette } from "./components/CommandPalette";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { UpdateModal } from "./components/UpdateModal";
import { backendService, MikasaAuthUser } from "./services/backendService";
import { UpdateService, UpdateCheckResponse } from "./services/updateService";
import { supabase, isSupabaseConfigured } from "./services/supabaseClient";
import "./styles/globals.css";

export type MisaAuthUser = MikasaAuthUser;

export function applyMisaAppearanceSettings() {
  try {
    const raw = localStorage.getItem("misa_appearance_settings");
    if (!raw) return;
    const parsed = JSON.parse(raw);
    const root = document.documentElement;

    // 1. Theme mode
    const theme = parsed.theme || "dark";
    if (theme === "light") {
      root.classList.add("theme-light");
      root.classList.remove("dark");
    } else if (theme === "system") {
      const prefersLight = window.matchMedia?.("(prefers-color-scheme: light)").matches;
      if (prefersLight) {
        root.classList.add("theme-light");
        root.classList.remove("dark");
      } else {
        root.classList.remove("theme-light");
        root.classList.add("dark");
      }
    } else {
      root.classList.remove("theme-light");
      root.classList.add("dark");
    }

    // 2. Accent color
    if (parsed.accentColor) {
      root.style.setProperty("--misa-accent", parsed.accentColor);
      root.style.setProperty("--primary", parsed.accentColor);
    }
    if (parsed.accentGlow) {
      root.style.setProperty("--misa-accent-glow", parsed.accentGlow);
      root.style.setProperty("--primary-glow", parsed.accentGlow);
    }

    // 3. Glass opacity (30% - 100%)
    if (typeof parsed.glassOpacity === "number") {
      const normalized = Math.max(0.25, Math.min(0.92, parsed.glassOpacity / 100));
      root.style.setProperty("--misa-glass-opacity", String(normalized));
    }

    // 4. Interface animations
    if (parsed.animationsEnabled === false) {
      root.classList.add("no-animations");
    } else {
      root.classList.remove("no-animations");
    }
  } catch {
    // Ignore storage parse issues
  }
}

function App() {
  const [activePath, setActivePath] = useState<string>("/");
  const [initialChatQuery, setInitialChatQuery] = useState<string | undefined>(undefined);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);

  // Phase 48: Auto-update modal state
  const [updateModalOpen, setUpdateModalOpen] = useState<boolean>(false);
  const [updateInfo, setUpdateInfo] = useState<UpdateCheckResponse | null>(null);

  // Check for updates on startup (after 4s delay)
  useEffect(() => {
    applyMisaAppearanceSettings();
    const timer = setTimeout(async () => {
      try {
        const res = await UpdateService.checkForUpdates();
        if (res && res.ok && res.update_available) {
          setUpdateInfo(res);
          setUpdateModalOpen(true);
        }
      } catch {
        // Silent fail on startup update check
      }
    }, 4000);
    return () => clearTimeout(timer);
  }, []);

  const handleOpenUpdateModal = useCallback((info: UpdateCheckResponse) => {
    setUpdateInfo(info);
    setUpdateModalOpen(true);
  }, []);

  // Auth & Profile State
  const [authChecking, setAuthChecking] = useState<boolean>(true);
  const [currentUser, setCurrentUser] = useState<MisaAuthUser | null>(null);
  const [userName, setUserName] = useState<string>(() => {
    return localStorage.getItem("misa_user_name") || "Ustoz";
  });
  const [avatarStyle, setAvatarStyle] = useState<string>(() => {
    return localStorage.getItem("misa_user_avatar") || "cosmic";
  });

  // Verify existing session on startup and subscribe to auth changes
  useEffect(() => {
    let mounted = true;

    const handleOAuthRedirectIfAny = async () => {
      const hash = window.location.hash;
      const search = window.location.search;
      if (
        (hash && (hash.includes("access_token=") || hash.includes("error="))) ||
        (search && (search.includes("code=") || search.includes("error=")))
      ) {
        try {
          const { data } = await supabase.auth.getSession();
          if (data?.session?.user && mounted) {
            if (data.session.access_token) {
              backendService.setAuthToken(data.session.access_token);
            }
            const u: MisaAuthUser = {
              id: data.session.user.id,
              username:
                data.session.user.user_metadata?.full_name ||
                data.session.user.user_metadata?.name ||
                data.session.user.email?.split("@")[0] ||
                "User",
              email: data.session.user.email || "",
              is_active: true,
              is_verified: true,
              created_at: Date.now() / 1000,
              avatar_url:
                data.session.user.user_metadata?.avatar_url ||
                data.session.user.user_metadata?.picture ||
                undefined,
              provider: data.session.user.app_metadata?.provider || "google",
            };
            setCurrentUser(u);
            if (u.username) {
              setUserName(u.username);
              localStorage.setItem("misa_user_name", u.username);
              localStorage.setItem("misa_user_name", u.username);
            }
            window.history.replaceState({}, document.title, window.location.pathname);
          }
        } catch (err) {
          console.error("OAuth redirect check error:", err);
        }
      }
    };

    const initAuth = async () => {
      try {
        await handleOAuthRedirectIfAny();

        if (isSupabaseConfigured) {
          const {
            data: { session },
          } = await supabase.auth.getSession();
          if (session?.access_token) {
            backendService.setAuthToken(session.access_token);
          }
        }

        const user = await backendService.getCurrentAuthUser();
        if (!mounted) return;
        if (user) {
          setCurrentUser(user);
          if (user.username) {
            setUserName(user.username);
            localStorage.setItem("misa_user_name", user.username);
            localStorage.setItem("misa_user_name", user.username);
          }
        } else {
          setCurrentUser(null);
        }
      } catch {
        if (mounted) {
          setCurrentUser(null);
        }
      } finally {
        if (mounted) {
          setAuthChecking(false);
        }
      }
    };

    initAuth();

    const unsubAuth = backendService.onAuthChange((user) => {
      if (!mounted) return;
      setCurrentUser(user);
      if (user?.username) {
        setUserName(user.username);
      }
    });

    backendService
      .getAccount()
      .then((data) => {
        if (!mounted) return;
        const freshName =
          data.name ||
          localStorage.getItem("misa_user_name") ||
          localStorage.getItem("misa_user_name") ||
          "Ustoz";
        const freshAvatar =
          data.avatar ||
          localStorage.getItem("misa_user_avatar") ||
          localStorage.getItem("misa_user_avatar") ||
          "cosmic";
        setUserName(freshName);
        setAvatarStyle(freshAvatar);
        localStorage.setItem("misa_user_name", freshName);
        localStorage.setItem("misa_user_name", freshName);
      })
      .catch(() => {});

    const unsubStatus = backendService.onStatusChange((status) => {
      if (mounted && status.user) {
        setUserName(status.user);
      }
    });

    return () => {
      mounted = false;
      unsubAuth();
      unsubStatus();
    };
  }, []);

  const handleProfileChange = (newName: string, newAvatar?: string) => {
    if (newName) {
      setUserName(newName);
      localStorage.setItem("misa_user_name", newName);
      localStorage.setItem("misa_user_name", newName);
    }
    if (newAvatar) {
      setAvatarStyle(newAvatar);
      localStorage.setItem("misa_user_avatar", newAvatar);
      localStorage.setItem("misa_user_avatar", newAvatar);
    }
  };

  // Global Keyboard Shortcuts (Ctrl+K, Ctrl+1..9)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
        return;
      }

      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case "1":
            e.preventDefault();
            handleNavigate("/");
            break;
          case "2":
            e.preventDefault();
            handleNavigate("/chat");
            break;
          case "3":
            e.preventDefault();
            handleNavigate("/memory");
            break;
          case "4":
            e.preventDefault();
            handleNavigate("/scheduler");
            break;
          case "5":
            e.preventDefault();
            handleNavigate("/commands");
            break;
          case "6":
            e.preventDefault();
            handleNavigate("/plugins");
            break;
          case "7":
            e.preventDefault();
            handleNavigate("/remote");
            break;
          case "8":
            e.preventDefault();
            handleNavigate("/devices");
            break;
          case "9":
            e.preventDefault();
            handleNavigate("/account");
            break;
          case "0":
            e.preventDefault();
            handleNavigate("/telegram");
            break;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleNavigate = (path: string) => {
    if (path !== "/chat") {
      setInitialChatQuery(undefined);
    }
    setActivePath(path);
  };

  const handleStartChatWithQuery = (query?: string) => {
    setInitialChatQuery(query);
    setActivePath("/chat");
  };

  const renderContent = () => {
    switch (activePath) {
      case "/":
        return (
          <LandingPage
            userName={userName}
            onStartChat={handleStartChatWithQuery}
            onStartVoice={() => handleNavigate("/voice")}
            onNavigate={handleNavigate}
          />
        );
      case "/chat":
        return (
          <ChatPage
            userName={userName}
            initialQuery={initialChatQuery}
            onNavigateHome={() => handleNavigate("/")}
            onNavigateVoice={() => handleNavigate("/voice")}
            onNavigate={handleNavigate}
          />
        );
      case "/voice":
        return (
          <VoicePage
            userName={userName}
            onNavigateHome={() => handleNavigate("/")}
            onNavigateChat={() => handleNavigate("/chat")}
          />
        );
      case "/commands":
        return <CommandsPage onNavigateHome={() => handleNavigate("/")} />;
      case "/memory":
        return <MemoryPage onNavigateHome={() => handleNavigate("/")} />;
      case "/scheduler":
        return (
          <SchedulerPage
            onNavigateHome={() => handleNavigate("/")}
            onAskMisa={handleStartChatWithQuery}
          />
        );
      case "/plugins":
        return <PluginsPage onNavigateHome={() => handleNavigate("/")} />;
      case "/remote":
        return <RemoteControlPage onNavigateHome={() => handleNavigate("/")} />;
      case "/devices":
        return <DevicesPage onNavigateHome={() => handleNavigate("/")} />;
      case "/telegram":
        return <TelegramIntegrationPage onNavigateHome={() => handleNavigate("/")} />;
      case "/account":
        return (
          <AccountPage
            onNavigateHome={() => handleNavigate("/")}
            onNavigate={handleNavigate}
            onProfileChange={handleProfileChange}
            currentUser={currentUser}
            onLogout={() => {
              setCurrentUser(null);
            }}
            onOpenUpdateModal={handleOpenUpdateModal}
          />
        );
      default:
        return (
          <LandingPage
            userName={userName}
            onStartChat={handleStartChatWithQuery}
            onStartVoice={() => handleNavigate("/voice")}
            onNavigate={handleNavigate}
          />
        );
    }
  };

  if (authChecking) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          width: "100vw",
          backgroundColor: "#02060E",
          color: "#F5F0FF",
          fontFamily: "var(--font-family)",
          gap: "14px",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "50%",
            border: "2.5px solid rgba(192, 76, 253, 0.2)",
            borderTopColor: "#C04CFD",
            animation: "orb-particle-spin 0.9s linear infinite",
          }}
        />
        <div style={{ fontSize: "13.5px", color: "var(--text-secondary)", fontWeight: 500 }}>
          Misa AI v9.0 ishga tushirilmoqda...
        </div>
      </div>
    );
  }

  if (!currentUser) {
    return (
      <ErrorBoundary onReset={() => setCurrentUser(null)}>
        <Suspense
          fallback={
            <div
              style={{
                display: "flex",
                height: "100vh",
                width: "100vw",
                alignItems: "center",
                justifyContent: "center",
                background: "var(--bg-base, #0E1422)",
                color: "var(--text-secondary, #94A3B8)",
                fontSize: "13px",
              }}
            >
              Yuklanmoqda...
            </div>
          }
        >
          <AuthPage
            onAuthSuccess={(user) => {
              setCurrentUser(user);
              if (user.username) {
                setUserName(user.username);
                localStorage.setItem("misa_user_name", user.username);
              }
            }}
          />
        </Suspense>
      </ErrorBoundary>
    );
  }

  return (
    <AppShell
      activePath={activePath}
      onNavigate={handleNavigate}
      onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      userName={userName}
      avatarStyle={avatarStyle}
      avatarUrl={currentUser?.avatar_url}
    >
      <ErrorBoundary key={activePath} onReset={() => handleNavigate("/")}>
        <Suspense
          fallback={
            <div
              style={{
                display: "flex",
                height: "100%",
                width: "100%",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-secondary, #94A3B8)",
                fontSize: "13px",
                padding: "40px",
              }}
            >
              Sahifa yuklanmoqda...
            </div>
          }
        >
          {renderContent()}
        </Suspense>
      </ErrorBoundary>
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onNavigate={handleNavigate}
        onExecuteQuery={handleStartChatWithQuery}
      />
      <UpdateModal
        isOpen={updateModalOpen}
        onClose={() => setUpdateModalOpen(false)}
        updateInfo={updateInfo}
      />
    </AppShell>
  );
}

export default App;
