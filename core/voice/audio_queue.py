# -*- coding: utf-8 -*-
"""
Misa AI — Central Audio Output Queue
Yagona markaziy audio navbati.
Bir vaqtning o'zida bir nechta ovoz baravar yangrab ketishining oldini oladi (1 active playback).
"To'xta" aytilganda navbatni tozalash va joriy ijroni to'xtatish (flush) imkoniyatini beradi.
"""

import os
import queue
import logging
import threading
from typing import Optional, Callable, Dict, Any
from .cancellation import CancellationToken
from .audio_player import AudioPlayer

logger = logging.getLogger("AudioQueue")


class AudioQueueItem:
    def __init__(
        self,
        file_path: str,
        text: str = "",
        cancel_token: Optional[CancellationToken] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_complete: Optional[Callable[[bool], None]] = None,
        delete_on_finish: bool = True
    ):
        self.file_path = file_path
        self.text = text
        self.cancel_token = cancel_token or CancellationToken()
        self.on_start = on_start
        self.on_complete = on_complete
        self.delete_on_finish = delete_on_finish


class AudioQueue:
    """
    Markazlashtirilgan ketma-ket audio navbati va boshqaruvchisi.
    """

    def __init__(self, player: Optional[AudioPlayer] = None):
        self.player = player or AudioPlayer()
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = True
        self._lock = threading.Lock()
        self._active_item: Optional[AudioQueueItem] = None
        self._state_change_cb: Optional[Callable[[str], None]] = None

        self._start_worker()

    def set_state_callback(self, cb: Callable[[str], None]) -> None:
        """Holat o'zgarganda xabar berish (speaking / idle / interrupted)"""
        self._state_change_cb = cb

    def _notify_state(self, state: str) -> None:
        if self._state_change_cb:
            try:
                self._state_change_cb(state)
            except Exception as e:
                logger.debug(f"State callback xatosi: {e}")

    def _start_worker(self) -> None:
        self._worker_thread = threading.Thread(
            target=self._queue_worker_loop,
            daemon=True,
            name="AudioQueueWorker"
        )
        self._worker_thread.start()

    def _queue_worker_loop(self) -> None:
        """Navbatdagi audio fayllarni ketma-ket tinglash oqimi"""
        while self._running:
            try:
                item: AudioQueueItem = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            with self._lock:
                self._active_item = item

            # Agar navbatda turganida bekor qilingan bo'lsa
            if item.cancel_token.is_cancelled:
                if item.delete_on_finish and os.path.exists(item.file_path):
                    try:
                        os.remove(item.file_path)
                    except Exception:
                        pass
                self._queue.task_done()
                with self._lock:
                    self._active_item = None
                continue

            self._notify_state("speaking")

            def _handle_start():
                if item.on_start:
                    item.on_start()

            def _handle_end(interrupted: bool):
                if item.on_complete:
                    item.on_complete(interrupted)
                if interrupted:
                    self._notify_state("interrupted")
                else:
                    # Agar navbat bo'sh bo'lsa idle ga o'tamiz
                    if self._queue.empty():
                        self._notify_state("idle")

            try:
                self.player.play_file(
                    item.file_path,
                    cancel_token=item.cancel_token,
                    on_start=_handle_start,
                    on_end=_handle_end,
                    delete_on_finish=item.delete_on_finish
                )
            except Exception as e:
                logger.error(f"AudioQueue ijroda kutilmagan xato: {e}")
            finally:
                with self._lock:
                    self._active_item = None
                self._queue.task_done()

                if self._queue.empty() and not self.player.is_playing():
                    self._notify_state("idle")

    def enqueue(
        self,
        file_path: str,
        text: str = "",
        cancel_token: Optional[CancellationToken] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_complete: Optional[Callable[[bool], None]] = None,
        delete_on_finish: bool = True
    ) -> AudioQueueItem:
        """Audio faylni navbatga qo'shish"""
        item = AudioQueueItem(
            file_path=file_path,
            text=text,
            cancel_token=cancel_token,
            on_start=on_start,
            on_complete=on_complete,
            delete_on_finish=delete_on_finish
        )
        self._queue.put(item)
        return item

    def flush(self) -> int:
        """
        Barcha navbatdagi elementlarni tozalash va joriy ijroni darhol to'xtatish ("To'xta").
        Qaytaradi: Tozalangan vazifalar soni.
        """
        cleared_count = 0

        # 1. Joriy aktiv ijroni to'xtatish
        with self._lock:
            if self._active_item:
                self._active_item.cancel_token.cancel()
        self.player.stop()

        # 2. Navbatda turgan qolgan barcha vazifalarni chiqarib bekor qilish
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                item.cancel_token.cancel()
                if item.delete_on_finish and os.path.exists(item.file_path):
                    try:
                        os.remove(item.file_path)
                    except Exception:
                        pass
                self._queue.task_done()
                cleared_count += 1
            except queue.Empty:
                break

        self._notify_state("idle")
        logger.info(f"AudioQueue flush: {cleared_count} ta navbatdagi audio tozalandi va ijro to'xtatildi")
        return cleared_count

    def is_busy(self) -> bool:
        """Navbatda ish bormi yoki audio yangrayaptimi?"""
        return not self._queue.empty() or self.player.is_playing()

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    def size(self) -> int:
        """Hozirgi navbat hajmi (navbatdagi + ijrodagi)"""
        return self._queue.qsize() + (1 if self._active_item or self.player.is_playing() else 0)
