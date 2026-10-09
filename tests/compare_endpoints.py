import re

with open('core/api_server.py', 'r', encoding='utf-8') as f:
    server = f.read()

with open('Misa/src/services/backendService.ts', 'r', encoding='utf-8') as f:
    client = f.read()

client_endpoints = sorted(set(re.findall(r'/api/[a-zA-Z0-9_\-/]+', client)))
# In server, find router additions: add_get, add_post, add_route, etc.
server_routes = set(re.findall(r'router\.add_[a-z]+\(\s*[\'"](/api/[^\'"]+)[\'"]', server))
# Also regex for any string literal starting with /api/
all_server_apis = set(re.findall(r'[\'"](/api/[a-zA-Z0-9_\-/{}\.]+)[\'"]', server))

print(f"Client endpoints count: {len(client_endpoints)}")
print(f"Server registered router paths: {len(server_routes)}")
print(f"All server /api/ literals: {len(all_server_apis)}")

missing_routes = []
for ce in client_endpoints:
    ce_clean = ce.rstrip('/')
    found = False
    for sr in all_server_apis:
        sr_clean = sr.rstrip('/')
        # Check pattern match if sr has {param}
        if '{' in sr:
            base = sr.split('{')[0].rstrip('/')
            if ce_clean.startswith(base):
                found = True
                break
        else:
            if ce_clean == sr_clean:
                found = True
                break
    if not found:
        missing_routes.append(ce)

print(f"\nMissing endpoints on backend: {len(missing_routes)}")
for m in missing_routes:
    print(f"  [MISSING] {m}")
