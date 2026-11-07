import React, { useState, useRef, useEffect, useCallback } from "react";

interface MisaIntroSplashProps {
  onFinish: () => void;
  minDurationMs?: number;
}

const INTRO_SOURCES = ["/Misa.mp4", "/misa_intro.mp4", "/Misa1.mp4"];

export const MisaIntroSplash: React.FC<MisaIntroSplashProps> = ({
  onFinish,
  minDurationMs = 1500,
}) => {
  const [isFading, setIsFading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [sourceIndex, setSourceIndex] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const completedRef = useRef<boolean>(false);

  const handleComplete = useCallback((instant: boolean = false) => {
    if (completedRef.current) return;
    completedRef.current = true;

    // Immediately stop video and exit picture-in-picture if triggered
    try {
      if ((document as any).pictureInPictureElement) {
        (document as any).exitPictureInPicture().catch(() => {});
      }
    } catch {}

    if (videoRef.current) {
      try {
        videoRef.current.pause();
        videoRef.current.removeAttribute("src");
        videoRef.current.load();
      } catch {}
    }

    if (instant) {
      setIsFading(true);
      onFinish();
      return;
    }

    // Enforce smooth minimum time so it doesn't flash if video ends instantly
    const elapsed = Date.now() - startTimeRef.current;
    const remaining = Math.max(0, minDurationMs - elapsed);

    setTimeout(() => {
      setIsFading(true);
      setTimeout(() => {
        onFinish();
      }, 280);
    }, remaining);
  }, [minDurationMs, onFinish]);

  // Unmute or resume audio on user interaction if restricted by browser policy
  const handleUserInteraction = useCallback(() => {
    const video = videoRef.current;
    if (video) {
      if (video.paused) {
        video.play().catch(() => {});
      }
      if (video.muted) {
        video.muted = false;
        video.volume = 1.0;
      }
    }
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.muted = false;
    video.volume = 1.0;

    // Autoplay video with sound, fallback to muted only if system autoplay policy restricts
    const playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        console.warn("[MisaIntroSplash] Audio autoplay restricted, trying muted fallback:", err);
        video.muted = true;
        video.play().catch((playErr) => {
          console.warn("[MisaIntroSplash] Muted video play failed:", playErr);
          // Try next fallback source if available
          if (sourceIndex < INTRO_SOURCES.length - 1) {
            setSourceIndex((prev) => prev + 1);
          } else {
            handleComplete(false);
          }
        });
      });
    }

    const handleTimeUpdate = () => {
      if (video.duration && !isNaN(video.duration)) {
        setProgress((video.currentTime / video.duration) * 100);
      }
    };

    // Intro video must play from start to end; it finishes when playback ends
    const onVideoEnd = () => handleComplete(false);

    const onVideoError = () => {
      console.warn(`[MisaIntroSplash] Error on source: ${INTRO_SOURCES[sourceIndex]}`);
      if (sourceIndex < INTRO_SOURCES.length - 1) {
        setSourceIndex((prev) => prev + 1);
      } else {
        handleComplete(false);
      }
    };

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("ended", onVideoEnd);
    video.addEventListener("error", onVideoError);

    // Global listener to unmute on first click or key if muted by policy
    window.addEventListener("pointerdown", handleUserInteraction);
    window.addEventListener("keydown", handleUserInteraction);

    // Safety timeout in case video stalls indefinitely
    const safetyTimeout = setTimeout(() => {
      handleComplete(false);
    }, 15000);

    return () => {
      clearTimeout(safetyTimeout);
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("ended", onVideoEnd);
      video.removeEventListener("error", onVideoError);
      window.removeEventListener("pointerdown", handleUserInteraction);
      window.removeEventListener("keydown", handleUserInteraction);
      try {
        if ((document as any).pictureInPictureElement) {
          (document as any).exitPictureInPicture().catch(() => {});
        }
      } catch {}
      try {
        video.pause();
        video.removeAttribute("src");
        video.load();
      } catch {}
    };
  }, [handleComplete, handleUserInteraction, sourceIndex]);

  return (
    <div
      onClick={handleUserInteraction}
      onContextMenu={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
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
        cursor: "default",
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

      {/* Fullscreen Video Presentation with Zero Margin and Full Audio */}
      <video
        ref={videoRef}
        key={INTRO_SOURCES[sourceIndex]}
        src={INTRO_SOURCES[sourceIndex]}
        playsInline
        autoPlay
        controls={false}
        disablePictureInPicture
        controlsList="nodownload noplaybackrate nofullscreen noremoteplayback"
        onContextMenu={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          backgroundColor: "#000000",
          border: "none",
          margin: 0,
          padding: 0,
          display: "block",
          pointerEvents: "none",
        }}
      >
        <source src={INTRO_SOURCES[sourceIndex]} type="video/mp4" />
        {INTRO_SOURCES.filter((_, i) => i !== sourceIndex).map((s) => (
          <source key={s} src={s} type="video/mp4" />
        ))}
      </video>

      {/* Bottom Edge Progress Bar */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          width: "100%",
          height: "3px",
          backgroundColor: "rgba(255, 255, 255, 0.12)",
          zIndex: 20,
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
  );
};

export default MisaIntroSplash;
