import React from "react";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  title: string;
  size?: number;
  variant?: "glass" | "ghost" | "primary";
}

export const IconButton: React.FC<IconButtonProps> = ({
  icon,
  title,
  size = 36,
  variant = "glass",
  className = "",
  style,
  ...props
}) => {
  const effectiveSize = Math.max(36, size);
  const getStyles = (): React.CSSProperties => {
    switch (variant) {
      case "primary":
        return {
          background: "var(--primary)",
          border: "1px solid var(--primary-glow)",
          color: "#FFFFFF",
        };
      case "ghost":
        return {
          background: "transparent",
          border: "1px solid transparent",
          color: "var(--text-secondary)",
        };
      case "glass":
      default:
        return {
          background: "var(--glass-bg)",
          border: "1px solid var(--glass-border)",
          color: "var(--text-secondary)",
        };
    }
  };

  return (
    <button
      title={title}
      aria-label={title || "Tugma"}
      className={`misa-icon-button icon-button ${className}`}
      style={{
        width: `${effectiveSize}px`,
        height: `${effectiveSize}px`,
        minWidth: "36px",
        minHeight: "36px",
        borderRadius: "50%",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "all 0.15s ease",
        cursor: "pointer",
        ...getStyles(),
        ...style,
      }}
      onMouseEnter={(e) => {
        if (variant === "glass") {
          e.currentTarget.style.backgroundColor = "var(--glass-bg-hover)";
          e.currentTarget.style.borderColor = "var(--glass-border-hover)";
          e.currentTarget.style.color = "var(--text-primary)";
        } else if (variant === "ghost") {
          e.currentTarget.style.backgroundColor = "var(--surface-hover)";
          e.currentTarget.style.color = "var(--text-primary)";
        }
      }}
      onMouseLeave={(e) => {
        const reset = getStyles();
        if (reset.background) e.currentTarget.style.backgroundColor = reset.background as string;
        if (reset.border) e.currentTarget.style.border = reset.border as string;
        if (reset.color) e.currentTarget.style.color = reset.color as string;
      }}
      {...props}
    >
      {icon}
    </button>
  );
};
