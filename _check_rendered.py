"""Check JS in rendered HTML"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('_rendered.html', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
if not scripts:
    print('No script tags found!')
    # Maybe it's inline
    idx = content.find('<script')
    if idx >= 0:
        print(f'Found <script at pos {idx}')
        print(content[idx:idx+200])
    else:
        print('No script at all!')
else:
    js = scripts[0]
    lines = js.split('\n')
    print(f'JS: {len(lines)} lines, {len(js)} chars')
    
    sq = dq = tpl = 0
    for i, line in enumerate(lines):
        j = 0
        while j < len(line):
            c = line[j]
            nc = line[j+1] if j+1 < len(line) else ''
            if c == '\\' and nc: j += 2; continue
            if c == "'" and not dq and not tpl: sq ^= 1
            elif c == '"' and not sq and not tpl: dq ^= 1
            elif c == '`' and not sq and not dq: tpl ^= 1
            j += 1
        
        total = sq + dq + tpl
        if i >= 795 and i <= 815:
            marker = ' <<<' if 798 <= i <= 809 else ''
            print(f'L{i+1}{marker}: sq={sq} dq={dq} tpl={tpl} | {line.strip()[:120]}')
    
    print(f'\nFinal: sq={sq} dq={dq} tpl={tpl}')
