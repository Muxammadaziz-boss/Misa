import React from "react";

export interface AvatarProps {
  initials?: string;
  name?: string;
  size?: number | "sm" | "md" | "lg";
  className?: string;
  avatarStyle?: string;
  styleId?: string;
  avatarUrl?: string;
}

const AVATAR_GRADIENTS: Record<string, string> = {
  violet: "linear-gradient(135deg, #9303C5 0%, #C04CFD 100%)",
  cosmic: "linear-gradient(135deg, #9303C5 0%, #C04CFD 100%)",
  emerald: "linear-gradient(135deg, #059669 0%, #10B981 100%)",
  blue: "linear-gradient(135deg, #0284C7 0%, #1D4ED8 100%)",
  purple: "linear-gradient(135deg, #7C3AED 0%, #9333EA 100%)",
  cyan: "linear-gradient(135deg, #0891B2 0%, #06B6D4 100%)",
  gold: "linear-gradient(135deg, #D97706 0%, #F59E0B 100%)",
  amber: "linear-gradient(135deg, #D97706 0%, #F59E0B 100%)",
  rose: "linear-gradient(135deg, #E11D48 0%, #F43F5E 100%)",
  slate: "linear-gradient(135deg, #334155 0%, #475569 100%)",
};

export const Avatar: React.FC<AvatarProps> = ({
  initials,
  name,
  size = 32,
  className = "",
  avatarStyle = "violet",
  styleId,
  avatarUrl,
}) => {
  const [imageError, setImageError] = React.useState(false);
  const resolvedStyle = styleId || avatarStyle || "violet";
  const gradient = AVATAR_GRADIENTS[resolvedStyle] || AVATAR_GRADIENTS.violet;
  const resolvedInitials =
    initials ||
    (name
      ? String(name)
          .trim()
          .split(/\s+/)
          .filter(Boolean)
          .map((p) => p[0] || "")
          .join("")
          .slice(0, 2)
          .toUpperCase() || "U"
      : "U");
  const resolvedSize = typeof size === "number" ? size : size === "sm" ? 28 : size === "lg" ? 64 : 36;

  if (avatarUrl && !imageError) {
    return (
      <div
        className={`user-avatar ${className}`}
        style={{
          width: `${resolvedSize}px`,
          height: `${resolvedSize}px`,
          borderRadius: "50%",
          overflow: "hidden",
          border: "1.5px solid rgba(255, 255, 255, 0.2)",
          boxShadow: "0 2px 10px rgba(0, 0, 0, 0.35)",
          flexShrink: 0,
          position: "relative",
        }}
      >
        <img
          src={avatarUrl}
          alt={resolvedInitials}
          onError={() => setImageError(true)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      </div>
    );
  }

  return (
    <div
      className={`user-avatar ${className}`}
      style={{
        width: `${resolvedSize}px`,
        height: `${resolvedSize}px`,
        borderRadius: "50%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: gradient,
        color: "#FFFFFF",
        fontWeight: 600,
        fontSize: `${Math.round(resolvedSize * 0.4)}px`,
        letterSpacing: "0.02em",
        boxShadow: "0 2px 8px rgba(0, 0, 0, 0.3)",
        userSelect: "none",
        flexShrink: 0,
      }}
    >
      {resolvedInitials}
    </div>
  );
};
