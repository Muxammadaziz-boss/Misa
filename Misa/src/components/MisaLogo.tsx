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
          borderRadius: `${Math.round(size * 0.24)}px`,
          overflow: "hidden",
          boxShadow: "0 0 18px rgba(147, 3, 197, 0.55), 0 0 4px rgba(192, 76, 253, 0.3)",
          border: "1px solid rgba(192, 76, 253, 0.35)",
          background: "rgba(18, 10, 28, 0.8)",
          flexShrink: 0,
        }}
      >
        <img
          src="/logo.png"
          alt="Misa AI"
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
          onError={(e) => {
            // Fallback to SVG if image fails to load
            e.currentTarget.style.display = "none";
          }}
        />
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
              v9.3
            </span>
          )}
        </div>
      )}
    </div>
  );
};


export default MisaLogo;
