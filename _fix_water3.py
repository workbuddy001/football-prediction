"""Precise fix for prematch.js - repair damage + add module-level water function"""
f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

# Find the damage point: look for orphaned "* " followed by comment lines
damage_start = -1
for i, line in enumerate(lines):
    stripped = line.strip()
    # Look for the pattern: a lone "* " then comment lines starting with * then */
    if stripped == '*' and i+1 < len(lines) and lines[i+1].strip().startswith('* '):
        # Check if this is the damage (orphaned after function removal)
        if i > 0 and lines[i-1].strip().endswith("';"):
            damage_start = i
            print(f'Damage found at line {i+1}: "{stripped}"')
            break

if damage_start < 0:
    # Try alternative detection: find orphaned content before (function()
    for i, line in enumerate(lines):
        if line.strip() == '(function () {' and i > 2:
            prev = lines[i-1].strip()
            if not prev.endswith('}') and not prev == '' and not prev.startswith('//') and not prev.startswith('*'):
                damage_start = i - 1
                print(f'Alternative damage at line {damage_start+1}: "{prev}"')
                break

if damage_start < 0:
    print('Could not auto-detect damage location!')
    # Manual search around line 447
    print(f'Lines 440-460:')
    for i in range(439, min(460, len(lines))):
        print(f'  {i+1}: [{lines[i].rstrip()}]')
else:
    # Find where the IIFE starts
    iife_start = -1
    for i in range(damage_start, min(damage_start+20, len(lines))):
        if '(function () {' in lines[i]:
            iife_start = i
            break
    
    if iife_start > 0:
        # Remove everything from damage_start to iife_start-1
        print(f'Removing lines {damage_start+1} to {iife_start} (damaged area)')
        
        # Insert the module-level function + proper spacing before IIFE
        new_lines = lines[:damage_start]
        new_lines.append('\n')
        new_lines.append('// Module-level water classification (shared across all scopes)\n')
        new_lines.append('function _classifyWaterLevel(o, C) {\n')
        new_lines.append("    if (!o || isNaN(o) || o <= 0) return {level:'-', intent:'-', color:(C&&C.textDim)||'#888', tier:-1};\n")
        new_lines.append("    if (o > 3.5) return {level:'\u8d85\u9ad8\u6c34', intent:'\u963b \u62c9\u9ad8\u8ba9\u4f60\u4e0d\u6542\u4e70', color:'#ef4444', tier:6};\n")
        new_lines.append("    if (o >= 2.8) return {level:'\u9ad8\u6c34', intent:'\u8bf3 \u9ad8\u500d\u52fe\u4f60\u535a', color:'#f97316', tier:5};\n")
        new_lines.append("    if (o >= 2.45) return {level:'\u4e2d\u5eb9', intent:'\u6563 \u62ff\u4e0d\u51c6\u4e3b\u610f', color:'#eab308', tier:4};\n")
        new_lines.append("    if (o >= 1.80) return {level:'\u4e2d\u6c34', intent:'\u5f15 \u5408\u7406\u533a\u95f4\u5f15\u5bfc', color:'#22c55e', tier:3};\n")
        new_lines.append("    if (o >= 1.50) return {level:'\u4f4e\u6c34', intent:'\u786e\u8ba4 \u5927\u6982\u7387\u65b9\u5411', color:'#3b82f6', tier:2};\n")
        new_lines.append("    return {level:'\u8d85\u4f4e\u6c34', intent:'\u5f3a\u786e\u8ba4 \u51e0\u4e49\u786e\u5b9a', color:'#06b6d4', tier:1};\n")
        new_lines.append('}\n')
        new_lines.append('\n')
        new_lines.extend(lines[iife_start:])  # Keep from IIFE onwards
        
        # Now fix all _hcWaterInfo calls in _synthesizeFinalRecommendation (external)
        full = ''.join(new_lines)
        
        # Find external function and replace its calls
        ext_start = full.find('function _synthesizeFinalRecommendation')
        if ext_start > 0:
            ext_section = full[ext_start:]
            orig_count = ext_section.count('_hcWaterInfo(')
            ext_section = ext_section.replace('_hcWaterInfo(', '_classifyWaterLevel(')
            ext_section = ext_section.replace('classifyWater(', '_classifyWaterLevel(')
            full = full[:ext_start] + ext_section
            if orig_count > 0:
                print(f'Replaced {orig_count} _hcWaterInfo calls in _synthesizeFinalRecommendation')
        
        # Verify brace balance
        opens = full.count('{')
        closes = full.count('}')
        print(f'Brace balance: {opens} open, {closes} close -> {"OK" if opens==closes else "MISMATCH!"}')
        
        f = open('d:/work/workbuddy/足球预测/static/js/prematch.js', 'w', encoding='utf-8')
        f.write(full)
        f.close()
        print(f'Saved ({len(full)} bytes)')
    else:
        print('ERROR: Could not find IIFE start position!')
