"""Precise quote balance checker - find the EXACT line where balance breaks"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('_temp_check.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track state per line
sq = 0  # single quote depth
dq = 0  # double quote depth
tpl = 0 # template literal depth
last_good = 0

for i, line in enumerate(lines):
    j = 0
    in_sq = sq > 0
    in_dq = dq > 0
    in_tpl = tpl > 0
    
    while j < len(line):
        c = line[j]
        nc = line[j+1] if j+1 < len(line) else ''
        
        # Skip escaped chars
        if c == '\\' and nc:
            j += 2
            continue
        
        if c == "'" and not in_dq and not in_tpl:
            in_sq = not in_sq
        elif c == '"' and not in_sq and not in_tpl:
            in_dq = not in_dq
        elif c == '`' and not in_sq and not in_dq:
            in_tpl = not in_tpl
        
        j += 1
    
    # Check balance at end of this line
    open_count = (1 if in_sq else 0) + (1 if in_dq else 0) + (1 if in_tpl else 0)
    
    if open_count == 0 and i > 2590 and i < 2830:
        print(f'L{i+1}: ALL CLOSED (good)')
    elif open_count > 0 and i >= 2590 and i < 2830:
        print(f'L{i+1}: OPEN! sq={in_sq} dq={in_dq} tpl={in_tpl} | {line.strip()[:100]}')
    
    sq = 1 if in_sq else 0
    dq = 1 if in_dq else 0
    tpl = 1 if in_tpl else 0
    
    if sq == 0 and dq == 0 and tpl == 0:
        last_good = i + 1

print(f'\nLast fully-closed line before end: L{last_good}')
if sq or dq or tpl:
    print(f'UNCLOSED at EOF: sq={sq} dq={dq} tpl={tpl}')
