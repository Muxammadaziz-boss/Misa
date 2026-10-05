import React from "react";

export interface MisaLogoProps {
  compact?: boolean;
  showVersion?: boolean;
  size?: number;
  showText?: boolean;
  showBadge?: boolean;
  onClick?: () => void;
  className?: string;
}

export const MisaLogo: React.FC<MisaLogoProps> = ({
  compact = false,
  showVersion = true,
  size = 32,
  showText,
  showBadge,
  onClick,
  className = "",
}) => {
  const isCompact = showText !== undefined ? !showText : compact;
  const displayVersion = showBadge !== undefined ? showBadge : showVersion;
  const iconSize = Math.round(size * 0.5);

  return (
    <div
      onClick={onClick}
      className={`misa-logo misa-logo misa-logo misa-logo misa-logo mikasa-logo ${className}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "10px",
        cursor: onClick ? "pointer" : "default",
        userSelect: "none",
      }}
    >
      <div
        style={{
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: `${size}px`,
          height: `${size}px`,
          borderRadius: "50%",
          background: "linear-gradient(135deg, #C04CFD 0%, #9303C5 55%, #500075 100%)",
          boxShadow: "0 0 16px rgba(147, 3, 197, 0.65), inset 0 1px 1px rgba(255, 255, 255, 0.4)",
          border: "1px solid rgba(255, 255, 255, 0.22)",
          flexShrink: 0,
        }}
      >
        {/* Equalizer / Core AI Pulse Icon */}
        <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.4" strokeLinecap="round">
          <line x1="6" y1="9" x2="6" y2="15" />
          <line x1="10" y1="5" x2="10" y2="19" />
          <line x1="14" y1="8" x2="14" y2="16" />
          <line x1="18" y1="10" x2="18" y2="14" />
        </svg>
      </div>

      {!isCompact && (
        <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
          <span
            style={{
              fontSize: size > 36 ? "20px" : "16px",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "#FFFFFF",
              fontFamily: "var(--font-display)",
              whiteSpace: "nowrap",
            }}
          >
            Misa
          </span>
          {displayVersion && (
            <span
              style={{
                fontSize: "10px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                padding: "2px 6px",
                borderRadius: "6px",
                background: "rgba(147, 3, 197, 0.22)",
                color: "#E8B3FF",
                border: "1px solid rgba(192, 76, 253, 0.32)",
                whiteSpace: "nowrap",
              }}
            >
              v9.0.1
            </span>
          )}
        </div>
      )}
    </div>
  );
};


export default MisaLogo;
