import React from "react";

export type ExpandableButtonVariant = "primary" | "secondary" | "destructive";
export type ExpandableButtonSize = "sm" | "md" | "lg";

export interface ExpandableButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "size"> {
  icon: React.ReactNode;
  label: string;
  variant?: ExpandableButtonVariant;
  size?: ExpandableButtonSize;
  loading?: boolean;
  expanded?: boolean;
  ariaLabel?: string;
  className?: string;
  style?: React.CSSProperties;
}

export const ExpandableButton: React.FC<ExpandableButtonProps> = ({
  icon,
  label,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  expanded = false,
  ariaLabel,
  title,
  className = "",
  style,
  onClick,
  type = "button",
  ...rest
}) => {
  const isDisabled = disabled || loading;

  const buttonClasses = [
    "misa-expandable-btn",
    `misa-expandable-btn--${variant}`,
    `misa-expandable-btn--${size}`,
    expanded ? "is-expanded" : "",
    loading ? "is-loading" : "",
    isDisabled ? "is-disabled" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={buttonClasses}
      disabled={isDisabled}
      onClick={isDisabled ? undefined : onClick}
      aria-label={ariaLabel || label}
      aria-busy={loading}
      title={title || label}
      style={style}
      {...rest}
    >
      <span className="misa-expandable-icon" aria-hidden="true">
        {loading ? <span className="misa-expandable-spinner" /> : icon}
      </span>
      <span className="misa-expandable-text">{label}</span>
    </button>
  );
};

export default ExpandableButton;
