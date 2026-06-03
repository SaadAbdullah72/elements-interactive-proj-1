from pathlib import Path
import re

pattern = re.compile(r'(?:^|\n)(.*Recommendation.*)', re.IGNORECASE)
for p in sorted(Path('.').glob('*.txt')):
    if p.name.startswith('extract_'): continue
    print(f'FILE: {p.name}')
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if 'recommendation' in line.lower():
            start = max(0, i-2)
            end = min(len(lines), i+3)
            print('---')
            print('\n'.join(lines[start:end]))
    print('\n' + '='*80 + '\n')
