#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
    'Referer': 'https://m.sporttery.cn/',
}

# 下载bssj.js
url = 'https://static.sporttery.cn/res_1_0/jcwm/default/zqlszl/bssj.js'
r = requests.get(url, headers=headers, timeout=10)
r.encoding = 'utf-8'

with open('bssj.js', 'w', encoding='utf-8') as f:
    f.write(r.text)

print(f'bssj.js 大小: {len(r.text)} 字节')

# 查找API调用
apis = re.findall(r'["\']([^"\']*gateway[^"\']*)["\']', r.text)
print('\nAPI URL:')
for a in set(apis):
    print(f'  {a}')

# 查找axios请求
axios = re.findall(r'(?:axios|fetch|get)\s*\(["\']([^"\']+)["\']', r.text)
print('\nAxios/Fetch请求:')
for a in set(axios):
    print(f'  {a}')

# 查找URL模板
url_templates = re.findall(r'url\s*:\s*["\']([^"\']+)["\']', r.text)
print('\nURL模板:')
for u in set(url_templates):
    print(f'  {u}')

# 查找方法名
methods = re.findall(r'(?:get|post|fetch)([A-Z]\w+)\s*\(', r.text)
print('\n方法名:')
for m in set(methods[:20]):
    print(f'  {m}')
