"""Extract JS from football_web.py and run through Node.js syntax checker"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('football_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
js = scripts[0]

# Write to temp file
with open('_temp_check.js', 'w', encoding='utf-8') as f:
    f.write(js)

print(f'Extracted {len(js)} chars of JS to _temp_check.js')
print('Run: node --check _temp_check.js')
