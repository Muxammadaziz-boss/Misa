import os
import re

page_dir = r"d:\Ishchi stoli\Misa\yordamchi_9.0.0\Misa\src\pages"
issues = []

for f in os.listdir(page_dir):
    if f.endswith('.tsx'):
        p = os.path.join(page_dir, f)
        with open(p, encoding='utf-8', errors='ignore') as fp:
            content = fp.read()
            lines = content.splitlines()

            # 1. Check for scroll container: if container has height 100% or flex: 1, does it have overflow-y: auto?
            has_overflow_y = 'overflowY' in content or 'overflow-y' in content or 'overflow: "auto"' in content or 'overflow: "scroll"' in content
            if not has_overflow_y:
                issues.append((f, "Katta ehtimol bilan vertikal skroll (overflow-y: auto) yo'q: sahifa kontenti kichik oynada kesilib qolishi mumkin."))

            # 2. Check for fixed width elements > 950px
            for idx, line in enumerate(lines, 1):
                match = re.search(r'width:\s*["\'](\d+)px["\']', line)
                if match:
                    px = int(match.group(1))
                    if px >= 950:
                        issues.append((f, f"L{idx}: Qat'iy katta pikselli kenglik (width: '{px}px') mavjud. 1024px o'lchamda gorizontal siqilish yoki overflow xatosi bo'lishi mumkin."))

                # 3. Check for minWidth > 800px
                match_min = re.search(r'minWidth:\s*["\'](\d+)px["\']', line)
                if match_min:
                    px_min = int(match_min.group(1))
                    if px_min >= 800:
                        issues.append((f, f"L{idx}: Katta minWidth (minWidth: '{px_min}px') mavjud. Kichik ekranda gorizontal scroll chiqaradi."))

                # 4. Check for console.log left in production pages
                if 'console.log(' in line and not line.strip().startswith('//'):
                    issues.append((f, f"L{idx}: Ishlab chiqarish (prod) kodida ortiqcha debug log: {line.strip()[:60]}"))

                # 5. Check for hardcoded colors that break theme switching
                if '#000000' in line or '#ffffff' in line or '#fff' in line:
                    if 'background' in line.lower() and 'rgba' not in line:
                        issues.append((f, f"L{idx}: Qat'iy oq/qora background rangi tema o'zgarganda buzilishi mumkin: {line.strip()[:60]}"))

print(f"Sahifalar bo'yicha topilgan UI/UX muammolari ({len(issues)} ta):")
for f, msg in issues:
    print(f"[{f}] {msg}")
