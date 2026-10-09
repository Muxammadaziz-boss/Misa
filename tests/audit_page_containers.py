import os
import re

print(f"{'Page':<25} | {'overflowY':<10} | {'Root Container Style'}")
print("-" * 80)

for f in sorted(os.listdir('Misa/src/pages')):
    if f.endswith('.tsx'):
        p = os.path.join('Misa/src/pages', f)
        with open(p, 'r', encoding='utf-8') as fp:
            c = fp.read()
        
        has_overflow_y = 'overflowY' in c or 'overflow-y' in c
        # find return ( <div ...
        m = re.search(r'return\s*\(\s*<div([^>]*)>', c)
        root_attrs = m.group(1).replace('\n', ' ')[:60] if m else "No root div"
        print(f"{f:<25} | {str(has_overflow_y):<10} | {root_attrs}")
