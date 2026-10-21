// ========== ContextMenu.tsx ==========
// Misa AI v9.3 — Native Dark Glassmorphism Context Menu
// Brauzerning standart context menyusini o'rnini bosuvchi va matndan nusxa olish,
// qo'yish, qirqish, ovozda o'qish hamda Misa AI bilan tahlil qilish imkonini beruvchi tizim

import React, { useState, useEffect, useRef, useCallback } from "react";
import { backendService } from "../services/backendService";

interface ContextMenuProps {
  onNavigate?: (path: string) => void;
  onAskMisa?: (query: string) => void;
}

interface MenuTargetInfo {
  selectedText: string;
  isEditable: boolean;
  targetElement: HTMLElement | null;
  isLink: boolean;
  linkUrl: string;
  isImage: boolean;
  imageUrl: string;
  hasMessageText: boolean;
  messageText: string;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ onNavigate, onAskMisa }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [targetInfo, setTargetInfo] = useState<MenuTargetInfo>({
    selectedText: "",
    isEditable: false,
    targetElement: null,
    isLink: false,
    linkUrl: "",
    isImage: false,
    imageUrl: "",
    hasMessageText: false,
    messageText: "",
  });
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const menuRef = useRef<HTMLDivElement>(null);

  const closeMenu = useCallback(() => {
    setIsOpen(false);
  }, []);

  const showToast = (text: string) => {
    setCopyFeedback(text);
    setTimeout(() => {
      setCopyFeedback(null);
    }, 1800);
  };

  const handleContextMenu = useCallback((e: MouseEvent) => {
    // 1. Standart WebView2 / Brauzer context menyusini 100% to'xtatish
    e.preventDefault();

    const target = e.target as HTMLElement;
    const selection = window.getSelection();
    const selectedText = selection ? selection.toString().trim() : "";

    const isInput =
      target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
    const isContentEditable = target.isContentEditable;
    const isEditable = isInput || isContentEditable;

    const linkElem = target.closest("a");
    const linkUrl = linkElem ? linkElem.href : "";

    const imgElem = target.closest("img");
    const imageUrl = imgElem ? imgElem.src : "";

    // Xabarlar maydoni
    const messageContainer = target.closest(
      ".chat-message, .message-bubble, .misa-ultra-glass, [data-message-text]"
    );
    let messageText = "";
    if (messageContainer) {
      messageText =
        (messageContainer as HTMLElement).dataset?.messageText ||
        messageContainer.textContent?.trim() ||
        "";
      if (messageText.length > 500) {
        messageText = messageText.slice(0, 500) + "...";
      }
    }

    // Oyna chegaralariga moslash (Clamping)
    const estimatedWidth = 230;
    const estimatedHeight = 310;
    let posX = e.clientX;
    let posY = e.clientY;

    if (posX + estimatedWidth > window.innerWidth) {
      posX = Math.max(12, window.innerWidth - estimatedWidth - 12);
    }
    if (posY + estimatedHeight > window.innerHeight) {
      posY = Math.max(12, window.innerHeight - estimatedHeight - 12);
    }

    setTargetInfo({
      selectedText,
      isEditable,
      targetElement: target,
      isLink: !!linkUrl,
      linkUrl,
      isImage: !!imageUrl,
      imageUrl,
      hasMessageText: !!messageText && !selectedText,
      messageText,
    });

    setPosition({ x: posX, y: posY });
    setIsOpen(true);
  }, []);

  useEffect(() => {
    // Butun ilova bo'ylab kontekst menyuni tutib olish
    window.addEventListener("contextmenu", handleContextMenu, { capture: true });

    const handleMouseDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        closeMenu();
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        closeMenu();
      }
    };

    window.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", closeMenu);
    window.addEventListener("scroll", closeMenu, true);

    return () => {
      window.removeEventListener("contextmenu", handleContextMenu, { capture: true });
      window.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", closeMenu);
      window.removeEventListener("scroll", closeMenu, true);
    };
  }, [handleContextMenu, closeMenu]);

  // --- ACTIONS ---

  // 1. Nusxa olish (Copy)
  const handleCopy = async () => {
    closeMenu();
    let textToCopy = targetInfo.selectedText;

    if (!textToCopy && targetInfo.messageText) {
      textToCopy = targetInfo.messageText;
    }

    if (!textToCopy && targetInfo.targetElement) {
      if (
        targetInfo.targetElement instanceof HTMLInputElement ||
        targetInfo.targetElement instanceof HTMLTextAreaElement
      ) {
        textToCopy = targetInfo.targetElement.value;
      }
    }

    if (textToCopy) {
      try {
        await navigator.clipboard.writeText(textToCopy);
        showToast("Nusxa olindi ✓");
      } catch {
        // Fallback document.execCommand
        try {
          const ta = document.createElement("textarea");
          ta.value = textToCopy;
          ta.style.position = "fixed";
          ta.style.opacity = "0";
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
          showToast("Nusxa olindi ✓");
        } catch {
          showToast("Nusxa olishda xatolik");
        }
      }
    }
  };

  // 2. Qirqib olish (Cut)
  const handleCut = async () => {
    closeMenu();
    if (!targetInfo.isEditable || !targetInfo.targetElement) return;

    const el = targetInfo.targetElement;
    if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
      const start = el.selectionStart || 0;
      const end = el.selectionEnd || 0;
      const val = el.value;
      const cutText = val.substring(start, end);

      if (cutText) {
        try {
          await navigator.clipboard.writeText(cutText);
          el.value = val.substring(0, start) + val.substring(end);
          el.selectionStart = el.selectionEnd = start;
          el.dispatchEvent(new Event("input", { bubbles: true }));
          showToast("Qirqib olindi ✓");
        } catch {
          showToast("Qirqib olishda xatolik");
        }
      }
    }
  };

  // 3. Qo'yish (Paste)
  const handlePaste = async () => {
    closeMenu();
    if (!targetInfo.isEditable || !targetInfo.targetElement) return;

    try {
      const clipText = await navigator.clipboard.readText();
      const el = targetInfo.targetElement;

      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
        const start = el.selectionStart || 0;
        const end = el.selectionEnd || 0;
        const val = el.value;

        el.value = val.substring(0, start) + clipText + val.substring(end);
        el.selectionStart = el.selectionEnd = start + clipText.length;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.focus();
        showToast("Matn qo'yildi ✓");
      }
    } catch {
      showToast("Xotiradan o'qish imkonsiz");
    }
  };

  // 4. Barchasini tanlash (Select All)
  const handleSelectAll = () => {
    closeMenu();
    if (
      targetInfo.targetElement instanceof HTMLInputElement ||
      targetInfo.targetElement instanceof HTMLTextAreaElement
    ) {
      targetInfo.targetElement.focus();
      targetInfo.targetElement.select();
    } else {
      const selection = window.getSelection();
      const range = document.createRange();
      const targetContainer =
        targetInfo.targetElement?.closest(".misa-ultra-glass, main, #root") || document.body;
      range.selectNodeContents(targetContainer);
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  };

  // 5. Ovozda o'qish (TTS Speak)
  const handleSpeak = () => {
    closeMenu();
    const textToSpeak = targetInfo.selectedText || targetInfo.messageText;
    if (textToSpeak) {
      backendService.speakText(textToSpeak);
      showToast("Ovozda o'qilmoqda...");
    }
  };

  // 6. Misa'dan so'rash / Tahlil qilish
  const handleAskMisa = () => {
    closeMenu();
    const query = targetInfo.selectedText || targetInfo.messageText;
    if (query) {
      if (onAskMisa) {
        onAskMisa(`Quyidagi matnni tushuntirib va tahlil qilib ber:\n"${query}"`);
      } else if (onNavigate) {
        onNavigate("/chat");
      }
    }
  };

  // 7. Havoladan nusxa olish
  const handleCopyLink = async () => {
    closeMenu();
    if (targetInfo.linkUrl) {
      await navigator.clipboard.writeText(targetInfo.linkUrl);
      showToast("Havola nusxalandi ✓");
    }
  };

  // 8. Brauzerda ochish
  const handleOpenLink = async () => {
    closeMenu();
    if (targetInfo.linkUrl) {
      try {
        const { invoke } = await import("@tauri-apps/api/core");
        await invoke("app_open_external_url", { url: targetInfo.linkUrl });
      } catch {
        window.open(targetInfo.linkUrl, "_blank");
      }
    }
  };

  // 9. Sahifani yangilash (Refresh)
  const handleRefresh = () => {
    closeMenu();
    window.location.reload();
  };

  const hasCopyable = !!(
    targetInfo.selectedText ||
    targetInfo.messageText ||
    (targetInfo.isEditable && targetInfo.targetElement)
  );

  return (
    <>
      {/* Toast Notification Pill */}
      {copyFeedback && (
        <div
          style={{
            position: "fixed",
            bottom: "28px",
            right: "28px",
            zIndex: 999999,
            padding: "8px 16px",
            borderRadius: "999px",
            background: "rgba(24, 13, 36, 0.94)",
            border: "1px solid rgba(192, 76, 253, 0.5)",
            boxShadow: "0 10px 25px rgba(147, 3, 197, 0.4)",
            color: "#FFFFFF",
            fontSize: "12px",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "8px",
            backdropFilter: "blur(16px)",
            pointerEvents: "none",
            animation: "misaFadeIn 0.2s ease-out",
          }}
        >
          <span style={{ color: "#4EDEA3" }}>●</span>
          <span>{copyFeedback}</span>
        </div>
      )}

      {/* Floating Glassmorphic Context Menu */}
      {isOpen && (
        <div
          ref={menuRef}
          style={{
            position: "fixed",
            top: `${position.y}px`,
            left: `${position.x}px`,
            zIndex: 99999,
            width: "228px",
            borderRadius: "16px",
            background: "rgba(18, 10, 28, 0.94)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            border: "1px solid rgba(192, 76, 253, 0.32)",
            boxShadow:
              "0 20px 48px rgba(0, 0, 0, 0.75), 0 0 24px rgba(147, 3, 197, 0.25)",
            padding: "6px",
            display: "flex",
            flexDirection: "column",
            gap: "2px",
            userSelect: "none",
            WebkitUserSelect: "none",
            animation: "misaScaleIn 0.12s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        >
          {/* 1. NUSXA OLISH (COPY) */}
          <button
            type="button"
            onClick={handleCopy}
            disabled={!hasCopyable}
            style={menuItemStyle(!hasCopyable)}
            onMouseEnter={(e) => handleHover(e, !hasCopyable)}
            onMouseLeave={(e) => handleUnhover(e, !hasCopyable)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
              <CopySvg size={14} />
              <span>Nusxa olish</span>
            </div>
            <kbd style={kbdStyle}>Ctrl+C</kbd>
          </button>

          {/* 2. QIRIB OLISH (CUT) — Faqat kiritish maydonida */}
          {targetInfo.isEditable && (
            <button
              type="button"
              onClick={handleCut}
              disabled={!targetInfo.selectedText}
              style={menuItemStyle(!targetInfo.selectedText)}
              onMouseEnter={(e) => handleHover(e, !targetInfo.selectedText)}
              onMouseLeave={(e) => handleUnhover(e, !targetInfo.selectedText)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                <CutSvg size={14} />
                <span>Qirqib olish</span>
              </div>
              <kbd style={kbdStyle}>Ctrl+X</kbd>
            </button>
          )}

          {/* 3. QO'YISH (PASTE) — Faqat kiritish maydonida */}
          {targetInfo.isEditable && (
            <button
              type="button"
              onClick={handlePaste}
              style={menuItemStyle(false)}
              onMouseEnter={(e) => handleHover(e, false)}
              onMouseLeave={(e) => handleUnhover(e, false)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                <PasteSvg size={14} />
                <span>Qo'yish</span>
              </div>
              <kbd style={kbdStyle}>Ctrl+V</kbd>
            </button>
          )}

          {/* 4. BARCHASINI TANLASH (SELECT ALL) */}
          <button
            type="button"
            onClick={handleSelectAll}
            style={menuItemStyle(false)}
            onMouseEnter={(e) => handleHover(e, false)}
            onMouseLeave={(e) => handleUnhover(e, false)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
              <SelectAllSvg size={14} />
              <span>Barchasini tanlash</span>
            </div>
            <kbd style={kbdStyle}>Ctrl+A</kbd>
          </button>

          {/* MATN TANLANGAN BO'LSA: AI VA OVOZLI QO'SHIMCHA FUNKSIYALAR */}
          {(targetInfo.selectedText || targetInfo.messageText) && (
            <>
              <div style={dividerStyle} />

              <button
                type="button"
                onClick={handleAskMisa}
                style={menuItemStyle(false, true)}
                onMouseEnter={(e) => handleHover(e, false, true)}
                onMouseLeave={(e) => handleUnhover(e, false, true)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                  <SparklesSvg size={14} />
                  <span>Misa'dan so'rash</span>
                </div>
                <span
                  style={{
                    fontSize: "10px",
                    padding: "1px 6px",
                    borderRadius: "4px",
                    background: "rgba(192, 76, 253, 0.25)",
                    color: "#E8B3FF",
                    fontWeight: 600,
                  }}
                >
                  AI
                </span>
              </button>

              <button
                type="button"
                onClick={handleSpeak}
                style={menuItemStyle(false)}
                onMouseEnter={(e) => handleHover(e, false)}
                onMouseLeave={(e) => handleUnhover(e, false)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                  <SpeakerSvg size={14} />
                  <span>Ovozda o'qish</span>
                </div>
              </button>
            </>
          )}

          {/* HAVOLA BOSILGANDA */}
          {targetInfo.isLink && (
            <>
              <div style={dividerStyle} />
              <button
                type="button"
                onClick={handleCopyLink}
                style={menuItemStyle(false)}
                onMouseEnter={(e) => handleHover(e, false)}
                onMouseLeave={(e) => handleUnhover(e, false)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                  <LinkSvg size={14} />
                  <span>Havolani nusxalash</span>
                </div>
              </button>
              <button
                type="button"
                onClick={handleOpenLink}
                style={menuItemStyle(false)}
                onMouseEnter={(e) => handleHover(e, false)}
                onMouseLeave={(e) => handleUnhover(e, false)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                  <ExternalSvg size={14} />
                  <span>Brauzerda ochish</span>
                </div>
              </button>
            </>
          )}

          {/* PASTKI UMUMIY HARAKATLAR */}
          <div style={dividerStyle} />

          <button
            type="button"
            onClick={handleRefresh}
            style={menuItemStyle(false)}
            onMouseEnter={(e) => handleHover(e, false)}
            onMouseLeave={(e) => handleUnhover(e, false)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
              <RefreshSvg size={14} />
              <span>Qayta yangilash</span>
            </div>
            <kbd style={kbdStyle}>Ctrl+R</kbd>
          </button>

          {onNavigate && (
            <button
              type="button"
              onClick={() => {
                closeMenu();
                onNavigate("/account");
              }}
              style={menuItemStyle(false)}
              onMouseEnter={(e) => handleHover(e, false)}
              onMouseLeave={(e) => handleUnhover(e, false)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
                <SettingsSvg size={14} />
                <span>Sozlamalar</span>
              </div>
            </button>
          )}
        </div>
      )}
    </>
  );
};

// --- STYLES & HELPERS ---

const menuItemStyle = (disabled = false, highlight = false): React.CSSProperties => ({
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  width: "100%",
  padding: "8px 12px",
  borderRadius: "10px",
  background: highlight ? "rgba(147, 3, 197, 0.16)" : "transparent",
  border: highlight ? "1px solid rgba(192, 76, 253, 0.28)" : "1px solid transparent",
  color: disabled ? "rgba(255, 255, 255, 0.25)" : highlight ? "#F5F0FF" : "#E2E8F0",
  fontSize: "12.5px",
  fontWeight: highlight ? 600 : 500,
  cursor: disabled ? "not-allowed" : "pointer",
  transition: "all 0.12s ease",
  textAlign: "left",
  outline: "none",
});

const handleHover = (
  e: React.MouseEvent<HTMLButtonElement>,
  disabled = false,
  highlight = false
) => {
  if (disabled) return;
  e.currentTarget.style.background = highlight
    ? "rgba(147, 3, 197, 0.32)"
    : "rgba(255, 255, 255, 0.08)";
  e.currentTarget.style.color = "#FFFFFF";
  if (!highlight) {
    e.currentTarget.style.borderColor = "rgba(255, 255, 255, 0.08)";
  }
};

const handleUnhover = (
  e: React.MouseEvent<HTMLButtonElement>,
  disabled = false,
  highlight = false
) => {
  if (disabled) return;
  e.currentTarget.style.background = highlight ? "rgba(147, 3, 197, 0.16)" : "transparent";
  e.currentTarget.style.color = highlight ? "#F5F0FF" : "#E2E8F0";
  e.currentTarget.style.borderColor = highlight
    ? "1px solid rgba(192, 76, 253, 0.28)"
    : "transparent";
};

const kbdStyle: React.CSSProperties = {
  fontSize: "10px",
  color: "rgba(255, 255, 255, 0.4)",
  fontFamily: "inherit",
  background: "rgba(255, 255, 255, 0.04)",
  padding: "2px 5px",
  borderRadius: "4px",
  border: "1px solid rgba(255, 255, 255, 0.06)",
};

const dividerStyle: React.CSSProperties = {
  height: "1px",
  background: "rgba(255, 255, 255, 0.08)",
  margin: "4px 4px",
};

// --- INLINE VECTOR ICONS ---

const CopySvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);

const CutSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="6" cy="6" r="3" />
    <circle cx="6" cy="18" r="3" />
    <line x1="20" y1="4" x2="8.12" y2="15.88" />
    <line x1="14.47" y1="14.48" x2="20" y2="20" />
    <line x1="8.12" y1="8.12" x2="12" y2="12" />
  </svg>
);

const PasteSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
  </svg>
);

const SelectAllSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" strokeDasharray="3 3" />
    <path d="M9 12h6" />
    <path d="M12 9v6" />
  </svg>
);

const SparklesSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#E8B3FF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2L14.2 8.8L21 11L14.2 13.2L12 20L9.8 13.2L3 11L9.8 8.8L12 2Z" fill="rgba(192, 76, 253, 0.4)" />
  </svg>
);

const SpeakerSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
  </svg>
);

const LinkSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);

const ExternalSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <polyline points="15 3 21 3 21 9" />
    <line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);

const RefreshSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="23 4 23 10 17 10" />
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
  </svg>
);

const SettingsSvg = ({ size = 14 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);
