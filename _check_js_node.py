"""Extract JS from football_web.py and run Node syntax checker"""
import re, sys, subprocess
sys.stdout.reconfigure(encoding='utf-8')

with open('football_web.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract script content
m = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if not m:
    print("No <script> found!")
    sys.exit(1)

js = m.group(1)
with open('_test_syntax.js', 'w', encoding='utf-8') as f:
    f.write(js)

print(f"Extracted {len(js)} chars of JS to _test_syntax.js")

# Run Node syntax check
result = subprocess.run(
    ['C:\\Program Files\\nodejs\\node.exe', '--check', '_test_syntax.js'],
    capture_output=True, text=True, encoding='utf-8'
)
print("\n=== NODE SYNTAX CHECK ===")
if result.returncode == 0:
    print("✅ NO SYNTAX ERRORS")
else:
    print(f"❌ Error (code {result.returncode}):")
    print(result.stderr)
