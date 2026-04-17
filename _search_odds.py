import re

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 搜索 "胜" 相关的行
lines = content.split('\n')
for i, line in enumerate(lines):
    if '1.83' in line or '3.90' in line or '3.06' in line:
        print(f"行 {i}: {line[:200]}")
        break

# 搜索 "竞彩" 
idx = content.find('竞彩')
if idx > 0:
    print(f"\n找到竞彩于位置 {idx}:")
    print(content[max(0,idx-100):idx+200])

# 搜索数字序列 1.83 3.90 3.06
search_str = '1.83'
idx = content.find(search_str)
if idx > 0:
    print(f"\n找到 {search_str} 于位置 {idx}:")
    print(content[max(0,idx-200):idx+500])
