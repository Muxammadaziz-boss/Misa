import React from "react";

export type MisaLoaderVariant = "main" | "inline";
export type MisaLoaderSize = "small" | "medium" | "large";

export interface MisaLoaderProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: MisaLoaderVariant;
  text?: string;
  size?: MisaLoaderSize;
  visible?: boolean;
  className?: string;
  style?: React.CSSProperties;
  "aria-label"?: string;
}

export const MisaLoader: React.FC<MisaLoaderProps> = ({
  variant = "inline",
  text,
  size = "medium",
  visible = true,
  className = "",
  style,
  "aria-label": ariaLabel,
  ...rest
}) => {
  if (!visible) return null;

  const accessibleDescription =
    ariaLabel || text || (variant === "main" ? "Misa ishga tushirilmoqda..." : "Yuklanmoqda...");

  const renderAnimatedLetters = (label: string) => {
    const letters = Array.from(label);
    return (
      <div className="misa-loader-text" aria-hidden="true">
        {letters.map((char, index) => (
          <span
            key={index}
            className="misa-loader-letter"
            style={{ "--letter-index": index } as React.CSSProperties}
          >
            {char === " " ? "\u00A0" : char}
          </span>
        ))}
      </div>
    );
  };

  if (variant === "main") {
    return (
      <div
        className={`misa-main-loader ${className}`}
        style={style}
        role="status"
        aria-live="polite"
        aria-label={accessibleDescription}
        {...rest}
      >
        <span className="misa-sr-only">{accessibleDescription}</span>
        <div className={`misa-main-loader-core misa-main-loader-core--${size}`} />
        {text && renderAnimatedLetters(text)}
      </div>
    );
  }

  // Inline variant
  return (
    <div
      className={`misa-inline-loader ${className}`}
      style={style}
      role="status"
      aria-live="polite"
      aria-label={accessibleDescription}
      {...rest}
    >
      <span className="misa-sr-only">{accessibleDescription}</span>
      <div className={`misa-inline-spinner misa-inline-spinner--${size}`} />
      {text && renderAnimatedLetters(text)}
    </div>
  );
};

export default MisaLoader;
