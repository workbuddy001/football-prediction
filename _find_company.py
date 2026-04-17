# -*- coding: utf-8 -*-
"""查找公司名称"""
import re

with open('_ouzhi_page.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 搜索赔率行附近的文本
lines = content.split('\n')
for i, line in enumerate(lines):
    if '1.83' in line and 'klfc' in line:
        # 打印前后10行
        for j in range(max(0, i-15), min(len(lines), i+5)):
            print(f"{j}: {lines[j][:150]}")
        break
