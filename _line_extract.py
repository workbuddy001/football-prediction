# -*- coding: utf-8 -*-
"""逐行提取"""
import re
import json

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

results = []
lines = content.split('\n')

# 找到包含赔率的行，追踪上下文
in_block = False
current_company = ""
current_odds = []

for i, line in enumerate(lines):
    # 公司名行
    if 'tb_plgs' in line:
        m = re.search(r'<span[^>]*>([^<]+)</span>', line)
        if m:
            current_company = m.group(1).strip()
    
    # 赔率行（包含 klfc=）
    if 'klfc=' in line and current_company:
        odds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', line)
        if odds:
            current_odds.extend(odds)
            # 当有6个赔率时，保存
            if len(current_odds) >= 6:
                results.append({
                    '公司': current_company,
                    '初盘胜': current_odds[0], '初盘平': current_odds[1], '初盘负': current_odds[2],
                    '即时胜': current_odds[3], '即时平': current_odds[4], '即时负': current_odds[5],
                })
                current_company = ""
                current_odds = []

print(f"提取了 {len(results)} 家公司")

# 打印
for r in results[:10]:
    print(f"{r['公司']}: {r['初盘胜']},{r['初盘平']},{r['初盘负']} | {r['即时胜']},{r['即时平']},{r['即时负']}")

# 保存
with open('_ouzhi_full.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n已保存到 _ouzhi_full.json")
