"""Fix: Inline water classification into _synthesizeFinalRecommendation to avoid scope issues"""
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
t = f.read()
f.close()

# Step 1: Find and remove the misplaced _classifyWaterLevel (it's inside IIFE)
# It starts with "function _classifyWaterLevel" and we need to find its exact end
cls_start = t.find('function _classifyWaterLevel')
if cls_start > 0:
    # Find matching close brace
    brace = 0
    found_open = False
    end = cls_start
    for i in range(cls_start, len(t)):
        if t[i] == '{':
            brace += 1
            found_open = True
        elif t[i] == '}':
            brace -= 1
            if found_open and brace == 0:
                end = i + 1
                break
    
    removed = t[cls_start:end]
    # Include trailing newlines
    while end < len(t) and t[end] in '\n\r':
        end += 1
        removed = t[cls_start:end]
    
    print(f'Removing _classifyWaterLevel ({end-cls_start} chars) at pos {cls_start}')
    t = t[:cls_start] + t[end:]
else:
    print('_classifyWaterLevel not found')

# Step 2: Now find _synthesizeFinalRecommendation and inline water logic
ext_start = t.find('function _synthesizeFinalRecommendation')
if ext_start < 0:
    print('ERROR: _synthesizeFinalRecommendation not found!')
else:
    print(f'Found _synthesizeFinalRecommendation at pos {ext_start}')
    
    # Define inline water helper as first line of function body
    inline_helper = """function _wl(o){if(!o||isNaN(o)||o<=0)return{t:'-',c:'#888',r:-1};if(o>3.5)return{t:'\u8d85\u9ad8\u6c34',c:'#ef4444',r:6};if(o>=2.8)return{t:'\u9ad8\u6c34',c:'#f97316',r:5};if(o>=2.45)return{t:'\u4e2d\u5eb9',c:'#eab308',r:4};if(o>=1.80)return{t:'\u4e2d\u6c34',c:'#22c55e',r:3};if(o>=1.50)return{t:'\u4f4e\u6c34',c:'#3b82f6',r:2};return{t:'\u8d85\u4f4e\u6c34',c:'#06b6d4',r:1}};"""
    
    # Insert after opening brace of function
    func_body_start = t.find('{', ext_start) + 1
    t = t[:func_body_start] + '\n        ' + inline_helper + '\n' + t[func_body_start:]
    print('Inserted inline water helper')
    
    # Replace all _classifyWaterLevel calls within this function
    ext_end = ext_start  # recalculate after insert
    ext_end = t.find('function _synthesizeFinalRecommendation')
    # Find end of function
    b = 0
    fo = False
    fe = ext_end
    for i in range(ext_end, min(ext_end+15000, len(t))):
        if t[i] == '{': b += 1; fo = True
        elif t[i] == '}':
            b -= 1
            if fo and b == 0:
                fe = i + 1
                break
    
    section = t[ext_end:fe]
    
    # Count replacements
    c1 = section.count('_classifyWaterLevel(')
    c2 = section.count('_hcWaterInfo(')
    c3 = section.count('classifyWater(')
    
    section = section.replace('_classifyWaterLevel(', '_wl(')
    section = section.replace('_hcWaterInfo(', '_wl(')
    section = section.replace('classifyWater(', '_wl(')
    
    t = t[:ext_end] + section + t[fe:]
    total = c1+c2+c3
    if total > 0:
        print(f'Replaced {total} calls (_classifyWaterLevel:{c1} _hcWaterInfo:{c2} classifyWater:{c3}) -> _wl()')

# Step 3: Check if there are still orphaned _classifyWaterLevel references elsewhere
remaining_cls = t.count('_classifyWaterLevel(')
remaining_hc = t.count('_hcWaterInfo(')
remaining_cl = t.count('classifyWater(')
print(f'Remaining refs: _classifyWaterLevel={remaining_cls} _hcWaterInfo={remaining_hc} classifyWater={remaining_cl}')

# Step 4: Verify brace balance
opens = t.count('{')
closes = t.count('}')
print(f'Braces: {opens}/{closes} -> {"OK" if opens==closes else "DIFF="+str(opens-closes)}')

# Save
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
f.write(t)
f.close()
print(f'Saved ({len(t)} bytes)')
