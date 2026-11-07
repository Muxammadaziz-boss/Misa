import React from "react";

export type NeumorphicCardVariant =
  | "default"
  | "elevated"
  | "interactive"
  | "selected"
  | "compact"
  | "stat"
  | "glass";

export interface NeumorphicCardTrend {
  label: React.ReactNode;
  direction?: "up" | "down" | "neutral";
}

export interface NeumorphicCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  variant?: NeumorphicCardVariant;
  elevated?: boolean;
  interactive?: boolean;
  selected?: boolean;
  compact?: boolean;
  glass?: boolean;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  footer?: React.ReactNode;
  value?: React.ReactNode;
  trend?: NeumorphicCardTrend;
  as?: "div" | "article" | "section" | "button";
}

export const NeumorphicCard: React.FC<NeumorphicCardProps> = ({
  variant = "default",
  elevated = false,
  interactive = false,
  selected = false,
  compact = false,
  glass = false,
  title,
  subtitle,
  icon,
  badge,
  footer,
  value,
  trend,
  as: Component = "div",
  className = "",
  style,
  onClick,
  onKeyDown,
  children,
  role,
  tabIndex,
  ...rest
}) => {
  const isInteractive = interactive || Boolean(onClick) || variant === "interactive";
  const isElevated = elevated || variant === "elevated";
  const isSelected = selected || variant === "selected";
  const isCompact = compact || variant === "compact";
  const isGlass = glass || variant === "glass";
  const isStat = variant === "stat" || (value !== undefined && title !== undefined);

  const classes = [
    "misa-neumorphic-card",
    isElevated ? "misa-neumorphic-card--elevated" : "",
    isInteractive ? "misa-neumorphic-card--interactive" : "",
    isSelected ? "misa-neumorphic-card--selected" : "",
    isCompact ? "misa-neumorphic-card--compact" : "",
    isGlass ? "misa-neumorphic-card--glass" : "",
    isStat ? "misa-neumorphic-card--stat" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (onKeyDown) {
      onKeyDown(e);
    }
    if (isInteractive && onClick && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onClick(e as unknown as React.MouseEvent<HTMLDivElement>);
    }
  };

  const interactiveProps = isInteractive
    ? {
        role: role || (isSelected !== undefined ? "button" : "button"),
        tabIndex: tabIndex !== undefined ? tabIndex : 0,
        "aria-pressed": isSelected,
      }
    : { role, tabIndex };

  const hasHeader = Boolean(title || subtitle || icon || badge);

  return (
    <Component
      className={classes}
      style={{
        ...(isInteractive ? { WebkitAppRegion: "no-drag" as any } : {}),
        ...style,
      }}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      {...interactiveProps}
      {...(rest as any)}
    >
      {hasHeader && (
        <div className="misa-neumorphic-card__header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
            {icon && <div className="misa-neumorphic-card__icon">{icon}</div>}
            {(title || subtitle) && (
              <div style={{ minWidth: 0, flex: 1 }}>
                {title && (
                  typeof title === "string" ? (
                    <div className="misa-neumorphic-card__title">{title}</div>
                  ) : (
                    title
                  )
                )}
                {subtitle && (
                  typeof subtitle === "string" ? (
                    <div className="misa-neumorphic-card__subtitle">{subtitle}</div>
                  ) : (
                    subtitle
                  )
                )}
              </div>
            )}
          </div>
          {badge && <div className="misa-neumorphic-card__badge">{badge}</div>}
        </div>
      )}

      {isStat && value !== undefined && (
        <div style={{ display: "flex", alignItems: "baseline", gap: "10px", margin: "4px 0" }}>
          <div className="misa-neumorphic-card__stat-value">{value}</div>
          {trend && (
            <div
              className={`misa-neumorphic-card__stat-trend ${
                trend.direction === "up"
                  ? "misa-neumorphic-card__stat-trend--up"
                  : trend.direction === "down"
                  ? "misa-neumorphic-card__stat-trend--down"
                  : "misa-neumorphic-card__stat-trend--neutral"
              }`}
            >
              {trend.direction === "up" && "▲ "}
              {trend.direction === "down" && "▼ "}
              {trend.label}
            </div>
          )}
        </div>
      )}

      {children && <div className="misa-neumorphic-card__body">{children}</div>}

      {footer && <div className="misa-neumorphic-card__footer">{footer}</div>}
    </Component>
  );
};

export const NeumorphicCardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => (
  <div className={`misa-neumorphic-card__header ${className}`} {...props}>
    {children}
  </div>
);

export const NeumorphicCardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className = "",
  children,
  ...props
}) => (
  <h3 className={`misa-neumorphic-card__title ${className}`} {...props}>
    {children}
  </h3>
);

export const NeumorphicCardSubtitle: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  className = "",
  children,
  ...props
}) => (
  <p className={`misa-neumorphic-card__subtitle ${className}`} {...props}>
    {children}
  </p>
);

export const NeumorphicCardBody: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => (
  <div className={`misa-neumorphic-card__body ${className}`} {...props}>
    {children}
  </div>
);

export const NeumorphicCardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => (
  <div className={`misa-neumorphic-card__footer ${className}`} {...props}>
    {children}
  </div>
);

export default NeumorphicCard;
