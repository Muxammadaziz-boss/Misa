// ========== VoicePage.tsx ==========
// Misa AI v9.0 — To'liq Ekranli Ovozli Muloqot Sahifasi
// Markaziy interaktiv MisaAperture va real vaqtli STT/TTS ovoz boshqaruvi

import React, { useState, useEffect } from "react";
import { MisaAperture } from "../components/MisaAperture";
import {
  MicIcon,
  HomeIcon,
  ChatIcon,
  UserIcon,
  SparklesIcon,
  RefreshIcon,
} from "../components/icons/Icons";
import { backendService, VoiceState, BackendStatus } from "../services/backendService";

interface VoicePageProps {
  userName?: string;
  onNavigateHome: () => void;
  onNavigateChat: () => void;
}

export const VoicePage: React.FC<VoicePageProps> = ({
  userName = "Ustoz",
  onNavigateHome,
  onNavigateChat,
}) => {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ status: "connecting" });
  const [userTranscript, setUserTranscript] = useState<string>("");
  const [lastTranscript, setLastTranscript] = useState<string>("");

  useEffect(() => {
    const unsubVoice = backendService.onVoiceStateChange((state) => {
      setVoiceState(state);
    });
    const unsubStatus = backendService.onStatusChange((status) => {
      setBackendStatus(status);
    });
    const unsubResp = backendService.onResponse((data) => {
      setLastTranscript(data.text);
    });
    const unsubTranscript = backendService.onTranscript((data) => {
      if (data.sender === "user") {
        setUserTranscript(data.text);
      } else {
        setLastTranscript(data.text);
      }
    });
    return () => {
      unsubVoice();
      unsubStatus();
      unsubResp();
      unsubTranscript();
    };
  }, []);

  const handleToggleVoice = async () => {
    if (voiceState === "listening") {
      await backendService.stopVoice();
    } else {
      setUserTranscript("");
      setLastTranscript("");
      await backendService.startVoice();
    }
  };

  const handleReplayVoice = async () => {
    if (lastTranscript) {
      await backendService.speakText(lastTranscript);
    }
  };

  const effectiveOrbState: VoiceState | "offline" | "loading" =
    backendStatus.status === "offline"
      ? "offline"
      : backendStatus.status === "connecting"
      ? "loading"
      : voiceState;

  const getStateDescription = () => {
    switch (effectiveOrbState) {
      case "wake_detected":
        return "Misa uyg'ondi! Sizni tinglamoqda...";
      case "acknowledging":
        return "Ha, eshitaman...";
      case "listening":
        return "Sizni eshitmoqdaman... Gapiring";
      case "thinking":
        return "Misa o'ylamoqda...";
      case "speaking":
        return "Misa gapirmoqda...";
      case "offline":
        return "Ovoz tizimi hozirda mavjud emas. Backend serveriga ulanish kutilmoqda...";
      case "loading":
        return "Audio tizimiga ulanilmoqda...";
      case "error":
        return "Ovoz tizimida xatolik yuz berdi. Mikrofon ruxsatini tekshiring yoki qayta urinib ko'ring.";
      case "idle":
      default:
        return "Muloqotni boshlash uchun optik linzani yoki pastdagi tugmani bosing";
    }
  };

  return (
    <div
      className="voice-page-container"
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        maxWidth: "1320px",
        margin: "0 auto",
        padding: "12px 24px 28px 24px",
        position: "relative",
        zIndex: 5,
        overflow: "hidden",
      }}
    >
      {/* 1. Header */}
      <div
        className="misa-glass-card"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 20px",
          borderRadius: "20px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            onClick={onNavigateHome}
            title="Bosh sahifaga qaytish"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: "34px",
              height: "34px",
              borderRadius: "10px",
              background: "rgba(255, 255, 255, 0.05)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              color: "var(--text-secondary)",
              cursor: "pointer",
            }}
          >
            <HomeIcon size={16} />
          </button>
          <div>
            <span style={{ fontFamily: "var(--font-display)", fontSize: "15px", fontWeight: 700, color: "#FFFFFF" }}>
              Misa Ovozli Muloqot Markazi
            </span>
            <div style={{ fontSize: "11px", color: backendStatus.status === "online" ? "#4EDEA3" : "var(--text-muted)" }}>
              {backendStatus.status === "online" ? "● Neural Audio Service Faol" : "Backendga ulanilmoqda..."}
            </div>
          </div>
        </div>

        <button
          onClick={onNavigateChat}
          title="Matnli chatga o'tish"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "7px 14px",
            borderRadius: "999px",
            background: "rgba(147, 3, 197, 0.18)",
            border: "1px solid rgba(192, 76, 253, 0.35)",
            color: "#E8B3FF",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          <ChatIcon size={14} color="#E8B3FF" />
          <span>Matnli suhbat</span>
        </button>
      </div>

      {/* 2. Center Optical AI Aperture & Voice Controls */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "32px",
          gap: "26px",
          textAlign: "center",
          overflowY: "auto",
        }}
      >
        <MisaAperture
          width="380px"
          height="180px"
          state={effectiveOrbState}
          showStatusPill={true}
          onClick={handleToggleVoice}
        />

        <div>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "28px",
              fontWeight: 700,
              color: "#F5F0FF",
              margin: "0 0 8px 0",
            }}
          >
            Salom,{" "}
            <span
              style={{
                background: "linear-gradient(90deg, #E8B3FF 0%, #C04CFD 55%, #9303C5 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              {userName || backendStatus.user || "Ustoz"}
            </span>
          </h2>
          <p
            style={{
              fontSize: "15px",
              color:
                voiceState === "listening"
                  ? "#4EDEA3"
                  : voiceState === "speaking"
                  ? "#E8B3FF"
                  : "var(--text-secondary)",
              fontWeight: 500,
              margin: 0,
              transition: "color 0.2s ease",
            }}
          >
            {getStateDescription()}
          </p>
        </div>

        {/* User spoken transcript */}
        {userTranscript && (
          <div
            className="misa-glass-card"
            style={{
              maxWidth: "540px",
              width: "100%",
              padding: "12px 18px",
              borderRadius: "16px",
              border: "1px solid rgba(192, 76, 253, 0.38)",
              color: "#FFFFFF",
              fontSize: "13.5px",
              textAlign: "left",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "11px",
                color: "#E8B3FF",
                fontWeight: 600,
                marginBottom: "4px",
              }}
            >
              <UserIcon size={13} color="#E8B3FF" />
              <span>Siz aytgan buyruq:</span>
            </div>
            {userTranscript}
          </div>
        )}

        {/* Misa Voice Response Card */}
        {lastTranscript && (
          <div
            className="misa-ultra-glass"
            style={{
              maxWidth: "540px",
              width: "100%",
              padding: "16px 20px",
              borderRadius: "18px",
              color: "#FFFFFF",
              fontSize: "13.5px",
              lineHeight: 1.55,
              textAlign: "left",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "6px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "11.5px",
                  color: "#E8B3FF",
                  fontWeight: 700,
                }}
              >
                <SparklesIcon size={13} color="#C04CFD" />
                <span>Misa javobi:</span>
              </div>
              <button
                onClick={handleReplayVoice}
                title="Ovozni qayta tinglash"
                style={{
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.35)",
                  borderRadius: "999px",
                  padding: "4px 10px",
                  color: "#E8B3FF",
                  fontSize: "11px",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                }}
              >
                <RefreshIcon size={12} color="#E8B3FF" />
                <span>Qayta eshitish</span>
              </button>
            </div>
            {lastTranscript}
          </div>
        )}

        {/* Main Voice Toggle Button */}
        <button
          onClick={handleToggleVoice}
          className={voiceState === "listening" ? "" : "misa-btn-violet"}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "12px",
            padding: "14px 36px",
            borderRadius: "9999px",
            background:
              voiceState === "listening"
                ? "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
                : undefined,
            border:
              voiceState === "listening"
                ? "1px solid rgba(239, 68, 68, 0.55)"
                : undefined,
            boxShadow:
              voiceState === "listening"
                ? "0 6px 28px rgba(239, 68, 68, 0.45)"
                : undefined,
            color: "#FFFFFF",
            fontSize: "14.5px",
            fontWeight: 600,
            cursor: "pointer",
            marginTop: "8px",
          }}
        >
          <MicIcon size={18} color="#FFFFFF" />
          <span>{voiceState === "listening" ? "Tinglashni to'xtatish" : "Tinglashni boshlash"}</span>
        </button>
      </div>
    </div>
  );
};
