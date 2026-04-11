# 检查文件夹
import os
import re

base = '分析模板/3.14'
count = 0
for f in os.listdir(base):
    if '源数据' in f:
        count += 1

print(f'3.14共 {count} 个文件')

base = '分析模板/3.15'
count = 0
for f in os.listdir(base):
    if '源数据' in f:
        count += 1

print(f'3.15共 {count} 个文件')

# 尝试读取一个文件
filepath = '分析模板/3.14/周六001_中国女vs中国台女_源数据.md'
with open(filepath, 'r', encoding='utf-8') as file:
    content = file.read()
    
# 检查关键内容
if '澳门心水' in content:
    print('澳门心水: 找到')
else:
    print('澳门心水: 未找到')
    
if 'realtime_odds' in content:
    print('realtime_odds: 找到')
else:
    print('realtime_odds: 未找到')
