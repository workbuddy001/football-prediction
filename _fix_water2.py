"""Minimal fix: add _classifyWaterLevel as module-level, fix only new function calls"""
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

# Step 1: Add module-level function right before IIFE (don't touch anything else)
module_func = '''// Module-level water classification for cross-scope access
function _classifyWaterLevel(o, C) {
    if (!o || isNaN(o) || o <= 0) return {level:"-", intent:"-", color:(C&&C.textDim)||"#888", tier:-1};
    if (o > 3.5) return {level:"\u8d85\u9ad8\u6c34", intent:"\u963b \u62c9\u9ad8\u8ba9\u4f60\u4e0d\u6542\u4e70", color:"#ef4444", tier:6};
    if (o >= 2.8) return {level:"\u9ad8\u6c34", intent:"\u8bf3 \u9ad8\u500d\u52fe\u4f60\u535a", color:"#f97316", tier:5};
    if (o >= 2.45) return {level:"\u4e2d\u5eb9", intent:"\u6563 \u62ff\u4e0d\u51c6\u4e3b\u610f", color:"#eab308", tier:4};
    if (o >= 1.80) return {level:"\u4e2d\u6c34", intent:"\u5f15 \u5408\u7406\u533a\u95f4\u5f15\u5bfc", color:"#22c55e", tier:3};
    if (o >= 1.50) return {level:"\u4f4e\u6c34", intent:"\u786e\u8ba4 \u5927\u6982\u7387\u65b9\u5411", color:"#3b82f6", tier:2};
    return {level:"\u8d85\u4f4e\u6c34", intent:"\u5f3a\u786e\u8ba4 \u51e0\u4e49\u786e\u5b9a", color:"#06b6d4", tier:1};
}

'''
iife_pos = t.find('(function()')
if iife_pos > 0 and '_classifyWaterLevel' not in t:
    t = t[:iife_pos] + module_func + t[iife_pos:]
    print(f'Added _classifyWaterLevel before IIFE at position {iife_pos}')
elif '_classifyWaterLevel' in t:
    print('_classifyWaterLevel already exists')

# Step 2: Only replace calls in _synthesizeFinalRecommendation (external function)
# Find the external function area
ext_start = t.find('function _synthesizeFinalRecommendation')
if ext_start > 0:
    # Replace all _hcWaterInfo calls in this function only
    ext_end = t.find('return null;\n}', ext_start)
    if ext_end < 0:
        ext_end = t.find('return null;}', ext_start)
    if ext_end > 0:
        ext_section = t[ext_start:ext_end]
        old_count = ext_section.count('_hcWaterInfo(')
        new_section = ext_section.replace('_hcWaterInfo(', '_classifyWaterLevel(')
        # Fix classifyWater too if present
        new_section = new_section.replace('classifyWater(', '_classifyWaterLevel(')
        t = t[:ext_start] + new_section + t[ext_end:]
        print(f'Replaced {old_count} _hcWaterInfo calls in _synthesizeFinalRecommendation')
else:
    print('WARNING: _synthesizeFinalRecommendation not found!')

# Step 3: Verify no syntax issues - check brace balance
opens = t.count('{')
closes = t.count('}')
print(f'Brace balance: {opens} open, {closes} close -> {"OK" if opens==closes else "MISMATCH!"}')

# Save
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
f.write(t)
f.close()
print(f'Saved ({len(t)} bytes)')
