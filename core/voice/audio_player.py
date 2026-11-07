# -*- coding: utf-8 -*-
"""
Misa AI — Interruptible Audio Player
Kutilmagan to'xtatish (Barge-in / "To'xta") imkoniyatiga ega xavfsiz audio ijrochi.
Windows MCI (winmm), Pygame mixer va Sounddevice orqali apparat darajasida boshqariladi.
"""

import os
import time
import logging
import threading
from typing import Optional, Callable
from .cancellation import CancellationToken

logger = logging.getLogger("AudioPlayer")


class AudioPlayer:
    """
    Tezkor to'xtatiluvchi audio ijro moduli.
    Ijro jarayonida CancellationToken holatini har 25ms da tekshiradi.
    Windows MCI (winmm), Pygame mixer va Sounddevice orqali apparat darajasida boshqariladi.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._is_playing = False
        self._current_cancel_token: Optional[CancellationToken] = None
        self._active_file: Optional[str] = None
        self._playback_start_cb: Optional[Callable[[str], None]] = None
        self._playback_end_cb: Optional[Callable[[str, bool], None]] = None
        self._pygame_initialized = False
        self._active_winmm_alias: Optional[str] = None

    def _ensure_pygame_mixer(self) -> bool:
        """Pygame mixer drayverini initsializatsiya qilish"""
        if self._pygame_initialized:
            return True
        try:
            import pygame
            if not pygame.mixer.get_init():
                # 44100Hz, stereo, 1024 bufer
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self._pygame_initialized = True
            return True
        except Exception as e:
            logger.warning(f"Pygame mixer initsializatsiyasida ogohlantirish: {e}")
            return False

    def is_playing(self) -> bool:
        """Hozir audio ijro etilyaptimi?"""
        with self._lock:
            return self._is_playing

    def stop(self) -> None:
        """Hozirgi ijroni zudlik bilan to'xtatish"""
        with self._lock:
            if self._current_cancel_token:
                self._current_cancel_token.cancel()
        self._force_stop_hardware()

    def _force_stop_hardware(self) -> None:
        """Apparat drayverlarida ijroni to'xtatish"""
        # 1. Windows MCI ijrosini to'xtatish
        with self._lock:
            alias = self._active_winmm_alias
        if alias and os.name == "nt":
            try:
                import ctypes
                ctypes.windll.winmm.mciSendStringW(f'stop {alias}', None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, 0)
            except Exception:
                pass

        # 2. Pygame mixer ijrosini to'xtatish
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass

    def _play_with_winmm(
        self,
        file_path: str,
        cancel_token: Optional[CancellationToken] = None
    ) -> tuple:
        """
        Windows native MCI (winmm) orqali ultra-barqaror ijro.
        DirectSound / Pygame / Sounddevice bilan ziddiyatga bormaydi.
        Qaytaradi: (handled: bool, completed_normally: bool)
        """
        if os.name != "nt":
            return False, False
        try:
            import ctypes
            import uuid
            winmm = ctypes.windll.winmm
            alias = f"misa_{uuid.uuid4().hex[:8]}"
            with self._lock:
                self._active_winmm_alias = alias

            ret = winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias {alias}', None, 0, 0)
            if ret != 0:
                ret = winmm.mciSendStringW(f'open "{file_path}" alias {alias}', None, 0, 0)
            if ret != 0:
                with self._lock:
                    self._active_winmm_alias = None
                return False, False

            winmm.mciSendStringW(f'set {alias} time format milliseconds', None, 0, 0)
            buf = ctypes.create_unicode_buffer(128)
            winmm.mciSendStringW(f'status {alias} length', buf, 128, 0)
            length_ms = int(buf.value) if buf.value.isdigit() else 2500

            winmm.mciSendStringW(f'play {alias}', None, 0, 0)
            start_t = time.time()
            interrupted = False

            while True:
                if cancel_token and cancel_token.is_cancelled:
                    winmm.mciSendStringW(f'stop {alias}', None, 0, 0)
                    interrupted = True
                    break
                winmm.mciSendStringW(f'status {alias} mode', buf, 128, 0)
                mode_str = buf.value.lower()
                if mode_str in ("stopped", "") or (time.time() - start_t) * 1000 > (length_ms + 300):
                    break
                time.sleep(0.025)

            winmm.mciSendStringW(f'close {alias}', None, 0, 0)
            with self._lock:
                self._active_winmm_alias = None
            return True, not interrupted
        except Exception as ex_mci:
            logger.debug(f"WinMM MCI ijrosida xato: {ex_mci}")
            with self._lock:
                self._active_winmm_alias = None
            return False, False

    def play_file(
        self,
        file_path: str,
        cancel_token: Optional[CancellationToken] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_end: Optional[Callable[[bool], None]] = None,
        delete_on_finish: bool = True
    ) -> bool:
        """
        Audio faylni sinxron (ammo tez to'xtatiluvchi) tarzda ijro etish.
        cancel_token.is_cancelled bo'lsa, <50ms ichida to'xtaydi.
        Qaytaradi: True agar to'liq eshitilgan bo'lsa, False agar to'xtatilgan yoki xato bo'lsa.
        """
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"Ijro uchun fayl mavjud emas: {file_path}")
            return False

        if cancel_token and cancel_token.is_cancelled:
            if delete_on_finish and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            return False

        with self._lock:
            self._is_playing = True
            self._current_cancel_token = cancel_token
            self._active_file = file_path

        interrupted = False
        completed_normally = False

        try:
            if on_start:
                try:
                    on_start()
                except Exception as e:
                    logger.debug(f"on_start callback xatosi: {e}")

            # 1. Windows MCI orqali apparat darajasida xavfsiz va toza ijro
            handled, ok = self._play_with_winmm(file_path, cancel_token=cancel_token)
            if handled:
                completed_normally = ok
                interrupted = not ok

            # 2. Pygame Mixer orqali ijro (agar MCI ishlamasa yoki Windows bo'lmasa)
            if not completed_normally and not interrupted and self._ensure_pygame_mixer():
                try:
                    import pygame
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()

                    while pygame.mixer.music.get_busy():
                        if cancel_token and cancel_token.is_cancelled:
                            logger.info("AudioPlayer: 'To'xta' signali olindi, ijro to'xtatilmoqda")
                            pygame.mixer.music.stop()
                            interrupted = True
                            break
                        time.sleep(0.025)  # 25ms tekshiruv qadami (past kechikish)

                    pygame.mixer.music.unload()
                    completed_normally = not interrupted
                except Exception as ex_pg:
                    logger.warning(f"Pygame ijrosida xato: {ex_pg}, Sounddevice fallbackga o'tilmoqda")
                    interrupted = False

            # 3. Sounddevice / Soundfile fallback (agar oldingilar ishlamasa)
            if not completed_normally and not interrupted and os.path.exists(file_path):
                try:
                    import soundfile as sf
                    import sounddevice as sd
                    data, fs = sf.read(file_path, dtype='float32')
                    stream = sd.OutputStream(samplerate=fs, channels=data.shape[1] if data.ndim > 1 else 1)
                    with stream:
                        chunk_size = int(fs * 0.05)  # 50ms
                        idx = 0
                        while idx < len(data):
                            if cancel_token and cancel_token.is_cancelled:
                                interrupted = True
                                break
                            chunk = data[idx:idx + chunk_size]
                            stream.write(chunk)
                            idx += chunk_size
                    completed_normally = not interrupted
                except Exception as ex_sd:
                    logger.debug(f"Sounddevice fallback xatosi: {ex_sd}")

        finally:
            with self._lock:
                self._is_playing = False
                self._current_cancel_token = None
                self._active_file = None

            if on_end:
                try:
                    on_end(interrupted)
                except Exception as e:
                    logger.debug(f"on_end callback xatosi: {e}")

            if delete_on_finish and os.path.exists(file_path):
                try:
                    # Faylni ushlab qolmaslik uchun biroz kutish
                    time.sleep(0.02)
                    os.remove(file_path)
                except Exception:
                    pass

        return completed_normally
