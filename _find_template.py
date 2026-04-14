"""Find where the backtick template string starting at line 275 closes"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('_test_syntax.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 275 (0-indexed: 274) starts: let html = `
# Find the matching close backtick

in_template = False
template_start = None
depth = 0  # track nested template literals via ${}

for i, line in enumerate(lines):
    if i < 274: continue  # skip before renderDetail
    
    j = 0
    while j < len(line):
        c = line[j]
        if c == '`':
            if not in_template:
                in_template = True
                template_start = (i+1, j)
                print(f"Template OPEN at L{i+1} col{j}: {line.strip()[:80]}")
            elif depth == 0:
                in_template = False
                print(f"Template CLOSE at L{i+1} col{j}: {line.strip()[:80]}")
                print(f"  → Template spanned {i+1 - template_start[0]} lines")
            else:
                depth -= 1  # nested template closing
        elif c == '$' and in_template and j+1 < len(line) and line[j+1] == '{':
            # Check for nested template literal inside ${}
            # Simple heuristic: look for next ` after ${
            rest = line[j+2:]
            if '`' in rest:
                depth += 1
        j += 1

if in_template:
    print(f"\n⚠️ TEMPLATE NEVER CLOSED! Started at L{template_start[0]}")
    print("Everything after that is inside a string literal!")
