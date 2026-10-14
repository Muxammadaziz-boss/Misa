import React, { useState, useEffect, useRef } from "react";
import { MinimizeIcon, MaximizeIcon, RestoreIcon, CloseIcon } from "./icons/Icons";

interface WindowControlsProps {
  className?: string;
}

export const WindowControls: React.FC<WindowControlsProps> = ({ className = "" }) => {
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    const checkMaximized = async () => {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        const max = await invoke<boolean>("app_is_maximized");
        setIsMaximized(max);
      } catch {
        try {
          const { getCurrentWindow } = await import("@tauri-apps/api/window");
          const max = await getCurrentWindow().isMaximized();
          setIsMaximized(max);
        } catch {
          // Browser fallback
        }
      }
    };
    checkMaximized();

    const setupListener = async () => {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        unlisten = await getCurrentWindow().onResized(async () => {
          checkMaximized();
        });
      } catch {
        // Browser fallback
      }
    };
    setupListener();

    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  const handleMinimize = async () => {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("app_minimize");
    } catch {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().minimize();
      } catch (err) {
        console.error("[WindowControls] Minimize error:", err);
      }
    }
  };

  const handleMaximize = async () => {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      const max = await invoke<boolean>("app_toggle_maximize");
      setIsMaximized(max);
    } catch {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().toggleMaximize();
        const max = await getCurrentWindow().isMaximized();
        setIsMaximized(max);
      } catch {
        setIsMaximized((prev) => !prev);
      }
    }
  };

  const isClosingRef = useRef(false);

  const handleClose = async () => {
    if (isClosingRef.current) return;
    isClosingRef.current = true;
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("app_close");
    } catch {
      try {
        const { getCurrentWindow } = await import("@tauri-apps/api/window");
        await getCurrentWindow().hide();
      } catch (err) {
        console.error("[WindowControls] Hide to tray error:", err);
      }
    } finally {
      // 500ms dan so'ng yana bosish imkonini beramiz
      setTimeout(() => {
        isClosingRef.current = false;
      }, 500);
    }
  };

  return (
    <div
      className={`window-controls ${className}`}
      style={{
        display: "flex",
        alignItems: "center",
        height: "34px",
        paddingRight: "4px",
        gap: "2px",
        flexShrink: 0,
        ...({ WebkitAppRegion: "no-drag" } as React.CSSProperties),
      }}
    >
      <button
        onClick={handleMinimize}
        title="Kichraytirish"
        aria-label="Kichraytirish"
        style={buttonStyle}
        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.08)")}
        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
      >
        <MinimizeIcon size={12} color="rgba(255, 255, 255, 0.82)" />
      </button>

      <button
        onClick={handleMaximize}
        title={isMaximized ? "Oldingi o‘lchamga qaytarish" : "Kattalashtirish"}
        aria-label={isMaximized ? "Oldingi o‘lchamga qaytarish" : "Kattalashtirish"}
        style={buttonStyle}
        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.08)")}
        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
      >
        {isMaximized ? (
          <RestoreIcon size={12} color="rgba(255, 255, 255, 0.82)" />
        ) : (
          <MaximizeIcon size={12} color="rgba(255, 255, 255, 0.82)" />
        )}
      </button>

      <button
        onClick={handleClose}
        title="Yopish"
        aria-label="Yopish"
        style={buttonStyle}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = "#EF4444";
          const svg = e.currentTarget.querySelector("svg");
          if (svg) svg.style.stroke = "#FFFFFF";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = "transparent";
          const svg = e.currentTarget.querySelector("svg");
          if (svg) svg.style.stroke = "rgba(255, 255, 255, 0.82)";
        }}
      >
        <CloseIcon size={12} color="rgba(255, 255, 255, 0.82)" />
      </button>
    </div>
  );
};

const buttonStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  width: "30px",
  height: "28px",
  borderRadius: "9999px",
  transition: "all 0.15s ease",
  cursor: "pointer",
  flexShrink: 0,
};
