import re

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

lines = t.split('\n')
print(f'Total lines: {len(lines)}')

# Strategy: Find where _classifyWaterLevel was inserted inside IIFE
# and move it outside

# 1. Identify: is _classifyWaterLevel before or after IIFE?
cls_pos = t.find('function _classifyWaterLevel')
iife_pos = t.find("(function () {\n    'use strict'")
print(f'_classifyWaterLevel at char {cls_pos}, line {t[:cls_pos].count(chr(10))+1}')
print(f'IIFE at char {iife_pos}, line {t[:iife_pos].count(chr(10))+1}')

if cls_pos > iife_pos:
    print('PROBLEM: _classifyWaterLevel is INSIDE IIFE - need to extract it')
    
    # Extract the function
    func_start = cls_pos
    func_end = t.find('\n}\n', func_start) + 2
    if func_end < func_start:
        # Try finding just }\n
        func_end = t.find('}\n', func_start)
        while func_end > 0:
            # Check if this looks like end of function
            chunk = t[func_start:func_end+2]
            if chunk.count('{') == chunk.count('}') + 1:  # one extra { from function decl
                func_end += 2
                break
            func_end = t.find('}\n', func_end+1)
    
    extracted_func = t[func_start:func_end]
    print(f'Extracted function ({len(extracted_func)} bytes):')
    for i, l in enumerate(extracted_func.split('\n')[:12]):
        print(f'  {l}')
    
    # Remove from inside IIFE
    t = t[:func_start] + t[func_end:]
    
    # Add before IIFE
    iife_pos2 = t.find("(function () {\n    'use strict'")
    t = t[:iife_pos2] + extracted_func + '\n\n' + t[iife_pos2:]
    print(f'Function moved to before IIFE')
else:
    print('OK: _classifyWaterLevel is already outside IIFE')

# 2. Fix _hcWaterInfo calls in external function
ext_start = t.find('function _synthesizeFinalRecommendation')
if ext_start > 0:
    ext_section = t[ext_start:]
    count1 = ext_section.count('_hcWaterInfo(')
    count2 = ext_section.count('classifyWater(')
    ext_section = ext_section.replace('_hcWaterInfo(', '_classifyWaterLevel(')
    ext_section = ext_section.replace('classifyWater(', '_classifyWaterLevel(')
    t = t[:ext_start] + ext_section
    if count1 > 0 or count2 > 0:
        print(f'Replaced {count1} _hcWaterInfo + {count2} classifyWater calls')

# 3. Verify
opens = t.count('{')
closes = t.count('}')
print(f'Braces: {opens} open / {closes} close -> {"BALANCED" if opens==closes else "UNBALANCED by "+str(opens-closes)}')

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
f.write(t)
f.close()
print(f'Saved ({len(t)} bytes)')
