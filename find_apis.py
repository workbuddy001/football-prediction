#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re

# 获取竞彩手机版页面
url = 'https://m.sporttery.cn/mjc/zqgdjjv1/?mid=2039135'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
}

r = requests.get(url, headers=headers, timeout=15)
r.encoding = 'utf-8'

# 查找所有JS文件
js_files = re.findall(r'src=["\'](.*?\.js)["\']', r.text)
print('所有JS文件:')
for f in js_files:
    print(f'  {f}')

# 保存完整页面
with open('full_page.html', 'w', encoding='utf-8') as f:
    f.write(r.text)

# 查找data-属性和API调用
print('\n页面中的API URL:')
api_patterns = re.findall(r'["\']([^"\']*gateway[^"\']*)["\']', r.text)
for a in set(api_patterns):
    print(f'  {a}')

# 查找前瞻相关
preview = re.findall(r'(?:前瞻|analysis|preview|analyze|伤停|injury)[^<>]*', r.text, re.I)
print('\n前瞻相关内容:')
for p in preview[:10]:
    print(f'  {p[:100]}')
