# -*- coding: utf-8 -*-
"""提取赔率数据"""
import re

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 提取所有 td 中的数字
all_tds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', content)

# 过滤出赔率（1.0 到 15.0 之间）
def is_odds(val):
    try:
        v = float(val)
        return 1.0 <= v <= 15.0
    except:
        return False

# 整理数据：每3个数字为一组
grouped = []
for i in range(0, len(all_tds), 3):
    if i+2 < len(all_tds):
        g = [all_tds[i], all_tds[i+1], all_tds[i+2]]
        if all(is_odds(x) for x in g):
            grouped.append(g)

print(f"找到 {len(grouped)} 组有效赔率")

# 每2组为一公司（初盘+即时）
companies = []
for i in range(0, len(grouped), 2):
    if i+1 < len(grouped):
        init = grouped[i]  # 初盘
        real = grouped[i+1]  # 即时
        companies.append({
            '初盘胜': init[0],
            '初盘平': init[1],
            '初盘负': init[2],
            '即时胜': real[0],
            '即时平': real[1],
            '即时负': real[2],
        })

print(f"提取了 {len(companies)} 家公司赔率")

# 提取公司名称
# 公司名在赔率行之前的 td 中
company_names = re.findall(r'<td[^>]*class="[^"]*tdis[^"]*"[^>]*>([^<]+)</td>', content)
print(f"\n公司名称: {len(company_names)}")
for i, name in enumerate(company_names[:5]):
    print(f"  {i+1}: {name.strip()}")

# 打印前5家公司
print("\n前5家公司赔率:")
for i, c in enumerate(companies[:5]):
    name = company_names[i].strip() if i < len(company_names) else f"公司{i+1}"
    print(f"  {name}: 初盘({c['初盘胜']},{c['初盘平']},{c['初盘负']}) 即时({c['即时胜']},{c['即时平']},{c['即时负']})")

# 保存结果
import json
with open('_ouzhi_data.json', 'w', encoding='utf-8') as f:
    json.dump(companies, f, ensure_ascii=False, indent=2)
print(f"\n已保存到 _ouzhi_data.json")
