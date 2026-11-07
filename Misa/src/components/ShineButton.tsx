// ========== ShineButton.tsx ==========
// Misa AI v9.4 — Premium Animated Shine Button (satyamchaudharydev Uiverse.io reference)
// Pill-shaped, diagonal travelling reflection, subtle icon movement on hover, Ultra Glass purple depth

import React from "react";

export interface ShineButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "emerald" | "full";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  fullWidth?: boolean;
  children: React.ReactNode;
}

export const ShineButton: React.FC<ShineButtonProps> = ({
  variant = "primary",
  size = "md",
  icon,
  iconPosition = "left",
  fullWidth = false,
  children,
  className = "",
  disabled = false,
  style,
  ...props
}) => {
  const sizeClass = size === "sm" ? "misa-shine-sm" : size === "lg" ? "misa-shine-lg" : "";
  const variantClass = variant === "emerald" ? "misa-shine-emerald" : "";
  const fullClass = fullWidth || variant === "full" ? "misa-shine-full" : "";

  return (
    <button
      className={`misa-shine-btn ${sizeClass} ${variantClass} ${fullClass} ${className}`.trim()}
      disabled={disabled}
      aria-disabled={disabled}
      style={style}
      {...props}
    >
      {icon && iconPosition === "left" && (
        <span className="misa-shine-icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <span className="misa-shine-label">{children}</span>
      {icon && iconPosition === "right" && (
        <span className="misa-shine-icon" aria-hidden="true">
          {icon}
        </span>
      )}
    </button>
  );
};

export default ShineButton;
