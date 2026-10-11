import React from "react";
import { Button } from "../components/Button";
import { HomeIcon } from "../components/icons/Icons";

interface RoutePlaceholderProps {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  onNavigateHome: () => void;
}

export const RoutePlaceholder: React.FC<RoutePlaceholderProps> = ({
  title,
  subtitle = "Ushbu sahifa Misa AI ning keyingi bosqichlarida joriy etiladi",
  icon,
  onNavigateHome,
}) => {
  return (
    <div
      className="route-placeholder"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        overflowY: "auto",
        boxSizing: "border-box",
        padding: "32px",
        textAlign: "center",
        userSelect: "none",
      }}
    >
      {icon && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "48px",
            height: "48px",
            borderRadius: "var(--radius-lg)",
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
            marginBottom: "16px",
          }}
        >
          {icon}
        </div>
      )}

      <h2
        style={{
          fontSize: "var(--font-size-heading)",
          fontWeight: 700,
          color: "var(--text-primary)",
          marginBottom: "6px",
        }}
      >
        {title}
      </h2>

      <p
        style={{
          fontSize: "var(--font-size-body)",
          color: "var(--text-muted)",
          maxWidth: "400px",
          marginBottom: "24px",
          lineHeight: 1.6,
        }}
      >
        {subtitle}
      </p>

      <Button
        variant="glass"
        size="md"
        icon={<HomeIcon size={15} color="var(--primary-glow)" />}
        onClick={onNavigateHome}
      >
        Bosh sahifaga qaytish
      </Button>
    </div>
  );
};
