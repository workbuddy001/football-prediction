#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re
import json

# 获取竞彩对阵页面
url = 'https://m.sporttery.cn/mjc/zqgdjjv1/?mid=2039135'
headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Accept': 'text/html,application/xhtml+xml',
}

r = requests.get(url, headers=headers, timeout=15)
r.encoding = 'utf-8'

# 查找所有JS文件
js_files = re.findall(r'<script[^>]+src=["\'](.*?)["\']', r.text)
print('JS文件:')
for f in js_files:
    print(f'  {f}')

# 查找可能的API URL
api_urls = re.findall(r'["\']([^"\']*api[^"\']*)["\']', r.text)
print('\n可能的API URL:')
for u in api_urls[:20]:
    print(f'  {u}')

# 查找webapi域名
webapi = re.findall(r'webapi\.sporttery\.cn[^\s"\'<>]*', r.text)
print('\nwebapi域名:')
for w in webapi[:20]:
    print(f'  {w}')

# 保存页面以便分析
with open('sporttery_analysis.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
print('\n页面已保存到 sporttery_analysis.html')
