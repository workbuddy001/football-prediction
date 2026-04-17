# -*- coding: utf-8 -*-
"""完整提取赔率和公司名"""
import re
import json

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

results = []

# 找到所有公司块
# 每行格式：<tr class="tr1" id="1" ...>...赔率...</tr>
company_blocks = re.findall(
    r'<tr[^>]*class="tr1[^"]*"[^>]*>(.*?)</tr>',
    content, re.S
)

print(f"找到 {len(company_blocks)} 个公司块")

# 提取每个公司的名称和赔率
for i, block in enumerate(company_blocks[:35]):  # 只取前35个
    # 公司名
    name_match = re.search(r'<span[^>]*class="quancheng"[^>]*>([^<]+)</span>', block)
    if not name_match:
        name_match = re.search(r'title="([^"]+)"', block)
    
    name = name_match.group(1).strip() if name_match else f"公司{i+1}"
    
    # 提取赔率（初盘+即时）
    odds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', block)
    
    if len(odds) >= 6:
        # 前3个是初盘，后3个是即时
        result = {
            '公司': name,
            '初盘胜': odds[0],
            '初盘平': odds[1],
            '初盘负': odds[2],
            '即时胜': odds[3],
            '即时平': odds[4],
            '即时负': odds[5],
        }
        results.append(result)
        print(f"  {len(results)}. {name}: 初盘({result['初盘胜']},{result['初盘平']},{result['初盘负']}) 即时({result['即时胜']},{result['即时平']},{result['即时负']})")

print(f"\n共提取 {len(results)} 家公司")
print("\n=== 完整数据 ===")
for r in results:
    print(f"{r['公司']}: {r['初盘胜']},{r['初盘平']},{r['初盘负']} | {r['即时胜']},{r['即时平']},{r['即时负']}")

# 保存
with open('_ouzhi_full.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n已保存到 _ouzhi_full.json")
