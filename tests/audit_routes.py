import re
import os

def run_audit():
    # 1. Backend routes in core/api_server.py
    with open('core/api_server.py', 'r', encoding='utf-8', errors='ignore') as f:
        server_content = f.read()

    raw_backend = re.findall(r'[\'"](/api/[a-zA-Z0-9_\-/{}\.]+)', server_content)
    backend_routes = set(raw_backend)

    # 2. Frontend routes in Misa/src/services/backendService.ts and all src
    frontend_routes = set()
    for root, _, files in os.walk('Misa/src'):
        for file in files:
            if file.endswith(('.ts', '.tsx')):
                p = os.path.join(root, file)
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    matches = re.findall(r'(?:API_BASE|\bapiBase|\bbaseUrl)?[\'"`](/api/[a-zA-Z0-9_\-/${}\.]+)', content)
                    for m in matches:
                        clean = m.split('?')[0].split('${')[0]
                        frontend_routes.add(clean)

    print(f"Backendda aniqlangan API yo'llari: {len(backend_routes)}")
    print(f"Frontendda chaqirilayotgan API yo'llari: {len(frontend_routes)}")

    unmatched = []
    for fr in sorted(frontend_routes):
        fr_norm = fr.rstrip('/')
        found = False
        for br in backend_routes:
            br_norm = br.rstrip('/')
            br_pattern = '^' + re.sub(r'\{[a-zA-Z0-9_]+\}', '[^/]+', re.escape(br_norm)).replace(r'\\{', '{').replace(r'\\}', '}') + '.*$'
            if fr_norm == br_norm or re.match(br_pattern, fr_norm) or br_norm.startswith(fr_norm):
                found = True
                break
        if not found:
            unmatched.append(fr)

    print("\n[FRONTEND VA BACKEND ROUTE MOSLIGI TAHLILI]")
    if unmatched:
        print(f"Backendda aniq belgilanmagan ({len(unmatched)}) ta frontend so'rovlari:")
        for u in unmatched:
            print(f"  - {u}")
    else:
        print("Barcha frontend API chaqiruvlari backend routerida mavjud!")

if __name__ == '__main__':
    run_audit()
