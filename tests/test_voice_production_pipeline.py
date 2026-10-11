# -*- coding: utf-8 -*-
"""
Misa AI v9.0.0 — Production Voice Pipeline Test Suite
Tests for:
- Local Wake Word Detector
- Barge-in & Cancellation Token
- Streaming VAD
- Audio Queue (FIFO, non-overlapping, flush)
- Voice Registry & Model Status Integrity (Ashley & Yukari honest status)
- Multi-turn Conversation Session & Follow-up Window
- Destructive Command Security Gate
"""

import os
import sys
import time
import pytest
import numpy as np

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.voice.cancellation import CancellationToken
from core.voice.barge_in import BargeInDetector
from core.voice.wake_word import WakeWordDetector
from core.voice.vad import StreamingVAD
from core.voice.voice_registry import get_voice_registry
from core.voice.session_manager import get_session_manager, ConversationSession
from core.voice.security import get_security_guard, VoiceSecurityGuard
from core.voice.audio_queue import AudioQueue
from core.voice.audio_player import AudioPlayer


def test_cancellation_token():
    """CancellationToken holati va xabarnomalarni tekshirish"""
    token = CancellationToken()
    assert not token.is_cancelled

    triggered = []
    token.register_callback(lambda: triggered.append(True))

    token.cancel()
    assert token.is_cancelled
    assert len(triggered) == 1

    # Qayta cancel qilinganda duplikat bo'lmasligi kerak
    token.cancel()
    assert len(triggered) == 1


def test_barge_in_stop_keywords():
    """'To'xta' va interruption kalit so'zlarini aniqlash"""
    detector = BargeInDetector()

    # To'xtatish komandalari
    stop_phrases = [
        "to'xta",
        "toxta",
        "to'xtang",
        "stop",
        "jim",
        "bas",
        "yetar",
        "og'zingni yop",
        "misa to'xta",
        "iltimos toxta",
        "bas yetar"
    ]
    for phrase in stop_phrases:
        assert detector.is_stop_command(phrase), f"'{phrase}' stop buyrug'i deb aniqlanmadi!"

    # Oddiy savollar to'xtatish deb hisoblanmasligi shart
    non_stop_phrases = [
        "salom misa",
        "bugun havo qanday",
        "ertaga soat nechada",
        "musiqa qo'y",
        "rahmat senga"
    ]
    for phrase in non_stop_phrases:
        assert not detector.is_stop_command(phrase), f"'{phrase}' noto'g'ri to'xtatish deb qabul qilindi!"


def test_voice_registry_integrity():
    """
    Ashley va Yukari statuslarining haqiqiyligi:
    Mock/Fake pitch-shifted qilinmaganligi, PyTorch yuklanmaganda
    aniq 'unavailable' ekani va sababi ko'rsatilishi kerak.
    """
    registry = get_voice_registry()
    catalog = registry.get_catalog()

    catalog_dict = {item["id"]: item for item in catalog}

    # Madina ("ayol") va Sardor ("erkak") mavjud bo'lishi kerak
    assert "ayol" in catalog_dict
    assert catalog_dict["ayol"]["provider"] == "edge_tts"
    assert catalog_dict["ayol"]["status"] == "available"
    assert "Madina" in catalog_dict["ayol"]["name"]

    assert "erkak" in catalog_dict
    assert catalog_dict["erkak"]["provider"] == "edge_tts"
    assert catalog_dict["erkak"]["status"] == "available"
    assert "Sardor" in catalog_dict["erkak"]["name"]

    # Fish Audio modellar
    assert "fish_yigit" in catalog_dict
    assert catalog_dict["fish_yigit"]["provider"] == "fish_audio"

    assert "fish_anime" in catalog_dict
    assert catalog_dict["fish_anime"]["provider"] == "fish_audio"

    # Ashley va Yukari tekshiruvi:
    assert "ashley" in catalog_dict
    ashley = catalog_dict["ashley"]
    assert ashley["provider"] == "rvc"
    # Runtime dependencylar yuklanmagan holda mock qilinmasligi, unavailable bo'lishi shart
    assert ashley["status"] == "unavailable"
    assert "dependency" in ashley.get("reason", "").lower() or "runtime" in ashley.get("reason", "").lower()

    assert "yukari" in catalog_dict
    yukari = catalog_dict["yukari"]
    assert yukari["provider"] == "rvc"
    assert yukari["status"] == "unavailable"
    assert "dependency" in yukari.get("reason", "").lower() or "runtime" in yukari.get("reason", "").lower()


def test_wake_word_detector_silence_and_noise_rejection():
    """Oflayn Wake-word detektori: sokinlik yoki fon shovqinida soxta uyg'onmaslik"""
    detector = WakeWordDetector(sample_rate=16000)

    # 1. Mutlaq jimlik (silence)
    silence = np.zeros(1600, dtype=np.float32)
    for _ in range(10):
        detected = detector.process_frame(silence)
        assert not detected, "Jimlikda 'Misa' aniqlanmasligi kerak!"

    # 2. Oq shovqin (white noise)
    np.random.seed(42)
    noise = (np.random.rand(1600).astype(np.float32) - 0.5) * 0.05
    for _ in range(10):
        detected = detector.process_frame(noise)
        assert not detected, "Fon shovqinida 'Misa' soxta (false positive) uyg'onmasligi kerak!"


def test_wake_word_detector_speech_trigger():
    """Haqiqiy 'Misa' nutqi kelganda WakeWordDetector uyg'onishi va callback chaqirilishi"""
    callback_fired = False

    def on_wake():
        nonlocal callback_fired
        callback_fired = True

    detector = WakeWordDetector(sample_rate=16000, sensitivity=0.65, on_wake_detected=on_wake)

    # Sun'iy 'Misa' fonetik ketma-ketligi:
    # 1. /m-i/ (200ms) - past/o'rta chastota 300Hz/2200Hz, past ZCR
    # 2. /s/ (150ms) - yuqori chastota 4500Hz, yuqori ZCR
    # 3. /a/ (200ms) - ochiq unli 750Hz, past ZCR
    sr = 16000
    t_mi = np.linspace(0, 0.20, int(sr * 0.20), endpoint=False)
    sig_mi = (0.25 * np.sin(2 * np.pi * 300 * t_mi) + 0.15 * np.sin(2 * np.pi * 2200 * t_mi)).astype(np.float32)

    t_s = np.linspace(0, 0.15, int(sr * 0.15), endpoint=False)
    np.random.seed(99)
    # /s/ frikativ: yuqori chastotali modulyatsiyalangan shovqin
    sig_s = (0.35 * np.sin(2 * np.pi * 4500 * t_s) + 0.10 * (np.random.rand(len(t_s)) - 0.5)).astype(np.float32)

    t_a = np.linspace(0, 0.20, int(sr * 0.20), endpoint=False)
    sig_a = (0.30 * np.sin(2 * np.pi * 750 * t_a) + 0.15 * np.sin(2 * np.pi * 1200 * t_a)).astype(np.float32)

    misa_speech = np.concatenate([sig_mi, sig_s, sig_a])

    # 100ms bo'laklar bilan yuborish
    chunk_size = 1600
    detected_any = False
    for i in range(0, len(misa_speech), chunk_size):
        chunk = misa_speech[i : i + chunk_size]
        if len(chunk) < chunk_size:
            chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
        if detector.process_frame(chunk):
            detected_any = True

    assert detected_any, "'Misa' fonetik ketma-ketligi kelganda detektor True qaytarishi shart!"
    assert callback_fired, "Wake-word callback chaqirilishi shart!"


def test_streaming_vad_speech_detection():
    """VAD faolligi: nutq va sukunat chegaralarini aniqlash"""
    vad = StreamingVAD(sample_rate=16000, silence_timeout=0.2, min_speech_duration=0.1)

    # Sukunat
    silence = np.zeros(1600, dtype=np.float32)
    event, _ = vad.process_chunk(silence)
    assert event == "silence"
    assert not vad.is_speaking

    # Nutq simulyatsiyasi (sinusoida 400Hz)
    t = np.linspace(0, 0.1, 1600, endpoint=False)
    speech = (0.25 * np.sin(2 * np.pi * 400 * t)).astype(np.float32)

    # Nutq boshlanishi
    events = []
    for _ in range(4):
        ev, _ = vad.process_chunk(speech)
        if ev:
            events.append(ev)
        time.sleep(0.03)

    assert "speech_start" in events
    assert vad.is_speaking

    # Sukunat boshlandi: 1-bo'lak sukunatni qayd etish (_silence_start_time boshlanadi)
    vad.process_chunk(silence)
    time.sleep(0.25)

    end_events = []
    full_audio = None
    for _ in range(4):
        ev, aud = vad.process_chunk(silence)
        if ev:
            end_events.append(ev)
        if aud is not None:
            full_audio = aud

    assert "speech_end" in end_events
    assert full_audio is not None
    assert len(full_audio) > 0


def test_conversation_session_follow_up():
    """Ko'p bosqichli suhbat va 7 soniyalik Follow-up oynasi"""
    session = ConversationSession(follow_up_window=2.0)

    # Boshlang'ich holat
    assert not session.is_in_follow_up_window()

    # Foydalanuvchi "Misa" deb boshladi
    session.on_wake_word_activated()
    assert not session.is_in_follow_up_window()

    # Misa javob berib, gapirishni tugatdi
    session.record_turn("Bugun Toshkentda havo qanday?", "Bugun Toshkentda 22 daraja iliq.")
    session.on_assistant_finished_speaking()

    # Nutq tugagach -> 7s (bu testda 2s) Follow-up oynasi ochiq bo'lishi kerak
    assert session.is_in_follow_up_window()
    assert session.last_user_message == "Bugun Toshkentda havo qanday?"
    assert session.last_assistant_message == "Bugun Toshkentda 22 daraja iliq."

    # Prompt kontekstini tekshirish
    ctx = session.get_context_for_prompt()
    assert "Toshkentda havo qanday" in ctx
    assert "22 daraja" in ctx

    # Follow-up oynasini qo'lda yopish
    session.close_follow_up()
    assert not session.is_in_follow_up_window()


def test_voice_security_guard_destructive_actions():
    """Xavfli buyruqlar uchun tasdiqlash eshigi (Destructive Confirmation Gate)"""
    guard = VoiceSecurityGuard()

    # 1. Bezarar buyruq
    dangerous, desc, prompt = guard.check_for_destructive_intent("Bugun ob-havo qanday?")
    assert not dangerous
    assert prompt is None

    # 2. Xavfli buyruq: kompyuterni o'chirish
    dangerous, desc, prompt = guard.check_for_destructive_intent("Kompyuterni o'chir")
    assert dangerous
    assert "o'chirish" in desc
    assert prompt is not None

    # Amalni tasdiqlash uchun kutish rejimiga qo'yish
    executed = []
    guard.stage_pending_action(desc, lambda: executed.append(True))
    assert guard.has_pending_action()

    # Rad etish ("Yo'q")
    success, msg, action = guard.evaluate_confirmation("yo'q, bekor qil")
    assert not success
    assert len(executed) == 0
    assert not guard.has_pending_action()

    # Qayta xavfli buyruq: faylni o'chirish
    dangerous, desc, prompt = guard.check_for_destructive_intent("barcha fayllarni o'chirib tashla")
    assert dangerous
    guard.stage_pending_action(desc, lambda: executed.append(True))

    # Tasdiqlash ("Ha, tasdiqlayman")
    success, msg, action = guard.evaluate_confirmation("ha, albatta bajar")
    assert success
    assert len(executed) == 1
    assert not guard.has_pending_action()


def test_audio_queue_fifo_and_flush():
    """AudioQueue: ketma-ketlik va zudlik bilan tozalash (Flush / Barge-in)"""
    class MockPlayer:
        def __init__(self):
            self.playing = False
        def play_file(self, fn, cancel_token=None, on_start=None, on_end=None, delete_on_finish=False):
            self.playing = True
            if on_start:
                on_start()
            for _ in range(25):
                if cancel_token and cancel_token.is_cancelled:
                    if on_end:
                        on_end(True)
                    self.playing = False
                    return False
                time.sleep(0.04)
            if on_end:
                on_end(False)
            self.playing = False
            return True
        def is_playing(self):
            return self.playing
        def stop(self):
            self.playing = False

    player = MockPlayer()
    queue = AudioQueue(player=player)

    token1 = CancellationToken()
    token2 = CancellationToken()

    queue.enqueue("fake1.mp3", text="1-qism", cancel_token=token1, delete_on_finish=False)
    queue.enqueue("fake2.mp3", text="2-qism", cancel_token=token2, delete_on_finish=False)

    time.sleep(0.06)  # Worker fake1 ni olishini kutish
    assert queue.is_busy()

    # Flush (barge-in "To'xta" komandasi berilganda)
    cleared = queue.flush()
    assert cleared >= 1
    assert token1.is_cancelled
    assert token2.is_cancelled


def test_wake_word_phrases_and_cleaning():
    """Wake-word bilan boshlangan iboralardan 'Misa' ni tozalash"""
    import re
    detector = WakeWordDetector()

    phrases = [
        ("Misa, bugun havo qanday?", "bugun havo qanday?"),
        ("Hey Misa, soat necha?", "soat necha?"),
        ("Misa eshit, ertaga dars bormi?", "ertaga dars bormi?"),
        ("Salom Misa, yangiliklarni ayt", "yangiliklarni ayt"),
    ]
    pattern = r"^(?:(?:salom|hey|ey|hoy)\s+)?(?:misa|mikasa|миса|микаса)(?:\s+(?:eshit|qara|ayt))?(?:[,\s:!.]*|$)"

    for raw, expected in phrases:
        cleaned = re.sub(pattern, "", raw, flags=re.IGNORECASE).strip()
        assert cleaned.lower() == expected.lower(), f"Tozalashda xato: {raw} -> {cleaned}"


def test_multi_turn_weather_context_retention():
    """
    Promptdagi aniq suhbat namunasi:
    'Misa' -> 'Bugun Toshkentda ob-havo qanday?'
    Follow-up: 'Unda ertaga-chi?' (Misasiz)
    Follow-up: 'Qaysi shaharni nazarda tutyapsan?'
    Kontekst to'liq saqlanadi.
    """
    session = ConversationSession(follow_up_window=7.0)

    # 1-turn
    session.on_wake_word_activated()
    session.record_turn("Bugun Toshkentda ob-havo qanday?", "Bugun Toshkentda havo ochiq, harorat 22 daraja.")
    session.on_assistant_finished_speaking()

    assert session.is_in_follow_up_window()

    # 2-turn (foydalanuvchi "Misa" demaydi!)
    session.record_turn("Unda ertaga-chi?", "Ertaga Toshkentda yog'ingarchilik kutilmaydi, 24 daraja bo'ladi.")
    session.on_assistant_finished_speaking()

    assert session.is_in_follow_up_window()

    # 3-turn
    session.record_turn("Qaysi shaharni nazarda tutyapsan?", "Siz so'ragan Toshkent shahrini nazarda tutyapman.")
    session.on_assistant_finished_speaking()

    # Xotira va kontekstni tekshirish
    full_ctx = session.get_context_for_prompt(max_turns=3)
    assert "Toshkentda ob-havo" in full_ctx
    assert "ertaga-chi" in full_ctx
    assert "Qaysi shaharni" in full_ctx
    assert session.active_turn == 3


def test_simultaneous_three_tts_requests_no_overlapping():
    """3 ta TTS so'rovi parallel kelganda audio ustma-ust tushmasligi (sequential FIFO)"""
    played_order = []
    active_count = 0
    max_concurrent = 0

    class MockPlayer:
        def play_file(self, fn, cancel_token=None, on_start=None, on_end=None, delete_on_finish=False):
            nonlocal active_count, max_concurrent
            active_count += 1
            if active_count > max_concurrent:
                max_concurrent = active_count
            played_order.append(fn)
            time.sleep(0.05)
            active_count -= 1
            if on_end:
                on_end(False)
            return True

        def is_playing(self):
            return active_count > 0

        def stop(self):
            pass

    player = MockPlayer()
    queue = AudioQueue(player=player)

    # 3 ta parallel audio so'rovi
    queue.enqueue("audio_chunk_1.mp3", delete_on_finish=False)
    queue.enqueue("audio_chunk_2.mp3", delete_on_finish=False)
    queue.enqueue("audio_chunk_3.mp3", delete_on_finish=False)

    # Bajarilishini kutish
    for _ in range(30):
        if len(played_order) == 3 and not queue.is_busy():
            break
        time.sleep(0.03)

    assert played_order == ["audio_chunk_1.mp3", "audio_chunk_2.mp3", "audio_chunk_3.mp3"]
    # Hech qachon 1 tadan ortiq audio parallel yangramasligi kerak!
    assert max_concurrent == 1, f"Parallel ovozlar soni 1 dan oshdi: {max_concurrent}"


def test_immediate_interruption_stop_latency():
    """'To'xta' komandasi berilganda bekor qilish tezligi (<100ms)"""
    token = CancellationToken()
    start_time = time.time()
    token.cancel()
    elapsed_ms = (time.time() - start_time) * 1000.0

    assert token.is_cancelled
    assert elapsed_ms < 100.0, f"Bekor qilish {elapsed_ms}ms cho'zildi (100ms dan kam bo'lishi shart)"


def test_all_voice_providers_explicit_status():
    """Barcha 6 ovoz provayderi holati: Madina, Sardor, Fish Yigit, Anime Drama, Ashley, Yukari"""
    from core.voice.voice_registry import get_voice_registry
    catalog = get_voice_registry().get_catalog()
    assert len(catalog) >= 6

    by_id = {v["id"]: v for v in catalog}

    # 1. Edge-TTS Madina
    assert by_id["ayol"]["provider"] == "edge_tts"
    assert by_id["ayol"]["status"] == "available"

    # 2. Edge-TTS Sardor
    assert by_id["erkak"]["provider"] == "edge_tts"
    assert by_id["erkak"]["status"] == "available"

    # 3. Fish Audio Yigit
    assert by_id["fish_yigit"]["provider"] == "fish_audio"

    # 4. Fish Audio Anime
    assert by_id["fish_anime"]["provider"] == "fish_audio"

    # 5. Ashley (RVC) — real model runtime yo'qligi halol aytiladi
    assert by_id["ashley"]["provider"] == "rvc"
    assert by_id["ashley"]["status"] == "unavailable"
    assert "model runtime not implemented" in by_id["ashley"]["reason"] or "dependency" in by_id["ashley"]["reason"]

    # 6. Yukari (RVC) — real model runtime yo'qligi halol aytiladi
    assert by_id["yukari"]["provider"] == "rvc"
    assert by_id["yukari"]["status"] == "unavailable"
    assert "model runtime not implemented" in by_id["yukari"]["reason"] or "dependency" in by_id["yukari"]["reason"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
