# ========== test_v9_voice_wakeword.py ==========
# Test suite for Misa AI v9.0.1 Voice, Wake-word ("Misa ..."), and System Status features

import pytest
from core.command_dispatcher import CommandDispatcher


def test_misa_wake_word_calling_only():
    dispatcher = CommandDispatcher()
    
    # User calls Misa or Mikasa
    for wake in ["Misa", "misa", "Mikasa", "mikasa", "Salom Misa", "Salom Mikasa", "Hey Mikasa", "микаса", "миса"]:
        success, reply = dispatcher.dispatch_local(wake)
        assert success is True, f"Failed for {wake}"
        assert "Labbay" in reply, f"No Labbay for {wake}"
        assert "tinglayapman" in reply, f"No tinglayapman for {wake}"


def test_misa_wake_word_with_local_command():
    dispatcher = CommandDispatcher()

    # User addresses Misa and asks for time
    success, reply = dispatcher.dispatch_local("Misa soat nechi")
    assert success is True
    assert "Hozirgi vaqt" in reply

    success, reply = dispatcher.dispatch_local("Misa vaqt nechi")
    assert success is True
    assert "Hozirgi vaqt" in reply

    success, reply = dispatcher.dispatch_local("Misa bugun qaysi kun")
    assert success is True
    assert "Bugun" in reply
    assert "yil" in reply


def test_device_telegram_check():
    dispatcher = CommandDispatcher()
    success, reply = dispatcher.dispatch_local("bu qurilmada telegram bormi?", user_name="Ustoz")
    assert success is True
    assert "Telegram" in reply or "telegram" in reply.lower()
    assert ("o'rnatilgan" in reply or "mavjud" in reply or "AyuGram" in reply)


def test_misa_wake_word_custom_user():
    dispatcher = CommandDispatcher()
    success, reply = dispatcher.dispatch_local("Misa", user_name="Azizbek")
    assert success is True
    assert "Azizbek" in reply
