import React from "react";
import { MikasaLogo } from "../components/MikasaLogo";
import { WindowControls } from "../components/WindowControls";

interface TopBarProps {
  onLogoClick?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onLogoClick }) => {
  return (
    <header
      data-tauri-drag-region
      className="misa-topbar"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        height: "var(--topbar-height)",
        backgroundColor: "var(--bg-darkest)",
        borderBottom: "1px solid var(--border)",
        userSelect: "none",
        zIndex: 100,
        position: "relative",
      }}
    >
      {/* Left brand area */}
      <div style={{ display: "flex", alignItems: "center", paddingLeft: "14px" }}>
        <MikasaLogo onClick={onLogoClick} />
      </div>

      {/* Center draggable region */}
      <div
        data-tauri-drag-region
        style={{
          flex: 1,
          height: "100%",
          cursor: "default",
        }}
      />

      {/* Right window controls */}
      <WindowControls />
    </header>
  );
};
