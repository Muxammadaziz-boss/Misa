import os
import re
import ast
import json

def run_deep_security_audit():
    findings = []
    root_dir = "."

    # 1. Check for unsafe pickle/yaml/eval/exec
    for root, _, files in os.walk(root_dir):
        if any(ignored in root for ignored in (".git", ".venv", "node_modules", "dist", "build", "__pycache__")):
            continue
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(root, f)
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    lines = content.splitlines()

                # pickle.loads
                for idx, line in enumerate(lines, 1):
                    if "pickle.loads" in line or "pickle.load" in line:
                        findings.append(("CRITICAL", p, idx, "Insecure pickle deserialization", line.strip()))
                    if "yaml.load(" in line and "SafeLoader" not in line and "yaml.safe_load" not in line:
                        findings.append(("HIGH", p, idx, "Insecure yaml.load without SafeLoader", line.strip()))
                    if re.search(r'\beval\s*\(', line) and "_safe_eval" not in line and "SAFE_OPS" not in line:
                        findings.append(("CRITICAL", p, idx, "Potential unsafe eval() call", line.strip()))
                    if re.search(r'\bexec\s*\(', line) and "sandbox" not in p:
                        findings.append(("CRITICAL", p, idx, "Potential unsafe exec() call", line.strip()))

    # 2. Check CORS configuration in core/api_server.py
    with open("core/api_server.py", "r", encoding="utf-8") as f:
        api_server = f.read()

    cors_matches = re.findall(r'cors|Access-Control-[A-Za-z0-9_-]+', api_server, re.IGNORECASE)
    print(f"CORS references found in api_server.py: {len(cors_matches)}")

    # 3. Check WebSocket connection management in core/api_server.py
    ws_matches = re.findall(r'async def handle_ws\(', api_server)
    print(f"handle_ws found: {len(ws_matches)}")

    # 4. Check for secret exposure in logs or responses
    for match in re.finditer(r'(logger\.(?:info|debug|warning|error)\([^)]*(?:password|token|secret|api_key)[^)]*\))', api_server, re.IGNORECASE):
        # check if it prints the actual token variable
        matched_str = match.group(1)
        if any(v in matched_str for v in ("{token}", "{api_key}", "{key}", "{password}")):
            findings.append(("HIGH", "core/api_server.py", 0, "Potential secret logging", matched_str[:80]))

    print(f"\n--- AUDIT FINDINGS ({len(findings)}) ---")
    for sev, path, line, title, detail in findings:
        print(f"[{sev}] {path}:{line} - {title}\n    {detail}")

if __name__ == '__main__':
    run_deep_security_audit()
