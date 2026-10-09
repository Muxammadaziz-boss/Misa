 # -*- coding: utf-8 -*-
"""
Misa AI — Production Autonomous Conversational Voice Service
To'liq siklli avtonom ovozli yordamchi dvigateli:
Wake Word ("Misa") -> Listening -> Streaming VAD -> STT -> Misa AI -> Streaming TTS -> Interruptible Playback ("To'xta") -> Multi-turn Follow-up
"""

import os
import re
import time
import logging
import threading
from typing import Optional, Callable, Dict, Any, List

import numpy as np

from .devices import MicrophoneManager
from .cancellation import CancellationToken
from .wake_word import WakeWordDetector
from .vad import StreamingVAD
from .barge_in import BargeInDetector
from .stt_provider import STTManager
from .session_manager import get_session_manager, ConversationSession
from .security import get_security_guard, VoiceSecurityGuard
from .voice_manager import get_voice_manager, VoiceManager
from .voice_registry import get_voice_registry

logger = logging.getLogger("VoiceService")


class VoiceServiceState:
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    ACKNOWLEDGING = "acknowledging"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ERROR = "error"


class ConversationalVoiceService:
    """
    Misa AI ning asosiy ishlab chiqarish (production) ovozli xizmati.
    Barcha audio oqimlarini boshqaradi va MisaAperture bilan sinxronlashadi.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        voice_id: Optional[str] = None
    ):
        self.sample_rate = sample_rate
        self.voice_id = voice_id or "ayol"

        # Quyi modullar
        self.mic_manager: MicrophoneManager = MicrophoneManager.get_instance()
        self.wake_detector = WakeWordDetector(sample_rate=self.sample_rate, sensitivity=0.65)
        self.vad = StreamingVAD(sample_rate=self.sample_rate, silence_timeout=1.1)
        self.barge_in = BargeInDetector(sample_rate=self.sample_rate)
        self.stt_manager = STTManager()
        self.session: ConversationSession = get_session_manager()
        self.security: VoiceSecurityGuard = get_security_guard()
        self.voice_manager: VoiceManager = get_voice_manager()

        # Oqim va holat
        self.state: str = VoiceServiceState.IDLE
        self._is_running = False
        self._reconnect_stream_event = threading.Event()
        self._lock = threading.Lock()
        self._stream_thread: Optional[threading.Thread] = None
        self._state_callbacks: List[Callable[[str], None]] = []
        self._transcript_callbacks: List[Callable[[str, str], None]] = []
        self._response_callbacks: List[Callable[[str], None]] = []
        self._level_callbacks: List[Callable[[float], None]] = []
        self._wake_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Interruption va playback nazorati
        self._active_cancel_token: Optional[CancellationToken] = None
        self._listening_deadline: float = 0.0
        self.barge_in.on_interrupted = self.handle_interruption

    def add_wake_callback(self, cb: Callable[[Dict[str, Any]], None]) -> None:
        """Uyg'otuvchi so'z aniqlanganda hodisa yuborish (WebSocket va frontend uchun)"""
        with self._lock:
            if cb not in self._wake_callbacks:
                self._wake_callbacks.append(cb)

    def add_state_callback(self, cb: Callable[[str], None]) -> None:
        """Holat o'zgarganda xabar berish (MisaAperture uchun)"""
        with self._lock:
            if cb not in self._state_callbacks:
                self._state_callbacks.append(cb)

    def add_transcript_callback(self, cb: Callable[[str, str], None]) -> None:
        """Transkripsiya paydo bo'lganda (text, sender)"""
        with self._lock:
            if cb not in self._transcript_callbacks:
                self._transcript_callbacks.append(cb)

    def add_response_callback(self, cb: Callable[[str], None]) -> None:
        """AI javobi tayyor bo'lganda"""
        with self._lock:
            if cb not in self._response_callbacks:
                self._response_callbacks.append(cb)

    def add_audio_level_callback(self, cb: Callable[[float], None]) -> None:
        """Mikrofon ovoz darajasi o'zgarganda (0.0 - 1.0)"""
        with self._lock:
            if cb not in self._level_callbacks:
                self._level_callbacks.append(cb)

    def _set_state(self, new_state: str) -> None:
        with self._lock:
            if self.state == new_state:
                return
            old_state = self.state
            self.state = new_state
            cbs = list(self._state_callbacks)

        logger.debug(f"VoiceService: State o'zgardi: {old_state} -> {new_state}")
        for cb in cbs:
            try:
                cb(new_state)
            except Exception as e:
                logger.debug(f"State callback xatosi: {e}")

    def _emit_transcript(self, text: str, sender: str = "user") -> None:
        with self._lock:
            cbs = list(self._transcript_callbacks)
        for cb in cbs:
            try:
                cb(text, sender)
            except Exception:
                pass

    def _emit_response(self, text: str) -> None:
        with self._lock:
            cbs = list(self._response_callbacks)
        for cb in cbs:
            try:
                cb(text)
            except Exception:
                pass

    def _emit_level(self, level: float) -> None:
        with self._lock:
            cbs = list(self._level_callbacks)
        for cb in cbs:
            try:
                cb(level)
            except Exception:
                pass

    def start(self) -> bool:
        """Ovozli xizmatni ishga tushirish (orqa fonda mikrofonni ochadi)"""
        with self._lock:
            if self._is_running:
                return True
            self._is_running = True

        # Wake detector callback bog'lash
        self.wake_detector.on_wake_detected = self._on_wake_detected

        self._stream_thread = threading.Thread(
            target=self._audio_capture_loop,
            daemon=True,
            name="MisaVoiceCaptureLoop"
        )
        self._stream_thread.start()
        logger.info("[VOICE] ConversationalVoiceService started")
        logger.info("[VOICE] WakeWordDetector started")
        self._set_state(VoiceServiceState.IDLE)
        return True

    def stop(self) -> None:
        """Ovozli xizmatni to'xtatish"""
        with self._lock:
            self._is_running = False
        self.voice_manager.interrupt()
        self._set_state(VoiceServiceState.IDLE)
        logger.info("ConversationalVoiceService: To'xtatildi")

    def handle_interruption(self) -> None:
        """Foydalanuvchi "To'xta" deganida chaqiriladi (Barge-in)"""
        logger.info("Barge-in: 'To'xta' komandasi qabul qilindi. Ijro darhol to'xtatildi.")
        self.voice_manager.interrupt()
        self._set_state(VoiceServiceState.INTERRUPTED)
        # 0.5s dan so'ng yana tinglashga o'tish
        time.sleep(0.3)
        self._set_state(VoiceServiceState.LISTENING)

    def set_microphone(self, device_id: str, device_name: Optional[str] = None) -> Dict[str, Any]:
        """Mikrofonni tanlash va agar oqim ishlayotgan bo'lsa uni yangi qurilmada qayta ishga tushirish"""
        res = self.mic_manager.set_selected_device(device_id, device_name)
        with self._lock:
            self._reconnect_stream_event.set()
            if self._is_running:
                logger.info("[VOICE] Mikrofon sozlamasi o'zgardi -> Oqim yangi qurilmaga o'tkazilmoqda...")
        return res

    def _audio_capture_loop(self) -> None:
        """
        Doimiy mikrofon oqimini o'qish va holatlar mashinasi (State Machine).
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("[VOICE] sounddevice o'rnatilmagan, ovozli xizmat ishlamaydi")
            self._set_state(VoiceServiceState.ERROR)
            return

        chunk_size = int(self.sample_rate * 0.1)  # 100ms = 1600 samples

        while self._is_running:
            self._reconnect_stream_event.clear()

            # Audio kirish qurilmasini aniqlash va diagnostika ma'lumotlarini chop etish
            dev_idx, dev_info, fallback_used, status_msg = self.mic_manager.resolve_selected_device()
            if dev_idx is None or dev_idx < 0:
                logger.error("[VOICE] Xatolik: Hech qanday audio kirish qurilmasi (mikrofon) topilmadi!")
                self._set_state(VoiceServiceState.ERROR)
                time.sleep(2.0)
                continue

            dev_name = dev_info.get("name", "Noma'lum mikrofon")
            if fallback_used:
                logger.warning(f"[VOICE] OGOHLANTIRISH: {status_msg}")
            else:
                logger.info(f"[VOICE] Tanlangan mikrofon: {dev_name} (Index: {dev_idx})")

            logger.info(f"[VOICE] Input device: {dev_name}")
            logger.info(f"[VOICE] Input device index: {dev_idx}")
            logger.info(f"[VOICE] Sample rate: {self.sample_rate}")
            logger.info(f"[VOICE] Channels: 1")
            logger.info(f"[VOICE] Block size: {chunk_size}")
            logger.info(f"[VOICE] Stream active: True")
            logger.info("[VOICE] Microphone stream started")

            # Apparat moslashuvi: to'g'ridan-to'g'ri 16000Hz yoki native samplerate bilan ochish
            native_sr = int(dev_info.get("sample_rate", 44100))
            use_resampling = False
            stream_sr = self.sample_rate
            stream_chunk = chunk_size

            # Test ochish: agar 16000Hz to'g'ridan-to'g'ri ishlamasa, native samplerate ishlatiladi
            try:
                test_stream = sd.InputStream(
                    device=dev_idx,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_size
                )
                test_stream.close()
            except Exception as sr_err:
                logger.info(f"[VOICE] 16000Hz to'g'ridan-to'g'ri ochilmadi ({sr_err}), native {native_sr}Hz ishlatilmoqda")
                use_resampling = True
                stream_sr = native_sr
                stream_chunk = int(native_sr * 0.1)

            try:
                with sd.InputStream(
                    device=dev_idx,
                    samplerate=stream_sr,
                    channels=1,
                    dtype="float32",
                    blocksize=stream_chunk
                ) as stream:
                    # Uskunaning dastlabki DC/click shovqinini tashlab yuborish (warmup)
                    try:
                        stream.read(stream_chunk)
                        stream.read(stream_chunk)
                    except Exception:
                        pass

                    while self._is_running and not self._reconnect_stream_event.is_set():
                        chunk, overflowed = stream.read(stream_chunk)
                        if chunk is None or len(chunk) == 0:
                            continue

                        raw_chunk = np.asarray(chunk, dtype=np.float32).flatten()
                        if use_resampling and len(raw_chunk) > 0:
                            indices = np.linspace(0, len(raw_chunk) - 1, chunk_size)
                            flat_chunk = np.interp(indices, np.arange(len(raw_chunk)), raw_chunk).astype(np.float32)
                        else:
                            flat_chunk = raw_chunk

                        rms = float(np.sqrt(np.mean(flat_chunk**2)))
                        self._emit_level(min(1.0, rms * 15.0))

                        # ==============================================================
                        # 1-HOLAT: SPEAKING / ACKNOWLEDGING (Misa gapirmoqda)
                        # ==============================================================
                        if self.state == VoiceServiceState.ACKNOWLEDGING:
                            # Qisqa "Ha, eshitaman." tasdig'i vaqtida barge-in o'chiriladi (o'zini o'zi to'xtatmasligi uchun)
                            continue

                        if self.voice_manager.is_speaking():
                            # Misa to'liq gapirayotganda barge-in tekshiriladi (yuqori bo'sag'a bilan)
                            if self.barge_in.check_audio_interruption(flat_chunk, threshold=0.075):
                                self.handle_interruption()
                            continue

                        # Agar hozirgina gapirib bo'lingan bo'lsa -> Follow-up ga o'tish
                        if self.session.is_in_follow_up_window():
                            if self.state not in (VoiceServiceState.LISTENING, VoiceServiceState.THINKING):
                                self._listening_deadline = time.time() + self.session.follow_up_window
                                self._set_state(VoiceServiceState.LISTENING)

                        # ==============================================================
                        # 2-HOLAT: IDLE (Kutish rejimi — Faqat lokal "Misa" qidiriladi)
                        # ==============================================================
                        if self.state == VoiceServiceState.IDLE:
                            self.wake_detector.update_ambient_noise(rms)
                            if self.wake_detector.process_frame(flat_chunk):
                                self._on_wake_detected()
                            continue

                        # ==============================================================
                        # 3-HOLAT: LISTENING (Foydalanuvchi buyrug'ini tinglash oynasi)
                        # ==============================================================
                        if self.state == VoiceServiceState.LISTENING:
                            vad_event, full_audio = self.vad.process_chunk(flat_chunk)

                            # Agar foydalanuvchi gapirayotgan bo'lsa
                            if self.vad.is_speaking:
                                if vad_event == "speech_end" and full_audio is not None:
                                    self._process_user_utterance(full_audio)
                                continue

                            # Jimlik davom etmoqda — muddat (deadline) tekshiriladi
                            now = time.time()
                            deadline = getattr(self, "_listening_deadline", 0.0)
                            is_follow_up = self.session.is_in_follow_up_window()

                            # Tinglash oynasi to'liq tugaganda (kamida 6-7 soniya) IDLE ga qaytish
                            if now > deadline and not is_follow_up:
                                logger.info("[VOICE] Tinglash darchasi tugadi (jimlik) -> IDLE holatiga qaytilmoqda")
                                self._set_state(VoiceServiceState.IDLE)
                                self.session.close_follow_up()
                                self.wake_detector.reset()
                                self.wake_detector._last_wake_time = time.time() + 0.5
                                continue

                            continue

            except Exception as e:
                logger.error(f"[VOICE] Mikrofon oqimida uzilish yoki xatolik: {e}. 1.5s dan so'ng qayta ulanadi...")
                time.sleep(1.5)

    def _on_wake_detected(self, event_data: Optional[Dict[str, Any]] = None) -> None:
        """'Salom Misa' kalit so'zi aniqlanganda darhol bajariladigan jarayon"""
        detected_phrase = (event_data or {}).get("phrase", getattr(self.wake_detector, "phrase", "Salom Misa"))
        engine_name = (event_data or {}).get("engine", self.wake_detector.get_active_engine_name())
        score = (event_data or {}).get("score", getattr(self.wake_detector, "last_wake_score", 1.0))

        logger.info(f"[VOICE] WAKE DETECTED: '{detected_phrase}' via {engine_name} (score={score:.2f})")
        logger.info("[VOICE] ACK START")
        self._set_state(VoiceServiceState.WAKE_DETECTED)
        self.session.on_wake_word_activated()

        # Wake callback tinglovchilariga (WebSocket / frontend) hodisani yuborish
        wake_payload = {
            "phrase": detected_phrase,
            "engine": engine_name,
            "score": float(score),
            "timestamp": time.time()
        }
        with self._lock:
            w_cbs = list(self._wake_callbacks)
        for cb in w_cbs:
            try:
                cb(wake_payload)
            except Exception as e:
                logger.debug(f"Wake callback xatosi: {e}")

        self._set_state(VoiceServiceState.ACKNOWLEDGING)
        self.wake_detector.reset()

        # Tezkor lokal javob ("Ha, eshitaman.")
        ack_phrase = "Ha, eshitaman."
        self._emit_response(ack_phrase)
        self._emit_transcript(detected_phrase, sender="user")

        def _on_ack_start():
            logger.info("[VOICE] ACK PLAYING")

        def _after_ack(interrupted: bool):
            logger.info(f"[VOICE] ACK COMPLETE (interrupted={interrupted})")
            if not interrupted and self._is_running:
                # Karnay ovozi mikrofon buferida qolmasligi uchun tozalash va 1.2s cooldown
                self.wake_detector.reset()
                self.wake_detector._last_wake_time = time.time() + 1.2
                self.vad.reset()
                # Foydalanuvchi gapirishi uchun 7 soniyalik to'liq darcha ochamiz
                self._listening_deadline = time.time() + 7.0
                self._set_state(VoiceServiceState.LISTENING)

        logger.info("[VOICE] ACK TTS CREATED")
        logger.info("[VOICE] ACK QUEUED")
        self.voice_manager.speak(
            ack_phrase,
            voice_id=self.voice_id,
            on_start=_on_ack_start,
            on_complete=_after_ack
        )

    def _process_user_utterance(self, audio_data: np.ndarray) -> None:
        """VAD orqali to'liq yozib olingan audio matnga aylantiriladi va AI ga uzatiladi"""
        self._set_state(VoiceServiceState.THINKING)
        logger.info("STT: Olingan nutq transkripsiyasi boshlanmoqda...")

        # 1. Transkripsiya (Google STT -> Mahalliy fallback)
        transcript = self.stt_manager.transcribe(audio_data, sample_rate=self.sample_rate, language="uz-UZ")
        if not transcript:
            logger.info("STT: Nutq tushunarsiz yoki bo'sh")
            # Agar follow-up rejimida bo'lsa, xotirjamlik bilan idle ga o'tamiz
            self.session.close_follow_up()
            self._set_state(VoiceServiceState.IDLE)
            return

        clean_text = transcript.strip()
        self._emit_transcript(clean_text, sender="user")
        logger.info(f"Foydalanuvchi buyrug'i: '{clean_text}'")

        # 2. "To'xta" komandasi ekanligini tezkor tekshirish
        if self.barge_in.is_stop_command(clean_text):
            self.handle_interruption()
            return

        # 3. Agar foydalanuvchi "Misa, bugun havo qanday?" degan bo'lsa, "Misa" qismini olib tashlash
        clean_text = re.sub(
            r"^(?:(?:salom|hey|ey|hoy)\s+)?(?:misa|mikasa|миса|микаса)(?:\s+(?:eshit|qara|ayt))?(?:[,\s:!.]*|$)",
            "",
            clean_text,
            flags=re.IGNORECASE
        ).strip()
        if not clean_text:
            clean_text = "ha"

        # 4. Xavfsizlik tekshiruvi (Destructive Command Gate)
        is_dangerous, action_desc, confirm_prompt = self.security.check_for_destructive_intent(clean_text)
        if is_dangerous and confirm_prompt:
            self._handle_dangerous_confirmation_request(action_desc, confirm_prompt, clean_text)
            return

        if self.security.has_pending_action():
            executed, msg, _ = self.security.evaluate_confirmation(clean_text)
            self._speak_and_listen_follow_up(msg)
            return

        # 5. Buyruqni Misa Intelligence tizimiga yuborish
        self._dispatch_to_misa_intelligence(clean_text)

    def _handle_dangerous_confirmation_request(self, desc: str, prompt: str, raw_text: str) -> None:
        """Xavfli buyruq uchun tasdiq so'rash"""
        def _dummy_execute():
            logger.info(f"Xavfli amal tasdiqlangan holda bajarilishi rejalashtirildi: {desc}")

        self.security.stage_pending_action(desc, _dummy_execute)
        self._speak_and_listen_follow_up(prompt)

    def _dispatch_to_misa_intelligence(self, user_query: str) -> None:
        """
        Buyruqni mavjud CommandDispatcher yoki ReAct Agent / AI tizimiga yo'naltirish.
        Multi-turn kontekst bilan boyitadi.
        """
        response_text = ""

        # 1-qadam: Tezkor deterministik mahalliy buyruqlar (CommandDispatcher)
        try:
            from core.command_dispatcher import get_command_dispatcher
            disp = get_command_dispatcher()
            handled, local_resp = disp.dispatch_local(user_query)
            if handled and local_resp:
                response_text = local_resp
        except Exception as e:
            logger.debug(f"CommandDispatcher tekshirishida ogohlantirish: {e}")

        # 2-qadam: Agar mahalliy buyruq bo'lmasa -> Yagona Unified Command Pipeline (execute_command_pipeline / ai_savol_yuborish)
        if not response_text:
            try:
                from core.api_server import execute_command_pipeline, get_current_user_name, get_current_voice_type
                user_name = get_current_user_name()
                voice_type = self.voice_id or get_current_voice_type()
                response_text = execute_command_pipeline(user_query, user=user_name, ovoz=voice_type, mode="ask")
            except Exception as e:
                logger.error(f"Unified pipeline orqali javob olishda xatolik: {e}")
                try:
                    from core.ai_engine import ai_savol_yuborish
                    res = ai_savol_yuborish(user_query)
                    if isinstance(res, dict):
                        response_text = res.get("response") or res.get("javob") or str(res)
                    elif res:
                        response_text = str(res)
                except Exception as e2:
                    logger.error(f"ai_savol_yuborish xatosi: {e2}")

        if not response_text:
            response_text = "Tushundim, buyruq qabul qilindi."

        # Javobni xotiraga yozish (kelgusi 'ertaga-chi?' kabi follow-up savollar uchun)
        self.session.record_turn(user_query, response_text)
        self._emit_response(response_text)
        self._emit_transcript(response_text, sender="misa")

        # 3-qadam: Javobni ovoz chiqarib o'qish va Follow-up oynasini ochish
        self._speak_and_listen_follow_up(response_text)

    def _speak_and_listen_follow_up(self, text_to_speak: str) -> None:
        """
        Javobni TTS orqali yangratish va yakunlangach 7 soniyalik Follow-up oynasini ochish.
        """
        self._set_state(VoiceServiceState.SPEAKING)

        def _on_speech_finished(interrupted: bool):
            # Karnay ovozi mikrofon buferida qolmasligi uchun tozalash va 1.2s cooldown
            self.wake_detector.reset()
            self.wake_detector._last_wake_time = time.time() + 1.2
            self.vad.reset()

            if interrupted:
                self._set_state(VoiceServiceState.INTERRUPTED)
                time.sleep(0.2)
                self._listening_deadline = time.time() + 6.0
                self._set_state(VoiceServiceState.LISTENING)
            else:
                # Nutq tugadi -> Follow-up oynasi ochiladi!
                self.session.on_assistant_finished_speaking()
                self._listening_deadline = time.time() + self.session.follow_up_window
                self._set_state(VoiceServiceState.LISTENING)

        self.voice_manager.speak(
            text_to_speak,
            voice_id=self.voice_id,
            on_complete=_on_speech_finished
        )


# Global yagona nusxa
_conversational_service_instance: Optional[ConversationalVoiceService] = None


def get_conversational_voice_service() -> ConversationalVoiceService:
    global _conversational_service_instance
    if _conversational_service_instance is None:
        _conversational_service_instance = ConversationalVoiceService()
    return _conversational_service_instance
