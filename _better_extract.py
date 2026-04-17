# -*- coding: utf-8 -*-
"""更好的提取方法"""
import re
import json

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

results = []

# 查找所有公司行
# 格式: <tr class="tr1" id="..." ...>...<td class="tb_plgs"...赔率表格...</tr>
# 或者：<tr class="tr1">...赔率...</tr>

# 先找所有 tr 元素
tr_pattern = re.compile(r'<tr[^>]*class="[^"]*tr1[^"]*"[^>]*>(.*?)</tr>', re.S)
trs = tr_pattern.findall(content)
print(f"找到 {len(trs)} 个 tr1")

# 提取公司名称
name_pattern = re.compile(r'<span[^>]*class="[^"]*quancheng[^"]*"[^>]*>([^<]+)</span>')
odds_pattern = re.compile(r'<td[^>]*>\s*([\d.]+)\s*</td>')

for i, tr in enumerate(trs[:35]):
    name_match = name_pattern.search(tr)
    name = name_match.group(1).strip() if name_match else f"公司{i+1}"
    
    odds = odds_pattern.findall(tr)
    if len(odds) >= 6:
        results.append({
            '公司': name,
            '初盘胜': odds[0], '初盘平': odds[1], '初盘负': odds[2],
            '即时胜': odds[3], '即时平': odds[4], '即时负': odds[5],
        })

print(f"提取了 {len(results)} 家公司")

# 打印前10家
for r in results[:10]:
    print(f"{r['公司']}: {r['初盘胜']},{r['初盘平']},{r['初盘负']} | {r['即时胜']},{r['即时平']},{r['即时负']}")

# 保存
with open('_ouzhi_full.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
