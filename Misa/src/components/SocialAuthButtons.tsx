// ========== SocialAuthButtons.tsx ==========
// Misa AI v9.4 — Premium Circular Social Authentication Buttons (david-mohseni Uiverse.io reference)
// Supports Google, GitHub, and Telegram OAuth with interactive tooltips and Ultra Glass styling

import React from "react";
import {
  GoogleIcon,
  GithubIcon,
  TelegramColorIcon,
} from "./icons/Icons";

export interface SocialAuthButtonsProps {
  onGoogleSignIn: () => void;
  onGithubSignIn: () => void;
  onTelegramSignIn: () => void;
  disabled?: boolean;
  loadingProvider?: "google" | "github" | "telegram" | null;
  className?: string;
  style?: React.CSSProperties;
}

export const SocialAuthButtons: React.FC<SocialAuthButtonsProps> = ({
  onGoogleSignIn,
  onGithubSignIn,
  onTelegramSignIn,
  disabled = false,
  loadingProvider = null,
  className = "",
  style,
}) => {
  return (
    <div
      className={`misa-social-circle-group ${className}`.trim()}
      style={style}
      role="group"
      aria-label="Ijtimoiy tarmoqlar orqali kirish"
    >
      {/* Google Button */}
      <button
        type="button"
        role="button"
        aria-label="Continue with Google"
        title="Continue with Google"
        onClick={onGoogleSignIn}
        disabled={disabled}
        className="misa-social-circle-btn misa-social-circle-google"
      >
        <span className="misa-social-circle-tooltip" role="tooltip">
          Continue with Google
        </span>
        <span className="misa-social-circle-icon">
          {loadingProvider === "google" ? (
            <span
              style={{
                width: "20px",
                height: "20px",
                border: "2px solid rgba(255, 255, 255, 0.3)",
                borderTopColor: "#4285F4",
                borderRadius: "50%",
                animation: "misaSpin 0.8s linear infinite",
                display: "inline-block",
              }}
            />
          ) : (
            <GoogleIcon size={22} />
          )}
        </span>
      </button>

      {/* GitHub Button */}
      <button
        type="button"
        role="button"
        aria-label="Continue with GitHub"
        title="Continue with GitHub"
        onClick={onGithubSignIn}
        disabled={disabled}
        className="misa-social-circle-btn misa-social-circle-github"
      >
        <span className="misa-social-circle-tooltip" role="tooltip">
          Continue with GitHub
        </span>
        <span className="misa-social-circle-icon">
          {loadingProvider === "github" ? (
            <span
              style={{
                width: "20px",
                height: "20px",
                border: "2px solid rgba(255, 255, 255, 0.3)",
                borderTopColor: "#FFFFFF",
                borderRadius: "50%",
                animation: "misaSpin 0.8s linear infinite",
                display: "inline-block",
              }}
            />
          ) : (
            <GithubIcon size={22} color="#FFFFFF" />
          )}
        </span>
      </button>

      {/* Telegram Button */}
      <button
        type="button"
        role="button"
        aria-label="Continue with Telegram"
        title="Continue with Telegram"
        onClick={onTelegramSignIn}
        disabled={disabled}
        className="misa-social-circle-btn misa-social-circle-telegram"
      >
        <span className="misa-social-circle-tooltip" role="tooltip">
          Continue with Telegram
        </span>
        <span className="misa-social-circle-icon">
          {loadingProvider === "telegram" ? (
            <span
              style={{
                width: "20px",
                height: "20px",
                border: "2px solid rgba(255, 255, 255, 0.3)",
                borderTopColor: "#229ED9",
                borderRadius: "50%",
                animation: "misaSpin 0.8s linear infinite",
                display: "inline-block",
              }}
            />
          ) : (
            <TelegramColorIcon size={22} />
          )}
        </span>
      </button>
    </div>
  );
};

export default SocialAuthButtons;
