"""Check ALL JS in rendered HTML - find every script and inline handler"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('_rendered.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all script tags
scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
print(f'Found {len(scripts)} <script> tags')
for i, s in enumerate(scripts):
    print(f'  Script {i+1}: {len(s)} chars, {s.count(chr(10))} lines')

# Check for inline onclick etc with rgba
inline = re.findall(r'onclick="[^"]*rgba[^"]*"', content)
if inline:
    print(f'\n{len(inline)} inline handlers with rgba:')
    for x in inline[:5]: print(f'  {x[:150]}')

# Also check for any bare 'rgba(' outside style/script context
# Look around line 808 area for anything weird
lines = content.split('\n')
print(f'\nTotal HTML: {len(lines)} lines')

# Find what HTML line corresponds to JS line 808
js_start = content.find('<script>')
# Count lines before script
html_lines_before = content[:js_start].count('\n')
print(f'HTML lines before <script>: {html_lines_before}')
print(f'So JS line 808 = HTML line ~{html_lines_before + 808}')

# Show that area
target = html_lines_before + 806
for i in range(max(0,target-3), min(len(lines), target+5)):
    marker = ' <<<' if i == target-1 else ''
    print(f'H{i+1}{marker}: {lines[i][:150]}')
