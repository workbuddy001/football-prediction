"""Comprehensive repair of prematch.js - find and fix ALL structural issues"""
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

print(f'File size: {len(t)} bytes')
print(f'Braces: {{ = {t.count("{")}  }} = {t.count("}")}')

# Problem analysis
issues = []

# 1. Check if _classifyWaterLevel is inside or outside IIFE
iife_start = t.find('(function () {\n    \'use strict\'')
cls_level_pos = t.find('function _classifyWaterLevel')
if cls_level_pos > 0 and iife_start > 0:
    if cls_level_pos < iife_start:
        issues.append('GOOD: _classifyWaterLevel is outside IIFE')
    else:
        issues.append(f'BAD: _classifyWaterLevel is INSIDE IIFE (pos {cls_level_pos} > IIFE pos {iife_start})')

# 2. Check for orphaned * lines (damage from first fix script)
lines = t.split('\n')
for i, line in enumerate(lines):
    s = line.strip()
    # Orphaned JSDoc fragment inside code
    if s == '*' and i > 0 and i < len(lines)-1:
        prev_s = lines[i-1].strip()
        next_s = lines[i+1].strip() if i+1 < len(lines) else ''
        if (prev_s.endswith("';") or prev_s.endswith("'))") or prev_s.endswith('"):
            if next_s.startswith('* ') or next_s == '*/':
                issues.append(f'DAMAGE: orphaned JSDoc fragment at line {i+1}')

# 3. Find all function definitions
import re
func_defs = [(m.start(), m.group()) for m in re.finditer(r'(?:function\s+\w+|\(function\s*\()', t)]
print(f'\nFound {len(func_defs)} function/IIFE definitions:')
for pos, name in func_defs[:15]:
    line_no = t[:pos].count('\n') + 1
    print(f'  Line {line_no}: {name[:50]}')

# 4. Check for duplicate IIFE
iife_count = t.count('(function () {')
if iife_count > 1:
    issues.append(f'BAD: Found {iife_count} IIFE starts - possible duplication!')
    # Show positions
    search_from = 0
    for _ in range(iife_count):
        p = t.find('(function () {', search_from)
        ln = t[:p].count('\n') + 1
        context = t[max(0,p-30):p+30].replace('\n', '\\n')
        issues.append(f'  IIFE #{_+1} at line {ln}: ...{context}...')
        search_from = p + 1

# 5. Show area around line 440-470
print(f'\n=== Lines 438-465 ===')
for i in range(437, min(465, len(lines))):
    marker = ' <--' if i in [446,447,459] else ''
    print(f'  {i+1}: [{lines[i].rstrip()}{marker}]')

print(f'\n=== Issues found: {len(issues)} ===')
for iss in issues:
    print(f'  • {iss}')
