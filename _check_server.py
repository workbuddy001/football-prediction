import urllib.request, re, sys, subprocess, json
sys.stdout.reconfigure(encoding='utf-8')

resp = urllib.request.urlopen('http://127.0.0.1:8899')
html = resp.read().decode('utf-8')
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
js = scripts[0]

# Save to temp file and run through node
with open('_temp_check.js', 'w', encoding='utf-8') as f:
    f.write(js)

# Try to parse with node
result = subprocess.run(['node', '--check', '_temp_check.js'], capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("RC:", result.returncode)

# If error, try acorn or simpler approach
if result.returncode != 0:
    # Try to narrow down by splitting the file
    print("\n--- Binary search for error location ---")
    full = js
    
    # Try parsing incrementally
    lines = full.split('\n')
    
    # Find which line range causes the error
    lo, hi = 0, len(lines)
    while hi - lo > 5:
        mid = (lo + hi) // 2
        test = '\n'.join(lines[:mid])
        with open('_temp_check.js', 'w', encoding='utf-8') as f:
            f.write(test)
        r = subprocess.run(['node', '--check', '_temp_check.js'], capture_output=True, text=True)
        if r.returncode == 0:
            lo = mid
        else:
            hi = mid
        print(f"  Range [{lo}, {hi}] -> {'OK' if r.returncode == 0 else 'ERROR'}")
    
    print(f"\nError is around line {lo+1}-{hi+1}")
    for i in range(max(0,lo-3), min(len(lines), hi+3)):
        marker = " >>>" if i >= lo and i < hi else ""
        print(f"L{i+1}{marker}: {lines[i][:150]}")
