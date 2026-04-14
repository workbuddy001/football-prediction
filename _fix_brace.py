import re

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

# Step 1: Remove orphaned [] lines (damage from first fix script)
lines = t.split('\n')
cleaned = []
removed = 0
for i, line in enumerate(lines):
    s = line.strip()
    if s == '[]':
        # Check if previous non-empty line ends with ) or ] (array/object close)
        # These are orphaned array literals from bad replacement
        prev_idx = len(cleaned) - 1
        while prev_idx >= 0 and cleaned[prev_idx].strip() == '':
            prev_idx -= 1
        if prev_idx >= 0:
            prev_s = cleaned[prev_idx].strip()
            if prev_s.endswith(')') or prev_s.endswith(']'):
                removed += 1
                continue  # skip this orphaned []
    cleaned.append(line)

if removed > 0:
    print(f'Removed {removed} orphaned [] lines')
t = '\n'.join(cleaned)

# Step 2: Remove _classifyWaterLevel if still inside IIFE
iife_start = t.find("(function () {\n    'use strict'")
cls_pos = t.find('function _classifyWaterLevel')

if cls_pos > iife_start and iife_start > 0:
    b = 0; fo = False; end = cls_pos
    for i in range(cls_pos, len(t)):
        if t[i] == '{': b += 1; fo = True
        elif t[i] == '}':
            b -= 1
            if fo and b == 0:
                end = i + 1
                break
    print(f'Removing misplaced _classifyWaterLevel at char {cls_pos}-{end}')
    t = t[:cls_pos] + t[end:]
else:
    print('_classifyWaterLevel position OK or not found')

# Step 3: Verify balance
opens = t.count('{')
closes = t.count('}')
diff = opens - closes
status = "OK!" if diff == 0 else "DIFF=" + str(diff)
print(f"Braces: {opens}/{closes} -> {status}")

if diff != 0:
    # Try to find where imbalance starts
    depth = 0
    for i, ch in enumerate(t):
        if ch == '{': depth += 1
        elif ch == '}': depth -= 1
        if abs(depth) > 8:
            line_no = t[:i].count('\n') + 1
            context = t[max(0,i-40):i+40]
            print(f'Large depth at char {i} (line {line_no}): depth={depth}')
            print(f'Context: ...{context}...')
            break

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
f.write(t)
f.close()
print(f'Saved ({len(t)} bytes)')
