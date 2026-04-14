"""Find exact JS line 808"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('football_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
js = scripts[0]
lines = js.split('\n')

# Show lines around 808
for i in range(800, min(820, len(lines))):
    marker = ' >>>>>>' if i == 807 else ''  # 0-indexed, so JS line 808 = index 807
    print(f'JS L{i+1}{marker}: {lines[i][:200]}')
