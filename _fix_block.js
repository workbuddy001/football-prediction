# -*- coding: utf-8 -*-
"""Fix prematch.js: add 阻盘检测 to conclusion logic"""
import re

filepath = r'd:\work\workbuddy\足球预测\static\js\prematch.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the conclusion section
old_marker = '// 结论（四维综合：赔付最优 > 基本面 > 澳门心水 > 排除法）'

if old_marker in content:
    new_conclusion = '''// 结论（五维综合：阻盘检测 > 推离最优解 > 基本面压制 > 赔付+排除法一致 > 赔付优先）'''
    content = content.replace(old_marker, new_conclusion)
    
    # Replace the isTrap&&isAnomaly line
    old1 = "reasonHtml='排除法\\u00d7让球出口\\u00d7基本面=完美共振\\u2192应对反向';"
    new1 = "reasonHtml='排除法\\u00d7\\u8ba9\\u7403\\u51fa\\u53e3\\u00d7\\u57fa\\u672c\\u9762=\\u5b8c\\u7f8e\\u5171\\u632f \\u2192 \\u5e94\\u5bf9\\u53cd\\u5411';"
    if old1 in content:
        content = content.replace(old1, new1)
        print("Fixed isTrap line")
    else:
        print(f"WARNING: old1 not found")
        
    # Replace the core judgment tree - find by unique pattern
    # Replace: === 核心判定树 === block
    old_tree_start = "// === \\u6838\\u5fc3\\u5224\\u5b9a\\u6811 ==="
    new_tree = """// === ① 阻盘模式（最高优先级）===
                        if(_isBlockedDir && bt2===stdLowest){
                            reasonHtml='\\u963b\\u76d8\\u6a21\\u5f0f\\uff01'+_blockedName+'\\u88ab\\u8ba9\\u7403\\u76d8\\u8d85\\u9ad8\\u6c34\\u963b\\u62e6,\\u57fa\\u672c\\u9762\\u540c\\u5411=\\u771f\\u65b9\\u5411';
                            finalVerdict=bt2; finalColor='#22c55e';
                        }
                        // === ② 推离最优解 ==="""
    
    if old_tree_start in content:
        # Find the position
        pos = content.find(old_tree_start)
        # Find end of this section (next else-if or closing brace after it)
        # We need to be surgical here
        
        # Instead of complex replacement, let's just do a simpler approach:
        # Insert 阻盘 check before 推离最优解
        insert_text = """// === ① 阻盘模式（最高优先级）===
                        if(_isBlockedDir && bt2===stdLowest){
                            var _blkN={home:mi.home+'胜',draw:'平局',away:mi.away+'胜'}[bt2]||bt2;
                            reasonHtml='\\u963b\\u76d8\\u6a21\\u5f0f\\uff01'+_blockedName+'\\u88ab\\u8ba9\\u7403\\u76d8\\u8d85\\u9ad8\\u6c34\\u963b\\u62e6,\\u57fa\\u672c\\u9762\\u540c\\u5411=\\u771f\\u65b9\\u5411';
                            finalVerdict=bt2; finalColor='#22c55e';
                        }
                        // === ② 推离最优解 ===
                        """
        content = content.replace(old_tree_start, insert_text + "\n                        // === ③ 原始逻辑(降级) ===")
        print("Inserted 阻盘 mode before 推离最优解")
    else:
        print(f"WARNING: tree start not found")
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: File written")
else:
    print(f"ERROR: marker '{old_marker}' not found in file!")
