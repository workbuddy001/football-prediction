# -*- coding: utf-8 -*-
"""在结论判断树中插入阻盘模式（最高优先级）"""
filepath = r'd:\work\workbuddy\足球预测\static\js\prematch.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 更新标题
old_title = '// 结论（四维综合：赔付最优 > 基本面 > 澳门心水 > 排除法）'
new_title = '// 结论（五维综合：阻盘检测 > 推离最优解 > 基本面压制 > 赔付+排除法一致 > 赔付优先）'
content = content.replace(old_title, new_title)

# 2. 在 === 核心判定树 === 之后、if(isPushedAwayBest)之前插入阻盘
old_block = """                        // === 核心判定树 ===
                        if(isPushedAwayBest){"""

new_block = """                        // === 核心判定树 ===
                        // ① 阻盘模式（最高优先级）：标准盘低赔方向被让球盘超高水阻拦 + 基本面同向 = 真方向
                        if(_isBlockedDir && bt2===stdLowest){
                            reasonHtml='\\u963b\\u76d8\\u6a21\\u5f0f\\uff01'+_blockedName+'\\u88ab\\u8ba9\\u7403\\u76d8\\u8d85\\u9ad8\\u6c34\\u963b\\u62e6,\\u57fa\\u672c\\u9762\\u540c\\u5411=\\u771f\\u65b9\\u5411';
                            finalVerdict=bt2; finalColor='#22c55e';
                        }
                        // ② 推离最优解
                        else if(isPushedAwayBest){"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("OK: inserted 阻盘 mode as #1 priority")
else:
    print("ERROR: old_block not found!")
    # debug: show what's around line 692
    idx = content.find('核心判定树')
    if idx >= 0:
        print(f"Found at pos {idx}: ...{repr(content[idx:idx+80])}...")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE")
