"""Extract JS from football_web.py and check syntax with node"""
import re
import subprocess

with open('football_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
js = scripts[0]

# Write to temp file
with open('_test_js.js', 'w', encoding='utf-8') as f:
    f.write(js)

# Check with node --check
result = subprocess.run(['node', '--check', '_test_js.js'], capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
