import os
import ctypes
import time

fn = os.path.abspath("test_uz-UZ-MadinaNeural.mp3")
print(f"Testing playback for: {fn}, exists: {os.path.exists(fn)}")

# Test 1: winmm mciSendStringW
winmm = ctypes.windll.winmm
alias = "test_madina"
res_open = winmm.mciSendStringW(f'open "{fn}" type mpegvideo alias {alias}', None, 0, 0)
print("mci open result:", res_open)
if res_open == 0:
    res_play = winmm.mciSendStringW(f"play {alias} wait", None, 0, 0)
    print("mci play result:", res_play)
    winmm.mciSendStringW(f"close {alias}", None, 0, 0)
else:
    err_buf = ctypes.create_unicode_buffer(256)
    winmm.mciGetErrorStringW(res_open, err_buf, 256)
    print(f"mci error message: {err_buf.value}")

# Test 2: pygame
try:
    import pygame
    pygame.mixer.init()
    print("pygame.mixer initialized successfully")
    pygame.mixer.music.load(fn)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    pygame.mixer.music.unload()
    print("pygame playback completed")
except Exception as e:
    print(f"pygame error: {e}")
