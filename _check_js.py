"""Check JS code for unclosed strings near rgba()"""
import re

with open('football_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
js = scripts[0]
lines = js.split('\n')

# Find lines with rgba that might have unbalanced quotes
for i, line in enumerate(lines):
    if 'rgba' in line.lower():
        sq = line.count("'")
        dq = line.count('"')
        # Check for odd quote counts (potential unclosed string)
        if sq % 2 == 1 or dq % 2 == 1:
            print(f'Line {i+1}: ODD quotes! single={sq} double={dq}')
            print(f'  {line[:150]}')
            print()
