import ast
import os
import re

def audit_backend():
    print("=== BACKEND KODINI CHUQUR TAHLIL QILISH ===")
    core_dir = "core"
    
    blocking_calls = []
    naked_json = []
    command_injections = []
    
    for root, _, files in os.walk(core_dir):
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(root, f)
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    lines = content.splitlines()

                # Check 1: requests.* inside async def
                # Find all async def functions and check if requests.* or time.sleep appears inside them
                try:
                    tree = ast.parse(content, filename=p)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.AsyncFunctionDef):
                            for subnode in ast.walk(node):
                                # Check for requests.get / post
                                if isinstance(subnode, ast.Call):
                                    func_name = ""
                                    if isinstance(subnode.func, ast.Attribute):
                                        if isinstance(subnode.func.value, ast.Name):
                                            func_name = f"{subnode.func.value.id}.{subnode.func.attr}"
                                    if func_name in ("requests.get", "requests.post", "requests.put", "requests.delete", "time.sleep"):
                                        blocking_calls.append((p, subnode.lineno, node.name, func_name))
                except Exception as e:
                    pass

                # Check 2: os.system or subprocess.Popen(..., shell=True) with unsanitized user input
                for idx, line in enumerate(lines, 1):
                    if "os.system(" in line and not line.strip().startswith("#"):
                        command_injections.append((p, idx, line.strip()))
                    if "subprocess.Popen" in line and "shell=True" in line and not line.strip().startswith("#"):
                        command_injections.append((p, idx, line.strip()))

    print(f"\n1. Async funksiyalarda bloklovchi (sinxron) chaqiruvlar ({len(blocking_calls)} ta):")
    for p, lineno, fn, call in blocking_calls:
        print(f"  [{p}:{lineno}] '{fn}' ichida '{call}' chaqirilgan (aiohttp event loopini muzlatadi)")

    print(f"\n2. Xavfli shell buyruqlari (os.system / shell=True) ({len(command_injections)} ta):")
    for p, lineno, line in command_injections[:20]:
        print(f"  [{p}:{lineno}] {line[:80]}")

if __name__ == '__main__':
    audit_backend()
