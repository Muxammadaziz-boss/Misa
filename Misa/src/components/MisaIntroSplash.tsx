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
  const [progress, setProgress] = useState(0);
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
      }, 250);
    }, remaining);
  }, [minDurationMs, onFinish]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Autoplay video with sound, fallback to muted if system restricts
    const playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise.catch(() => {
        video.muted = true;
        video.play().catch(() => {
          // If video completely fails to play after all fallbacks
          handleComplete(false);
        });
      });
    }

    const handleTimeUpdate = () => {
      if (video.duration && !isNaN(video.duration)) {
        setProgress((video.currentTime / video.duration) * 100);
      }
    };

    // Intro video must play from start to end; it cannot be skipped
    const onVideoEnd = () => handleComplete(false);

    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("ended", onVideoEnd);
    video.addEventListener("error", onVideoEnd);

    return () => {
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("ended", onVideoEnd);
      video.removeEventListener("error", onVideoEnd);
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
  }, [handleComplete]);

  return (
    <div
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

      {/* Fullscreen Video Presentation with Zero Margin */}
      <video
        ref={videoRef}
        playsInline
        autoPlay
        muted
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
        <source src="/Misa.mp4" type="video/mp4" />
        <source src="/Misa1.mp4" type="video/mp4" />
        <source src="/misa_intro.mp4" type="video/mp4" />
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
