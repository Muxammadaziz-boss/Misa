import ctypes
import time
import os

fn = os.path.abspath("test_uz-UZ-MadinaNeural.mp3")
winmm = ctypes.windll.winmm
alias = "test_status"
r_open = winmm.mciSendStringW(f'open "{fn}" type mpegvideo alias {alias}', None, 0, 0)
print("open:", r_open)
winmm.mciSendStringW(f'play {alias}', None, 0, 0)
status_buf = ctypes.create_unicode_buffer(64)
for i in range(10):
    winmm.mciSendStringW(f'status {alias} mode', status_buf, 64, 0)
    print(f"step {i}: status = '{status_buf.value}'")
    time.sleep(0.04)

winmm.mciSendStringW(f'close {alias}', None, 0, 0)
