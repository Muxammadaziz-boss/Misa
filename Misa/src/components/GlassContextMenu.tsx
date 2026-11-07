import React, { useEffect, useRef, useState, useCallback } from "react";

export interface GlassMenuItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  destructive?: boolean;
  highlight?: boolean;
  shortcut?: string;
  badge?: string;
  description?: string;
}

export interface GlassMenuGroup {
  id?: string;
  title?: string;
  items: GlassMenuItem[];
}

export interface GlassContextMenuProps {
  isOpen: boolean;
  onClose: () => void;
  position?: { x: number; y: number };
  groups: GlassMenuGroup[];
  title?: string;
  className?: string;
  style?: React.CSSProperties;
  minWidth?: number;
}

export const GlassContextMenu: React.FC<GlassContextMenuProps> = ({
  isOpen,
  onClose,
  position = { x: 0, y: 0 },
  groups,
  title,
  className = "",
  style,
  minWidth = 220,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [adjustedPos, setAdjustedPos] = useState<{ x: number; y: number }>(position);
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  // Flatten active items for keyboard navigation
  const allItems = groups.flatMap((g) => g.items);

  // Adjust position to stay inside viewport boundaries
  useEffect(() => {
    if (!isOpen) {
      setFocusedIndex(-1);
      return;
    }

    const pad = 12;
    const menuEl = menuRef.current;
    const menuWidth = menuEl?.offsetWidth || minWidth;
    const menuHeight = menuEl?.offsetHeight || 260;

    const winW = window.innerWidth;
    const winH = window.innerHeight;

    let nextX = position.x;
    let nextY = position.y;

    if (nextX + menuWidth > winW - pad) {
      nextX = Math.max(pad, winW - menuWidth - pad);
    }
    if (nextY + menuHeight > winH - pad) {
      nextY = Math.max(pad, winH - menuHeight - pad);
    }

    setAdjustedPos({ x: nextX, y: nextY });
  }, [isOpen, position, minWidth]);

  // Click outside and Escape key dismissal
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      const activeItems = allItems.filter((i) => !i.disabled);
      if (activeItems.length === 0) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedIndex((prev) => (prev + 1) % activeItems.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedIndex((prev) => (prev - 1 + activeItems.length) % activeItems.length);
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (focusedIndex >= 0 && focusedIndex < activeItems.length) {
          const item = activeItems[focusedIndex];
          if (item && !item.disabled) {
            item.onClick?.();
            onClose();
          }
        }
      }
    };

    window.addEventListener("mousedown", handleClickOutside, true);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("mousedown", handleClickOutside, true);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose, allItems, focusedIndex]);

  const handleItemClick = useCallback(
    (item: GlassMenuItem) => {
      if (item.disabled) return;
      item.onClick?.();
      onClose();
    },
    [onClose]
  );

  if (!isOpen) return null;

  return (
    <div
      ref={menuRef}
      className={`misa-glass-menu ${className}`}
      role="menu"
      aria-label={title || "Kontekst menyusi"}
      style={{
        top: adjustedPos.y,
        left: adjustedPos.x,
        minWidth: `${minWidth}px`,
        ...style,
      }}
    >
      {title && <div className="misa-glass-menu-header">{title}</div>}

      {groups.map((group, groupIdx) => (
        <React.Fragment key={group.id || `group-${groupIdx}`}>
          {groupIdx > 0 && <div className="misa-glass-menu-separator" role="separator" />}

          {group.title && (
            <div className="misa-glass-menu-group-title">{group.title}</div>
          )}

          <div className="misa-glass-menu-group" role="group">
            {group.items.map((item) => {
              const itemClasses = [
                "misa-glass-menu-item",
                item.destructive ? "misa-glass-menu-item--destructive" : "",
                item.highlight ? "misa-glass-menu-item--highlight" : "",
                item.disabled ? "is-disabled" : "",
              ]
                .filter(Boolean)
                .join(" ");

              return (
                <button
                  key={item.id}
                  type="button"
                  className={itemClasses}
                  role="menuitem"
                  disabled={item.disabled}
                  onClick={() => handleItemClick(item)}
                  aria-disabled={item.disabled}
                >
                  <div className="misa-glass-menu-item-left">
                    {item.icon && (
                      <span className="misa-glass-menu-icon" aria-hidden="true">
                        {item.icon}
                      </span>
                    )}
                    <span className="misa-glass-menu-label">{item.label}</span>
                  </div>

                  <div className="misa-glass-menu-item-right">
                    {item.badge && (
                      <span className="misa-glass-menu-badge">{item.badge}</span>
                    )}
                    {item.shortcut && (
                      <kbd className="misa-glass-menu-kbd">{item.shortcut}</kbd>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </React.Fragment>
      ))}
    </div>
  );
};

export default GlassContextMenu;
