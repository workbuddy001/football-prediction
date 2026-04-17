# -*- coding: utf-8 -*-
"""解析欧赔页面"""
import re

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找赔率表格
# 格式: 公司名 | 初盘胜 | 初盘平 | 初盘负 | 即时胜 | 即时平 | 即时负
results = []

# 找到赔率数据区域
table_match = re.search(r'_table_data">(.*?)</tbody>', content, re.S)
if table_match:
    table_content = table_match.group(1)
    
    # 找到所有公司行（每个公司有多个 tr）
    # tr class="tr_bdb td_show_cp" = 初盘数据行
    # tr 包含 class="bg-a" = 即时数据行
    
    companies = re.findall(r'<td[^>]*class="[^"]*tdis[^"]*"[^>]*>(.*?)</td>', table_content)
    print(f"找到 {len(companies)} 个公司")
    if companies:
        print(f"示例: {companies[:5]}")
    
    # 查找所有赔率行
    # 格式：每行3个赔率
    odds_rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_content, re.S)
    print(f"\n找到 {len(odds_rows)} 行")
    
    # 提取每行的赔率
    all_odds = []
    for row in odds_rows:
        tds = re.findall(r'<td[^>]*>([\d.]+)</td>', row)
        if len(tds) >= 3:
            all_odds.append(tds)
    
    print(f"提取了 {len(all_odds)} 组赔率")
    if all_odds:
        print(f"示例: {all_odds[:6]}")

# 更精确地解析
# 每个公司有两行：第一行是初盘，第二行（含bg-a class）是即时
company_names = re.findall(r'<td[^>]*class="[^"]*tdis[^"]*"[^>]*>.*?\(.*?\)</td>', content)
print(f"\n公司名称（简化）: {len(company_names)}")

# 直接搜索赔率序列模式
# 初盘: 1.83 3.90 3.06  即时: 1.91 3.92 2.85
pattern = r'<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>\s*</tr>\s*<tr[^>]*>\s*<td[^>]*class="[^"]*bg-a[^"]*"[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*class="[^"]*bg-a[^"]*"[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*class="[^"]*bg-a[^"]*"[^>]*>\s*([\d.]+)\s*</td>'

matches = re.findall(pattern, content)
print(f"\n精确匹配: {len(matches)} 组")
for i, m in enumerate(matches[:5]):
    print(f"  {i+1}: 初盘({m[0]},{m[1]},{m[2]}) 即时({m[3]},{m[4]},{m[5]})")

# 提取公司名（和赔率对应）
companies = re.findall(r'<td[^>]*class="[^"]*tdis[^"]*"[^>]*>([^<]+)</td>', content)
print(f"\n公司名: {len(companies)}")
for i, c in enumerate(companies[:5]):
    print(f"  {i+1}: {c.strip()}")
