import os
import re

page_dir = r"d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src"
findings = []

for root, dirs, files in os.walk(page_dir):
    for f in files:
        if f.endswith(('.tsx', '.ts')):
            p = os.path.join(root, f)
            with open(p, encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
                rel = os.path.relpath(p, page_dir)
                
                # Check 1: localhost hardcoded without config
                for m in re.finditer(r'http://(?:localhost|127\.0\.0\.1):(\d+)', content):
                    port = m.group(1)
                    if port not in ('18420', '1420'):
                        findings.append((rel, f"Hardcoded URL: {m.group(0)}"))
                        
                # Check 2: target=_blank without noopener
                if 'target="_blank"' in content or "target='_blank'" in content:
                    if 'noopener' not in content:
                        findings.append((rel, "Xavfsiz bo'lmagan link: target=_blank mavjud lekin rel=noopener yo'q"))
                    
                # Check 3: any img without alt
                for m in re.finditer(r'<img\s+([^>]*?)>', content):
                    tag = m.group(0)
                    if 'alt=' not in tag:
                        findings.append((rel, f"Rasmda alt atributi yo'q: {tag[:60]}"))

                # Check 4: Mikasa branding residue in user-facing text
                # We check for 'Mikasa' in JSX text (excluding technical imports or legacy fallbacks)
                for line_idx, line in enumerate(content.splitlines(), 1):
                    if 'Mikasa' in line and not any(k in line for k in ['mikasa_user', 'mikasa.exe', 'mikasa-7', 'mikasa_backend', 'legacy', 'mikasa-app-shell', 'mikasa-glass-topnav', 'mikasa-topnav-center']):
                        findings.append((rel, f"L{line_idx}: Mikasa eski brend nomi qolib ketgan: {line.strip()[:70]}"))

print(f"Jami tekshiruvlar: {len(findings)} ta topildi")
for f, issue in findings:
    print(f"[{f}] {issue}")
