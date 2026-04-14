"""Find where quotes break AFTER L2026"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('_temp_check.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

sq = dq = tpl = 0
for i, line in enumerate(lines):
    j = 0
    while j < len(line):
        c = line[j]
        nc = line[j+1] if j+1 < len(line) else ''
        if c == '\\' and nc: 
            j += 2; continue
        if c == "'" and not dq and not tpl: sq ^= 1
        elif c == '"' and not sq and not tpl: dq ^= 1
        elif c == '`' and not sq and not dq: tpl ^= 1
        j += 1
    
    if i >= 2025:
        print(f'L{i+1}: sq={sq} dq={dq} tpl={tpl} | {line.strip()[:120]}')
