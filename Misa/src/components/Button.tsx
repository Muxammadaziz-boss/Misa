import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "glass" | "ghost";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  icon,
  children,
  className = "",
  style,
  ...props
}) => {
  const getPadding = () => {
    switch (size) {
      case "sm": return "5px 12px";
      case "lg": return "11px 24px";
      case "md":
      default: return "8px 18px";
    }
  };

  const getFontSize = () => {
    switch (size) {
      case "sm": return "var(--font-size-caption)";
      case "lg": return "var(--font-size-body)";
      case "md":
      default: return "var(--font-size-body)";
    }
  };

  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case "secondary":
        return {
          background: "var(--surface)",
          border: "1px solid var(--border)",
          color: "var(--text-primary)",
        };
      case "glass":
        return {
          background: "var(--glass-bg)",
          border: "1px solid var(--glass-border)",
          color: "var(--text-primary)",
          backdropFilter: "blur(12px)",
        };
      case "ghost":
        return {
          background: "transparent",
          border: "1px solid transparent",
          color: "var(--text-secondary)",
        };
      case "primary":
      default:
        return {
          background: "var(--primary)",
          border: "1px solid var(--primary-glow)",
          color: "#FFFFFF",
          boxShadow: "0 2px 14px rgba(147, 3, 197, 0.35)",
        };
    }
  };

  return (
    <button
      className={`misa-button btn-${variant} ${className}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px",
        padding: getPadding(),
        fontSize: getFontSize(),
        fontWeight: 600,
        borderRadius: "var(--radius-pill)",
        transition: "all 0.18s ease",
        cursor: "pointer",
        ...getVariantStyles(),
        ...style,
      }}
      onMouseEnter={(e) => {
        if (variant === "primary") {
          e.currentTarget.style.backgroundColor = "var(--primary-hover)";
        } else if (variant === "glass") {
          e.currentTarget.style.backgroundColor = "var(--glass-bg-hover)";
          e.currentTarget.style.borderColor = "var(--glass-border-hover)";
        } else if (variant === "secondary") {
          e.currentTarget.style.backgroundColor = "var(--surface-hover)";
        } else if (variant === "ghost") {
          e.currentTarget.style.backgroundColor = "var(--surface-hover)";
          e.currentTarget.style.color = "var(--text-primary)";
        }
      }}
      onMouseLeave={(e) => {
        const reset = getVariantStyles();
        if (reset.background) e.currentTarget.style.backgroundColor = reset.background as string;
        if (reset.border) e.currentTarget.style.border = reset.border as string;
        if (reset.color) e.currentTarget.style.color = reset.color as string;
      }}
      {...props}
    >
      {icon && <span style={{ display: "flex", alignItems: "center" }}>{icon}</span>}
      <span>{children}</span>
    </button>
  );
};
