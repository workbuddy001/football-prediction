"""Extract JS and find rgba outside strings"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('football_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
js = scripts[0]
lines = js.split('\n')

in_single = False
in_double = False

for i, line in enumerate(lines):
    j = 0
    while j < len(line):
        c = line[j]
        if c == "'" and not in_double:
            if j == 0 or line[j-1] != '\\':
                in_single = not in_single
        elif c == '"' and not in_single:
            if j == 0 or line[j-1] != '\\':
                in_double = not in_double
        j += 1
    
    if 'rgba' in line.lower() and not in_single and not in_double:
        print(f'Line {i+1}: rgba OUTSIDE STRING!')
    
    if 2590 <= i <= 2830:
        print(f'  L{i+1}: sq={in_single} dq={in_double} | {line.strip()[:100]}')

print(f'\nFinal: in_single={in_single}, in_double={in_double}')
