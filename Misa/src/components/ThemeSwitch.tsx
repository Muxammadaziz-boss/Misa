import React from "react";

export interface ThemeSwitchProps {
  theme?: "dark" | "light" | "system";
  isDark?: boolean;
  onChange?: (nextTheme: "dark" | "light") => void;
  disabled?: boolean;
  className?: string;
  style?: React.CSSProperties;
  id?: string;
  ariaLabel?: string;
}

export const ThemeSwitch: React.FC<ThemeSwitchProps> = ({
  theme,
  isDark: propIsDark,
  onChange,
  disabled = false,
  className = "",
  style,
  id = "misa-theme-switch",
  ariaLabel = "Toggle theme",
}) => {
  // Determine if currently in dark mode
  const isDarkMode =
    propIsDark !== undefined
      ? propIsDark
      : theme !== undefined
      ? theme !== "light"
      : true;

  const isChecked = !isDarkMode; // Checked = Light mode (Sun on right)

  const handleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled) return;
    const nextChecked = e.target.checked;
    const nextTheme: "dark" | "light" = nextChecked ? "light" : "dark";
    onChange?.(nextTheme);
  };

  const containerClasses = [
    "misa-theme-switch-wrapper",
    isChecked ? "is-day" : "is-night",
    disabled ? "is-disabled" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <label className={containerClasses} style={style} htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        role="switch"
        className="misa-theme-switch-input"
        checked={isChecked}
        disabled={disabled}
        onChange={handleToggle}
        aria-label={ariaLabel}
        aria-checked={isChecked}
      />

      <div className="misa-theme-switch-track" aria-hidden="true">
        {/* Stars (Night Mode Background) */}
        <div className="misa-theme-switch-stars">
          <span className="misa-star misa-star-1" />
          <span className="misa-star misa-star-2" />
          <span className="misa-star misa-star-3" />
          <span className="misa-star misa-star-4" />
          <span className="misa-star misa-star-5" />
        </div>

        {/* Clouds (Day Mode Background) */}
        <div className="misa-theme-switch-clouds">
          <span className="misa-cloud misa-cloud-1" />
          <span className="misa-cloud misa-cloud-2" />
          <span className="misa-cloud misa-cloud-3" />
        </div>

        {/* Moving Thumb: Moon / Sun */}
        <div className="misa-theme-switch-thumb">
          {/* Moon Surface & Craters */}
          <div className="misa-thumb-moon">
            <span className="misa-crater misa-crater-1" />
            <span className="misa-crater misa-crater-2" />
            <span className="misa-crater misa-crater-3" />
          </div>

          {/* Sun Surface & Subtle Rays */}
          <div className="misa-thumb-sun" />
        </div>
      </div>
    </label>
  );
};

export default ThemeSwitch;
