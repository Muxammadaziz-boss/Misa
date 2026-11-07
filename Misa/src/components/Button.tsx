import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "glass" | "ghost" | "shine";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  icon,
  iconPosition = "left",
  children,
  className = "",
  style,
  disabled,
  ...props
}) => {
  const isShineVariant = variant === "primary" || variant === "shine";

  const getPadding = () => {
    switch (size) {
      case "sm": return "6px 14px";
      case "lg": return "12px 26px";
      case "md":
      default: return "9px 20px";
    }
  };

  const getFontSize = () => {
    switch (size) {
      case "sm": return "var(--font-size-caption, 12.5px)";
      case "lg": return "var(--font-size-body, 15px)";
      case "md":
      default: return "var(--font-size-body, 13.5px)";
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
      case "shine":
      case "primary":
      default:
        return {};
    }
  };

  const buttonClass = isShineVariant
    ? `misa-shine-btn ${size === "sm" ? "misa-shine-sm" : size === "lg" ? "misa-shine-lg" : ""} ${className}`.trim()
    : `misa-button btn-${variant} ${className}`.trim();

  return (
    <button
      className={buttonClass}
      disabled={disabled}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "8px",
        padding: getPadding(),
        fontSize: getFontSize(),
        fontWeight: 600,
        borderRadius: "9999px",
        transition: "all 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        cursor: disabled ? "not-allowed" : "pointer",
        ...getVariantStyles(),
        ...style,
      }}
      onMouseEnter={(e) => {
        if (!isShineVariant) {
          if (variant === "glass") {
            e.currentTarget.style.backgroundColor = "var(--glass-bg-hover)";
            e.currentTarget.style.borderColor = "var(--glass-border-hover)";
          } else if (variant === "secondary" || variant === "ghost") {
            e.currentTarget.style.backgroundColor = "var(--surface-hover)";
            if (variant === "ghost") e.currentTarget.style.color = "var(--text-primary)";
          }
        }
      }}
      onMouseLeave={(e) => {
        if (!isShineVariant) {
          const reset = getVariantStyles();
          if (reset.background) e.currentTarget.style.backgroundColor = reset.background as string;
          if (reset.border) e.currentTarget.style.border = reset.border as string;
          if (reset.color) e.currentTarget.style.color = reset.color as string;
        }
      }}
      {...props}
    >
      {icon && iconPosition === "left" && (
        <span className={isShineVariant ? "misa-shine-icon" : undefined} style={{ display: "flex", alignItems: "center" }}>
          {icon}
        </span>
      )}
      <span className={isShineVariant ? "misa-shine-label" : undefined}>{children}</span>
      {icon && iconPosition === "right" && (
        <span className={isShineVariant ? "misa-shine-icon" : undefined} style={{ display: "flex", alignItems: "center" }}>
          {icon}
        </span>
      )}
    </button>
  );
};
