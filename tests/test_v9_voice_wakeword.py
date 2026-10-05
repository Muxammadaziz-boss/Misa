# ========== test_v9_voice_wakeword.py ==========
# Test suite for Misa AI v9.0.1 Voice, Wake-word ("Misa ..."), and System Status features

import pytest
from core.command_dispatcher import CommandDispatcher


def test_misa_wake_word_calling_only():
    dispatcher = CommandDispatcher()
    
    # User calls Misa by name only
    success, reply = dispatcher.dispatch_local("Misa")
    assert success is True
    assert "Labbay" in reply
    assert "tinglayapman" in reply

    success, reply = dispatcher.dispatch_local("Salom Misa")
    assert success is True
    assert "Labbay" in reply

    success, reply = dispatcher.dispatch_local("Hey Misa")
    assert success is True
    assert "Labbay" in reply

    success, reply = dispatcher.dispatch_local("Ey Misa")
    assert success is True
    assert "Labbay" in reply


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


def test_misa_wake_word_custom_user():
    dispatcher = CommandDispatcher()
    success, reply = dispatcher.dispatch_local("Misa", user_name="Azizbek")
    assert success is True
    assert "Azizbek" in reply
