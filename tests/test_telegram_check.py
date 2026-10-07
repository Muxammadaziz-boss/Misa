import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

print("Testing ai_savol_yuborish('bu qurilmada telegram bormi?')...")
try:
    from core.ai_engine import ai_savol_yuborish
    resp = ai_savol_yuborish("bu qurilmada telegram bormi?", "Ustoz")
    print("\nResult type:", type(resp))
    import json
    print("Result:", json.dumps(resp, ensure_ascii=True, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
