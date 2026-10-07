import os, sys, time
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.api_server import speak_out_loud

print("Testing speak_out_loud...")
res = speak_out_loud("Salom, bu Madina ovozi sinovi.")
print("speak_out_loud returned:", res)
time.sleep(4)
print("Done sleep")
