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
        self._lock = threading.Lock()
        self._stream_thread: Optional[threading.Thread] = None
        self._state_callbacks: List[Callable[[str], None]] = []
        self._transcript_callbacks: List[Callable[[str, str], None]] = []
        self._response_callbacks: List[Callable[[str], None]] = []
        self._level_callbacks: List[Callable[[float], None]] = []

        # Interruption va playback nazorati
        self._active_cancel_token: Optional[CancellationToken] = None
        self.barge_in.on_interrupted = self.handle_interruption

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

        self._stream_thread = threading.Thread(
            target=self._audio_capture_loop,
            daemon=True,
            name="MisaVoiceCaptureLoop"
        )
        self._stream_thread.start()
        logger.info("ConversationalVoiceService: Ishga tushirildi (Mahalliy 'Misa' kutish rejimi)")
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

    def _audio_capture_loop(self) -> None:
        """
        Doimiy mikrofon oqimini o'qish va holatlar mashinasi (State Machine).
        """
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice o'rnatilmagan, ovozli xizmat ishlamaydi")
            self._set_state(VoiceServiceState.ERROR)
            return

        chunk_size = int(self.sample_rate * 0.1)  # 100ms = 1600 samples

        while self._is_running:
            try:
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    blocksize=chunk_size
                ) as stream:
                    logger.info("PortAudio kirish oqimi muvaffaqiyatli ochildi")

                    while self._is_running:
                        chunk, overflowed = stream.read(chunk_size)
                        if chunk is None or len(chunk) == 0:
                            continue

                        flat_chunk = chunk.flatten().astype(np.float32)
                        rms = float(np.sqrt(np.mean(flat_chunk**2)))
                        self._emit_level(min(1.0, rms * 15.0))

                        # ==============================================================
                        # 1-HOLAT: SPEAKING (Misa gapirmoqda, lekin mikrofon ochiq!)
                        # ==============================================================
                        if self.voice_manager.is_speaking():
                            # Barge-in: gapirish vaqtida "To'xta" aytilganini tekshirish
                            if self.barge_in.check_audio_interruption(flat_chunk, threshold=0.040):
                                # Agar ovoz to'xtatish komandasi bo'lsa
                                self.handle_interruption()
                            continue

                        # Agar hozirgina gapirib bo'lingan bo'lsa -> Follow-up ga o'tish
                        if self.session.is_in_follow_up_window():
                            if self.state not in (VoiceServiceState.LISTENING, VoiceServiceState.THINKING):
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
                        # 3-HOLAT: LISTENING (Foydalanuvchi buyrug'ini qabul qilish)
                        # ==============================================================
                        if self.state == VoiceServiceState.LISTENING:
                            vad_event, full_audio = self.vad.process_chunk(flat_chunk)

                            # Agar follow-up oynasi tugagan bo'lsa va foydalanuvchi gapirmagan bo'lsa
                            if not self.vad.is_speaking and not self.session.is_in_follow_up_window():
                                if self.state == VoiceServiceState.LISTENING and not self.session.last_user_message:
                                    # Standart IDLE ga qaytish
                                    self._set_state(VoiceServiceState.IDLE)
                                    continue

                            if vad_event == "speech_end" and full_audio is not None:
                                self._process_user_utterance(full_audio)
                            continue

            except Exception as e:
                logger.error(f"Mikrofon oqimida uzilish yoki xatolik: {e}. 1.5s dan so'ng qayta ulanadi...")
                time.sleep(1.5)

    def _on_wake_detected(self) -> None:
        """'Misa' kalit so'zi aniqlanganda darhol bajariladigan jarayon"""
        self._set_state(VoiceServiceState.WAKE_DETECTED)
        self.session.on_wake_word_activated()
        logger.info("WakeWord hodisasi: Foydalanuvchi 'Misa' deb chaqirdi")

        self._set_state(VoiceServiceState.ACKNOWLEDGING)

        # Tezkor lokal javob ("Ha, eshitaman.")
        ack_phrase = "Ha, eshitaman."
        self._emit_response(ack_phrase)
        self._emit_transcript("Misa", sender="user")

        def _after_ack(interrupted: bool):
            if not interrupted and self._is_running:
                self.vad.reset()
                self._set_state(VoiceServiceState.LISTENING)

        self.voice_manager.speak(
            ack_phrase,
            voice_id=self.voice_id,
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

        # 2-qadam: Agar mahalliy buyruq bo'lmasa -> ReAct Agent / Misa AI orqali hal qilish
        if not response_text:
            try:
                import main
                if hasattr(main, "agent_pipeline_run"):
                    response_text = main.agent_pipeline_run(user_query)
                elif hasattr(main, "ai_savol_berish"):
                    response_text = main.ai_savol_berish(user_query)
            except Exception as e:
                logger.error(f"Misa AI orqali javob olishda xatolik: {e}")
                response_text = "Kechirasiz, so'rovingizni qayta ishlashda xatolik yuz berdi."

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
            if interrupted:
                self._set_state(VoiceServiceState.INTERRUPTED)
                time.sleep(0.2)
                self._set_state(VoiceServiceState.LISTENING)
            else:
                # Nutq tugadi -> Follow-up oynasi ochiladi!
                self.session.on_assistant_finished_speaking()
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
