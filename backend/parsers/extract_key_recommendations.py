from pathlib import Path
import re
pat = re.compile(r'^(\d{1,3}\.\d+[a-z]?)\s+(.*)', re.IGNORECASE)
num_pat = re.compile(r'^Recommendation', re.IGNORECASE)
for p in sorted(Path('.').glob('*.txt')):
    if p.name.startswith('extract_'): continue
    print(f'FILE: {p.name}')
    lines = p.read_text(encoding='utf-8').splitlines()
    for line in lines:
        if num_pat.match(line):
            print(line)
        elif pat.match(line):
            print(line)
    print('\n' + '='*80 + '\n')
