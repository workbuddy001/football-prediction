"""Fix: promote _hcWaterInfo to module-level _classifyWaterLevel"""
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

# Step 1: Find and remove inner _hcWaterInfo function
start_marker = 'function _hcWaterInfo(o) {'
end_marker = "return {level:'\u8d85\u4f4e\u6c34'"
idx = t.find(start_marker)
if idx >= 0:
    # Find the closing } of this function (the one before the next statement)
    # Look for the pattern: tier:1}\n                    }
    search_start = idx
    close_pattern = "tier:1}\n"
    end_idx = t.find(close_pattern, search_start) + len(close_pattern) + 20  # approximate
    # More precise: find the matching }
    brace_count = 0
    found_open = False
    for i in range(idx, min(idx+500, len(t))):
        if t[i] == '{':
            brace_count += 1
            found_open = True
        elif t[i] == '}':
            brace_count -= 1
            if found_open and brace_count == 0:
                end_idx = i + 1  # include the closing }
                break
    
    # Also remove leading whitespace and newline after
    while end_idx < len(t) and t[end_idx] in ' \t\n':
        end_idx += 1
        
    print(f'Removing inner function at {idx}-{end_idx}')
    t = t[:idx].rstrip() + '\n' + t[end_idx:].lstrip('\n')
    if not t[end_idx:end_idx+1] == '\n':
        t = t[:idx].rstrip() + '\n' + t[end_idx:]
else:
    print('Inner function not found')

# Step 2: Add module-level function before IIFE
module_func = '''// Module-level water classification (shared across all scopes)
function _classifyWaterLevel(o, C) {
    if (!o || isNaN(o) || o <= 0) return {level:"-", intent:"-", color:(C||{}).textDim||"#888", tier:-1};
    if (o > 3.5) return {level:"\u8d85\u9ad8\u6c34", intent:"\u963b \u62c9\u9ad8\u8ba9\u4f60\u4e0d\u6542\u4e70", color:"#ef4444", tier:6};
    if (o >= 2.8) return {level:"\u9ad8\u6c34", intent:"\u8bf3 \u9ad8\u500d\u52fe\u4f60\u535a", color:"#f97316", tier:5};
    if (o >= 2.45) return {level:"\u4e2d\u5eb9", intent:"\u6563 \u62ff\u4e0d\u51c6\u4e3b\u610f", color:"#eab308", tier:4};
    if (o >= 1.80) return {level:"\u4e2d\u6c34", intent:"\u5f15 \u5408\u7406\u533a\u95f4\u5f15\u5bfc", color:"#22c55e", tier:3};
    if (o >= 1.50) return {level:"\u4f4e\u6c34", intent:"\u786e\u8ba4 \u5927\u6982\u7387\u65b9\u5411", color:"#3b82f6", tier:2};
    return {level:"\u8d85\u4f4e\u6c34", intent:"\u5f3a\u786e\u8ba4 \u51e0\u4e49\u786e\u5b9a", color:"#06b6d4", tier:1};
}

'''
iife_pos = t.find('(function()')
if iife_pos > 0:
    t = t[:iife_pos] + module_func + t[iife_pos:]
    print('Added module-level function before IIFE')

# Step 3: Replace all calls to _hcWaterInfo with _classifyWaterLevel
replacements = [
    '_hcWaterInfo(hci.odds)',
    '_hcWaterInfo(_hcPredOdds)', 
    '_hcWaterInfo(hh)',
]
for old in replacements:
    if old in t:
        new = old.replace('_hcWaterInfo(', '_classifyWaterLevel(').replace(')', ', C)')
        cnt = t.count(old)
        t = t.replace(old, new)
        print(f'  Replaced {cnt}x: {old}')

# Also fix classifyWater calls and remaining _hcWaterInfo
for old_str in ['classifyWater(', '_hcWaterInfo(']:
    if old_str in t:
        t = t.replace(old_str, '_classifyWaterLevel(')
        print(f'  Also replaced: {old_str} -> _classifyWaterLevel(')

# Verify no more references to undefined _hcWaterInfo
if '_hcWaterInfo(' in t:
    print('WARNING: still has _hcWaterInfo( references!')
else:
    print('All _hcWaterInfo references cleaned up')

f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
f.write(t)
f.close()
print(f'Done! File saved ({len(t)} bytes)')
