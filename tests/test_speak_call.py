import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def test_speak_call_importable():
    from core.api_server import speak_out_loud
    assert callable(speak_out_loud)


def run_manual_speak():
    from core.api_server import speak_out_loud
    print("Testing speak_out_loud...")
    res = speak_out_loud("Salom, bu Madina ovozi sinovi.")
    print("speak_out_loud returned:", res)
    time.sleep(4)
    print("Done sleep")


if __name__ == "__main__":
    run_manual_speak()
