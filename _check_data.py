import re
import os

# 检查 page_raw 文件
folder = '分析模板/2026.04.17'
files = sorted(os.listdir(folder))
html_files = [f for f in files if f.startswith('page_raw')]
print(f"HTML文件数: {len(html_files)}")

# 检查第一个文件
if html_files:
    path = os.path.join(folder, html_files[0])
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找日期、时间等
    patterns = [
        ('日期', r'"date"[:\s]+"([^"]+)"'),
        ('时间', r'"time"[:\s]+"([^"]+)"'),
        ('联赛', r'"league"[:\s]+"([^"]+)"'),
        ('编号', r'"match_num"[:\s]+"([^"]+)"'),
        ('主队', r'"home"[:\s]+"([^"]+)"'),
        ('客队', r'"away"[:\s]+"([^"]+)"'),
    ]
    
    for name, pattern in patterns:
        m = re.search(pattern, content)
        print(f"{name}: {m.group(1)[:30] if m else 'N/A'}")

print("\n检查 matches_full 数据:")
import json
with open('分析模板/matches_full_2026-04-17.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

m = data[0]
print(f"字段: {list(m.keys())}")
print(f"date: {m.get('date')}")
print(f"time: {m.get('time')}")
print(f"league: {m.get('league')}")
print(f"match_num: {m.get('match_num')}")
