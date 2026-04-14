"""Binary search for the exact unbalanced brace location in source file"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('football_web.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the <script> start line
script_start = None
for i, line in enumerate(lines):
    if '<script>' in line:
        script_start = i
        break

print(f"<script> at file line {script_start+1}")

# Extract only the JS part (from script_start to </script>)
js_lines = []
for i in range(script_start+1, len(lines)):
    if '</script>' in lines[i]:
        break
    js_lines.append(lines[i].rstrip('\n'))

print(f"JS has {len(js_lines)} lines")

# Now do binary search: find the earliest line where prefix is still valid
# We'll use a simple approach: check if the JS up to line N has balanced braces (approximately)

def check_balance_up_to(n):
    """Check brace balance up to line n, ignoring strings/templates"""
    text = '\n'.join(js_lines[:n])
    # Remove string contents (simple approach)
    import re
    # Remove template literals
    text2 = re.sub(r'`[^`]*\${', '', text)
    text2 = re.sub(r'}[^`]*`', '', text2)
    # Remove regular strings
    text2 = re.sub(r'"(?:[^"\\]|\\.)*"', '', text2)
    text2 = re.sub(r"'(?:[^'\\]|\\.)*'", '', text2)
    return text2.count('{') - text2.count('}')

# Binary search
lo, hi = 10, len(js_lines)
last_good = lo
while hi - lo > 1:
    mid = (lo + hi) // 2
    bal = check_balance_up_to(mid)
    print(f"  Lines 1-{mid}: balance={bal}")
    # If balance went very negative or we're past the issue
    if bal < -5:
        hi = mid
    elif abs(bal) < 20:  # reasonable range
        last_good = mid
        lo = mid
    else:
        hi = mid

print(f"\nLast good range: around line {last_good}")
print(f"Showing lines {max(1,last_good-5)} to {min(len(js_lines), last_good+5)}:")
for i in range(max(0,last_good-5), min(len(js_lines), last_good+5)):
    print(f"  PyL{i+1} (srcL{i+script_start+1}): {js_lines[i][:150]}")

# Also show the full balance at end
print(f"\nFinal full balance: {check_balance_up_to(len(js_lines))}")
