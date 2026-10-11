import React from "react";

export type OrbState =
  | "idle"
  | "wake_detected"
  | "acknowledging"
  | "listening"
  | "thinking"
  | "planning"
  | "acting"
  | "verifying"
  | "replanning"
  | "speaking"
  | "completed"
  | "error"
  // Backwards compatibility aliases:
  | "loading"
  | "offline";

export interface MisaApertureProps {
  size?: number | string;
  width?: number | string;
  height?: number | string;
  state?: OrbState;
  audioLevel?: number;
  showStatusPill?: boolean;
  statusLabel?: string;
  className?: string;
  onClick?: () => void;
}

export const MisaAperture: React.FC<MisaApertureProps> = ({
  size,
  width,
  height,
  state = "idle",
  audioLevel = 0,
  showStatusPill = false,
  statusLabel,
  className = "",
  onClick,
}) => {
  const normState: OrbState =
    state === "loading" ? "thinking" : state === "offline" ? "error" : state;

  // Compute dimensions: default Home design is 380x180px.
  // If a numeric size is passed (e.g. 100 or 200), scale proportionally unless width/height are explicit.
  const numericSize =
    typeof size === "number"
      ? size
      : typeof size === "string" && size.endsWith("px")
      ? parseFloat(size)
      : null;

  const scaleFactor = numericSize ? Math.max(0.45, Math.min(1.2, numericSize / 220)) : 1;
  const resolvedWidth = width ?? (numericSize ? `${Math.round(380 * scaleFactor)}px` : "380px");
  const resolvedHeight = height ?? (numericSize ? `${Math.round(180 * scaleFactor)}px` : "180px");

  const getStateVisuals = () => {
    switch (normState) {
      case "wake_detected":
        return {
          aura: "radial-gradient(ellipse at center, rgba(78, 222, 163, 0.6) 0%, rgba(192, 76, 253, 0.3) 45%, transparent 72%)",
          eyeColor: "#4EDEA3",
          eyeGlow: "0 0 28px rgba(78, 222, 163, 1)",
          smileColor: "#4EDEA3",
          borderColor: "rgba(78, 222, 163, 0.6)",
          badgeDot: "#4EDEA3",
          defaultLabel: "Misa eshitmoqda!",
        };
      case "acknowledging":
        return {
          aura: "radial-gradient(ellipse at center, rgba(192, 76, 253, 0.55) 0%, rgba(78, 222, 163, 0.25) 48%, transparent 72%)",
          eyeColor: "#F5F0FF",
          eyeGlow: "0 0 24px rgba(232, 179, 255, 0.95)",
          smileColor: "#4EDEA3",
          borderColor: "rgba(192, 76, 253, 0.5)",
          badgeDot: "#4EDEA3",
          defaultLabel: "Javob berilmoqda...",
        };
      case "listening":
        return {
          aura: "radial-gradient(ellipse at center, rgba(192, 76, 253, 0.5) 0%, rgba(78, 222, 163, 0.25) 45%, transparent 72%)",
          eyeColor: "#4EDEA3",
          eyeGlow: "0 0 22px rgba(78, 222, 163, 0.95)",
          smileColor: "#4EDEA3",
          borderColor: "rgba(78, 222, 163, 0.45)",
          badgeDot: "#4EDEA3",
          defaultLabel: "Tinglanmoqda...",
        };
      case "thinking":
      case "planning":
        return {
          aura: "radial-gradient(ellipse at center, rgba(192, 76, 253, 0.55) 0%, rgba(147, 3, 197, 0.28) 48%, transparent 72%)",
          eyeColor: "#E8B3FF",
          eyeGlow: "0 0 24px rgba(192, 76, 253, 0.95)",
          smileColor: "#C04CFD",
          borderColor: "rgba(192, 76, 253, 0.5)",
          badgeDot: "#C04CFD",
          defaultLabel: normState === "planning" ? "Rejalashtirilmoqda..." : "Tahlil qilinmoqda...",
        };
      case "acting":
      case "verifying":
      case "replanning":
        return {
          aura: "radial-gradient(ellipse at center, rgba(147, 3, 197, 0.52) 0%, rgba(192, 76, 253, 0.25) 48%, transparent 72%)",
          eyeColor: "#F5F0FF",
          eyeGlow: "0 0 22px rgba(232, 179, 255, 0.95)",
          smileColor: "#E8B3FF",
          borderColor: "rgba(232, 179, 255, 0.45)",
          badgeDot: "#E8B3FF",
          defaultLabel:
            normState === "acting"
              ? "Bajarilmoqda..."
              : normState === "verifying"
              ? "Tekshirilmoqda..."
              : "Qayta rejalashtirilmoqda...",
        };
      case "speaking":
        return {
          aura: "radial-gradient(ellipse at center, rgba(192, 76, 253, 0.55) 0%, rgba(78, 222, 163, 0.22) 48%, transparent 72%)",
          eyeColor: "#F5F0FF",
          eyeGlow: "0 0 24px rgba(232, 179, 255, 0.95)",
          smileColor: "#4EDEA3",
          borderColor: "rgba(192, 76, 253, 0.48)",
          badgeDot: "#4EDEA3",
          defaultLabel: "Misa javob bermoqda...",
        };
      case "completed":
        return {
          aura: "radial-gradient(ellipse at center, rgba(78, 222, 163, 0.4) 0%, rgba(147, 3, 197, 0.22) 48%, transparent 72%)",
          eyeColor: "#4EDEA3",
          eyeGlow: "0 0 20px rgba(78, 222, 163, 0.9)",
          smileColor: "#4EDEA3",
          borderColor: "rgba(78, 222, 163, 0.4)",
          badgeDot: "#4EDEA3",
          defaultLabel: "Tayyor",
        };
      case "error":
        return {
          aura: "radial-gradient(ellipse at center, rgba(255, 113, 108, 0.42) 0%, rgba(147, 3, 197, 0.18) 48%, transparent 72%)",
          eyeColor: "#FF716C",
          eyeGlow: "0 0 20px rgba(255, 113, 108, 0.9)",
          smileColor: "#FF716C",
          borderColor: "rgba(255, 113, 108, 0.45)",
          badgeDot: "#FF716C",
          defaultLabel: "Aloqa tekshirilmoqda",
        };
      case "idle":
      default:
        return {
          aura: "radial-gradient(ellipse at center, rgba(147, 3, 197, 0.35) 0%, rgba(80, 0, 117, 0.12) 48%, transparent 72%)",
          eyeColor: "#E2DDF0",
          eyeGlow: "0 0 18px rgba(232, 179, 255, 0.85)",
          smileColor: "#E8B3FF",
          borderColor: "rgba(255, 255, 255, 0.1)",
          badgeDot: "#4EDEA3",
          defaultLabel: "Tayyor",
        };
    }
  };

  const visuals = getStateVisuals();
  const audioScale = Math.min(1 + audioLevel * 0.08, 1.12);
  const eyeWidth = Math.max(8, Math.round(14 * scaleFactor));
  const eyeHeight = Math.max(20, Math.round(36 * scaleFactor));
  const eyeGap = Math.max(24, Math.round(48 * scaleFactor));

  return (
    <div
      onClick={onClick}
      className={`misa-aperture-wrapper misa-orb-wrapper misa-orb-wrapper misa-orb-wrapper misa-orb-wrapper mikasa-orb-wrapper ${className}`}
      role="status"
      aria-label={`Misa AI Holati: ${normState}`}
      style={{
        position: "relative",
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        cursor: onClick ? "pointer" : "default",
        userSelect: "none",
        transform: `scale(${audioScale})`,
        transition: "transform 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* Outer Ambient Violet Aura */}
      <div
        style={{
          position: "absolute",
          inset: "-24px",
          borderRadius: "36px",
          background: visuals.aura,
          filter: "blur(28px)",
          opacity: normState === "idle" ? 0.78 : 0.96,
          pointerEvents: "none",
          transition: "all 0.5s ease",
        }}
      />

      {/* Main Optical Lens Chassis */}
      <div
        style={{
          position: "relative",
          width: resolvedWidth,
          height: resolvedHeight,
          maxWidth: "90vw",
          borderRadius: `${Math.round(28 * scaleFactor)}px`,
          background: "linear-gradient(180deg, rgba(17, 21, 38, 0.84) 0%, rgba(7, 11, 20, 0.94) 100%)",
          backdropFilter: "blur(24px) saturate(180%)",
          WebkitBackdropFilter: "blur(24px) saturate(180%)",
          border: `1px solid ${visuals.borderColor}`,
          boxShadow:
            "0 25px 70px -15px rgba(2, 6, 14, 0.95), 0 0 40px -10px rgba(147, 3, 197, 0.28), inset 0 1px 1px rgba(255, 255, 255, 0.16)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
          transition: "border-color 0.35s ease, box-shadow 0.35s ease",
          animation: normState === "listening" ? "aperture-listening 2s ease-in-out infinite" : "none",
        }}
      >
        {/* Top Specular Edge Highlight */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: "16%",
            right: "16%",
            height: "1px",
            background: "linear-gradient(90deg, transparent 0%, rgba(232, 179, 255, 0.48) 50%, transparent 100%)",
            pointerEvents: "none",
          }}
        />

        {/* Inner Concentric Lens Ring */}
        <div
          style={{
            position: "absolute",
            inset: `${Math.max(6, Math.round(12 * scaleFactor))}px`,
            borderRadius: `${Math.round(20 * scaleFactor)}px`,
            border: "1px solid rgba(255, 255, 255, 0.045)",
            pointerEvents: "none",
          }}
        />

        {/* Minimalist Optical Eyes & Expression */}
        <div
          style={{
            position: "relative",
            zIndex: 2,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: `${Math.max(8, Math.round(16 * scaleFactor))}px`,
          }}
        >
          {/* Capsule Eyes */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: `${eyeGap}px`,
            }}
          >
            <div
              style={{
                width: `${eyeWidth}px`,
                height: `${eyeHeight}px`,
                borderRadius: "9999px",
                background: visuals.eyeColor,
                boxShadow: visuals.eyeGlow,
                animation:
                  normState === "thinking" || normState === "planning"
                    ? "pulse-slow 1.2s ease-in-out infinite"
                    : "aperture-eye-blink 5.5s ease-in-out infinite",
                transition: "background 0.3s ease, box-shadow 0.3s ease",
              }}
            />
            <div
              style={{
                width: `${eyeWidth}px`,
                height: `${eyeHeight}px`,
                borderRadius: "9999px",
                background: visuals.eyeColor,
                boxShadow: visuals.eyeGlow,
                animation:
                  normState === "thinking" || normState === "planning"
                    ? "pulse-slow 1.2s ease-in-out 0.2s infinite"
                    : "aperture-eye-blink 5.5s ease-in-out infinite",
                transition: "background 0.3s ease, box-shadow 0.3s ease",
              }}
            />
          </div>

          {/* Expression: Speaking / Listening Audio Wave OR Subtle Curved Smile */}
          {normState === "speaking" || normState === "listening" ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "4px",
                height: `${Math.max(12, Math.round(18 * scaleFactor))}px`,
              }}
            >
              {[0.7, 1.2, 1.6, 1.2, 0.7].map((rate, idx) => (
                <span
                  key={idx}
                  style={{
                    width: "3px",
                    height: `${Math.max(8, Math.round(12 * scaleFactor))}px`,
                    borderRadius: "999px",
                    background: visuals.smileColor,
                    boxShadow: `0 0 8px ${visuals.smileColor}`,
                    animation: `wave-bounce ${0.55 / rate}s ease-in-out infinite alternate`,
                  }}
                />
              ))}
            </div>
          ) : (
            <svg
              width={Math.round(42 * scaleFactor)}
              height={Math.round(14 * scaleFactor)}
              viewBox="0 0 42 14"
              style={{
                opacity: 0.9,
                filter: `drop-shadow(0 0 8px ${visuals.smileColor})`,
              }}
            >
              <path
                d={normState === "error" ? "M 8 10 Q 21 4 34 10" : "M 6 4 Q 21 14 36 4"}
                fill="none"
                stroke={visuals.smileColor}
                strokeWidth="3"
                strokeLinecap="round"
              />
            </svg>
          )}
        </div>
      </div>

      {/* Optional Status Pill (Bottom Anchor) */}
      {showStatusPill && (
        <div
          style={{
            marginTop: "-14px",
            zIndex: 4,
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            padding: "4px 14px",
            borderRadius: "9999px",
            background: "#0B0F1C",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 20px rgba(0, 0, 0, 0.65)",
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: visuals.badgeDot,
              boxShadow: `0 0 8px ${visuals.badgeDot}`,
            }}
          />
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              color: "var(--text-secondary)",
              letterSpacing: "0.04em",
            }}
          >
            {statusLabel || visuals.defaultLabel}
          </span>
        </div>
      )}
    </div>
  );
};

export const MisaOrb = MisaAperture;
export default MisaAperture;
