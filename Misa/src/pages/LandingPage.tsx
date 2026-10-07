import React, { useState, useEffect, useRef } from "react";
import { MisaAperture, OrbState } from "../components/MisaAperture";
import { MarkdownView } from "../components/MarkdownView";
import {
  ArrowUpIcon,
  MicIcon,
  SparklesIcon,
  VolumeIcon,
  CloseIcon,
  RefreshIcon,
  CodeIcon,
  CpuIcon,
  SchedulerIcon,
  DatabaseIcon,
  ChatIcon,
} from "../components/icons/Icons";
import {
  backendService,
  VoiceState,
  BackendStatus,
  SystemTelemetry,
  AgentStepItem,
} from "../services/backendService";

interface LandingPageProps {
  userName?: string;
  onStartChat: (initialQuery?: string) => void;
  onStartVoice: () => void;
  onNavigate?: (path: string) => void;
}

const QUICK_SUGGESTIONS = [
  {
    id: "voice",
    label: "Ovozli suhbat",
    query: "__VOICE__",
    icon: "eq",
  },
  {
    id: "code",
    label: "Kod va tahlil",
    query: "Python dasturlash tilida samarali arxitektura va kod tahlili bo'yicha yordam ber",
    icon: "code",
  },
  {
    id: "write",
    label: "Matn yaratish",
    query: "Professional loyiha taqdimoti va rasmiy xat matnini tayyorlashga yordam ber",
    icon: "edit",
  },
  {
    id: "system",
    label: "Kompyuter holati",
    query: "Kompyuterimning joriy CPU, RAM va xotira holatini tahlil qilib ber",
    icon: "cpu",
  },
  {
    id: "plan",
    label: "Bugungi reja",
    query: "Bugungi vazifalarim va kun tartibimni samarali rejalashtirib ber",
    icon: "plan",
  },
];

export function formatUzbekDateTime(date: Date): string {
  const dayNames = ["Yakshanba", "Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba"];
  const monthNames = [
    "yanvar",
    "fevral",
    "mart",
    "aprel",
    "may",
    "iyun",
    "iyul",
    "avgust",
    "sentabr",
    "oktabr",
    "noyabr",
    "dekabr",
  ];
  const day = dayNames[date.getDay()];
  const dateNum = date.getDate();
  const month = monthNames[date.getMonth()];
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${day}, ${dateNum}-${month} • ${hours}:${minutes}`;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  userName = "Ustoz",
  onStartChat,
  onNavigate,
}) => {
  const [queryText, setQueryText] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [orbState, setOrbState] = useState<OrbState>("idle");
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ status: "connecting" });

  // Response & Agent Execution State on Home
  const [userTranscript, setUserTranscript] = useState<string>("");
  const [assistantResponse, setAssistantResponse] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [micError, setMicError] = useState<string | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<
    { name: string; size: number; content?: string; dataUrl?: string; type?: "text" | "image" }[]
  >([]);

  // Startup System Briefing (Voice & Banner)
  const [startupBriefing, setStartupBriefing] = useState<string | null>(null);
  const [briefingSeverity, setBriefingSeverity] = useState<"success" | "warning" | "error">("success");
  const [isBriefingVisible, setIsBriefingVisible] = useState<boolean>(true);

  // Telemetry & Agent Loop
  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);
  const [currentTime, setCurrentTime] = useState<Date>(new Date());
  const [agentGoal, setAgentGoal] = useState<string | null>(null);
  const [agentSteps, setAgentSteps] = useState<AgentStepItem[]>([]);
  const [activeVoiceType, setActiveVoiceType] = useState<string>("ayol");

  const recognitionRef = useRef<any>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const activeTranscriptRef = useRef<string>("");
  const silenceTimerRef = useRef<any>(null);
  const isStoppingRef = useRef<boolean>(false);
  const isListeningRef = useRef<boolean>(false);
  const isSecretaryModeRef = useRef<boolean>(true);

  useEffect(() => {
    backendService.getAccount().then((acc) => {
      if (acc && acc.voice_type) {
        setActiveVoiceType(acc.voice_type);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const clockInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 15000);

    const fetchMetrics = async () => {
      try {
        const data = await backendService.getSystemTelemetry();
        if (data && data.ok !== false) {
          setTelemetry(data);
          // Backend aloqada ekanligi tasdiqlandi -> xatolik bannerini darhol yopamiz
          setStartupBriefing((prev) => {
            if (prev && prev.includes("18420-portda ishga tushirilishi kutilmoqda")) {
              return null;
            }
            return prev;
          });
        }
      } catch {
        // Silent fallback
      }
    };
    fetchMetrics();
    const metricsInterval = setInterval(fetchMetrics, 6000);

    return () => {
      clearInterval(clockInterval);
      clearInterval(metricsInterval);
    };
  }, []);

  useEffect(() => {
    const unsubVoice = backendService.onVoiceStateChange((state) => {
      setVoiceState(state);
      setOrbState(state);
    });
    const unsubStatus = backendService.onStatusChange((status) => {
      setBackendStatus(status);
      if (status.status === "online") {
        setStartupBriefing((prev) => {
          if (prev && prev.includes("18420-portda ishga tushirilishi kutilmoqda")) {
            return null;
          }
          return prev;
        });
      }
    });
    const unsubResp = backendService.onResponse((data) => {
      setAssistantResponse(data.text);
      setIsProcessing(false);
    });
    const unsubTranscript = backendService.onTranscript((data) => {
      if (data.sender === "user") {
        setUserTranscript(data.text);
      } else {
        setAssistantResponse(data.text);
      }
    });
    const unsubOrb = backendService.onOrbStateChange((ev) => {
      setOrbState(ev.state as OrbState);
    });
    const unsubPlan = backendService.onAgentPlan((plan) => {
      setAgentGoal(plan.goal);
      setAgentSteps(plan.steps || []);
    });
    const unsubStep = backendService.onAgentStepUpdate((update) => {
      setAgentSteps((prev) =>
        prev.map((s) =>
          s.id === update.step_id
            ? {
                ...s,
                status: update.status,
                result_summary: update.result_summary ?? s.result_summary,
                error: update.error ?? s.error,
              }
            : s
        )
      );
    });

    // ── App Startup Audio & System Health Briefing ──
    const runStartupBriefing = async () => {
      if (sessionStorage.getItem("misa_v9_startup_briefing_done")) {
        setTimeout(() => {
          startSecretaryListening();
        }, 600);
        return;
      }
      sessionStorage.setItem("misa_v9_startup_briefing_done", "true");

      // Backend ishga tushishi uchun qayta tekshiruv (retry loop, jami ~7 soniya)
      let currentStat: BackendStatus = { status: "connecting" };
      for (let attempt = 0; attempt < 10; attempt++) {
        try {
          currentStat = await backendService.checkStatus();
          if (currentStat.status === "online") break;
        } catch {
          currentStat = { status: "offline" };
        }
        await new Promise((r) => setTimeout(r, 700));
      }

      let account: any = null;
      try {
        account = await backendService.getAccount();
        if (account?.voice_type) {
          setActiveVoiceType(account.voice_type);
        }
      } catch {}

      let textToSpeak = "";
      let severity: "success" | "warning" | "error" = "success";

      if (currentStat.status === "online") {
        const hasKey = account?.has_gemini_key || currentStat.ai_available;
        if (hasKey) {
          severity = "success";
          textToSpeak = `Assalomu alaykum Ustoz! Misa tizimi muvaffaqiyatli ishga tushdi, serverga ulandi. Barcha modullar faol va tayyor. Meni chaqirish uchun "Misa..." deb gapirishingiz mumkin.`;
        } else {
          severity = "warning";
          textToSpeak = `Assalomu alaykum Ustoz! Serverga ulandim, lekin menda xatolik bor: AI kaliti kiritilmagan. Sozlamalar bo'limidan API kalitini kiritishingizni so'rayman.`;
        }
      } else {
        severity = "error";
        textToSpeak = `Salom Ustoz! Menda xatolik bor: mahalliy backend serveriga ulanib bo'lmadi. Server 18420-portda ishga tushirilishi kutilmoqda.`;
      }

      setStartupBriefing(textToSpeak);
      setBriefingSeverity(severity);

      // Faqat server online bo'lsa yoki haqiqiy milliy ovoz bo'lsagina ovozda ijro etamiz
      if (currentStat.status === "online") {
        const voiceChoice = account?.voice_type || activeVoiceType || "ayol";
        await playSpeechAudio(textToSpeak, voiceChoice);
      }
      setTimeout(() => {
        startSecretaryListening();
      }, 500);
    };

    runStartupBriefing();

    return () => {
      unsubVoice();
      unsubStatus();
      unsubResp();
      unsubTranscript();
      unsubOrb();
      unsubPlan();
      unsubStep();
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
      stopAudioMonitor();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
    };
  }, []);

  const startAudioMonitor = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 128;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateLevel = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        setAudioLevel(Math.min(avg / 110, 1.0));
        animFrameRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();
      return true;
    } catch (err: any) {
      if (err?.name === "NotAllowedError" || err?.name === "PermissionDeniedError") {
        setMicError("Tovushli boshqaruv uchun mikrofon ruxsati kerak.");
      } else {
        setMicError("Mikrofon qurilmasi topilmadi yoki band.");
      }
      setVoiceState("error");
      setOrbState("error");
      return false;
    }
  };

  const stopAudioMonitor = () => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch {}
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  };

  // ── Multi-Layer High-Fidelity Speech Player (Edge TTS, Fish Audio, RVC) ──
  const playSpeechAudio = async (text: string, voiceOverride?: string): Promise<void> => {
    const cleanText = text
      .replace(/\[.*?\]\(.*?\)/g, "")
      .replace(/```[\s\S]*?```/g, "")
      .replace(/`.*?`/g, "")
      .replace(/[\*\_~#>]/g, "")
      .replace(/[🎤🗣️📝🎯✅❌⚠️💡📊🎵▶️⏸️🔊🔉🔇📌🤖✨🔹👋]/gu, "")
      .trim();

    if (!cleanText) return;

    // Nutq so'zlanayotganda mikrofondan o'z ovozini eshitib olmasligi uchun tinglashni vaqtinchalik to'xtatamiz
    if (recognitionRef.current && isListeningRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {}
      stopAudioMonitor();
      isListeningRef.current = false;
    }

    setVoiceState("speaking");
    setOrbState("speaking");

    return new Promise<void>(async (resolve) => {
      let resolved = false;
      const finish = () => {
        if (!resolved) {
          resolved = true;
          setVoiceState("idle");
          setOrbState("idle");
          resolve();
          // Misa gapirib bo'lgach, kotiba kabi avtomatik yana eshitishga o'tadi
          if (isSecretaryModeRef.current && !isStoppingRef.current) {
            setTimeout(() => {
              startSecretaryListening();
            }, 350);
          }
        }
      };

      // 1. Backend Edge-TTS orqali yuqori sifatli milliy ovozda ijro etish (uz-UZ-MadinaNeural / uz-UZ-SardorNeural)
      let backendPlayed = false;
      const voiceToUse = voiceOverride || activeVoiceType || "ayol";
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          backendPlayed = await backendService.speakText(cleanText, voiceToUse);
          if (backendPlayed) break;
        } catch {
          backendPlayed = false;
        }
        await new Promise((r) => setTimeout(r, 400));
      }

      if (backendPlayed) {
        // O'zbek tilida o'rtacha gapirish tezligi: soniyasiga ~13 belgi
        const durationMs = Math.max(1600, Math.min(18000, (cleanText.length / 13) * 1000));
        setTimeout(finish, durationMs);
        return;
      }

      // Agar backend bir lahzaga ulanmagan bo'lsa, xunuk inglizcha/ruscha robot ovozlarga
      // aslo o'tmaslik kerak — xavfsiz yakunlaymiz
      finish();
    });
  };

  // ── Wake-Word & Call Prefix Parser ("Misa ...", "Mikasa ...") ──
  const parseMisaInvocation = (rawText: string) => {
    const trimmed = rawText.trim();
    const callRegex = /^(?:(?:salom|assalomu\s+alaykum|hey|ey|o['']?y|hoy|qani|iltimos)\s+)?(?:misa|mikasa|micasa|миса|микаса|мекаса|mekasa)(?:[,\s:!.]+|$)/i;
    const match = trimmed.match(callRegex);
    const containsMisa =
      match !== null ||
      /\b(?:misa|mikasa|micasa|миса|микаса|мекаса|mekasa)\b/i.test(trimmed) ||
      /(?:misa|mikasa|micasa|миса|микаса)/i.test(trimmed);

    let command = trimmed;
    if (match) {
      command = trimmed.slice(match[0].length).trim();
    } else if (containsMisa) {
      command = trimmed.replace(/\b(?:misa|mikasa|micasa|миса|микаса|мекаса|mekasa)\b/gi, "").trim();
    }

    return {
      hasMisa: containsMisa,
      isCallingOnly: containsMisa && (!command || command.length < 2),
      cleanCommand: command || trimmed,
    };
  };

  const resumeSecretaryListening = () => {
    if (isSecretaryModeRef.current && !isStoppingRef.current) {
      setTimeout(() => {
        startSecretaryListening();
      }, 350);
    }
  };

  const executeMisaQuery = async (text: string, speakReply = true, isVoiceInput = false) => {
    const clean = text.trim();
    if (!clean) {
      if (isVoiceInput) resumeSecretaryListening();
      return;
    }

    const invocation = parseMisaInvocation(clean);

    // KOTIBA REJIMI:
    // Agar ovoz orqali eshitilsa va gap ichida "Misa" (yoki "Mikasa") bo'lmasa,
    // xuddi kompaniya kotibi kabi jim eshitib turadi va javob bermaydi (begona suhbatlarga xalal bermaydi).
    if (isVoiceInput && !invocation.hasMisa) {
      setUserTranscript("");
      resumeSecretaryListening();
      return;
    }

    // Foydalanuvchi faqat Misa deb chaqirsa ("Misa", "Salom Misa"):
    if (invocation.isCallingOnly) {
      const greetingResponse = "Labbay Ustoz! Sizni tinglayapman, marhamat buyuring.";
      setUserTranscript(clean);
      setAssistantResponse(greetingResponse);
      setIsProcessing(false);
      if (speakReply) {
        await playSpeechAudio(greetingResponse);
      } else {
        resumeSecretaryListening();
      }
      return;
    }

    const commandToExecute = invocation.cleanCommand || clean;

    const attachmentContext =
      attachedFiles.length > 0
        ? "\n\n[Biriktirilgan fayllar: " +
          attachedFiles
            .map((f) => `${f.name}${f.content ? `:\n${f.content.slice(0, 2000)}` : ""}`)
            .join("\n") +
          "]"
        : "";

    const fullQuery = commandToExecute + attachmentContext;

    const attachedImage = attachedFiles.find((f) => f.dataUrl || f.type === "image");
    const imageToSend = attachedImage?.dataUrl;

    setUserTranscript(clean);
    setAttachedFiles([]);
    setAssistantResponse("");
    setMicError(null);
    setAgentGoal(null);
    setAgentSteps([]);
    setIsProcessing(true);
    setVoiceState("thinking");
    setOrbState("thinking");

    try {
      // Backendga { speak: false } yuboriladi, shunda backend o'zi alohida gapirib 2 marta takrorlanmaydi
      const res = await backendService.sendMessage(fullQuery, { speak: false, image: imageToSend });
      const replyText = res.reply || "Buyruq bajarildi.";
      setAssistantResponse(replyText);
      setIsProcessing(false);

      if (speakReply) {
        await playSpeechAudio(replyText);
      } else {
        setVoiceState("idle");
        setOrbState("idle");
        if (isVoiceInput) {
          resumeSecretaryListening();
        }
      }
    } catch {
      const errReply = "Kechirasiz, Misa serveri bilan bog'lanishda xatolik yuz berdi.";
      setAssistantResponse(errReply);
      setIsProcessing(false);
      setVoiceState("error");
      setOrbState("error");
      if (speakReply) {
        await playSpeechAudio(errReply);
      } else if (isVoiceInput) {
        resumeSecretaryListening();
      }
    }
  };

  const startSecretaryListening = async () => {
    if (isListeningRef.current || (voiceState as string) === "speaking" || isProcessing) {
      return;
    }
    isStoppingRef.current = false;
    isSecretaryModeRef.current = true;
    isListeningRef.current = true;
    activeTranscriptRef.current = "";

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRecognition) {
      const micAllowed = await startAudioMonitor();
      if (!micAllowed) {
        isListeningRef.current = false;
        return;
      }

      try {
        if (recognitionRef.current) {
          try {
            recognitionRef.current.abort();
          } catch {}
        }
        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;
        recognition.lang = "uz-UZ";
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;

        setVoiceState("listening");
        setOrbState("listening");

        let finalizedText = "";

        recognition.onresult = (event: any) => {
          let interimText = "";
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalizedText += (finalizedText ? " " : "") + transcript;
            } else {
              interimText += transcript;
            }
          }
          const currentTotal = (finalizedText + " " + interimText).trim();
          activeTranscriptRef.current = currentTotal;
          setUserTranscript(currentTotal);

          // Reset silence timer on any speech detected
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
          }
          silenceTimerRef.current = setTimeout(() => {
            const captured = activeTranscriptRef.current.trim();
            if (captured) {
              const inv = parseMisaInvocation(captured);
              if (!inv.hasMisa) {
                // Xonadagi begona suhbat, Misa chaqirilmagan -> jim e'tiborsiz qoldiriladi
                activeTranscriptRef.current = "";
                setUserTranscript("");
                return;
              }
              // Misa chaqirildi!
              activeTranscriptRef.current = "";
              if (recognitionRef.current) {
                try {
                  recognitionRef.current.stop();
                } catch {}
              }
              stopAudioMonitor();
              isListeningRef.current = false;
              executeMisaQuery(captured, true, true);
            }
          }, 1800);
        };

        recognition.onerror = (event: any) => {
          if (event.error === "not-allowed" || event.error === "service-not-allowed") {
            isListeningRef.current = false;
            stopAudioMonitor();
            setMicError("Tovushli boshqaruv uchun mikrofon ruxsati kerak.");
            setVoiceState("error");
            setOrbState("error");
          } else if (event.error === "no-speech") {
            // Xonadagi tabiiy jimlik - kotiba tinglashda davom etadi
          } else {
            console.warn("Speech recognition notice:", event.error);
          }
        };

        recognition.onend = () => {
          if (isStoppingRef.current) {
            isListeningRef.current = false;
            return;
          }
          const gathered = activeTranscriptRef.current.trim();
          activeTranscriptRef.current = "";
          if (gathered) {
            const inv = parseMisaInvocation(gathered);
            if (inv.hasMisa) {
              isListeningRef.current = false;
              stopAudioMonitor();
              executeMisaQuery(gathered, true, true);
              return;
            }
          }
          // Doimiy kotiba tinglash tsikli: uzilish bo'lsa darhol qayta ulanadi
          if (isSecretaryModeRef.current && !isStoppingRef.current) {
            try {
              recognition.start();
            } catch {
              setTimeout(() => {
                if (isSecretaryModeRef.current && !isStoppingRef.current) {
                  startSecretaryListening();
                }
              }, 400);
            }
          } else {
            isListeningRef.current = false;
            stopAudioMonitor();
          }
        };

        recognition.start();
        return;
      } catch (e) {
        isListeningRef.current = false;
        stopAudioMonitor();
        console.error("Kotiba tinglash xatosi:", e);
      }
    }

    // Web Speech API mavjud bo'lmasa backend fon xizmatiga ulanish
    setUserTranscript("");
    setAssistantResponse("");
    setVoiceState("listening");
    setOrbState("listening");
    await backendService.startVoice();
  };

  const handleToggleVoice = async () => {
    setMicError(null);

    if (isListeningRef.current || (voiceState as string) === "listening") {
      isStoppingRef.current = true;
      isSecretaryModeRef.current = false;
      isListeningRef.current = false;
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
        silenceTimerRef.current = null;
      }
      stopAudioMonitor();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
      await backendService.stopVoice();
      activeTranscriptRef.current = "";
      setVoiceState("idle");
      setOrbState("idle");
      return;
    }

    // Foydalanuvchi aperturaga yoki mikrofonga bosib Kotiba rejimini faollashtirdi
    isStoppingRef.current = false;
    isSecretaryModeRef.current = true;
    startSecretaryListening();
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!queryText.trim() && attachedFiles.length === 0) return;
    const text = queryText.trim() || "Biriktirilgan faylni tahlil qil";
    setQueryText("");
    executeMisaQuery(text, false, false);
  };

  const handleSuggestionClick = (item: (typeof QUICK_SUGGESTIONS)[0]) => {
    if (item.query === "__VOICE__") {
      handleToggleVoice();
      return;
    }
    executeMisaQuery(item.query, false, false);
  };

  const handleFileAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    Array.from(files).forEach((file) => {
      if (file.type.startsWith("image/") || /\.(png|jpe?g|webp|gif|bmp)$/i.test(file.name)) {
        const reader = new FileReader();
        reader.onload = () => {
          setAttachedFiles((prev) => [
            ...prev,
            { name: file.name, size: file.size, dataUrl: String(reader.result || ""), type: "image" },
          ]);
        };
        reader.readAsDataURL(file);
      } else if (
        file.size <= 256 * 1024 &&
        (file.type.startsWith("text/") ||
          /\.(txt|md|json|py|ts|tsx|js|csv|html|css|log)$/i.test(file.name))
      ) {
        const reader = new FileReader();
        reader.onload = () => {
          setAttachedFiles((prev) => [
            ...prev,
            { name: file.name, size: file.size, content: String(reader.result || ""), type: "text" },
          ]);
        };
        reader.readAsText(file);
      } else {
        setAttachedFiles((prev) => [...prev, { name: file.name, size: file.size }]);
      }
    });
    e.target.value = "";
  };

  const effectiveOrbState: OrbState =
    backendStatus.status === "offline"
      ? "error"
      : backendStatus.status === "connecting"
      ? "thinking"
      : isProcessing && orbState === "idle"
      ? "thinking"
      : orbState;

  const getStatusSubtitle = () => {
    switch (effectiveOrbState) {
      case "listening":
        return userTranscript
          ? `Tinglanmoqda: "${userTranscript}"`
          : 'Kotiba rejimi faol — Misa eshitmoqda... Chaqirish uchun "Misa..." deb gapiring';
      case "thinking":
        return "So'rovingiz tahlil qilinmoqda...";
      case "planning":
        return "Reja tuzilmoqda...";
      case "acting":
        return "Buyruq bajarilmoqda...";
      case "verifying":
        return "Natija tekshirilmoqda...";
      case "replanning":
        return "Yangi yondashuv tanlanmoqda...";
      case "speaking":
        return "Misa javob bermoqda...";
      case "error":
        return (
          micError ||
          (backendStatus.status === "offline"
            ? "Menda xatolik bor: server bilan aloqa uzilgan (Port 18420)"
            : "Tizim holatini tekshiring yoki qayta urinib ko'ring")
        );
      case "idle":
      default:
        return 'Kotiba rejimi pauzada. Boshlash uchun markaziy aperturaga bosing';
    }
  };

  const displayName = userName || backendStatus.user || "Ustoz";

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 24px 24px 24px",
        overflowY: "auto",
        zIndex: 5,
      }}
    >
      {/* Hidden File Input for Composer Attachment */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: "none" }}
        onChange={handleFileAttach}
      />

      {/* Top Spacer */}
      <div style={{ height: "4px", flexShrink: 0 }} />

      {/* ══════════════════════════════════════════════════════════════════
          CENTER STAGE: STATUS BADGE, GREETING & OPTICAL AI APERTURE
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          width: "100%",
          maxWidth: "780px",
          margin: "auto 0",
          textAlign: "center",
        }}
      >
        {/* 1. Status Badge Pill */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            padding: "5px 14px",
            borderRadius: "9999px",
            background: "rgba(147, 3, 197, 0.12)",
            border: "1px solid rgba(192, 76, 253, 0.3)",
            marginBottom: "16px",
            boxShadow: "0 0 20px rgba(147, 3, 197, 0.15)",
          }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor:
                backendStatus.status === "online"
                  ? "#4EDEA3"
                  : backendStatus.status === "connecting"
                  ? "#F59E0B"
                  : "#FF716C",
              boxShadow:
                backendStatus.status === "online"
                  ? "0 0 8px #4EDEA3"
                  : "0 0 8px rgba(245, 158, 11, 0.8)",
            }}
          />
          <span
            style={{
              fontSize: "11px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#E8B3FF",
            }}
          >
            Misa Autonom Agent Faol
          </span>
          <span style={{ color: "rgba(255,255,255,0.2)", fontSize: "11px" }}>•</span>
          <span style={{ fontSize: "11px", color: "var(--text-secondary)", fontWeight: 500 }}>
            {formatUzbekDateTime(currentTime)}
          </span>
          {telemetry && (
            <>
              <span style={{ color: "rgba(255,255,255,0.2)", fontSize: "11px" }}>•</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                CPU {Math.round(telemetry.cpu_percent)}% · RAM {Math.round(telemetry.ram_percent)}%
              </span>
            </>
          )}
        </div>

        {/* 1.5. Startup System Status & Diagnostic Briefing Banner */}
        {startupBriefing && isBriefingVisible && (
          <div
            className="misa-glass-card"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "10px",
              padding: "9px 18px",
              borderRadius: "16px",
              marginBottom: "18px",
              maxWidth: "680px",
              width: "100%",
              background:
                briefingSeverity === "success"
                  ? "rgba(18, 53, 36, 0.72)"
                  : briefingSeverity === "warning"
                  ? "rgba(64, 43, 10, 0.72)"
                  : "rgba(56, 14, 20, 0.72)",
              border:
                briefingSeverity === "success"
                  ? "1px solid rgba(78, 222, 163, 0.45)"
                  : briefingSeverity === "warning"
                  ? "1px solid rgba(245, 158, 11, 0.45)"
                  : "1px solid rgba(255, 113, 108, 0.45)",
              boxShadow: "0 6px 24px rgba(0, 0, 0, 0.35)",
            }}
          >
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                flexShrink: 0,
                backgroundColor:
                  briefingSeverity === "success"
                    ? "#4EDEA3"
                    : briefingSeverity === "warning"
                    ? "#F59E0B"
                    : "#FF716C",
                boxShadow: `0 0 10px ${
                  briefingSeverity === "success"
                    ? "#4EDEA3"
                    : briefingSeverity === "warning"
                    ? "#F59E0B"
                    : "#FF716C"
                }`,
              }}
            />
            <span
              style={{
                fontSize: "12.5px",
                color:
                  briefingSeverity === "success"
                    ? "#C2F0DD"
                    : briefingSeverity === "warning"
                    ? "#FDE68A"
                    : "#FFD1D0",
                flex: 1,
                textAlign: "left",
                fontWeight: 500,
                lineHeight: 1.45,
              }}
            >
              {startupBriefing}
            </span>
            <button
              type="button"
              onClick={() => playSpeechAudio(startupBriefing)}
              title="Qayta tinglash"
              style={{
                background: "rgba(255, 255, 255, 0.08)",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                borderRadius: "8px",
                padding: "4px 8px",
                color: "#FFFFFF",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "11px",
              }}
            >
              <VolumeIcon size={12} color="currentColor" />
              <span>Ovozda</span>
            </button>
            <button
              type="button"
              onClick={() => setIsBriefingVisible(false)}
              title="Yopish"
              style={{
                background: "transparent",
                border: "none",
                color: "rgba(255, 255, 255, 0.5)",
                cursor: "pointer",
                padding: "4px",
                display: "inline-flex",
                alignItems: "center",
              }}
            >
              <CloseIcon size={12} color="currentColor" />
            </button>
          </div>
        )}

        {/* 2. Greeting Typography */}
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(28px, 4vw, 40px)",
            fontWeight: 700,
            letterSpacing: "-0.025em",
            color: "#F5F0FF",
            marginBottom: "8px",
            lineHeight: 1.18,
          }}
        >
          Salom,{" "}
          <span
            style={{
              background: "linear-gradient(90deg, #E8B3FF 0%, #C04CFD 50%, #9303C5 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            {displayName}
          </span>
        </h1>

        <p
          style={{
            fontSize: "15px",
            fontWeight: 400,
            color:
              (effectiveOrbState as string) === "listening"
                ? "#4EDEA3"
                : effectiveOrbState === "error"
                ? "#FF716C"
                : "var(--text-secondary)",
            marginBottom: "32px",
            transition: "color 0.25s ease",
          }}
        >
          {getStatusSubtitle()}
        </p>

        {/* 3. Focal Point: Misa Abstract Optical AI Aperture */}
        <div style={{ marginBottom: assistantResponse || micError || agentSteps.length > 0 ? "22px" : "12px" }}>
          <MisaAperture
            width="380px"
            height="180px"
            state={effectiveOrbState}
            audioLevel={audioLevel}
            showStatusPill={true}
            onClick={handleToggleVoice}
          />
        </div>

        {/* 4. Microphone Error Banner (if any) */}
        {micError && (
          <div
            className="misa-glass-card"
            style={{
              marginTop: "12px",
              padding: "12px 18px",
              borderRadius: "16px",
              border: "1px solid rgba(255, 113, 108, 0.4)",
              background: "rgba(38, 12, 22, 0.78)",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              maxWidth: "540px",
              width: "100%",
            }}
          >
            <span style={{ fontSize: "12.5px", color: "#FFB4AB", flex: 1, textAlign: "left" }}>
              {micError}
            </span>
            <button
              type="button"
              onClick={handleToggleVoice}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "999px",
                background: "rgba(255, 113, 108, 0.2)",
                border: "1px solid rgba(255, 113, 108, 0.4)",
                color: "#FFDAD6",
                fontSize: "11.5px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              <RefreshIcon size={12} color="currentColor" />
              <span>Qayta urinish</span>
            </button>
          </div>
        )}

        {/* 5. Multi-Step Autonomous Agent Plan Card */}
        {agentSteps.length > 0 && (
          <div
            className="misa-ultra-glass"
            style={{
              marginTop: "14px",
              width: "100%",
              maxWidth: "620px",
              padding: "14px 18px",
              borderRadius: "20px",
              textAlign: "left",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "8px",
              }}
            >
              <span
                style={{
                  fontSize: "11.5px",
                  fontWeight: 700,
                  color: "#E8B3FF",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Avtonom Reja: {agentGoal || "Vazifa"}
              </span>
              <span style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                {agentSteps.filter((s) => s.status === "completed").length}/{agentSteps.length} qadam
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {agentSteps.map((st) => (
                <div
                  key={st.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "12px",
                    color: st.status === "completed" ? "#4EDEA3" : "#F5F0FF",
                  }}
                >
                  <span>
                    {st.status === "completed"
                      ? "✓"
                      : st.status === "running"
                      ? "⟳"
                      : st.status === "failed"
                      ? "✕"
                      : "•"}
                  </span>
                  <span style={{ fontWeight: 600 }}>{st.tool}:</span>
                  <span style={{ color: "var(--text-secondary)", flex: 1 }}>
                    {st.result_summary || st.description}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. Live Misa Response Card on Home */}
        {(userTranscript || assistantResponse) && (
          <div
            className="misa-ultra-glass"
            style={{
              marginTop: "14px",
              width: "100%",
              maxWidth: "660px",
              padding: "16px 20px",
              borderRadius: "22px",
              textAlign: "left",
              maxHeight: "240px",
              overflowY: "auto",
              animation: "misa-fade-in 0.2s ease-out",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "8px",
                gap: "10px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
                <SparklesIcon size={14} color="#C04CFD" />
                <span style={{ fontSize: "12px", fontWeight: 700, color: "#E8B3FF" }}>
                  Misa AI Javobi
                </span>
                {userTranscript && (
                  <span
                    style={{
                      fontSize: "11px",
                      color: "var(--text-muted)",
                      maxWidth: "260px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    • "{userTranscript}"
                  </span>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                {assistantResponse && (
                  <>
                    <button
                      type="button"
                      onClick={() => playSpeechAudio(assistantResponse)}
                      title="Ovozda eshitish"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "5px",
                        padding: "4px 10px",
                        borderRadius: "999px",
                        background: "rgba(147, 3, 197, 0.18)",
                        border: "1px solid rgba(192, 76, 253, 0.35)",
                        color: "#E8B3FF",
                        fontSize: "11px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      <VolumeIcon size={12} color="#E8B3FF" />
                      <span>Tinglash</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => onStartChat()}
                      title="To'liq suhbat oynasida ochish"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "5px",
                        padding: "4px 10px",
                        borderRadius: "999px",
                        background: "rgba(255, 255, 255, 0.06)",
                        border: "1px solid rgba(255, 255, 255, 0.12)",
                        color: "var(--text-primary)",
                        fontSize: "11px",
                        fontWeight: 500,
                        cursor: "pointer",
                      }}
                    >
                      <ChatIcon size={12} color="currentColor" />
                      <span>Suhbatda ochish</span>
                    </button>
                  </>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setUserTranscript("");
                    setAssistantResponse("");
                    setAgentSteps([]);
                  }}
                  title="Yopish"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "24px",
                    height: "24px",
                    borderRadius: "50%",
                    background: "rgba(255, 255, 255, 0.06)",
                    color: "var(--text-secondary)",
                    cursor: "pointer",
                  }}
                >
                  <CloseIcon size={12} color="currentColor" />
                </button>
              </div>
            </div>

            {assistantResponse ? (
              <div style={{ fontSize: "13.5px", color: "#F5F0FF", lineHeight: 1.6 }}>
                <MarkdownView content={assistantResponse} />
              </div>
            ) : (
              <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                Misa javob tayyorlamoqda...
              </div>
            )}
          </div>
        )}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          BOTTOM SECTION: SUGGESTION PILLS & FLOATING GLASS COMPOSER
         ══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          width: "100%",
          maxWidth: "740px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "14px",
          marginTop: "16px",
          flexShrink: 0,
        }}
      >
        {/* Quick Suggestion Pills */}
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
          }}
        >
          {QUICK_SUGGESTIONS.map((item) => {
            const isVoiceBtn = item.id === "voice";
            const isActiveVoice = isVoiceBtn && voiceState === "listening";
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleSuggestionClick(item)}
                className="misa-pill"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 16px",
                  borderRadius: "9999px",
                  fontSize: "12.5px",
                  fontWeight: 500,
                  color: isActiveVoice ? "#FFFFFF" : "var(--text-secondary)",
                  background: isActiveVoice
                    ? "linear-gradient(135deg, #9303C5 0%, #68008E 100%)"
                    : undefined,
                  borderColor: isActiveVoice ? "rgba(232, 179, 255, 0.5)" : undefined,
                  cursor: "pointer",
                }}
              >
                {item.icon === "eq" && <MicIcon size={14} color="#E8B3FF" />}
                {item.icon === "code" && <CodeIcon size={14} color="#E8B3FF" />}
                {item.icon === "edit" && <SparklesIcon size={14} color="#E8B3FF" />}
                {item.icon === "cpu" && <CpuIcon size={14} color="#E8B3FF" />}
                {item.icon === "plan" && <SchedulerIcon size={14} color="#E8B3FF" />}
                <span>{item.label}</span>
              </button>
            );
          })}

          {onNavigate && (
            <button
              type="button"
              onClick={() => onNavigate("/memory")}
              className="misa-pill"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                borderRadius: "9999px",
                fontSize: "12.5px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                cursor: "pointer",
              }}
            >
              <DatabaseIcon size={14} color="#E8B3FF" />
              <span>Xotiralar</span>
            </button>
          )}
        </div>

        {/* Attached Files Chips (if any) */}
        {attachedFiles.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "8px",
              width: "100%",
              padding: "0 8px",
            }}
          >
            {attachedFiles.map((f, idx) => (
              <div
                key={idx}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "4px 10px",
                  borderRadius: "999px",
                  background: "rgba(147, 3, 197, 0.2)",
                  border: "1px solid rgba(192, 76, 253, 0.35)",
                  fontSize: "11.5px",
                  color: "#E8B3FF",
                }}
              >
                <span>📎 {f.name}</span>
                <button
                  type="button"
                  onClick={() => setAttachedFiles((prev) => prev.filter((_, i) => i !== idx))}
                  style={{ color: "#E8B3FF", cursor: "pointer", fontSize: "12px" }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Raycast-Style Floating Dark Glass Input Bar */}
        <form
          onSubmit={handleFormSubmit}
          style={{
            width: "100%",
            position: "relative",
          }}
        >
          <div
            style={{
              width: "100%",
              borderRadius: "20px",
              padding: "8px 10px 8px 14px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              background: "rgba(11, 15, 28, 0.84)",
              backdropFilter: "blur(28px) saturate(190%)",
              WebkitBackdropFilter: "blur(28px) saturate(190%)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              boxShadow:
                "0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(147, 3, 197, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.12)",
            }}
          >
            {/* Left Attachment Action */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Fayl biriktirish"
              aria-label="Fayl biriktirish"
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "12px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-secondary)",
                background: "transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
                flexShrink: 0,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255, 255, 255, 0.06)";
                e.currentTarget.style.color = "#FFFFFF";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "var(--text-secondary)";
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>

            {/* Input Field */}
            <input
              type="text"
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder='Misa bilan suhbatlashing... (masalan: "Misa, bugun ob-havo qanday?")'
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: "14px",
                color: "#F5F0FF",
                padding: "6px 4px",
              }}
            />

            {/* Right Actions: Send */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
              <button
                type="submit"
                disabled={!queryText.trim() && attachedFiles.length === 0}
                title="Yuborish"
                aria-label="Yuborish"
                className="misa-btn-violet"
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: queryText.trim() || attachedFiles.length > 0 ? 1 : 0.45,
                  cursor: queryText.trim() || attachedFiles.length > 0 ? "pointer" : "default",
                }}
              >
                <ArrowUpIcon size={16} color="#FFFFFF" />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
