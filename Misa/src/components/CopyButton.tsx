import React, { useState, useRef, useEffect } from "react";
import { CopyIcon, CheckIcon } from "./icons/Icons";

export interface CopyButtonProps {
  /** The text content to copy to clipboard */
  text: string;
  /** Custom class name */
  className?: string;
  /** Inline style overrides */
  style?: React.CSSProperties;
  /** Button width/height in pixels (default: 36) */
  size?: number;
  /** Default tooltip text on hover (default: "Copy") */
  defaultTooltip?: string;
  /** Tooltip text upon successful copy (default: "Copied!") */
  successTooltip?: string;
  /** Tooltip text if clipboard operation fails (default: "Failed!") */
  errorTooltip?: string;
  /** Accessible title attribute */
  title?: string;
  /** Accessible ARIA label */
  ariaLabel?: string;
  /** Callback on copy success */
  onCopySuccess?: () => void;
  /** Callback on copy error */
  onCopyError?: (err: unknown) => void;
}

/**
 * Premium Neumorphic Ultra Glass Copy Button
 * Designed for Misa Chat Message Toolbar based on Uiverse.io Galahhad architecture.
 */
export const CopyButton: React.FC<CopyButtonProps> = ({
  text,
  className = "",
  style,
  size = 36,
  defaultTooltip = "Copy",
  successTooltip = "Copied!",
  errorTooltip = "Failed!",
  title = "Nusxa olish",
  ariaLabel = "Xabardan nusxa olish",
  onCopySuccess,
  onCopyError,
}) => {
  const [copyState, setCopyState] = useState<"idle" | "success" | "error">("idle");
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up any pending reset timers on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleCopy = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();

    // Reset previous timer if user clicks repeatedly
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    let success = false;

    // 1. Primary modern Clipboard API
    if (navigator?.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        success = true;
      } catch {
        success = false;
      }
    }

    // 2. Resilient fallback for restricted/sandboxed desktop environments
    if (!success) {
      try {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        textArea.setAttribute("readonly", "");
        document.body.appendChild(textArea);
        textArea.select();
        success = document.execCommand("copy");
        document.body.removeChild(textArea);
      } catch (err) {
        success = false;
      }
    }

    if (success) {
      setCopyState("success");
      onCopySuccess?.();
      timeoutRef.current = setTimeout(() => {
        setCopyState("idle");
        timeoutRef.current = null;
      }, 2000);
    } else {
      setCopyState("error");
      onCopyError?.(new Error("Clipboard permission or writeText failed"));
      timeoutRef.current = setTimeout(() => {
        setCopyState("idle");
        timeoutRef.current = null;
      }, 2000);
    }
  };

  const tooltipText =
    copyState === "success"
      ? successTooltip
      : copyState === "error"
      ? errorTooltip
      : defaultTooltip;

  const stateClass =
    copyState === "success"
      ? "is-success show-tooltip"
      : copyState === "error"
      ? "is-error show-tooltip"
      : "";

  const customSizeStyle: React.CSSProperties =
    size !== 36 ? ({ "--btn-size": `${size}px` } as React.CSSProperties) : {};

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copyState === "success" ? successTooltip : title}
      aria-label={copyState === "success" ? successTooltip : ariaLabel}
      className={`misa-copy-btn ${stateClass} ${className}`.trim()}
      style={{
        ...customSizeStyle,
        ...style,
      }}
    >
      <div className="misa-copy-icon-box" aria-hidden="true">
        <span className="misa-copy-icon-default">
          <CopyIcon size={size > 30 ? 15 : 12} color="currentColor" />
        </span>
        <span className="misa-copy-icon-success">
          <CheckIcon size={size > 30 ? 15 : 12} color="#4EDEA3" />
        </span>
      </div>

      <span className="misa-copy-tooltip" role="tooltip" aria-live="polite">
        {tooltipText}
      </span>
    </button>
  );
};
