import React, { useState, useRef, useEffect, useCallback } from "react";

interface MisaIntroSplashProps {
  onFinish: () => void;
  minDurationMs?: number;
}

export const MisaIntroSplash: React.FC<MisaIntroSplashProps> = ({
  onFinish,
  minDurationMs = 1200,
}) => {
  const [isFading, setIsFading] = useState(false);
  const [canSkip, setCanSkip] = useState(false);
  const [progress, setProgress] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const completedRef = useRef<boolean>(false);

  const handleComplete = useCallback(() => {
    if (completedRef.current) return;
    completedRef.current = true;

    // Enforce smooth minimum time so it doesn't flash if video ends instantly
    const elapsed = Date.now() - startTimeRef.current;
    const remaining = Math.max(0, minDurationMs - elapsed);

    setTimeout(() => {
      setIsFading(true);
      setTimeout(() => {
        onFinish();
      }, 350);
    }, remaining);
  }, [minDurationMs, onFinish]);

  useEffect(() => {
    // Show skip button after 1 second so user isn't locked if they're in a hurry
    const skipTimer = setTimeout(() => {
      setCanSkip(true);
    }, 800);

    // Keyboard shortcut to skip (Escape, Space, Enter)
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === " " || e.key === "Enter") {
        e.preventDefault();
        handleComplete();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      clearTimeout(skipTimer);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleComplete]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Attempt autoplay with sound, fallback to muted if system restricts
    const playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        // Fallback to muted playback
        video.muted = true;
        video.play().catch(() => {
          // If video completely cannot play, finish gracefully
          handleComplete();
        });
      });
    }

    const handleTimeUpdate = () => {
      if (video.duration && !isNaN(video.duration)) {
        setProgress((video.currentTime / video.duration) * 100);
      }
    };

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("ended", handleComplete);
    video.addEventListener("error", handleComplete);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("ended", handleComplete);
      video.removeEventListener("error", handleComplete);
    };
  }, [handleComplete]);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 999999,
        backgroundColor: "#030108",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: isFading ? 0 : 1,
        transition: "opacity 0.35s cubic-bezier(0.16, 1, 0.3, 1)",
        pointerEvents: isFading ? "none" : "auto",
        overflow: "hidden",
        userSelect: "none",
      }}
    >
      {/* Background ambient crystal glow */}
      <div
        style={{
          position: "absolute",
          width: "550px",
          height: "550px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(168, 85, 247, 0.18) 0%, rgba(126, 34, 206, 0.06) 50%, transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />

      {/* Main Video Presentation */}
      <div
        style={{
          position: "relative",
          maxWidth: "880px",
          maxHeight: "85vh",
          width: "92vw",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <video
          ref={videoRef}
          src="/misa_intro.mp4"
          playsInline
          autoPlay
          style={{
            width: "100%",
            maxHeight: "75vh",
            objectFit: "contain",
            borderRadius: "16px",
            boxShadow: "0 20px 60px -15px rgba(0, 0, 0, 0.8), 0 0 40px -10px rgba(168, 85, 247, 0.25)",
            border: "1px solid rgba(168, 85, 247, 0.2)",
            backgroundColor: "#000000",
          }}
        />

        {/* Subtle Video Progress Bar */}
        <div
          style={{
            width: "100%",
            height: "3px",
            backgroundColor: "rgba(255, 255, 255, 0.08)",
            borderRadius: "2px",
            marginTop: "12px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              width: `${progress}%`,
              height: "100%",
              background: "linear-gradient(90deg, #A855F7, #EC4899)",
              transition: "width 0.1s linear",
            }}
          />
        </div>
      </div>

      {/* Skip Button */}
      {canSkip && (
        <button
          onClick={handleComplete}
          style={{
            position: "absolute",
            top: "24px",
            right: "28px",
            background: "rgba(18, 12, 28, 0.7)",
            backdropFilter: "blur(12px)",
            border: "1px solid rgba(168, 85, 247, 0.3)",
            borderRadius: "20px",
            color: "#E2E8F0",
            padding: "8px 18px",
            fontSize: "12.5px",
            fontWeight: 500,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s ease",
            boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "rgba(168, 85, 247, 0.7)";
            e.currentTarget.style.backgroundColor = "rgba(28, 18, 44, 0.85)";
            e.currentTarget.style.transform = "translateY(-1px)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "rgba(168, 85, 247, 0.3)";
            e.currentTarget.style.backgroundColor = "rgba(18, 12, 28, 0.7)";
            e.currentTarget.style.transform = "translateY(0)";
          }}
        >
          <span>O'tkazib yuborish</span>
          <span
            style={{
              fontSize: "10.5px",
              background: "rgba(255, 255, 255, 0.1)",
              padding: "2px 6px",
              borderRadius: "4px",
              color: "#94A3B8",
            }}
          >
            Esc
          </span>
        </button>
      )}
    </div>
  );
};
