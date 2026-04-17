# -*- coding: utf-8 -*-
"""解析欧赔页面 - 简化版"""
import re

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 方案1: 搜索所有赔率数据
# 提取所有 td 中的数字
all_tds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', content)
print(f"总共 {len(all_tds)} 个 td 数字")

# 找到包含赔率数字的行
lines = content.split('\n')
odds_data = []
for i, line in enumerate(lines):
    if 'klfc=' in line:
        tds = re.findall(r'<td[^>]*>\s*([\d.]+)\s*</td>', line)
        if len(tds) >= 3:
            odds_data.append(tds)

print(f"找到 {len(odds_data)} 行赔率")

# 每2行一组（初盘+即时）
companies_raw = re.findall(r'<td[^>]*class="[^"]*tdis[^"]*"[^>]*>([^<]+)</td>', content)
print(f"公司数量: {len(companies_raw)}")

# 打印前30行赔率
print("\n前30行赔率:")
for i, odds in enumerate(odds_data[:30]):
    print(f"  {i+1}: {odds}")

# 整理数据：每3个数字为一行
# 格式：初盘胜、初盘平、初盘负、即时胜、即时平、即时负
print("\n整理后的数据（每3个一组）:")
grouped = []
for i in range(0, len(all_tds), 3):
    if i+2 < len(all_tds):
        grouped.append((all_tds[i], all_tds[i+1], all_tds[i+2]))
        
print(f"共 {len(grouped)} 组")
for i, g in enumerate(grouped[:10]):
    print(f"  {i+1}: {g}")
