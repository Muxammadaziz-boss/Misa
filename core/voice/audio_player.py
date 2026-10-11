# -*- coding: utf-8 -*-
"""
Misa AI — Interruptible Audio Player
Kutilmagan to'xtatish (Barge-in / "To'xta") imkoniyatiga ega xavfsiz audio ijrochi.
Windows MCI bloklanishlarini chetlab o'tib, Pygame va Sounddevice orqali real-vaqtda boshqariladi.
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
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._is_playing = False
        self._current_cancel_token: Optional[CancellationToken] = None
        self._active_file: Optional[str] = None
        self._playback_start_cb: Optional[Callable[[str], None]] = None
        self._playback_end_cb: Optional[Callable[[str, bool], None]] = None
        self._pygame_initialized = False

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
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass

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

            # 1. Pygame Mixer orqali ijro (Eng tez va to'xtatish oson usul)
            if self._ensure_pygame_mixer():
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
                    logger.warning(f"Pygame ijrosida xato: {ex_pg}, fallbackga o'tilmoqda")
                    interrupted = True

            # 2. Sounddevice / Soundfile fallback (agar Pygame ishlamasa)
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
