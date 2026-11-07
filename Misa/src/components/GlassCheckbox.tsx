import React, { forwardRef, useState, useEffect } from "react";

export interface GlassCheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "size" | "onChange"> {
  checked?: boolean;
  defaultChecked?: boolean;
  onChange?: (checked: boolean, e: React.ChangeEvent<HTMLInputElement>) => void;
  label?: React.ReactNode;
  description?: React.ReactNode;
  size?: "sm" | "md" | "lg";
  error?: string;
  className?: string;
  containerStyle?: React.CSSProperties;
}

export const GlassCheckbox = forwardRef<HTMLInputElement, GlassCheckboxProps>(
  (
    {
      checked: controlledChecked,
      defaultChecked = false,
      onChange,
      label,
      description,
      size = "md",
      disabled = false,
      required = false,
      error,
      className = "",
      containerStyle,
      id,
      name,
      value,
      style,
      ...rest
    },
    ref
  ) => {
    const isControlled = controlledChecked !== undefined;
    const [internalChecked, setInternalChecked] = useState<boolean>(
      isControlled ? controlledChecked : defaultChecked
    );

    useEffect(() => {
      if (isControlled) {
        setInternalChecked(controlledChecked);
      }
    }, [isControlled, controlledChecked]);

    const isChecked = isControlled ? controlledChecked : internalChecked;

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (disabled) return;
      const nextChecked = e.target.checked;
      if (!isControlled) {
        setInternalChecked(nextChecked);
      }
      onChange?.(nextChecked, e);
    };

    const generatedId = id || (name ? `checkbox-${name}` : undefined);

    const containerClasses = [
      "misa-glass-checkbox-wrapper",
      `misa-glass-checkbox--${size}`,
      isChecked ? "is-checked" : "",
      disabled ? "is-disabled" : "",
      error ? "has-error" : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <label className={containerClasses} style={containerStyle} htmlFor={generatedId}>
        <div className="misa-glass-checkbox-container">
          <input
            ref={ref}
            id={generatedId}
            type="checkbox"
            name={name}
            value={value}
            checked={isChecked}
            disabled={disabled}
            required={required}
            onChange={handleChange}
            className="misa-glass-checkbox-input"
            aria-invalid={!!error}
            style={style}
            {...rest}
          />
          <div className="misa-glass-checkbox-box" aria-hidden="true">
            <svg
              className="misa-glass-checkbox-check"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="2.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
        </div>

        {(label || description) && (
          <div className="misa-glass-checkbox-label-group">
            {label && <span className="misa-glass-checkbox-label">{label}</span>}
            {description && (
              <span className="misa-glass-checkbox-description">{description}</span>
            )}
            {error && <span className="misa-glass-checkbox-error">{error}</span>}
          </div>
        )}
      </label>
    );
  }
);

GlassCheckbox.displayName = "GlassCheckbox";
export default GlassCheckbox;
