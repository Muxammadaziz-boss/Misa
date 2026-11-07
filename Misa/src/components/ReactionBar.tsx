import React, { useCallback, useRef } from "react";

export interface ReactionItem {
  id: string;
  emoji: string;
  tooltip: string;
  label: string;
}

export const REACTION_ITEMS: ReactionItem[] = [
  { id: "like", emoji: "👍", tooltip: "Like", label: "Yoqdi (Like)" },
  { id: "cheer", emoji: "👏🏻", tooltip: "Cheer", label: "Qarsaklar (Cheer)" },
  { id: "celebrate", emoji: "🎉", tooltip: "Celebrate", label: "Tabrik (Celebrate)" },
  { id: "appreciate", emoji: "✨", tooltip: "Appreciate", label: "Minnatdorchilik (Appreciate)" },
  { id: "smile", emoji: "🙂", tooltip: "Smile", label: "Tabassum (Smile)" },
];

export interface ReactionBarProps {
  selectedReaction?: string | null;
  onSelectReaction?: (reactionId: string) => void;
  disabled?: boolean;
  className?: string;
  style?: React.CSSProperties;
  size?: "sm" | "md";
  showContainer?: boolean;
}

export const ReactionBar: React.FC<ReactionBarProps> = ({
  selectedReaction,
  onSelectReaction,
  disabled = false,
  className = "",
  style,
  size = "md",
  showContainer = true,
}) => {
  const lastClickRef = useRef<number>(0);

  const handleClick = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      if (disabled) return;
      const now = Date.now();
      if (now - lastClickRef.current < 250) return;
      lastClickRef.current = now;
      onSelectReaction?.(id);
    },
    [disabled, onSelectReaction]
  );

  const containerClasses = [
    "misa-reaction-bar",
    size === "sm" ? "misa-reaction-bar--sm" : "",
    !showContainer ? "misa-reaction-bar--compact" : "",
    disabled ? "is-disabled" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={containerClasses}
      style={style}
      role="toolbar"
      aria-label="Xabarga munosabat bildirish"
    >
      {REACTION_ITEMS.map((item) => {
        const isSelected = selectedReaction === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={`misa-reaction-btn ${isSelected ? "is-selected" : ""}`}
            onClick={(e) => handleClick(e, item.id)}
            disabled={disabled}
            aria-label={item.label}
            aria-pressed={isSelected}
            title={item.tooltip}
          >
            <span className="misa-reaction-tooltip" role="tooltip">
              {item.tooltip}
            </span>
            <span className="misa-reaction-emoji" aria-hidden="true">
              {item.emoji}
            </span>
          </button>
        );
      })}
    </div>
  );
};

export default ReactionBar;
